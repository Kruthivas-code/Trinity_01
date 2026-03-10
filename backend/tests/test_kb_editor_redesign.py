"""
Test KB Editor Backend Redesign Features
- Global Docs Settings endpoints
- Article description field
- Published=false default for new articles
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://assign-me-fix.preview.emergentagent.com')
SESSION_TOKEN = "test_kb_editor_session_2026"

@pytest.fixture
def auth_cookies():
    """Session token cookie for authenticated requests."""
    return {"session_token": SESSION_TOKEN}


class TestGlobalDocsSettings:
    """Test /api/kb/admin/docs-settings endpoints."""

    def test_get_docs_settings_requires_auth(self):
        """GET /api/kb/admin/docs-settings should return 401 without auth."""
        response = requests.get(f"{BASE_URL}/api/kb/admin/docs-settings")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_get_docs_settings_with_auth(self, auth_cookies):
        """GET /api/kb/admin/docs-settings should return settings with auth."""
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/docs-settings",
            cookies=auth_cookies
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should have expected keys
        expected_keys = ["meta_title", "meta_description"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    def test_put_docs_settings_requires_auth(self):
        """PUT /api/kb/admin/docs-settings should return 401 without auth."""
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/docs-settings",
            json={"meta_title": "Test"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_put_docs_settings_with_auth(self, auth_cookies):
        """PUT /api/kb/admin/docs-settings should update settings."""
        test_data = {
            "meta_title": f"TEST_Title_{uuid.uuid4().hex[:8]}",
            "meta_description": f"TEST_Description_{uuid.uuid4().hex[:8]}",
            "footer_text": f"TEST_Footer_{uuid.uuid4().hex[:8]}"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/docs-settings",
            json=test_data,
            cookies=auth_cookies
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify data was saved
        assert data.get("meta_title") == test_data["meta_title"]
        assert data.get("meta_description") == test_data["meta_description"]
        assert data.get("footer_text") == test_data["footer_text"]

    def test_docs_settings_persistence(self, auth_cookies):
        """Settings should persist after being saved."""
        test_title = f"TEST_Persist_{uuid.uuid4().hex[:8]}"
        
        # Save setting
        requests.put(
            f"{BASE_URL}/api/kb/admin/docs-settings",
            json={"meta_title": test_title},
            cookies=auth_cookies
        )
        
        # Read back
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/docs-settings",
            cookies=auth_cookies
        )
        assert response.status_code == 200
        assert response.json().get("meta_title") == test_title

    def test_docs_settings_all_fields(self, auth_cookies):
        """Test all 7 settings fields can be saved."""
        test_data = {
            "meta_title": f"TEST_{uuid.uuid4().hex[:6]}",
            "meta_description": f"TEST_desc_{uuid.uuid4().hex[:6]}",
            "favicon_url": "/favicon.ico",
            "og_image_url": "https://example.com/og.png",
            "logo_url": "https://example.com/logo.svg",
            "footer_text": "Built with Emergent",
            "custom_domain": "docs.example.com"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/docs-settings",
            json=test_data,
            cookies=auth_cookies
        )
        assert response.status_code == 200
        data = response.json()
        
        for key, value in test_data.items():
            assert data.get(key) == value, f"Field {key} mismatch"


class TestArticleDescriptionField:
    """Test new description field on articles."""

    def test_create_article_with_description(self, auth_cookies):
        """POST /api/kb/admin/articles should accept description field."""
        unique_slug = f"test-desc-{uuid.uuid4().hex[:8]}"
        article_data = {
            "title": f"TEST Article {unique_slug}",
            "slug": unique_slug,
            "description": "This is a test description for the article",
            "content_markdown": "# Test Content",
            "nav_group_key": "",
            "nav_group_label": "",
            "section_key": "",
            "section_label": ""
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/kb/admin/articles",
                json=article_data,
                cookies=auth_cookies
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            
            # Verify description was saved
            assert data.get("description") == article_data["description"]
            assert data.get("title") == article_data["title"]
            
        finally:
            # Cleanup
            requests.delete(
                f"{BASE_URL}/api/kb/admin/articles/{unique_slug}",
                cookies=auth_cookies
            )

    def test_update_article_description(self, auth_cookies):
        """PUT /api/kb/admin/articles/{slug} should update description."""
        unique_slug = f"test-update-desc-{uuid.uuid4().hex[:8]}"
        
        # Create article first
        article_data = {
            "title": f"TEST Article {unique_slug}",
            "slug": unique_slug,
            "description": "Initial description",
            "content_markdown": "# Test"
        }
        
        try:
            requests.post(
                f"{BASE_URL}/api/kb/admin/articles",
                json=article_data,
                cookies=auth_cookies
            )
            
            # Update description
            new_description = "Updated description text"
            response = requests.put(
                f"{BASE_URL}/api/kb/admin/articles/{unique_slug}",
                json={"description": new_description},
                cookies=auth_cookies
            )
            
            assert response.status_code == 200
            assert response.json().get("description") == new_description
            
        finally:
            requests.delete(
                f"{BASE_URL}/api/kb/admin/articles/{unique_slug}",
                cookies=auth_cookies
            )


class TestArticlePublishedDefault:
    """Test that new articles default to published=false (draft)."""

    def test_new_article_defaults_to_draft(self, auth_cookies):
        """New articles should have published=false by default."""
        unique_slug = f"test-draft-{uuid.uuid4().hex[:8]}"
        article_data = {
            "title": f"TEST Draft Article {unique_slug}",
            "slug": unique_slug,
            "description": "Test draft article",
            "content_markdown": "# Draft Content"
            # Note: NOT including 'published' field
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/kb/admin/articles",
                json=article_data,
                cookies=auth_cookies
            )
            assert response.status_code == 200
            data = response.json()
            
            # Should default to draft (published=false)
            assert data.get("published") == False, "New article should default to draft (published=false)"
            
        finally:
            requests.delete(
                f"{BASE_URL}/api/kb/admin/articles/{unique_slug}",
                cookies=auth_cookies
            )

    def test_article_can_be_published(self, auth_cookies):
        """Article can be set to published=true explicitly."""
        unique_slug = f"test-publish-{uuid.uuid4().hex[:8]}"
        article_data = {
            "title": f"TEST Published Article {unique_slug}",
            "slug": unique_slug,
            "description": "Test published article",
            "content_markdown": "# Published Content",
            "published": True  # Explicitly set to published
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/kb/admin/articles",
                json=article_data,
                cookies=auth_cookies
            )
            assert response.status_code == 200
            data = response.json()
            
            # Should be published when explicitly set
            assert data.get("published") == True
            
        finally:
            requests.delete(
                f"{BASE_URL}/api/kb/admin/articles/{unique_slug}",
                cookies=auth_cookies
            )

    def test_toggle_published_status(self, auth_cookies):
        """Article published status can be toggled via PUT."""
        unique_slug = f"test-toggle-{uuid.uuid4().hex[:8]}"
        article_data = {
            "title": f"TEST Toggle Article {unique_slug}",
            "slug": unique_slug,
            "description": "Test toggle",
            "content_markdown": "# Content"
        }
        
        try:
            # Create as draft
            response = requests.post(
                f"{BASE_URL}/api/kb/admin/articles",
                json=article_data,
                cookies=auth_cookies
            )
            assert response.json().get("published") == False
            
            # Toggle to published
            response = requests.put(
                f"{BASE_URL}/api/kb/admin/articles/{unique_slug}",
                json={"published": True},
                cookies=auth_cookies
            )
            assert response.status_code == 200
            assert response.json().get("published") == True
            
            # Toggle back to draft
            response = requests.put(
                f"{BASE_URL}/api/kb/admin/articles/{unique_slug}",
                json={"published": False},
                cookies=auth_cookies
            )
            assert response.status_code == 200
            assert response.json().get("published") == False
            
        finally:
            requests.delete(
                f"{BASE_URL}/api/kb/admin/articles/{unique_slug}",
                cookies=auth_cookies
            )


class TestArticleValidation:
    """Test article validation requirements."""

    def test_article_requires_title(self, auth_cookies):
        """Article creation should require title."""
        unique_slug = f"test-no-title-{uuid.uuid4().hex[:8]}"
        article_data = {
            "slug": unique_slug,
            "description": "No title"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles",
            json=article_data,
            cookies=auth_cookies
        )
        # Should fail validation
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"

    def test_article_requires_slug(self, auth_cookies):
        """Article creation should require slug."""
        article_data = {
            "title": "Test Article Without Slug",
            "description": "No slug"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles",
            json=article_data,
            cookies=auth_cookies
        )
        # Should fail validation
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"

    def test_duplicate_slug_rejected(self, auth_cookies):
        """Creating article with duplicate slug should fail."""
        # Use an existing slug
        article_data = {
            "title": "Duplicate Slug Test",
            "slug": "welcome",  # This already exists
            "description": "Test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles",
            json=article_data,
            cookies=auth_cookies
        )
        # Should return 409 Conflict
        assert response.status_code == 409, f"Expected 409 Conflict, got {response.status_code}"
