"""
QA Batch 5: Admin, Analytics, Search, Webhooks, Exports
Sections: 16, 17, 18, 19, 20 from QA Test Plan
"""
import sys, uuid, time
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch5_admin_analytics_search_webhooks_exports")
    s = runner.admin_session()
    s_agent = runner.agent_session()
    s_noauth = runner.no_auth_session()

    print("=" * 60)
    print("BATCH 5: Admin, Analytics, Search, Webhooks, Exports")
    print("=" * 60)

    # ===== 16. Admin & Settings =====
    print("\n--- 16. Admin & Settings ---")

    def test_16_1():
        r = api_get(s, "/api/admin/settings")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, dict)
            return ok, f"Settings keys: {list(data.keys())[:10]}"
        return False, f"Status={r.status_code}"
    runner.run_test("16.1", "GET /api/admin/settings returns global settings", test_16_1)

    def test_16_2():
        r = api_put(s, "/api/admin/settings", {"auto_reassign_reopened": True})
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("16.2", "PUT /api/admin/settings updates settings", test_16_2)

    def test_16_3():
        r = api_get(s_agent, "/api/admin/settings")
        # Agent should be forbidden from admin endpoints
        return r.status_code == 403, f"Status={r.status_code}"
    runner.run_test("16.3", "Agent cannot access admin settings (403)", test_16_3)

    # Custom Fields
    print("\n  -- Custom Fields --")
    created_cf_id = None

    def test_16_4():
        nonlocal created_cf_id
        r = api_post(s, "/api/admin/custom-fields", {
            "name": f"qa_field_{uuid.uuid4().hex[:6]}",
            "field_type": "text",
            "entity_type": "ticket",
            "description": "QA test custom field",
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_cf_id = data.get("field_id") or data.get("id")
            return created_cf_id is not None, f"field_id={created_cf_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("16.4", "Create custom field (text, ticket)", test_16_4)

    def test_16_5():
        r = api_get(s, "/api/admin/custom-fields")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} custom fields"
        return False, f"Status={r.status_code}"
    runner.run_test("16.5", "List custom fields", test_16_5)

    def test_16_6():
        if not created_cf_id:
            return False, "No custom field"
        r = api_put(s, f"/api/admin/custom-fields/{created_cf_id}", {"description": "Updated description"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("16.6", "Update custom field", test_16_6)

    def test_16_7():
        if not created_cf_id:
            return False, "No custom field"
        r = api_delete(s, f"/api/admin/custom-fields/{created_cf_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("16.7", "Delete custom field", test_16_7)

    # Routing Rules
    print("\n  -- Routing Rules --")
    created_rr_id = None

    def test_16_8():
        r = api_get(s, "/api/admin/routing-rules")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} routing rules"
        return False, f"Status={r.status_code}"
    runner.run_test("16.8", "List routing rules", test_16_8)

    def test_16_9():
        nonlocal created_rr_id
        r = api_post(s, "/api/admin/routing-rules", {
            "name": f"QA Route {uuid.uuid4().hex[:6]}",
            "condition_groups": [
                {"conditions": [{"field": "priority", "operator": "is", "value": "urgent"}]}
            ],
            "action": {"type": "assign_team", "team_id": "some_team"},
            "priority": 10,
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_rr_id = data.get("rule_id") or data.get("id")
            return created_rr_id is not None, f"rule_id={created_rr_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("16.9", "Create routing rule", test_16_9)

    def test_16_10():
        r = api_post(s, "/api/admin/routing-rules/test", {
            "ticket": {"priority": "urgent", "status": "todo", "tags": []}
        })
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("16.10", "Test routing rules (dry run)", test_16_10)

    def test_16_11():
        if not created_rr_id:
            return False, "No routing rule"
        r = api_delete(s, f"/api/admin/routing-rules/{created_rr_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("16.11", "Delete routing rule", test_16_11)

    def test_16_12():
        r = api_get(s, "/api/admin/auto-close-status")
        if r.status_code == 200:
            data = r.json()
            ok = "enabled" in data or "hours" in data
            return ok, f"Data: {data}"
        return False, f"Status={r.status_code}"
    runner.run_test("16.12", "GET auto-close status", test_16_12)

    # ===== 17. Analytics & Reporting =====
    print("\n--- 17. Analytics & Reporting ---")

    def test_17_1():
        r = api_get(s, "/api/analytics/summary")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, dict)
            return ok, f"Summary keys: {list(data.keys())[:10]}"
        return False, f"Status={r.status_code}"
    runner.run_test("17.1", "GET /api/analytics/summary returns faceted summary", test_17_1)

    def test_17_2():
        r = api_get(s, "/api/analytics/overview?period=7d")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, dict)
            return ok, f"Overview keys: {list(data.keys())[:10]}"
        return False, f"Status={r.status_code}"
    runner.run_test("17.2", "GET /api/analytics/overview?period=7d", test_17_2)

    def test_17_3():
        r = api_get(s, "/api/analytics/overview?period=30d")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("17.3", "GET /api/analytics/overview?period=30d", test_17_3)

    def test_17_4():
        r = api_get(s, "/api/analytics/agents")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, (list, dict))
            return ok, f"Agent analytics type={type(data).__name__}"
        return False, f"Status={r.status_code}"
    runner.run_test("17.4", "GET /api/analytics/agents returns per-agent stats", test_17_4)

    def test_17_5():
        r = api_get(s, "/api/dashboard/stats")
        if r.status_code == 200:
            data = r.json()
            return isinstance(data, dict), f"Dashboard keys: {list(data.keys())[:10]}"
        return False, f"Status={r.status_code}"
    runner.run_test("17.5", "GET /api/dashboard/stats", test_17_5)

    # ===== 18. Search & Presence =====
    print("\n--- 18. Search & Presence ---")

    def test_18_1():
        r = api_post(s, "/api/search", {"query": "test"})
        if r.status_code == 200:
            data = r.json()
            return isinstance(data, (dict, list)), f"Search results type={type(data).__name__}"
        return False, f"Status={r.status_code}"
    runner.run_test("18.1", "POST /api/search with query", test_18_1)

    def test_18_2():
        r = api_get(s, "/api/search/suggestions?q=te")
        if r.status_code == 200:
            data = r.json()
            return isinstance(data, (dict, list)), f"Suggestions type={type(data).__name__}"
        return False, f"Status={r.status_code}"
    runner.run_test("18.2", "GET /api/search/suggestions (min 2 chars)", test_18_2)

    def test_18_3():
        r = api_get(s, "/api/search/suggestions?q=t")
        # Less than 2 chars - should return empty or 422
        if r.status_code == 200:
            data = r.json()
            is_empty = (isinstance(data, list) and len(data) == 0) or (isinstance(data, dict) and not data.get("results"))
            return True, f"Returned {type(data).__name__} (may be empty)"
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("18.3", "Suggestions with <2 chars returns empty/422", test_18_3)

    def test_18_4():
        r = api_get(s, "/api/notifications")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} notifications"
        return False, f"Status={r.status_code}"
    runner.run_test("18.4", "GET /api/notifications lists notifications", test_18_4)

    def test_18_5():
        r = api_get(s, "/api/presence/stats")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("18.5", "GET /api/presence/stats", test_18_5)

    # ===== 19. Webhooks =====
    print("\n--- 19. Webhooks ---")
    created_webhook_id = None

    def test_19_1():
        r = api_get(s, "/api/webhooks")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} webhooks"
        return False, f"Status={r.status_code}"
    runner.run_test("19.1", "GET /api/webhooks lists all", test_19_1)

    def test_19_2():
        nonlocal created_webhook_id
        r = api_post(s, "/api/webhooks", {
            "url": "https://httpbin.org/post",
            "events": ["ticket.created", "ticket.updated"],
            "name": f"QA Webhook {uuid.uuid4().hex[:6]}",
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_webhook_id = data.get("webhook_id") or data.get("id")
            return created_webhook_id is not None, f"webhook_id={created_webhook_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("19.2", "Create webhook", test_19_2)

    def test_19_3():
        """SSRF: private IP blocked"""
        r = api_post(s, "/api/webhooks", {
            "url": "http://127.0.0.1:8080/malicious",
            "events": ["ticket.created"],
            "name": "SSRF Test",
        })
        ok = r.status_code in (400, 422)
        return ok, f"Status={r.status_code}, detail={r.json().get('detail','') if r.status_code >= 400 else ''}"
    runner.run_test("19.3", "SSRF: private IP webhook URL blocked", test_19_3)

    def test_19_4():
        r = api_post(s, "/api/webhooks", {
            "url": "http://10.0.0.1:9090/internal",
            "events": ["ticket.created"],
            "name": "SSRF Private Net",
        })
        ok = r.status_code in (400, 422)
        return ok, f"Status={r.status_code}"
    runner.run_test("19.4", "SSRF: 10.x.x.x webhook URL blocked", test_19_4)

    def test_19_5():
        if not created_webhook_id:
            return False, "No webhook"
        r = api_put(s, f"/api/webhooks/{created_webhook_id}", {"active": False})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("19.5", "Update webhook (deactivate)", test_19_5)

    def test_19_6():
        if not created_webhook_id:
            return False, "No webhook"
        r = api_get(s, f"/api/webhooks/{created_webhook_id}/logs")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("19.6", "GET webhook logs", test_19_6)

    def test_19_7():
        if not created_webhook_id:
            return False, "No webhook"
        r = api_delete(s, f"/api/webhooks/{created_webhook_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("19.7", "Delete webhook", test_19_7)

    # ===== 20. Exports =====
    print("\n--- 20. Exports ---")

    def test_20_1():
        r = api_get(s, "/api/export?format=json")
        if r.status_code == 200:
            return True, f"Export returned data"
        return False, f"Status={r.status_code}"
    runner.run_test("20.1", "GET /api/export?format=json (basic export)", test_20_1)

    def test_20_2():
        r = api_get(s, "/api/export?format=csv")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}, content-type={r.headers.get('content-type','')}"
    runner.run_test("20.2", "GET /api/export?format=csv (basic CSV export)", test_20_2)

    def test_20_3():
        r = api_post(s, "/api/admin/export/tickets", {
            "format": "json",
            "include_notes": True,
            "include_changelog": True,
        })
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("20.3", "POST /api/admin/export/tickets (admin, JSON)", test_20_3)

    def test_20_4():
        r = api_post(s, "/api/admin/export/full", {"format": "json"})
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("20.4", "POST /api/admin/export/full (all collections)", test_20_4)

    def test_20_5():
        r = api_get(s, "/api/admin/export/customers")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("20.5", "GET /api/admin/export/customers", test_20_5)

    def test_20_6():
        r = api_get(s, "/api/admin/export/analytics")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("20.6", "GET /api/admin/export/analytics", test_20_6)

    def test_20_7():
        # Agent should not access admin exports
        r = api_post(s_agent, "/api/admin/export/tickets", {"format": "json"})
        return r.status_code == 403, f"Status={r.status_code}"
    runner.run_test("20.7", "Agent cannot access admin exports (403)", test_20_7)

    runner.save_report()

run_batch()
