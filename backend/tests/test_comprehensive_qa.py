"""
Comprehensive QA Test Suite for KB Docs and Customer Portal
Tests all backend APIs for KB and Portal functionality
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://support-portal-86.preview.emergentagent.com')

# Generate unique test email for each test run
TEST_EMAIL = f"testqa_{int(time.time())}_{uuid.uuid4().hex[:6]}@test.com"
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "QA Test User"


class TestKBPublicData:
    """Test KB public-data endpoint (AK1-AK10)"""

    def test_ak1_public_data_returns_200(self):
        """AK1: GET /api/kb/public-data returns 200"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"

    def test_ak2_response_has_required_fields(self):
        """AK2: Response has project, config, documents fields"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        assert "project" in data, "Missing 'project' field"
        assert "config" in data, "Missing 'config' field"
        assert "documents" in data, "Missing 'documents' field"

    def test_ak3_navigation_has_5_tabs(self):
        """AK3: config.navigation.tabs has 5 tabs"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        assert len(tabs) == 5, f"Expected 5 tabs, got {len(tabs)}"

    def test_ak4_tabs_have_required_fields(self):
        """AK4: Each tab has id, label, icon, groups"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        for tab in tabs:
            assert "id" in tab, f"Tab missing 'id': {tab}"
            assert "label" in tab, f"Tab missing 'label': {tab}"
            assert "icon" in tab, f"Tab missing 'icon': {tab}"
            assert "groups" in tab, f"Tab missing 'groups': {tab}"

    def test_ak5_groups_have_pages(self):
        """AK5: Groups have group name and pages array"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        for tab in tabs:
            for group in tab.get("groups", []):
                assert "group" in group, f"Group missing 'group' field: {group}"
                assert "pages" in group, f"Group missing 'pages' field: {group}"
                assert isinstance(group["pages"], list), "pages should be a list"

    def test_ak6_pages_have_slug_and_title(self):
        """AK6: Pages have page (slug) and title"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        for tab in tabs:
            for group in tab.get("groups", []):
                for page in group.get("pages", []):
                    assert "page" in page, f"Page missing 'page': {page}"
                    assert "title" in page, f"Page missing 'title': {page}"

    def test_ak7_documents_count(self):
        """AK7: documents array has 21+ items"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        docs = data.get("documents", [])
        assert len(docs) >= 21, f"Expected 21+ documents, got {len(docs)}"

    def test_ak8_documents_have_required_fields(self):
        """AK8: Each document has id, slug, title, content"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        docs = data.get("documents", [])
        for doc in docs[:5]:  # Check first 5 documents
            assert "id" in doc, f"Document missing 'id': {doc}"
            assert "slug" in doc, f"Document missing 'slug': {doc}"
            assert "title" in doc, f"Document missing 'title': {doc}"
            assert "content" in doc, f"Document missing 'content': {doc}"

    def test_ak9_navbar_has_support_link(self):
        """AK9: config.navbar.links includes Support -> /portal"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        links = data.get("config", {}).get("navbar", {}).get("links", [])
        support_link = next((l for l in links if l.get("label") == "Support"), None)
        assert support_link is not None, "Missing Support link in navbar"
        assert support_link.get("href") == "/portal", f"Support href should be /portal, got {support_link.get('href')}"

    def test_ak10_navbar_has_primary_cta(self):
        """AK10: config.navbar.primary has Try Emergent link"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        primary = data.get("config", {}).get("navbar", {}).get("primary", {})
        assert primary.get("label") == "Try Emergent", f"Expected 'Try Emergent', got {primary.get('label')}"
        assert "emergent" in primary.get("href", "").lower(), f"Expected emergent URL, got {primary.get('href')}"


class TestKBArticlesAPI:
    """Test KB articles endpoints (AK11-AK15)"""

    def test_ak11_articles_list(self):
        """AK11: GET /api/kb/articles returns article list without content_markdown"""
        res = requests.get(f"{BASE_URL}/api/kb/articles")
        assert res.status_code == 200
        data = res.json()
        assert "articles" in data
        # Check that content_markdown is excluded
        for article in data.get("articles", [])[:3]:
            assert "content_markdown" not in article, "content_markdown should be excluded"

    def test_ak12_articles_by_slug(self):
        """AK12: GET /api/kb/articles/welcome returns full article with content"""
        res = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert res.status_code == 200
        data = res.json()
        assert "article" in data
        article = data["article"]
        assert article.get("slug") == "welcome"
        assert "content_markdown" in article

    def test_ak13_nonexistent_article_404(self):
        """AK13: GET /api/kb/articles/nonexistent returns 404"""
        res = requests.get(f"{BASE_URL}/api/kb/articles/nonexistent-slug-xyz123")
        assert res.status_code == 404

    def test_ak14_search_returns_results(self):
        """AK14: GET /api/kb/search?q=voice returns results"""
        res = requests.get(f"{BASE_URL}/api/kb/search?q=voice")
        assert res.status_code == 200
        data = res.json()
        assert "results" in data
        assert len(data["results"]) > 0, "Expected results for 'voice' search"

    def test_ak15_navigation_endpoint(self):
        """AK15: GET /api/kb/navigation returns nav_groups"""
        res = requests.get(f"{BASE_URL}/api/kb/navigation")
        assert res.status_code == 200
        data = res.json()
        assert "nav_groups" in data


class TestPortalCategories:
    """Test Portal Categories endpoints (AP1-AP4)"""

    def test_ap1_categories_list(self):
        """AP1: GET /api/portal/categories returns list of categories"""
        res = requests.get(f"{BASE_URL}/api/portal/categories")
        assert res.status_code == 200
        data = res.json()
        assert "categories" in data
        assert len(data["categories"]) > 0, "Expected categories"

    def test_ap2_categories_have_required_fields(self):
        """AP2: Each category has slug, title, description, icon"""
        res = requests.get(f"{BASE_URL}/api/portal/categories")
        data = res.json()
        for cat in data.get("categories", [])[:5]:
            assert "slug" in cat, f"Category missing 'slug': {cat}"
            assert "title" in cat, f"Category missing 'title': {cat}"
            assert "description" in cat, f"Category missing 'description': {cat}"
            assert "icon" in cat, f"Category missing 'icon': {cat}"

    def test_ap3_category_by_slug(self):
        """AP3: GET /api/portal/categories/:slug returns single category"""
        res = requests.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        assert res.status_code == 200
        data = res.json()
        assert data.get("slug") == "credits-pricing"
        assert "title" in data

    def test_ap4_nonexistent_category_404(self):
        """AP4: GET /api/portal/categories/nonexistent returns 404"""
        res = requests.get(f"{BASE_URL}/api/portal/categories/nonexistent-cat-xyz")
        assert res.status_code == 404


class TestPortalAuth:
    """Test Portal Authentication endpoints (AP5-AP10)"""
    
    # Class-level storage for token
    _token = None
    _customer_id = None

    def test_ap5_register_customer(self):
        """AP5: POST /api/portal/auth/register creates new customer"""
        res = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
            "name": TEST_NAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        assert res.status_code == 200, f"Registration failed: {res.text}"
        data = res.json()
        assert "customer_id" in data
        assert "token" in data
        assert data["email"] == TEST_EMAIL.lower()
        TestPortalAuth._token = data["token"]
        TestPortalAuth._customer_id = data["customer_id"]

    def test_ap6_register_duplicate_fails(self):
        """AP6: POST /api/portal/auth/register with duplicate email fails"""
        res = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
            "name": "Duplicate User",
            "email": TEST_EMAIL,
            "password": "AnotherPass123!",
        })
        assert res.status_code == 409, f"Expected 409 for duplicate, got {res.status_code}"

    def test_ap7_login_valid_credentials(self):
        """AP7: POST /api/portal/auth/login with valid creds returns token"""
        res = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        data = res.json()
        assert "token" in data
        assert "customer_id" in data
        TestPortalAuth._token = data["token"]

    def test_ap8_login_wrong_password(self):
        """AP8: POST /api/portal/auth/login with wrong password fails"""
        res = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": TEST_EMAIL,
            "password": "WrongPassword123!",
        })
        assert res.status_code == 401

    def test_ap9_get_me_with_token(self):
        """AP9: GET /api/portal/auth/me with valid token returns customer"""
        if not TestPortalAuth._token:
            pytest.skip("No token available - registration may have failed")
        res = requests.get(f"{BASE_URL}/api/portal/auth/me", 
                          headers={"Authorization": f"Bearer {TestPortalAuth._token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == TEST_EMAIL.lower()

    def test_ap10_get_me_without_token(self):
        """AP10: GET /api/portal/auth/me without token returns 401"""
        res = requests.get(f"{BASE_URL}/api/portal/auth/me")
        assert res.status_code == 401


class TestPortalTickets:
    """Test Portal Ticket endpoints (AP11-AP18)"""
    
    _ticket_id = None
    _token = None

    @pytest.fixture(autouse=True)
    def setup_token(self):
        """Ensure we have a valid token for ticket tests"""
        if not TestPortalTickets._token:
            # Login first
            res = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            })
            if res.status_code == 200:
                TestPortalTickets._token = res.json()["token"]
            else:
                # Try to register
                reg_res = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
                    "name": TEST_NAME,
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                })
                if reg_res.status_code == 200:
                    TestPortalTickets._token = reg_res.json()["token"]

    def test_ap11_create_ticket_auth_required(self):
        """AP11: POST /api/portal/tickets creates ticket (auth required)"""
        if not TestPortalTickets._token:
            pytest.skip("No token available")
        res = requests.post(f"{BASE_URL}/api/portal/tickets", 
                           headers={"Authorization": f"Bearer {TestPortalTickets._token}"},
                           json={
                               "category_slug": "credits-pricing",
                               "subcategory": "Credit Usage",
                               "subject": "QA Test Ticket",
                               "description": "This is a test ticket created during QA testing",
                           })
        assert res.status_code == 200, f"Ticket creation failed: {res.text}"
        data = res.json()
        assert "ticket_id" in data
        TestPortalTickets._ticket_id = data["ticket_id"]

    def test_ap12_create_ticket_without_auth(self):
        """AP12: POST /api/portal/tickets without auth returns 401"""
        res = requests.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "credits-pricing",
            "subject": "Unauthorized Ticket",
            "description": "Should fail",
        })
        assert res.status_code == 401

    def test_ap13_list_tickets_auth_required(self):
        """AP13: GET /api/portal/tickets returns customer's tickets (auth required)"""
        if not TestPortalTickets._token:
            pytest.skip("No token available")
        res = requests.get(f"{BASE_URL}/api/portal/tickets",
                          headers={"Authorization": f"Bearer {TestPortalTickets._token}"})
        assert res.status_code == 200
        data = res.json()
        assert "tickets" in data

    def test_ap14_get_ticket_detail(self):
        """AP14: GET /api/portal/tickets/:id returns ticket detail with messages"""
        if not TestPortalTickets._token or not TestPortalTickets._ticket_id:
            pytest.skip("No token or ticket_id available")
        res = requests.get(f"{BASE_URL}/api/portal/tickets/{TestPortalTickets._ticket_id}",
                          headers={"Authorization": f"Bearer {TestPortalTickets._token}"})
        assert res.status_code == 200
        data = res.json()
        assert "ticket" in data
        assert "messages" in data
        assert data["ticket"]["ticket_id"] == TestPortalTickets._ticket_id

    def test_ap15_reply_to_ticket(self):
        """AP15: POST /api/portal/tickets/:id/reply adds reply message"""
        if not TestPortalTickets._token or not TestPortalTickets._ticket_id:
            pytest.skip("No token or ticket_id available")
        res = requests.post(f"{BASE_URL}/api/portal/tickets/{TestPortalTickets._ticket_id}/reply",
                           headers={"Authorization": f"Bearer {TestPortalTickets._token}"},
                           json={"body": "QA Test reply message"})
        assert res.status_code == 200
        data = res.json()
        assert "message_id" in data

    def test_ap16_reply_type_is_customer_reply(self):
        """AP16: Reply type is 'customer_reply'"""
        if not TestPortalTickets._token or not TestPortalTickets._ticket_id:
            pytest.skip("No token or ticket_id available")
        res = requests.get(f"{BASE_URL}/api/portal/tickets/{TestPortalTickets._ticket_id}",
                          headers={"Authorization": f"Bearer {TestPortalTickets._token}"})
        data = res.json()
        messages = data.get("messages", [])
        # Should have original + reply
        reply_msgs = [m for m in messages if m.get("type") == "customer_reply"]
        assert len(reply_msgs) > 0, "No customer_reply messages found"

    def test_ap17_ticket_updated_after_reply(self):
        """AP17: Ticket status updates with last_customer_reply_at after reply"""
        if not TestPortalTickets._token or not TestPortalTickets._ticket_id:
            pytest.skip("No token or ticket_id available")
        res = requests.get(f"{BASE_URL}/api/portal/tickets/{TestPortalTickets._ticket_id}",
                          headers={"Authorization": f"Bearer {TestPortalTickets._token}"})
        data = res.json()
        ticket = data.get("ticket", {})
        # After customer reply, status should be 'todo' (reopened)
        assert ticket.get("status") == "todo", f"Expected 'todo' status after reply, got {ticket.get('status')}"

    def test_ap18_logout(self):
        """AP18: POST /api/portal/auth/logout clears session"""
        if not TestPortalTickets._token:
            pytest.skip("No token available")
        res = requests.post(f"{BASE_URL}/api/portal/auth/logout",
                           headers={"Authorization": f"Bearer {TestPortalTickets._token}"})
        assert res.status_code == 200


