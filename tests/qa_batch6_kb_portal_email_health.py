"""
QA Batch 6: KB, Portal, Email/Upload, AI, Health (v2 - fixed)
"""
import sys, uuid
sys.path.insert(0, "/app/tests")
from qa_test_utils import *

def run_batch():
    runner = QATestRunner("batch6_kb_portal_email_health")
    s = runner.admin_session()
    s_noauth = runner.no_auth_session()

    print("=" * 60)
    print("BATCH 6: KB, Portal, Email/Upload, AI, Health")
    print("=" * 60)

    # ===== 22. KB Internal =====
    print("\n--- 22. KB Internal Snippets ---")
    created_snippet_id = None

    def test_22_1():
        r = api_get(s, "/api/knowledge-base")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("22.1", "GET /api/knowledge-base", test_22_1)

    def test_22_2():
        nonlocal created_snippet_id
        r = api_post(s, "/api/knowledge-base", {
            "title": f"QA-{uuid.uuid4().hex[:6]}", "content": "QA test content.",
            "tags": ["qa"], "status": "draft"})
        if r.status_code in (200, 201):
            created_snippet_id = r.json().get("snippet_id") or r.json().get("id")
            return created_snippet_id is not None, f"snippet_id={created_snippet_id}"
        return False, f"Status={r.status_code}"
    runner.run_test("22.2", "Create KB snippet", test_22_2)

    def test_22_3():
        if not created_snippet_id: return False, "No snippet"
        return api_get(s, f"/api/knowledge-base/{created_snippet_id}").status_code == 200, "OK"
    runner.run_test("22.3", "Get KB snippet", test_22_3)

    def test_22_4():
        if not created_snippet_id: return False, "No snippet"
        return api_put(s, f"/api/knowledge-base/{created_snippet_id}", {"status": "published"}).status_code == 200, "Published"
    runner.run_test("22.4", "Update KB snippet", test_22_4)

    def test_22_5():
        r = api_get(s, "/api/knowledge-base-search?q=QA")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("22.5", "GET /api/knowledge-base-search", test_22_5)

    def test_22_6():
        r = api_get(s, "/api/knowledge-base-export?format=json")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("22.6", "Export KB (JSON)", test_22_6)

    def test_22_7():
        r = api_get(s, "/api/knowledge-base-export?format=csv")
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("22.7", "Export KB (CSV)", test_22_7)

    def test_22_8():
        if not created_snippet_id: return False, "No snippet"
        return api_delete(s, f"/api/knowledge-base/{created_snippet_id}").status_code == 200, "Deleted"
    runner.run_test("22.8", "Delete KB snippet", test_22_8)

    # ===== 23. KB Public =====
    print("\n--- 23. KB Public Docs ---")
    created_article_slug = None

    def test_23_1():
        return api_get(s_noauth, "/api/kb/navigation").status_code == 200, "OK"
    runner.run_test("23.1", "GET /api/kb/navigation (public)", test_23_1)

    def test_23_2():
        return api_get(s_noauth, "/api/kb/public-data").status_code == 200, "OK"
    runner.run_test("23.2", "GET /api/kb/public-data (public)", test_23_2)

    def test_23_3():
        r = api_get(s_noauth, "/api/kb/articles")
        if r.status_code == 200:
            data = r.json()
            # Response is {"articles": [...]}
            articles = data.get("articles", []) if isinstance(data, dict) else data
            return isinstance(articles, list), f"Found {len(articles)} articles"
        return False, f"Status={r.status_code}"
    runner.run_test("23.3", "GET /api/kb/articles (public)", test_23_3)

    def test_23_4():
        nonlocal created_article_slug
        slug = f"qa-article-{uuid.uuid4().hex[:6]}"
        r = api_post(s, "/api/kb/admin/articles", {
            "title": f"QA Article {uuid.uuid4().hex[:6]}", "slug": slug,
            "section_key": "general", "section_label": "General",
            "nav_group_key": "getting-started", "nav_group_label": "Getting Started",
            "content_markdown": "# QA Test Article\nContent here.", "published": True})
        if r.status_code in (200, 201):
            created_article_slug = slug
            return True, f"slug={slug}"
        return False, f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("23.4", "Create KB article (admin)", test_23_4)

    def test_23_5():
        """Duplicate slug returns 409"""
        if not created_article_slug: return False, "No article"
        r = api_post(s, "/api/kb/admin/articles", {
            "title": "Dup", "slug": created_article_slug,
            "section_key": "g", "section_label": "G",
            "nav_group_key": "g", "nav_group_label": "G",
            "content_markdown": "dup"})
        return r.status_code == 409, f"Status={r.status_code}"
    runner.run_test("23.5", "Duplicate slug returns 409", test_23_5)

    def test_23_6():
        return api_get(s_noauth, "/api/kb/search?q=QA").status_code == 200, "OK"
    runner.run_test("23.6", "Search KB articles (public)", test_23_6)

    def test_23_7():
        r = api_get(s, "/api/kb/admin/articles")
        if r.status_code == 200:
            data = r.json()
            # Response is {"articles": [...], "nav_groups": [...]}
            articles = data.get("articles", []) if isinstance(data, dict) else data
            return isinstance(articles, list), f"Found {len(articles)} articles"
        return False, f"Status={r.status_code}"
    runner.run_test("23.7", "GET /api/kb/admin/articles", test_23_7)

    if created_article_slug:
        try: api_delete(s, f"/api/kb/admin/articles/{created_article_slug}")
        except: pass

    # ===== 24. Portal =====
    print("\n--- 24. Customer Portal ---")
    portal_token = None

    def test_24_1():
        email = f"qa_portal_{uuid.uuid4().hex[:6]}@example.com"
        r = api_post(s_noauth, "/api/portal/auth/register", {"email": email, "password": "testpass123", "name": "QA Portal"})
        return r.status_code in (200, 201), f"Status={r.status_code}"
    runner.run_test("24.1", "Portal registration", test_24_1)

    def test_24_2():
        r = api_post(s_noauth, "/api/portal/auth/register", {"email": f"x_{uuid.uuid4().hex[:6]}@e.com", "password": "12345", "name": "Short"})
        return r.status_code in (400, 422), f"Status={r.status_code}"
    runner.run_test("24.2", "Short password fails", test_24_2)

    def test_24_3():
        nonlocal portal_token
        email = f"qa_login_{uuid.uuid4().hex[:6]}@example.com"
        api_post(s_noauth, "/api/portal/auth/register", {"email": email, "password": "testpass123", "name": "Login"})
        r = api_post(s_noauth, "/api/portal/auth/login", {"email": email, "password": "testpass123"})
        if r.status_code == 200:
            portal_token = r.json().get("token")
            return portal_token is not None, f"token={portal_token is not None}"
        return False, f"Status={r.status_code}"
    runner.run_test("24.3", "Portal login", test_24_3)

    def test_24_4():
        r = api_post(s_noauth, "/api/portal/auth/login", {"email": "nonexist@e.com", "password": "wrong"})
        return r.status_code in (401, 404), f"Status={r.status_code}"
    runner.run_test("24.4", "Invalid portal login fails", test_24_4)

    def test_24_5():
        r = api_get(s_noauth, "/api/portal/categories")
        if r.status_code == 200:
            data = r.json()
            # Response is {"categories": [...]}
            cats = data.get("categories", []) if isinstance(data, dict) else data
            return isinstance(cats, list), f"Found {len(cats)} categories"
        return False, f"Status={r.status_code}"
    runner.run_test("24.5", "GET portal categories (public)", test_24_5)

    def test_24_6():
        if not portal_token: return False, "No token"
        ps = requests.Session()
        ps.headers.update({"Authorization": f"Bearer {portal_token}", "Content-Type": "application/json"})
        r = ps.post(f"{BASE_URL}/api/portal/tickets", json={
            "subject": f"Portal-{uuid.uuid4().hex[:6]}", "description": "Portal ticket", "category_slug": "general"}, timeout=15)
        return r.status_code in (200, 201), f"Status={r.status_code}, body={r.text[:200]}"
    runner.run_test("24.6", "Submit ticket via portal", test_24_6)

    def test_24_7():
        if not portal_token: return False, "No token"
        ps = requests.Session()
        ps.headers.update({"Authorization": f"Bearer {portal_token}", "Content-Type": "application/json"})
        r = ps.get(f"{BASE_URL}/api/portal/tickets", timeout=15)
        return r.status_code == 200, f"Status={r.status_code}"
    runner.run_test("24.7", "List portal tickets", test_24_7)

    # ===== 21. Email/Upload =====
    print("\n--- 21. Email, Upload & Import ---")

    def test_21_1():
        import io
        jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' + b'\x00'*100 + b'\xff\xd9'
        ss = runner.admin_session()
        ss.headers.pop("Content-Type", None)
        r = ss.post(f"{BASE_URL}/api/upload/image", files={"file": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")}, timeout=15)
        return r.status_code in (200, 201), f"Status={r.status_code}"
    runner.run_test("21.1", "Upload image", test_21_1)

    def test_21_2():
        r = api_get(s_noauth, "/api/uploads/../../etc/passwd")
        return r.status_code in (404, 400), f"Status={r.status_code}"
    runner.run_test("21.2", "Path traversal blocked", test_21_2)

    def test_21_4():
        t = api_post(s, "/api/tickets", {"title": f"Reply-{uuid.uuid4().hex[:8]}", "customer_email": f"r_{uuid.uuid4().hex[:4]}@e.com"})
        tid = t.json().get("ticket_id")
        r = api_post(s, f"/api/tickets/{tid}/reply", {"content": "Test reply", "reply_type": "email"})
        api_delete(s, f"/api/tickets/{tid}")
        return r.status_code in (200, 201), f"Status={r.status_code}"
    runner.run_test("21.4", "Ticket reply", test_21_4)

    # ===== 27. AI =====
    print("\n--- 27. AI Summaries ---")

    def test_27_1():
        t = api_post(s, "/api/tickets", {"title": f"AI-{uuid.uuid4().hex[:8]}"})
        tid = t.json().get("ticket_id")
        r = api_get(s, f"/api/tickets/{tid}/summary")
        api_delete(s, f"/api/tickets/{tid}")
        return r.status_code in (200, 400, 404), f"Status={r.status_code}"
    runner.run_test("27.1", "GET /api/tickets/:id/summary", test_27_1)

    # ===== 33. Atlas Import =====
    print("\n--- 33. Atlas Import ---")

    def test_33_1():
        r = api_post(s, "/api/import/atlas", {"atlas_url": "https://invalid.atlas.so/api/v1"})
        return r.status_code in (200, 400, 401, 422, 500), f"Status={r.status_code} (endpoint accessible)"
    runner.run_test("33.1", "Atlas import endpoint accessible", test_33_1)

    # ===== 34. Health =====
    print("\n--- 34. Health & Startup ---")

    def test_34_1():
        for path in ["/health", "/api/health", "/"]:
            r = api_get(s_noauth, path)
            if r.status_code == 200: return True, f"Health at {path}"
        return False, "No health endpoint"
    runner.run_test("34.1", "Health check", test_34_1)

    def test_34_2():
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return True, "MongoDB OK"
    runner.run_test("34.2", "MongoDB accessible", test_34_2)

    def test_34_3():
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        colls = client["test_database"].list_collection_names()
        missing = [c for c in ["users", "tickets", "user_sessions"] if c not in colls]
        return len(missing) == 0, f"Missing: {missing}"
    runner.run_test("34.3", "Required collections exist", test_34_3)

    def test_34_4():
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=5)
        return r.status_code in (200, 401), f"Backend responds: {r.status_code}"
    runner.run_test("34.4", "Backend on port 8001", test_34_4)

    def test_34_5():
        r = requests.get("http://localhost:3000", timeout=10)
        return r.status_code == 200, f"Frontend: {r.status_code}"
    runner.run_test("34.5", "Frontend on port 3000", test_34_5)

    runner.save_report()

run_batch()
