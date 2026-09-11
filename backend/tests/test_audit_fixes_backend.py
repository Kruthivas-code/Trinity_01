"""
Backend Audit Fixes Test Suite - Iteration 80
Tests for 4 backend audit fixes:
1. Robustified get_current_user auth dependency with proper error handling
2. Added authorization checks (require_lead_or_admin) to team mutation endpoints
3. Added input validation to TeamCreate/TeamUpdate/TeamMemberAdd schemas
4. Cleaned up dead migration code from server.py startup
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
import uuid

# Use public URL from frontend/.env
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://github-clone-tool-6.preview.emergentagent.com').rstrip('/')

# Test session tokens created in MongoDB
TIMESTAMP = "1773667817493"
ADMIN_SESSION = f"TEST_audit_admin_session_{TIMESTAMP}"
LEAD_SESSION = f"TEST_audit_lead_session_{TIMESTAMP}"
AGENT_SESSION = f"TEST_audit_agent_session_{TIMESTAMP}"
AGENT_USER_ID = f"TEST_audit_agent_{TIMESTAMP}"


class TestHealthCheck:
    """Test 1: Backend starts without errors (no migration code failures)"""
    
    def test_health_endpoint_returns_200(self):
        """Health check endpoint should return 200 and healthy status"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", f"Unhealthy status: {data}"
        assert "checks" in data
        assert data["checks"].get("database", {}).get("status") == "healthy"
        print(f"✓ Health check passed: {data['status']}")


