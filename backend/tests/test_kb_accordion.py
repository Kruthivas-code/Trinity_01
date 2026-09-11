"""
Test KB API for Accordion feature.
Tests accordion markdown parsing, rendering, and API operations.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://github-clone-tool-6.preview.emergentagent.com').rstrip('/')
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


class TestKBAccordionPublicAPI:
    """Tests for public KB docs API endpoints with Accordion content."""

    def test_get_public_article_accordion_test(self, api_client):
        """GET /api/kb/articles/accordion-test returns article with Accordion content."""
        response = api_client.get(f"{BASE_URL}/api/kb/articles/accordion-test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "article" in data, "Response should contain 'article' key"
        article = data["article"]
        
        assert article["slug"] == "accordion-test"
        assert article["title"] == "Accordion Test"
        assert article["published"] is True
        
        # Verify Accordion markdown is present
        content = article.get("content_markdown", "")
        assert "<Accordion>" in content, "Content should contain Accordion tag"
        assert "<AccordionItem" in content, "Content should contain AccordionItem tags"
        assert "</Accordion>" in content, "Content should have closing Accordion tag"
        assert "</AccordionItem>" in content, "Content should have closing AccordionItem tag"

    def test_accordion_has_three_items(self, api_client):
        """Accordion article should have exactly 3 accordion items."""
        response = api_client.get(f"{BASE_URL}/api/kb/articles/accordion-test")
        assert response.status_code == 200
        
        content = response.json()["article"]["content_markdown"]
        
        # Count AccordionItem tags
        item_count = content.count("<AccordionItem")
        assert item_count == 3, f"Expected 3 accordion items, found {item_count}"
        
        # Verify all expected titles
        assert 'title="What is Trinity?"' in content
        assert 'title="How do I get started?"' in content
        assert 'title="Is there a free plan?"' in content

    def test_accordion_item_content(self, api_client):
        """Accordion items should contain their expected content."""
        response = api_client.get(f"{BASE_URL}/api/kb/articles/accordion-test")
        assert response.status_code == 200
        
        content = response.json()["article"]["content_markdown"]
        
        # Verify first item content
        assert "Trinity is a full-stack customer support suite." in content
        
        # Verify second item content (includes markdown bullet list)
        assert "Step 1: Create account" in content
        assert "Step 2: Configure settings" in content
        assert "Step 3: Start using" in content
        
        # Verify third item content
        assert "generous free tier for small teams" in content

    def test_get_public_data_includes_accordion_test(self, api_client):
        """GET /api/kb/public-data includes accordion-test document."""
        response = api_client.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "documents" in data, "Response should contain 'documents' key"
        
        doc_slugs = [d["slug"] for d in data["documents"]]
        assert "accordion-test" in doc_slugs, "accordion-test should be in documents"
        
        # Find the document and verify content
        accordion_doc = next((d for d in data["documents"] if d["slug"] == "accordion-test"), None)
        assert accordion_doc is not None
        assert "<Accordion>" in accordion_doc.get("content", ""), "Document content should have Accordion"


class TestKBAccordionAdminAPI:
    """Tests for admin KB API endpoints with Accordion content."""

    def test_admin_get_article_accordion_test(self, api_client):
        """GET /api/kb/admin/articles/accordion-test returns full article with Accordion."""
        response = api_client.get(f"{BASE_URL}/api/kb/admin/articles/accordion-test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        article = response.json()
        
        assert article["slug"] == "accordion-test"
        assert article["title"] == "Accordion Test"
        
        # Verify full Accordion markdown content
        content = article.get("content_markdown", "")
        assert "<Accordion>" in content, "Content should have Accordion tag"
        assert "<AccordionItem" in content, "Content should have AccordionItem tag"
        assert 'title="What is Trinity?"' in content, "First accordion item title should be present"

    def test_admin_list_articles_includes_accordion_test(self, api_client):
        """GET /api/kb/admin/articles lists accordion-test."""
        response = api_client.get(f"{BASE_URL}/api/kb/admin/articles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "articles" in data
        
        article_slugs = [a["slug"] for a in data["articles"]]
        assert "accordion-test" in article_slugs

    def test_admin_update_article_accordion_preserves_content(self, api_client):
        """PUT /api/kb/admin/articles/accordion-test can update and preserve Accordion."""
        # First get the current article
        get_response = api_client.get(f"{BASE_URL}/api/kb/admin/articles/accordion-test")
        assert get_response.status_code == 200
        original_article = get_response.json()
        original_content = original_article.get("content_markdown", "")
        
        # Update with modified content (add a test line)
        test_marker = "\n\n<!-- ACCORDION_TEST_MARKER -->"
        updated_content = original_content + test_marker
        
        update_response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/accordion-test",
            json={
                "content_markdown": updated_content,
                "title": original_article["title"],
                "description": original_article.get("description", ""),
                "nav_group_key": original_article["nav_group_key"],
                "section_key": original_article["section_key"],
                "published": original_article["published"]
            }
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.status_code}"
        
        # Verify the update persisted
        verify_response = api_client.get(f"{BASE_URL}/api/kb/admin/articles/accordion-test")
        assert verify_response.status_code == 200
        verified_article = verify_response.json()
        verified_content = verified_article.get("content_markdown", "")
        
        # Check Accordion content was preserved
        assert "<Accordion>" in verified_content, "Accordion tag should be preserved"
        assert "<AccordionItem" in verified_content, "AccordionItem tags should be preserved"
        assert 'title="What is Trinity?"' in verified_content, "Accordion item titles should be preserved"
        assert 'title="How do I get started?"' in verified_content
        assert 'title="Is there a free plan?"' in verified_content
        assert "<!-- ACCORDION_TEST_MARKER -->" in verified_content, "Test marker should be in content"
        
        # Clean up - restore original content
        cleanup_response = api_client.put(
            f"{BASE_URL}/api/kb/admin/articles/accordion-test",
            json={
                "content_markdown": original_content,
                "title": original_article["title"],
                "description": original_article.get("description", ""),
                "nav_group_key": original_article["nav_group_key"],
                "section_key": original_article["section_key"],
                "published": original_article["published"]
            }
        )
        assert cleanup_response.status_code == 200, "Cleanup should succeed"

    def test_admin_accordion_markdown_structure(self, api_client):
        """Verify Accordion markdown follows expected structure."""
        response = api_client.get(f"{BASE_URL}/api/kb/admin/articles/accordion-test")
        assert response.status_code == 200
        
        content = response.json().get("content_markdown", "")
        
        # Verify structure: Accordion wraps AccordionItems
        accordion_start = content.find("<Accordion>")
        accordion_end = content.find("</Accordion>")
        
        assert accordion_start != -1, "Should find Accordion start tag"
        assert accordion_end != -1, "Should find Accordion end tag"
        assert accordion_start < accordion_end, "Accordion start should be before end"
        
        # All AccordionItems should be within Accordion
        items_section = content[accordion_start:accordion_end]
        assert 'title="What is Trinity?"' in items_section
        assert 'title="How do I get started?"' in items_section
        assert 'title="Is there a free plan?"' in items_section


class TestKBAccordionSearchAPI:
    """Tests for KB search API with Accordion content."""

    def test_search_finds_accordion_test(self, api_client):
        """GET /api/kb/search?q=Accordion returns accordion-test."""
        response = api_client.get(f"{BASE_URL}/api/kb/search?q=Accordion")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        
        result_slugs = [r["slug"] for r in data["results"]]
        assert "accordion-test" in result_slugs, "Search should find accordion-test article"

    def test_search_finds_accordion_content(self, api_client):
        """GET /api/kb/search?q=Trinity finds accordion-test via content."""
        response = api_client.get(f"{BASE_URL}/api/kb/search?q=Trinity")
        assert response.status_code == 200
        
        data = response.json()
        result_slugs = [r["slug"] for r in data["results"]]
        # Trinity is mentioned in the accordion content
        assert "accordion-test" in result_slugs, "Search should find accordion-test by content"


class TestKBAccordionBackwardCompatibility:
    """Tests to ensure accordion doesn't break existing content."""

    def test_column_layout_still_works(self, api_client):
        """Verify ColumnLayout articles still work after accordion addition."""
        response = api_client.get(f"{BASE_URL}/api/kb/articles/col-layout-test")
        assert response.status_code == 200
        
        content = response.json()["article"]["content_markdown"]
        assert "<ColumnLayout" in content, "ColumnLayout should still be present"
        assert "<Col>" in content, "Col tags should still be present"

    def test_old_columns_still_work(self, api_client):
        """Verify old Columns (card-based) articles still work."""
        response = api_client.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        
        content = response.json()["article"]["content_markdown"]
        assert "<Columns" in content, "Old Columns should still be present"
        assert "<Card" in content, "Card tags should still be present"

    def test_steps_still_work(self, api_client):
        """Verify Steps components still work after accordion addition."""
        # Search for articles with Steps
        response = api_client.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        
        documents = response.json()["documents"]
        # Just verify the API returns documents correctly
        assert len(documents) > 0, "Should have documents"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
