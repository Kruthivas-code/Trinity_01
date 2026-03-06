"""
Test Portal KB Integration APIs
Tests for kb_group_key field, admin kb-nav-groups and kb-articles-list endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://atlas-first-sync.preview.emergentagent.com')
ADMIN_SESSION_TOKEN = "test_kb_session_token"


class TestPortalCategoriesPublic:
    """Test public portal category endpoints for kb_group_key field"""
    
    def test_get_categories_returns_kb_group_key(self):
        """GET /api/portal/categories returns categories with kb_group_key field"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0
        
        # Check that categories have kb_group_key field
        for cat in data["categories"]:
            assert "kb_group_key" in cat, f"Category {cat.get('slug')} missing kb_group_key field"
    
    def test_credits_pricing_has_beginners_guide_kb_group(self):
        """credits-pricing category should have kb_group_key='beginners-guide'"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200
        data = response.json()
        
        credits_pricing = next(
            (cat for cat in data["categories"] if cat["slug"] == "credits-pricing"),
            None
        )
        assert credits_pricing is not None, "credits-pricing category not found"
        assert credits_pricing["kb_group_key"] == "beginners-guide", \
            f"Expected kb_group_key='beginners-guide', got '{credits_pricing.get('kb_group_key')}'"
    
    def test_get_single_category_returns_kb_group_key(self):
        """GET /api/portal/categories/credits-pricing returns category with kb_group_key"""
        response = requests.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        assert response.status_code == 200
        data = response.json()
        
        assert "kb_group_key" in data
        assert data["kb_group_key"] == "beginners-guide"
        assert data["title"] == "Credits & Pricing"


class TestPortalHelpTopics:
    """Test GET /api/portal/help-topics endpoint"""
    
    def test_help_topics_returns_icon_and_description(self):
        """GET /api/portal/help-topics returns topics with icon and description fields"""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics")
        assert response.status_code == 200
        data = response.json()
        
        assert "topics" in data
        assert len(data["topics"]) >= 5, "Expected at least 5 KB nav groups"
        
        # Check that each topic has icon and description
        for topic in data["topics"]:
            assert "key" in topic
            assert "label" in topic
            assert "icon" in topic, f"Topic {topic['key']} missing icon field"
            assert "description" in topic, f"Topic {topic['key']} missing description field"
            assert topic["icon"], f"Topic {topic['key']} has empty icon"
            assert topic["description"], f"Topic {topic['key']} has empty description"
    
    def test_help_topics_has_expected_kb_groups(self):
        """Help topics should include all expected KB navigation groups"""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics")
        assert response.status_code == 200
        data = response.json()
        
        expected_groups = ["beginners-guide", "features", "building-your-app", 
                          "deploy-and-manage", "troubleshooting"]
        topic_keys = [t["key"] for t in data["topics"]]
        
        for group_key in expected_groups:
            assert group_key in topic_keys, f"Expected KB group '{group_key}' not found in help topics"


class TestPortalAdminKBEndpoints:
    """Test admin KB endpoints requiring authentication"""
    
    @pytest.fixture
    def admin_session(self):
        """Session with admin auth cookie"""
        session = requests.Session()
        session.cookies.set("session_token", ADMIN_SESSION_TOKEN)
        return session
    
    def test_kb_nav_groups_returns_5_groups(self, admin_session):
        """GET /api/portal/admin/kb-nav-groups returns list of 5 KB nav groups"""
        response = admin_session.get(f"{BASE_URL}/api/portal/admin/kb-nav-groups")
        assert response.status_code == 200
        data = response.json()
        
        assert "nav_groups" in data
        assert len(data["nav_groups"]) == 5, f"Expected 5 nav groups, got {len(data['nav_groups'])}"
        
        # Verify each group has key and label
        for group in data["nav_groups"]:
            assert "key" in group, "Nav group missing 'key' field"
            assert "label" in group, "Nav group missing 'label' field"
    
    def test_kb_nav_groups_contains_expected_keys(self, admin_session):
        """KB nav groups should contain all expected keys"""
        response = admin_session.get(f"{BASE_URL}/api/portal/admin/kb-nav-groups")
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = ["beginners-guide", "features", "building-your-app",
                        "deploy-and-manage", "troubleshooting"]
        actual_keys = [g["key"] for g in data["nav_groups"]]
        
        for key in expected_keys:
            assert key in actual_keys, f"Expected nav group key '{key}' not found"
    
    def test_kb_nav_groups_unauthorized_without_auth(self):
        """GET /api/portal/admin/kb-nav-groups should require authentication"""
        response = requests.get(f"{BASE_URL}/api/portal/admin/kb-nav-groups")
        assert response.status_code == 401
    
    def test_kb_articles_list_returns_published_articles(self, admin_session):
        """GET /api/portal/admin/kb-articles-list returns published KB articles"""
        response = admin_session.get(f"{BASE_URL}/api/portal/admin/kb-articles-list")
        assert response.status_code == 200
        data = response.json()
        
        assert "articles" in data
        assert len(data["articles"]) > 0, "Expected at least one KB article"
        
        # Verify each article has slug and title
        for article in data["articles"]:
            assert "slug" in article, "Article missing 'slug' field"
            assert "title" in article, "Article missing 'title' field"
    
    def test_kb_articles_list_unauthorized_without_auth(self):
        """GET /api/portal/admin/kb-articles-list should require authentication"""
        response = requests.get(f"{BASE_URL}/api/portal/admin/kb-articles-list")
        assert response.status_code == 401


class TestPortalAdminCategoryKBField:
    """Test admin category endpoints for kb_group_key field"""
    
    @pytest.fixture
    def admin_session(self):
        """Session with admin auth cookie"""
        session = requests.Session()
        session.cookies.set("session_token", ADMIN_SESSION_TOKEN)
        return session
    
    @pytest.fixture
    def test_category_slug(self):
        """Generate unique test category slug"""
        return f"test-kb-{uuid.uuid4().hex[:8]}"
    
    def test_create_category_with_kb_group_key(self, admin_session, test_category_slug):
        """POST /api/portal/admin/categories creates category with kb_group_key"""
        payload = {
            "title": "TEST KB Category",
            "slug": test_category_slug,
            "description": "Test category with KB group",
            "icon": "HelpCircle",
            "kb_group_key": "features"
        }
        
        response = admin_session.post(
            f"{BASE_URL}/api/portal/admin/categories",
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["kb_group_key"] == "features"
        assert data["slug"] == test_category_slug
        
        # Clean up
        admin_session.delete(f"{BASE_URL}/api/portal/admin/categories/{test_category_slug}")
    
    def test_update_category_kb_group_key(self, admin_session, test_category_slug):
        """PUT /api/portal/admin/categories/{slug} updates kb_group_key field"""
        # First create the category
        create_payload = {
            "title": "TEST Update KB Category",
            "slug": test_category_slug,
            "description": "Test update",
            "kb_group_key": "beginners-guide"
        }
        create_response = admin_session.post(
            f"{BASE_URL}/api/portal/admin/categories",
            json=create_payload
        )
        assert create_response.status_code == 200
        
        # Update kb_group_key
        update_payload = {"kb_group_key": "troubleshooting"}
        update_response = admin_session.put(
            f"{BASE_URL}/api/portal/admin/categories/{test_category_slug}",
            json=update_payload
        )
        assert update_response.status_code == 200
        data = update_response.json()
        
        assert data["kb_group_key"] == "troubleshooting"
        
        # Verify via GET
        get_response = requests.get(f"{BASE_URL}/api/portal/categories/{test_category_slug}")
        assert get_response.status_code == 200
        assert get_response.json()["kb_group_key"] == "troubleshooting"
        
        # Clean up
        admin_session.delete(f"{BASE_URL}/api/portal/admin/categories/{test_category_slug}")
    
    def test_update_existing_category_kb_group_key(self, admin_session):
        """PUT /api/portal/admin/categories/columns-rebuild updates kb_group_key if exists"""
        # Test on an existing category - let's use credits-pricing
        # First get current state
        get_response = requests.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        original_kb_group = get_response.json().get("kb_group_key")
        
        # Update to a different value
        new_value = "features" if original_kb_group != "features" else "troubleshooting"
        update_response = admin_session.put(
            f"{BASE_URL}/api/portal/admin/categories/credits-pricing",
            json={"kb_group_key": new_value}
        )
        assert update_response.status_code == 200
        assert update_response.json()["kb_group_key"] == new_value
        
        # Restore original value
        admin_session.put(
            f"{BASE_URL}/api/portal/admin/categories/credits-pricing",
            json={"kb_group_key": original_kb_group}
        )
