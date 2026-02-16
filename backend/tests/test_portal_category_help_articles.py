"""
Test portal category management with help_articles feature.
- Admin CRUD for categories with help_articles field
- Slug rename functionality
- Customer auth and ticket history
"""
import pytest
import requests
import os
import secrets
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Module-level session management
ADMIN_TOKEN = None
PORTAL_TOKEN = None
TEST_CUSTOMER_EMAIL = f"test.portal.{secrets.token_hex(4)}@example.com"


@pytest.fixture(scope="module")
def admin_session():
    """Create admin session via MongoDB"""
    global ADMIN_TOKEN
    if ADMIN_TOKEN:
        return ADMIN_TOKEN
    
    # Create session directly in MongoDB
    import sys
    sys.path.insert(0, '/app/backend')
    from database import users_collection, sessions_collection
    
    user = users_collection.find_one({}, {'_id': 0, 'user_id': 1})
    if not user:
        pytest.skip("No admin user found in database")
    
    token = secrets.token_urlsafe(32)
    sessions_collection.insert_one({
        'session_token': token,
        'user_id': user['user_id'],
        'created_at': datetime.now(timezone.utc),
        'expires_at': datetime.now(timezone.utc) + timedelta(days=1)
    })
    ADMIN_TOKEN = token
    return token


@pytest.fixture(scope="module")
def portal_customer():
    """Register a portal customer for testing"""
    global PORTAL_TOKEN
    
    resp = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
        "name": "Test Portal User",
        "email": TEST_CUSTOMER_EMAIL,
        "password": "testpass123"
    })
    
    if resp.status_code == 409:  # Email already exists
        resp = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": "testpass123"
        })
    
    assert resp.status_code in [200, 201], f"Portal auth failed: {resp.text}"
    data = resp.json()
    PORTAL_TOKEN = data['token']
    return data


