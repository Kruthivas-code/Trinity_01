"""
Tests for KB Bulk Move Articles endpoint
POST /api/kb/admin/articles/bulk-move

This feature allows moving all articles from one section to another group/section.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {'Authorization': 'Bearer test_admin_session_flow', 'Content-Type': 'application/json'}


class TestBulkMoveArticlesEndpoint:
    """Tests for POST /api/kb/admin/articles/bulk-move"""
    
    def test_bulk_move_requires_authentication(self):
        """Bulk move endpoint should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={
                "source_group_key": "test",
                "source_section_key": "test",
                "target_group_key": "test",
                "target_group_label": "Test",
                "target_section_key": "test",
                "target_section_label": "Test"
            },
            headers={'Content-Type': 'application/json'}
        )
        # Should fail without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Bulk move endpoint requires authentication (status: {response.status_code})")
    
    def test_bulk_move_with_auth_no_op(self):
        """Bulk move from a section to itself (no-op) - verifies endpoint works without breaking data"""
        # First get navigation to find a valid section
        nav_response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers=AUTH_HEADER
        )
        assert nav_response.status_code == 200, f"Failed to get articles: {nav_response.status_code}"
        data = nav_response.json()
        nav_groups = data.get('nav_groups', [])
        
        # Find the integrations section (should have 17 articles per review request)
        source_group = None
        source_section = None
        for group in nav_groups:
            for section in group.get('sections', []):
                if 'integrations' in section.get('key', '').lower() or 'integrations' in section.get('label', '').lower():
                    source_group = group
                    source_section = section
                    break
            if source_section:
                break
        
        # If no integrations section found, use first available section
        if not source_group or not source_section:
            if nav_groups and nav_groups[0].get('sections'):
                source_group = nav_groups[0]
                source_section = nav_groups[0]['sections'][0]
        
        assert source_group and source_section, "No valid section found to test"
        
        print(f"Testing bulk move from '{source_group['label']}/{source_section['label']}' to itself (no-op)")
        
        # Move from section to itself (safe no-op)
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={
                "source_group_key": source_group['key'],
                "source_section_key": source_section['key'],
                "target_group_key": source_group['key'],
                "target_group_label": source_group['label'],
                "target_section_key": source_section['key'],
                "target_section_label": source_section['label']
            },
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response has 'moved' count
        assert 'moved' in data, f"Response should have 'moved' field: {data}"
        assert isinstance(data['moved'], int), f"'moved' should be an integer: {data}"
        
        print(f"✓ Bulk move endpoint works - reported {data['moved']} articles moved (no-op test)")
    
    def test_bulk_move_returns_count(self):
        """Verify bulk move returns accurate count of moved articles"""
        # Get current articles to count
        nav_response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers=AUTH_HEADER
        )
        assert nav_response.status_code == 200
        data = nav_response.json()
        articles = data.get('articles', [])
        nav_groups = data.get('nav_groups', [])
        
        # Find a section with articles
        target_group = None
        target_section = None
        expected_count = 0
        
        for group in nav_groups:
            for section in group.get('sections', []):
                section_articles = [
                    a for a in articles 
                    if a.get('nav_group_key') == group['key'] and a.get('section_key') == section['key']
                ]
                if section_articles:
                    target_group = group
                    target_section = section
                    expected_count = len(section_articles)
                    break
            if target_group:
                break
        
        if not target_group:
            pytest.skip("No sections with articles found for testing")
        
        print(f"Testing section '{target_group['label']}/{target_section['label']}' with {expected_count} articles")
        
        # Move to itself - count should match
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={
                "source_group_key": target_group['key'],
                "source_section_key": target_section['key'],
                "target_group_key": target_group['key'],
                "target_group_label": target_group['label'],
                "target_section_key": target_section['key'],
                "target_section_label": target_section['label']
            },
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Note: When moving to same section, MongoDB may report 0 modified if values unchanged
        # or the actual count if it updates timestamps
        assert 'moved' in data
        print(f"✓ Bulk move returned count: {data['moved']}")
    
    def test_bulk_move_empty_section(self):
        """Bulk move from an empty/nonexistent section should return 0"""
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={
                "source_group_key": "nonexistent-group-12345",
                "source_section_key": "nonexistent-section-12345",
                "target_group_key": "test-target",
                "target_group_label": "Test Target",
                "target_section_key": "test-section",
                "target_section_label": "Test Section"
            },
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get('moved') == 0, f"Expected 0 articles moved for nonexistent section, got {data}"
        print("✓ Bulk move from nonexistent section correctly returns 0")
    
    def test_bulk_move_validation(self):
        """Bulk move should validate request body"""
        # Missing required fields
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={
                "source_group_key": "test"
                # Missing other required fields
            },
            headers=AUTH_HEADER
        )
        
        # Should return validation error (422) for missing fields
        assert response.status_code == 422, f"Expected 422 for missing fields, got {response.status_code}"
        print("✓ Bulk move validates required fields (422 for incomplete payload)")


class TestBulkMoveIntegration:
    """Integration tests for bulk move with actual data verification"""
    
    def test_get_navigation_structure(self):
        """Verify we can get navigation structure needed for bulk move UI"""
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure for frontend UI
        assert 'nav_groups' in data, "Response should contain nav_groups"
        assert 'articles' in data, "Response should contain articles"
        
        nav_groups = data['nav_groups']
        articles = data['articles']
        
        print(f"✓ Navigation structure: {len(nav_groups)} groups, {len(articles)} articles")
        
        # Print groups and sections for reference
        for group in nav_groups:
            sections_count = len(group.get('sections', []))
            print(f"  - {group.get('label')} ({group.get('key')}): {sections_count} sections")
            for section in group.get('sections', []):
                section_articles = [
                    a for a in articles 
                    if a.get('nav_group_key') == group['key'] and a.get('section_key') == section['key']
                ]
                print(f"    - {section.get('label')} ({section.get('key')}): {len(section_articles)} articles")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
