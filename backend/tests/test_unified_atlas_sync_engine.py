"""
Test Suite: Unified Atlas Sync Engine (5-Layer Architecture)
=============================================================
Tests the unified atlas_sync.py engine including:
- Layer 1: Webhook handlers (POST /api/webhooks/atlas)
- Layer 2: Poller (safety net)
- Layer 3: Full crawl (historical reconciliation)
- Layer 4: Push-back (sync_ticket_to_atlas, sync_assignment_to_atlas)

Endpoints tested:
- /api/health - Backend health
- /api/webhooks/atlas - Webhook processing (POST, no auth)
- /api/webhooks/atlas/health - Webhook health (GET, no auth)
- /api/admin/atlas/sync/status - Sync engine status (GET, auth)
- /api/admin/atlas/sync/start - Start engine (POST, auth)
- /api/admin/atlas/sync/stop - Stop engine (POST, auth)
- /api/admin/atlas/sync/config - Update config (PATCH, auth)
- /api/admin/atlas/backfill/* - Legacy stubbed endpoints (auth)
- /api/admin/atlas/agents/import - Import Atlas agents (POST, auth)
- /api/admin/atlas/sync-health - Sync health audit (GET, auth)
- /api/admin/atlas/parity - Data parity stats (GET, auth)
- /api/admin/atlas/test - Atlas API connectivity (GET, auth)
- Push-back functions (Python import test)
- /api/tickets CRUD operations (auth)
"""

import pytest
import requests
import os
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://customer-support-app-2.preview.emergentagent.com').rstrip('/')


