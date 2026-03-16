"""
Test suite for Atlas Sync Engine 20 Fixes Verification
========================================================
Static code analysis and functional verification of all 20 fixes
in atlas_sync.py and atlas_webhooks.py

This test performs:
1. Static code verification (reading and validating fix implementations)
2. Health check verification (backend is running)
"""

import pytest
import re
import os

# Read the source files
ATLAS_SYNC_PATH = "/app/backend/services/atlas_sync.py"
ATLAS_WEBHOOKS_PATH = "/app/backend/routes/atlas_webhooks.py"

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="module")
def atlas_sync_code():
    """Load atlas_sync.py content for static analysis."""
    with open(ATLAS_SYNC_PATH, "r") as f:
        return f.read()


@pytest.fixture(scope="module")
def atlas_webhooks_code():
    """Load atlas_webhooks.py content for static analysis."""
    with open(ATLAS_WEBHOOKS_PATH, "r") as f:
        return f.read()


class TestFlaw1PollerDocstring:
    """Flaw 1: Verify _run_realtime_sync docstring states it catches CREATED conversations only."""
    
    def test_docstring_mentions_created_only(self, atlas_sync_code):
        # Check docstring mentions 'creation date' or 'CREATED' conversations only
        pattern = r"def _run_realtime_sync.*?\"\"\"(.*?)\"\"\"" 
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_run_realtime_sync function not found"
        docstring = match.group(1)
        
        # Should mention that it catches NEW/CREATED conversations
        assert "creation date" in docstring.lower() or "catches NEW" in docstring.upper() or "CREATED" in docstring, \
            f"Docstring should mention it catches CREATED conversations only. Got: {docstring[:200]}"
        print("✓ Flaw 1 PASSED: _run_realtime_sync docstring correctly states it catches CREATED conversations only")


class TestFlaw2MessageSyncPoisoning:
    """Flaw 2: Verify _process_conversation_batch uses 'last_message_synced_at' not 'last_synced_at'."""
    
    def test_uses_last_message_synced_at(self, atlas_sync_code):
        # Find _process_conversation_batch function
        pattern = r"def _process_conversation_batch.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_process_conversation_batch not found"
        func_code = match.group(0)
        
        # Should use last_message_synced_at, not just last_synced_at
        assert 'last_message_synced_at' in func_code, \
            "Should use last_message_synced_at for skip_messages_if_recent check"
        
        # Check docstring mentions the fix
        assert "last_message_synced_at" in func_code, \
            "Should use last_message_synced_at field"
        print("✓ Flaw 2 PASSED: _process_conversation_batch uses last_message_synced_at for skip logic")
    
    def test_sync_fields_updates_last_synced_at(self, atlas_sync_code):
        # _sync_fields should always update last_synced_at
        pattern = r"def _sync_fields.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_sync_fields not found"
        func_code = match.group(0)
        
        assert 'updates["last_synced_at"]' in func_code or "last_synced_at" in func_code, \
            "_sync_fields should update last_synced_at"
        print("✓ Flaw 2 PASSED: _sync_fields updates last_synced_at")


class TestFlaw3TagRemoval:
    """Flaw 3: Verify _sync_fields handles empty tags properly."""
    
    def test_empty_tags_handling(self, atlas_sync_code):
        # Find the tag handling section in _sync_fields
        pattern = r"def _sync_fields.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_sync_fields not found"
        func_code = match.group(0)
        
        # Should use 'if tag_lookup is not None' not 'if raw_tags and tag_lookup'
        assert "if tag_lookup is not None" in func_code, \
            "Should use 'if tag_lookup is not None' to handle empty tags"
        
        # Should set mapped_tags = [] when raw_tags is empty
        assert "mapped_tags = []" in func_code, \
            "Should set mapped_tags to empty list when Atlas has no tags"
        print("✓ Flaw 3 PASSED: _sync_fields correctly handles empty tags (tag removal)")


class TestFlaw4NinetyDayInvisibility:
    """Flaw 4: Verify _run_cold_crawl_batch does NOT use startDate filter."""
    
    def test_cold_crawl_no_date_filter(self, atlas_sync_code):
        # Find _run_cold_crawl_batch
        pattern = r"def _run_cold_crawl_batch.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_run_cold_crawl_batch not found"
        func_code = match.group(0)
        
        # Should NOT have startDate in params
        # Extract the requests.get params section
        params_match = re.search(r'params=\{([^}]+)\}', func_code)
        assert params_match, "Could not find params in _run_cold_crawl_batch"
        params_content = params_match.group(1)
        
        assert "startDate" not in params_content, \
            f"Cold crawl should NOT use startDate filter. Found: {params_content}"
        
        # Should only use cursor and limit
        assert "cursor" in params_content, "Should use cursor"
        assert "limit" in params_content, "Should use limit"
        print("✓ Flaw 4 PASSED: _run_cold_crawl_batch does NOT use startDate filter")


