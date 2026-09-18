"""
Tests for KB Bulk Move Articles endpoint
POST /api/kb/admin/articles/bulk-move

This feature moves every page filed directly under one nav-tree group over
to another group (by key — the tree already carries labels/nesting).
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {'Authorization': 'Bearer test_admin_session_flow', 'Content-Type': 'application/json'}


def _find_group_with_pages(nodes):
    """Depth-first search for a group node that has at least one direct page
    child, returning (group_node, direct_page_count)."""
    for node in nodes:
        if node.get('type') != 'group':
            continue
        direct_pages = [c for c in node.get('children', []) if c.get('type') == 'page']
        if direct_pages:
            return node, len(direct_pages)
        found = _find_group_with_pages(node.get('children', []))
        if found:
            return found
    return None


class TestBulkMoveArticlesEndpoint:
    """Tests for POST /api/kb/admin/articles/bulk-move"""

    def test_bulk_move_requires_authentication(self):
        """Bulk move endpoint should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={"source_key": "test", "target_key": "test"},
            headers={'Content-Type': 'application/json'}
        )
        # Should fail without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Bulk move endpoint requires authentication (status: {response.status_code})")

    def test_bulk_move_with_auth_no_op(self):
        """Bulk move from a group to itself (no-op) - verifies endpoint works without breaking data"""
        # First get navigation to find a valid group with pages
        nav_response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers=AUTH_HEADER
        )
        assert nav_response.status_code == 200, f"Failed to get articles: {nav_response.status_code}"
        data = nav_response.json()
        nav_groups = data.get('groups', [])

        found = _find_group_with_pages(nav_groups)
        assert found, "No valid group with pages found to test"
        source_group, page_count = found

        print(f"Testing bulk move from '{source_group['label']}' ({page_count} pages) to itself (no-op)")

        # Move from group to itself (safe no-op)
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={"source_key": source_group['key'], "target_key": source_group['key']},
            headers=AUTH_HEADER
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify response has 'moved' count
        assert 'moved' in data, f"Response should have 'moved' field: {data}"
        assert isinstance(data['moved'], int), f"'moved' should be an integer: {data}"
        assert data['moved'] == page_count, f"Expected {page_count} pages reported moved, got {data['moved']}"

        print(f"✓ Bulk move endpoint works - reported {data['moved']} articles moved (no-op test)")

    def test_bulk_move_returns_count(self):
        """Verify bulk move returns accurate count of moved articles"""
        nav_response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers=AUTH_HEADER
        )
        assert nav_response.status_code == 200
        data = nav_response.json()
        nav_groups = data.get('groups', [])

        found = _find_group_with_pages(nav_groups)
        if not found:
            pytest.skip("No groups with articles found for testing")
        target_group, expected_count = found

        print(f"Testing group '{target_group['label']}' with {expected_count} direct pages")

        # Move to itself - count should match the group's direct page count
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={"source_key": target_group['key'], "target_key": target_group['key']},
            headers=AUTH_HEADER
        )

        assert response.status_code == 200
        data = response.json()

        assert 'moved' in data
        assert data['moved'] == expected_count, f"Expected {expected_count}, got {data['moved']}"
        print(f"✓ Bulk move returned count: {data['moved']}")

    def test_bulk_move_nonexistent_group_404s(self):
        """Bulk move referencing an unknown group key should 404, not silently no-op"""
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={"source_key": "nonexistent-group-12345", "target_key": "also-nonexistent-98765"},
            headers=AUTH_HEADER
        )

        assert response.status_code == 404, f"Expected 404 for unknown group keys, got {response.status_code}"
        print("✓ Bulk move with nonexistent group keys correctly returns 404")

    def test_bulk_move_validation(self):
        """Bulk move should validate request body"""
        # Missing required field (target_key)
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/articles/bulk-move",
            json={"source_key": "test"},
            headers=AUTH_HEADER
        )

        # Should return validation error (422) for missing fields
        assert response.status_code == 422, f"Expected 422 for missing fields, got {response.status_code}"
        print("✓ Bulk move validates required fields (422 for incomplete payload)")


class TestBulkMoveIntegration:
    """Integration tests for bulk move with actual data verification"""

    def test_get_navigation_structure(self):
        """Verify we can get the nav tree structure needed for the bulk-move UI"""
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/articles",
            headers=AUTH_HEADER
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure for frontend UI
        assert 'groups' in data, "Response should contain the nav tree under 'groups'"
        assert 'articles' in data, "Response should contain articles"

        nav_groups = data['groups']
        articles = data['articles']

        print(f"✓ Navigation structure: {len(nav_groups)} top-level groups, {len(articles)} articles")

        # Print the tree (recursively) with each group's direct article counts,
        # cross-checked against the articles' own nav_group_key/section_key.
        def describe(nodes, depth=0):
            for node in nodes:
                if node.get('type') != 'group':
                    continue
                direct_articles = [
                    a for a in articles
                    if a.get('section_key') == node['key']
                ]
                print(f"  {'  ' * depth}- {node.get('label')} ({node.get('key')}): {len(direct_articles)} direct articles")
                describe(node.get('children', []), depth + 1)

        describe(nav_groups)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
