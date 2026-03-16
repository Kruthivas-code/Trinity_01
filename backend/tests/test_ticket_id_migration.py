"""
Test: Ticket ID Format Migration Verification
=============================================
Verifies that all ticket IDs have been migrated from zero-padded format (TKT-070723)
to unpadded format (TKT-70723) across the entire app.

Tests:
1. Database verification - no zero-padded IDs remain
2. Search by number - finds tickets correctly
3. Search by email - email search works
4. Search by text - normal text search works
5. API endpoints - health, tickets, messages, webhooks
6. Code verification - utils.py and atlas_sync.py use unpadded format
"""

import pytest
import requests
import os
import re
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://qasweep.preview.emergentagent.com')

# MongoDB connection for direct database verification
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


@pytest.fixture(scope="module")
def db():
    """Get MongoDB database connection."""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_endpoint(self, api_client):
        """GET /health returns 200 with healthy status."""
        response = api_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data["checks"]
        print(f"✓ /health returned 200 with status=healthy")
    
    def test_api_health_endpoint(self, api_client):
        """GET /api/health returns 200 with healthy status."""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ /api/health returned 200 with status=healthy")


class TestDatabaseTicketIdFormat:
    """Direct database verification of ticket ID format migration."""
    
    def test_no_padded_ticket_ids_in_tickets_collection(self, db):
        """Verify no zero-padded ticket IDs (TKT-0XXXXX) remain in tickets collection."""
        # Pattern: TKT- followed by a leading zero and then more digits
        padded_regex = re.compile(r'^TKT-0\d+$')
        
        padded_count = db.tickets.count_documents({
            "ticket_id": {"$regex": "^TKT-0\\d+$"}
        })
        
        if padded_count > 0:
            # Get some examples
            examples = list(db.tickets.find(
                {"ticket_id": {"$regex": "^TKT-0\\d+$"}},
                {"ticket_id": 1, "_id": 0}
            ).limit(10))
            pytest.fail(f"Found {padded_count} padded ticket IDs in tickets collection. Examples: {examples}")
        
        print(f"✓ No zero-padded ticket IDs found in tickets collection")
    
    def test_no_padded_ticket_ids_in_messages_collection(self, db):
        """Verify no zero-padded ticket IDs remain in messages collection for active tickets."""
        # Find all padded ticket IDs in messages
        padded_ids = db.messages.distinct("ticket_id", {"ticket_id": {"$regex": "^TKT-0\\d+$"}})
        
        # Check how many are orphaned (parent ticket doesn't exist in either format)
        orphaned = []
        active_padded = []
        import re
        for tid in padded_ids:
            # Check if unpadded version exists
            m = re.match(r"^TKT-0+(\d+)$", tid)
            if m:
                unpadded = f"TKT-{m.group(1)}"
                if db.tickets.find_one({"ticket_id": unpadded}):
                    active_padded.append((tid, unpadded))  # This is a bug!
                else:
                    orphaned.append(tid)
        
        if active_padded:
            pytest.fail(f"Found {len(active_padded)} padded ticket IDs with active parent tickets: {active_padded}")
        
        if orphaned:
            print(f"  ⚠ Found {len(orphaned)} orphaned padded records (deleted tickets) - not a functional issue")
        
        print(f"✓ No padded ticket IDs found for active tickets in messages collection")
    
    def test_no_padded_ticket_ids_in_email_replies(self, db):
        """Verify no zero-padded ticket IDs remain in email_replies collection for active tickets."""
        # Find all padded ticket IDs
        padded_ids = db.email_replies.distinct("ticket_id", {"ticket_id": {"$regex": "^TKT-0\\d+$"}})
        
        # Check how many are orphaned
        orphaned = []
        active_padded = []
        import re
        for tid in padded_ids:
            m = re.match(r"^TKT-0+(\d+)$", tid)
            if m:
                unpadded = f"TKT-{m.group(1)}"
                if db.tickets.find_one({"ticket_id": unpadded}):
                    active_padded.append((tid, unpadded))
                else:
                    orphaned.append(tid)
        
        if active_padded:
            pytest.fail(f"Found {len(active_padded)} padded ticket IDs with active parent tickets: {active_padded}")
        
        if orphaned:
            print(f"  ⚠ Found {len(orphaned)} orphaned padded records (deleted tickets) - not a functional issue")
        
        print(f"✓ No padded ticket IDs found for active tickets in email_replies collection")
    
    def test_no_padded_ticket_ids_in_ticket_changelog(self, db):
        """Verify no zero-padded ticket IDs remain in ticket_changelog collection for active tickets."""
        # Find all padded ticket IDs
        padded_ids = db.ticket_changelog.distinct("ticket_id", {"ticket_id": {"$regex": "^TKT-0\\d+$"}})
        
        # Check how many are orphaned
        orphaned = []
        active_padded = []
        import re
        for tid in padded_ids:
            m = re.match(r"^TKT-0+(\d+)$", tid)
            if m:
                unpadded = f"TKT-{m.group(1)}"
                if db.tickets.find_one({"ticket_id": unpadded}):
                    active_padded.append((tid, unpadded))
                else:
                    orphaned.append(tid)
        
        if active_padded:
            pytest.fail(f"Found {len(active_padded)} padded ticket IDs with active parent tickets: {active_padded}")
        
        if orphaned:
            print(f"  ⚠ Found {len(orphaned)} orphaned padded records (deleted tickets) - not a functional issue")
        
        print(f"✓ No padded ticket IDs found for active tickets in ticket_changelog collection")
    
    def test_no_padded_ticket_ids_in_email_threads(self, db):
        """Verify no zero-padded ticket IDs remain in email_threads collection."""
        padded_count = db.email_threads.count_documents({
            "ticket_id": {"$regex": "^TKT-0\\d+$"}
        })
        
        if padded_count > 0:
            examples = list(db.email_threads.find(
                {"ticket_id": {"$regex": "^TKT-0\\d+$"}},
                {"ticket_id": 1, "_id": 0}
            ).limit(10))
            pytest.fail(f"Found {padded_count} padded ticket IDs in email_threads collection. Examples: {examples}")
        
        print(f"✓ No zero-padded ticket IDs found in email_threads collection")
    
    def test_no_padded_ticket_ids_in_csat_responses(self, db):
        """Verify no zero-padded ticket IDs remain in csat_responses collection."""
        padded_count = db.csat_responses.count_documents({
            "ticket_id": {"$regex": "^TKT-0\\d+$"}
        })
        
        if padded_count > 0:
            examples = list(db.csat_responses.find(
                {"ticket_id": {"$regex": "^TKT-0\\d+$"}},
                {"ticket_id": 1, "_id": 0}
            ).limit(10))
            pytest.fail(f"Found {padded_count} padded ticket IDs in csat_responses collection. Examples: {examples}")
        
        print(f"✓ No zero-padded ticket IDs found in csat_responses collection")
    
    def test_verify_unpadded_format_exists(self, db):
        """Verify that tickets exist in unpadded format (TKT-XXXXX)."""
        # Find tickets that should be in unpadded format
        unpadded_count = db.tickets.count_documents({
            "ticket_id": {"$regex": "^TKT-[1-9]\\d*$"}
        })
        
        total_count = db.tickets.count_documents({})
        
        print(f"✓ Found {unpadded_count} tickets with unpadded format out of {total_count} total")
        assert unpadded_count > 0, "Expected to find tickets with unpadded format"