class TestKBAdminAuth:
    """Test that KB admin endpoints require authentication"""

    def test_admin_articles_requires_auth(self):
        """Admin GET /api/kb/admin/articles requires auth"""
        res = requests.get(f"{BASE_URL}/api/kb/admin/articles")
        assert res.status_code == 401

    def test_admin_create_article_requires_auth(self):
        """Admin POST /api/kb/admin/articles requires auth"""
        res = requests.post(f"{BASE_URL}/api/kb/admin/articles", json={
            "title": "Test",
            "slug": "test",
            "section_key": "test",
            "section_label": "Test",
            "nav_group_key": "test",
            "nav_group_label": "Test",
        })
        assert res.status_code == 401

    def test_admin_update_article_requires_auth(self):
        """Admin PUT /api/kb/admin/articles/:slug requires auth"""
        res = requests.put(f"{BASE_URL}/api/kb/admin/articles/welcome", json={
            "title": "Modified Title",
        })
        assert res.status_code == 401

    def test_admin_delete_article_requires_auth(self):
        """Admin DELETE /api/kb/admin/articles/:slug requires auth"""
        res = requests.delete(f"{BASE_URL}/api/kb/admin/articles/welcome")
        assert res.status_code == 401


class TestPortalAdminAuth:
    """Test that Portal admin endpoints require authentication"""

    def test_admin_create_category_requires_auth(self):
        """Admin POST /api/portal/admin/categories requires auth"""
        res = requests.post(f"{BASE_URL}/api/portal/admin/categories", json={
            "title": "Test Category",
            "slug": "test-category",
        })
        assert res.status_code == 401

    def test_admin_update_category_requires_auth(self):
        """Admin PUT /api/portal/admin/categories/:slug requires auth"""
        res = requests.put(f"{BASE_URL}/api/portal/admin/categories/credits-pricing", json={
            "title": "Modified Title",
        })
        assert res.status_code == 401

    def test_admin_delete_category_requires_auth(self):
        """Admin DELETE /api/portal/admin/categories/:slug requires auth"""
        res = requests.delete(f"{BASE_URL}/api/portal/admin/categories/credits-pricing")
        assert res.status_code == 401


