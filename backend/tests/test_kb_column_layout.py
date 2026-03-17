"""
Test KB API for ColumnLayout feature.
Tests backward compatibility with old Columns and new ColumnLayout markdown.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://backend-refresh-3.preview.emergentagent.com').rstrip('/')
SESSION_TOKEN = 'test_kb_session_token'


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


class TestKBPublicDocs:
    """Tests for public KB docs API endpoints."""

    def test_get_public_article_col_layout_test(self, api_client):
        """GET /api/kb/articles/col-layout-test returns article with ColumnLayout content."""
        response = api_client.get(f"{BASE_URL}/api/kb/articles/col-layout-test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "article" in data, "Response should contain 'article' key"
        article = data["article"]
        
        assert article["slug"] == "col-layout-test"
        assert article["title"] == "Column Layout Test"
        assert article["published"] is True
        
        # Verify ColumnLayout markdown is present
        content = article.get("content_markdown", "")
        assert "<ColumnLayout" in content, "Content should contain ColumnLayout tag"
        assert "<Col>" in content, "Content should contain Col tags"
        assert "</ColumnLayout>" in content, "Content should have closing ColumnLayout tag"

    def test_get_public_article_welcome_has_old_columns(self, api_client):
        """GET /api/kb/articles/welcome returns article with old Columns content."""
        response = api_client.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "article" in data, "Response should contain 'article' key"
        article = data["article"]
        
        assert article["slug"] == "welcome"
        # Verify old Columns markdown is present
        content = article.get("content_markdown", "")
        assert "<Columns" in content, "Content should contain old Columns tag"
        assert "<Card" in content, "Content should contain Card tags inside Columns"

    def test_get_public_data_includes_col_layout_test(self, api_client):
        """GET /api/kb/public-data includes col-layout-test document."""
        response = api_client.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "documents" in data, "Response should contain 'documents' key"
        
        doc_slugs = [d["slug"] for d in data["documents"]]
        assert "col-layout-test" in doc_slugs, "col-layout-test should be in documents"
        
        # Find the document and verify content
        col_layout_doc = next((d for d in data["documents"] if d["slug"] == "col-layout-test"), None)
        assert col_layout_doc is not None
        assert "<ColumnLayout" in col_layout_doc.get("content", ""), "Document content should have ColumnLayout"


class TestKBAdminAPI:
    """Tests for admin KB API endpoints requiring authentication."""

    def test_admin_get_article_col_layout_test(self, api_client):
        """GET /api/kb/admin/articles/col-layout-test returns full article with ColumnLayout."""
        response = api_client.get(f"{BASE_URL}/api/kb/admin/articles/col-layout-test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        article = response.json()
        
        assert article["slug"] == "col-layout-test"
        assert article["title"] == "Column Layout Test"
        
        # Verify full ColumnLayout markdown content
        content = article.get("content_markdown", "")
        assert "<ColumnLayout cols={2}>" in content, "Content should have ColumnLayout cols={2}"
        assert "<Col>" in content, "Content should have Col tags"
        assert "### Left" in content, "Content should have Left heading"
        assert "### Right" in content, "Content should have Right heading"
        
        # Verify old Columns are also present
        assert "<Columns cols={2}>" in content, "Content should have old Columns cols={2}"
        assert 'title="Card"' in content, "Content should have Card with title"
        assert 'icon="rocket"' in content, "Content should have rocket icon"

    def test_admin_get_article_welcome(self, api_client):
        """GET /api/kb/admin/articles/welcome returns article with old Columns."""
        response = api_client.get(f"{BASE_URL}/api/kb/admin/articles/welcome")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        article = response.json()
        
        assert article["slug"] == "welcome"
        content = article.get("content_markdown", "")
        assert "<Columns" in content, "Welcome article should have old Columns"

    def test_admin_list_articles_includes_col_layout_test(self, api_client):
        """GET /api/kb/admin/articles lists col-layout-test."""
        response = api_client.get(f"{BASE_URL}/api/kb/admin/articles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "articles" in data
        
        article_slugs = [a["slug"] for a in data["articles"]]
        assert "col-layout-test" in article_slugs
        assert "welcome" in article_slugs

    def test_admin_update_article_col_layout_preserves_content(self, api_client):
        """PUT /api/kb/admin/articles/col-layout-test can update and preserve ColumnLayout."""
        # First get the current article
        get_response = api_client.get(f"{BASE_URL}/api/kb/admin/articles/col-layout-test")
        assert get_response.status_code == 200
        original_article = get_response.json()
        original_content = original_article.get("content_markdown", "")
        
        # Update with modified content (add a test line)
        test_marker = "\n\n<!-- TEST_MARKER -->"
        updated_content = original_content + test_marker
        
        update_response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/col-layout-test",
            json={"content_markdown": updated_content}
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.status_code}"
        
        # Verify the update persisted
        verify_response = api_client.get(f"{BASE_URL}/api/kb/admin/articles/col-layout-test")
        assert verify_response.status_code == 200
        verified_article = verify_response.json()
        verified_content = verified_article.get("content_markdown", "")
        
        # Check content was preserved
        assert "<ColumnLayout cols={2}>" in verified_content
        assert "<Col>" in verified_content
        assert "<!-- TEST_MARKER -->" in verified_content
        
        # Clean up - restore original content
        cleanup_response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/col-layout-test",
            json={"content_markdown": original_content}
        )
        assert cleanup_response.status_code == 200


class TestKBSearchAPI:
    """Tests for KB search API."""

    def test_search_finds_col_layout_test(self, api_client):
        """GET /api/kb/search?q=Column Layout returns col-layout-test."""
        response = api_client.get(f"{BASE_URL}/api/kb/search?q=Column Layout")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        
        result_slugs = [r["slug"] for r in data["results"]]
        assert "col-layout-test" in result_slugs, "Search should find col-layout-test article"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
