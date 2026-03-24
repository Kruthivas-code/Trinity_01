"""
Test KB Editor Redesign Backend APIs
Tests for new fields: sidebar_title, keywords, tags
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_kb_editor_session_2026"


@pytest.fixture
def auth_session():
    """Create authenticated session with cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestKBAdminArticles:
    """Test KB Admin Article endpoints with new fields"""
    
    def test_get_admin_articles_list(self, auth_session):
        """Test GET /api/kb/admin/articles returns articles"""
        response = auth_session.get(f"{BASE_URL}/api/kb/admin/articles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "articles" in data
        assert "nav_groups" in data
        assert len(data["articles"]) > 0, "Expected at least one article"
        print(f"Found {len(data['articles'])} articles")
    
    def test_get_single_article(self, auth_session):
        """Test GET /api/kb/admin/articles/{slug} returns article with all fields"""
        response = auth_session.get(f"{BASE_URL}/api/kb/admin/articles/welcome")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        article = response.json()
        assert "title" in article
        assert "slug" in article
        assert "content_markdown" in article
        print(f"Article title: {article['title']}")
    
    def test_create_article_with_new_fields(self, auth_session):
        """Test POST /api/kb/admin/articles with sidebar_title, keywords, tags"""
        unique_id = uuid.uuid4().hex[:8]
        test_slug = f"TEST_article_{unique_id}"
        
        payload = {
            "title": f"Test Article {unique_id}",
            "slug": test_slug,
            "description": "Test description",
            "content_markdown": "# Test Content\n\nThis is test content.",
            "nav_group_key": "beginners-guide",
            "nav_group_label": "The Beginner's Guide",
            "section_key": "introduction",
            "section_label": "Introduction",
            "published": False,
            "order": 999,
            "sidebar_title": f"Sidebar Title {unique_id}",
            "keywords": ["test", "keyword1", "keyword2"],
            "tags": ["tag1", "tag2"]
        }
        
        response = auth_session.post(f"{BASE_URL}/api/kb/admin/articles", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        created = response.json()
        assert created["slug"] == test_slug
        assert created["sidebar_title"] == payload["sidebar_title"]
        assert created["keywords"] == payload["keywords"]
        assert created["tags"] == payload["tags"]
        print(f"Created article with slug: {test_slug}")
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/kb/admin/articles/{test_slug}")
    
    def test_update_article_with_new_fields(self, auth_session):
        """Test PUT /api/kb/admin/articles/{slug} updates sidebar_title, keywords, tags"""
        unique_id = uuid.uuid4().hex[:8]
        test_slug = f"TEST_update_{unique_id}"
        
        # Create article first
        create_payload = {
            "title": f"Update Test {unique_id}",
            "slug": test_slug,
            "description": "Initial description",
            "content_markdown": "Initial content",
            "nav_group_key": "beginners-guide",
            "nav_group_label": "The Beginner's Guide",
            "section_key": "introduction",
            "section_label": "Introduction",
            "published": False,
            "sidebar_title": "Initial Sidebar",
            "keywords": ["initial"],
            "tags": ["initial-tag"]
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/kb/admin/articles", json=create_payload)
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        
        # Update with new values
        update_payload = {
            "sidebar_title": "Updated Sidebar Title",
            "keywords": ["updated", "new-keyword"],
            "tags": ["updated-tag", "new-tag"]
        }
        
        update_resp = auth_session.put(f"{BASE_URL}/api/kb/admin/articles/{test_slug}", json=update_payload)
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        
        updated = update_resp.json()
        assert updated["sidebar_title"] == "Updated Sidebar Title"
        assert updated["keywords"] == ["updated", "new-keyword"]
        assert updated["tags"] == ["updated-tag", "new-tag"]
        print(f"Updated article fields successfully")
        
        # Verify with GET
        get_resp = auth_session.get(f"{BASE_URL}/api/kb/admin/articles/{test_slug}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["sidebar_title"] == "Updated Sidebar Title"
        assert fetched["keywords"] == ["updated", "new-keyword"]
        assert fetched["tags"] == ["updated-tag", "new-tag"]
        print("Verified updated fields persist correctly")
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/kb/admin/articles/{test_slug}")
    
    def test_delete_article(self, auth_session):
        """Test DELETE /api/kb/admin/articles/{slug}"""
        unique_id = uuid.uuid4().hex[:8]
        test_slug = f"TEST_delete_{unique_id}"
        
        # Create article
        create_payload = {
            "title": f"Delete Test {unique_id}",
            "slug": test_slug,
            "description": "To be deleted",
            "content_markdown": "Delete me",
            "nav_group_key": "beginners-guide",
            "nav_group_label": "The Beginner's Guide",
            "section_key": "introduction",
            "section_label": "Introduction",
            "published": False
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/kb/admin/articles", json=create_payload)
        assert create_resp.status_code == 200
        
        # Delete
        delete_resp = auth_session.delete(f"{BASE_URL}/api/kb/admin/articles/{test_slug}")
        assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.text}"
        
        # Verify deleted
        get_resp = auth_session.get(f"{BASE_URL}/api/kb/admin/articles/{test_slug}")
        assert get_resp.status_code == 404, "Article should be deleted"
        print(f"Article {test_slug} deleted successfully")
    
    def test_update_published_status(self, auth_session):
        """Test updating published status (for Draft tag feature)"""
        unique_id = uuid.uuid4().hex[:8]
        test_slug = f"TEST_publish_{unique_id}"
        
        # Create unpublished article
        create_payload = {
            "title": f"Publish Test {unique_id}",
            "slug": test_slug,
            "description": "Test publishing",
            "content_markdown": "Content",
            "nav_group_key": "beginners-guide",
            "nav_group_label": "The Beginner's Guide",
            "section_key": "introduction",
            "section_label": "Introduction",
            "published": False
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/kb/admin/articles", json=create_payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert created["published"] == False, "Should be unpublished initially"
        
        # Update to published
        update_resp = auth_session.put(f"{BASE_URL}/api/kb/admin/articles/{test_slug}", json={"published": True})
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["published"] == True, "Should be published after update"
        print("Published status updated successfully")
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/kb/admin/articles/{test_slug}")


class TestKBNavigation:
    """Test KB Navigation endpoints"""
    
    def test_get_navigation(self, auth_session):
        """Test GET /api/kb/navigation returns nav groups"""
        response = auth_session.get(f"{BASE_URL}/api/kb/navigation")
        assert response.status_code == 200
        
        data = response.json()
        assert "nav_groups" in data
        assert len(data["nav_groups"]) > 0, "Expected at least one nav group"
        print(f"Found {len(data['nav_groups'])} navigation groups")
    
    def test_update_navigation(self, auth_session):
        """Test PUT /api/kb/admin/navigation"""
        # Get current navigation
        get_resp = auth_session.get(f"{BASE_URL}/api/kb/navigation")
        assert get_resp.status_code == 200
        current_nav = get_resp.json()["nav_groups"]
        
        # Update navigation (just re-save the same)
        update_resp = auth_session.put(
            f"{BASE_URL}/api/kb/admin/navigation",
            json={"nav_groups": current_nav}
        )
        assert update_resp.status_code == 200
        print("Navigation update successful")


class TestKBPublicEndpoints:
    """Test public KB endpoints (no auth required)"""
    
    def test_public_articles_list(self):
        """Test GET /api/kb/articles (public)"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        
        data = response.json()
        assert "articles" in data
        # All returned articles should be published
        for article in data["articles"]:
            assert article.get("published", True) == True or "published" not in article
        print(f"Found {len(data['articles'])} published articles")
    
    def test_public_article_detail(self):
        """Test GET /api/kb/articles/{slug} (public)"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        
        data = response.json()
        assert "article" in data
        assert data["article"]["slug"] == "welcome"
        print(f"Public article: {data['article']['title']}")
    
    def test_public_data_endpoint(self):
        """Test GET /api/kb/public-data (for docs frontend)"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        
        data = response.json()
        assert "project" in data
        assert "config" in data
        assert "documents" in data
        print(f"Public data: {len(data['documents'])} documents")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
