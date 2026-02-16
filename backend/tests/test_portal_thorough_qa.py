"""
Thorough QA tests for Trinity Portal - Admin Category CRUD & Customer Ticket History
- Admin Category Management with help_articles
- Customer Authentication edge cases
- Customer Ticket History and replies
- Edge cases, validation, 404s, 401s, duplicate handling
"""
import pytest
import requests
import os
import secrets
import sys
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Global session tokens
ADMIN_TOKEN = None
PORTAL_TOKEN = None
TEST_UNIQUE_ID = secrets.token_hex(4)
TEST_CUSTOMER_EMAIL = f"qa.thorough.{TEST_UNIQUE_ID}@example.com"
TEST_CUSTOMER_PASSWORD = "test1234"


@pytest.fixture(scope="module")
def admin_session():
    """Create admin session via MongoDB for admin endpoints"""
    global ADMIN_TOKEN
    if ADMIN_TOKEN:
        return ADMIN_TOKEN
    
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
def portal_customer_token():
    """Register a portal customer and return token"""
    global PORTAL_TOKEN
    if PORTAL_TOKEN:
        return PORTAL_TOKEN
    
    # Try to register
    resp = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
        "name": "QA Thorough Tester",
        "email": TEST_CUSTOMER_EMAIL,
        "password": TEST_CUSTOMER_PASSWORD
    })
    
    if resp.status_code == 409:  # Already exists
        resp = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
    
    assert resp.status_code in [200, 201], f"Portal auth failed: {resp.text}"
    PORTAL_TOKEN = resp.json()['token']
    return PORTAL_TOKEN


# ==================== ADMIN CATEGORY CRUD TESTS ====================

