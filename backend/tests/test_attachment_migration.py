"""
Attachment Migration Tests
=========================
Tests for the Atlas CDN to Emergent Object Storage migration feature.
- File proxy endpoint (/api/files/{path})
- Migration API endpoints (auth-gated)
- MongoDB migration state
- Migrated attachment structure
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API_KEY = "tk_live_C47oqvueOkUiCEBs-8EBNkJmu3-VyYdSfOB8RgeFZXI"


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """Health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("PASS: Health check returns healthy")


class TestFileProxyEndpoint:
    """Tests for the public file proxy endpoint /api/files/{path}"""
    
    def test_file_proxy_returns_200_for_test_file(self):
        """File proxy returns 200 for test file (no auth required)"""
        response = requests.get(
            f"{BASE_URL}/api/files/trinity/attachments/test/sample_screenshot.png",
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        # Check content length > 0
        assert len(response.content) > 0, "File content should not be empty"
        print(f"PASS: File proxy returned {len(response.content)} bytes")
    
    def test_file_proxy_returns_image_content_type(self):
        """File proxy returns correct content type for PNG"""
        response = requests.get(
            f"{BASE_URL}/api/files/trinity/attachments/test/sample_screenshot.png",
            timeout=30
        )
        assert response.status_code == 200
        content_type = response.headers.get("Content-Type", "")
        assert "image" in content_type or "png" in content_type.lower(), \
            f"Expected image content type, got {content_type}"
        print(f"PASS: Content-Type is {content_type}")
    
    def test_file_proxy_returns_404_for_nonexistent(self):
        """File proxy returns 404 for non-existent file"""
        response = requests.get(
            f"{BASE_URL}/api/files/trinity/attachments/nonexistent_file_12345.xyz",
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: 404 returned for non-existent file")
    
    def test_file_proxy_serves_migrated_attachment(self):
        """File proxy can serve a real migrated attachment"""
        # First, get a migrated attachment path from MongoDB
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        
        migrated = db.messages.find_one(
            {"attachments.storage_path": {"$exists": True}},
            {"attachments": 1, "_id": 0}
        )
        
        if not migrated or not migrated.get("attachments"):
            pytest.skip("No migrated attachments found in database")
        
        # Get the storage path from the first attachment
        att = migrated["attachments"][0]
        storage_path = att.get("storage_path")
        assert storage_path, "Attachment should have storage_path"
        
        # Fetch from file proxy
        response = requests.get(f"{BASE_URL}/api/files/{storage_path}", timeout=30)
        assert response.status_code == 200, f"Failed to fetch migrated file: {response.status_code}"
        assert len(response.content) > 0, "File content should not be empty"
        print(f"PASS: Migrated file served successfully ({len(response.content)} bytes)")
        
        client.close()


class TestMigrationAPIEndpoints:
    """Tests for migration API endpoints (require authentication)"""
    
    def test_status_endpoint_returns_401_without_auth(self):
        """GET /api/admin/atlas/attachments/status returns 401 (not 404)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/attachments/status",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Status endpoint exists (returns 401 without auth)")
    
    def test_start_endpoint_returns_401_without_auth(self):
        """POST /api/admin/atlas/attachments/start returns 401 (not 404)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/attachments/start",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Start endpoint exists (returns 401 without auth)")
    
    def test_stop_endpoint_returns_401_without_auth(self):
        """POST /api/admin/atlas/attachments/stop returns 401 (not 404)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/atlas/attachments/stop",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Stop endpoint exists (returns 401 without auth)")
    
    def test_status_endpoint_with_api_key(self):
        """GET /api/admin/atlas/attachments/status returns 200 with API key"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/attachments/status",
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Check required fields
        assert "status" in data, "Response should have 'status' field"
        assert "migrated" in data, "Response should have 'migrated' field"
        assert "is_running" in data, "Response should have 'is_running' field"
        print(f"PASS: Status endpoint returns data (migrated: {data.get('migrated')}, status: {data.get('status')})")


class TestMongoDBMigrationState:
    """Tests for MongoDB atlas_backfill_state attachment_migration document"""
    
    @pytest.fixture(scope="class")
    def mongo_client(self):
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        yield client
        client.close()
    
    def test_attachment_migration_document_exists(self, mongo_client):
        """MongoDB has attachment_migration state document"""
        db = mongo_client["test_database"]
        state = db.atlas_backfill_state.find_one(
            {"_type": "attachment_migration"},
            {"_id": 0}
        )
        assert state is not None, "attachment_migration document should exist"
        print(f"PASS: attachment_migration document exists with status={state.get('status')}")
    
    def test_migration_has_migrated_count(self, mongo_client):
        """Migration state shows migrated > 0"""
        db = mongo_client["test_database"]
        state = db.atlas_backfill_state.find_one(
            {"_type": "attachment_migration"},
            {"_id": 0}
        )
        assert state is not None
        migrated = state.get("migrated", 0)
        assert migrated > 0, f"Expected migrated > 0, got {migrated}"
        print(f"PASS: Migrated count = {migrated}")
    
    def test_migration_has_required_fields(self, mongo_client):
        """Migration state has all required fields"""
        db = mongo_client["test_database"]
        state = db.atlas_backfill_state.find_one(
            {"_type": "attachment_migration"},
            {"_id": 0}
        )
        assert state is not None
        
        required_fields = ["status", "migrated", "failed", "skipped", "total_attachments", "bytes_transferred"]
        for field in required_fields:
            assert field in state, f"Missing required field: {field}"
        
        print(f"PASS: All required fields present: {required_fields}")


class TestMigratedAttachmentStructure:
    """Tests for migrated message attachment structure"""
    
    @pytest.fixture(scope="class")
    def mongo_client(self):
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        yield client
        client.close()
    
    def test_migrated_messages_exist(self, mongo_client):
        """Messages with migrated attachments exist"""
        db = mongo_client["test_database"]
        count = db.messages.count_documents({"attachments.storage_path": {"$exists": True}})
        assert count > 0, "No migrated messages found"
        print(f"PASS: Found {count} messages with migrated attachments")
    
    def test_attachments_have_storage_path(self, mongo_client):
        """Migrated attachments have storage_path field"""
        db = mongo_client["test_database"]
        migrated = db.messages.find_one(
            {"attachments.storage_path": {"$exists": True}},
            {"attachments": 1, "_id": 0}
        )
        assert migrated is not None
        att = migrated["attachments"][0]
        assert "storage_path" in att, "Attachment should have storage_path"
        assert att["storage_path"].startswith("trinity/attachments/"), \
            f"storage_path should start with 'trinity/attachments/', got {att['storage_path']}"
        print(f"PASS: storage_path = {att['storage_path']}")
    
    def test_attachments_have_original_url(self, mongo_client):
        """Migrated attachments have original_url field"""
        db = mongo_client["test_database"]
        migrated = db.messages.find_one(
            {"attachments.storage_path": {"$exists": True}},
            {"attachments": 1, "_id": 0}
        )
        assert migrated is not None
        att = migrated["attachments"][0]
        assert "original_url" in att, "Attachment should have original_url"
        # Original URL should be from Atlas CDN or Discord
        original = att["original_url"]
        assert "files.atlas.so" in original or "discord" in original, \
            f"original_url should be from Atlas/Discord CDN, got {original[:50]}..."
        print(f"PASS: original_url preserved")
    
    def test_attachments_url_points_to_api_files(self, mongo_client):
        """Migrated attachments have url pointing to /api/files/*"""
        db = mongo_client["test_database"]
        migrated = db.messages.find_one(
            {"attachments.storage_path": {"$exists": True}},
            {"attachments": 1, "_id": 0}
        )
        assert migrated is not None
        att = migrated["attachments"][0]
        assert "url" in att, "Attachment should have url"
        assert att["url"].startswith("/api/files/"), \
            f"url should start with '/api/files/', got {att['url']}"
        print(f"PASS: url = {att['url']}")
    
    def test_all_migrated_attachments_have_required_fields(self, mongo_client):
        """Verify 5 random migrated attachments have all required fields"""
        db = mongo_client["test_database"]
        messages = list(db.messages.find(
            {"attachments.storage_path": {"$exists": True}},
            {"message_id": 1, "attachments": 1, "_id": 0}
        ).limit(5))
        
        assert len(messages) > 0, "No migrated messages to check"
        
        all_valid = True
        for msg in messages:
            for att in msg.get("attachments", []):
                if att.get("storage_path"):  # Only check migrated attachments
                    has_storage = "storage_path" in att
                    has_original = "original_url" in att
                    has_proxy_url = att.get("url", "").startswith("/api/files/")
                    
                    if not (has_storage and has_original and has_proxy_url):
                        all_valid = False
                        print(f"FAIL: Message {msg['message_id']} attachment missing fields")
        
        assert all_valid, "Some attachments missing required fields"
        print(f"PASS: All {len(messages)} sampled messages have proper attachment structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
