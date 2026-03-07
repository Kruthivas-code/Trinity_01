"""
One-time catchup script to sync all Atlas conversations from the last 24 hours.
Handles the gap from machine sleep period.
Run once, then delete.
"""
import requests
import time
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import os

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]
tickets_col = db["tickets"]
messages_col = db["messages"]

def _headers():
    return {"Accept": "application/json", "Authorization": f"Bearer {ATLAS_KEY}"}

# Import sync functions from the main module
import sys
sys.path.insert(0, "/app/backend")
from services.atlas_sync import (
    _sync_messages, _sync_fields, _create_ticket_from_conv,
    _build_agent_email_map, _fetch_tags,
)

def run_catchup(lookback_hours=24):
    print(f"[CATCHUP] Starting — looking back {lookback_hours} hours")
    
    agent_map = _build_agent_email_map()
    tag_map = _fetch_tags()
    print(f"[CATCHUP] Loaded {len(agent_map)} agent mappings, {len(tag_map)} tags")
    
    start_date = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    cursor = 0
    total_checked = 0
    total_created = 0
    total_updated = 0
    total_msgs = 0
    page = 0
    
    while True:
        params = {"startDate": start_date, "limit": 100, "cursor": cursor}
        
        resp = requests.get(f"{ATLAS_API}/conversations", params=params, headers=_headers(), timeout=30)
        if resp.status_code != 200:
            print(f"[CATCHUP] API error: {resp.status_code} {resp.text[:200]}")
            break
        
        data = resp.json()
        convs = data.get("data", [])
        api_total = data.get("total", 0)
        
        if not convs:
            break
        
        page += 1
        print(f"[CATCHUP] Page {page}: {len(convs)} conversations (API total: {api_total})")
        
        for conv in convs:
            atlas_id = str(conv.get("id", ""))
            num = conv.get("number")
            total_checked += 1
            
            existing = tickets_col.find_one(
                {"atlas_conversation_id": atlas_id},
                {"_id": 0}
            )
            
            if existing:
                # Sync fields
                field_changes, _ = _sync_fields(conv, existing, agent_map)
                total_updated += field_changes
                
                # Sync messages
                new_msgs = _sync_messages(atlas_id, existing["ticket_id"])
                total_msgs += new_msgs
                
                # Update last_synced_at
                tickets_col.update_one(
                    {"ticket_id": existing["ticket_id"]},
                    {"$set": {"last_synced_at": datetime.now(timezone.utc)}}
                )
            else:
                # Create new ticket
                ticket_id = _create_ticket_from_conv(conv, tag_map, agent_map)
                if ticket_id:
                    total_created += 1
                    # Sync messages for new ticket
                    new_msgs = _sync_messages(atlas_id, ticket_id)
                    total_msgs += new_msgs
                    print(f"  CREATED: {ticket_id} (Atlas #{num}) +{new_msgs} msgs")
            
            time.sleep(0.1)  # Rate limit
        
        cursor += len(convs)
        if cursor >= api_total:
            break
    
    print(f"\n[CATCHUP] DONE")
    print(f"  Checked: {total_checked}")
    print(f"  Created: {total_created}")
    print(f"  Field updates: {total_updated}")
    print(f"  Messages synced: {total_msgs}")
    return {
        "checked": total_checked,
        "created": total_created,
        "updated": total_updated,
        "messages": total_msgs,
    }

if __name__ == "__main__":
    run_catchup(24)
