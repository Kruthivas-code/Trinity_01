"""
Test suite for conversation thread fixes:
- No duplicate messages in conversation thread
- Notes API returns 'original' type messages
- Tags display without # prefix
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = 'playwright_test_session'

# Test tickets with known conversation structure
TEST_TICKET_1 = 'TKT-024453'  # Has original + customer_reply (2 messages)
TEST_TICKET_2 = 'TKT-023869'  # Has reply + original + multiple customer_replies (6 messages)


@pytest.fixture
def auth_session():
    """Create authenticated session with session cookie"""
    session = requests.Session()
    session.cookies.set('session_token', SESSION_TOKEN)
    session.headers.update({'Content-Type': 'application/json'})
    return session


class TestNotesAPI:
    """Test Notes API returns 'original' type messages"""
    
    def test_notes_api_returns_original_type_ticket1(self, auth_session):
        """Verify TKT-024453 notes include 'original' type message"""
        response = auth_session.get(f'{BASE_URL}/api/tickets/{TEST_TICKET_1}/notes')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'messages' in data, "Response should contain 'messages' field"
        
        messages = data['messages']
        assert len(messages) > 0, "Should have at least one message"
        
        # Check for 'original' type message
        message_types = [m.get('type') for m in messages]
        assert 'original' in message_types, f"Should include 'original' type message, got types: {message_types}"
        
        # Verify original message content matches ticket description
        original_msg = next((m for m in messages if m.get('type') == 'original'), None)
        assert original_msg is not None, "Should have an original message"
        assert 'content' in original_msg, "Original message should have content"
        assert len(original_msg['content']) > 0, "Original message content should not be empty"
    
    def test_notes_api_returns_original_type_ticket2(self, auth_session):
        """Verify TKT-023869 notes include 'original' type message"""
        response = auth_session.get(f'{BASE_URL}/api/tickets/{TEST_TICKET_2}/notes')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        messages = data['messages']
        
        # Check for 'original' type message
        message_types = [m.get('type') for m in messages]
        assert 'original' in message_types, f"Should include 'original' type message, got types: {message_types}"
        
        # Should also have customer_reply messages
        assert 'customer_reply' in message_types, "Should include 'customer_reply' messages"
    
    def test_no_duplicate_messages_ticket1(self, auth_session):
        """Verify TKT-024453 has exactly 2 messages (no duplicates)"""
        response = auth_session.get(f'{BASE_URL}/api/tickets/{TEST_TICKET_1}/notes')
        assert response.status_code == 200
        
        data = response.json()
        messages = data['messages']
        
        # TKT-024453 should have exactly 2 messages: original + customer_reply
        assert len(messages) == 2, f"Expected exactly 2 messages, got {len(messages)}"
        
        message_types = sorted([m.get('type') for m in messages])
        expected_types = sorted(['original', 'customer_reply'])
        assert message_types == expected_types, f"Expected {expected_types}, got {message_types}"
    
    def test_no_duplicate_messages_ticket2(self, auth_session):
        """Verify TKT-023869 has expected message count (no duplicates)"""
        response = auth_session.get(f'{BASE_URL}/api/tickets/{TEST_TICKET_2}/notes')
        assert response.status_code == 200
        
        data = response.json()
        messages = data['messages']
        
        # TKT-023869 should have 6 messages: 1 reply + 1 original + 4 customer_replies
        assert len(messages) == 6, f"Expected exactly 6 messages, got {len(messages)}"
        
        # Count message types
        type_counts = {}
        for m in messages:
            msg_type = m.get('type')
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
        
        assert type_counts.get('original') == 1, "Should have exactly 1 original message"
        assert type_counts.get('reply') == 1, "Should have exactly 1 reply"
        assert type_counts.get('customer_reply') == 4, f"Should have 4 customer_replies, got {type_counts.get('customer_reply')}"
    
    def test_original_message_matches_ticket_description(self, auth_session):
        """Verify original message content matches ticket description"""
        # Get ticket details
        ticket_response = auth_session.get(f'{BASE_URL}/api/tickets/{TEST_TICKET_1}')
        assert ticket_response.status_code == 200
        ticket = ticket_response.json()
        
        # Get notes
        notes_response = auth_session.get(f'{BASE_URL}/api/tickets/{TEST_TICKET_1}/notes')
        assert notes_response.status_code == 200
        messages = notes_response.json()['messages']
        
        # Find original message
        original_msg = next((m for m in messages if m.get('type') == 'original'), None)
        assert original_msg is not None, "Should have original message"
        
        # Content should match (or be similar - handle potential whitespace differences)
        ticket_desc = ticket.get('description', '').strip()
        msg_content = original_msg.get('content', '').strip()
        
        # They should match or at least start the same
        assert msg_content[:100] == ticket_desc[:100], \
            f"Original message content should match ticket description. Got:\n{msg_content[:100]}\nExpected:\n{ticket_desc[:100]}"


class TestTicketTags:
    """Test ticket tags functionality"""
    
    def test_ticket_has_tags(self, auth_session):
        """Verify test ticket has tags in expected format"""
        response = auth_session.get(f'{BASE_URL}/api/tickets/{TEST_TICKET_1}')
        assert response.status_code == 200
        
        ticket = response.json()
        assert 'tags' in ticket, "Ticket should have tags field"
        
        tags = ticket.get('tags', [])
        assert isinstance(tags, list), "Tags should be a list"
        
        # Verify tags don't have # prefix (stored in backend)
        for tag in tags:
            assert not tag.startswith('#'), f"Tag '{tag}' should not have # prefix"


class TestTicketSource:
    """Test ticket source field"""
    
    def test_ticket_has_source_field(self, auth_session):
        """Verify ticket has source field without redundant channel"""
        response = auth_session.get(f'{BASE_URL}/api/tickets/{TEST_TICKET_1}')
        assert response.status_code == 200
        
        ticket = response.json()
        assert 'source' in ticket, "Ticket should have source field"
        
        source = ticket.get('source')
        assert source in ['email', 'portal', 'atlas', 'manual', 'api'], \
            f"Source should be a valid value, got: {source}"
        
        # Verify no redundant 'channel' field
        assert 'channel' not in ticket or ticket.get('channel') == ticket.get('source'), \
            "Should not have separate channel field or it should match source"


class TestAuthenticatedUser:
    """Verify authentication is working"""
    
    def test_auth_me_returns_user(self, auth_session):
        """Verify /api/auth/me returns authenticated user"""
        response = auth_session.get(f'{BASE_URL}/api/auth/me')
        assert response.status_code == 200, f"Auth check failed: {response.status_code}"
        
        user = response.json()
        assert 'user_id' in user or 'id' in user, "User should have id"
        assert 'email' in user, "User should have email"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
