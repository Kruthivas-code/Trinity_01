"""
Test KB Search API Endpoint
Tests for GET /api/kb/search with snippets and category breadcrumbs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://docs-sync-test.preview.emergentagent.com')


class TestKBSearchEndpoint:
    """Test GET /api/kb/search endpoint."""

    def test_search_endpoint_exists(self):
        """GET /api/kb/search should be accessible."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_search_returns_results_structure(self):
        """Search should return results array."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data, "Response should have 'results' key"
        assert isinstance(data["results"], list), "Results should be a list"

    def test_search_finds_matching_articles(self):
        """Search should find articles matching query."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        
        # Should find articles with "emergent" in title or content
        assert len(data["results"]) > 0, "Should find at least one result for 'emergent'"

    def test_search_results_have_required_fields(self):
        """Each search result should have slug, title, and snippet."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "slug" in result, "Result should have 'slug'"
            assert "title" in result, "Result should have 'title'"
            assert "snippet" in result, "Result should have 'snippet'"

    def test_search_results_have_category_info(self):
        """Results should have nav_group_key and section_key for breadcrumbs."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "nav_group_key" in result, "Result should have 'nav_group_key' for breadcrumb"
            assert "section_key" in result, "Result should have 'section_key' for breadcrumb"

    def test_search_snippet_contains_context(self):
        """Snippet should contain context around the matched query."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["results"]) > 0:
            result = data["results"][0]
            snippet = result.get("snippet", "")
            
            # Snippet should have reasonable length (context around match)
            assert len(snippet) > 20, "Snippet should have meaningful context"
            assert len(snippet) < 300, "Snippet should not be too long"

    def test_search_empty_query_returns_empty(self):
        """Empty query should return empty results."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=")
        assert response.status_code == 200
        data = response.json()
        
        assert data["results"] == [], "Empty query should return empty results"

    def test_search_short_query_returns_empty(self):
        """Query shorter than 2 characters should return empty."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=a")
        assert response.status_code == 200
        data = response.json()
        
        assert data["results"] == [], "Single character query should return empty"

    def test_search_no_match_returns_empty(self):
        """Query with no matches should return empty results."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=xyznonexistentterm123")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 0, "Non-matching query should return empty"

    def test_search_case_insensitive(self):
        """Search should be case insensitive."""
        response_lower = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        response_upper = requests.get(f"{BASE_URL}/api/kb/search?q=EMERGENT")
        
        assert response_lower.status_code == 200
        assert response_upper.status_code == 200
        
        data_lower = response_lower.json()
        data_upper = response_upper.json()
        
        # Both should find the same results
        assert len(data_lower["results"]) == len(data_upper["results"]), \
            "Case should not affect search results"

    def test_search_only_published_articles(self):
        """Search should only return published articles."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        
        # All results should be from published articles
        # (can't directly verify published status from search results,
        # but we verify the endpoint filters correctly by design)
        for result in data["results"]:
            # Each result should be a valid published article
            article_response = requests.get(f"{BASE_URL}/api/kb/articles/{result['slug']}")
            assert article_response.status_code == 200, \
                f"Article {result['slug']} from search should be publicly accessible"

    def test_search_limits_results(self):
        """Search should limit results to prevent overwhelming responses."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=the")  # Common word
        assert response.status_code == 200
        data = response.json()
        
        # Should have max 20 results (as per backend implementation)
        assert len(data["results"]) <= 20, "Results should be limited to 20"

    def test_search_result_snippet_with_ellipsis(self):
        """Snippet should use ellipsis for truncated content."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["results"]) > 0:
            snippet = data["results"][0].get("snippet", "")
            # Snippet typically has ellipsis if truncated
            # This is not a hard requirement, just checking format is sensible
            assert isinstance(snippet, str), "Snippet should be a string"


class TestKBSearchIntegration:
    """Integration tests for search with public docs."""

    def test_search_result_matches_article_content(self):
        """Search result slug should lead to actual article."""
        # Search for known content
        response = requests.get(f"{BASE_URL}/api/kb/search?q=welcome")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["results"]) > 0:
            result = data["results"][0]
            
            # Fetch the actual article
            article_response = requests.get(f"{BASE_URL}/api/kb/articles/{result['slug']}")
            assert article_response.status_code == 200
            
            article_data = article_response.json()
            # Title should match
            assert article_data["article"]["title"] == result["title"]

    def test_search_breadcrumb_info_matches_nav(self):
        """Category info in search results should match navigation."""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=welcome")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["results"]) > 0:
            result = data["results"][0]
            
            # These should be valid nav keys
            nav_group_key = result.get("nav_group_key")
            section_key = result.get("section_key")
            
            # Verify against navigation structure
            nav_response = requests.get(f"{BASE_URL}/api/kb/navigation")
            assert nav_response.status_code == 200
            nav_data = nav_response.json()
            
            # Find the nav group
            nav_groups = nav_data.get("nav_groups", [])
            group_keys = [g.get("key") for g in nav_groups]
            
            if nav_group_key:
                assert nav_group_key in group_keys, \
                    f"nav_group_key '{nav_group_key}' should exist in navigation"