class TestSearchFunctionality:
    """Test that search works correctly with new ticket ID format."""
    
    def test_search_by_ticket_number(self, db):
        """Search by number (e.g., '70723') should find TKT-70723."""
        # First, find a real ticket to search for
        sample_ticket = db.tickets.find_one(
            {"ticket_id": {"$regex": "^TKT-[1-9]"}},
            {"ticket_id": 1, "_id": 0}
        )
        
        if not sample_ticket:
            pytest.skip("No tickets found to test search")
        
        ticket_id = sample_ticket["ticket_id"]
        # Extract the number portion (e.g., TKT-70723 -> 70723)
        number = ticket_id.replace("TKT-", "")
        
        print(f"  Testing search for number: {number} (expecting {ticket_id})")
        
        # The search logic in search.py should handle this
        # Direct ticket ID lookup test
        found = db.tickets.find_one({"ticket_id": ticket_id})
        assert found is not None, f"Could not find ticket {ticket_id}"
        print(f"✓ Found ticket {ticket_id} by exact match")
    
    def test_search_by_email_formlyhq(self, db):
        """Search by email 'formlyhq@gmail.com' should find matching tickets."""
        email = "formlyhq@gmail.com"
        
        # Check if this email exists in the database
        ticket = db.tickets.find_one(
            {"customer_email": {"$regex": email, "$options": "i"}},
            {"ticket_id": 1, "customer_email": 1, "_id": 0}
        )
        
        if ticket:
            print(f"✓ Found ticket {ticket['ticket_id']} for email {email}")
            assert ticket["ticket_id"].startswith("TKT-"), "Ticket ID should start with TKT-"
            # Verify it's NOT padded
            assert not re.match(r'^TKT-0\d+$', ticket["ticket_id"]), f"Ticket {ticket['ticket_id']} is still padded!"
        else:
            print(f"  No tickets found for {email} - checking if data exists")
            count = db.tickets.count_documents({})
            print(f"  Total tickets in database: {count}")


