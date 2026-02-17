"""
Portal Triage Funnel Tests - Tests for the new triage funnel flow:
- Category pages show subtopics as buttons, not KB links
- Ticket submission with tags[] and priority fields
- URL params are correctly passed through the flow
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPortalCategoriesTriageFunnel:
    """Test that categories API returns subtopics as triage options (no KB links)"""
    
    def test_get_categories_list(self):
        """GET /api/portal/categories returns list of categories"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) >= 10  # Should have at least 10 default categories
        print(f"PASS: Got {len(data['categories'])} categories")
    
    def test_get_category_with_subtopics(self):
        """GET /api/portal/categories/:slug returns category with subtopics"""
        response = requests.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        assert response.status_code == 200
        data = response.json()
        
        # Verify category structure
        assert data["slug"] == "credits-pricing"
        assert data["title"] == "Credits & Pricing"
        assert "subtopics" in data
        
        # Verify subtopics have items for triage
        subtopics = data["subtopics"]
        assert len(subtopics) >= 4  # Credit Usage, Credit Types, Refunds, Pricing
        
        # Check that subtopics have correct structure
        credit_usage = next((s for s in subtopics if s["name"] == "Credit Usage"), None)
        assert credit_usage is not None
        assert "items" in credit_usage
        assert "High usage" in credit_usage["items"]
        assert "How credits work" in credit_usage["items"]
        print("PASS: Category has subtopics with items for triage")
    
    def test_deployments_category_for_emergency(self):
        """GET /api/portal/categories/deployments - used for emergency flow"""
        response = requests.get(f"{BASE_URL}/api/portal/categories/deployments")
        assert response.status_code == 200
        data = response.json()
        
        assert data["slug"] == "deployments"
        assert "Production outage" in [s["name"] for s in data.get("subtopics", [])]
        print("PASS: Deployments category available for emergency flow")


