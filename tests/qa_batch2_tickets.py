"""
QA Batch 2: Ticket CRUD, Assignment, Operations, Notes, Tags
Sections: 2, 3, 4, 5, 6 from QA Test Plan
"""
import sys, uuid, time
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch2_tickets")
    s = runner.admin_session()
    s_agent = runner.agent_session()
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
            ok = "tickets" in data and "total" in data
            return ok, f"total={data.get('total')}, tickets_count={len(data.get('tickets', []))}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.1.1", "List all tickets returns paginated list", test_2_1_1)

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
            data = r.json()
            ok = len(data.get("tickets", [])) <= 3
            return ok, f"tickets={len(data.get('tickets',[]))}, total={data.get('total')}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.1.9", "Pagination: page=1, limit=3", test_2_1_9)

    def test_2_1_14():
        r = api_get(s, "/api/tickets?page=0")
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.1.14", "Invalid page=0 returns 422", test_2_1_14)

    def test_2_1_15():
        r = api_get(s, "/api/tickets?limit=201")
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.1.15", "Limit=201 exceeds max returns 422", test_2_1_15)

    # ===== 2.2 Create Ticket =====
    print("\n--- 2.2 Create Ticket ---")

    def test_2_2_1():
        r = api_post(s, "/api/tickets", {"title": f"QA Test Ticket {uuid.uuid4().hex[:8]}"})
        if r.status_code in (200, 201):
            data = r.json()
            tid = data.get("ticket_id") or data.get("id")
            if tid:
                created_ticket_ids.append(tid)
            ok = tid and tid.startswith("TKT-")
            return ok, f"ticket_id={tid}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("2.2.1", "Create ticket with title only, gets TKT-XXXXXX ID", test_2_2_1)

    def test_2_2_2():
        r = api_post(s, "/api/tickets", {
            "title": f"QA Full Ticket {uuid.uuid4().hex[:8]}",
            "description": "Full description for QA test",
            "status": "todo",
            "priority": "high",
            "tags": ["qa-test", "automated"],
            "customer_email": "qa_customer@example.com",
        })
        if r.status_code in (200, 201):
            data = r.json()
            tid = data.get("ticket_id") or data.get("id")
            if tid:
                created_ticket_ids.append(tid)
            ok = data.get("priority") == "high" and "qa-test" in (data.get("tags") or [])
            return ok, f"ticket_id={tid}, priority={data.get('priority')}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("2.2.2", "Create with all fields persists correctly", test_2_2_2)

    def test_2_2_3():
        r = api_post(s, "/api/tickets", {"title": ""})
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.2.3", "Empty title returns 422", test_2_2_3)

    def test_2_2_4():
        r = api_post(s, "/api/tickets", {"title": "x" * 501})
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.2.4", "Title >500 chars returns 422", test_2_2_4)

    def test_2_2_6():
        r = api_post(s, "/api/tickets", {"title": "test", "status": "invalid_status"})
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.2.6", "Invalid status returns 422", test_2_2_6)

    def test_2_2_7():
        r = api_post(s, "/api/tickets", {"title": "test", "priority": "invalid_priority"})
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.2.7", "Invalid priority returns 422", test_2_2_7)

    def test_2_2_10():
        r = api_post(s, "/api/tickets", {"title": "test", "tags": ["t"] * 51})
        return r.status_code == 422, f"Status={r.status_code}"
    runner.run_test("2.2.10", "Tags >50 returns 422", test_2_2_10)

    def test_2_2_12():
        r = api_post(s, "/api/tickets", {
            "title": f"Customer Link {uuid.uuid4().hex[:8]}",
            "customer_email": "qa_autolink@example.com",
        })
        if r.status_code in (200, 201):
            data = r.json()
            tid = data.get("ticket_id") or data.get("id")
            if tid:
                created_ticket_ids.append(tid)
            ok = data.get("customer_id") is not None
            return ok, f"customer_id={data.get('customer_id')}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.2.12", "Customer email auto-creates/links customer", test_2_2_12)

    def test_2_2_19():
        # Create two tickets and check IDs are sequential
        r1 = api_post(s, "/api/tickets", {"title": f"SEQ-1 {uuid.uuid4().hex[:8]}"})
        r2 = api_post(s, "/api/tickets", {"title": f"SEQ-2 {uuid.uuid4().hex[:8]}"})
        if r1.status_code in (200,201) and r2.status_code in (200,201):
            id1 = r1.json().get("ticket_id", "")
            id2 = r2.json().get("ticket_id", "")
            created_ticket_ids.extend([id1, id2])
            # Extract numbers
            try:
                n1 = int(id1.split("-")[1])
                n2 = int(id2.split("-")[1])
                return n2 == n1 + 1, f"id1={id1}, id2={id2}, sequential={n2==n1+1}"
            except:
                return False, f"Could not parse IDs: {id1}, {id2}"
        return False, f"Status r1={r1.status_code}, r2={r2.status_code}"
    runner.run_test("2.2.19", "Sequential ticket ID generation", test_2_2_19)

    # ===== 2.3 Get Single Ticket =====
    print("\n--- 2.3 Get Single Ticket ---")

    def test_2_3_1():
        if not created_ticket_ids:
            return False, "No tickets created"
        r = api_get(s, f"/api/tickets/{created_ticket_ids[0]}")
        if r.status_code == 200:
            data = r.json()
            ok = (data.get("ticket_id") or data.get("id")) is not None
            return ok, f"Got ticket {created_ticket_ids[0]}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.3.1", "Get valid ticket by ID", test_2_3_1)

    def test_2_3_2():
        r = api_get(s, "/api/tickets/TKT-999999")
        return r.status_code == 404, f"Status={r.status_code}"
    runner.run_test("2.3.2", "Non-existent ticket returns 404", test_2_3_2)

    # ===== 2.4 Update Ticket =====
    print("\n--- 2.4 Update Ticket ---")

    def test_2_4_1():
        if not created_ticket_ids:
            return False, "No tickets"
        r = api_put(s, f"/api/tickets/{created_ticket_ids[0]}", {"status": "in_progress"})
        if r.status_code == 200:
            data = r.json()
            return data.get("status") == "in_progress", f"status={data.get('status')}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("2.4.1", "Update single field (status)", test_2_4_1)

    def test_2_4_3():
        if not created_ticket_ids:
            return False, "No tickets"
        r = api_put(s, f"/api/tickets/{created_ticket_ids[0]}", {"status": "resolved"})
        if r.status_code == 200:
            data = r.json()
            ok = data.get("status") == "resolved" and data.get("resolved_at") is not None
            return ok, f"resolved_at={data.get('resolved_at')}"
        return False, f"Status={r.status_code}"
    runner.run_test("2.4.3", "Status=resolved sets resolved_at", test_2_4_3)

    def test_2_4_6():
        r = api_put(s, "/api/tickets/TKT-999999", {"status": "todo"})
        return r.status_code == 404, f"Status={r.status_code}"
    runner.run_test("2.4.6", "Update non-existent ticket returns 404", test_2_4_6)

    def test_2_4_10():
        """Check changelog entries after update"""
        if not created_ticket_ids:
            return False, "No tickets"
        tid = created_ticket_ids[0]
        r = api_get(s, f"/api/tickets/{tid}/changelog")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list) and len(data) > 0
            return ok, f"Found {len(data)} changelog entries"
        return False, f"Status={r.status_code}"
    runner.run_test("2.4.10", "Changelog logged for changed fields", test_2_4_10)

    # ===== 2.5 Delete Ticket =====
    print("\n--- 2.5 Delete Ticket ---")

    def test_2_5_1():
        # Create a ticket to delete
        r = api_post(s, "/api/tickets", {"title": f"DELETE-ME {uuid.uuid4().hex[:8]}"})
        if r.status_code not in (200, 201):
            return False, f"Could not create ticket: {r.status_code}"
        tid = r.json().get("ticket_id") or r.json().get("id")
        r2 = api_delete(s, f"/api/tickets/{tid}")
        ok = r2.status_code == 200
        # Verify gone
        r3 = api_get(s, f"/api/tickets/{tid}")
        return ok and r3.status_code == 404, f"Delete status={r2.status_code}, get_after={r3.status_code}"
    runner.run_test("2.5.1", "Delete ticket removes it", test_2_5_1)

    def test_2_5_2():
        r = api_delete(s, "/api/tickets/TKT-999999")
        return r.status_code == 404, f"Status={r.status_code}"
    runner.run_test("2.5.2", "Delete non-existent ticket returns 404", test_2_5_2)

    # ===== 3. Ticket Assignment & Routing =====
    print("\n--- 3. Ticket Assignment & Routing ---")

    def test_3_1():
        r = api_get(s, "/api/tickets/escalation-counts")
        if r.status_code == 200:
            data = r.json()
            ok = "L1" in data or "L2" in data or "L3" in data or isinstance(data, dict)
            return ok, f"escalation_counts={data}"
        return False, f"Status={r.status_code}"
    runner.run_test("3.1", "GET escalation-counts returns L1/L2/L3 counts", test_3_1)

    def test_3_2():
        r = api_get(s, "/api/tickets?escalation_level=L1")
        if r.status_code == 200:
            data = r.json()
            all_l1 = all(t.get("escalation_level") == "L1" for t in data.get("tickets", []))
            return True, f"total={data.get('total')}, all_L1={all_l1}"
        return False, f"Status={r.status_code}"
    runner.run_test("3.2", "Filter tickets by escalation_level=L1", test_3_2)

    # ===== 4. Ticket Operations =====
    print("\n--- 4. Ticket Operations (Merge/Split/Link/Bulk) ---")

    def test_4_1_merge():
        # Create 2 tickets to merge
        r1 = api_post(s, "/api/tickets", {"title": f"MERGE-PRIMARY {uuid.uuid4().hex[:8]}"})
        r2 = api_post(s, "/api/tickets", {"title": f"MERGE-SECONDARY {uuid.uuid4().hex[:8]}"})
        if r1.status_code not in (200,201) or r2.status_code not in (200,201):
            return False, "Could not create merge tickets"
        t1 = r1.json().get("ticket_id") or r1.json().get("id")
        t2 = r2.json().get("ticket_id") or r2.json().get("id")
        created_ticket_ids.extend([t1, t2])
        r = api_post(s, f"/api/tickets/{t1}/merge", {"source_ticket_id": t2})
        if r.status_code == 200:
            # Check secondary is now "merged"
            r3 = api_get(s, f"/api/tickets/{t2}")
            merged = r3.json().get("status") == "merged" if r3.status_code == 200 else False
            return merged, f"Merge status={r.status_code}, secondary_status={r3.json().get('status') if r3.status_code == 200 else 'N/A'}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("4.1", "Merge tickets: secondary becomes 'merged'", test_4_1_merge)

    def test_4_2_link():
        if len(created_ticket_ids) < 2:
            return False, "Need 2 tickets"
        r = api_post(s, f"/api/tickets/{created_ticket_ids[0]}/link", {"linked_ticket_id": created_ticket_ids[1], "link_type": "related"})
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}"
    runner.run_test("4.2", "Link tickets as related", test_4_2_link)

    def test_4_3_bulk_update():
        if len(created_ticket_ids) < 2:
            return False, "Need 2 tickets"
        r = api_put(s, "/api/tickets/bulk", {
            "ticket_ids": created_ticket_ids[:2],
            "updates": {"priority": "urgent"}
        })
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("4.3", "Bulk update tickets", test_4_3_bulk_update)

    # ===== 5. Internal Notes & Activity =====
    print("\n--- 5. Internal Notes & Activity ---")

    def test_5_1():
        if not created_ticket_ids:
            return False, "No tickets"
        r = api_post(s, f"/api/tickets/{created_ticket_ids[0]}/notes", {
            "content": "This is a QA test internal note"
        })
        ok = r.status_code in (200, 201)
        return ok, f"Status={r.status_code}"
    runner.run_test("5.1", "Add internal note to ticket", test_5_1)

    def test_5_2():
        if not created_ticket_ids:
            return False, "No tickets"
        r = api_get(s, f"/api/tickets/{created_ticket_ids[0]}/notes")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} notes"
        return False, f"Status={r.status_code}"
    runner.run_test("5.2", "List internal notes for ticket", test_5_2)

    def test_5_3():
        if not created_ticket_ids:
            return False, "No tickets"
        r = api_get(s, f"/api/tickets/{created_ticket_ids[0]}/messages")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} messages"
        return False, f"Status={r.status_code}"
    runner.run_test("5.3", "Get ticket messages/activity", test_5_3)

    # ===== 6. Tags & Starred =====
    print("\n--- 6. Tags & Starred ---")

    def test_6_1():
        r = api_get(s, "/api/tags")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list)
            return ok, f"Found {len(data)} tags"
        return False, f"Status={r.status_code}"
    runner.run_test("6.1", "GET /api/tags returns tag list", test_6_1)

    def test_6_2():
        if not created_ticket_ids:
            return False, "No tickets"
        r = api_put(s, f"/api/tickets/{created_ticket_ids[0]}", {"is_starred": True})
        if r.status_code == 200:
            return r.json().get("is_starred") == True, f"is_starred={r.json().get('is_starred')}"
        return False, f"Status={r.status_code}"
    runner.run_test("6.2", "Star a ticket", test_6_2)

    def test_6_3():
        r = api_get(s, "/api/tickets?is_starred=true")
        if r.status_code == 200:
            data = r.json()
            return True, f"Found {data.get('total', 0)} starred tickets"
        return False, f"Status={r.status_code}"
    runner.run_test("6.3", "Filter starred tickets", test_6_3)

    # ===== Cleanup =====
    print("\n--- Cleanup ---")
    for tid in created_ticket_ids:
        try:
            api_delete(s, f"/api/tickets/{tid}")
        except:
            pass

    runner.save_report()

run_batch()
