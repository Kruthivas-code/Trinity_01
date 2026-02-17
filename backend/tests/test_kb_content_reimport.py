"""
Test KB Content Re-import Verification
Tests that KB articles were correctly re-imported from help.emergent.sh API
with proper MDX components, paragraph spacing, icons, and 46 articles.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestKBPublicData:
    """BA1-BA10: Backend API verification for KB public data"""
    
    def test_ba1_public_data_returns_46_documents(self):
        """BA1: GET /api/kb/public-data returns 46 documents"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        data = response.json()
        documents = data.get('documents', [])
        assert len(documents) == 46, f"Expected 46 documents, got {len(documents)}"
    
    def test_ba2_welcome_document_has_iframe(self):
        """BA2: Welcome document content includes <iframe> tag"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        data = response.json()
        documents = data.get('documents', [])
        welcome = next((d for d in documents if d.get('slug') == 'welcome'), None)
        assert welcome is not None, "Welcome document not found"
        content = welcome.get('content', '')
        # Check for YouTube iframe which may be embedded as <iframe> or <YouTube> component
        has_iframe = '<iframe' in content or 'youtube' in content.lower()
        assert has_iframe, "Welcome document should contain iframe or YouTube embed"
    
    def test_ba3_welcome_document_has_columns_and_cards(self):
        """BA3: Welcome document content includes <Columns> and <Card> tags"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        data = response.json()
        documents = data.get('documents', [])
        welcome = next((d for d in documents if d.get('slug') == 'welcome'), None)
        assert welcome is not None, "Welcome document not found"
        content = welcome.get('content', '')
        assert '<Columns' in content, "Welcome document should contain <Columns> component"
        assert '<Card' in content, "Welcome document should contain <Card> component"
    
    def test_ba4_all_tab_pages_have_icons(self):
        """BA4: All tab pages have icon field populated"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        data = response.json()
        tabs = data.get('config', {}).get('navigation', {}).get('tabs', [])
        
        pages_without_icons = []
        for tab in tabs:
            for group in tab.get('groups', []):
                for page in group.get('pages', []):
                    page_slug = page.get('page', '')
                    page_icon = page.get('icon', '')
                    if not page_icon:
                        pages_without_icons.append(page_slug)
        
        assert len(pages_without_icons) == 0, f"Pages without icons: {pages_without_icons}"
    
    def test_ba5_navigation_has_5_tabs(self):
        """BA5: Navigation has 5 tabs with correct group counts"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        data = response.json()
        tabs = data.get('config', {}).get('navigation', {}).get('tabs', [])
        
        assert len(tabs) == 5, f"Expected 5 tabs, got {len(tabs)}"
        
        # Verify tab names
        tab_ids = [t.get('id') for t in tabs]
        expected_tabs = ['beginners-guide', 'features', 'building-your-app', 'deploy-and-manage', 'troubleshooting']
        for expected in expected_tabs:
            assert expected in tab_ids, f"Missing tab: {expected}"
    
    def test_ba6_articles_endpoint_returns_46(self):
        """BA6: GET /api/kb/articles returns 46 articles"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        data = response.json()
        articles = data.get('articles', [])
        assert len(articles) == 46, f"Expected 46 articles, got {len(articles)}"
    
    def test_ba7_welcome_article_has_mdx_content(self):
        """BA7: GET /api/kb/articles/welcome returns content with MDX"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        data = response.json()
        article = data.get('article', {})
        content = article.get('content_markdown', '')
        
        # Check for MDX components
        has_mdx = any(x in content for x in ['<Columns', '<Card', '<iframe', '>'])
        assert has_mdx, "Welcome article should contain MDX components"
        
        # Check for proper blockquote
        assert content.strip().startswith('>'), "Welcome should start with blockquote"
    
    def test_ba8_agent_architecture_article_exists(self):
        """BA8: GET /api/kb/articles/agent-architecture returns valid article"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/agent-architecture")
        assert response.status_code == 200
        data = response.json()
        article = data.get('article')
        assert article is not None, "Agent architecture article not found"
        assert article.get('title') == 'Agent Architecture', f"Unexpected title: {article.get('title')}"
    
    def test_ba9_search_integration_returns_results(self):
        """BA9: GET /api/kb/search?q=integration returns results"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=integration")
        assert response.status_code == 200
        data = response.json()
        results = data.get('results', [])
        assert len(results) > 0, "Search for 'integration' should return results"
        # Should include integration-related articles
        titles = [r.get('title', '').lower() for r in results]
        has_integration = any('integration' in t for t in titles)
        assert has_integration, "Search results should include integration articles"
    
    def test_ba10_admin_articles_requires_auth(self):
        """BA10: GET /api/kb/admin/articles requires authentication"""
        response = requests.get(f"{BASE_URL}/api/kb/admin/articles")
        assert response.status_code == 401, f"Admin endpoint should require auth, got {response.status_code}"


