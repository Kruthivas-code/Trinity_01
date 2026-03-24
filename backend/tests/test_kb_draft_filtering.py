"""
Test KB Editor Draft Filtering - Iteration 86
Tests for:
1. Draft pages (published=false) NOT returned by public endpoints
2. Draft pages returned by admin endpoints
3. Auto-save on slider close (published status persistence)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_kb_editor_session_2026"

# Test article slug for draft testing
TEST_DRAFT_SLUG = "test-draft-article-iter86"


class TestKBDraftFiltering:
    """Test that draft pages are filtered from public endpoints but visible in admin"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Create a test draft article"""
        self.session = requests.Session()
        self.session.cookies.set("session_token", SESSION_TOKEN)
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Create test draft article
        payload = {
            "title": "Test Draft Article Iter86",
            "slug": TEST_DRAFT_SLUG,
            "description": "Test draft article for iteration 86 testing",
            "content_markdown": "# Test Draft Content\n\nThis is a draft article.",
            "nav_group_key": "beginners-guide",
            "nav_group_label": "The Beginner's Guide",
            "section_key": "introduction",
            "section_label": "Introduction",
            "published": False,  # DRAFT
            "sidebar_title": "Draft Test",
            "keywords": ["test", "draft"],
            "tags": ["testing"]
        }
        
        # Delete if exists first
        self.session.delete(f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}")
        
        # Create the draft article
        response = self.session.post(f"{BASE_URL}/api/kb/admin/articles", json=payload)
        if response.status_code not in [200, 201]:
            print(f"Warning: Could not create test article: {response.status_code} - {response.text}")
        
        yield
        
        # Cleanup: Delete test article
        self.session.delete(f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}")
    
    def test_draft_not_in_public_articles_list(self):
        """Draft pages should NOT appear in public GET /api/kb/articles"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        articles = data.get("articles", [])
        
        # Check that our draft article is NOT in the list
        draft_found = any(a.get("slug") == TEST_DRAFT_SLUG for a in articles)
        assert not draft_found, f"Draft article '{TEST_DRAFT_SLUG}' should NOT appear in public articles list"
        print(f"PASS: Draft article not found in public articles list ({len(articles)} articles)")
    
    def test_draft_not_accessible_by_public_slug_endpoint(self):
        """Draft pages should return 404 from public GET /api/kb/articles/{slug}"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/{TEST_DRAFT_SLUG}")
        assert response.status_code == 404, f"Expected 404 for draft article, got {response.status_code}"
        print(f"PASS: Draft article returns 404 from public endpoint")
    
    def test_draft_not_in_public_data(self):
        """Draft pages should NOT appear in GET /api/kb/public-data"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        documents = data.get("documents", [])
        
        # Check that our draft article is NOT in documents
        draft_found = any(d.get("slug") == TEST_DRAFT_SLUG for d in documents)
        assert not draft_found, f"Draft article '{TEST_DRAFT_SLUG}' should NOT appear in public-data documents"
        print(f"PASS: Draft article not found in public-data ({len(documents)} documents)")
    
    def test_draft_visible_in_admin_articles_list(self):
        """Draft pages SHOULD appear in admin GET /api/kb/admin/articles"""
        response = self.session.get(f"{BASE_URL}/api/kb/admin/articles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        articles = data.get("articles", [])
        
        # Check that our draft article IS in the admin list
        draft_article = next((a for a in articles if a.get("slug") == TEST_DRAFT_SLUG), None)
        assert draft_article is not None, f"Draft article '{TEST_DRAFT_SLUG}' should appear in admin articles list"
        assert draft_article.get("published") == False, "Draft article should have published=False"
        print(f"PASS: Draft article found in admin articles list with published=False")
    
    def test_draft_accessible_by_admin_slug_endpoint(self):
        """Draft pages SHOULD be accessible from admin GET /api/kb/admin/articles/{slug}"""
        response = self.session.get(f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}")
        assert response.status_code == 200, f"Expected 200 for admin access to draft, got {response.status_code}"
        
        data = response.json()
        assert data.get("slug") == TEST_DRAFT_SLUG
        assert data.get("published") == False
        print(f"PASS: Draft article accessible via admin endpoint")
    
    def test_published_status_persistence(self):
        """Test that toggling published status persists correctly (simulates auto-save)"""
        # First verify it's unpublished
        response = self.session.get(f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}")
        assert response.status_code == 200
        assert response.json().get("published") == False
        
        # Toggle to published
        response = self.session.put(
            f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}",
            json={"published": True}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json().get("published") == True
        
        # Verify persistence by fetching again
        response = self.session.get(f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}")
        assert response.status_code == 200
        assert response.json().get("published") == True, "Published status should persist as True"
        print("PASS: Published=True persisted correctly")
        
        # Toggle back to draft
        response = self.session.put(
            f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}",
            json={"published": False}
        )
        assert response.status_code == 200
        assert response.json().get("published") == False
        
        # Verify persistence
        response = self.session.get(f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}")
        assert response.status_code == 200
        assert response.json().get("published") == False, "Published status should persist as False"
        print("PASS: Published=False persisted correctly")
    
    def test_published_article_appears_in_public(self):
        """When article is published, it should appear in public endpoints"""
        # Publish the article
        response = self.session.put(
            f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}",
            json={"published": True}
        )
        assert response.status_code == 200
        
        # Check public articles list
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        articles = response.json().get("articles", [])
        published_found = any(a.get("slug") == TEST_DRAFT_SLUG for a in articles)
        assert published_found, "Published article should appear in public articles list"
        print("PASS: Published article appears in public list")
        
        # Check public slug endpoint
        response = requests.get(f"{BASE_URL}/api/kb/articles/{TEST_DRAFT_SLUG}")
        assert response.status_code == 200, "Published article should be accessible via public endpoint"
        print("PASS: Published article accessible via public slug endpoint")
        
        # Check public-data
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        documents = response.json().get("documents", [])
        in_public_data = any(d.get("slug") == TEST_DRAFT_SLUG for d in documents)
        assert in_public_data, "Published article should appear in public-data"
        print("PASS: Published article appears in public-data")
        
        # Unpublish again for cleanup
        self.session.put(
            f"{BASE_URL}/api/kb/admin/articles/{TEST_DRAFT_SLUG}",
            json={"published": False}
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