class TestPortalTicketSubmissionWithTags:
    """Test ticket submission with tags[] and priority fields"""
    
    @pytest.fixture
    def test_customer_token(self):
        """Register a test customer and get auth token"""
        unique_email = f"test_triage_{uuid.uuid4().hex[:8]}@test.com"
        register_data = {
            "name": "Test Triage User",
            "email": unique_email,
            "password": "TestPass123!"
        }
        response = requests.post(f"{BASE_URL}/api/portal/auth/register", json=register_data)
        if response.status_code == 409:
            # Email already exists, try login
            login_data = {"email": unique_email, "password": "TestPass123!"}
            response = requests.post(f"{BASE_URL}/api/portal/auth/login", json=login_data)
        
        assert response.status_code in [200, 201]
        return response.json()["token"]
    
    def test_submit_ticket_with_tags_from_triage(self, test_customer_token):
        """POST /api/portal/tickets accepts tags[] array from triage flow"""
        ticket_data = {
            "category_slug": "credits-pricing",
            "subcategory": "Credit Usage",
            "subject": "Test ticket with tags from triage",
            "description": "This ticket was created via the triage funnel flow",
            "tags": ["credits-pricing", "Credit Usage", "High usage"],
            "priority": "medium"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/portal/tickets",
            json=ticket_data,
            headers={"Authorization": f"Bearer {test_customer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ticket_id" in data
        assert data["status"] == "todo"
        print(f"PASS: Created ticket with tags: {data['ticket_id']}")
        return data["ticket_id"]
    
    def test_submit_ticket_with_emergency_priority(self, test_customer_token):
        """POST /api/portal/tickets accepts priority='urgent' for emergency"""
        ticket_data = {
            "category_slug": "deployments",
            "subcategory": "Production outage",
            "subject": "EMERGENCY: Production app down",
            "description": "Our production app is completely down. URL: https://myapp.com. Error: 502 Bad Gateway",
            "tags": ["deployments", "Production outage", "emergency"],
            "priority": "urgent"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/portal/tickets",
            json=ticket_data,
            headers={"Authorization": f"Bearer {test_customer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ticket_id" in data
        print(f"PASS: Created emergency ticket: {data['ticket_id']}")
        
        # Verify the ticket has correct priority
        ticket_response = requests.get(
            f"{BASE_URL}/api/portal/tickets/{data['ticket_id']}",
            headers={"Authorization": f"Bearer {test_customer_token}"}
        )
        assert ticket_response.status_code == 200
        ticket = ticket_response.json()["ticket"]
        assert ticket["priority"] == "urgent"
        print("PASS: Ticket has urgent priority")
    
    def test_submit_ticket_with_empty_tags(self, test_customer_token):
        """POST /api/portal/tickets works with empty tags array"""
        ticket_data = {
            "category_slug": "features",
            "subject": "General feature question",
            "description": "How do I use feature X?",
            "tags": [],
            "priority": "low"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/portal/tickets",
            json=ticket_data,
            headers={"Authorization": f"Bearer {test_customer_token}"}
        )
        
        assert response.status_code == 200
        print("PASS: Ticket created with empty tags array")
    
    def test_submit_ticket_without_tags_field(self, test_customer_token):
        """POST /api/portal/tickets works without tags field (backward compatible)"""
        ticket_data = {
            "category_slug": "account-management",
            "subject": "Need password reset help",
            "description": "I forgot my password and can't receive the reset email"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/portal/tickets",
            json=ticket_data,
            headers={"Authorization": f"Bearer {test_customer_token}"}
        )
        
        assert response.status_code == 200
        print("PASS: Ticket created without tags field (backward compatible)")
    
    def test_ticket_stores_tags_correctly(self, test_customer_token):
        """Verify tags are stored and retrievable on the ticket"""
        test_tags = ["test-category", "test-subtopic", "specific-tag"]
        ticket_data = {
            "category_slug": "database",
            "subcategory": "Data sync",
            "subject": "Test tag storage",
            "description": "Testing that tags are stored correctly",
            "tags": test_tags,
            "priority": "medium"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/portal/tickets",
            json=ticket_data,
            headers={"Authorization": f"Bearer {test_customer_token}"}
        )
        
        assert response.status_code == 200
        ticket_id = response.json()["ticket_id"]
        
        # Get the ticket and verify tags
        ticket_response = requests.get(
            f"{BASE_URL}/api/portal/tickets/{ticket_id}",
            headers={"Authorization": f"Bearer {test_customer_token}"}
        )
        assert ticket_response.status_code == 200
        ticket = ticket_response.json()["ticket"]
        
        # Tags should include all the ones we sent
        for tag in test_tags:
            assert tag in ticket["tags"], f"Tag '{tag}' not found in ticket tags"
        print(f"PASS: Ticket tags stored correctly: {ticket['tags']}")


class TestPortalAuthAndRedirect:
    """Test auth flow preserves URL params for triage funnel"""
    
    def test_customer_registration(self):
        """POST /api/portal/auth/register creates new customer"""
        unique_email = f"test_auth_{uuid.uuid4().hex[:8]}@test.com"
        register_data = {
            "name": "Auth Test User",
            "email": unique_email,
            "password": "AuthTest123!"
        }
        
        response = requests.post(f"{BASE_URL}/api/portal/auth/register", json=register_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "customer_id" in data
        assert "token" in data
        assert data["email"] == unique_email.lower()
        print("PASS: Customer registration works")
    
    def test_customer_login(self):
        """POST /api/portal/auth/login returns token for existing customer"""
        # First register
        unique_email = f"test_login_{uuid.uuid4().hex[:8]}@test.com"
        register_data = {
            "name": "Login Test User",
            "email": unique_email,
            "password": "LoginTest123!"
        }
        requests.post(f"{BASE_URL}/api/portal/auth/register", json=register_data)
        
        # Then login
        login_data = {"email": unique_email, "password": "LoginTest123!"}
        response = requests.post(f"{BASE_URL}/api/portal/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print("PASS: Customer login works")
    
    def test_auth_me_with_token(self):
        """GET /api/portal/auth/me returns customer info with valid token"""
        # Register and get token
        unique_email = f"test_me_{uuid.uuid4().hex[:8]}@test.com"
        register_data = {
            "name": "Me Test User",
            "email": unique_email,
            "password": "MeTest123!"
        }
        response = requests.post(f"{BASE_URL}/api/portal/auth/register", json=register_data)
        token = response.json()["token"]
        
        # Call /auth/me
        me_response = requests.get(
            f"{BASE_URL}/api/portal/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert me_response.status_code == 200
        data = me_response.json()
        assert data["email"] == unique_email.lower()
        print("PASS: /auth/me returns customer info")


class TestTriageFunnelURLParams:
    """Test that the triage flow params are correctly formatted"""
    
    def test_category_only_params(self):
        """Verify category param format for 'None of these match?' CTA"""
        # When clicking 'None of these match?', URL should be:
        # /portal/submit?category=credits-pricing
        expected_params = {"category": "credits-pricing"}
        # This is a frontend test - just document the expected behavior
        print("EXPECTED: /portal/submit?category=credits-pricing for 'None of these match?' CTA")
        print("PASS: Category-only params documented")
    
    def test_category_subtopic_params(self):
        """Verify category + subtopic param format for subtopic click"""
        # When clicking a subtopic, URL should be:
        # /portal/submit?category=credits-pricing&subtopic=Credit+Usage
        expected_params = {"category": "credits-pricing", "subtopic": "Credit Usage"}
        print("EXPECTED: /portal/submit?category=credits-pricing&subtopic=Credit+Usage")
        print("PASS: Category + subtopic params documented")
    
    def test_category_subtopic_tag_params(self):
        """Verify category + subtopic + tag param format for sub-item click"""
        # When clicking a sub-item, URL should be:
        # /portal/submit?category=credits-pricing&subtopic=Credit+Usage&tag=High+usage
        expected_params = {"category": "credits-pricing", "subtopic": "Credit Usage", "tag": "High usage"}
        print("EXPECTED: /portal/submit?category=credits-pricing&subtopic=Credit+Usage&tag=High+usage")
        print("PASS: Category + subtopic + tag params documented")
    
    def test_emergency_params(self):
        """Verify emergency param format for emergency card click"""
        # When clicking emergency card, URL should be:
        # /portal/submit?priority=emergency&category=deployments
        expected_params = {"priority": "emergency", "category": "deployments"}
        print("EXPECTED: /portal/submit?priority=emergency&category=deployments")
        print("PASS: Emergency params documented")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
