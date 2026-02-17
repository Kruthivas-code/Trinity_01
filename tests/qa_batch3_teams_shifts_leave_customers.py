"""
QA Batch 3: Teams, Shifts, Leave, Customers (v2 - fixed)
"""
import sys, uuid
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch3_teams_shifts_leave_customers")
    s = runner.admin_session()

    print("=" * 60)
    print("BATCH 3: Teams, Shifts, Leave, Customers")
    print("=" * 60)

    # ===== 7. Teams =====
    print("\n--- 7. Team Management ---")
    created_team_id = None

    def test_7_1():
        r = api_get(s, "/api/teams")
        return r.status_code == 200 and isinstance(r.json(), list), f"Found {len(r.json())} teams"
    runner.run_test("7.1", "GET /api/teams", test_7_1)

    def test_7_2():
        nonlocal created_team_id
        r = api_post(s, "/api/teams", {"name": f"QA-{uuid.uuid4().hex[:6]}", "description": "QA test", "escalation_level": "L1"})
        if r.status_code in (200, 201):
            created_team_id = r.json().get("team_id")
            return created_team_id is not None, f"team_id={created_team_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("7.2", "Create team", test_7_2)

    def test_7_3():
        if not created_team_id: return False, "No team"
        r = api_get(s, f"/api/teams/{created_team_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("7.3", "Get team by ID", test_7_3)

    def test_7_4():
        if not created_team_id: return False, "No team"
        r = api_put(s, f"/api/teams/{created_team_id}", {"description": "Updated"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("7.4", "Update team", test_7_4)

    def test_7_5():
        if not created_team_id: return False, "No team"
        r = api_post(s, f"/api/teams/{created_team_id}/members", {"user_id": "qa_agent_user"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("7.5", "Add member to team", test_7_5)

    def test_7_7():
        if not created_team_id: return False, "No team"
        r = api_delete(s, f"/api/teams/{created_team_id}/members/qa_agent_user")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("7.7", "Remove member from team", test_7_7)

    def test_7_8():
        return api_get(s, "/api/teams/nonexistent").status_code == 404, "Checked"
    runner.run_test("7.8", "Non-existent team returns 404", test_7_8)

    def test_7_9():
        if not created_team_id: return False, "No team"
        return api_delete(s, f"/api/teams/{created_team_id}").status_code == 200, "Deleted"
    runner.run_test("7.9", "Delete team", test_7_9)

    # ===== 8. Shifts =====
    print("\n--- 8. Shift Management ---")
    shift_team_id = None
    created_shift_id = None

    def test_8_1():
        r = api_get(s, "/api/shifts")
        return r.status_code == 200 and isinstance(r.json(), list), f"Found {len(r.json())} shifts"
    runner.run_test("8.1", "GET /api/shifts", test_8_1)

    def test_8_2():
        nonlocal shift_team_id, created_shift_id
        # Create a team first (shift requires team_id)
        tr = api_post(s, "/api/teams", {"name": f"Shift-Team-{uuid.uuid4().hex[:6]}", "escalation_level": "L1"})
        if tr.status_code not in (200, 201): return False, "Could not create team"
        shift_team_id = tr.json().get("team_id")
        r = api_post(s, "/api/shifts", {
            "name": f"QA-Shift-{uuid.uuid4().hex[:6]}", "start_time": "09:00", "end_time": "17:00",
            "timezone": "Asia/Kolkata", "days": ["monday","tuesday","wednesday","thursday","friday"],
            "team_id": shift_team_id})
        if r.status_code in (200, 201):
            created_shift_id = r.json().get("shift_id") or r.json().get("id")
            return created_shift_id is not None, f"shift_id={created_shift_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("8.2", "Create shift (with team_id)", test_8_2)

    def test_8_3():
        if not created_shift_id: return False, "No shift"
        r = api_put(s, f"/api/shifts/{created_shift_id}", {"name": "Updated Shift"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("8.3", "Update shift", test_8_3)

    # Cleanup
    if created_shift_id:
        try: api_delete(s, f"/api/shifts/{created_shift_id}")
        except: pass
    if shift_team_id:
        try: api_delete(s, f"/api/teams/{shift_team_id}")
        except: pass

    # ===== 9. Leave =====
    print("\n--- 9. Leave Management ---")
    created_leave_id = None

    def test_9_1():
        r = api_get(s, "/api/leaves")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("9.1", "GET /api/leaves", test_9_1)

    def test_9_2():
        nonlocal created_leave_id
        r = api_post(s, "/api/leaves", {
            "user_id": "qa_agent_user", "start_date": "2026-03-10", "end_date": "2026-03-12",
            "leave_type": "vacation", "reason": "QA test leave"})
        if r.status_code in (200, 201):
            created_leave_id = r.json().get("leave_id") or r.json().get("id")
            return created_leave_id is not None, f"leave_id={created_leave_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("9.2", "Create leave request", test_9_2)

    def test_9_3():
        if not created_leave_id: return False, "No leave"
        r = api_get(s, f"/api/leaves/{created_leave_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("9.3", "Get leave by ID", test_9_3)

    def test_9_6():
        if not created_leave_id: return False, "No leave"
        r = api_put(s, f"/api/leaves/{created_leave_id}", {"reason": "Updated"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("9.6", "Update leave", test_9_6)

    def test_9_7():
        if not created_leave_id: return False, "No leave"
        return api_delete(s, f"/api/leaves/{created_leave_id}").status_code == 200, "Deleted"
    runner.run_test("9.7", "Delete leave", test_9_7)

    # ===== 10. Customers =====
    print("\n--- 10. Customer Management ---")
    created_customer_id = None

    def test_10_1():
        r = api_get(s, "/api/customers")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("10.1", "GET /api/customers", test_10_1)

    def test_10_2():
        nonlocal created_customer_id
        r = api_post(s, "/api/customers", {
            "primary_email": f"qa_{uuid.uuid4().hex[:6]}@testcorp.com",
            "name": "QA Customer"})
        if r.status_code in (200, 201):
            created_customer_id = r.json().get("customer_id")
            return created_customer_id is not None, f"customer_id={created_customer_id}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("10.2", "Create customer (primary_email)", test_10_2)

    def test_10_3():
        if not created_customer_id: return False, "No customer"
        r = api_get(s, f"/api/customers/{created_customer_id}")
        return r.status_code == 200, f"name={r.json().get('name')}"
    runner.run_test("10.3", "Get customer by ID", test_10_3)

    def test_10_4():
        if not created_customer_id: return False, "No customer"
        r = api_put(s, f"/api/customers/{created_customer_id}", {"name": "Updated QA"})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("10.4", "Update customer", test_10_4)

    def test_10_5():
        r = api_get(s, "/api/customers?search=QA")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("10.5", "Search customers", test_10_5)

    def test_10_6():
        r = api_get(s, "/api/customers/b2b-prospects")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("10.6", "GET /api/customers/b2b-prospects", test_10_6)

    def test_10_8():
        return api_get(s, "/api/customers/nonexistent").status_code == 404, "Checked"
    runner.run_test("10.8", "Non-existent customer returns 404", test_10_8)

    runner.save_report()

run_batch()
