"""
QA Batch 4: Filters, CSAT, Canned, Feature Requests, SLA (v2 - fixed)
"""
import sys, uuid
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch4_filters_csat_canned_features_sla")
    s = runner.admin_session()
    s_noauth = runner.no_auth_session()

    print("=" * 60)
    print("BATCH 4: Filters, CSAT, Canned, Feature Requests, SLA")
    print("=" * 60)

    # ===== 11. Filters =====
    print("\n--- 11. Filters & Custom Inboxes ---")
    created_inbox_id = None

    def test_11_1():
        r = api_get(s, "/api/filter/fields")
        return r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) > 0, f"Found {len(r.json())} fields"
    runner.run_test("11.1", "GET /api/filter/fields", test_11_1)

    def test_11_2():
        r = api_post(s, "/api/filter/tickets", {
            "filter_tree": {"op": "AND", "conditions": [{"field": "status", "op": "is", "value": "todo"}]}
        })
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("11.2", "POST /api/filter/tickets (simple condition)", test_11_2)

    def test_11_3():
        r = api_post(s, "/api/filter/tickets", {
            "filter_tree": {"op": "AND", "conditions": [
                {"field": "status", "op": "is", "value": "todo"},
                {"field": "priority", "op": "is", "value": "high"}]}})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("11.3", "Filter with AND group", test_11_3)

    def test_11_4():
        r = api_post(s, "/api/filter/tickets", {
            "filter_tree": {"op": "OR", "conditions": [
                {"field": "status", "op": "is", "value": "todo"},
                {"field": "status", "op": "is", "value": "in_progress"}]}})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("11.4", "Filter with OR group", test_11_4)

    def test_11_5():
        nonlocal created_inbox_id
        r = api_post(s, "/api/inboxes", {
            "name": f"QA-Inbox-{uuid.uuid4().hex[:6]}",
            "filter_tree": {"op": "AND", "conditions": [{"field": "status", "op": "is", "value": "todo"}]}})
        if r.status_code in (200, 201):
            created_inbox_id = r.json().get("inbox_id")
            return created_inbox_id is not None, f"inbox_id={created_inbox_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("11.5", "Create custom inbox", test_11_5)

    def test_11_6():
        r = api_get(s, "/api/inboxes")
        return r.status_code == 200 and isinstance(r.json(), list), f"Found {len(r.json())} inboxes"
    runner.run_test("11.6", "GET /api/inboxes", test_11_6)

    def test_11_7():
        if not created_inbox_id: return False, "No inbox"
        r = api_get(s, f"/api/inboxes/{created_inbox_id}/tickets")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("11.7", "GET inbox tickets", test_11_7)

    def test_11_8():
        if not created_inbox_id: return False, "No inbox"
        return api_put(s, f"/api/inboxes/{created_inbox_id}", {"name": "Updated"}).status_code == 200, "Updated"
    runner.run_test("11.8", "Update inbox", test_11_8)

    def test_11_9():
        if not created_inbox_id: return False, "No inbox"
        return api_post(s, f"/api/inboxes/{created_inbox_id}/share", {"user_ids": ["qa_agent_user"]}).status_code == 200, "Shared"
    runner.run_test("11.9", "Share inbox", test_11_9)

    def test_11_10():
        if not created_inbox_id: return False, "No inbox"
        return api_delete(s, f"/api/inboxes/{created_inbox_id}").status_code == 200, "Deleted"
    runner.run_test("11.10", "Delete inbox", test_11_10)

    # ===== 12. CSAT =====
    print("\n--- 12. CSAT ---")
    csat_ticket_id = None
    csat_token = None
    csat_response_id = None

    t = api_post(s, "/api/tickets", {"title": f"CSAT-{uuid.uuid4().hex[:8]}", "customer_email": f"csat_{uuid.uuid4().hex[:6]}@example.com"})
    if t.status_code in (200, 201): csat_ticket_id = t.json().get("ticket_id")

    def test_12_1():
        nonlocal csat_token
        if not csat_ticket_id: return False, "No ticket"
        r = api_post(s, f"/api/csat/send/{csat_ticket_id}")
        if r.status_code == 200:
            csat_token = r.json().get("token")
            return csat_token is not None, f"token={csat_token}"
        return False, f"Status={r.status_code}"
    runner.run_test("12.1", "Send CSAT survey", test_12_1)

    def test_12_2():
        if not csat_token: return False, "No token"
        r = api_get(s_noauth, f"/api/csat/check/{csat_token}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("12.2", "Check CSAT token (public)", test_12_2)

    def test_12_3():
        nonlocal csat_response_id
        if not csat_token: return False, "No token"
        r = api_post(s_noauth, f"/api/csat/rate/{csat_token}", {"rating": 5})
        if r.status_code == 200:
            csat_response_id = r.json().get("response_id") or r.json().get("id")
            return True, f"Rated 5 stars, response_id={csat_response_id}"
        return False, f"Status={r.status_code}"
    runner.run_test("12.3", "Rate CSAT (5 stars)", test_12_3)

    def test_12_4():
        if not csat_response_id: return False, "No response_id"
        r = api_post(s_noauth, f"/api/csat/{csat_response_id}/feedback", {"feedback": "Great!"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("12.4", "Submit CSAT feedback", test_12_4)

    def test_12_5():
        if not csat_ticket_id: return False, "No ticket"
        return api_get(s, f"/api/csat/ticket/{csat_ticket_id}").status_code == 200, "OK"
    runner.run_test("12.5", "Get CSAT for ticket", test_12_5)

    def test_12_6():
        r = api_get(s, "/api/csat/analytics")
        return r.status_code == 200 and isinstance(r.json(), dict), f"Keys={list(r.json().keys())[:5]}"
    runner.run_test("12.6", "GET /api/csat/analytics", test_12_6)

    def test_12_8():
        return api_get(s_noauth, "/api/csat/check/invalid_token").status_code in (400, 404), "Checked"
    runner.run_test("12.8", "Invalid CSAT token returns error", test_12_8)

    if csat_ticket_id: api_delete(s, f"/api/tickets/{csat_ticket_id}")

    # ===== 13. Canned Responses =====
    print("\n--- 13. Canned Responses ---")
    created_canned_id = None

    def test_13_1():
        r = api_get(s, "/api/canned-responses")
        if r.status_code == 200:
            data = r.json()
            # Response is {"global": [...], "personal": [...], "all": [...]}
            has_keys = isinstance(data, dict) and "all" in data
            return has_keys, f"Keys={list(data.keys()) if isinstance(data,dict) else type(data).__name__}"
        return False, f"Status={r.status_code}"
    runner.run_test("13.1", "GET /api/canned-responses", test_13_1)

    def test_13_2():
        nonlocal created_canned_id
        r = api_post(s, "/api/canned-responses", {
            "title": f"QA-{uuid.uuid4().hex[:6]}",
            "content": "Thank you for contacting us.",
            "shortcode": f"qa{uuid.uuid4().hex[:4]}"})  # no / prefix, alphanumeric only
        if r.status_code in (200, 201):
            created_canned_id = r.json().get("id") or r.json().get("response_id")
            return created_canned_id is not None, f"id={created_canned_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("13.2", "Create canned response", test_13_2)

    def test_13_3():
        if not created_canned_id: return False, "No response"
        return api_put(s, f"/api/canned-responses/{created_canned_id}", {"content": "Updated"}).status_code == 200, "Updated"
    runner.run_test("13.3", "Update canned response", test_13_3)

    def test_13_4():
        if not created_canned_id: return False, "No response"
        return api_delete(s, f"/api/canned-responses/{created_canned_id}").status_code == 200, "Deleted"
    runner.run_test("13.4", "Delete canned response", test_13_4)

    # ===== 14. Feature Requests =====
    print("\n--- 14. Feature Requests ---")
    created_fr_id = None

    def test_14_1():
        r = api_get(s, "/api/feature-requests")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("14.1", "GET /api/feature-requests", test_14_1)

    def test_14_2():
        nonlocal created_fr_id
        r = api_post(s, "/api/feature-requests", {
            "title": f"QA-FR-{uuid.uuid4().hex[:6]}", "description": "Test", "status": "open"})
        if r.status_code in (200, 201):
            created_fr_id = r.json().get("id") or r.json().get("feature_request_id")
            return created_fr_id is not None, f"id={created_fr_id}"
        return False, f"Status={r.status_code}"
    runner.run_test("14.2", "Create feature request", test_14_2)

    def test_14_3():
        if not created_fr_id: return False, "No FR"
        return api_get(s, f"/api/feature-requests/{created_fr_id}").status_code == 200, "OK"
    runner.run_test("14.3", "Get feature request", test_14_3)

    def test_14_5():
        if not created_fr_id: return False, "No FR"
        return api_post(s, f"/api/feature-requests/{created_fr_id}/vote").status_code == 200, "Voted"
    runner.run_test("14.5", "Vote on feature request", test_14_5)

    def test_14_6():
        if not created_fr_id: return False, "No FR"
        return api_delete(s, f"/api/feature-requests/{created_fr_id}").status_code == 200, "Deleted"
    runner.run_test("14.6", "Delete feature request", test_14_6)

    # ===== 15. SLA =====
    print("\n--- 15. SLA Policies & Escalation ---")

    def test_15_1():
        r = api_get(s, "/api/admin/sla-policies")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("15.1", "GET /api/admin/sla-policies", test_15_1)

    def test_15_3():
        r = api_get(s, "/api/admin/sla-escalation-rules")
        return r.status_code == 200 and isinstance(r.json(), list), f"Found {len(r.json())} rules"
    runner.run_test("15.3", "GET /api/admin/sla-escalation-rules", test_15_3)

    created_rule_id = None
    def test_15_4():
        nonlocal created_rule_id
        r = api_post(s, "/api/admin/sla-escalation-rules", {
            "name": f"QA-Rule-{uuid.uuid4().hex[:6]}",
            "trigger_type": "first_response_breach",
            "trigger_threshold": 100,
            "priority_filter": ["high", "urgent"],
            "actions": [{"type": "escalate", "value": "L2"}],
            "priority": 10, "is_active": True})
        if r.status_code in (200, 201):
            created_rule_id = r.json().get("rule_id") or r.json().get("id")
            return created_rule_id is not None, f"rule_id={created_rule_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("15.4", "Create escalation rule", test_15_4)

    def test_15_5():
        if not created_rule_id: return False, "No rule"
        return api_delete(s, f"/api/admin/sla-escalation-rules/{created_rule_id}").status_code == 200, "Deleted"
    runner.run_test("15.5", "Delete escalation rule", test_15_5)

    def test_15_6():
        t = api_post(s, "/api/tickets", {"title": f"SLA-{uuid.uuid4().hex[:8]}", "priority": "high"})
        if t.status_code not in (200, 201): return False, "No ticket"
        tid = t.json().get("ticket_id")
        r = api_get(s, f"/api/sla/ticket/{tid}")
        api_delete(s, f"/api/tickets/{tid}")
        # APP BUG: SLA ticket endpoint returns 500 server error
        return r.status_code == 200, f"Status={r.status_code} (APP BUG: 500 if failing)"
    runner.run_test("15.6", "GET /api/sla/ticket/:id", test_15_6)

    runner.save_report()

run_batch()
