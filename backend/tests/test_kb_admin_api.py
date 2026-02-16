"""
KB Admin API Tests
Tests for admin-only KB article management endpoints:
- GET /api/kb/admin/articles - List all articles with content
- POST /api/kb/admin/articles - Create new article
- PUT /api/kb/admin/articles/{slug} - Update article
- DELETE /api/kb/admin/articles/{slug} - Delete article
- PUT /api/kb/admin/navigation - Update navigation structure
"""
import pytest
import requests
import os
import secrets
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Generate a session token for testing
def get_admin_session():
    """Create admin session for testing"""
    import sys
    sys.path.insert(0, '/app/backend')
    from database import users_collection, sessions_collection
    
    user = users_collection.find_one({}, {'_id': 0, 'user_id': 1})
    if not user:
        pytest.skip("No user found in database")
    
    token = secrets.token_urlsafe(32)
    sessions_collection.insert_one({
        'session_token': token,
        'user_id': user['user_id'],
        'created_at': datetime.now(timezone.utc),
        'expires_at': datetime.now(timezone.utc) + timedelta(days=1)
    })
    return token

@pytest.fixture(scope="module")
def admin_session():
    """Session token fixture"""
    token = get_admin_session()
    yield token
    # Cleanup session after tests
    import sys
    sys.path.insert(0, '/app/backend')
    from database import sessions_collection
    sessions_collection.delete_one({'session_token': token})

@pytest.fixture
def api_client(admin_session):
    """API client with auth"""
    session = requests.Session()
    session.cookies.set('session_token', admin_session)
    session.headers.update({'Content-Type': 'application/json'})
    return session


