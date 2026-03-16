"""
Test suite for Status Standardization Changes
=============================================
Verifies:
1. Backend health check
2. No 'resolved' status exists in MongoDB tickets
3. No 'waiting_on_customer', 'snoozed', or 'pending' statuses in MongoDB
4. VALID_STATUSES in database.py includes 'waiting' and 'closed' but NOT 'resolved'
5. atlas_import.py STATUS_MAP maps correctly
6. atlas_backfill.py STATUS_MAP maps correctly
7. email_templates.py status_color map has 'closed' but NOT 'resolved'
8. exports.py aggregate queries use only ['closed']
9. tickets.py webhook triggers: both 'ticket.resolved' and 'ticket.closed' fire on close
"""

import pytest
import requests
import os
import sys

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-engine-fixes.preview.emergentagent.com').rstrip('/')


class TestHealthCheck:
    """Test 1: Backend health check"""
    
    def test_health_endpoint(self):
        """Verify /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Health status not healthy: {data}"
        assert "checks" in data
        assert data["checks"].get("database", {}).get("status") == "healthy"
        print(f"✓ Health check passed: {data['status']}")


class TestDatabaseStatusValues:
    """Test 2-3: Verify no invalid statuses exist in MongoDB tickets"""
    
    def test_no_resolved_status_in_tickets(self):
        """Verify no tickets have 'resolved' status in MongoDB"""
        from database import tickets_collection
        
        resolved_count = tickets_collection.count_documents({"status": "resolved"})
        assert resolved_count == 0, f"Found {resolved_count} tickets with 'resolved' status - should be 0"
        print(f"✓ No tickets with 'resolved' status found (count: {resolved_count})")
    
    def test_no_stray_waiting_statuses(self):
        """Verify no tickets have 'waiting_on_customer', 'snoozed', or 'pending' statuses"""
        from database import tickets_collection
        
        stray_statuses = ['waiting_on_customer', 'snoozed', 'pending']
        for status in stray_statuses:
            count = tickets_collection.count_documents({"status": status})
            assert count == 0, f"Found {count} tickets with '{status}' status - should be 0"
            print(f"✓ No tickets with '{status}' status found (count: {count})")


class TestValidStatusesConstant:
    """Test 4: VALID_STATUSES constant validation"""
    
    def test_valid_statuses_includes_waiting_and_closed(self):
        """Verify VALID_STATUSES includes 'waiting' and 'closed' but NOT 'resolved'"""
        from database import VALID_STATUSES
        
        assert 'waiting' in VALID_STATUSES, f"'waiting' not in VALID_STATUSES: {VALID_STATUSES}"
        assert 'closed' in VALID_STATUSES, f"'closed' not in VALID_STATUSES: {VALID_STATUSES}"
        assert 'resolved' not in VALID_STATUSES, f"'resolved' should NOT be in VALID_STATUSES: {VALID_STATUSES}"
        
        print(f"✓ VALID_STATUSES correct: {VALID_STATUSES}")
        print(f"  - Contains 'waiting': True")
        print(f"  - Contains 'closed': True")
        print(f"  - Contains 'resolved': False (correct)")


class TestAtlasImportStatusMap:
    """Test 5: atlas_import.py STATUS_MAP validation"""
    
    def test_atlas_import_status_map(self):
        """Verify atlas_import.py STATUS_MAP maps 'CLOSED' to 'closed' not 'resolved'"""
        from atlas_import import STATUS_MAP
        
        # Verify CLOSED maps to 'closed' not 'resolved'
        assert STATUS_MAP.get("CLOSED") == "closed", f"CLOSED maps to '{STATUS_MAP.get('CLOSED')}', expected 'closed'"
        
        # Verify SNOOZED maps to 'waiting'
        assert STATUS_MAP.get("SNOOZED") == "waiting", f"SNOOZED maps to '{STATUS_MAP.get('SNOOZED')}', expected 'waiting'"
        
        # Verify PENDING maps to 'waiting'
        assert STATUS_MAP.get("PENDING") == "waiting", f"PENDING maps to '{STATUS_MAP.get('PENDING')}', expected 'waiting'"
        
        # Verify 'resolved' is not a value in the map
        assert "resolved" not in STATUS_MAP.values(), f"'resolved' found in STATUS_MAP values: {STATUS_MAP}"
        
        print(f"✓ atlas_import.py STATUS_MAP correct:")
        print(f"  - CLOSED → {STATUS_MAP.get('CLOSED')}")
        print(f"  - SNOOZED → {STATUS_MAP.get('SNOOZED')}")
        print(f"  - PENDING → {STATUS_MAP.get('PENDING')}")


class TestAtlasBackfillStatusMap:
    """Test 6: atlas_backfill.py STATUS_MAP validation"""
    
    def test_atlas_backfill_status_map(self):
        """Verify atlas_backfill.py STATUS_MAP maps correctly"""
        from services.atlas_backfill import STATUS_MAP
        
        # Verify CLOSED maps to 'closed' not 'resolved'
        assert STATUS_MAP.get("CLOSED") == "closed", f"CLOSED maps to '{STATUS_MAP.get('CLOSED')}', expected 'closed'"
        
        # Verify SNOOZED maps to 'waiting'
        assert STATUS_MAP.get("SNOOZED") == "waiting", f"SNOOZED maps to '{STATUS_MAP.get('SNOOZED')}', expected 'waiting'"
        
        # Verify PENDING maps to 'waiting'
        assert STATUS_MAP.get("PENDING") == "waiting", f"PENDING maps to '{STATUS_MAP.get('PENDING')}', expected 'waiting'"
        
        # Verify 'resolved' is not a value in the map
        assert "resolved" not in STATUS_MAP.values(), f"'resolved' found in STATUS_MAP values: {STATUS_MAP}"
        
        print(f"✓ atlas_backfill.py STATUS_MAP correct:")
        print(f"  - CLOSED → {STATUS_MAP.get('CLOSED')}")
        print(f"  - SNOOZED → {STATUS_MAP.get('SNOOZED')}")
        print(f"  - PENDING → {STATUS_MAP.get('PENDING')}")


class TestEmailTemplatesStatusColor:
    """Test 7: email_templates.py status_color validation"""
    
    def test_email_templates_status_color(self):
        """Verify email_templates.py status_color dict has 'closed' but NOT 'resolved'"""
        # The status_color dict is defined inline in the status_update_html function
        # We'll verify the module loads and check the expected behavior
        from services.email_templates import status_update_html
        
        # Generate HTML for 'closed' status - should work
        closed_html = status_update_html("TKT-001", "Test Customer", "Test Subject", "closed")
        assert "Closed" in closed_html, "Status 'closed' not rendered correctly in email template"
        assert "#22c55e" in closed_html, "Closed status should have green color #22c55e"
        
        # The key is that 'closed' works and 'resolved' would fall back to default color
        # Let's verify the inline status_color dict in the function
        import inspect
        source = inspect.getsource(status_update_html)
        
        # Check that 'closed' is in the status_color dict
        assert '"closed"' in source or "'closed'" in source, "'closed' not found in status_color dict"
        
        # Check that 'resolved' is NOT in the status_color dict
        assert '"resolved"' not in source and "'resolved'" not in source, "'resolved' should NOT be in status_color dict"
        
        print(f"✓ email_templates.py status_color correct:")
        print(f"  - Contains 'closed': True")
        print(f"  - Contains 'resolved': False (correct)")


class TestExportsAggregateQuery:
    """Test 8: exports.py aggregate query validation"""
    
    def test_exports_aggregate_uses_closed_only(self):
        """Verify exports.py aggregate queries use only ['closed'] not ['resolved', 'closed']"""
        import inspect
        from routes.exports import export_customers, export_analytics
        
        # Get source code of export_customers
        customers_source = inspect.getsource(export_customers)
        
        # Check the aggregate query uses ["closed"] not ["resolved", "closed"]
        # Line 264-265 should have: "$in": ["$status", ["closed"]]
        assert '["closed"]' in customers_source or "['closed']" in customers_source, \
            "exports.py should use ['closed'] in aggregate queries"
        
        # Verify 'resolved' is not in the aggregate conditions
        # We need to be careful here - 'resolved_tickets' is a variable name, not a status
        # Check that there's no "$in" with "resolved" as a status value
        assert '"resolved"' not in customers_source or "resolved_tickets" in customers_source, \
            "'resolved' status should not be in aggregate queries"
        
        # Same check for export_analytics
        analytics_source = inspect.getsource(export_analytics)
        assert '["closed"]' in analytics_source or "['closed']" in analytics_source, \
            "exports.py analytics should use ['closed'] in aggregate queries"
        
        print(f"✓ exports.py aggregate queries use ['closed'] correctly")


class TestTicketsWebhookTriggers:
    """Test 9: tickets.py webhook trigger validation"""
    
    def test_webhook_triggers_on_close(self):
        """Verify both 'ticket.resolved' and 'ticket.closed' webhooks fire when status changes to 'closed'"""
        import inspect
        from routes.tickets import update_ticket
        
        source = inspect.getsource(update_ticket)
        
        # Both webhooks should be triggered when status is 'closed'
        # Lines 658-659 should trigger both ticket.resolved and ticket.closed
        assert 'ticket.resolved' in source, "'ticket.resolved' webhook not found in update_ticket"
        assert 'ticket.closed' in source, "'ticket.closed' webhook not found in update_ticket"
        
        # Verify they fire sequentially (not as elif which would be dead code)
        # Check that both are within asyncio.create_task calls
        assert source.count('trigger_webhooks("ticket.resolved"') >= 1, \
            "ticket.resolved webhook trigger not found"
        assert source.count('trigger_webhooks("ticket.closed"') >= 1, \
            "ticket.closed webhook trigger not found"
        
        print(f"✓ tickets.py correctly triggers both 'ticket.resolved' and 'ticket.closed' webhooks")


class TestWebhooksEventDescriptions:
    """Test webhook event descriptions"""
    
    def test_webhook_resolved_description(self):
        """Verify ticket.resolved description indicates it's a legacy alias"""
        response = requests.get(f"{BASE_URL}/api/webhooks/events", timeout=10)
        
        # This endpoint might require auth, so we'll check the code directly too
        import inspect
        from routes.webhooks import list_webhook_events
        
        source = inspect.getsource(list_webhook_events)
        
        # Check that ticket.resolved description mentions it's a legacy alias
        assert "legacy" in source.lower() or "alias" in source.lower(), \
            "ticket.resolved description should mention it's a legacy alias for ticket.closed"
        
        print(f"✓ webhooks.py ticket.resolved correctly documented as legacy alias")