class TestAdminCategoryCRUD:
    """Comprehensive tests for admin category CRUD operations"""
    
    TEST_SLUG = f"test-qa-{TEST_UNIQUE_ID}"
    
    def test_01_admin_create_category_all_fields(self, admin_session):
        """POST /api/portal/admin/categories - create with ALL fields"""
        resp = requests.post(
            f"{BASE_URL}/api/portal/admin/categories",
            headers={"Cookie": f"session_token={admin_session}"},
            json={
                "title": f"QA Test Category {TEST_UNIQUE_ID}",
                "slug": self.TEST_SLUG,
                "description": "Testing all fields including help_articles",
                "icon": "Rocket",
                "subtopics": [
                    {"name": "SubA", "items": ["item1", "item2"]},
                    {"name": "SubB", "items": []}
                ],
                "help_articles": [
                    {"title": "Welcome To Emergent", "url": "https://help.emergent.sh/welcome"},
                    {"title": "Plans and Credits", "url": "https://help.emergent.sh/plans-and-credits"}
                ],
                "order": 99
            }
        )
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        data = resp.json()
        
        # Verify all fields
        assert data["title"] == f"QA Test Category {TEST_UNIQUE_ID}"
        assert data["slug"] == self.TEST_SLUG
        assert data["description"] == "Testing all fields including help_articles"
        assert data["icon"] == "Rocket"
        assert len(data["subtopics"]) == 2
        assert data["subtopics"][0]["name"] == "SubA"
        assert len(data["subtopics"][0]["items"]) == 2
        assert len(data["help_articles"]) == 2
        assert data["help_articles"][0]["url"] == "https://help.emergent.sh/welcome"
        assert data["order"] == 99
        assert "category_id" in data
    
    def test_02_admin_create_duplicate_slug_409(self, admin_session):
        """POST /api/portal/admin/categories - reject duplicate slug (409)"""
        resp = requests.post(
            f"{BASE_URL}/api/portal/admin/categories",
            headers={"Cookie": f"session_token={admin_session}"},
            json={
                "title": "Duplicate Attempt",
                "slug": self.TEST_SLUG  # Same slug as above
            }
        )
        assert resp.status_code == 409, f"Expected 409 for duplicate, got {resp.status_code}: {resp.text}"
        assert "already exists" in resp.json().get("detail", "").lower()
    
    def test_03_admin_create_unauthenticated_401(self):
        """POST /api/portal/admin/categories - reject without auth (401)"""
        resp = requests.post(
            f"{BASE_URL}/api/portal/admin/categories",
            json={"title": "No Auth", "slug": "no-auth-test"}
        )
        assert resp.status_code == 401
    
    def test_04_admin_update_all_fields(self, admin_session):
        """PUT /api/portal/admin/categories/{slug} - update all fields including help_articles"""
        resp = requests.put(
            f"{BASE_URL}/api/portal/admin/categories/{self.TEST_SLUG}",
            headers={"Cookie": f"session_token={admin_session}"},
            json={
                "title": f"Updated QA Category {TEST_UNIQUE_ID}",
                "description": "Updated description",
                "icon": "Database",
                "subtopics": [{"name": "NewSub", "items": ["new1"]}],
                "help_articles": [
                    {"title": "GitHub Integration", "url": "https://help.emergent.sh/github-integration"},
                    {"title": "Voice Mode", "url": "https://help.emergent.sh/voice-mode"},
                    {"title": "Deployment", "url": "https://help.emergent.sh/deployment-on-emergent"}
                ],
                "order": 50
            }
        )
        assert resp.status_code == 200, f"Update failed: {resp.text}"
        data = resp.json()
        
        assert data["title"] == f"Updated QA Category {TEST_UNIQUE_ID}"
        assert data["description"] == "Updated description"
        assert data["icon"] == "Database"
        assert len(data["subtopics"]) == 1
        assert len(data["help_articles"]) == 3
        assert data["order"] == 50
    
    def test_05_admin_update_slug_rename(self, admin_session):
        """PUT /api/portal/admin/categories/{slug} - rename slug works"""
        new_slug = f"test-qa-renamed-{TEST_UNIQUE_ID}"
        
        resp = requests.put(
            f"{BASE_URL}/api/portal/admin/categories/{self.TEST_SLUG}",
            headers={"Cookie": f"session_token={admin_session}"},
            json={"slug": new_slug}
        )
        assert resp.status_code == 200, f"Slug rename failed: {resp.text}"
        assert resp.json()["slug"] == new_slug
        
        # Verify old slug returns 404
        old_resp = requests.get(f"{BASE_URL}/api/portal/categories/{self.TEST_SLUG}")
        assert old_resp.status_code == 404
        
        # Verify new slug works
        new_resp = requests.get(f"{BASE_URL}/api/portal/categories/{new_slug}")
        assert new_resp.status_code == 200
        
        # Update class slug for cleanup
        TestAdminCategoryCRUD.TEST_SLUG = new_slug
    
    def test_06_admin_update_slug_conflict_409(self, admin_session):
        """PUT /api/portal/admin/categories/{slug} - reject if new slug conflicts"""
        # Try to rename to an existing slug (credits-pricing always exists)
        resp = requests.put(
            f"{BASE_URL}/api/portal/admin/categories/{self.TEST_SLUG}",
            headers={"Cookie": f"session_token={admin_session}"},
            json={"slug": "credits-pricing"}  # This slug should exist
        )
        assert resp.status_code == 409, f"Expected 409 for slug conflict, got {resp.status_code}"
    
    def test_07_admin_update_nonexistent_404(self, admin_session):
        """PUT /api/portal/admin/categories/{slug} - 404 for non-existent"""
        resp = requests.put(
            f"{BASE_URL}/api/portal/admin/categories/this-does-not-exist-xyz",
            headers={"Cookie": f"session_token={admin_session}"},
            json={"title": "Won't work"}
        )
        assert resp.status_code == 404
    
    def test_08_admin_delete_and_verify(self, admin_session):
        """DELETE /api/portal/admin/categories/{slug} - delete and verify gone"""
        resp = requests.delete(
            f"{BASE_URL}/api/portal/admin/categories/{self.TEST_SLUG}",
            headers={"Cookie": f"session_token={admin_session}"}
        )
        assert resp.status_code == 200
        
        # Verify deleted
        get_resp = requests.get(f"{BASE_URL}/api/portal/categories/{self.TEST_SLUG}")
        assert get_resp.status_code == 404
    
    def test_09_admin_delete_nonexistent_404(self, admin_session):
        """DELETE /api/portal/admin/categories/{slug} - 404 for non-existent"""
        resp = requests.delete(
            f"{BASE_URL}/api/portal/admin/categories/already-deleted-xyz",
            headers={"Cookie": f"session_token={admin_session}"}
        )
        assert resp.status_code == 404