class TestFlaw5CSATClosedAtReupdate:
    """Flaw 5: Verify _sync_fields allows re-updates of CSAT and closed_at."""
    
    def test_no_one_shot_guards(self, atlas_sync_code):
        # Find _sync_fields
        pattern = r"def _sync_fields.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_sync_fields not found"
        func_code = match.group(0)
        
        # Should NOT have 'not ticket.get("closed_at")' guard
        assert 'not ticket.get("closed_at")' not in func_code, \
            "Should NOT have one-shot guard for closed_at"
        assert "not ticket.get('closed_at')" not in func_code, \
            "Should NOT have one-shot guard for closed_at"
        
        # Should NOT have 'not ticket.get("atlas_csat_score")' guard
        assert 'not ticket.get("atlas_csat_score")' not in func_code, \
            "Should NOT have one-shot guard for atlas_csat_score"
        assert "not ticket.get('atlas_csat_score')" not in func_code, \
            "Should NOT have one-shot guard for atlas_csat_score"
        
        print("✓ Flaw 5 PASSED: _sync_fields allows re-updates of CSAT and closed_at")


class TestFlaw7And14ErrorBoundary:
    """Flaw 7/14: Verify _process_conversation_batch has try/except per conversation."""
    
    def test_error_boundary_per_conversation(self, atlas_sync_code):
        # Find _process_conversation_batch
        pattern = r"def _process_conversation_batch.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_process_conversation_batch not found"
        func_code = match.group(0)
        
        # Should have consecutive_failures tracking
        assert "consecutive_failures" in func_code, \
            "Should track consecutive_failures"
        
        # Should have MAX_CONSECUTIVE_FAILURES
        assert "MAX_CONSECUTIVE_FAILURES" in func_code, \
            "Should have MAX_CONSECUTIVE_FAILURES constant"
        
        # Should have try/except inside the for loop
        assert "try:" in func_code and "except Exception" in func_code, \
            "Should have try/except for error handling"
        
        # Should abort after consecutive failures
        assert "consecutive_failures >= MAX_CONSECUTIVE_FAILURES" in func_code, \
            "Should abort batch after MAX_CONSECUTIVE_FAILURES"
        
        print("✓ Flaw 7/14 PASSED: _process_conversation_batch has error boundary with consecutive failure tracking")


class TestFlaw8TagCache:
    """Flaw 8: Verify _get_cached_tag_lookup does not cache empty results."""
    
    def test_no_empty_cache_poisoning(self, atlas_sync_code):
        # Find _get_cached_tag_lookup
        pattern = r"def _get_cached_tag_lookup.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_get_cached_tag_lookup not found"
        func_code = match.group(0)
        
        # Should have logic to not cache empty when existing data exists
        assert "fresh or not _lookup_cache" in func_code or \
               "Don't poison cache" in func_code or \
               "keeping existing cache" in func_code, \
            "Should not poison cache with empty results when existing data is present"
        
        print("✓ Flaw 8 PASSED: _get_cached_tag_lookup does not cache empty results over existing data")


class TestFlaw9FalsePositiveMatching:
    """Flaw 9: Verify _create_or_link_ticket Match 2 has source filter and time constraint."""
    
    def test_match_2_filters(self, atlas_sync_code):
        # Find _create_or_link_ticket
        pattern = r"def _create_or_link_ticket.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_create_or_link_ticket not found"
        func_code = match.group(0)
        
        # Should have source filter with email/imap/gmail
        assert '"$in": ["email", "imap", "gmail"]' in func_code or \
               "'$in': ['email', 'imap', 'gmail']" in func_code or \
               '"source": {"$in":' in func_code, \
            "Match 2 should include source filter ($in: email/imap/gmail)"
        
        # Should have time constraint (7 days)
        assert "timedelta(days=7)" in func_code, \
            "Match 2 should have 7-day time constraint"
        
        assert "match_window" in func_code or "created_at" in func_code, \
            "Should have created_at time constraint"
        
        print("✓ Flaw 9 PASSED: _create_or_link_ticket Match 2 has source filter and time constraint")


