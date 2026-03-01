"""
KB Admin API Performance Tests
Tests lazy loading behavior - list endpoint excludes content_markdown,
individual article endpoint returns full content.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_COOKIE = "session_token=test_kb_session_token"


class TestKBAdminPerformance:
    """Tests for KB admin article endpoints - performance optimization (lazy loading)"""

    def test_admin_list_articles_excludes_content_markdown(self):
        """GET /api/kb/admin/articles should NOT include content_markdown field for performance"""
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers={"Cookie": SESSION_COOKIE}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "articles" in data, "Response should have 'articles' key"
        assert len(data["articles"]) > 0, "Should have at least one article"
        
        # Check that NO article in the list has content_markdown
        for article in data["articles"]:
            assert "content_markdown" not in article, \
                f"Article '{article.get('slug')}' should NOT have content_markdown in listing"
            # Verify other essential fields ARE present
            assert "slug" in article, "Article should have 'slug'"
            assert "title" in article, "Article should have 'title'"
        
        print(f"SUCCESS: {len(data['articles'])} articles returned without content_markdown")

    def test_admin_get_single_article_includes_content_markdown(self):
        """GET /api/kb/admin/articles/{slug} should return full article including content_markdown"""
        # First get an article slug from the list
        list_response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers={"Cookie": SESSION_COOKIE}
        )
        assert list_response.status_code == 200
        articles = list_response.json().get("articles", [])
        assert len(articles) > 0, "Need at least one article to test"
        
        test_slug = "welcome"  # Use welcome article which has cards
        
        # Now fetch the full article
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles/{test_slug}",
            headers={"Cookie": SESSION_COOKIE}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "slug" in data, "Response should have 'slug'"
        assert data["slug"] == test_slug, f"Expected slug '{test_slug}'"
        assert "content_markdown" in data, "Single article response SHOULD have content_markdown"
        assert len(data["content_markdown"]) > 0, "content_markdown should not be empty"
        
        print(f"SUCCESS: Article '{test_slug}' returned with content_markdown ({len(data['content_markdown'])} chars)")

    def test_admin_get_nonexistent_article_returns_404(self):
        """GET /api/kb/admin/articles/{slug} should return 404 for non-existent slug"""
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles/nonexistent-article-slug-12345",
            headers={"Cookie": SESSION_COOKIE}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Non-existent article returns 404")

    def test_admin_list_includes_feedback_stats(self):
        """GET /api/kb/admin/articles should include feedback stats for each article"""
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers={"Cookie": SESSION_COOKIE}
        )
        assert response.status_code == 200
        
        data = response.json()
        articles = data.get("articles", [])
        assert len(articles) > 0, "Need articles to test"
        
        # Check first article has feedback fields
        article = articles[0]
        assert "feedback_total" in article, "Article should have feedback_total"
        assert "feedback_helpful" in article, "Article should have feedback_helpful"
        
        print(f"SUCCESS: Articles include feedback stats")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