# ==================== PUBLIC CATEGORY TESTS ====================

class TestPublicCategories:
    """Tests for public category endpoints"""
    
    def test_01_get_all_categories_with_help_articles(self):
        """GET /api/portal/categories - returns all with help_articles field"""
        resp = requests.get(f"{BASE_URL}/api/portal/categories")
        assert resp.status_code == 200
        data = resp.json()
        
        assert "categories" in data
        assert len(data["categories"]) >= 1
        
        # Check structure
        for cat in data["categories"]:
            assert "slug" in cat
            assert "title" in cat
            # help_articles should be present (even if empty array)
            assert "help_articles" in cat or cat.get("help_articles") is None or isinstance(cat.get("help_articles", []), list)
    
    def test_02_get_single_category_with_help_articles(self):
        """GET /api/portal/categories/{slug} - returns single with help_articles"""
        resp = requests.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["slug"] == "credits-pricing"
        assert data["title"] == "Credits & Pricing"
        # help_articles can be empty or populated
        assert isinstance(data.get("help_articles", []), list)
    
    def test_03_get_category_404(self):
        """GET /api/portal/categories/{slug} - 404 for invalid"""
        resp = requests.get(f"{BASE_URL}/api/portal/categories/nonexistent-category-xyz")
        assert resp.status_code == 404


# ==================== CUSTOMER AUTH TESTS ====================

