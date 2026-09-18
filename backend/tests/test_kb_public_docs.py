"""
Test KB Public Docs API - Testing the new PublicDocs component backend endpoints
Tests /api/kb/public-data endpoint and related functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestKBPublicDataEndpoint:
    """Test /api/kb/public-data endpoint - Main data source for PublicDocs frontend"""

    def test_public_data_returns_200(self):
        """GET /api/kb/public-data returns 200"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /api/kb/public-data returns 200")

    def test_public_data_structure(self):
        """Verify response contains project, config, and documents"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        assert "project" in data, "Missing 'project' key"
        assert "config" in data, "Missing 'config' key"
        assert "documents" in data, "Missing 'documents' key"
        
        # Verify project structure
        project = data["project"]
        assert "id" in project, "Project missing 'id'"
        assert "name" in project, "Project missing 'name'"
        assert "slug" in project, "Project missing 'slug'"
        print(f"PASS: Response structure valid - project: {project['name']}")

    def test_config_has_navigation_tabs(self):
        """Verify config.navigation.tabs contains 5 tabs"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        config = data.get("config", {})
        navigation = config.get("navigation", {})
        tabs = navigation.get("tabs", [])
        
        assert len(tabs) >= 5, f"Expected at least 5 tabs, got {len(tabs)}"
        
        # Verify expected tab IDs
        expected_tab_ids = ["beginners-guide", "features", "building-your-app", "deploy-and-manage", "troubleshooting"]
        actual_tab_ids = [t["id"] for t in tabs]
        for expected_id in expected_tab_ids:
            assert expected_id in actual_tab_ids, f"Missing tab '{expected_id}'"
        
        print(f"PASS: Found {len(tabs)} tabs: {actual_tab_ids}")

    def test_tab_labels(self):
        """Verify each tab has correct label"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        tabs = data["config"]["navigation"]["tabs"]
        expected_labels = {
            "beginners-guide": "The Beginner's Guide",
            "features": "Features",
            "building-your-app": "Building Your App",
            "deploy-and-manage": "Deploy and Manage",
            "troubleshooting": "Troubleshooting"
        }
        
        for tab in tabs:
            if tab["id"] in expected_labels:
                assert tab["label"] == expected_labels[tab["id"]], f"Tab {tab['id']} has wrong label: {tab['label']}"
        
        print("PASS: All tab labels are correct")

    def test_tabs_have_groups(self):
        """Verify each tab contains groups array"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        tabs = data["config"]["navigation"]["tabs"]
        for tab in tabs:
            assert "groups" in tab, f"Tab '{tab['id']}' missing 'groups'"
            assert isinstance(tab["groups"], list), f"Tab '{tab['id']}' groups should be a list"
            if len(tab["groups"]) > 0:
                first_group = tab["groups"][0]
                assert "group" in first_group, f"Group missing 'group' label"
                assert "pages" in first_group, f"Group missing 'pages' array"
        
        print("PASS: All tabs have groups with correct structure")

    def test_tabs_have_icons(self):
        """Verify each tab has an icon field"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        tabs = data["config"]["navigation"]["tabs"]
        expected_icons = {
            "beginners-guide": "book-open",
            "features": "zap",
            "building-your-app": "code",
            "deploy-and-manage": "rocket",
            "troubleshooting": "wrench"
        }
        
        for tab in tabs:
            assert "icon" in tab, f"Tab '{tab['id']}' missing 'icon'"
            if tab["id"] in expected_icons:
                assert tab["icon"] == expected_icons[tab["id"]], f"Tab {tab['id']} has wrong icon"
        
        print("PASS: All tabs have correct icons")


class TestKBDocuments:
    """Test documents array in public-data response"""

    def test_documents_not_empty(self):
        """Verify documents array is not empty"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        documents = data.get("documents", [])
        assert len(documents) > 0, "Documents array is empty"
        print(f"PASS: Found {len(documents)} documents")

    def test_documents_structure(self):
        """Verify each document has required fields"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        documents = data.get("documents", [])
        required_fields = ["id", "slug", "title", "content"]
        
        for doc in documents[:5]:  # Check first 5 documents
            for field in required_fields:
                assert field in doc, f"Document {doc.get('slug', 'unknown')} missing '{field}'"
        
        print("PASS: Documents have correct structure")

    def test_welcome_article_exists(self):
        """Verify 'welcome' article exists and is the first in beginners-guide"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        # Find welcome in documents
        documents = data.get("documents", [])
        welcome_doc = next((d for d in documents if d["slug"] == "welcome"), None)
        assert welcome_doc is not None, "Welcome article not found"
        assert welcome_doc["title"] == "Welcome To Emergent", f"Welcome has wrong title: {welcome_doc['title']}"
        
        # Verify welcome is first in beginners-guide tab
        tabs = data["config"]["navigation"]["tabs"]
        beginners_tab = next((t for t in tabs if t["id"] == "beginners-guide"), None)
        assert beginners_tab is not None, "Beginners guide tab not found"
        
        first_group = beginners_tab["groups"][0] if beginners_tab["groups"] else None
        assert first_group is not None, "Beginners guide has no groups"
        
        first_page = first_group["pages"][0] if first_group["pages"] else None
        assert first_page is not None, "First group has no pages"
        assert first_page["page"] == "welcome", f"First page is not welcome: {first_page['page']}"
        
        print("PASS: Welcome article exists and is first in navigation")

    def test_documents_have_content(self):
        """Verify documents contain actual markdown content"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        documents = data.get("documents", [])
        for doc in documents[:3]:
            content = doc.get("content", "")
            assert len(content) > 0, f"Document {doc['slug']} has empty content"
            # Verify markdown-like content
            assert "#" in content or len(content) > 100, f"Document {doc['slug']} content seems invalid"
        
        print("PASS: Documents have content")


class TestKBNavbar:
    """Test navbar configuration in public-data response"""

    def test_navbar_has_links(self):
        """Verify navbar.links exists"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        navbar = data["config"].get("navbar", {})
        links = navbar.get("links", [])
        assert isinstance(links, list), "navbar.links should be a list"
        print(f"PASS: Found {len(links)} navbar links")

    def test_navbar_has_primary_cta(self):
        """Verify navbar.primary CTA exists"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        data = response.json()
        
        navbar = data["config"].get("navbar", {})
        primary = navbar.get("primary", {})
        
        assert "label" in primary, "Primary CTA missing label"
        assert "href" in primary, "Primary CTA missing href"
        assert "emergent" in primary["href"].lower(), f"Primary CTA href unexpected: {primary['href']}"
        
        print(f"PASS: Primary CTA: {primary['label']} -> {primary['href']}")


class TestKBOtherEndpoints:
    """Test other KB public endpoints for regression"""

    def test_navigation_endpoint(self):
        """GET /api/kb/navigation returns the nav tree under 'groups'"""
        response = requests.get(f"{BASE_URL}/api/kb/navigation")
        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        print(f"PASS: /api/kb/navigation returns {len(data['groups'])} groups")

    def test_articles_list(self):
        """GET /api/kb/articles returns published articles"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert len(data["articles"]) > 0
        # content_markdown should NOT be included in list
        if data["articles"]:
            assert "content_markdown" not in data["articles"][0], "List should not include content_markdown"
        print(f"PASS: /api/kb/articles returns {len(data['articles'])} articles")

    def test_article_by_slug(self):
        """GET /api/kb/articles/{slug} returns single article"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        data = response.json()
        assert "article" in data
        assert data["article"]["slug"] == "welcome"
        assert "prev" in data  # Should have prev navigation
        assert "next" in data  # Should have next navigation
        print("PASS: /api/kb/articles/welcome returns article with prev/next")

    def test_search_endpoint(self):
        """GET /api/kb/search?q=emergent returns results"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        # Should have some results for 'emergent'
        assert len(data["results"]) > 0, "Search should return results for 'emergent'"
        print(f"PASS: /api/kb/search returns {len(data['results'])} results for 'emergent'")


class TestPortalRegression:
    """Regression tests for portal endpoints"""

    def test_portal_categories(self):
        """GET /api/portal/categories returns 200"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200, f"Portal categories returned {response.status_code}"
        print("PASS: /api/portal/categories returns 200")


class TestLoginRegression:
    """Regression test for login endpoint"""

    def test_login_page_backend(self):
        """GET /api/users returns 401 without auth (login route exists)"""
        response = requests.get(f"{BASE_URL}/api/users")
        # Should require auth
        assert response.status_code in [401, 403], f"Users endpoint should require auth, got {response.status_code}"
        print("PASS: Protected endpoints require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
