"""Verify Trinity data matches Atlas exactly."""
import requests
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from database import db

ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")
headers = {"Authorization": f"Bearer {ATLAS_KEY}", "Accept": "application/json"}
tickets = db["tickets"]
messages_col = db["messages"]

session = requests.Session()
session.headers.update(headers)
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

# Build Trinity lookup
print("Building Trinity lookups...")
trinity_by_atlas_id = {}
trinity_by_number = {}
for t in tickets.find(
    {"atlas_conversation_id": {"$exists": True}},
    {"_id": 0, "ticket_id": 1, "atlas_conversation_id": 1, "atlas_number": 1,
     "status": 1, "priority": 1, "escalation_level": 1, "customer_email": 1, "title": 1}
):
    trinity_by_atlas_id[t["atlas_conversation_id"]] = t
    if "atlas_number" in t:
        trinity_by_number[t["atlas_number"]] = t

print(f"Trinity: {len(trinity_by_atlas_id)} Atlas-linked tickets")

# Paginate through ALL Atlas conversations
missing = []
number_mismatch = []
status_mismatch = []
priority_mismatch = []
escalation_mismatch = []
atlas_total = 0
cursor_val = None

STATUS_MAP = {"open": "todo", "closed": "closed", "snoozed": "waiting", "pending": "waiting",
              "OPEN": "todo", "CLOSED": "closed", "SNOOZED": "waiting", "PENDING": "waiting"}
PRIORITY_MAP = {"URGENT": "urgent", "HIGH": "high", "MEDIUM": "medium", "LOW": "low", "NO_PRIORITY": "medium",
                "urgent": "urgent", "high": "high", "medium": "medium", "low": "low"}

print("Checking Atlas conversations...")
page_size = 100
cursor_val = 0

while True:
    url = f"https://api.atlas.so/v1/conversations?limit={page_size}&sort=number:asc&cursor={cursor_val}"
    resp = session.get(url, timeout=60)
    if not resp.ok:
        print(f"API error: {resp.status_code}")
        break
    data = resp.json()
    convos = data.get("data", [])
    if not convos:
        break

    for c in convos:
        atlas_total += 1
        cid = str(c.get("id", ""))
        num = c.get("number")

        if cid not in trinity_by_atlas_id:
            missing.append({"id": cid, "number": num, "status": c.get("status")})
            continue

        t = trinity_by_atlas_id[cid]

        # Verify ticket number
        expected_id = f"TKT-{num:06d}"
        if t["ticket_id"] != expected_id:
            number_mismatch.append({"atlas_num": num, "expected": expected_id, "actual": t["ticket_id"]})

        # Verify status
        atlas_status = STATUS_MAP.get(c.get("status", ""), c.get("status", "").lower())
        if t.get("status") != atlas_status:
            status_mismatch.append({"tid": t["ticket_id"], "atlas": c.get("status"), "trinity": t.get("status")})

        # Verify priority
        atlas_pri = PRIORITY_MAP.get(c.get("priority", ""), "medium")
        if t.get("priority") != atlas_pri:
            priority_mismatch.append({"tid": t["ticket_id"], "atlas": c.get("priority"), "trinity": t.get("priority")})

        # Verify escalation level
        atlas_esc = (c.get("customFields") or {}).get("support_level", "L1")
        if t.get("escalation_level") != atlas_esc:
            escalation_mismatch.append({"tid": t["ticket_id"], "atlas": atlas_esc, "trinity": t.get("escalation_level")})

    cursor_val += page_size
    if len(convos) < page_size:
        break
    if atlas_total % 5000 == 0:
        print(f"  ... checked {atlas_total}")
    time.sleep(0.3)

print(f"\n{'='*60}")
print(f"VERIFICATION RESULTS")
print(f"{'='*60}")
print(f"Atlas total: {atlas_total}")
print(f"Trinity Atlas-linked: {len(trinity_by_atlas_id)}")
print(f"")
print(f"Missing from Trinity:    {len(missing)}")
print(f"Ticket number mismatch:  {len(number_mismatch)}")
print(f"Status mismatch:         {len(status_mismatch)}")
print(f"Priority mismatch:       {len(priority_mismatch)}")
print(f"Escalation mismatch:     {len(escalation_mismatch)}")

if missing:
    print(f"\n--- Missing (first 10) ---")
    for m in missing[:10]:
        print(f"  atlas #{m['number']} ({m['id'][:16]}...) status={m['status']}")

if number_mismatch:
    print(f"\n--- Number mismatch (first 10) ---")
    for m in number_mismatch[:10]:
        print(f"  atlas #{m['atlas_num']}: expected={m['expected']}, actual={m['actual']}")

if status_mismatch:
    print(f"\n--- Status mismatch (first 10) ---")
    for m in status_mismatch[:10]:
        print(f"  {m['tid']}: atlas={m['atlas']}, trinity={m['trinity']}")

if priority_mismatch:
    print(f"\n--- Priority mismatch (first 10) ---")
    for m in priority_mismatch[:10]:
        print(f"  {m['tid']}: atlas={m['atlas']}, trinity={m['trinity']}")

if escalation_mismatch:
    print(f"\n--- Escalation mismatch (first 10) ---")
    for m in escalation_mismatch[:10]:
        print(f"  {m['tid']}: atlas={m['atlas']}, trinity={m['trinity']}")

total_issues = len(missing) + len(number_mismatch) + len(status_mismatch) + len(priority_mismatch) + len(escalation_mismatch)
print(f"\nTOTAL DEVIATIONS: {total_issues}")