class TestKBTabMapping:
    """Test that KB tabs map to correct first articles"""

    def test_beginners_guide_first_article(self):
        """Beginner's Guide tab first article is welcome"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        bg_tab = next((t for t in tabs if t["id"] == "beginners-guide"), None)
        assert bg_tab is not None, "Beginner's Guide tab not found"
        first_group = bg_tab["groups"][0] if bg_tab["groups"] else None
        assert first_group is not None
        first_page = first_group["pages"][0]["page"] if first_group["pages"] else None
        assert first_page == "welcome", f"Expected 'welcome', got {first_page}"

    def test_features_first_article(self):
        """Features tab first article is voice-mode"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        f_tab = next((t for t in tabs if t["id"] == "features"), None)
        assert f_tab is not None, "Features tab not found"
        first_group = f_tab["groups"][0] if f_tab["groups"] else None
        assert first_group is not None
        first_page = first_group["pages"][0]["page"] if first_group["pages"] else None
        assert first_page == "voice-mode", f"Expected 'voice-mode', got {first_page}"

    def test_building_your_app_first_article(self):
        """Building Your App tab first article is prompting-basics"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        bya_tab = next((t for t in tabs if t["id"] == "building-your-app"), None)
        assert bya_tab is not None, "Building Your App tab not found"
        first_group = bya_tab["groups"][0] if bya_tab["groups"] else None
        assert first_group is not None
        first_page = first_group["pages"][0]["page"] if first_group["pages"] else None
        assert first_page == "prompting-basics", f"Expected 'prompting-basics', got {first_page}"

    def test_deploy_and_manage_first_article(self):
        """Deploy and Manage tab first article is pre-deployment-health-check"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        dm_tab = next((t for t in tabs if t["id"] == "deploy-and-manage"), None)
        assert dm_tab is not None, "Deploy and Manage tab not found"
        first_group = dm_tab["groups"][0] if dm_tab["groups"] else None
        assert first_group is not None
        first_page = first_group["pages"][0]["page"] if first_group["pages"] else None
        assert first_page == "pre-deployment-health-check", f"Expected 'pre-deployment-health-check', got {first_page}"

    def test_troubleshooting_first_article(self):
        """Troubleshooting tab first article check"""
        res = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = res.json()
        tabs = data.get("config", {}).get("navigation", {}).get("tabs", [])
        ts_tab = next((t for t in tabs if t["id"] == "troubleshooting"), None)
        assert ts_tab is not None, "Troubleshooting tab not found"
        first_group = ts_tab["groups"][0] if ts_tab["groups"] else None
        assert first_group is not None
        # Just verify it has pages
        assert len(first_group["pages"]) > 0, "Troubleshooting should have pages"


class TestKBSearch:
    """Test KB Search functionality"""

    def test_search_min_2_chars(self):
        """Search requires at least 2 characters"""
        res = requests.get(f"{BASE_URL}/api/kb/search?q=a")
        assert res.status_code == 200
        data = res.json()
        assert data.get("results") == []

    def test_search_voice_returns_results(self):
        """Searching 'voice' returns results"""
        res = requests.get(f"{BASE_URL}/api/kb/search?q=voice")
        assert res.status_code == 200
        data = res.json()
        assert len(data.get("results", [])) > 0

    def test_search_emergent_returns_many(self):
        """Searching 'emergent' returns many results"""
        res = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert res.status_code == 200
        data = res.json()
        assert len(data.get("results", [])) > 5  # Should find multiple mentions

    def test_search_nonexistent(self):
        """Searching nonexistent term returns empty"""
        res = requests.get(f"{BASE_URL}/api/kb/search?q=xyznonexistent123abc")
        assert res.status_code == 200
        data = res.json()
        assert data.get("results") == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