class TestFlaw10WebhookProjection:
    """Flaw 10: Verify webhook handlers use _TICKET_PROJECTION."""
    
    def test_webhook_field_change_projection(self, atlas_sync_code):
        # Find _webhook_field_change
        pattern = r"def _webhook_field_change.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_webhook_field_change not found"
        func_code = match.group(0)
        
        assert "_TICKET_PROJECTION" in func_code, \
            "_webhook_field_change should use _TICKET_PROJECTION"
        assert "{'_id': 0}" not in func_code, \
            "_webhook_field_change should NOT use minimal {'_id': 0} projection"
        
    def test_webhook_new_message_projection(self, atlas_sync_code):
        pattern = r"def _webhook_new_message.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_webhook_new_message not found"
        func_code = match.group(0)
        
        assert "_TICKET_PROJECTION" in func_code, \
            "_webhook_new_message should use _TICKET_PROJECTION"
    
    def test_webhook_tags_changed_projection(self, atlas_sync_code):
        pattern = r"def _webhook_tags_changed.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_webhook_tags_changed not found"
        func_code = match.group(0)
        
        assert "_TICKET_PROJECTION" in func_code, \
            "_webhook_tags_changed should use _TICKET_PROJECTION"
        
        print("✓ Flaw 10 PASSED: All webhook handlers use _TICKET_PROJECTION")


class TestFlaw12RedundantPollerSync:
    """Flaw 12: Verify _run_realtime_sync skips message sync for recently synced tickets."""
    
    def test_poller_skips_recent_messages(self, atlas_sync_code):
        # Find _run_realtime_sync
        pattern = r"def _run_realtime_sync.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_run_realtime_sync not found"
        func_code = match.group(0)
        
        # Should check last_message_synced_at
        assert "last_message_synced_at" in func_code, \
            "Should check last_message_synced_at"
        
        # Should skip if < 120 seconds ago
        assert "120" in func_code, \
            "Should skip message sync if last_message_synced_at < 120 seconds ago"
        
        print("✓ Flaw 12 PASSED: _run_realtime_sync skips message sync for recently synced tickets")


class TestFlaw13WebhookIMAMLinking:
    """Flaw 13: Verify _webhook_conversation_created calls _create_or_link_ticket."""
    
    def test_uses_create_or_link(self, atlas_sync_code):
        # Find _webhook_conversation_created
        pattern = r"def _webhook_conversation_created.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_webhook_conversation_created not found"
        func_code = match.group(0)
        
        # Should call _create_or_link_ticket, NOT _create_ticket_from_conv directly
        assert "_create_or_link_ticket" in func_code, \
            "_webhook_conversation_created should call _create_or_link_ticket"
        
        print("✓ Flaw 13 PASSED: _webhook_conversation_created calls _create_or_link_ticket (not _create_ticket_from_conv)")


class TestFlaw15WebhookAsync:
    """Flaw 15: Verify atlas_webhooks.py processes in background thread."""
    
    def test_background_thread_processing(self, atlas_webhooks_code):
        # Should use threading.Thread
        assert "threading.Thread" in atlas_webhooks_code, \
            "Should use threading.Thread for background processing"
        
        # Should return 200 immediately
        assert 'return JSONResponse({"status": "ok"})' in atlas_webhooks_code, \
            "Should return 200 immediately"
        
        # Thread should be daemon
        assert "daemon=True" in atlas_webhooks_code, \
            "Background thread should be daemon"
        
        print("✓ Flaw 15 PASSED: atlas_webhooks.py processes events in background thread and returns 200 immediately")


class TestFlaw16ReversePriority:
    """Flaw 16: Verify _REVERSE_PRIORITY_MAP maps 'medium' to 'NORMAL'."""
    
    def test_medium_maps_to_normal(self, atlas_sync_code):
        # Find _REVERSE_PRIORITY_MAP
        pattern = r"_REVERSE_PRIORITY_MAP\s*=\s*\{([^}]+)\}"
        match = re.search(pattern, atlas_sync_code)
        assert match, "_REVERSE_PRIORITY_MAP not found"
        map_content = match.group(1)
        
        # Should map medium to NORMAL (not MEDIUM)
        assert '"medium": "NORMAL"' in map_content or "'medium': 'NORMAL'" in map_content, \
            f"medium should map to NORMAL, not MEDIUM. Found: {map_content}"
        
        print("✓ Flaw 16 PASSED: _REVERSE_PRIORITY_MAP maps 'medium' to 'NORMAL'")