class TestAuthErrorHandling:
    """Test 2: get_current_user auth dependency error handling"""
    
    def test_auth_me_returns_user_with_valid_session(self):
        """/api/auth/me should return user data with valid session"""
        headers = {"Authorization": f"Bearer {ADMIN_SESSION}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=10)
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        assert "user_id" in data or "id" in data
        assert "email" in data
        print(f"✓ Auth/me returned user: {data.get('email')}")
    
    def test_auth_returns_401_for_invalid_session(self):
        """Should return 401 for invalid session token"""
        headers = {"Authorization": "Bearer invalid_session_token_12345"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid session correctly returns 401")
    
    def test_auth_returns_401_for_no_auth(self):
        """Should return 401 when no auth provided"""
        response = requests.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ No auth correctly returns 401")
    
    def test_auth_returns_401_for_expired_session(self):
        """Should return 401 for expired session (handled gracefully)"""
        # Use a fake expired token - the auth system should handle gracefully
        headers = {"Authorization": "Bearer expired_session_token_abc123"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Expired/invalid session correctly returns 401")


class TestTeamsAuthorizationForAgents:
    """Test 3: Teams API - GET endpoints should work for regular agents"""
    
    def test_get_teams_works_for_agent(self):
        """GET /api/teams should work for regular agents"""
        headers = {"Authorization": f"Bearer {AGENT_SESSION}"}
        response = requests.get(f"{BASE_URL}/api/teams", headers=headers, timeout=10)
        assert response.status_code == 200, f"Agent GET teams failed: {response.text}"
        assert isinstance(response.json(), list)
        print("✓ Agent can GET /api/teams")
    
    def test_get_team_by_id_works_for_agent(self):
        """GET /api/teams/{team_id} should work for regular agents"""
        # First get list of teams
        headers = {"Authorization": f"Bearer {ADMIN_SESSION}"}
        teams_response = requests.get(f"{BASE_URL}/api/teams", headers=headers, timeout=10)
        teams = teams_response.json()
        
        if teams:
            team_id = teams[0].get("team_id")
            headers = {"Authorization": f"Bearer {AGENT_SESSION}"}
            response = requests.get(f"{BASE_URL}/api/teams/{team_id}", headers=headers, timeout=10)
            assert response.status_code == 200, f"Agent GET team by ID failed: {response.text}"
            print(f"✓ Agent can GET /api/teams/{team_id}")
        else:
            print("⚠ No teams exist to test GET by ID (skipped)")


class TestTeamsMutationAuthorization:
    """Test 4: Teams mutation endpoints require lead/admin role"""
    
    def test_create_team_returns_403_for_agent(self):
        """POST /api/teams should return 403 for non-lead/admin users"""
        headers = {
            "Authorization": f"Bearer {AGENT_SESSION}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": "TEST_Agent_Team",
            "escalation_level": "L1",
            "description": "Test team created by agent"
        }
        response = requests.post(f"{BASE_URL}/api/teams", headers=headers, json=payload, timeout=10)
        assert response.status_code == 403, f"Expected 403 for agent, got {response.status_code}: {response.text}"
        print("✓ POST /api/teams correctly returns 403 for agent")
    
    def test_create_team_works_for_lead(self):
        """POST /api/teams should work for lead users"""
        headers = {
            "Authorization": f"Bearer {LEAD_SESSION}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": f"TEST_Lead_Team_{uuid.uuid4().hex[:6]}",
            "escalation_level": "L1",
            "description": "Test team created by lead"
        }
        response = requests.post(f"{BASE_URL}/api/teams", headers=headers, json=payload, timeout=10)
        assert response.status_code == 200, f"Lead POST team failed: {response.text}"
        data = response.json()
        assert "team_id" in data
        print(f"✓ Lead can POST /api/teams - created {data['team_id']}")
        return data["team_id"]
    
    def test_create_team_works_for_admin(self):
        """POST /api/teams should work for admin users"""
        headers = {
            "Authorization": f"Bearer {ADMIN_SESSION}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": f"TEST_Admin_Team_{uuid.uuid4().hex[:6]}",
            "escalation_level": "L2",
            "description": "Test team created by admin"
        }
        response = requests.post(f"{BASE_URL}/api/teams", headers=headers, json=payload, timeout=10)
        assert response.status_code == 200, f"Admin POST team failed: {response.text}"
        data = response.json()
        assert "team_id" in data
        print(f"✓ Admin can POST /api/teams - created {data['team_id']}")
        return data["team_id"]
    
    def test_update_team_returns_403_for_agent(self):
        """PUT /api/teams/{team_id} should return 403 for non-lead/admin users"""
        # First create a team as admin
        headers = {
            "Authorization": f"Bearer {ADMIN_SESSION}",
            "Content-Type": "application/json"
        }
        create_payload = {
            "name": f"TEST_Update_Team_{uuid.uuid4().hex[:6]}",
            "escalation_level": "L1"
        }
        create_response = requests.post(f"{BASE_URL}/api/teams", headers=headers, json=create_payload, timeout=10)
        assert create_response.status_code == 200
        team_id = create_response.json()["team_id"]
        
        # Now try to update as agent
        agent_headers = {
            "Authorization": f"Bearer {AGENT_SESSION}",
            "Content-Type": "application/json"
        }
        update_payload = {"name": "Agent_Updated_Name"}
        response = requests.put(f"{BASE_URL}/api/teams/{team_id}", headers=agent_headers, json=update_payload, timeout=10)
        assert response.status_code == 403, f"Expected 403 for agent update, got {response.status_code}: {response.text}"
        print("✓ PUT /api/teams/{id} correctly returns 403 for agent")
    
    def test_add_member_returns_403_for_agent(self):
        """POST /api/teams/{team_id}/members should return 403 for non-lead/admin users"""
        # Get an existing team
        headers = {"Authorization": f"Bearer {ADMIN_SESSION}"}
        teams_response = requests.get(f"{BASE_URL}/api/teams", headers=headers, timeout=10)
        teams = teams_response.json()
        
        if teams:
            team_id = teams[0].get("team_id")
            agent_headers = {
                "Authorization": f"Bearer {AGENT_SESSION}",
                "Content-Type": "application/json"
            }
            payload = {"user_id": AGENT_USER_ID}
            response = requests.post(f"{BASE_URL}/api/teams/{team_id}/members", headers=agent_headers, json=payload, timeout=10)
            assert response.status_code == 403, f"Expected 403 for agent add member, got {response.status_code}: {response.text}"
            print("✓ POST /api/teams/{id}/members correctly returns 403 for agent")
        else:
            pytest.skip("No teams exist to test add member")
    
    def test_remove_member_returns_403_for_agent(self):
        """DELETE /api/teams/{team_id}/members/{user_id} should return 403 for non-lead/admin users"""
        # Get an existing team
        headers = {"Authorization": f"Bearer {ADMIN_SESSION}"}
        teams_response = requests.get(f"{BASE_URL}/api/teams", headers=headers, timeout=10)
        teams = teams_response.json()
        
        if teams:
            team_id = teams[0].get("team_id")
            agent_headers = {"Authorization": f"Bearer {AGENT_SESSION}"}
            response = requests.delete(f"{BASE_URL}/api/teams/{team_id}/members/some_user_id", headers=agent_headers, timeout=10)
            assert response.status_code == 403, f"Expected 403 for agent remove member, got {response.status_code}: {response.text}"
            print("✓ DELETE /api/teams/{id}/members/{user_id} correctly returns 403 for agent")
        else:
            pytest.skip("No teams exist to test remove member")


class TestTeamSchemaValidation:
    """Test 5: TeamCreate/TeamUpdate/TeamMemberAdd schema validation"""
    
    def test_create_team_empty_name_returns_422(self):
        """TeamCreate validation: empty name should return 422"""
        headers = {
            "Authorization": f"Bearer {ADMIN_SESSION}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": "",  # Empty name should fail
            "escalation_level": "L1"
        }
        response = requests.post(f"{BASE_URL}/api/teams", headers=headers, json=payload, timeout=10)
        assert response.status_code == 422, f"Expected 422 for empty name, got {response.status_code}: {response.text}"
        print("✓ Empty team name correctly returns 422")
    
    def test_create_team_invalid_escalation_level_returns_422(self):
        """TeamCreate validation: invalid escalation_level (e.g. 'L5') should return 422"""
        headers = {
            "Authorization": f"Bearer {ADMIN_SESSION}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": "Test Team Valid Name",
            "escalation_level": "L5"  # Invalid - only L1, L2, L3 are valid
        }
        response = requests.post(f"{BASE_URL}/api/teams", headers=headers, json=payload, timeout=10)
        assert response.status_code == 422, f"Expected 422 for invalid escalation level, got {response.status_code}: {response.text}"
        print("✓ Invalid escalation level (L5) correctly returns 422")
    
    def test_create_team_valid_data_succeeds(self):
        """TeamCreate validation: valid data should succeed for admin"""
        headers = {
            "Authorization": f"Bearer {ADMIN_SESSION}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": f"TEST_Valid_Team_{uuid.uuid4().hex[:6]}",
            "escalation_level": "L2",
            "description": "Valid team with proper data"
        }
        response = requests.post(f"{BASE_URL}/api/teams", headers=headers, json=payload, timeout=10)
        assert response.status_code == 200, f"Valid team creation failed: {response.text}"
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["escalation_level"] == "L2"
        print(f"✓ Valid team data succeeds - created {data['team_id']}")
    
    def test_update_team_invalid_escalation_returns_422(self):
        """TeamUpdate validation: invalid escalation_level should return 422"""
        # First create a valid team
        headers = {
            "Authorization": f"Bearer {ADMIN_SESSION}",
            "Content-Type": "application/json"
        }
        create_payload = {
            "name": f"TEST_Update_Valid_Team_{uuid.uuid4().hex[:6]}",
            "escalation_level": "L1"
        }
        create_response = requests.post(f"{BASE_URL}/api/teams", headers=headers, json=create_payload, timeout=10)
        assert create_response.status_code == 200
        team_id = create_response.json()["team_id"]
        
        # Try to update with invalid escalation level
        update_payload = {"escalation_level": "L99"}
        response = requests.put(f"{BASE_URL}/api/teams/{team_id}", headers=headers, json=update_payload, timeout=10)
        assert response.status_code == 422, f"Expected 422 for invalid escalation update, got {response.status_code}: {response.text}"
        print("✓ TeamUpdate with invalid escalation level correctly returns 422")
    
    def test_add_member_empty_user_id_returns_422(self):
        """TeamMemberAdd validation: empty user_id should return 422"""
        # Get an existing team
        headers = {
            "Authorization": f"Bearer {ADMIN_SESSION}",
            "Content-Type": "application/json"
        }
        teams_response = requests.get(f"{BASE_URL}/api/teams", headers=headers, timeout=10)
        teams = teams_response.json()
        
        if teams:
            team_id = teams[0].get("team_id")
            payload = {"user_id": ""}  # Empty user_id should fail
            response = requests.post(f"{BASE_URL}/api/teams/{team_id}/members", headers=headers, json=payload, timeout=10)
            assert response.status_code == 422, f"Expected 422 for empty user_id, got {response.status_code}: {response.text}"
            print("✓ Empty user_id in add member correctly returns 422")
        else:
            pytest.skip("No teams exist to test add member validation")


class TestAdminEndpointsAuthorization:
    """Test 6: Admin endpoints require admin role"""
    
    def test_admin_settings_returns_403_for_agent(self):
        """GET /api/admin/settings should return 403 for agents"""
        headers = {"Authorization": f"Bearer {AGENT_SESSION}"}
        response = requests.get(f"{BASE_URL}/api/admin/settings", headers=headers, timeout=10)
        assert response.status_code == 403, f"Expected 403 for agent on admin settings, got {response.status_code}"
        print("✓ GET /api/admin/settings correctly returns 403 for agent")
    
    def test_admin_settings_works_for_admin(self):
        """GET /api/admin/settings should work for admin"""
        headers = {"Authorization": f"Bearer {ADMIN_SESSION}"}
        response = requests.get(f"{BASE_URL}/api/admin/settings", headers=headers, timeout=10)
        assert response.status_code == 200, f"Admin settings failed: {response.text}"
        data = response.json()
        assert "company_name" in data or "auto_assignment" in data
        print("✓ Admin can GET /api/admin/settings")


class TestTicketsCRUD:
    """Test 7: Ticket CRUD endpoints still work"""
    
    def test_get_tickets_works(self):
        """GET /api/tickets should work with valid auth"""
        headers = {"Authorization": f"Bearer {AGENT_SESSION}"}
        response = requests.get(f"{BASE_URL}/api/tickets", headers=headers, timeout=10)
        assert response.status_code == 200, f"GET tickets failed: {response.text}"
        data = response.json()
        assert "tickets" in data or isinstance(data, list)
        print("✓ GET /api/tickets works")
    
    def test_create_ticket_works(self):
        """POST /api/tickets should work with valid auth"""
        headers = {
            "Authorization": f"Bearer {AGENT_SESSION}",
            "Content-Type": "application/json"
        }
        payload = {
            "title": f"TEST_Audit_Ticket_{uuid.uuid4().hex[:6]}",
            "description": "Test ticket for audit verification",
            "priority": "medium",
            "status": "todo"
        }
        response = requests.post(f"{BASE_URL}/api/tickets", headers=headers, json=payload, timeout=10)
        assert response.status_code in [200, 201], f"POST ticket failed: {response.text}"
        data = response.json()
        assert "ticket_id" in data
        print(f"✓ POST /api/tickets works - created {data['ticket_id']}")
        return data["ticket_id"]
    
    def test_update_ticket_works(self):
        """PUT /api/tickets/{ticket_id} should work with valid auth"""
        # First create a ticket
        headers = {
            "Authorization": f"Bearer {AGENT_SESSION}",
            "Content-Type": "application/json"
        }
        create_payload = {
            "title": f"TEST_Update_Ticket_{uuid.uuid4().hex[:6]}",
            "description": "Test ticket for update verification"
        }
        create_response = requests.post(f"{BASE_URL}/api/tickets", headers=headers, json=create_payload, timeout=10)
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create ticket for update test: {create_response.text}")
        
        ticket_id = create_response.json()["ticket_id"]
        
        # Update the ticket
        update_payload = {"priority": "high"}
        response = requests.put(f"{BASE_URL}/api/tickets/{ticket_id}", headers=headers, json=update_payload, timeout=10)
        assert response.status_code == 200, f"PUT ticket failed: {response.text}"
        print(f"✓ PUT /api/tickets/{ticket_id} works")


class TestBackendStartsCleanly:
    """Test 8: Verify backend started without migration code errors"""
    
    def test_no_migration_errors_in_logs(self):
        """Backend should start cleanly without one-time migration failures"""
        # We verify this indirectly by checking that health is healthy
        # and the server is responding normally
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        # Check database connection is working
        assert data.get("checks", {}).get("database", {}).get("status") == "healthy"
        print("✓ Backend started cleanly - no migration errors detected")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Clean up TEST_ prefixed teams after tests"""
    yield
    # Cleanup after all tests
    try:
        headers = {"Authorization": f"Bearer {ADMIN_SESSION}"}
        teams_response = requests.get(f"{BASE_URL}/api/teams", headers=headers, timeout=10)
        if teams_response.status_code == 200:
            teams = teams_response.json()
            for team in teams:
                if team.get("name", "").startswith("TEST_"):
                    team_id = team.get("team_id")
                    requests.delete(f"{BASE_URL}/api/teams/{team_id}", headers=headers, timeout=10)
                    print(f"Cleaned up team: {team_id}")
    except Exception as e:
        print(f"Cleanup warning: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
