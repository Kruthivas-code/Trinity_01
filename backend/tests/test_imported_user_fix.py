"""
Tests for @imported.local email fix and defensive assignee validation
======================================================================

Tests:
1. PUT /api/tickets/{ticket_id} - defensive validation passes for VALID user_id
2. PUT /api/tickets/{ticket_id} - defensive validation returns 400 for INVALID user_id
3. PUT /api/tickets/{ticket_id} - unassigning (assignee_id: null) still works
4. POST /api/tickets/{ticket_id}/assign - returns 400 for INVALID user_id
5. POST /api/tickets/{ticket_id}/assign - succeeds for VALID user_id
6. Auth flow _resolve_imported_user function - test logic via unit test
7. Migration script runs in dry-run mode without errors
"""

import pytest
import requests
import os
import sys
import uuid
from datetime import datetime, timezone

# For migration script test
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test session token and user - will be created in setup
TEST_USER_ID = None
TEST_SESSION_TOKEN = None
TEST_TICKET_ID = None


@pytest.fixture(scope="module")
def api_session():
    """Create a requests session for API calls."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_and_session(api_session):
    """Create a test user and session in MongoDB for authenticated API calls."""
    global TEST_USER_ID, TEST_SESSION_TOKEN
    
    import subprocess
    
    timestamp = int(datetime.now().timestamp())
    TEST_USER_ID = f"test_user_{timestamp}"
    TEST_SESSION_TOKEN = f"test_session_{timestamp}"
    test_email = f"test.user.{timestamp}@example.com"
    
    # Create test user and session in MongoDB
    mongo_script = f"""
    use('test_database');
    db.users.insertOne({{
      user_id: '{TEST_USER_ID}',
      email: '{test_email}',
      name: 'Test User ImportFix',
      picture: 'https://via.placeholder.com/150',
      role: 'admin',
      created_at: new Date()
    }});
    db.user_sessions.insertOne({{
      user_id: '{TEST_USER_ID}',
      session_token: '{TEST_SESSION_TOKEN}',
      expires_at: new Date(Date.now() + 7*24*60*60*1000),
      created_at: new Date()
    }});
    print('CREATED');
    """
    
    result = subprocess.run(
        ["mongosh", "--quiet", "--eval", mongo_script],
        capture_output=True,
        text=True
    )
    
    assert "CREATED" in result.stdout or result.returncode == 0, f"Failed to create test user: {result.stderr}"
    
    # Add auth header to session
    api_session.headers.update({
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}",
        "Cookie": f"session_token={TEST_SESSION_TOKEN}"
    })
    api_session.cookies.set("session_token", TEST_SESSION_TOKEN)
    
    yield {"user_id": TEST_USER_ID, "session_token": TEST_SESSION_TOKEN}
    
    # Cleanup after tests
    cleanup_script = f"""
    use('test_database');
    db.users.deleteOne({{ user_id: '{TEST_USER_ID}' }});
    db.user_sessions.deleteOne({{ session_token: '{TEST_SESSION_TOKEN}' }});
    print('CLEANED');
    """
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True, text=True)


@pytest.fixture(scope="module")
def test_ticket(api_session, test_user_and_session):
    """Create a test ticket for assignment tests."""
    global TEST_TICKET_ID
    
    response = api_session.post(
        f"{BASE_URL}/api/tickets",
        json={
            "title": "TEST_ImportFix Test Ticket",
            "description": "Test ticket for imported user fix validation",
            "status": "todo",
            "priority": "medium",
            "customer_email": "test@example.com"
        }
    )
    
    assert response.status_code in [200, 201], f"Failed to create test ticket: {response.status_code} {response.text}"
    ticket_data = response.json()
    TEST_TICKET_ID = ticket_data.get("ticket_id")
    
    yield ticket_data
    
    # Cleanup ticket after tests
    if TEST_TICKET_ID:
        api_session.delete(f"{BASE_URL}/api/tickets/{TEST_TICKET_ID}")


class TestDefensiveAssigneeValidation:
    """Tests for defensive assignee_id validation in update_ticket and assign_ticket."""
    
    def test_update_ticket_with_valid_user_id_succeeds(self, api_session, test_user_and_session, test_ticket):
        """PUT /api/tickets/{ticket_id} - assigning with a VALID user_id succeeds."""
        ticket_id = test_ticket["ticket_id"]
        valid_user_id = test_user_and_session["user_id"]
        
        response = api_session.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"assignee_id": valid_user_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("assignee_id") == valid_user_id, "Assignee should be set to the valid user"
        print(f"✓ PUT /api/tickets/{ticket_id} with valid user_id={valid_user_id} succeeded")
    
    def test_update_ticket_with_invalid_user_id_returns_400(self, api_session, test_ticket):
        """PUT /api/tickets/{ticket_id} - assigning with an INVALID/nonexistent user_id returns 400."""
        ticket_id = test_ticket["ticket_id"]
        invalid_user_id = f"nonexistent_user_{uuid.uuid4().hex[:8]}"
        
        response = api_session.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"assignee_id": invalid_user_id}
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid user, got {response.status_code}: {response.text}"
        data = response.json()
        assert "invalid" in data.get("detail", "").lower() or "does not exist" in data.get("detail", "").lower(), \
            f"Error message should indicate invalid user: {data}"
        print(f"✓ PUT /api/tickets/{ticket_id} with invalid user_id={invalid_user_id} correctly returned 400")
    
    def test_update_ticket_unassign_with_null_succeeds(self, api_session, test_user_and_session, test_ticket):
        """PUT /api/tickets/{ticket_id} - unassigning (assignee_id: null) still works."""
        ticket_id = test_ticket["ticket_id"]
        valid_user_id = test_user_and_session["user_id"]
        
        # First assign to valid user
        assign_response = api_session.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"assignee_id": valid_user_id}
        )
        assert assign_response.status_code == 200, "Setup: assignment should succeed"
        
        # Now unassign with null
        unassign_response = api_session.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"assignee_id": None}
        )
        
        assert unassign_response.status_code == 200, f"Expected 200 for unassign, got {unassign_response.status_code}: {unassign_response.text}"
        data = unassign_response.json()
        assert data.get("assignee_id") is None, "Assignee should be null after unassign"
        print(f"✓ PUT /api/tickets/{ticket_id} unassign with null succeeded")
    
    def test_assign_endpoint_with_invalid_user_id_returns_400(self, api_session, test_ticket):
        """POST /api/tickets/{ticket_id}/assign - assigning with INVALID user_id returns 400."""
        ticket_id = test_ticket["ticket_id"]
        invalid_user_id = f"fake_user_{uuid.uuid4().hex[:8]}"
        
        response = api_session.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/assign",
            json={"assignee_id": invalid_user_id}
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid user, got {response.status_code}: {response.text}"
        data = response.json()
        assert "invalid" in data.get("detail", "").lower() or "does not exist" in data.get("detail", "").lower(), \
            f"Error message should indicate invalid user: {data}"
        print(f"✓ POST /api/tickets/{ticket_id}/assign with invalid user_id correctly returned 400")
    
    def test_assign_endpoint_with_valid_user_id_succeeds(self, api_session, test_user_and_session, test_ticket):
        """POST /api/tickets/{ticket_id}/assign - assigning with VALID user_id succeeds."""
        ticket_id = test_ticket["ticket_id"]
        valid_user_id = test_user_and_session["user_id"]
        
        response = api_session.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/assign",
            json={"assignee_id": valid_user_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("assignee_id") == valid_user_id, "Assignee should be set to the valid user"
        print(f"✓ POST /api/tickets/{ticket_id}/assign with valid user_id={valid_user_id} succeeded")


class TestResolveImportedUserLogic:
    """Tests for the _resolve_imported_user function in auth.py."""
    
    def test_resolve_imported_user_function_exists(self):
        """Verify _resolve_imported_user function exists and can be imported."""
        from routes.auth import _resolve_imported_user
        
        assert callable(_resolve_imported_user), "_resolve_imported_user should be callable"
        print("✓ _resolve_imported_user function exists and is callable")
    
    def test_resolve_imported_user_returns_false_for_unknown_email(self):
        """_resolve_imported_user returns False when email has no Atlas mapping."""
        from routes.auth import _resolve_imported_user
        
        # Use a clearly fake email that won't exist in Atlas
        fake_email = f"nonexistent_{uuid.uuid4().hex}@fakeprovider.com"
        result = _resolve_imported_user(fake_email)
        
        # Should return False because no atlas_user_id can be found
        assert result is False, f"Expected False for unknown email, got {result}"
        print(f"✓ _resolve_imported_user returns False for unknown email: {fake_email}")
    
    def test_resolve_imported_user_with_imported_placeholder(self):
        """Test _resolve_imported_user logic for @imported.local placeholder scenario."""
        import subprocess
        
        # This test simulates the scenario but doesn't require actual @imported.local records
        # because they don't exist in the preview environment.
        
        # Create a test imported user with placeholder email AND atlas_user_id
        timestamp = int(datetime.now().timestamp())
        test_imported_user_id = f"test_imported_{timestamp}"
        fake_atlas_id = f"atlas_test_{timestamp}"
        placeholder_email = f"test_{timestamp}@imported.local"
        
        # Create the imported user record
        create_script = f"""
        use('test_database');
        db.users.insertOne({{
          user_id: '{test_imported_user_id}',
          email: '{placeholder_email}',
          atlas_user_id: '{fake_atlas_id}',
          name: 'Test Imported User',
          created_at: new Date()
        }});
        print('CREATED_IMPORTED');
        """
        
        result = subprocess.run(
            ["mongosh", "--quiet", "--eval", create_script],
            capture_output=True,
            text=True
        )
        
        try:
            # The _resolve_imported_user function queries Atlas API to find real email
            # In preview environment, this fake atlas_id won't match anything
            from routes.auth import _resolve_imported_user
            
            # This should return False since our fake atlas_id won't match Atlas records
            real_email = f"testreal_{timestamp}@example.com"
            resolve_result = _resolve_imported_user(real_email)
            
            # Expected: False (no match in Atlas for our fake ID)
            assert resolve_result is False, f"Expected False for test scenario, got {resolve_result}"
            print("✓ _resolve_imported_user correctly handles non-matching Atlas lookup")
            
        finally:
            # Cleanup test imported user
            cleanup_script = f"""
            use('test_database');
            db.users.deleteOne({{ user_id: '{test_imported_user_id}' }});
            print('CLEANED_IMPORTED');
            """
            subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True, text=True)


class TestMigrationScriptDryRun:
    """Test that the migration script runs without errors in dry-run mode."""
    
    def test_migration_script_dry_run_executes(self):
        """Migration script at fix_imported_local_emails.py runs in dry-run mode without errors."""
        import subprocess
        
        # Run the migration script in dry-run mode
        result = subprocess.run(
            ["python", "-m", "one_time_migrations.fix_imported_local_emails"],
            capture_output=True,
            text=True,
            cwd="/app/backend",
            timeout=60
        )
        
        # Should not raise an error (exit code 0 or script completes)
        # In preview environment, it will find 0 @imported.local records, which is expected
        combined_output = result.stdout + result.stderr
        print(f"Migration script output:\n{combined_output}")
        
        # Check for success indicators (logging output goes to stderr)
        assert "DRY RUN" in combined_output or "Migration" in combined_output, \
            f"Migration script should indicate dry run mode. Output: {combined_output}"
        
        # Should not have critical Python errors (Traceback exceptions)
        assert "Traceback (most recent call last)" not in result.stderr, \
            f"Migration script raised exception: {result.stderr}"
        assert result.returncode == 0, f"Migration script exited with code {result.returncode}"
        
        print("✓ Migration script runs in dry-run mode without errors")
    
    def test_migration_script_finds_no_records_in_preview(self):
        """In preview environment, migration finds 0 @imported.local records (expected)."""
        import subprocess
        
        result = subprocess.run(
            ["python", "-m", "one_time_migrations.fix_imported_local_emails"],
            capture_output=True,
            text=True,
            cwd="/app/backend",
            timeout=60
        )
        
        # In preview, there are no @imported.local records
        # The script should report 0 records found (logging goes to stderr)
        combined_output = result.stdout + result.stderr
        
        # Either "Found 0 @imported.local users" or "nothing to do"
        has_zero_indicator = (
            "Found 0" in combined_output or
            "Imported records found: 0" in combined_output or
            "nothing to do" in combined_output.lower() or
            "No @imported.local" in combined_output
        )
        
        assert has_zero_indicator, f"Expected 0 @imported.local records in preview. Output: {combined_output}"
        print("✓ Migration correctly finds 0 @imported.local records in preview environment")


class TestAuthFlowIntegration:
    """Integration tests for auth flow _resolve_imported_user being called."""
    
    def test_auth_session_endpoint_accessible(self, api_session):
        """Verify /api/auth/session endpoint exists (integration check)."""
        # We can't fully test OAuth flow, but we can verify endpoint exists
        # Sending empty/invalid session_id should get 401, not 404
        response = api_session.post(
            f"{BASE_URL}/api/auth/session",
            json={"session_id": "invalid_test_session"}
        )
        
        # 401 = endpoint exists and rejected invalid session
        # 422 = validation error (endpoint exists)
        # 404 = endpoint doesn't exist (bad)
        assert response.status_code != 404, f"Auth session endpoint should exist. Got: {response.status_code}"
        print(f"✓ /api/auth/session endpoint exists (returned {response.status_code} for invalid session)")
    
    def test_resolve_imported_user_called_before_upsert(self):
        """Verify that _resolve_imported_user is called before upsert in auth flow."""
        # This is a code review/structure test
        import inspect
        from routes.auth import create_session, _resolve_imported_user
        
        # Get the source code of create_session
        source = inspect.getsource(create_session)
        
        # Verify _resolve_imported_user is called in the function
        assert "_resolve_imported_user" in source, "create_session should call _resolve_imported_user"
        
        # Verify it's called BEFORE the upsert (check code structure)
        resolve_index = source.find("_resolve_imported_user")
        upsert_index = source.find("update_one")
        
        # The resolve call should come before the main update_one (upsert)
        assert resolve_index < upsert_index, "_resolve_imported_user should be called before upsert"
        
        print("✓ Code structure verified: _resolve_imported_user is called before upsert in create_session")


# Run specific tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