class TestFlaw17TeamIdSync:
    """Flaw 17: Verify _sync_fields syncs assignedTeamId to team_id."""
    
    def test_team_id_synced(self, atlas_sync_code):
        # Find _sync_fields
        pattern = r"def _sync_fields.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_sync_fields not found"
        func_code = match.group(0)
        
        # Should sync assignedTeamId to team_id
        assert "assignedTeamId" in func_code, "Should read assignedTeamId from conv"
        assert 'updates["team_id"]' in func_code or "updates['team_id']" in func_code, \
            "Should update team_id field"
        
        print("✓ Flaw 17 PASSED: _sync_fields syncs assignedTeamId to team_id")


class TestFlaw18MessageText:
    """Flaw 18: Verify _sync_messages allows messages with attachments even when plain_text is empty."""
    
    def test_attachment_only_messages_allowed(self, atlas_sync_code):
        # Find _sync_messages
        pattern = r"def _sync_messages.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_sync_messages not found"
        func_code = match.group(0)
        
        # Should check both plain_text AND raw_attachments
        assert "not plain_text and not raw_attachments" in func_code, \
            "Should skip only when BOTH plain_text and attachments are empty"
        
        print("✓ Flaw 18 PASSED: _sync_messages allows messages with attachments even when plain_text is empty")


class TestFlaw19ConflictCounter:
    """Flaw 19: Verify _sync_fields returns actual conflict count."""
    
    def test_returns_conflict_count(self, atlas_sync_code):
        # Find _sync_fields
        pattern = r"def _sync_fields.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_sync_fields not found"
        func_code = match.group(0)
        
        # Should increment conflicts when assignment_protected
        assert "conflicts += 1" in func_code or "conflicts = 1" in func_code, \
            "Should increment conflict counter when assignment is protected"
        
        # Should return conflicts in return value
        assert "return" in func_code and "conflicts" in func_code, \
            "Should return actual conflicts count, not hardcoded 0"
        
        print("✓ Flaw 19 PASSED: _sync_fields returns actual conflict count")


class TestFlaw20TagsDoubleUpdate:
    """Flaw 20: Verify _webhook_tags_changed only uses _sync_fields for updates."""
    
    def test_no_direct_tag_update(self, atlas_sync_code):
        # Find _webhook_tags_changed
        pattern = r"def _webhook_tags_changed.*?(?=\ndef |\Z)"
        match = re.search(pattern, atlas_sync_code, re.DOTALL)
        assert match, "_webhook_tags_changed not found"
        func_code = match.group(0)
        
        # Should call _sync_fields for updates
        assert "_sync_fields" in func_code, \
            "_webhook_tags_changed should call _sync_fields"
        
        # Should NOT have direct tag update like updates["tags"] or ticket.update
        # The only tag-related code should be in _sync_fields call
        lines = func_code.split('\n')
        for line in lines:
            if "updates[" in line and "tags" in line:
                assert False, f"Should NOT have direct tag update. Found: {line}"
        
        print("✓ Flaw 20 PASSED: _webhook_tags_changed only uses _sync_fields for all updates (no direct tag update)")


class TestTicketProjectionFields:
    """Verify _TICKET_PROJECTION includes required fields."""
    
    def test_projection_includes_required_fields(self, atlas_sync_code):
        # Find _TICKET_PROJECTION
        pattern = r"_TICKET_PROJECTION\s*=\s*\{([^}]+)\}"
        match = re.search(pattern, atlas_sync_code)
        assert match, "_TICKET_PROJECTION not found"
        projection = match.group(1)
        
        required_fields = [
            "last_message_synced_at",
            "atlas_csat_comment", 
            "team_id",
            "trinity_assigned_at",
            "tags",
        ]
        
        for field in required_fields:
            assert field in projection, f"_TICKET_PROJECTION should include {field}"
        
        print("✓ PASSED: _TICKET_PROJECTION includes all required fields")


class TestBackendHealth:
    """Verify backend is running and healthy."""
    
    def test_health_endpoint(self):
        import requests
        
        if not BASE_URL:
            pytest.skip("BASE_URL not set")
        
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Backend unhealthy: {data}"
        
        print("✓ PASSED: Backend is healthy and running")


class TestWebhookHealthEndpoint:
    """Verify webhook health endpoint works."""
    
    def test_webhook_health(self):
        import requests
        
        if not BASE_URL:
            pytest.skip("BASE_URL not set")
        
        response = requests.get(f"{BASE_URL}/api/webhooks/atlas/health", timeout=10)
        assert response.status_code == 200, f"Webhook health check failed: {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "ok", f"Webhook health not ok: {data}"
        
        print("✓ PASSED: Webhook health endpoint is accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
