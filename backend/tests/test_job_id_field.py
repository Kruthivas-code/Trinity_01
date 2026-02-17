"""
Test Job ID field feature on the ticket submit form.
Job ID is required for: agent-ai, deployments, database, mobile-builds, features, custom-domain
and for credits-pricing when subtopic is 'Credit Usage'.
Job ID should NOT appear for: subscription-management, account-management, security-compliance
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Categories where job_id is mandatory
JOB_ID_REQUIRED_CATEGORIES = ['agent-ai', 'deployments', 'database', 'mobile-builds', 'features', 'custom-domain']
# Categories where job_id is NOT required
JOB_ID_NOT_REQUIRED_CATEGORIES = ['subscription-management', 'account-management', 'security-compliance', 'credits-pricing']


class TestSetup:
    """Test fixtures and setup"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    @pytest.fixture(scope="class")
    def test_customer(self, session):
        """Register or login a test customer"""
        email = f"test_jobid_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPass123!"
        
        # Try to register
        register_resp = session.post(f"{BASE_URL}/api/portal/auth/register", json={
            "name": "Job ID Tester",
            "email": email,
            "password": password
        })
        
        if register_resp.status_code == 201 or register_resp.status_code == 200:
            data = register_resp.json()
            return {"token": data["token"], "email": email, "customer_id": data["customer_id"]}
        elif register_resp.status_code == 409:
            # Email already registered, try to login
            login_resp = session.post(f"{BASE_URL}/api/portal/auth/login", json={
                "email": email,
                "password": password
            })
            if login_resp.status_code == 200:
                data = login_resp.json()
                return {"token": data["token"], "email": email, "customer_id": data["customer_id"]}
        
        pytest.skip(f"Could not create test customer: {register_resp.text}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, test_customer):
        return {"Authorization": f"Bearer {test_customer['token']}", "Content-Type": "application/json"}


class TestBackendJobIdStorage(TestSetup):
    """Backend API tests for job_id field storage"""
    
    def test_ticket_submission_with_job_id(self, session, test_customer, auth_headers):
        """Test that job_id is stored when provided in ticket submission"""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "deployments",
            "subcategory": "Build failures",
            "subject": "TEST: Ticket with Job ID",
            "description": "Test ticket to verify job_id is stored correctly",
            "job_id": job_id,
            "tags": ["deployments", "test"],
            "priority": "medium"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "ticket_id" in data, "Response should contain ticket_id"
        
        # Verify ticket was created - fetch and check job_id is stored
        ticket_id = data["ticket_id"]
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{ticket_id}", headers=auth_headers)
        assert get_response.status_code == 200, f"Failed to fetch ticket: {get_response.text}"
        
        ticket_data = get_response.json()
        assert "ticket" in ticket_data, "Response should contain ticket object"
        ticket = ticket_data["ticket"]
        assert ticket.get("job_id") == job_id, f"Expected job_id={job_id}, got {ticket.get('job_id')}"
        print(f"PASS: job_id '{job_id}' correctly stored on ticket {ticket_id}")
    
    def test_ticket_submission_without_job_id_for_non_required_category(self, session, test_customer, auth_headers):
        """Test that ticket can be created without job_id for categories that don't require it"""
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "subscription-management",
            "subcategory": "Plans",
            "subject": "TEST: Ticket without Job ID",
            "description": "Test ticket to verify ticket creation works without job_id",
            "tags": ["subscription-management", "test"],
            "priority": "medium"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "ticket_id" in data, "Response should contain ticket_id"
        
        # Verify ticket was created with null job_id
        ticket_id = data["ticket_id"]
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{ticket_id}", headers=auth_headers)
        assert get_response.status_code == 200, f"Failed to fetch ticket: {get_response.text}"
        
        ticket_data = get_response.json()
        ticket = ticket_data["ticket"]
        # job_id should be null or not present
        assert ticket.get("job_id") is None or "job_id" not in ticket, f"job_id should be null, got {ticket.get('job_id')}"
        print(f"PASS: Ticket {ticket_id} created without job_id for subscription-management category")
    
    def test_ticket_submission_with_empty_job_id(self, session, test_customer, auth_headers):
        """Test that empty job_id is stored as null/None"""
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "account-management",
            "subcategory": "Password reset",
            "subject": "TEST: Ticket with empty Job ID",
            "description": "Test ticket to verify empty job_id becomes null",
            "job_id": "",
            "tags": ["account-management", "test"],
            "priority": "low"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        ticket_id = data["ticket_id"]
        
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{ticket_id}", headers=auth_headers)
        ticket_data = get_response.json()
        ticket = ticket_data["ticket"]
        # Empty string job_id should be stored as null
        assert ticket.get("job_id") is None, f"Empty job_id should be null, got {ticket.get('job_id')}"
        print(f"PASS: Empty job_id correctly stored as null on ticket {ticket_id}")
    
    def test_ticket_submission_job_id_for_deployments(self, session, test_customer, auth_headers):
        """Test ticket submission with job_id for deployments category"""
        job_id = f"job_deploy_{uuid.uuid4().hex[:8]}"
        
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "deployments",
            "subcategory": "Post-deployment issues",
            "subject": "TEST: Deployment issue with Job ID",
            "description": "Test deployment issue ticket",
            "job_id": job_id,
            "tags": ["deployments"],
            "priority": "high"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{data['ticket_id']}", headers=auth_headers)
        ticket = get_response.json()["ticket"]
        assert ticket.get("job_id") == job_id, f"job_id not stored correctly for deployments"
        print(f"PASS: deployments category stores job_id correctly")
    
    def test_ticket_submission_job_id_for_agent_ai(self, session, test_customer, auth_headers):
        """Test ticket submission with job_id for agent-ai category"""
        job_id = f"job_ai_{uuid.uuid4().hex[:8]}"
        
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "agent-ai",
            "subcategory": "Bugs",
            "subject": "TEST: Agent AI issue with Job ID",
            "description": "Test agent AI issue ticket",
            "job_id": job_id,
            "tags": ["agent-ai"],
            "priority": "medium"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{data['ticket_id']}", headers=auth_headers)
        ticket = get_response.json()["ticket"]
        assert ticket.get("job_id") == job_id, f"job_id not stored correctly for agent-ai"
        print(f"PASS: agent-ai category stores job_id correctly")
    
    def test_ticket_submission_job_id_for_features(self, session, test_customer, auth_headers):
        """Test ticket submission with job_id for features category"""
        job_id = f"job_feat_{uuid.uuid4().hex[:8]}"
        
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "features",
            "subcategory": "GitHub integration",
            "subject": "TEST: Feature issue with Job ID",
            "description": "Test feature issue ticket",
            "job_id": job_id,
            "tags": ["features"],
            "priority": "medium"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{data['ticket_id']}", headers=auth_headers)
        ticket = get_response.json()["ticket"]
        assert ticket.get("job_id") == job_id, f"job_id not stored correctly for features"
        print(f"PASS: features category stores job_id correctly")
    
    def test_ticket_submission_job_id_for_custom_domain(self, session, test_customer, auth_headers):
        """Test ticket submission with job_id for custom-domain category"""
        job_id = f"job_dom_{uuid.uuid4().hex[:8]}"
        
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "custom-domain",
            "subcategory": "DNS",
            "subject": "TEST: Custom domain issue with Job ID",
            "description": "Test custom domain issue ticket",
            "job_id": job_id,
            "tags": ["custom-domain"],
            "priority": "medium"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{data['ticket_id']}", headers=auth_headers)
        ticket = get_response.json()["ticket"]
        assert ticket.get("job_id") == job_id, f"job_id not stored correctly for custom-domain"
        print(f"PASS: custom-domain category stores job_id correctly")
    
    def test_ticket_submission_job_id_for_database(self, session, test_customer, auth_headers):
        """Test ticket submission with job_id for database category"""
        job_id = f"job_db_{uuid.uuid4().hex[:8]}"
        
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "database",
            "subcategory": "Data sync",
            "subject": "TEST: Database issue with Job ID",
            "description": "Test database issue ticket",
            "job_id": job_id,
            "tags": ["database"],
            "priority": "medium"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{data['ticket_id']}", headers=auth_headers)
        ticket = get_response.json()["ticket"]
        assert ticket.get("job_id") == job_id, f"job_id not stored correctly for database"
        print(f"PASS: database category stores job_id correctly")
    
    def test_ticket_submission_job_id_for_mobile_builds(self, session, test_customer, auth_headers):
        """Test ticket submission with job_id for mobile-builds category"""
        job_id = f"job_mob_{uuid.uuid4().hex[:8]}"
        
        response = session.post(f"{BASE_URL}/api/portal/tickets", json={
            "category_slug": "mobile-builds",
            "subcategory": "Technical issues",
            "subject": "TEST: Mobile build issue with Job ID",
            "description": "Test mobile build issue ticket",
            "job_id": job_id,
            "tags": ["mobile-builds"],
            "priority": "medium"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        get_response = session.get(f"{BASE_URL}/api/portal/tickets/{data['ticket_id']}", headers=auth_headers)
        ticket = get_response.json()["ticket"]
        assert ticket.get("job_id") == job_id, f"job_id not stored correctly for mobile-builds"
        print(f"PASS: mobile-builds category stores job_id correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
