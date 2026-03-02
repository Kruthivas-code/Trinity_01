"""
Integration tests for Portal Help Topics API (KB-derived topics).
Tests the new endpoints: GET /api/portal/help-topics and GET /api/portal/help-topics/{topic_key}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPortalHelpTopicsAPI:
    """Test the KB-derived help topics endpoints."""

    def test_list_help_topics_returns_200(self):
        """GET /api/portal/help-topics returns 200 with topics list."""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics")
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        assert isinstance(data["topics"], list)

    def test_list_help_topics_has_expected_structure(self):
        """Each topic has required fields: key, label, icon, description, article_count, first_slug, sections."""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics")
        data = response.json()
        
        assert len(data["topics"]) > 0, "Expected at least one topic"
        
        for topic in data["topics"]:
            assert "key" in topic, "Topic missing 'key'"
            assert "label" in topic, "Topic missing 'label'"
            assert "icon" in topic, "Topic missing 'icon'"
            assert "description" in topic, "Topic missing 'description'"
            assert "article_count" in topic, "Topic missing 'article_count'"
            assert "first_slug" in topic, "Topic missing 'first_slug'"
            assert "sections" in topic, "Topic missing 'sections'"
            assert isinstance(topic["sections"], list), "sections should be a list"

    def test_list_help_topics_sections_have_articles(self):
        """Each section should contain articles with slug and title."""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics")
        data = response.json()
        
        # Find a topic with sections
        topics_with_sections = [t for t in data["topics"] if t["sections"]]
        assert len(topics_with_sections) > 0, "Expected at least one topic with sections"
        
        topic = topics_with_sections[0]
        section = topic["sections"][0]
        assert "key" in section, "Section missing 'key'"
        assert "label" in section, "Section missing 'label'"
        assert "articles" in section, "Section missing 'articles'"
        
        if section["articles"]:
            article = section["articles"][0]
            assert "slug" in article, "Article missing 'slug'"
            assert "title" in article, "Article missing 'title'"

    def test_get_single_topic_returns_200(self):
        """GET /api/portal/help-topics/{topic_key} returns 200 for valid topic."""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics/beginners-guide")
        assert response.status_code == 200
        data = response.json()
        
        assert data["key"] == "beginners-guide"
        assert "label" in data
        assert "icon" in data
        assert "description" in data
        assert "article_count" in data
        assert "sections" in data

    def test_get_single_topic_has_full_structure(self):
        """Single topic endpoint returns detailed structure with sections and articles."""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics/features")
        assert response.status_code == 200
        data = response.json()
        
        assert data["key"] == "features"
        assert isinstance(data["sections"], list)
        
        # Check sections have articles
        if data["sections"]:
            section = data["sections"][0]
            assert "key" in section
            assert "label" in section
            assert "articles" in section
            if section["articles"]:
                article = section["articles"][0]
                assert "slug" in article
                assert "title" in article

    def test_get_nonexistent_topic_returns_404(self):
        """GET /api/portal/help-topics/nonexistent returns 404."""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics/nonexistent-topic-xyz")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_article_count_matches_actual_count(self):
        """Verify article_count field matches the actual number of articles in sections."""
        response = requests.get(f"{BASE_URL}/api/portal/help-topics/beginners-guide")
        assert response.status_code == 200
        data = response.json()
        
        # Count all articles across sections
        actual_count = sum(len(section["articles"]) for section in data["sections"])
        assert data["article_count"] == actual_count, f"article_count ({data['article_count']}) doesn't match actual ({actual_count})"


class TestPortalCategoriesAPI:
    """Ensure existing portal categories still work."""

    def test_list_categories_returns_200(self):
        """GET /api/portal/categories still returns 200."""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)

    def test_list_categories_has_data(self):
        """Categories endpoint should return existing categories."""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        data = response.json()
        assert len(data["categories"]) > 0, "Expected at least one category"

    def test_category_structure(self):
        """Each category should have expected fields."""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        data = response.json()
        
        if data["categories"]:
            cat = data["categories"][0]
            assert "slug" in cat
            assert "title" in cat

    def test_get_single_category_returns_200(self):
        """GET /api/portal/categories/{slug} returns 200 for valid category."""
        response = requests.get(f"{BASE_URL}/api/portal/categories/features")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "features"


class TestKBArticlesForPortal:
    """Test KB articles endpoint used by PortalCategory for related articles."""

    def test_kb_articles_by_nav_group(self):
        """GET /api/kb/articles?nav_group={group} returns articles."""
        response = requests.get(f"{BASE_URL}/api/kb/articles?nav_group=deploy-and-manage")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        # Should have articles for deploy-and-manage group
        assert len(data["articles"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