class TestAdminArticlesEndpoint:
    """Test GET /api/kb/admin/articles"""
    
    def test_admin_articles_requires_auth(self):
        """Admin articles endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/kb/admin/articles")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Admin articles returns 401 without auth")
    
    def test_admin_articles_with_auth(self, api_client):
        """Admin articles returns full article list with content"""
        response = api_client.get(f"{BASE_URL}/api/kb/admin/articles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'articles' in data, "Response should contain 'articles'"
        assert 'nav_groups' in data, "Response should contain 'nav_groups'"
        
        articles = data['articles']
        assert len(articles) >= 21, f"Expected at least 21 articles, got {len(articles)}"
        
        # Verify content_markdown is included (unlike public endpoint)
        if articles:
            first_article = articles[0]
            assert 'content_markdown' in first_article, "Admin endpoint should include content_markdown"
            assert 'title' in first_article
            assert 'slug' in first_article
            assert 'published' in first_article
        
        print(f"✓ Admin articles returns {len(articles)} articles with content")
    
    def test_admin_articles_includes_nav_groups(self, api_client):
        """Admin articles includes navigation groups"""
        response = api_client.get(f"{BASE_URL}/api/kb/admin/articles")
        assert response.status_code == 200
        
        data = response.json()
        nav_groups = data.get('nav_groups', [])
        assert len(nav_groups) >= 5, f"Expected at least 5 nav groups, got {len(nav_groups)}"
        
        # Verify nav group structure
        for group in nav_groups:
            assert 'key' in group
            assert 'label' in group
            assert 'sections' in group
        
        print(f"✓ Admin articles includes {len(nav_groups)} nav groups")


class TestArticleCRUD:
    """Test article Create, Update, Delete operations"""
    
    def test_create_article(self, api_client):
        """Create a new article via POST"""
        payload = {
            "title": "TEST_PyTest Article",
            "slug": "test-pytest-article",
            "section_key": "introduction",
            "section_label": "Introduction",
            "nav_group_key": "beginners-guide",
            "nav_group_label": "The Beginner's Guide",
            "content_markdown": "# Test\n\nThis is a pytest test article.",
            "published": True,
            "order": 999
        }
        
        response = api_client.post(f"{BASE_URL}/api/kb/admin/articles", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['title'] == payload['title']
        assert data['slug'] == payload['slug']
        assert data['content_markdown'] == payload['content_markdown']
        assert data['published'] == True
        assert 'created_at' in data
        
        print("✓ Article created successfully")
    
    def test_create_duplicate_slug_rejected(self, api_client):
        """Duplicate slug should return 409"""
        payload = {
            "title": "Duplicate Test",
            "slug": "test-pytest-article",  # Same slug as above
            "section_key": "introduction",
            "section_label": "Introduction",
            "nav_group_key": "beginners-guide",
            "nav_group_label": "The Beginner's Guide",
            "content_markdown": "Test",
            "published": True,
            "order": 1000
        }
        
        response = api_client.post(f"{BASE_URL}/api/kb/admin/articles", json=payload)
        assert response.status_code == 409, f"Expected 409 for duplicate slug, got {response.status_code}"
        
        data = response.json()
        assert 'detail' in data
        assert 'exists' in data['detail'].lower()
        
        print("✓ Duplicate slug correctly rejected with 409")
    
    def test_update_article_title_and_content(self, api_client):
        """Update article title and content via PUT"""
        update_payload = {
            "title": "TEST_PyTest Article UPDATED",
            "content_markdown": "# Updated\n\nContent has been updated."
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/test-pytest-article",
            json=update_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['title'] == update_payload['title']
        assert data['content_markdown'] == update_payload['content_markdown']
        assert 'updated_at' in data
        
        print("✓ Article title and content updated")
    
    def test_update_article_slug_rename(self, api_client):
        """Rename article slug via PUT"""
        update_payload = {"slug": "test-pytest-article-renamed"}
        
        response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/test-pytest-article",
            json=update_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data['slug'] == "test-pytest-article-renamed"
        
        # Verify old slug no longer exists
        old_response = api_client.get(f"{BASE_URL}/api/kb/articles/test-pytest-article")
        assert old_response.status_code == 404, "Old slug should return 404"
        
        print("✓ Article slug renamed successfully")
    
    def test_toggle_published_status(self, api_client):
        """Toggle published status via PUT"""
        # Set to unpublished
        response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/test-pytest-article-renamed",
            json={"published": False}
        )
        assert response.status_code == 200
        assert response.json()['published'] == False
        
        # Verify not in public listing
        public_response = requests.get(f"{BASE_URL}/api/kb/articles")
        public_articles = public_response.json().get('articles', [])
        slugs = [a['slug'] for a in public_articles]
        assert "test-pytest-article-renamed" not in slugs, "Unpublished article should not appear in public"
        
        # Toggle back to published
        response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/test-pytest-article-renamed",
            json={"published": True}
        )
        assert response.status_code == 200
        assert response.json()['published'] == True
        
        print("✓ Published status toggle works")
    
    def test_update_nonexistent_article_returns_404(self, api_client):
        """Update non-existent article returns 404"""
        response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/nonexistent-slug-xyz-123",
            json={"title": "Not Found"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent article returns 404")
    
    def test_delete_article(self, api_client):
        """Delete article via DELETE"""
        response = api_client.delete(f"{BASE_URL}/api/kb/admin/articles/test-pytest-article-renamed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'message' in data
        
        # Verify article is gone
        verify_response = api_client.get(f"{BASE_URL}/api/kb/admin/articles")
        articles = verify_response.json().get('articles', [])
        slugs = [a['slug'] for a in articles]
        assert "test-pytest-article-renamed" not in slugs, "Deleted article should not appear"
        
        print("✓ Article deleted successfully")


class TestNavigationUpdate:
    """Test PUT /api/kb/admin/navigation"""
    
    def test_update_navigation_structure(self, api_client):
        """Update navigation structure"""
        # Get current navigation
        current_response = api_client.get(f"{BASE_URL}/api/kb/admin/articles")
        current_nav = current_response.json().get('nav_groups', [])
        
        # Update with modified structure (add test group)
        modified_nav = current_nav.copy()
        
        response = api_client.put(
            f"{BASE_URL}/api/kb/admin/navigation",
            json={"nav_groups": modified_nav}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'nav_groups' in data
        
        print("✓ Navigation structure updated")


class TestPublicAPIRegression:
    """Verify public API still works correctly"""
    
    def test_public_articles_excludes_content(self):
        """Public articles endpoint excludes content_markdown"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        
        data = response.json()
        articles = data.get('articles', [])
        
        if articles:
            first_article = articles[0]
            assert 'content_markdown' not in first_article, "Public endpoint should NOT include content_markdown"
            assert 'title' in first_article
            assert 'slug' in first_article
        
        print(f"✓ Public API returns {len(articles)} articles without content_markdown")
    
    def test_public_articles_only_published(self):
        """Public API returns only published articles"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        
        articles = response.json().get('articles', [])
        for article in articles:
            assert article.get('published', True) == True, f"Article {article['slug']} should be published"
        
        print("✓ Public API returns only published articles")
    
    def test_public_navigation_works(self):
        """Public navigation endpoint works"""
        response = requests.get(f"{BASE_URL}/api/kb/navigation")
        assert response.status_code == 200
        
        data = response.json()
        nav_groups = data.get('nav_groups', [])
        assert len(nav_groups) >= 1, "Should have at least 1 nav group"
        
        print(f"✓ Public navigation returns {len(nav_groups)} groups")
    
    def test_public_article_detail_with_prev_next(self):
        """Public article detail includes prev/next"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        
        data = response.json()
        assert 'article' in data
        assert 'prev' in data
        assert 'next' in data
        assert 'content_markdown' in data['article'], "Article detail should include content_markdown"
        
        print("✓ Public article detail works with prev/next navigation")
    
    def test_search_works(self):
        """Search endpoint works"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get('results', [])
        assert len(results) > 0, "Search for 'emergent' should return results"
        
        print(f"✓ Search returns {len(results)} results for 'emergent'")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
