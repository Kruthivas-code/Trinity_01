"""One-time backfill: link unlinked non-closed tickets to Atlas conversations."""
import sys, os, re, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import tickets_collection
from datetime import datetime, timezone, timedelta
from pymongo.errors import DuplicateKeyError

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "3OEY066356RJIPOYM7N25YL5EQH5H5DVWSV40TCG9CRXYNX0C3B7K0RES960HBHM")
headers = {"Accept": "application/json", "Authorization": f"Bearer {ATLAS_KEY}"}

tkt_re = re.compile(r"^TKT-(\d+)$")
unlinked = list(tickets_collection.find(
    {"$or": [{"atlas_conversation_id": None}, {"atlas_conversation_id": {"$exists": False}}], "status": {"$ne": "closed"}},
    {"_id": 0, "ticket_id": 1}
))
needed = {}
for t in unlinked:
    m = tkt_re.match(t["ticket_id"])
    if m:
        needed[int(m.group(1))] = t["ticket_id"]

print(f"[BACKFILL] {len(needed)} non-closed unlinked tickets")

now = datetime.now(timezone.utc)
start = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
linked = 0
dupes = 0
cursor = 0

while needed and cursor < 50000:
    resp = requests.get(f"{ATLAS_API}/conversations", params={"startDate": start, "limit": 200, "cursor": cursor}, headers=headers, timeout=30)
    if resp.status_code != 200:
        break
    convs = resp.json().get("data", [])
    if not convs:
        break
    for conv in convs:
        num = conv.get("number")
        if num in needed:
            try:
                tickets_collection.update_one(
                    {"ticket_id": needed[num]},
                    {"$set": {"atlas_conversation_id": str(conv["id"]), "atlas_number": num}}
                )
                linked += 1
            except DuplicateKeyError:
                # Atlas conv already linked to another ticket — close the orphan
                tickets_collection.update_one(
                    {"ticket_id": needed[num]},
                    {"$set": {"status": "closed", "auto_closed_reason": "duplicate_of_atlas_linked"}}
                )
                dupes += 1
            del needed[num]
    cursor += len(convs)
    if cursor % 2000 == 0:
        print(f"  ...scanned {cursor}, linked {linked}, dupes={dupes}, remaining={len(needed)}")

print(f"[BACKFILL] Done: linked={linked}, dupes_closed={dupes}, remaining={len(needed)}")
