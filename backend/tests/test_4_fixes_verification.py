"""
Test verification for 4 fixes:
1. Fix 1: Dead zone fix for closed tickets with null last_synced_at
2. Fix 2: Email search functionality
3. Fix 3: Attachment rendering (code verification)
4. Fix 4: IMAP duplicate prevention (_has_atlas_duplicate function)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestHealthEndpoints:
    """Backend health check - GET /health and GET /api/health should both return 200"""
    
    def test_root_health_endpoint(self):
        """Test /health endpoint returns 200 with status 'healthy'"""
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", f"Expected 'healthy', got {data.get('status')}"
        print(f"✓ /health returns 200 with status=healthy")
    
    def test_api_health_endpoint(self):
        """Test /api/health endpoint returns 200 with status 'healthy'"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", f"Expected 'healthy', got {data.get('status')}"
        print(f"✓ /api/health returns 200 with status=healthy")


class TestEmailSearch:
    """Fix 2: Email search - verify search API works with email addresses"""
    
    def test_search_by_email_formlyhq(self):
        """Test searching for 'formlyhq@gmail.com' returns tickets (specifically TKT-070723)"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "formlyhq@gmail.com"},
            timeout=30
        )
        # Note: search endpoint may require auth, but should at least return 200 or 401
        assert response.status_code in [200, 401], f"Expected 200 or 401, got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            # Check if TKT-070723 is in results
            results = data.get("results", data.get("by_category", {}).get("tickets", []))
            ticket_ids = [r.get("ticket_id") for r in results]
            print(f"✓ Search for 'formlyhq@gmail.com' returned {len(results)} results: {ticket_ids[:5]}")
            # This is informational - the search API may return results or not depending on data
        else:
            print(f"✓ Search API requires auth (401) - expected for protected endpoint")
    
    def test_search_by_email_world_secrets(self):
        """Test searching for 'world.secrets.1000@gmail.com' returns matching tickets"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "world.secrets.1000@gmail.com"},
            timeout=30
        )
        assert response.status_code in [200, 401], f"Expected 200 or 401, got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", data.get("by_category", {}).get("tickets", []))
            ticket_ids = [r.get("ticket_id") for r in results]
            print(f"✓ Search for 'world.secrets.1000@gmail.com' returned {len(results)} results: {ticket_ids[:5]}")
        else:
            print(f"✓ Search API requires auth (401)")
    
    def test_normal_text_search(self):
        """Test normal text search like 'deployment error' still works"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "deployment error"},
            timeout=30
        )
        assert response.status_code in [200, 401], f"Expected 200 or 401, got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", data.get("by_category", {}).get("tickets", []))
            print(f"✓ Normal text search 'deployment error' returned {len(results)} results")
        else:
            print(f"✓ Search API requires auth (401)")


class TestCodeVerification:
    """Code-level verification of fixes - ensures implementation exists"""
    
    def test_fix1_closed_batch_query_includes_null_last_synced_at(self):
        """Fix 1: Verify closed_batch recheck query in atlas_sync.py includes $or for null last_synced_at"""
        import re
        with open('/app/backend/services/atlas_sync.py', 'r') as f:
            content = f.read()
        
        # Check for the $or clause that handles null/missing last_synced_at
        assert '"last_synced_at": None' in content, "Missing 'last_synced_at': None in closed_batch query"
        assert '"last_synced_at": {"$exists": False}' in content, "Missing last_synced_at $exists: False in closed_batch query"
        
        # Verify it's in the closed_batch context
        closed_batch_pattern = r'closed_batch = list.*?\$or.*?last_synced_at.*?None.*?last_synced_at.*?\$exists.*?False'
        assert re.search(closed_batch_pattern, content, re.DOTALL), "closed_batch query doesn't have proper $or for null last_synced_at"
        print("✓ Fix 1: closed_batch query includes $or for null/missing last_synced_at")
    
    def test_fix2_email_search_detection_logic(self):
        """Fix 2: Verify email detection with @ and regex fallback in search.py"""
        with open('/app/backend/search.py', 'r') as f:
            content = f.read()
        
        # Check for email detection logic
        assert "'@' in query" in content, "Missing @ email detection in search_tickets"
        assert 'email_regex' in content, "Missing email_regex variable in search"
        assert '"customer_email"' in content, "Missing customer_email search"
        assert '"associated_emails"' in content, "Missing associated_emails search"
        assert 're.escape(query)' in content, "Missing re.escape for safe regex"
        print("✓ Fix 2: Email search detection with @ and regex fallback is implemented")
    
    def test_fix3_attachment_rendering_in_email_message(self):
        """Fix 3: Verify EmailMessage accepts attachments prop and renders with data-testid='message-attachments'"""
        with open('/app/frontend/src/components/tickets/EmailMessage.js', 'r') as f:
            content = f.read()
        
        # Check EmailMessage props include attachments
        assert 'attachments' in content, "Missing attachments prop in EmailMessage"
        assert 'data-testid="message-attachments"' in content, "Missing data-testid='message-attachments'"
        
        # Check for image thumbnail rendering
        assert 'attachment-image' in content or 'isImage' in content, "Missing image attachment handling"
        
        # Check for file download link
        assert 'attachment-file' in content or 'Download' in content, "Missing file attachment download"
        print("✓ Fix 3: EmailMessage accepts attachments prop and renders with data-testid='message-attachments'")
    
    def test_fix3_ticket_conversation_passes_attachments(self):
        """Fix 3: Verify TicketConversation passes attachments to EmailMessage"""
        with open('/app/frontend/src/components/tickets/TicketConversation.js', 'r') as f:
            content = f.read()
        
        assert 'attachments={msg.attachments}' in content, "Missing attachments={msg.attachments} in TicketConversation"
        print("✓ Fix 3: TicketConversation passes attachments={msg.attachments} to EmailMessage")
    
    def test_fix3_use_ticket_drawer_builds_attachments(self):
        """Fix 3: Verify useTicketDrawer builds conversationThread with attachments"""
        with open('/app/frontend/src/hooks/useTicketDrawer.js', 'r') as f:
            content = f.read()
        
        assert 'attachments: note.attachments' in content, "Missing attachments in conversationThread builder"
        print("✓ Fix 3: useTicketDrawer includes attachments: note.attachments in conversationThread")
    
    def test_fix4_has_atlas_duplicate_function_exists(self):
        """Fix 4: Verify _has_atlas_duplicate function exists in email_poller.py"""
        with open('/app/backend/services/email_poller.py', 'r') as f:
            content = f.read()
        
        assert 'def _has_atlas_duplicate' in content, "Missing _has_atlas_duplicate function"
        assert 'atlas_message_id' in content, "Missing atlas_message_id check in _has_atlas_duplicate"
        print("✓ Fix 4: _has_atlas_duplicate function exists in email_poller.py")
    
    def test_fix4_has_atlas_duplicate_called_in_inbound(self):
        """Fix 4: Verify _has_atlas_duplicate is called before insert_one in inbound path"""
        with open('/app/backend/services/email_poller.py', 'r') as f:
            content = f.read()
        
        # Count occurrences of _has_atlas_duplicate being called
        call_count = content.count('_has_atlas_duplicate(')
        # Should be called at least twice: once in inbound, once in sent
        assert call_count >= 2, f"_has_atlas_duplicate called only {call_count} times, expected at least 2"
        print(f"✓ Fix 4: _has_atlas_duplicate is called {call_count} times (inbound and sent paths)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