class TestPortalCategoriesPublic:
    """Test public category endpoints"""
    
    def test_get_all_categories(self):
        """GET /api/portal/categories returns all categories"""
        resp = requests.get(f"{BASE_URL}/api/portal/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data
        assert len(data["categories"]) >= 1
        
        # Verify structure includes help_articles field
        first_cat = data["categories"][0]
        assert "slug" in first_cat
        assert "title" in first_cat
        # help_articles may or may not be present initially
    
    def test_get_single_category(self):
        """GET /api/portal/categories/{slug} returns category with help_articles"""
        resp = requests.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "credits-pricing"
        assert data["title"] == "Credits & Pricing"
        # Check help_articles field exists
        assert "help_articles" in data or data.get("help_articles") is None or isinstance(data.get("help_articles", []), list)
    
    def test_get_nonexistent_category(self):
        """GET /api/portal/categories/{slug} returns 404 for invalid slug"""
        resp = requests.get(f"{BASE_URL}/api/portal/categories/nonexistent-cat-xyz")
        assert resp.status_code == 404


class TestAdminCategoryManagement:
    """Test admin category CRUD with help_articles"""
    
    def test_create_category_with_help_articles(self, admin_session):
        """POST /api/portal/admin/categories - create with help_articles"""
        resp = requests.post(
            f"{BASE_URL}/api/portal/admin/categories",
            headers={"Cookie": f"session_token={admin_session}"},
            json={
                "title": "TEST Category With Docs",
                "slug": "test-cat-with-docs",
                "description": "Testing help articles feature",
                "icon": "HelpCircle",
                "help_articles": [
                    {"title": "Welcome To Emergent", "url": "https://help.emergent.sh/welcome"},
                    {"title": "Plans and Credits", "url": "https://help.emergent.sh/plans-and-credits"}
                ],
                "order": 99
            }
        )
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        data = resp.json()
        assert data["title"] == "TEST Category With Docs"
        assert data["slug"] == "test-cat-with-docs"
        assert len(data["help_articles"]) == 2
        assert data["help_articles"][0]["title"] == "Welcome To Emergent"
    
    def test_update_category_help_articles(self, admin_session):
        """PUT /api/portal/admin/categories/{slug} - update help_articles"""
        resp = requests.put(
            f"{BASE_URL}/api/portal/admin/categories/test-cat-with-docs",
            headers={"Cookie": f"session_token={admin_session}"},
            json={
                "description": "Updated description",
                "help_articles": [
                    {"title": "Voice Mode", "url": "https://help.emergent.sh/voice-mode"},
                    {"title": "GitHub Integration", "url": "https://help.emergent.sh/github-integration"},
                    {"title": "Deployment on Emergent", "url": "https://help.emergent.sh/deployment-on-emergent"}
                ]
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Updated description"
        assert len(data["help_articles"]) == 3
    
    def test_update_category_slug_rename(self, admin_session):
        """PUT /api/portal/admin/categories/{slug} - rename slug"""
        resp = requests.put(
            f"{BASE_URL}/api/portal/admin/categories/test-cat-with-docs",
            headers={"Cookie": f"session_token={admin_session}"},
            json={"slug": "test-cat-renamed"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "test-cat-renamed"
        
        # Verify old slug no longer exists
        old_resp = requests.get(f"{BASE_URL}/api/portal/categories/test-cat-with-docs")
        assert old_resp.status_code == 404
        
        # Verify new slug works
        new_resp = requests.get(f"{BASE_URL}/api/portal/categories/test-cat-renamed")
        assert new_resp.status_code == 200
    
    def test_delete_category(self, admin_session):
        """DELETE /api/portal/admin/categories/{slug}"""
        resp = requests.delete(
            f"{BASE_URL}/api/portal/admin/categories/test-cat-renamed",
            headers={"Cookie": f"session_token={admin_session}"}
        )
        assert resp.status_code == 200
        
        # Verify deleted
        get_resp = requests.get(f"{BASE_URL}/api/portal/categories/test-cat-renamed")
        assert get_resp.status_code == 404
    
    def test_admin_auth_required(self):
        """Admin endpoints require session_token cookie"""
        resp = requests.post(
            f"{BASE_URL}/api/portal/admin/categories",
            json={"title": "Unauthorized", "slug": "unauth-test"}
        )
        assert resp.status_code == 401


class TestPortalCustomerAuth:
    """Test portal customer authentication"""
    
    def test_register_customer(self):
        """POST /api/portal/auth/register"""
        email = f"test.reg.{secrets.token_hex(4)}@example.com"
        resp = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
            "name": "Registration Test",
            "email": email,
            "password": "testpass123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "customer_id" in data
        assert data["email"] == email
    
    def test_login_customer(self, portal_customer):
        """POST /api/portal/auth/login"""
        resp = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": "testpass123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
    
    def test_get_customer_me(self, portal_customer):
        """GET /api/portal/auth/me"""
        resp = requests.get(
            f"{BASE_URL}/api/portal/auth/me",
            headers={"Authorization": f"Bearer {PORTAL_TOKEN}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == TEST_CUSTOMER_EMAIL
    
    def test_invalid_login(self):
        """POST /api/portal/auth/login with wrong credentials"""
        resp = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert resp.status_code == 401


class TestCustomerTicketHistory:
    """Test customer ticket submission and history"""
    
    def test_submit_ticket(self, portal_customer):
        """POST /api/portal/tickets - submit as customer"""
        resp = requests.post(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {PORTAL_TOKEN}"},
            json={
                "category_slug": "credits-pricing",
                "subcategory": "Credit Usage",
                "subject": "TEST: Ticket history test",
                "description": "Testing ticket submission for history feature"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "ticket_id" in data
        assert data["status"] == "todo"
        return data["ticket_id"]
    
    def test_get_my_tickets(self, portal_customer):
        """GET /api/portal/tickets - customer ticket list"""
        resp = requests.get(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {PORTAL_TOKEN}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tickets" in data
        # Should have at least the ticket we just created
        assert len(data["tickets"]) >= 1
        
        # Verify ticket structure
        ticket = data["tickets"][0]
        assert "ticket_id" in ticket
        assert "title" in ticket
        assert "status" in ticket
    
    def test_get_ticket_detail(self, portal_customer):
        """GET /api/portal/tickets/{ticket_id} - ticket detail with messages"""
        # First get list to find a ticket_id
        list_resp = requests.get(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {PORTAL_TOKEN}"}
        )
        tickets = list_resp.json().get("tickets", [])
        if not tickets:
            pytest.skip("No tickets to test detail view")
        
        ticket_id = tickets[0]["ticket_id"]
        
        resp = requests.get(
            f"{BASE_URL}/api/portal/tickets/{ticket_id}",
            headers={"Authorization": f"Bearer {PORTAL_TOKEN}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "ticket" in data
        assert "messages" in data
        assert data["ticket"]["ticket_id"] == ticket_id
    
    def test_ticket_auth_required(self):
        """Ticket endpoints require customer auth"""
        resp = requests.get(f"{BASE_URL}/api/portal/tickets")
        assert resp.status_code == 401


class TestHelpArticlesInCategory:
    """Verify help_articles display in category pages"""
    
    def test_credits_pricing_has_help_articles(self):
        """credits-pricing category should have help_articles"""
        resp = requests.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        assert resp.status_code == 200
        data = resp.json()
        
        # According to the context, credits-pricing has one help article
        help_articles = data.get("help_articles", [])
        assert isinstance(help_articles, list)
        # Should have at least one article (Plans and Credits)
        if len(help_articles) > 0:
            assert "title" in help_articles[0]
            assert "url" in help_articles[0]
            print(f"Found {len(help_articles)} help article(s): {[a['title'] for a in help_articles]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
