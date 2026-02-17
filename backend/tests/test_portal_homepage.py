"""
Portal Homepage Redesign Backend API Tests
Tests for: /api/portal/inquiries, /api/portal/engineer-plans, /api/portal/categories
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPortalInquiriesAPI:
    """Tests for POST /api/portal/inquiries - creates tickets from inquiry forms"""
    
    def test_partner_inquiry_creates_ticket(self):
        """Partner inquiry should create a ticket with partner tag"""
        response = requests.post(f"{BASE_URL}/api/portal/inquiries", json={
            "name": "TEST_Partner User",
            "email": "test_partner@example.com",
            "company": "Test Company Inc",
            "message": "Interested in partner program",
            "type": "partner"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "ok"
        assert "ticket_id" in data
        assert data["ticket_id"].startswith("TKT-")
        print(f"PASS: Partner inquiry created ticket {data['ticket_id']}")
    
    def test_sales_inquiry_creates_ticket(self):
        """Sales inquiry should create a ticket with sales tag"""
        response = requests.post(f"{BASE_URL}/api/portal/inquiries", json={
            "name": "TEST_Sales User",
            "email": "test_sales@example.com",
            "message": "Enterprise inquiry",
            "type": "sales"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "ok"
        assert "ticket_id" in data
        print(f"PASS: Sales inquiry created ticket {data['ticket_id']}")
    
    def test_engineer_inquiry_creates_ticket(self):
        """Engineer inquiry should create a ticket with engineer tag and high priority"""
        response = requests.post(f"{BASE_URL}/api/portal/inquiries", json={
            "name": "TEST_Engineer User",
            "email": "test_eng@example.com",
            "message": "Need dedicated engineer",
            "type": "engineer"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "ok"
        assert "ticket_id" in data
        print(f"PASS: Engineer inquiry created ticket {data['ticket_id']}")
    
    def test_inquiry_requires_name(self):
        """Inquiry without name should fail validation"""
        response = requests.post(f"{BASE_URL}/api/portal/inquiries", json={
            "email": "test@example.com",
            "message": "Test message",
            "type": "partner"
        })
        # Pydantic validation should fail
        assert response.status_code == 422, f"Expected 422 for missing name, got {response.status_code}"
        print("PASS: Missing name returns 422")
    
    def test_inquiry_requires_email(self):
        """Inquiry without email should fail validation"""
        response = requests.post(f"{BASE_URL}/api/portal/inquiries", json={
            "name": "Test User",
            "message": "Test message",
            "type": "partner"
        })
        assert response.status_code == 422, f"Expected 422 for missing email, got {response.status_code}"
        print("PASS: Missing email returns 422")
    
    def test_inquiry_requires_type(self):
        """Inquiry without type should fail validation"""
        response = requests.post(f"{BASE_URL}/api/portal/inquiries", json={
            "name": "Test User",
            "email": "test@example.com",
            "message": "Test message"
        })
        assert response.status_code == 422, f"Expected 422 for missing type, got {response.status_code}"
        print("PASS: Missing type returns 422")


class TestEngineerPlansAPI:
    """Tests for GET /api/portal/engineer-plans"""
    
    def test_get_engineer_plans_returns_active_plans(self):
        """GET /api/portal/engineer-plans should return active plans"""
        response = requests.get(f"{BASE_URL}/api/portal/engineer-plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "plans" in data
        assert isinstance(data["plans"], list)
        print(f"PASS: Returned {len(data['plans'])} engineer plans")
    
    def test_engineer_plan_structure(self):
        """Each plan should have required fields"""
        response = requests.get(f"{BASE_URL}/api/portal/engineer-plans")
        assert response.status_code == 200
        data = response.json()
        
        if data["plans"]:
            plan = data["plans"][0]
            required_fields = ["plan_id", "title", "price", "hours", "period", "features", "active"]
            for field in required_fields:
                assert field in plan, f"Plan missing required field: {field}"
            
            # Verify the seeded plan data
            assert plan["title"] == "Dedicated Engineer"
            assert plan["price"] == 1000
            assert plan["hours"] == 10
            assert plan["period"] == "month"
            assert isinstance(plan["features"], list)
            assert len(plan["features"]) > 0
            print(f"PASS: Plan structure validated - {plan['title']} ${plan['price']}/{plan['period']}")


class TestPortalCategoriesAPI:
    """Tests for GET /api/portal/categories"""
    
    def test_get_categories_returns_list(self):
        """GET /api/portal/categories should return category list"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) > 0, "Expected at least one category"
        print(f"PASS: Returned {len(data['categories'])} categories")
    
    def test_category_structure(self):
        """Each category should have required fields"""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200
        data = response.json()
        
        for cat in data["categories"]:
            required_fields = ["title", "slug", "description", "icon"]
            for field in required_fields:
                assert field in cat, f"Category {cat.get('slug', 'unknown')} missing field: {field}"
        
        print(f"PASS: All {len(data['categories'])} categories have valid structure")
    
    def test_get_single_category(self):
        """GET /api/portal/categories/:slug should return category details"""
        response = requests.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["slug"] == "credits-pricing"
        assert data["title"] == "Credits & Pricing"
        print(f"PASS: Single category returned: {data['title']}")
    
    def test_get_nonexistent_category_returns_404(self):
        """GET /api/portal/categories/:slug for nonexistent slug should return 404"""
        response = requests.get(f"{BASE_URL}/api/portal/categories/nonexistent-slug-xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Nonexistent category returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
