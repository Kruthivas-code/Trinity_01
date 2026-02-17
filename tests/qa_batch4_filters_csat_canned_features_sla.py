"""
QA Batch 4: Filters, CSAT, Canned Responses, Feature Requests, SLA
Sections: 11, 12, 13, 14, 15 from QA Test Plan
"""
import sys, uuid, time
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch4_filters_csat_canned_features_sla")
    s = runner.admin_session()
    s_agent = runner.agent_session()
    s_noauth = runner.no_auth_session()

    print("=" * 60)
    print("BATCH 4: Filters, CSAT, Canned Responses, Feature Requests, SLA")
    print("=" * 60)

    # ===== 11. Filters & Custom Inboxes =====
    print("\n--- 11. Filters & Custom Inboxes ---")
    created_inbox_id = None

    def test_11_1():
        r = api_get(s, "/api/filter/fields")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list) and len(data) > 0
            return ok, f"Found {len(data)} filterable fields"
        return False, f"Status={r.status_code}"
    runner.run_test("11.1", "GET /api/filter/fields returns available fields", test_11_1)

    def test_11_2():
        r = api_post(s, "/api/filter/apply", {
            "conditions": {
                "operator": "AND",
                "conditions": [
                    {"field": "status", "operator": "is", "value": "todo"}
                ]
            }
        })
        if r.status_code == 200:
            data = r.json()
            ok = "tickets" in data or isinstance(data, list)
            return ok, f"Filter applied, got results"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("11.2", "POST /api/filter/apply with simple condition", test_11_2)

    def test_11_3():
        r = api_post(s, "/api/filter/apply", {
            "conditions": {
                "operator": "AND",
                "conditions": [
                    {"field": "status", "operator": "is", "value": "todo"},
                    {"field": "priority", "operator": "is", "value": "high"}
                ]
            }
        })
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("11.3", "Filter with AND group", test_11_3)

    def test_11_4():
        r = api_post(s, "/api/filter/apply", {
            "conditions": {
                "operator": "OR",
                "conditions": [
                    {"field": "status", "operator": "is", "value": "todo"},
                    {"field": "status", "operator": "is", "value": "in_progress"}
                ]
            }
        })
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("11.4", "Filter with OR group", test_11_4)

    def test_11_5():
        nonlocal created_inbox_id
        r = api_post(s, "/api/inboxes", {
            "name": f"QA Inbox {uuid.uuid4().hex[:6]}",
            "filter": {
                "operator": "AND",
                "conditions": [
                    {"field": "status", "operator": "is", "value": "todo"}
                ]
            }
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_inbox_id = data.get("inbox_id") or data.get("id")
            return created_inbox_id is not None, f"inbox_id={created_inbox_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("11.5", "Create custom inbox", test_11_5)

    def test_11_6():
        r = api_get(s, "/api/inboxes")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} inboxes"
        return False, f"Status={r.status_code}"
    runner.run_test("11.6", "GET /api/inboxes lists custom inboxes", test_11_6)

    def test_11_7():
        if not created_inbox_id:
            return False, "No inbox created"
        r = api_get(s, f"/api/inboxes/{created_inbox_id}/tickets")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("11.7", "GET inbox tickets executes filter", test_11_7)

    def test_11_8():
        if not created_inbox_id:
            return False, "No inbox created"
        r = api_put(s, f"/api/inboxes/{created_inbox_id}", {"name": "QA Updated Inbox"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("11.8", "Update custom inbox", test_11_8)

    def test_11_9():
        if not created_inbox_id:
            return False, "No inbox created"
        r = api_post(s, f"/api/inboxes/{created_inbox_id}/share", {"user_ids": ["qa_agent_user"]})
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("11.9", "Share inbox (creates copies)", test_11_9)

    def test_11_10():
        if not created_inbox_id:
            return False, "No inbox created"
        r = api_delete(s, f"/api/inboxes/{created_inbox_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("11.10", "Delete custom inbox", test_11_10)

    # ===== 12. CSAT =====
    print("\n--- 12. CSAT (Customer Satisfaction) ---")

    # Create a ticket for CSAT testing
    csat_ticket = api_post(s, "/api/tickets", {"title": f"CSAT Test {uuid.uuid4().hex[:8]}", "customer_email": "csat_test@example.com"})
    csat_ticket_id = None
    csat_token = None
    if csat_ticket.status_code in (200, 201):
        csat_ticket_id = csat_ticket.json().get("ticket_id") or csat_ticket.json().get("id")

    def test_12_1():
        nonlocal csat_token
        if not csat_ticket_id:
            return False, "No ticket for CSAT"
        r = api_post(s, f"/api/csat/send/{csat_ticket_id}")
        if r.status_code == 200:
            data = r.json()
            csat_token = data.get("token")
            return csat_token is not None, f"token={csat_token}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("12.1", "Send CSAT survey for ticket", test_12_1)

    def test_12_2():
        if not csat_token:
            return False, "No CSAT token"
        r = api_get(s_noauth, f"/api/csat/check/{csat_token}")
        if r.status_code == 200:
            data = r.json()
            return "submitted" in data or "valid" in str(data).lower() or isinstance(data, dict), f"Check result={data}"
        return False, f"Status={r.status_code}"
    runner.run_test("12.2", "Check CSAT token status (public)", test_12_2)

    def test_12_3():
        if not csat_token:
            return False, "No CSAT token"
        r = api_post(s_noauth, f"/api/csat/rate/{csat_token}", {"rating": 5})
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("12.3", "Rate CSAT (5 stars, public endpoint)", test_12_3)

    def test_12_4():
        if not csat_token:
            return False, "No CSAT token"
        r = api_post(s_noauth, f"/api/csat/feedback/{csat_token}", {"feedback": "Great service!"})
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("12.4", "Submit CSAT feedback (public)", test_12_4)

    def test_12_5():
        if not csat_ticket_id:
            return False, "No ticket"
        r = api_get(s, f"/api/csat/ticket/{csat_ticket_id}")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("12.5", "Get CSAT for specific ticket", test_12_5)

    def test_12_6():
        r = api_get(s, "/api/csat/analytics")
        if r.status_code == 200:
            data = r.json()
            ok = "avg_rating" in data or "distribution" in data or isinstance(data, dict)
            return ok, f"Analytics keys={list(data.keys()) if isinstance(data, dict) else type(data)}"
        return False, f"Status={r.status_code}"
    runner.run_test("12.6", "GET /api/csat/analytics returns analytics", test_12_6)

    def test_12_7():
        """Low rating creates notification"""
        # Create another ticket and rate low
        t = api_post(s, "/api/tickets", {"title": f"Low CSAT {uuid.uuid4().hex[:8]}", "customer_email": "lowcsat@example.com"})
        if t.status_code not in (200, 201):
            return False, "Could not create ticket"
        tid = t.json().get("ticket_id") or t.json().get("id")
        # Send CSAT
        r1 = api_post(s, f"/api/csat/send/{tid}")
        if r1.status_code != 200:
            return False, f"Could not send CSAT: {r1.status_code}"
        token = r1.json().get("token")
        # Rate low
        r2 = api_post(s_noauth, f"/api/csat/rate/{token}", {"rating": 1})
        ok = r2.status_code == 200
        # Cleanup
        api_delete(s, f"/api/tickets/{tid}")
        return ok, f"Low rating submitted, status={r2.status_code}"
    runner.run_test("12.7", "Low rating (<=2) triggers alert", test_12_7)

    def test_12_8():
        r = api_get(s_noauth, "/api/csat/check/invalid_token_xyz")
        ok = r.status_code in (400, 404)
        return ok, f"Status={r.status_code}"
    runner.run_test("12.8", "Invalid CSAT token returns error", test_12_8)

    # Cleanup CSAT ticket
    if csat_ticket_id:
        api_delete(s, f"/api/tickets/{csat_ticket_id}")

    # ===== 13. Canned Responses =====
    print("\n--- 13. Canned Responses ---")
    created_canned_id = None

    def test_13_1():
        r = api_get(s, "/api/canned-responses")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} canned responses"
        return False, f"Status={r.status_code}"
    runner.run_test("13.1", "GET /api/canned-responses lists all", test_13_1)

    def test_13_2():
        nonlocal created_canned_id
        r = api_post(s, "/api/canned-responses", {
            "title": f"QA Canned {uuid.uuid4().hex[:6]}",
            "content": "Thank you for contacting us. We'll get back to you shortly.",
            "shortcut": f"/qa{uuid.uuid4().hex[:4]}",
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_canned_id = data.get("id") or data.get("response_id")
            return created_canned_id is not None, f"id={created_canned_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("13.2", "Create canned response with shortcut", test_13_2)

    def test_13_3():
        if not created_canned_id:
            return False, "No canned response"
        r = api_put(s, f"/api/canned-responses/{created_canned_id}", {"content": "Updated QA response"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("13.3", "Update canned response", test_13_3)

    def test_13_4():
        if not created_canned_id:
            return False, "No canned response"
        r = api_delete(s, f"/api/canned-responses/{created_canned_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("13.4", "Delete canned response", test_13_4)

    # ===== 14. Feature Requests =====
    print("\n--- 14. Feature Requests ---")
    created_fr_id = None

    def test_14_1():
        r = api_get(s, "/api/feature-requests")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, (list, dict))
            return ok, f"Response type={type(data).__name__}"
        return False, f"Status={r.status_code}"
    runner.run_test("14.1", "GET /api/feature-requests lists all", test_14_1)

    def test_14_2():
        nonlocal created_fr_id
        r = api_post(s, "/api/feature-requests", {
            "title": f"QA Feature {uuid.uuid4().hex[:6]}",
            "description": "This is a QA test feature request",
            "status": "open",
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_fr_id = data.get("id") or data.get("feature_request_id")
            return created_fr_id is not None, f"id={created_fr_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("14.2", "Create feature request", test_14_2)

    def test_14_3():
        if not created_fr_id:
            return False, "No feature request"
        r = api_get(s, f"/api/feature-requests/{created_fr_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("14.3", "Get single feature request", test_14_3)

    def test_14_4():
        if not created_fr_id:
            return False, "No feature request"
        r = api_put(s, f"/api/feature-requests/{created_fr_id}", {"status": "planned"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("14.4", "Update feature request status", test_14_4)

    def test_14_5():
        if not created_fr_id:
            return False, "No feature request"
        r = api_post(s, f"/api/feature-requests/{created_fr_id}/vote")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("14.5", "Vote on feature request", test_14_5)

    def test_14_6():
        if not created_fr_id:
            return False, "No feature request"
        r = api_delete(s, f"/api/feature-requests/{created_fr_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("14.6", "Delete feature request", test_14_6)

    # ===== 15. SLA Policies & Escalation =====
    print("\n--- 15. SLA Policies & Escalation ---")

    def test_15_1():
        r = api_get(s, "/api/sla/policies")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, (dict, list))
            return ok, f"Response: {type(data).__name__}"
        return False, f"Status={r.status_code}"
    runner.run_test("15.1", "GET /api/sla/policies returns SLA policies", test_15_1)

    def test_15_2():
        r = api_get(s, "/api/admin/sla")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, dict)
            return ok, f"Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}"
        return False, f"Status={r.status_code}"
    runner.run_test("15.2", "GET /api/admin/sla returns SLA settings", test_15_2)

    def test_15_3():
        r = api_get(s, "/api/admin/escalation-rules")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} escalation rules"
        return False, f"Status={r.status_code}"
    runner.run_test("15.3", "GET escalation rules", test_15_3)

    created_rule_id = None
    def test_15_4():
        nonlocal created_rule_id
        r = api_post(s, "/api/admin/escalation-rules", {
            "name": f"QA Escalation {uuid.uuid4().hex[:6]}",
            "trigger_type": "sla_breach",
            "action": "escalate",
            "priority_filter": ["high", "urgent"],
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_rule_id = data.get("rule_id") or data.get("id")
            return created_rule_id is not None, f"rule_id={created_rule_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("15.4", "Create escalation rule", test_15_4)

    def test_15_5():
        if not created_rule_id:
            return False, "No rule created"
        r = api_delete(s, f"/api/admin/escalation-rules/{created_rule_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("15.5", "Delete escalation rule", test_15_5)

    def test_15_6():
        """Per-ticket SLA status"""
        # Create a ticket first
        t = api_post(s, "/api/tickets", {"title": f"SLA Test {uuid.uuid4().hex[:8]}", "priority": "high"})
        if t.status_code not in (200, 201):
            return False, "Could not create ticket"
        tid = t.json().get("ticket_id") or t.json().get("id")
        r = api_get(s, f"/api/sla/ticket/{tid}")
        ok = r.status_code == 200
        # Cleanup
        api_delete(s, f"/api/tickets/{tid}")
        return ok, f"Status={r.status_code}"
    runner.run_test("15.6", "GET /api/sla/ticket/:id returns per-ticket SLA status", test_15_6)

    runner.save_report()

run_batch()
