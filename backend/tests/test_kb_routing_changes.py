"""
Test KB Route Changes and Full-Page Editor Backend APIs
Routes Changed: KB now at / (homepage), Portal at /portal, KB Editor at /dashboard/kb-editor
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestKBPublicAPI:
    """Test public KB API endpoints (no auth required)"""
    
    def test_kb_public_data_returns_200(self):
        """A1: GET /api/kb/public-data returns 200 with correct structure"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert "config" in data
        assert "documents" in data
        print("PASS: /api/kb/public-data returns 200")
    
    def test_kb_public_data_has_5_navigation_tabs(self):
        """A2: Response has 5 navigation tabs"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        tabs = data["config"]["navigation"]["tabs"]
        assert len(tabs) == 5, f"Expected 5 tabs, got {len(tabs)}"
        tab_ids = [t["id"] for t in tabs]
        expected = ["beginners-guide", "features", "building-your-app", "deploy-and-manage", "troubleshooting"]
        assert tab_ids == expected, f"Tab IDs mismatch: {tab_ids}"
        print(f"PASS: 5 navigation tabs present: {tab_ids}")
    
    def test_kb_public_data_has_documents(self):
        """A3: Response has 21+ documents"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        docs = data["documents"]
        assert len(docs) >= 21, f"Expected 21+ documents, got {len(docs)}"
        print(f"PASS: {len(docs)} documents present")
    
    def test_documents_have_required_fields(self):
        """A4: Documents have id, slug, title, content fields"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        docs = data["documents"]
        for doc in docs[:5]:  # Check first 5
            assert "id" in doc, f"Missing id in doc"
            assert "slug" in doc, f"Missing slug in doc"
            assert "title" in doc, f"Missing title in doc"
            assert "content" in doc, f"Missing content in doc"
        print("PASS: Documents have required fields")
    
    def test_navigation_tabs_have_groups_with_pages(self):
        """A5: Navigation tabs have groups with pages"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        tabs = data["config"]["navigation"]["tabs"]
        for tab in tabs:
            assert "groups" in tab, f"Tab {tab['id']} missing groups"
            assert len(tab["groups"]) > 0, f"Tab {tab['id']} has no groups"
            for group in tab["groups"]:
                assert "pages" in group, f"Group {group.get('group')} missing pages"
        print("PASS: Tabs have groups with pages")
    
    def test_navbar_has_support_link(self):
        """A6: Navbar has Support link pointing to /portal"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        navbar = data["config"]["navbar"]
        links = navbar.get("links", [])
        support_link = next((l for l in links if l.get("label") == "Support"), None)
        assert support_link is not None, "No Support link in navbar"
        assert support_link.get("href") == "/portal", f"Support link href is {support_link.get('href')}"
        print("PASS: Navbar has Support link pointing to /portal")
    
    def test_kb_articles_list(self):
        """A7: GET /api/kb/articles returns article list"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert len(data["articles"]) > 0
        # Verify content_markdown is excluded
        for art in data["articles"]:
            assert "content_markdown" not in art, "content_markdown should be excluded"
        print(f"PASS: /api/kb/articles returns {len(data['articles'])} articles")
    
    def test_kb_article_by_slug_welcome(self):
        """A8: GET /api/kb/articles/welcome returns full article"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        data = response.json()
        assert "article" in data
        assert data["article"]["slug"] == "welcome"
        assert data["article"]["title"] == "Welcome To Emergent"
        assert "content_markdown" in data["article"]
        print("PASS: /api/kb/articles/welcome returns Welcome article")
    
    def test_kb_article_by_slug_voice_mode(self):
        """A9: GET /api/kb/articles/voice-mode returns correct article"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/voice-mode")
        assert response.status_code == 200
        data = response.json()
        assert data["article"]["slug"] == "voice-mode"
        assert "Voice Mode" in data["article"]["title"]
        print("PASS: /api/kb/articles/voice-mode returns Voice Mode article")
    
    def test_kb_search_emergent(self):
        """A10: GET /api/kb/search?q=emergent returns results"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0, "Expected search results for 'emergent'"
        print(f"PASS: Search for 'emergent' returns {len(data['results'])} results")
    
    def test_kb_search_short_query(self):
        """S5: Typing 1 character shows no results"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=a")
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("results", [])) == 0, "Expected no results for 1-char query"
        print("PASS: 1-character search returns no results")
    
    def test_kb_navigation(self):
        """GET /api/kb/navigation returns nav_groups"""
        response = requests.get(f"{BASE_URL}/api/kb/navigation")
        assert response.status_code == 200
        data = response.json()
        assert "nav_groups" in data
        print("PASS: /api/kb/navigation works")


class TestKBAdminAPIAuth:
    """Test admin KB endpoints require authentication"""
    
    def test_admin_articles_requires_auth(self):
        """A11: GET /api/kb/admin/articles returns articles (requires auth)"""
        response = requests.get(f"{BASE_URL}/api/kb/admin/articles")
        # Should return 401 without auth
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/kb/admin/articles requires auth")
    
    def test_admin_create_article_requires_auth(self):
        """A12: POST /api/kb/admin/articles requires auth"""
        payload = {
            "title": "Test Article",
            "slug": "test-article",
            "section_key": "introduction",
            "section_label": "Introduction",
            "nav_group_key": "beginners-guide",
            "nav_group_label": "The Beginner's Guide",
            "content_markdown": "Test content"
        }
        response = requests.post(f"{BASE_URL}/api/kb/admin/articles", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/kb/admin/articles requires auth")
    
    def test_admin_update_article_requires_auth(self):
        """A13: PUT /api/kb/admin/articles/:slug requires auth"""
        response = requests.put(f"{BASE_URL}/api/kb/admin/articles/welcome", json={"title": "Updated"})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: PUT /api/kb/admin/articles/:slug requires auth")
    
    def test_admin_delete_article_requires_auth(self):
        """A14: DELETE /api/kb/admin/articles/:slug requires auth"""
        response = requests.delete(f"{BASE_URL}/api/kb/admin/articles/welcome")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: DELETE /api/kb/admin/articles/:slug requires auth")


class TestPortalRegression:
    """Test Portal endpoints still work after route changes"""
    
    def test_portal_categories(self):
        """A15: GET /api/portal/categories still works (regression)"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200, f"Portal categories failed: {response.status_code}"
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0, "No portal categories"
        print(f"PASS: Portal categories working ({len(data['categories'])} categories)")


class TestRoutingIntegrity:
    """Verify routing changes don't break basic endpoints"""
    
    def test_health_check(self):
        """Basic health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("PASS: /api/health returns 200")
    
    def test_auth_me_returns_401_unauthenticated(self):
        """R11: /dashboard redirects to login (API returns 401 without auth)"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("PASS: /api/auth/me returns 401 without auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