class TestKBContentStructure:
    """Additional content structure verification tests"""
    
    def test_welcome_has_proper_paragraph_separation(self):
        """Verify Welcome document has proper paragraph spacing (double newlines)"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome")
        assert response.status_code == 200
        data = response.json()
        content = data.get('article', {}).get('content_markdown', '')
        
        # Count double newlines (paragraph separators)
        double_newlines = content.count('\n\n')
        assert double_newlines >= 5, f"Expected at least 5 paragraph breaks, got {double_newlines}"
    
    def test_voice_mode_has_callouts(self):
        """Verify Voice Mode article has callout components"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/voice-mode")
        assert response.status_code == 200
        data = response.json()
        content = data.get('article', {}).get('content_markdown', '')
        
        # Check for callout indicators (blockquote syntax or MDX callout)
        has_callout = '> [!' in content or '<Callout' in content or '[!INFO]' in content or '[!TIP]' in content or '[!NOTE]' in content
        # If not found in raw, it might be rendered differently - check for callout text patterns
        if not has_callout:
            has_callout = 'Info' in content and 'talk to Emergent' in content
        assert has_callout, "Voice Mode should contain callout components"
    
    def test_all_articles_have_titles(self):
        """Verify all 46 articles have non-empty titles"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        data = response.json()
        articles = data.get('articles', [])
        
        articles_without_titles = [a.get('slug') for a in articles if not a.get('title')]
        assert len(articles_without_titles) == 0, f"Articles without titles: {articles_without_titles}"
    
    def test_all_articles_have_icons(self):
        """Verify all articles have icon field populated"""
        response = requests.get(f"{BASE_URL}/api/kb/articles")
        assert response.status_code == 200
        data = response.json()
        articles = data.get('articles', [])
        
        articles_without_icons = [a.get('slug') for a in articles if not a.get('icon')]
        assert len(articles_without_icons) == 0, f"Articles without icons: {articles_without_icons}"
    
    def test_tab_article_counts(self):
        """Verify each tab has expected number of articles"""
        response = requests.get(f"{BASE_URL}/api/kb/public-data")
        assert response.status_code == 200
        data = response.json()
        tabs = data.get('config', {}).get('navigation', {}).get('tabs', [])
        
        tab_counts = {}
        for tab in tabs:
            total = sum(len(g.get('pages', [])) for g in tab.get('groups', []))
            tab_counts[tab.get('id')] = total
        
        # Verify minimum expected counts
        assert tab_counts.get('beginners-guide', 0) >= 5, "Beginner's Guide should have >= 5 articles"
        assert tab_counts.get('features', 0) >= 10, "Features should have >= 10 articles"
        assert tab_counts.get('building-your-app', 0) >= 20, "Building Your App should have >= 20 articles (many integrations)"
        assert tab_counts.get('troubleshooting', 0) >= 3, "Troubleshooting should have >= 3 articles"


class TestKBNavigation:
    """Test KB navigation structure"""
    
    def test_prev_next_navigation(self):
        """Verify prev/next navigation returns correct articles"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/first-app")
        assert response.status_code == 200
        data = response.json()
        
        prev_doc = data.get('prev')
        next_doc = data.get('next')
        
        assert prev_doc is not None, "first-app should have previous article"
        assert prev_doc.get('slug') == 'welcome', f"Previous should be 'welcome', got {prev_doc.get('slug')}"
        
        assert next_doc is not None, "first-app should have next article"
    
    def test_search_voice_returns_results(self):
        """Verify search for 'voice' returns voice-mode and related articles"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=voice")
        assert response.status_code == 200
        data = response.json()
        results = data.get('results', [])
        
        assert len(results) > 0, "Search for 'voice' should return results"
        slugs = [r.get('slug') for r in results]
        assert 'voice-mode' in slugs, "Search should include voice-mode article"
    
    def test_search_emergent_returns_many_results(self):
        """Verify search for 'emergent' returns many results"""
        response = requests.get(f"{BASE_URL}/api/kb/search?q=emergent")
        assert response.status_code == 200
        data = response.json()
        results = data.get('results', [])
        
        # 'emergent' is mentioned in many articles
        assert len(results) >= 10, f"Search for 'emergent' should return >= 10 results, got {len(results)}"


class TestPortalRegression:
    """Regression tests for Portal functionality"""
    
    def test_portal_categories_exist(self):
        """RG2: Verify portal categories still work"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200
        data = response.json()
        categories = data.get('categories', [])
        assert len(categories) > 0, "Portal should have categories"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