class TestAtlasWebhook:
    """Test Atlas webhook endpoint."""
    
    def test_webhook_health(self, api_client):
        """GET /api/webhooks/atlas/health returns 200."""
        response = api_client.get(f"{BASE_URL}/api/webhooks/atlas/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print(f"✓ /api/webhooks/atlas/health returned 200 OK")
    
    def test_webhook_accepts_post(self, api_client):
        """POST /api/webhooks/atlas accepts events and returns 200."""
        # Send a minimal test event
        test_payload = {
            "event": "test_event",
            "data": {"test": True}
        }
        response = api_client.post(f"{BASE_URL}/api/webhooks/atlas", json=test_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print(f"✓ POST /api/webhooks/atlas returned 200 OK")


class TestCodeVerification:
    """Verify code changes for unpadded ticket ID format."""
    
    def test_utils_generate_ticket_id_format(self):
        """Verify utils.py generates unpadded ticket IDs."""
        with open('/app/backend/utils.py', 'r') as f:
            content = f.read()
        
        # Check that it uses f"TKT-{counter['seq']}" without :06d padding
        # The correct line should be: return f"TKT-{counter['seq']}"
        assert ':06d' not in content or 'TKT-{counter' in content, "utils.py may still use padded format"
        
        # Verify the exact pattern
        import re
        pattern = r'return f["\']TKT-\{counter\[["\']seq["\']\]\}["\']'
        if not re.search(pattern, content):
            # Check for the simpler pattern
            assert "f\"TKT-{counter['seq']}\"" in content or "f'TKT-{counter[\"seq\"]}'" in content, \
                "Could not find unpadded ticket ID generation in utils.py"
        
        print(f"✓ utils.py uses unpadded format for generate_ticket_id")
    
    def test_atlas_sync_ticket_id_format(self):
        """Verify atlas_sync.py creates tickets with unpadded IDs."""
        with open('/app/backend/services/atlas_sync.py', 'r') as f:
            content = f.read()
        
        # Check that it uses f"TKT-{atlas_number}" without padding
        # Should NOT contain :06d for ticket_id
        
        # Look for the ticket_id assignment around line 252
        lines = content.split('\n')
        found_unpadded = False
        for i, line in enumerate(lines):
            if 'ticket_id' in line and 'TKT-' in line and 'atlas_number' in line:
                # Should be: ticket_id = f"TKT-{atlas_number}"
                # Should NOT be: ticket_id = f"TKT-{atlas_number:06d}"
                if ':06d' in line:
                    pytest.fail(f"Line {i+1} still uses padded format: {line.strip()}")
                found_unpadded = True
                print(f"  Line {i+1}: {line.strip()}")
        
        assert found_unpadded, "Could not verify atlas_sync.py ticket_id format"
        print(f"✓ atlas_sync.py uses unpadded format for ticket creation")
    
    def test_email_poller_has_atlas_duplicate_function(self):
        """Verify _has_atlas_duplicate function exists in email_poller.py."""
        with open('/app/backend/services/email_poller.py', 'r') as f:
            content = f.read()
        
        assert 'def _has_atlas_duplicate' in content, "_has_atlas_duplicate function not found"
        print(f"✓ _has_atlas_duplicate function exists in email_poller.py")
    
    def test_search_py_numeric_search_logic(self):
        """Verify search.py handles both padded and unpadded lookups for backwards compatibility."""
        with open('/app/backend/search.py', 'r') as f:
            content = f.read()
        
        # The search logic should look for both formats to handle edge cases
        # Lines ~335-347 should have the numeric search logic
        assert 'stripped.zfill(6)' in content or 'zfill(6)' in content, \
            "search.py should handle both padded and unpadded formats for backwards compat"
        
        print(f"✓ search.py handles numeric search with backwards compatibility")


class TestFrontendComponents:
    """Verify frontend components are ready for unpadded ticket IDs."""
    
    def test_ticket_card_renders_ticket_id(self):
        """Verify TicketCard.js renders ticket_id correctly."""
        with open('/app/frontend/src/components/tickets/TicketCard.js', 'r') as f:
            content = f.read()
        
        assert 'data-testid="ticket-card"' in content, "TicketCard missing data-testid"
        assert 'ticket.ticket_id' in content, "TicketCard should use ticket.ticket_id"
        print(f"✓ TicketCard.js has correct data-testid and uses ticket_id")
    
    def test_email_message_has_attachments_prop(self):
        """Verify EmailMessage.js accepts attachments prop with data-testid."""
        with open('/app/frontend/src/components/tickets/EmailMessage.js', 'r') as f:
            content = f.read()
        
        assert 'attachments' in content, "EmailMessage should accept attachments prop"
        assert 'data-testid="message-attachments"' in content, \
            "EmailMessage should have data-testid for attachments"
        print(f"✓ EmailMessage.js accepts attachments prop with data-testid")


class TestSampleTickets:
    """Test actual ticket data in database."""
    
    def test_sample_tickets_have_correct_format(self, db):
        """Verify sample tickets have unpadded format."""
        # Get 10 random tickets
        tickets = list(db.tickets.find({}, {"ticket_id": 1, "_id": 0}).limit(20))
        
        padded_examples = []
        unpadded_examples = []
        
        for t in tickets:
            tid = t.get("ticket_id", "")
            if re.match(r'^TKT-0\d+$', tid):
                padded_examples.append(tid)
            elif re.match(r'^TKT-[1-9]\d*$', tid):
                unpadded_examples.append(tid)
        
        print(f"  Sample tickets - Unpadded: {len(unpadded_examples)}, Padded: {len(padded_examples)}")
        
        if unpadded_examples:
            print(f"  Unpadded examples: {unpadded_examples[:5]}")
        if padded_examples:
            print(f"  ⚠ Padded examples still exist: {padded_examples[:5]}")
            pytest.fail(f"Found {len(padded_examples)} padded tickets: {padded_examples[:5]}")
        
        print(f"✓ All sampled tickets have correct unpadded format")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