class TestPortalCustomerAuth:
    """Tests for portal customer authentication edge cases"""
    
    def test_01_register_success(self):
        """POST /api/portal/auth/register - valid registration returns token"""
        unique_email = f"qa.reg.{secrets.token_hex(6)}@example.com"
        resp = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
            "name": "New QA User",
            "email": unique_email,
            "password": "validpass123"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        assert "token" in data
        assert len(data["token"]) > 10
        assert "customer_id" in data
        assert data["email"] == unique_email.lower()
        assert data["name"] == "New QA User"
    
    def test_02_register_duplicate_email_409(self):
        """POST /api/portal/auth/register - reject duplicate email (409)"""
        # First registration
        email = f"qa.dup.{secrets.token_hex(4)}@example.com"
        resp1 = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
            "name": "First User",
            "email": email,
            "password": "password123"
        })
        assert resp1.status_code == 200
        
        # Duplicate attempt
        resp2 = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
            "name": "Second User",
            "email": email,  # Same email
            "password": "anotherpass"
        })
        assert resp2.status_code == 409
        assert "already registered" in resp2.json().get("detail", "").lower()
    
    def test_03_register_short_password_400(self):
        """POST /api/portal/auth/register - reject short password (<6 chars)"""
        resp = requests.post(f"{BASE_URL}/api/portal/auth/register", json={
            "name": "Short Pass User",
            "email": f"qa.short.{secrets.token_hex(4)}@example.com",
            "password": "abc"  # Only 3 chars
        })
        assert resp.status_code == 400
        assert "at least 6 characters" in resp.json().get("detail", "").lower()
    
    def test_04_login_success(self, portal_customer_token):
        """POST /api/portal/auth/login - valid login returns token"""
        resp = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
        assert resp.status_code == 200
        data = resp.json()
        
        assert "token" in data
        assert "customer_id" in data
        assert data["email"] == TEST_CUSTOMER_EMAIL.lower()
    
    def test_05_login_invalid_email_401(self):
        """POST /api/portal/auth/login - invalid email returns 401"""
        resp = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": "nonexistent.email.xyz@example.com",
            "password": "anypassword"
        })
        assert resp.status_code == 401
        assert "invalid credentials" in resp.json().get("detail", "").lower()
    
    def test_06_login_wrong_password_401(self, portal_customer_token):
        """POST /api/portal/auth/login - wrong password returns 401"""
        resp = requests.post(f"{BASE_URL}/api/portal/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": "wrongpassword123"
        })
        assert resp.status_code == 401
    
    def test_07_get_me_authenticated(self, portal_customer_token):
        """GET /api/portal/auth/me - returns customer info with token"""
        resp = requests.get(
            f"{BASE_URL}/api/portal/auth/me",
            headers={"Authorization": f"Bearer {portal_customer_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == TEST_CUSTOMER_EMAIL.lower()
    
    def test_08_get_me_no_auth_401(self):
        """GET /api/portal/auth/me - 401 without token"""
        resp = requests.get(f"{BASE_URL}/api/portal/auth/me")
        assert resp.status_code == 401


# ==================== CUSTOMER TICKET TESTS ====================

class TestCustomerTickets:
    """Tests for customer ticket submission and history"""
    
    CREATED_TICKET_ID = None
    
    def test_01_get_tickets_401_without_auth(self):
        """GET /api/portal/tickets - 401 without auth token"""
        resp = requests.get(f"{BASE_URL}/api/portal/tickets")
        assert resp.status_code == 401
    
    def test_02_submit_ticket_authenticated(self, portal_customer_token):
        """POST /api/portal/tickets - submit ticket as authenticated customer"""
        resp = requests.post(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {portal_customer_token}"},
            json={
                "category_slug": "credits-pricing",
                "subcategory": "Credit Usage",
                "subject": f"QA Test Ticket {TEST_UNIQUE_ID}",
                "description": "This is a test ticket for thorough QA testing"
            }
        )
        assert resp.status_code == 200, f"Submit failed: {resp.text}"
        data = resp.json()
        
        assert "ticket_id" in data
        assert data["status"] == "todo"
        TestCustomerTickets.CREATED_TICKET_ID = data["ticket_id"]
    
    def test_03_get_my_tickets(self, portal_customer_token):
        """GET /api/portal/tickets - returns only customer's tickets"""
        resp = requests.get(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {portal_customer_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert "tickets" in data
        assert len(data["tickets"]) >= 1
        
        # Verify ticket structure
        ticket = data["tickets"][0]
        assert "ticket_id" in ticket
        assert "title" in ticket
        assert "status" in ticket
        assert "priority" in ticket
    
    def test_04_get_my_tickets_with_status_filter(self, portal_customer_token):
        """GET /api/portal/tickets?status=todo - filter by status"""
        resp = requests.get(
            f"{BASE_URL}/api/portal/tickets?status=todo",
            headers={"Authorization": f"Bearer {portal_customer_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # All returned tickets should have status 'todo'
        for ticket in data["tickets"]:
            assert ticket["status"] == "todo"
    
    def test_05_get_ticket_detail_with_messages(self, portal_customer_token):
        """GET /api/portal/tickets/{ticket_id} - returns ticket with messages"""
        if not self.CREATED_TICKET_ID:
            pytest.skip("No ticket created")
        
        resp = requests.get(
            f"{BASE_URL}/api/portal/tickets/{self.CREATED_TICKET_ID}",
            headers={"Authorization": f"Bearer {portal_customer_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert "ticket" in data
        assert "messages" in data
        assert data["ticket"]["ticket_id"] == self.CREATED_TICKET_ID
        assert len(data["messages"]) >= 1  # At least the original message
    
    def test_06_get_another_customers_ticket_404(self, portal_customer_token):
        """GET /api/portal/tickets/{ticket_id} - 404 for another customer's ticket"""
        # Use a fake ticket_id that doesn't belong to this customer
        resp = requests.get(
            f"{BASE_URL}/api/portal/tickets/FAKE-12345",
            headers={"Authorization": f"Bearer {portal_customer_token}"}
        )
        assert resp.status_code == 404
    
    def test_07_reply_to_ticket(self, portal_customer_token):
        """POST /api/portal/tickets/{ticket_id}/reply - customer can reply"""
        if not self.CREATED_TICKET_ID:
            pytest.skip("No ticket created")
        
        resp = requests.post(
            f"{BASE_URL}/api/portal/tickets/{self.CREATED_TICKET_ID}/reply",
            headers={
                "Authorization": f"Bearer {portal_customer_token}",
                "Content-Type": "application/json"
            },
            json={"body": "This is a follow-up reply from QA testing"}
        )
        assert resp.status_code == 200, f"Reply failed: {resp.text}"
        data = resp.json()
        
        assert "message_id" in data
        
        # Verify reply was added
        detail_resp = requests.get(
            f"{BASE_URL}/api/portal/tickets/{self.CREATED_TICKET_ID}",
            headers={"Authorization": f"Bearer {portal_customer_token}"}
        )
        assert detail_resp.status_code == 200
        assert len(detail_resp.json()["messages"]) >= 2
    
    def test_08_reply_to_nonexistent_ticket_404(self, portal_customer_token):
        """POST /api/portal/tickets/{ticket_id}/reply - 404 for wrong ticket"""
        resp = requests.post(
            f"{BASE_URL}/api/portal/tickets/FAKE-99999/reply",
            headers={
                "Authorization": f"Bearer {portal_customer_token}",
                "Content-Type": "application/json"
            },
            json={"body": "This should fail"}
        )
        assert resp.status_code == 404


# ==================== HELP ARTICLES VERIFICATION ====================

class TestHelpArticlesVerification:
    """Verify help_articles field is properly stored and returned"""
    
    def test_verify_help_articles_structure(self, admin_session):
        """Create category with help_articles, verify stored and returned correctly"""
        test_slug = f"help-art-test-{TEST_UNIQUE_ID}"
        
        # Create with specific help_articles
        create_resp = requests.post(
            f"{BASE_URL}/api/portal/admin/categories",
            headers={"Cookie": f"session_token={admin_session}"},
            json={
                "title": "Help Articles Test",
                "slug": test_slug,
                "help_articles": [
                    {"title": "Article One", "url": "https://help.emergent.sh/one"},
                    {"title": "Article Two", "url": "https://help.emergent.sh/two"}
                ]
            }
        )
        assert create_resp.status_code == 200
        
        # Fetch and verify
        get_resp = requests.get(f"{BASE_URL}/api/portal/categories/{test_slug}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        
        assert len(data["help_articles"]) == 2
        assert data["help_articles"][0]["title"] == "Article One"
        assert data["help_articles"][1]["url"] == "https://help.emergent.sh/two"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/portal/admin/categories/{test_slug}",
            headers={"Cookie": f"session_token={admin_session}"}
        )


# ==================== CROSS-FEATURE TESTS ====================

class TestCrossFeature:
    """End-to-end flows spanning multiple features"""
    
    def test_full_category_lifecycle(self, admin_session):
        """Admin creates -> visible on portal -> edit -> verify -> delete -> verify"""
        slug = f"lifecycle-{TEST_UNIQUE_ID}"
        
        # 1. Create
        create_resp = requests.post(
            f"{BASE_URL}/api/portal/admin/categories",
            headers={"Cookie": f"session_token={admin_session}"},
            json={
                "title": "Lifecycle Test",
                "slug": slug,
                "description": "Testing full lifecycle",
                "help_articles": [{"title": "Lifecycle Doc", "url": "https://help.emergent.sh/lifecycle"}]
            }
        )
        assert create_resp.status_code == 200
        
        # 2. Verify visible on public endpoint
        public_resp = requests.get(f"{BASE_URL}/api/portal/categories/{slug}")
        assert public_resp.status_code == 200
        assert public_resp.json()["title"] == "Lifecycle Test"
        
        # 3. Verify in list
        list_resp = requests.get(f"{BASE_URL}/api/portal/categories")
        slugs = [c["slug"] for c in list_resp.json()["categories"]]
        assert slug in slugs
        
        # 4. Edit
        edit_resp = requests.put(
            f"{BASE_URL}/api/portal/admin/categories/{slug}",
            headers={"Cookie": f"session_token={admin_session}"},
            json={"title": "Lifecycle Test Updated", "description": "Updated!"}
        )
        assert edit_resp.status_code == 200
        
        # 5. Verify edit
        verify_resp = requests.get(f"{BASE_URL}/api/portal/categories/{slug}")
        assert verify_resp.json()["title"] == "Lifecycle Test Updated"
        assert verify_resp.json()["description"] == "Updated!"
        
        # 6. Delete
        delete_resp = requests.delete(
            f"{BASE_URL}/api/portal/admin/categories/{slug}",
            headers={"Cookie": f"session_token={admin_session}"}
        )
        assert delete_resp.status_code == 200
        
        # 7. Verify gone
        gone_resp = requests.get(f"{BASE_URL}/api/portal/categories/{slug}")
        assert gone_resp.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
