"""
QA Batch 2: Ticket CRUD, Assignment, Operations, Notes, Tags (v2 - fixed)
"""
import sys, uuid, time
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch2_tickets")
    s = runner.admin_session()
    s_noauth = runner.no_auth_session()

    print("=" * 60)
    print("BATCH 2: Ticket CRUD, Assignment, Operations, Notes, Tags")
    print("=" * 60)

    created_ticket_ids = []

    # ===== 2.1 List Tickets =====
    print("\n--- 2.1 List Tickets ---")

    def test_2_1_1():
        r = api_get(s, "/api/tickets")
        if r.status_code == 200:
            data = r.json()
            return "tickets" in data and "total" in data, f"total={data.get('total')}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.1.1", "List tickets returns paginated list", test_2_1_1)

    def test_2_1_2():
        r = api_get(s, "/api/tickets?status=todo")
        if r.status_code == 200:
            data = r.json()
            all_todo = all(t.get("status") == "todo" for t in data.get("tickets", []))
            return all_todo, f"total={data.get('total')}, all_todo={all_todo}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.1.2", "Filter by status=todo", test_2_1_2)

    def test_2_1_9():
        r = api_get(s, "/api/tickets?page=1&limit=3")
        if r.status_code == 200:
            return len(r.json().get("tickets", [])) <= 3, f"Got {len(r.json().get('tickets',[]))} tickets"
        return False, f"Status={r.status_code}"
    runner.run_test("2.1.9", "Pagination: limit=3", test_2_1_9)

    def test_2_1_14():
        r = api_get(s, "/api/tickets?page=0")
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.1.14", "Invalid page=0 returns 422", test_2_1_14)

    def test_2_1_15():
        r = api_get(s, "/api/tickets?limit=201")
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.1.15", "Limit=201 returns 422", test_2_1_15)

    # ===== 2.2 Create Ticket =====
    print("\n--- 2.2 Create Ticket ---")

    def test_2_2_1():
        r = api_post(s, "/api/tickets", {"title": f"QA-{uuid.uuid4().hex[:8]}"})
        if r.status_code in (200, 201):
            tid = r.json().get("ticket_id")
            if tid: created_ticket_ids.append(tid)
            return tid and tid.startswith("TKT-"), f"ticket_id={tid}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.2.1", "Create ticket gets TKT-XXXXXX ID", test_2_2_1)

    def test_2_2_2():
        r = api_post(s, "/api/tickets", {
            "title": f"QA-Full-{uuid.uuid4().hex[:8]}",
            "description": "Full test", "status": "todo", "priority": "high",
            "tags": ["qa-test"], "customer_email": f"qa_{uuid.uuid4().hex[:6]}@example.com"})
        if r.status_code in (200, 201):
            d = r.json(); tid = d.get("ticket_id")
            if tid: created_ticket_ids.append(tid)
            return d.get("priority") == "high", f"priority={d.get('priority')}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.2.2", "Create with all fields", test_2_2_2)

    def test_2_2_3():
        return api_post(s, "/api/tickets", {"title": ""}).status_code == 422, "Checked"
    runner.run_test("2.2.3", "Empty title returns 422", test_2_2_3)

    def test_2_2_4():
        return api_post(s, "/api/tickets", {"title": "x" * 501}).status_code == 422, "Checked"
    runner.run_test("2.2.4", "Title >500 chars returns 422", test_2_2_4)

    def test_2_2_6():
        return api_post(s, "/api/tickets", {"title": "t", "status": "invalid"}).status_code == 422, "Checked"
    runner.run_test("2.2.6", "Invalid status returns 422", test_2_2_6)

    def test_2_2_7():
        return api_post(s, "/api/tickets", {"title": "t", "priority": "invalid"}).status_code == 422, "Checked"
    runner.run_test("2.2.7", "Invalid priority returns 422", test_2_2_7)

    def test_2_2_10():
        return api_post(s, "/api/tickets", {"title": "t", "tags": ["t"] * 51}).status_code == 422, "Checked"
    runner.run_test("2.2.10", "Tags >50 returns 422", test_2_2_10)

    def test_2_2_12():
        email = f"qa_link_{uuid.uuid4().hex[:6]}@example.com"
        r = api_post(s, "/api/tickets", {"title": f"Link-{uuid.uuid4().hex[:6]}", "customer_email": email})
        if r.status_code in (200, 201):
            tid = r.json().get("ticket_id"); created_ticket_ids.append(tid) if tid else None
            return r.json().get("customer_id") is not None, f"customer_id={r.json().get('customer_id')}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.2.12", "Customer email auto-creates customer", test_2_2_12)

    def test_2_2_19():
        r1 = api_post(s, "/api/tickets", {"title": f"SEQ1-{uuid.uuid4().hex[:8]}"})
        r2 = api_post(s, "/api/tickets", {"title": f"SEQ2-{uuid.uuid4().hex[:8]}"})
        if r1.status_code in (200,201) and r2.status_code in (200,201):
            id1, id2 = r1.json().get("ticket_id",""), r2.json().get("ticket_id","")
            created_ticket_ids.extend([id1, id2])
            try:
                n1, n2 = int(id1.split("-")[1]), int(id2.split("-")[1])
                return n2 == n1 + 1, f"{id1} -> {id2}, sequential={n2==n1+1}"
            except: return False, f"Parse error: {id1}, {id2}"
        return False, f"Status r1={r1.status_code}, r2={r2.status_code}"
    runner.run_test("2.2.19", "Sequential ticket IDs", test_2_2_19)

    # ===== 2.3 Get Ticket =====
    print("\n--- 2.3 Get Single Ticket ---")

    def test_2_3_1():
        if not created_ticket_ids: return False, "No tickets"
        r = api_get(s, f"/api/tickets/{created_ticket_ids[0]}")
        return r.status_code == 200, f"Got ticket {created_ticket_ids[0]}"
    runner.run_test("2.3.1", "Get valid ticket", test_2_3_1)

    def test_2_3_2():
        return api_get(s, "/api/tickets/TKT-999999").status_code == 404, "Checked"
    runner.run_test("2.3.2", "Non-existent ticket returns 404", test_2_3_2)

    # ===== 2.4 Update =====
    print("\n--- 2.4 Update Ticket ---")

    def test_2_4_1():
        if not created_ticket_ids: return False, "No tickets"
        r = api_put(s, f"/api/tickets/{created_ticket_ids[0]}", {"status": "in_progress"})
        return r.status_code == 200 and r.json().get("status") == "in_progress", f"status={r.json().get('status')}"
    runner.run_test("2.4.1", "Update status to in_progress", test_2_4_1)

    def test_2_4_3():
        if not created_ticket_ids: return False, "No tickets"
        r = api_put(s, f"/api/tickets/{created_ticket_ids[0]}", {"status": "resolved"})
        return r.status_code == 200 and r.json().get("resolved_at") is not None, f"resolved_at={r.json().get('resolved_at')}"
    runner.run_test("2.4.3", "Status=resolved sets resolved_at", test_2_4_3)

    def test_2_4_6():
        return api_put(s, "/api/tickets/TKT-999999", {"status": "todo"}).status_code == 404, "Checked"
    runner.run_test("2.4.6", "Update non-existent returns 404", test_2_4_6)

    def test_2_4_10():
        if not created_ticket_ids: return False, "No tickets"
        r = api_get(s, f"/api/tickets/{created_ticket_ids[0]}/changelog")
        return r.status_code == 200 and isinstance(r.json(), list), f"entries={len(r.json())}"
    runner.run_test("2.4.10", "Changelog entries exist", test_2_4_10)

    # ===== 2.5 Delete =====
    print("\n--- 2.5 Delete Ticket ---")

    def test_2_5_1():
        r = api_post(s, "/api/tickets", {"title": f"DEL-{uuid.uuid4().hex[:8]}"})
        tid = r.json().get("ticket_id")
        r2 = api_delete(s, f"/api/tickets/{tid}")
        r3 = api_get(s, f"/api/tickets/{tid}")
        return r2.status_code == 200 and r3.status_code == 404, f"del={r2.status_code}, get={r3.status_code}"
    runner.run_test("2.5.1", "Delete removes ticket", test_2_5_1)

    def test_2_5_2():
        return api_delete(s, "/api/tickets/TKT-999999").status_code == 404, "Checked"
    runner.run_test("2.5.2", "Delete non-existent returns 404", test_2_5_2)

    # ===== 3. Assignment =====
    print("\n--- 3. Ticket Assignment ---")

    def test_3_1():
        r = api_get(s, "/api/tickets/escalation-counts")
        return r.status_code == 200 and isinstance(r.json(), dict), f"counts={r.json()}"
    runner.run_test("3.1", "GET escalation-counts", test_3_1)

    # ===== 4. Operations =====
    print("\n--- 4. Ticket Operations ---")

    def test_4_1():
        r1 = api_post(s, "/api/tickets", {"title": f"M1-{uuid.uuid4().hex[:8]}"})
        r2 = api_post(s, "/api/tickets", {"title": f"M2-{uuid.uuid4().hex[:8]}"})
        t1, t2 = r1.json().get("ticket_id"), r2.json().get("ticket_id")
        created_ticket_ids.extend([t1, t2])
        # Merge t1 INTO t2 (t2 is target, t1 gets merged status)
        r = api_post(s, f"/api/tickets/{t1}/merge", {"target_ticket_id": t2})
        if r.status_code == 200:
            r3 = api_get(s, f"/api/tickets/{t1}")
            if r3.status_code == 200:
                return r3.json().get("status") == "merged", f"source_status={r3.json().get('status')}"
            return True, f"Merge succeeded, status={r.status_code}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("4.1", "Merge tickets", test_4_1)

    def test_4_2():
        if len(created_ticket_ids) < 2: return False, "Need 2 tickets"
        r = api_post(s, f"/api/tickets/{created_ticket_ids[0]}/link", {"target_ticket_id": created_ticket_ids[1], "link_type": "related"})
        return r.status_code == 200, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("4.2", "Link tickets", test_4_2)

    def test_4_3():
        if len(created_ticket_ids) < 2: return False, "Need 2 tickets"
        r = api_post(s, "/api/tickets/bulk-update", {"ticket_ids": created_ticket_ids[:2], "updates": {"priority": "urgent"}})
        return r.status_code == 200, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("4.3", "Bulk update tickets", test_4_3)

    # ===== 5. Notes & Activity =====
    print("\n--- 5. Notes & Activity ---")

    def test_5_1():
        if not created_ticket_ids: return False, "No tickets"
        r = api_post(s, f"/api/tickets/{created_ticket_ids[0]}/notes", {"content": "QA test note"})
        return r.status_code in (200, 201), f"Status={r.status_code}"
    runner.run_test("5.1", "Add internal note", test_5_1)

    def test_5_2():
        if not created_ticket_ids: return False, "No tickets"
        r = api_get(s, f"/api/tickets/{created_ticket_ids[0]}/notes")
        if r.status_code == 200:
            data = r.json()
            msgs = data.get("messages", []) if isinstance(data, dict) else data
            return len(msgs) >= 1, f"Found {len(msgs)} notes"
        return False, f"Status={r.status_code}"
    runner.run_test("5.2", "List internal notes", test_5_2)

    def test_5_3():
        if not created_ticket_ids: return False, "No tickets"
        r = api_get(s, f"/api/tickets/{created_ticket_ids[0]}/activity")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("5.3", "Get ticket activity", test_5_3)

    def test_5_4():
        if not created_ticket_ids: return False, "No tickets"
        r = api_get(s, f"/api/tickets/{created_ticket_ids[0]}/activity-feed")
        # APP BUG: activity-feed endpoint returns 500 server error
        return r.status_code == 200, f"Status={r.status_code} (APP BUG: 500 if failing)"
    runner.run_test("5.4", "Get ticket activity-feed", test_5_4)

    # ===== 6. Tags & Starred =====
    print("\n--- 6. Tags & Starred ---")

    def test_6_1():
        if not created_ticket_ids: return False, "No tickets"
        # Tags API expects a bare list, not an object
        r = s.post(f"{BASE_URL}/api/tickets/{created_ticket_ids[0]}/tags", json=["qa-tag"])
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("6.1", "Add tag to ticket", test_6_1)

    def test_6_2():
        if not created_ticket_ids: return False, "No tickets"
        r = api_put(s, f"/api/tickets/{created_ticket_ids[0]}", {"is_starred": True})
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("6.2", "Star a ticket", test_6_2)

    def test_6_3():
        r = api_get(s, "/api/tickets/starred")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("6.3", "GET /api/tickets/starred", test_6_3)

    # Cleanup
    for tid in created_ticket_ids:
        try: api_delete(s, f"/api/tickets/{tid}")
        except: pass

    runner.save_report()

run_batch()
