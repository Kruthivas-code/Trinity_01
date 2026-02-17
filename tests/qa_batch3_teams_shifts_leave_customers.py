"""
QA Batch 3: Teams, Shifts, Leave, Customers
Sections: 7, 8, 9, 10 from QA Test Plan
"""
import sys, uuid, time
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch3_teams_shifts_leave_customers")
    s = runner.admin_session()
    s_agent = runner.agent_session()
    s_noauth = runner.no_auth_session()

    print("=" * 60)
    print("BATCH 3: Teams, Shifts, Leave, Customers")
    print("=" * 60)

    # ===== 7. Team Management =====
    print("\n--- 7. Team Management ---")
    created_team_id = None

    def test_7_1():
        r = api_get(s, "/api/teams")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} teams"
        return False, f"Status={r.status_code}"
    runner.run_test("7.1", "GET /api/teams lists all teams", test_7_1)

    def test_7_2():
        nonlocal created_team_id
        r = api_post(s, "/api/teams", {
            "name": f"QA Team {uuid.uuid4().hex[:6]}",
            "description": "QA test team",
            "escalation_level": "L1",
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_team_id = data.get("team_id") or data.get("id")
            ok = created_team_id is not None
            return ok, f"team_id={created_team_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("7.2", "Create team with name, description, escalation_level", test_7_2)

    def test_7_3():
        if not created_team_id:
            return False, "No team created"
        r = api_get(s, f"/api/teams/{created_team_id}")
        if r.status_code == 200:
            data = r.json()
            ok = data.get("escalation_level") == "L1"
            return ok, f"team={data.get('name')}, level={data.get('escalation_level')}"
        return False, f"Status={r.status_code}"
    runner.run_test("7.3", "GET single team by ID", test_7_3)

    def test_7_4():
        if not created_team_id:
            return False, "No team created"
        r = api_put(s, f"/api/teams/{created_team_id}", {"description": "Updated description"})
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("7.4", "Update team description", test_7_4)

    def test_7_5():
        if not created_team_id:
            return False, "No team created"
        r = api_post(s, f"/api/teams/{created_team_id}/members", {"user_id": "qa_agent_user"})
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("7.5", "Add member to team", test_7_5)

    def test_7_6():
        if not created_team_id:
            return False, "No team created"
        r = api_get(s, f"/api/teams/{created_team_id}/members")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} members"
        return False, f"Status={r.status_code}"
    runner.run_test("7.6", "List team members", test_7_6)

    def test_7_7():
        if not created_team_id:
            return False, "No team created"
        r = api_delete(s, f"/api/teams/{created_team_id}/members/qa_agent_user")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("7.7", "Remove member from team", test_7_7)

    def test_7_8():
        r = api_get(s, "/api/teams/nonexistent_team_id")
        return r.status_code == 404, f"Status={r.status_code}"
    runner.run_test("7.8", "Get non-existent team returns 404", test_7_8)

    def test_7_9():
        if not created_team_id:
            return False, "No team created"
        r = api_delete(s, f"/api/teams/{created_team_id}")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("7.9", "Delete team", test_7_9)

    # ===== 8. Shift Management =====
    print("\n--- 8. Shift Management ---")
    created_shift_id = None

    def test_8_1():
        r = api_get(s, "/api/shifts")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} shifts"
        return False, f"Status={r.status_code}"
    runner.run_test("8.1", "GET /api/shifts lists shifts", test_8_1)

    def test_8_2():
        nonlocal created_shift_id
        r = api_post(s, "/api/shifts", {
            "name": f"QA Shift {uuid.uuid4().hex[:6]}",
            "start_time": "09:00",
            "end_time": "17:00",
            "timezone": "Asia/Kolkata",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_shift_id = data.get("shift_id") or data.get("id")
            return created_shift_id is not None, f"shift_id={created_shift_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("8.2", "Create shift with schedule", test_8_2)

    def test_8_3():
        if not created_shift_id:
            return False, "No shift created"
        r = api_put(s, f"/api/shifts/{created_shift_id}", {"name": "QA Shift Updated"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("8.3", "Update shift", test_8_3)

    def test_8_4():
        r = api_get(s, "/api/user-shifts")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("8.4", "GET /api/user-shifts lists user shift assignments", test_8_4)

    def test_8_5():
        if not created_shift_id:
            return False, "No shift created"
        r = api_post(s, "/api/user-shifts", {
            "user_id": "qa_agent_user",
            "shift_id": created_shift_id,
        })
        ok = r.status_code in (200, 201)
        return ok, f"Status={r.status_code}"
    runner.run_test("8.5", "Assign user to shift", test_8_5)

    def test_8_6():
        r = api_get(s, "/api/shifts/status")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("8.6", "GET /api/shifts/status returns current shift statuses", test_8_6)

    # Cleanup shift
    if created_shift_id:
        try:
            api_delete(s, f"/api/shifts/{created_shift_id}")
        except:
            pass

    # ===== 9. Leave Management =====
    print("\n--- 9. Leave Management ---")
    created_leave_id = None

    def test_9_1():
        r = api_get(s, "/api/leaves")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, (list, dict))
            return ok, f"Response type={type(data).__name__}"
        return False, f"Status={r.status_code}"
    runner.run_test("9.1", "GET /api/leaves lists leaves", test_9_1)

    def test_9_2():
        nonlocal created_leave_id
        r = api_post(s, "/api/leaves", {
            "user_id": "qa_agent_user",
            "start_date": "2026-03-01",
            "end_date": "2026-03-03",
            "leave_type": "vacation",
            "reason": "QA test leave"
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_leave_id = data.get("leave_id") or data.get("id")
            return created_leave_id is not None, f"leave_id={created_leave_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("9.2", "Create leave request (auto-approved)", test_9_2)

    def test_9_3():
        if not created_leave_id:
            return False, "No leave created"
        r = api_get(s, f"/api/leaves/{created_leave_id}")
        if r.status_code == 200:
            data = r.json()
            ok = data.get("leave_type") == "vacation"
            return ok, f"leave_type={data.get('leave_type')}"
        return False, f"Status={r.status_code}"
    runner.run_test("9.3", "Get single leave by ID", test_9_3)

    def test_9_4():
        r = api_get(s, "/api/leaves/calendar")
        if r.status_code == 200:
            data = r.json()
            return isinstance(data, (list, dict)), f"Response type={type(data).__name__}"
        return False, f"Status={r.status_code}"
    runner.run_test("9.4", "GET /api/leaves/calendar returns leave calendar", test_9_4)

    def test_9_5():
        r = api_get(s, "/api/leaves/types")
        if r.status_code == 200:
            data = r.json()
            return isinstance(data, list), f"Found {len(data)} leave types"
        return False, f"Status={r.status_code}"
    runner.run_test("9.5", "GET /api/leaves/types returns leave types", test_9_5)

    def test_9_6():
        if not created_leave_id:
            return False, "No leave created"
        r = api_put(s, f"/api/leaves/{created_leave_id}", {"reason": "Updated QA reason"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("9.6", "Update leave request", test_9_6)

    def test_9_7():
        if not created_leave_id:
            return False, "No leave created"
        r = api_delete(s, f"/api/leaves/{created_leave_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("9.7", "Delete leave request", test_9_7)

    def test_9_8():
        r = api_get(s, "/api/leaves/summary?year=2026")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("9.8", "GET /api/leaves/summary returns summary by year", test_9_8)

    # ===== 10. Customer Management =====
    print("\n--- 10. Customer Management ---")
    created_customer_id = None

    def test_10_1():
        r = api_get(s, "/api/customers")
        if r.status_code == 200:
            data = r.json()
            ok = "customers" in data or isinstance(data, list)
            return ok, f"Response keys={list(data.keys()) if isinstance(data, dict) else f'list[{len(data)}]'}"
        return False, f"Status={r.status_code}"
    runner.run_test("10.1", "GET /api/customers lists customers", test_10_1)

    def test_10_2():
        nonlocal created_customer_id
        r = api_post(s, "/api/customers", {
            "email": f"qa_cust_{uuid.uuid4().hex[:6]}@example.com",
            "name": "QA Test Customer",
            "company": "QA Corp",
        })
        if r.status_code in (200, 201):
            data = r.json()
            created_customer_id = data.get("customer_id") or data.get("id")
            return created_customer_id is not None, f"customer_id={created_customer_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("10.2", "Create customer", test_10_2)

    def test_10_3():
        if not created_customer_id:
            return False, "No customer created"
        r = api_get(s, f"/api/customers/{created_customer_id}")
        if r.status_code == 200:
            data = r.json()
            return data.get("name") == "QA Test Customer", f"name={data.get('name')}"
        return False, f"Status={r.status_code}"
    runner.run_test("10.3", "Get single customer by ID", test_10_3)

    def test_10_4():
        if not created_customer_id:
            return False, "No customer created"
        r = api_put(s, f"/api/customers/{created_customer_id}", {"company": "Updated QA Corp"})
        if r.status_code == 200:
            data = r.json()
            return data.get("company") == "Updated QA Corp", f"company={data.get('company')}"
        return False, f"Status={r.status_code}"
    runner.run_test("10.4", "Update customer", test_10_4)

    def test_10_5():
        r = api_get(s, "/api/customers?search=QA Test")
        if r.status_code == 200:
            data = r.json()
            customers = data.get("customers", data) if isinstance(data, dict) else data
            return isinstance(customers, list), f"Found results"
        return False, f"Status={r.status_code}"
    runner.run_test("10.5", "Search customers", test_10_5)

    def test_10_6():
        if not created_customer_id:
            return False, "No customer created"
        r = api_get(s, f"/api/customers/{created_customer_id}/tickets")
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("10.6", "Get customer tickets", test_10_6)

    def test_10_7():
        if not created_customer_id:
            return False, "No customer created"
        r = api_delete(s, f"/api/customers/{created_customer_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("10.7", "Delete customer", test_10_7)

    def test_10_8():
        r = api_get(s, "/api/customers/nonexistent_id")
        return r.status_code == 404, f"Status={r.status_code}"
    runner.run_test("10.8", "Get non-existent customer returns 404", test_10_8)

    runner.save_report()

run_batch()
