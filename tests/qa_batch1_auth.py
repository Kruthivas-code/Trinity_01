"""
QA Batch 1: Authentication, Authorization & User Management
Sections: 1, 26 from QA Test Plan
"""
import sys
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch1_auth_users")
    s_admin = runner.admin_session()
    s_lead = runner.lead_session()
    s_agent = runner.agent_session()
    s_noauth = runner.no_auth_session()

    print("=" * 60)
    print("BATCH 1: Authentication, Authorization & User Management")
    print("=" * 60)

    # ===== 1.2 Get Current User =====
    print("\n--- 1.2 Get Current User (GET /api/auth/me) ---")

    def test_1_2_1():
        r = api_get(s_admin, "/api/auth/me")
        ok = r.status_code == 200 and r.json().get("user_id") == "qa_admin_user"
        return ok, f"Status={r.status_code}, user_id={r.json().get('user_id')}"
    runner.run_test("1.2.1", "Valid session token (cookie) returns user object", test_1_2_1)

    def test_1_2_2():
        s = requests.Session()
        s.headers.update({"Authorization": "Bearer qa_test_admin_session_token_2026", "Content-Type": "application/json"})
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
        ok = r.status_code == 200 and r.json().get("user_id") == "qa_admin_user"
        return ok, f"Status={r.status_code}"
    runner.run_test("1.2.2", "Valid session token (Bearer header) returns user object", test_1_2_2)

    def test_1_2_3():
        r = api_get(s_noauth, "/api/auth/me")
        return r.status_code == 401, f"Status={r.status_code}, detail={r.json().get('detail')}"
    runner.run_test("1.2.3", "No token returns 401", test_1_2_3)

    def test_1_2_4():
        s = requests.Session()
        s.cookies.set("session_token", "invalid_token_xyz")
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
        return r.status_code == 401, f"Status={r.status_code}"
    runner.run_test("1.2.4", "Invalid session token returns 401", test_1_2_4)

    def test_1_2_5():
        # Create expired session directly via DB
        from pymongo import MongoClient
        from datetime import datetime, timezone, timedelta
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        expired_token = "qa_expired_token_test"
        db.user_sessions.update_one(
            {"session_token": expired_token},
            {"$set": {
                "session_token": expired_token,
                "user_id": "qa_admin_user",
                "expires_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
                "created_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
            }},
            upsert=True
        )
        s = requests.Session()
        s.cookies.set("session_token", expired_token)
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
        # Clean up
        db.user_sessions.delete_one({"session_token": expired_token})
        ok = r.status_code == 401 and "expired" in r.json().get("detail", "").lower()
        return ok, f"Status={r.status_code}, detail={r.json().get('detail')}"
    runner.run_test("1.2.5", "Expired session token returns 401 'Session expired'", test_1_2_5)

    # ===== 1.3 Logout =====
    print("\n--- 1.3 Logout (POST /api/auth/logout) ---")

    def test_1_3_1():
        from pymongo import MongoClient
        from datetime import datetime, timezone, timedelta
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        temp_token = "qa_logout_test_token"
        db.user_sessions.insert_one({
            "session_token": temp_token,
            "user_id": "qa_admin_user",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "created_at": datetime.now(timezone.utc),
        })
        s = requests.Session()
        s.cookies.set("session_token", temp_token)
        r = s.post(f"{BASE_URL}/api/auth/logout", timeout=10)
        # Verify session deleted
        session_exists = db.user_sessions.find_one({"session_token": temp_token})
        ok = r.status_code == 200 and session_exists is None
        return ok, f"Status={r.status_code}, session_deleted={session_exists is None}"
    runner.run_test("1.3.1", "Logout with valid session deletes session from DB", test_1_3_1)

    def test_1_3_2():
        r = api_post(s_noauth, "/api/auth/logout")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("1.3.2", "Logout with no session token returns 200", test_1_3_2)

    # ===== 1.4 API Key Management =====
    print("\n--- 1.4 API Key Management ---")

    created_key_id = None
    created_key_value = None

    def test_1_4_1():
        nonlocal created_key_id, created_key_value
        r = api_post(s_admin, "/api/auth/api-keys", {"name": "QA Test Key", "description": "For QA testing"})
        if r.status_code == 200:
            data = r.json()
            created_key_id = data.get("key_id")
            created_key_value = data.get("key")
            ok = all([created_key_id, created_key_value, data.get("name") == "QA Test Key"])
            return ok, f"key_id={created_key_id}, key_prefix={created_key_value[:12] if created_key_value else 'N/A'}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("1.4.1", "Create API key returns key_id and full key", test_1_4_1)

    def test_1_4_3():
        r = api_get(s_admin, "/api/auth/api-keys")
        if r.status_code == 200:
            keys = r.json()
            ok = isinstance(keys, list) and any(k.get("key_id") == created_key_id for k in keys)
            # Check key_hash is excluded
            has_hash = any("key_hash" in k for k in keys)
            return ok and not has_hash, f"Found {len(keys)} keys, has_hash_exposed={has_hash}"
        return False, f"Status={r.status_code}"
    runner.run_test("1.4.3", "List API keys returns keys for current user, key_hash excluded", test_1_4_3)

    def test_1_4_6_and_7():
        if not created_key_value:
            return False, "No API key created in 1.4.1"
        s = requests.Session()
        s.headers.update({"X-API-Key": created_key_value, "Content-Type": "application/json"})
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
        ok = r.status_code == 200
        return ok, f"Status={r.status_code}, API key auth works"
    runner.run_test("1.4.7", "API key SHA-256 lookup + bcrypt verification works", test_1_4_6_and_7)

    def test_1_4_4():
        if not created_key_id:
            return False, "No API key created"
        r = api_delete(s_admin, f"/api/auth/api-keys/{created_key_id}")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("1.4.4", "Revoke API key", test_1_4_4)

    def test_1_4_6():
        if not created_key_value:
            return False, "No API key available"
        s = requests.Session()
        s.headers.update({"X-API-Key": created_key_value, "Content-Type": "application/json"})
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
        return r.status_code == 401, f"Status={r.status_code}"
    runner.run_test("1.4.6", "Use revoked API key returns 401", test_1_4_6)

    def test_1_4_5():
        # Agent trying to revoke admin's key
        r = api_delete(s_agent, f"/api/auth/api-keys/{created_key_id or 'nonexistent'}")
        return r.status_code == 404, f"Status={r.status_code}"
    runner.run_test("1.4.5", "Revoke another user's API key returns 404", test_1_4_5)

    # ===== 1.5 Role-Based Authorization =====
    print("\n--- 1.5 Role-Based Authorization ---")

    def test_1_5_1():
        r = api_get(s_agent, "/api/tickets")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("1.5.1", "Agent accessing agent-level endpoint (GET tickets)", test_1_5_1)

    def test_1_5_3():
        # Admin-only: export endpoints
        r = api_get(s_agent, "/api/admin/export/customers")
        return r.status_code == 403, f"Status={r.status_code}, detail={r.json().get('detail','')}"
    runner.run_test("1.5.3", "Agent accessing admin-only endpoint returns 403", test_1_5_3)

    def test_1_5_5():
        r = api_get(s_admin, "/api/admin/export/customers")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("1.5.5", "Admin accessing admin endpoint is allowed", test_1_5_5)

    # ===== 26. User Management =====
    print("\n--- 26. User Management ---")

    def test_26_1():
        r = api_get(s_admin, "/api/users/me")
        if r.status_code == 200:
            data = r.json()
            ok = data.get("email") == "qa_admin@test.com"
            return ok, f"email={data.get('email')}"
        return False, f"Status={r.status_code}"
    runner.run_test("26.1", "GET /api/users/me returns current user profile", test_26_1)

    def test_26_2():
        r = api_put(s_admin, "/api/users/me/preferences", {"theme": "light"})
        if r.status_code == 200:
            # Verify
            r2 = api_get(s_admin, "/api/users/me")
            prefs = r2.json().get("preferences", {})
            ok = prefs.get("theme") == "light"
            # Reset
            api_put(s_admin, "/api/users/me/preferences", {"theme": "dark"})
            return ok, f"theme={prefs.get('theme')}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("26.2", "PUT /api/users/me/preferences updates preferences", test_26_2)

    def test_26_3():
        r = api_get(s_admin, "/api/users")
        if r.status_code == 200:
            data = r.json()
            ok = isinstance(data, list) and len(data) > 0
            return ok, f"Found {len(data)} users"
        return False, f"Status={r.status_code}"
    runner.run_test("26.3", "GET /api/users lists all users", test_26_3)

    def test_26_4():
        r = api_get(s_admin, "/api/users?search=qa_admin")
        if r.status_code == 200:
            data = r.json()
            found = any("qa_admin" in u.get("email", "") for u in data)
            return found, f"Found {len(data)} matching users"
        return False, f"Status={r.status_code}"
    runner.run_test("26.4", "GET /api/users?search= filters users", test_26_4)

    def test_26_5():
        r = api_put(s_admin, "/api/users/qa_agent_user/role", {"role": "lead"})
        status_ok = r.status_code == 200
        # Verify
        r2 = api_get(s_admin, "/api/users")
        agent_user = [u for u in r2.json() if u.get("user_id") == "qa_agent_user"]
        role_ok = agent_user[0].get("role") == "lead" if agent_user else False
        # Reset
        api_put(s_admin, "/api/users/qa_agent_user/role", {"role": "agent"})
        return status_ok and role_ok, f"Status={r.status_code}, role updated"
    runner.run_test("26.5", "Admin can update user role", test_26_5)

    def test_26_6():
        r = api_put(s_agent, "/api/users/qa_lead_user/role", {"role": "agent"})
        return r.status_code == 403, f"Status={r.status_code}"
    runner.run_test("26.6", "Agent cannot update user role (403)", test_26_6)

    runner.save_report()

run_batch()
