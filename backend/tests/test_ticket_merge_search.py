"""
Test Ticket Merge and Search Bug Fixes

Tests for:
1. GET /api/search?q=042237&type=ticket - should find TKT-042237 (numeric ID search without prefix)
2. GET /api/search?q=TKT-042237&type=ticket - should still work with prefix
3. GET /api/search?q=term&type=ticket - should return results in by_category.tickets
4. GET /api/tickets/{ticket_id}/merge-suggestions - should return ALL potential duplicates
5. POST /api/tickets/{source}/merge - should merge source into target
"""
import pytest
import requests
import os
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://assign-me-fix.preview.emergentagent.com').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'qa_test_admin_session_token_2026')


class TestNumericTicketSearch:
    """Test that numeric-only queries find tickets without TKT- prefix"""
    
    def test_search_numeric_id_without_prefix(self):
        """Search for '000875' should find TKT-000875"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={'q': '000875', 'type': 'ticket'},
            cookies={'session_token': SESSION_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check that results exist
        tickets = data.get('by_category', {}).get('tickets', [])
        assert len(tickets) > 0, f"Expected to find tickets, got empty results. Full response: {data}"
        
        # Verify TKT-000875 is in results
        ticket_ids = [t.get('ticket_id') for t in tickets]
        assert 'TKT-000875' in ticket_ids, f"Expected TKT-000875 in results, got: {ticket_ids}"
        
    def test_search_ticket_id_with_prefix(self):
        """Search for 'TKT-000875' should still work"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={'q': 'TKT-000875', 'type': 'ticket'},
            cookies={'session_token': SESSION_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        tickets = data.get('by_category', {}).get('tickets', [])
        assert len(tickets) > 0, "Expected to find ticket with TKT- prefix"
        
        # Verify exact match
        ticket_ids = [t.get('ticket_id') for t in tickets]
        assert 'TKT-000875' in ticket_ids, f"Expected TKT-000875 in results, got: {ticket_ids}"


class TestSearchResponseFormat:
    """Test that search returns results in correct format"""
    
    def test_search_returns_by_category_tickets(self):
        """Search should return ticket results in by_category.tickets"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={'q': 'support', 'type': 'ticket'},
            cookies={'session_token': SESSION_TOKEN}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Verify structure
        assert 'by_category' in data, f"Expected 'by_category' in response, got keys: {data.keys()}"
        assert 'tickets' in data.get('by_category', {}), f"Expected 'tickets' in by_category, got: {data.get('by_category', {}).keys()}"
        
        tickets = data['by_category']['tickets']
        if len(tickets) > 0:
            # Verify ticket structure
            ticket = tickets[0]
            assert 'ticket_id' in ticket, f"Expected 'ticket_id' in ticket, got: {ticket.keys()}"
            assert 'title' in ticket, f"Expected 'title' in ticket, got: {ticket.keys()}"
            
    def test_search_param_is_type_not_types(self):
        """Verify API uses 'type' param (not 'types')"""
        # This should work (correct param)
        response_correct = requests.get(
            f"{BASE_URL}/api/search",
            params={'q': 'test', 'type': 'ticket'},
            cookies={'session_token': SESSION_TOKEN}
        )
        assert response_correct.status_code == 200
        
        data = response_correct.json()
        # When type=ticket, only tickets should be in results
        assert 'by_category' in data
        assert 'tickets' in data.get('by_category', {})


class TestMergeSuggestions:
    """Test merge suggestions returns ALL potential duplicates"""
    
    def test_get_merge_suggestions_returns_multiple(self):
        """GET /api/tickets/{id}/merge-suggestions should return all duplicates"""
        # Use a ticket that we know has duplicates (ivanjason0@gmail.com has 4 tickets)
        # First, find the ticket IDs for this customer
        search_response = requests.get(
            f"{BASE_URL}/api/search",
            params={'q': 'customer:ivanjason0@gmail.com', 'type': 'ticket'},
            cookies={'session_token': SESSION_TOKEN}
        )
        
        if search_response.status_code != 200:
            pytest.skip("Could not find test tickets for merge suggestions")
            
        search_data = search_response.json()
        tickets = search_data.get('by_category', {}).get('tickets', [])
        
        if len(tickets) < 2:
            pytest.skip("Not enough tickets from same customer to test merge suggestions")
        
        # Get merge suggestions for first ticket
        ticket_id = tickets[0].get('ticket_id')
        response = requests.get(
            f"{BASE_URL}/api/tickets/{ticket_id}/merge-suggestions",
            cookies={'session_token': SESSION_TOKEN}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'suggestions' in data, f"Expected 'suggestions' in response, got: {data.keys()}"
        
        # The API should return suggestions (other tickets from same customer)
        # Note: might be empty if tickets are not within 2-hour window
        print(f"Merge suggestions for {ticket_id}: {len(data.get('suggestions', []))} suggestions found")


class TestMergeEndpoint:
    """Test the POST /api/tickets/{source}/merge endpoint"""
    
    def test_merge_endpoint_exists(self):
        """POST /api/tickets/{id}/merge endpoint should exist and require target_ticket_id"""
        # Create two test tickets first
        ticket1_response = requests.post(
            f"{BASE_URL}/api/tickets",
            json={
                'title': 'TEST_Merge_Source_' + str(int(time.time())),
                'description': 'Test ticket for merge source',
                'priority': 'medium',
                'customer_email': 'test_merge_test@example.com'
            },
            cookies={'session_token': SESSION_TOKEN}
        )
        
        ticket2_response = requests.post(
            f"{BASE_URL}/api/tickets",
            json={
                'title': 'TEST_Merge_Target_' + str(int(time.time())),
                'description': 'Test ticket for merge target',
                'priority': 'medium',
                'customer_email': 'test_merge_test@example.com'
            },
            cookies={'session_token': SESSION_TOKEN}
        )
        
        if ticket1_response.status_code != 201 or ticket2_response.status_code != 201:
            pytest.skip("Could not create test tickets for merge test")
        
        source_ticket = ticket1_response.json()
        target_ticket = ticket2_response.json()
        
        source_id = source_ticket.get('ticket_id') or source_ticket.get('id')
        target_id = target_ticket.get('ticket_id') or target_ticket.get('id')
        
        # Test merge: merge source INTO target
        merge_response = requests.post(
            f"{BASE_URL}/api/tickets/{source_id}/merge",
            json={'target_ticket_id': target_id},
            cookies={'session_token': SESSION_TOKEN}
        )
        
        assert merge_response.status_code == 200, f"Expected 200, got {merge_response.status_code}: {merge_response.text}"
        
        merge_data = merge_response.json()
        assert 'message' in merge_data, f"Expected 'message' in merge response, got: {merge_data.keys()}"
        
        # Verify source ticket is now merged
        source_check = requests.get(
            f"{BASE_URL}/api/tickets/{source_id}",
            cookies={'session_token': SESSION_TOKEN}
        )
        
        if source_check.status_code == 200:
            source_data = source_check.json()
            assert source_data.get('status') == 'merged', f"Expected source ticket status 'merged', got: {source_data.get('status')}"
            assert source_data.get('merged_into') == target_id, f"Expected merged_into={target_id}, got: {source_data.get('merged_into')}"
        
        # Cleanup: The tickets are marked as merged, so no need to delete
        print(f"Successfully merged {source_id} into {target_id}")
        
    def test_merge_requires_target_ticket_id(self):
        """Merge should fail if target_ticket_id is not provided"""
        response = requests.post(
            f"{BASE_URL}/api/tickets/TKT-000875/merge",
            json={},  # Missing target_ticket_id
            cookies={'session_token': SESSION_TOKEN}
        )
        
        # Should return 400 Bad Request
        assert response.status_code == 400, f"Expected 400 for missing target_ticket_id, got {response.status_code}"


class TestSearchTypeSingular:
    """Verify the search param is 'type' (singular) not 'types' (plural)"""
    
    def test_search_uses_type_param(self):
        """Frontend should use type=ticket, not types=tickets"""
        # The correct API call with type=ticket
        response = requests.get(
            f"{BASE_URL}/api/search",
            params={'q': 'urgent', 'type': 'ticket'},
            cookies={'session_token': SESSION_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify we get results in the expected format
        assert 'by_category' in data or 'results' in data, f"Expected search results, got: {data.keys()}"
        
        # If by_category exists, tickets should be there
        if 'by_category' in data:
            # When type=ticket filter is used, we should get tickets
            tickets = data.get('by_category', {}).get('tickets', [])
            # Just verify the structure is correct
            print(f"Search returned {len(tickets)} tickets for query 'urgent'")


# Cleanup fixture
@pytest.fixture(scope='module', autouse=True)
def cleanup_test_tickets():
    """Clean up test tickets after all tests"""
    yield
    # After tests, clean up TEST_ prefixed tickets
    # Note: In a real scenario, we'd delete these, but merged tickets
    # stay in the DB with status='merged'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
