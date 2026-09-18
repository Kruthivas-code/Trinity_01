"""
KB Docs API Tests - Knowledge Base documentation site APIs
Tests navigation, articles listing, article detail with prev/next, search, and filtering
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestKBNavigation:
    """KB navigation structure API tests"""
    
    def test_get_navigation_returns_5_groups(self):
        """GET /api/kb/navigation - returns the recursive nav tree with 5 top-level groups"""
        response = requests.get(f"{BASE_URL}/api/kb/navigation")
        assert response.status_code == 200

        data = response.json()
        assert "groups" in data
        nav_groups = data["groups"]
        assert len(nav_groups) == 5

        # Verify expected nav group keys
        group_keys = [g["key"] for g in nav_groups]
        expected_keys = ["beginners-guide", "features", "building-your-app", "deploy-and-manage", "troubleshooting"]
        assert sorted(group_keys) == sorted(expected_keys)

        # Verify each top-level group is a tree node with nested groups ("sections")
        for group in nav_groups:
            assert group.get("type") == "group"
            assert "key" in group
            assert "label" in group
            assert "children" in group
            nested_groups = [c for c in group["children"] if c.get("type") == "group"]
            assert len(nested_groups) > 0


class TestKBArticlesList:
    """KB articles listing API tests"""
    
    def test_get_all_articles_returns_21_without_content(self):
        """GET /api/kb/articles - returns all 21 published articles without content_markdown"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        
        data = response.json()
        assert "articles" in data
        articles = data["articles"]
        assert len(articles) == 21
        
        # Verify content_markdown is NOT included
        for article in articles:
            assert "content_markdown" not in article
            assert "slug" in article
            assert "title" in article
            assert "section_key" in article
            assert "nav_group_key" in article
    
    def test_filter_articles_by_nav_group(self):
        """GET /api/kb/articles?nav_group=features - filters by nav group"""
        response = requests.get(f"{BASE_URL}/api/kb/articles?nav_group=features")
        assert response.status_code == 200
        
        data = response.json()
        articles = data["articles"]
        assert len(articles) > 0
        
        # All articles should have features nav group
        for article in articles:
            assert article["nav_group_key"] == "features"
    
    def test_filter_articles_by_section(self):
        """GET /api/kb/articles?section=core-features - filters by section"""
        response = requests.get(f"{BASE_URL}/api/kb/articles?section=core-features")
        assert response.status_code == 200
        
        data = response.json()
        articles = data["articles"]
        assert len(articles) > 0
        
        # All articles should have core-features section
        for article in articles:
            assert article["section_key"] == "core-features"


class TestKBArticleDetail:
    """KB article detail API tests"""
    
    def test_get_welcome_article_full_content(self):
        """GET /api/kb/articles/welcome - returns full article with content_markdown"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        
        data = response.json()
        assert "article" in data
        article = data["article"]
        
        assert article["slug"] == "welcome"
        assert article["title"] == "Welcome To Emergent"
        assert "content_markdown" in article
        assert len(article["content_markdown"]) > 100  # Has substantial content
        assert "# Welcome To Emergent" in article["content_markdown"]
    
    def test_get_article_with_prev_next_navigation(self):
        """GET /api/kb/articles/welcome - returns prev/next navigation links"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        
        data = response.json()
        assert "prev" in data
        assert "next" in data
        
        # Welcome is first article - no prev, but has next
        assert data["prev"] is None
        assert data["next"] is not None
        assert "slug" in data["next"]
        assert "title" in data["next"]
        assert data["next"]["slug"] == "first-app"
    
    def test_get_middle_article_has_both_prev_next(self):
        """A middle article should have both prev and next"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/first-app")
        assert response.status_code == 200
        
        data = response.json()
        assert data["prev"] is not None
        assert data["next"] is not None
        assert data["prev"]["slug"] == "welcome"
    
    def test_get_nonexistent_article_returns_404(self):
        """GET /api/kb/articles/nonexistent - returns 404"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/nonexistent-article-slug")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_get_deployment_types_article_long_content(self):
        """GET /api/kb/articles/deployment-types - returns long article with rich TOC"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/deployment-types")
        assert response.status_code == 200
        
        data = response.json()
        article = data["article"]
        
        assert article["slug"] == "deployment-types"
        assert "content_markdown" in article
        
        # Should have multiple headings for TOC
        content = article["content_markdown"]
        assert "## " in content  # Has h2 headings
        assert content.count("## ") >= 3  # Multiple h2 sections


class TestKBSearch:
    """KB search API tests"""
    
    def test_search_returns_matching_articles(self):
        """GET /api/kb/search?q=deployment - returns matching articles"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=deployment")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        results = data["results"]
        assert len(results) > 0
        
        # Should find deployment-related articles
        titles = [r["title"].lower() for r in results]
        found_deployment = any("deployment" in t for t in titles)
        assert found_deployment
        
        # Results should not include content_markdown
        for result in results:
            assert "content_markdown" not in result
    
    def test_search_short_query_returns_empty(self):
        """GET /api/kb/search?q=x - returns empty for short query"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=x")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert data["results"] == []
    
    def test_search_empty_query_returns_empty(self):
        """GET /api/kb/search?q= - returns empty for empty query"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=")
        assert response.status_code == 200
        
        data = response.json()
        assert data["results"] == []
    
    def test_search_case_insensitive(self):
        """Search should be case insensitive"""
        response_lower = requests.get(f"{BASE_URL}/api/kb/search?q=github")
        response_upper = requests.get(f"{BASE_URL}/api/kb/search?q=GITHUB")
        
        assert response_lower.status_code == 200
        assert response_upper.status_code == 200
        
        # Both should return same results
        lower_slugs = {r["slug"] for r in response_lower.json()["results"]}
        upper_slugs = {r["slug"] for r in response_upper.json()["results"]}
        assert lower_slugs == upper_slugs
        assert len(lower_slugs) > 0


class TestKBArticleStructure:
    """Verify article data structure"""
    
    def test_article_list_has_required_fields(self):
        """Articles in list have all required fields"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        
        articles = response.json()["articles"]
        required_fields = ["slug", "title", "section_key", "section_label", 
                          "nav_group_key", "nav_group_label", "order", "published"]
        
        for article in articles:
            for field in required_fields:
                assert field in article, f"Missing field {field} in article {article.get('slug', 'unknown')}"
    
    def test_articles_sorted_by_order(self):
        """Articles should be sorted by order field"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        
        articles = response.json()["articles"]
        orders = [a["order"] for a in articles]
        assert orders == sorted(orders), "Articles not sorted by order"


class TestKBPortalDocsLink:
    """Verify portal 'Docs' link points to /docs"""
    
    def test_portal_home_still_works(self):
        """Portal home page categories API still works"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
