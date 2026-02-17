"""
QA Batch 5: Admin, Analytics, Search, Webhooks, Exports (v2 - fixed)
"""
import sys, uuid
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch5_admin_analytics_search_webhooks_exports")
    s = runner.admin_session()
    s_agent = runner.agent_session()

    print("=" * 60)
    print("BATCH 5: Admin, Analytics, Search, Webhooks, Exports")
    print("=" * 60)

    # ===== 16. Admin =====
    print("\n--- 16. Admin & Settings ---")

    def test_16_1():
        r = api_get(s, "/api/admin/settings")
        return r.status_code == 200 and isinstance(r.json(), dict), f"Keys: {list(r.json().keys())[:5]}"
    runner.run_test("16.1", "GET /api/admin/settings", test_16_1)

    def test_16_2():
        return api_put(s, "/api/admin/settings", {"auto_reassign_reopened": True}).status_code == 200, "Updated"
    runner.run_test("16.2", "PUT /api/admin/settings", test_16_2)

    def test_16_3():
        """Verify admin/settings blocks agents"""
        r = api_get(s_agent, "/api/admin/settings")
        return r.status_code == 403, f"Status={r.status_code}"
    runner.run_test("16.3", "Agent blocked from /api/admin/settings (403)", test_16_3)

    # Custom Fields
    created_cf_id = None
    def test_16_4():
        nonlocal created_cf_id
        r = api_post(s, "/api/admin/custom-fields", {
            "name": f"qa_{uuid.uuid4().hex[:6]}", "field_type": "text",
            "entity_type": "ticket", "description": "QA field"})
        if r.status_code in (200, 201):
            created_cf_id = r.json().get("field_id") or r.json().get("id")
            return created_cf_id is not None, f"field_id={created_cf_id}"
        return False, f"Status={r.status_code}"
    runner.run_test("16.4", "Create custom field", test_16_4)

    def test_16_5():
        r = api_get(s, "/api/admin/custom-fields")
        return r.status_code == 200 and isinstance(r.json(), list), f"Found {len(r.json())}"
    runner.run_test("16.5", "List custom fields", test_16_5)

    def test_16_7():
        if not created_cf_id: return False, "No field"
        return api_delete(s, f"/api/admin/custom-fields/{created_cf_id}").status_code == 200, "Deleted"
    runner.run_test("16.7", "Delete custom field", test_16_7)

    # Routing Rules
    created_rr_id = None
    def test_16_8():
        return api_get(s, "/api/admin/routing-rules").status_code == 200, "OK"
    runner.run_test("16.8", "List routing rules", test_16_8)

    def test_16_9():
        nonlocal created_rr_id
        r = api_post(s, "/api/admin/routing-rules", {
            "name": f"QA-{uuid.uuid4().hex[:6]}",
            "condition_groups": [[{"field": "priority", "operator": "equals", "value": "urgent"}]],
            "actions": [{"type": "assign_team", "value": "some_team"}],
            "priority": 10, "is_active": True})
        if r.status_code in (200, 201):
            created_rr_id = r.json().get("rule_id") or r.json().get("id")
            return created_rr_id is not None, f"rule_id={created_rr_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("16.9", "Create routing rule", test_16_9)

    def test_16_10():
        r = api_post(s, "/api/admin/routing-rules/test", {"ticket": {"priority": "urgent", "status": "todo", "tags": []}})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("16.10", "Test routing (dry run)", test_16_10)

    def test_16_11():
        if not created_rr_id: return False, "No rule"
        return api_delete(s, f"/api/admin/routing-rules/{created_rr_id}").status_code == 200, "Deleted"
    runner.run_test("16.11", "Delete routing rule", test_16_11)

    def test_16_12():
        r = api_get(s, "/api/admin/auto-close-status")
        return r.status_code == 200 and "enabled" in r.json(), f"Data: {r.json()}"
    runner.run_test("16.12", "GET auto-close status", test_16_12)

    # ===== 17. Analytics =====
    print("\n--- 17. Analytics ---")

    def test_17_1():
        r = api_get(s, "/api/analytics/summary")
        return r.status_code == 200 and isinstance(r.json(), dict), f"Keys: {list(r.json().keys())[:5]}"
    runner.run_test("17.1", "GET /api/analytics/summary", test_17_1)

    def test_17_2():
        return api_get(s, "/api/analytics/overview?period=7d").status_code == 200, "OK"
    runner.run_test("17.2", "GET /api/analytics/overview?period=7d", test_17_2)

    def test_17_3():
        return api_get(s, "/api/analytics/overview?period=30d").status_code == 200, "OK"
    runner.run_test("17.3", "GET /api/analytics/overview?period=30d", test_17_3)

    def test_17_4():
        return api_get(s, "/api/analytics/agents").status_code == 200, "OK"
    runner.run_test("17.4", "GET /api/analytics/agents", test_17_4)

    # ===== 18. Search =====
    print("\n--- 18. Search & Presence ---")

    def test_18_1():
        return api_post(s, "/api/search", {"query": "test"}).status_code == 200, "OK"
    runner.run_test("18.1", "POST /api/search", test_18_1)

    def test_18_2():
        return api_get(s, "/api/search/suggestions?q=te").status_code == 200, "OK"
    runner.run_test("18.2", "GET suggestions (2+ chars)", test_18_2)

    def test_18_4():
        r = api_get(s, "/api/notifications")
        return r.status_code == 200 and isinstance(r.json(), list), f"Found {len(r.json())}"
    runner.run_test("18.4", "GET /api/notifications", test_18_4)

    def test_18_5():
        return api_get(s, "/api/presence/stats").status_code == 200, "OK"
    runner.run_test("18.5", "GET /api/presence/stats", test_18_5)

    # ===== 19. Webhooks =====
    print("\n--- 19. Webhooks ---")
    created_webhook_id = None

    def test_19_1():
        r = api_get(s, "/api/webhooks")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("19.1", "GET /api/webhooks", test_19_1)

    def test_19_2():
        nonlocal created_webhook_id
        r = api_post(s, "/api/webhooks", {
            "url": "https://httpbin.org/post", "events": ["ticket.created"],
            "name": f"QA-WH-{uuid.uuid4().hex[:6]}"})
        if r.status_code == 200:
            data = r.json()
            wh = data.get("webhook", {})
            created_webhook_id = wh.get("webhook_id")
            return created_webhook_id is not None, f"webhook_id={created_webhook_id}"
        return False, f"Status={r.status_code}"
    runner.run_test("19.2", "Create webhook", test_19_2)

    def test_19_3():
        r = api_post(s, "/api/webhooks", {"url": "http://127.0.0.1:8080/x", "events": ["ticket.created"], "name": "SSRF"})
        return r.status_code in (400, 422), f"Status={r.status_code}"
    runner.run_test("19.3", "SSRF: localhost blocked", test_19_3)

    def test_19_4():
        r = api_post(s, "/api/webhooks", {"url": "http://10.0.0.1:9090/x", "events": ["ticket.created"], "name": "SSRF2"})
        return r.status_code in (400, 422), f"Status={r.status_code}"
    runner.run_test("19.4", "SSRF: 10.x blocked", test_19_4)

    def test_19_5():
        if not created_webhook_id: return False, "No webhook"
        return api_put(s, f"/api/webhooks/{created_webhook_id}", {"is_active": False}).status_code == 200, "Deactivated"
    runner.run_test("19.5", "Deactivate webhook", test_19_5)

    def test_19_6():
        if not created_webhook_id: return False, "No webhook"
        return api_get(s, f"/api/webhooks/{created_webhook_id}/logs").status_code == 200, "OK"
    runner.run_test("19.6", "GET webhook logs", test_19_6)

    def test_19_7():
        if not created_webhook_id: return False, "No webhook"
        return api_delete(s, f"/api/webhooks/{created_webhook_id}").status_code == 200, "Deleted"
    runner.run_test("19.7", "Delete webhook", test_19_7)

    # ===== 20. Exports =====
    print("\n--- 20. Exports ---")

    def test_20_1():
        return api_get(s, "/api/export?format=json").status_code == 200, "OK"
    runner.run_test("20.1", "GET /api/export?format=json", test_20_1)

    def test_20_2():
        return api_get(s, "/api/export?format=csv").status_code == 200, "OK"
    runner.run_test("20.2", "GET /api/export?format=csv", test_20_2)

    def test_20_3():
        return api_post(s, "/api/admin/export/tickets", {"format": "json", "include_notes": True}).status_code == 200, "OK"
    runner.run_test("20.3", "POST /api/admin/export/tickets", test_20_3)

    def test_20_4():
        r = api_post(s, "/api/admin/export/full", {"format": "json"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("20.4", "POST /api/admin/export/full", test_20_4)

    def test_20_5():
        return api_get(s, "/api/admin/export/customers").status_code == 200, "OK"
    runner.run_test("20.5", "GET /api/admin/export/customers", test_20_5)

    def test_20_6():
        return api_get(s, "/api/admin/export/analytics").status_code == 200, "OK"
    runner.run_test("20.6", "GET /api/admin/export/analytics", test_20_6)

    def test_20_7():
        r = api_post(s_agent, "/api/admin/export/tickets", {"format": "json"})
        return r.status_code == 403, f"Status={r.status_code}"
    runner.run_test("20.7", "Agent blocked from /api/admin/export/tickets (403)", test_20_7)

    runner.save_report()

run_batch()
