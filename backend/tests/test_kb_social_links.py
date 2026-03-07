"""
Test KB Social Links API endpoints.
Tests both public GET and authenticated PUT endpoints.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://atlas-parity-fix.preview.emergentagent.com')
SESSION_TOKEN = "d32ac462-b0ff-435e-832d-9d068479737e"

PLATFORMS = ["linkedin", "twitter", "discord", "youtube", "reddit"]


class TestSocialLinksPublicAPI:
    """Test public social links endpoint (no auth required)."""

    def test_get_social_links_returns_200(self):
        """GET /api/kb/social-links should return 200 without auth."""
        response = requests.get(f"{BASE_URL}/api/kb/social-links")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_get_social_links_returns_links_object(self):
        """Response should contain a 'links' object."""
        response = requests.get(f"{BASE_URL}/api/kb/social-links")
        data = response.json()
        assert "links" in data, f"Response missing 'links' key: {data}"
        assert isinstance(data["links"], dict), f"'links' should be a dict: {data['links']}"

    def test_get_social_links_contains_platform_keys(self):
        """Links object should contain expected platform keys."""
        response = requests.get(f"{BASE_URL}/api/kb/social-links")
        data = response.json()
        links = data.get("links", {})
        
        # Should have at least some of the expected platforms
        found_platforms = [p for p in PLATFORMS if p in links]
        assert len(found_platforms) > 0, f"No expected platforms found in links: {links}"


class TestSocialLinksAdminAPI:
    """Test admin social links endpoint (requires auth)."""

    def test_put_social_links_without_auth_returns_401(self):
        """PUT /api/kb/admin/social-links without auth should return 401."""
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/social-links",
            json={"links": {"twitter": "https://x.com/test"}},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"

    def test_put_social_links_with_auth_returns_200(self):
        """PUT /api/kb/admin/social-links with auth should return 200."""
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/social-links",
            json={"links": {"twitter": "https://x.com/testuser"}},
            headers={"Content-Type": "application/json"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_put_social_links_persists_data(self):
        """PUT should persist data that can be retrieved via GET."""
        test_links = {
            "twitter": "https://x.com/testpersist",
            "linkedin": "https://linkedin.com/in/testpersist"
        }
        
        # Save new links
        put_response = requests.put(
            f"{BASE_URL}/api/kb/admin/social-links",
            json={"links": test_links},
            headers={"Content-Type": "application/json"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert put_response.status_code == 200
        
        # Verify via GET
        get_response = requests.get(f"{BASE_URL}/api/kb/social-links")
        data = get_response.json()
        
        assert data["links"].get("twitter") == test_links["twitter"]
        assert data["links"].get("linkedin") == test_links["linkedin"]

    def test_put_social_links_returns_saved_links(self):
        """PUT response should return the saved links."""
        test_links = {"discord": "https://discord.gg/testreturn"}
        
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/social-links",
            json={"links": test_links},
            headers={"Content-Type": "application/json"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        data = response.json()
        assert "links" in data
        assert data["links"].get("discord") == test_links["discord"]

    def test_put_all_five_platforms(self):
        """Should be able to save all 5 platform links."""
        test_links = {
            "twitter": "https://x.com/emergentsh",
            "linkedin": "https://linkedin.com/company/emergent",
            "discord": "https://discord.gg/emergent",
            "youtube": "https://youtube.com/@emergent",
            "reddit": "https://reddit.com/r/emergent"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/social-links",
            json={"links": test_links},
            headers={"Content-Type": "application/json"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for platform in PLATFORMS:
            assert data["links"].get(platform) == test_links[platform], \
                f"Platform {platform} not saved correctly"


class TestSocialLinksEdgeCases:
    """Test edge cases for social links API."""

    def test_empty_links_clears_all(self):
        """Sending empty links should clear all values."""
        # First set some links
        requests.put(
            f"{BASE_URL}/api/kb/admin/social-links",
            json={"links": {"twitter": "https://x.com/test"}},
            headers={"Content-Type": "application/json"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        # Clear all links
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/social-links",
            json={"links": {}},
            headers={"Content-Type": "application/json"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All values should be empty or missing
        for platform in PLATFORMS:
            assert not data["links"].get(platform), f"Platform {platform} should be empty"

    def test_unknown_platform_ignored(self):
        """Unknown platform keys should be ignored."""
        response = requests.put(
            f"{BASE_URL}/api/kb/admin/social-links",
            json={"links": {"unknown_platform": "https://example.com", "twitter": "https://x.com/valid"}},
            headers={"Content-Type": "application/json"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Unknown platform should not be in response
        assert "unknown_platform" not in data["links"]
        # Valid platform should be saved
        assert data["links"].get("twitter") == "https://x.com/valid"


@pytest.fixture(autouse=True, scope="module")
def restore_social_links():
    """Restore social links to original values after all tests."""
    yield
    # Restore original test data
    original_links = {
        "twitter": "https://x.com/emergentsh",
        "linkedin": "https://linkedin.com/company/emergent",
        "discord": "https://discord.gg/emergent",
        "youtube": "https://youtube.com/@emergent",
        "reddit": "https://reddit.com/r/emergent"
    }
    requests.put(
        f"{BASE_URL}/api/kb/admin/social-links",
        json={"links": original_links},
        headers={"Content-Type": "application/json"},
        cookies={"session_token": SESSION_TOKEN}
    )
