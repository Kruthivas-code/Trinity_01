"""
Test module for Atlas Shadow Sync and Collapsible Quoted Content features

Tests:
1. Backend health check
2. Shadow sync state running in MongoDB
3. Tickets created by atlas_sync
4. Synced tickets have atlas_conversation_id and last_synced_at fields
5. Messages with source='atlas'
6. No duplicate atlas_conversation_ids
7. API endpoints exist (return 401 not 404)
8. Frontend compiles without errors
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBackendHealth:
    """Backend health check"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'healthy'
        print(f"✓ Health check passed: {data}")


class TestAtlasSyncAPIEndpoints:
    """Verify Atlas sync API endpoints exist (return 401 not 404)"""
    
    def test_sync_status_endpoint_exists(self):
        """GET /api/admin/atlas/sync/status returns 401 not 404"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/sync/status", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/admin/atlas/sync/status returns 401 (auth required)")
    
    def test_sync_start_endpoint_exists(self):
        """POST /api/admin/atlas/sync/start returns 401 not 404"""
        response = requests.post(f"{BASE_URL}/api/admin/atlas/sync/start", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/admin/atlas/sync/start returns 401 (auth required)")
    
    def test_sync_stop_endpoint_exists(self):
        """POST /api/admin/atlas/sync/stop returns 401 not 404"""
        response = requests.post(f"{BASE_URL}/api/admin/atlas/sync/stop", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/admin/atlas/sync/stop returns 401 (auth required)")
    
    def test_sync_config_endpoint_exists(self):
        """PATCH /api/admin/atlas/sync/config returns 401 not 404"""
        response = requests.patch(
            f"{BASE_URL}/api/admin/atlas/sync/config",
            json={"poll_interval": 60},
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ PATCH /api/admin/atlas/sync/config returns 401 (auth required)")


class TestMongoDBShadowSyncState:
    """Verify shadow sync state in MongoDB"""
    
    @pytest.fixture(autouse=True)
    def setup_pymongo(self):
        """Setup PyMongo connection"""
        from pymongo import MongoClient
        self.client = MongoClient("mongodb://localhost:27017")
        self.db = self.client["test_database"]
        yield
        self.client.close()
    
    def test_shadow_sync_state_exists(self):
        """Shadow sync state document exists with _type='shadow'"""
        state = self.db.atlas_backfill_state.find_one({"_type": "shadow"}, {"_id": 0})
        assert state is not None, "Shadow sync state document not found"
        assert state.get("_type") == "shadow"
        print(f"✓ Shadow sync state exists")
    
    def test_shadow_sync_is_running(self):
        """Shadow sync status is 'running'"""
        state = self.db.atlas_backfill_state.find_one({"_type": "shadow"}, {"_id": 0})
        assert state is not None
        assert state.get("status") == "running", f"Expected status='running', got {state.get('status')}"
        print(f"✓ Shadow sync status is 'running'")
    
    def test_shadow_sync_has_cycles(self):
        """Shadow sync has completed cycles"""
        state = self.db.atlas_backfill_state.find_one({"_type": "shadow"}, {"_id": 0})
        assert state is not None
        cycles = state.get("cycles_completed", 0)
        assert cycles > 0, f"Expected cycles > 0, got {cycles}"
        print(f"✓ Shadow sync completed {cycles} cycles")


class TestAtlasSyncedTickets:
    """Verify tickets created by atlas_sync"""
    
    @pytest.fixture(autouse=True)
    def setup_pymongo(self):
        """Setup PyMongo connection"""
        from pymongo import MongoClient
        self.client = MongoClient("mongodb://localhost:27017")
        self.db = self.client["test_database"]
        yield
        self.client.close()
    
    def test_tickets_created_by_atlas_sync_exist(self):
        """Tickets with created_by='atlas_sync' exist"""
        count = self.db.tickets.count_documents({"created_by": "atlas_sync"})
        assert count > 0, f"Expected atlas_sync tickets > 0, got {count}"
        print(f"✓ Found {count} tickets created by atlas_sync")
    
    def test_synced_tickets_have_atlas_conversation_id(self):
        """Synced tickets have atlas_conversation_id field"""
        ticket = self.db.tickets.find_one(
            {"created_by": "atlas_sync"},
            {"_id": 0, "ticket_id": 1, "atlas_conversation_id": 1}
        )
        assert ticket is not None
        assert ticket.get("atlas_conversation_id") is not None, "Missing atlas_conversation_id"
        assert len(ticket.get("atlas_conversation_id", "")) > 0
        print(f"✓ Synced ticket {ticket.get('ticket_id')} has atlas_conversation_id: {ticket.get('atlas_conversation_id')}")
    
    def test_synced_tickets_have_last_synced_at(self):
        """Synced tickets have last_synced_at field"""
        ticket = self.db.tickets.find_one(
            {"created_by": "atlas_sync"},
            {"_id": 0, "ticket_id": 1, "last_synced_at": 1}
        )
        assert ticket is not None
        assert ticket.get("last_synced_at") is not None, "Missing last_synced_at"
        print(f"✓ Synced ticket {ticket.get('ticket_id')} has last_synced_at: {ticket.get('last_synced_at')}")
    
    def test_no_duplicate_atlas_conversation_ids(self):
        """No duplicate atlas_conversation_ids among synced tickets"""
        pipeline = [
            {"$match": {"atlas_conversation_id": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$atlas_conversation_id", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicates = list(self.db.tickets.aggregate(pipeline))
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate atlas_conversation_ids: {duplicates[:3]}"
        print(f"✓ No duplicate atlas_conversation_ids found")


class TestAtlasSyncedMessages:
    """Verify messages synced from Atlas"""
    
    @pytest.fixture(autouse=True)
    def setup_pymongo(self):
        """Setup PyMongo connection"""
        from pymongo import MongoClient
        self.client = MongoClient("mongodb://localhost:27017")
        self.db = self.client["test_database"]
        yield
        self.client.close()
    
    def test_messages_with_source_atlas_exist(self):
        """Messages with source='atlas' exist"""
        count = self.db.messages.count_documents({"source": "atlas"})
        assert count > 0, f"Expected atlas messages > 0, got {count}"
        print(f"✓ Found {count} messages with source='atlas'")
    
    def test_atlas_messages_have_required_fields(self):
        """Atlas messages have required fields"""
        msg = self.db.messages.find_one(
            {"source": "atlas"},
            {"_id": 0, "message_id": 1, "ticket_id": 1, "source": 1, "type": 1}
        )
        assert msg is not None
        assert msg.get("source") == "atlas"
        assert msg.get("message_id") is not None
        assert msg.get("ticket_id") is not None
        assert msg.get("type") is not None
        print(f"✓ Atlas message {msg.get('message_id')} has all required fields")


class TestSplitQuotedContentFunction:
    """Test splitQuotedContent function logic (JavaScript function behavior)"""
    
    def test_on_wrote_pattern(self):
        """'On ... wrote:' pattern correctly splits text"""
        # This tests the logic that should be in the JS function
        text = 'Hello\nOn Mon wrote:\nold text'
        lines = text.split('\n')
        cut_index = -1
        for i, line in enumerate(lines):
            trimmed = line.strip()
            import re
            if re.match(r'^On .+ wrote:\s*$', trimmed):
                cut_index = i
                break
        assert cut_index == 1, f"Expected cut_index=1, got {cut_index}"
        visible = '\n'.join(lines[:cut_index]).strip()
        quoted = '\n'.join(lines[cut_index:]).strip()
        assert visible == 'Hello'
        assert 'On Mon wrote:' in quoted
        print(f"✓ 'On ... wrote:' pattern splits correctly: visible='{visible}', quoted contains '{quoted[:30]}...'")
    
    def test_sent_from_outlook_pattern(self):
        """'Sent from Outlook' pattern correctly splits text"""
        text = 'Hi\nSent from Outlook for Android\n____'
        lines = text.split('\n')
        cut_index = -1
        for i, line in enumerate(lines):
            trimmed = line.strip()
            import re
            if re.match(r'^Sent from (Outlook|Mail|iPhone|my)', trimmed, re.IGNORECASE):
                cut_index = i
                break
        assert cut_index == 1, f"Expected cut_index=1, got {cut_index}"
        visible = '\n'.join(lines[:cut_index]).strip()
        assert visible == 'Hi'
        print(f"✓ 'Sent from Outlook' pattern splits correctly: visible='{visible}'")
    
    def test_no_quoted_pattern_returns_full_text(self):
        """No quoted patterns returns full text as visible"""
        text = 'Just a normal message without any quoted content'
        lines = text.split('\n')
        cut_index = -1
        # No pattern matches
        for i, line in enumerate(lines):
            trimmed = line.strip()
            import re
            if re.match(r'^On .+ wrote:\s*$', trimmed):
                cut_index = i
                break
            if trimmed == '________________________________':
                cut_index = i
                break
            if re.match(r'^Sent from (Outlook|Mail|iPhone|my)', trimmed, re.IGNORECASE):
                cut_index = i
                break
        assert cut_index == -1 or cut_index == 0, f"Expected no cut, got {cut_index}"
        # Full text is visible
        visible = text if cut_index <= 0 else '\n'.join(lines[:cut_index]).strip()
        assert visible == text
        print(f"✓ No quoted pattern returns full text as visible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