class TestHealthEndpoint:
    """Test backend health endpoint"""
    
    def test_health_returns_healthy(self):
        """GET /api/health should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Expected healthy, got {data.get('status')}"
        assert "timestamp" in data
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "healthy"


class TestWebhookEndpoints:
    """Test Atlas webhook endpoints (no auth required)"""
    
    def test_webhook_health(self):
        """GET /api/webhooks/atlas/health should return ok status"""
        response = requests.get(f"{BASE_URL}/api/webhooks/atlas/health", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "ok"
        assert data.get("service") == "trinity-atlas-webhook"
        assert "timestamp" in data
    
    def test_webhook_valid_json_returns_ok(self):
        """POST /api/webhooks/atlas with valid JSON should return {status: ok}"""
        payload = {
            "event": "conversation.created",
            "conversation": {"id": "test-conv-123", "number": 99999}
        }
        response = requests.post(
            f"{BASE_URL}/api/webhooks/atlas",
            json=payload,
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "ok"
    
    def test_webhook_invalid_json_returns_400(self):
        """POST /api/webhooks/atlas with invalid JSON should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/webhooks/atlas",
            data="invalid json",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 400
        
        data = response.json()
        assert data.get("status") == "error"
        assert "Invalid JSON" in data.get("message", "")
    
    def test_webhook_empty_body_returns_400(self):
        """POST /api/webhooks/atlas with empty body should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/webhooks/atlas",
            data="",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        # Empty body will fail JSON parsing
        assert response.status_code == 400


@pytest.fixture(scope="module")
def auth_session():
    """Create a test user and session for authenticated endpoints"""
    import subprocess
    import time
    
    timestamp = int(time.time() * 1000)
    user_id = f"test-unified-sync-{timestamp}"
    session_token = f"test_session_unified_{timestamp}"
    
    # Create user and session via mongosh
    script = f"""
    use('test_database');
    db.users.insertOne({{
      user_id: '{user_id}',
      email: 'test.unified.{timestamp}@example.com',
      name: 'Unified Sync Test User',
      role: 'admin',
      created_at: new Date()
    }});
    db.user_sessions.insertOne({{
      user_id: '{user_id}',
      session_token: '{session_token}',
      expires_at: new Date(Date.now() + 7*24*60*60*1000),
      created_at: new Date()
    }});
    """
    
    result = subprocess.run(
        ["mongosh", "--quiet", "--eval", script],
        capture_output=True,
        text=True
    )
    
    yield {
        "user_id": user_id,
        "session_token": session_token,
        "headers": {"Authorization": f"Bearer {session_token}"}
    }
    
    # Cleanup
    cleanup_script = f"""
    use('test_database');
    db.users.deleteOne({{ user_id: '{user_id}' }});
    db.user_sessions.deleteOne({{ session_token: '{session_token}' }});
    """
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True)


class TestSyncEndpoints:
    """Test /api/admin/atlas/sync/* endpoints (require auth)"""
    
    def test_sync_status_requires_auth(self):
        """GET /api/admin/atlas/sync/status without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/sync/status", timeout=10)
        assert response.status_code == 401
    
    def test_sync_status_with_auth(self, auth_session):
        """GET /api/admin/atlas/sync/status with auth returns engine status"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/sync/status",
            headers=auth_session["headers"],
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data  # 'running' or 'stopped'
        assert "is_running" in data
        assert "cycles_completed" in data
        assert "poll_interval" in data
        assert "lookback_minutes" in data
    
    def test_sync_start_requires_auth(self):
        """POST /api/admin/atlas/sync/start without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/admin/atlas/sync/start", timeout=10)
        assert response.status_code == 401
    
    def test_sync_start_with_auth(self, auth_session):
        """POST /api/admin/atlas/sync/start with auth starts or confirms running"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/sync/start",
            headers=auth_session["headers"],
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data or "status" in data
        # Could be "already running" or "started"
    
    def test_sync_stop_requires_auth(self):
        """POST /api/admin/atlas/sync/stop without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/admin/atlas/sync/stop", timeout=10)
        assert response.status_code == 401
    
    def test_sync_config_requires_auth(self):
        """PATCH /api/admin/atlas/sync/config without auth returns 401"""
        response = requests.patch(
            f"{BASE_URL}/api/admin/atlas/sync/config",
            json={"poll_interval": 60},
            timeout=10
        )
        assert response.status_code == 401
    
    def test_sync_config_with_auth(self, auth_session):
        """PATCH /api/admin/atlas/sync/config with auth updates config"""
        response = requests.patch(
            f"{BASE_URL}/api/admin/atlas/sync/config",
            headers=auth_session["headers"],
            json={"poll_interval": 60, "lookback_minutes": 15},
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("message") == "Config updated"
        assert "poll_interval" in data
        assert "lookback_minutes" in data


class TestLegacyBackfillEndpoints:
    """Test legacy backfill endpoints (should return completed/deprecated)"""
    
    def test_backfill_status_requires_auth(self):
        """GET /api/admin/atlas/backfill/status without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/backfill/status", timeout=10)
        assert response.status_code == 401
    
    def test_backfill_status_returns_completed(self, auth_session):
        """GET /api/admin/atlas/backfill/status returns completed status"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/backfill/status",
            headers=auth_session["headers"],
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "completed"
        assert "unified sync" in data.get("message", "").lower() or "backfill" in data.get("message", "").lower()
    
    def test_backfill_start_returns_completed(self, auth_session):
        """POST /api/admin/atlas/backfill/start returns completed (deprecated)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/backfill/start",
            headers=auth_session["headers"],
            json={},
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_backfill_stop_returns_completed(self, auth_session):
        """POST /api/admin/atlas/backfill/stop returns completed (deprecated)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/backfill/stop",
            headers=auth_session["headers"],
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_backfill_reset_returns_completed(self, auth_session):
        """POST /api/admin/atlas/backfill/reset returns completed (deprecated)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/backfill/reset",
            headers=auth_session["headers"],
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_backfill_test_returns_completed(self, auth_session):
        """POST /api/admin/atlas/backfill/test returns completed (deprecated)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/backfill/test",
            headers=auth_session["headers"],
            json={"count": 10},
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "completed"


class TestLegacyEnrichmentEndpoints:
    """Test legacy enrichment endpoints (should return completed)"""
    
    def test_enrich_start_returns_completed(self, auth_session):
        """POST /api/admin/atlas/backfill/enrich returns completed (deprecated)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/backfill/enrich",
            headers=auth_session["headers"],
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_enrich_status_returns_completed(self, auth_session):
        """GET /api/admin/atlas/backfill/enrich/status returns completed (deprecated)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/backfill/enrich/status",
            headers=auth_session["headers"],
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "completed"
    
    def test_enrich_stop_returns_completed(self, auth_session):
        """POST /api/admin/atlas/backfill/enrich/stop returns completed (deprecated)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/backfill/enrich/stop",
            headers=auth_session["headers"],
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "completed"


class TestAtlasAdminEndpoints:
    """Test other Atlas admin endpoints"""
    
    def test_agents_import_requires_auth(self):
        """POST /api/admin/atlas/agents/import without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/admin/atlas/agents/import", timeout=10)
        assert response.status_code == 401
    
    def test_agents_import_with_auth(self, auth_session):
        """POST /api/admin/atlas/agents/import works (may take time)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/agents/import",
            headers=auth_session["headers"],
            timeout=60  # Longer timeout for import
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should have import results
        assert "total_fetched" in data or "error" in data
    
    def test_sync_health_requires_auth(self):
        """GET /api/admin/atlas/sync-health without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/sync-health", timeout=10)
        assert response.status_code == 401
    
    def test_sync_health_with_auth(self, auth_session):
        """GET /api/admin/atlas/sync-health returns audit report"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/sync-health",
            headers=auth_session["headers"],
            timeout=30  # May take time for audit
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "grade" in data  # A, B, C, or F
        assert "overall_pct" in data
        assert "total_checked" in data
    
    def test_parity_requires_auth(self):
        """GET /api/admin/atlas/parity without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/parity", timeout=10)
        assert response.status_code == 401
    
    def test_parity_with_auth(self, auth_session):
        """GET /api/admin/atlas/parity returns linking stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/parity",
            headers=auth_session["headers"],
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "trinity_total" in data
        assert "atlas_linked" in data
        assert "parity_pct" in data
    
    def test_atlas_test_requires_auth(self):
        """GET /api/admin/atlas/test without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/test", timeout=10)
        assert response.status_code == 401
    
    def test_atlas_test_with_auth(self, auth_session):
        """GET /api/admin/atlas/test returns API connectivity check"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/test",
            headers=auth_session["headers"],
            timeout=15
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "connection" in data
        assert "key_set" in data


class TestPushBackFunctions:
    """Test that push-back functions are importable and callable"""
    
    def test_sync_functions_importable(self):
        """Verify sync_ticket_to_atlas and sync_assignment_to_atlas are importable"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.atlas_sync import sync_ticket_to_atlas, sync_assignment_to_atlas, sync_tags_to_atlas
        
        # Functions should be callable
        assert callable(sync_ticket_to_atlas)
        assert callable(sync_assignment_to_atlas)
        assert callable(sync_tags_to_atlas)
    
    def test_sync_ticket_to_atlas_returns_bool(self):
        """sync_ticket_to_atlas should return bool for non-existent ticket"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.atlas_sync import sync_ticket_to_atlas
        
        # Non-existent ticket should return False
        result = sync_ticket_to_atlas("NONEXISTENT-TICKET-12345", {"status": "closed"})
        assert isinstance(result, bool)
        assert result == False  # Ticket doesn't exist
    
    def test_sync_assignment_to_atlas_returns_bool(self):
        """sync_assignment_to_atlas should return bool for non-existent ticket"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.atlas_sync import sync_assignment_to_atlas
        
        # Non-existent ticket should return False
        result = sync_assignment_to_atlas("NONEXISTENT-TICKET-12345", "user_abc123")
        assert isinstance(result, bool)
        assert result == False  # Ticket doesn't exist


class TestTicketCRUD:
    """Test ticket CRUD operations still work with the refactored sync engine"""
    
    def test_get_tickets_requires_auth(self):
        """GET /api/tickets without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/tickets", timeout=10)
        assert response.status_code == 401
    
    def test_get_tickets_with_auth(self, auth_session):
        """GET /api/tickets with auth returns tickets list"""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            headers=auth_session["headers"],
            params={"limit": 5},
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        assert isinstance(data["tickets"], list)
    
    def test_create_ticket_requires_auth(self):
        """POST /api/tickets without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/tickets",
            json={"title": "Test", "description": "Test"},
            timeout=10
        )
        assert response.status_code == 401
    
    def test_ticket_crud_workflow(self, auth_session):
        """Test full ticket CRUD workflow"""
        # CREATE
        create_payload = {
            "title": "TEST_unified_sync_test_ticket",
            "description": "Testing ticket CRUD with unified sync engine",
            "priority": "medium",
            "status": "todo",
            "customer_email": "test.customer@example.com"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/tickets",
            headers=auth_session["headers"],
            json=create_payload,
            timeout=10
        )
        assert create_response.status_code == 200
        
        created_ticket = create_response.json()
        assert "ticket_id" in created_ticket
        ticket_id = created_ticket["ticket_id"]
        
        # READ
        get_response = requests.get(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            headers=auth_session["headers"],
            timeout=10
        )
        assert get_response.status_code == 200
        
        fetched_ticket = get_response.json()
        assert fetched_ticket["ticket_id"] == ticket_id
        assert fetched_ticket["title"] == create_payload["title"]
        
        # UPDATE
        update_payload = {"priority": "high"}
        update_response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            headers=auth_session["headers"],
            json=update_payload,
            timeout=10
        )
        assert update_response.status_code == 200
        
        updated_ticket = update_response.json()
        assert updated_ticket["priority"] == "high"
        
        # DELETE
        delete_response = requests.delete(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            headers=auth_session["headers"],
            timeout=10
        )
        assert delete_response.status_code == 200
        
        # Verify deleted
        verify_response = requests.get(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            headers=auth_session["headers"],
            timeout=10
        )
        assert verify_response.status_code == 404


class TestWebhookEventTypes:
    """Test various webhook event types are handled"""
    
    def test_conversation_created_event(self):
        """Test conversation.created event is handled"""
        payload = {
            "event": "conversation.created",
            "conversationId": "test-webhook-conv-123",
            "conversation": {
                "id": "test-webhook-conv-123",
                "number": 99998,
                "status": "OPEN",
                "priority": "MEDIUM"
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/webhooks/atlas",
            json=payload,
            timeout=10
        )
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
    
    def test_status_changed_event(self):
        """Test conversation.status_changed event is handled"""
        payload = {
            "event": "conversation.status_changed",
            "conversationId": "test-status-conv-123",
            "conversation": {
                "id": "test-status-conv-123",
                "status": "CLOSED"
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/webhooks/atlas",
            json=payload,
            timeout=10
        )
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
    
    def test_agent_changed_event(self):
        """Test conversation.agent_changed event is handled"""
        payload = {
            "event": "conversation.agent_changed",
            "conversationId": "test-agent-conv-123",
            "conversation": {
                "id": "test-agent-conv-123",
                "assignedAgent": {"id": "agent-123", "email": "agent@example.com"}
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/webhooks/atlas",
            json=payload,
            timeout=10
        )
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
    
    def test_new_message_event(self):
        """Test message.received event is handled"""
        payload = {
            "event": "message.received",
            "conversationId": "test-msg-conv-123",
            "message": {
                "id": "msg-123",
                "text": "Test message"
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/webhooks/atlas",
            json=payload,
            timeout=10
        )
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
    
    def test_unknown_event_type_handled(self):
        """Test unknown event type doesn't cause error"""
        payload = {
            "event": "some.unknown.event",
            "conversationId": "test-unknown-conv-123"
        }
        response = requests.post(
            f"{BASE_URL}/api/webhooks/atlas",
            json=payload,
            timeout=10
        )
        assert response.status_code == 200
        assert response.json().get("status") == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