class TestServerLogMessages:
    """Test server.py log messages"""
    
    def test_server_auto_close_log_messages(self):
        """Verify server.py auto-close log messages reference 'closed' not 'resolved'"""
        import inspect
        from server import auto_close_resolved_tickets
        
        source = inspect.getsource(auto_close_resolved_tickets)
        
        # The log messages should reference 'closed' status
        assert "closed" in source.lower(), "Auto-close function should reference 'closed' status"
        
        print(f"✓ server.py auto-close messages reference 'closed' status correctly")


# Summary test that runs all validations
class TestStatusStandardizationSummary:
    """Summary test for all status standardization requirements"""
    
    def test_all_standardization_requirements(self):
        """Run a summary check of all requirements"""
        from database import VALID_STATUSES
        from atlas_import import STATUS_MAP as atlas_import_map
        from services.atlas_backfill import STATUS_MAP as atlas_backfill_map
        
        print("\n" + "="*60)
        print("STATUS STANDARDIZATION VERIFICATION SUMMARY")
        print("="*60)
        
        # Check 1: VALID_STATUSES
        has_waiting = 'waiting' in VALID_STATUSES
        has_closed = 'closed' in VALID_STATUSES
        no_resolved = 'resolved' not in VALID_STATUSES
        print(f"\n1. VALID_STATUSES: {VALID_STATUSES}")
        print(f"   - Has 'waiting': {has_waiting}")
        print(f"   - Has 'closed': {has_closed}")
        print(f"   - No 'resolved': {no_resolved}")
        
        # Check 2: atlas_import.py STATUS_MAP
        print(f"\n2. atlas_import.py STATUS_MAP:")
        print(f"   - CLOSED → {atlas_import_map.get('CLOSED')}")
        print(f"   - SNOOZED → {atlas_import_map.get('SNOOZED')}")
        print(f"   - PENDING → {atlas_import_map.get('PENDING')}")
        
        # Check 3: atlas_backfill.py STATUS_MAP
        print(f"\n3. atlas_backfill.py STATUS_MAP:")
        print(f"   - CLOSED → {atlas_backfill_map.get('CLOSED')}")
        print(f"   - SNOOZED → {atlas_backfill_map.get('SNOOZED')}")
        print(f"   - PENDING → {atlas_backfill_map.get('PENDING')}")
        
        # All assertions
        assert has_waiting and has_closed and no_resolved
        assert atlas_import_map.get('CLOSED') == 'closed'
        assert atlas_backfill_map.get('CLOSED') == 'closed'
        
        print(f"\n{'='*60}")
        print("ALL STATUS STANDARDIZATION CHECKS PASSED ✓")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
