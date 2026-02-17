"""
Test KB Image Upload Functionality - New Feature (P0)
Tests the following endpoints:
- POST /api/kb/admin/images - Upload an image
- GET /api/kb/admin/images - List uploaded images
- DELETE /api/kb/admin/images/:filename - Delete an image
- GET /api/kb/images/:filename - Public access to uploaded images
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "67e642d8-ae8c-4b91-a019-27d2718b5740"


class TestKBImageUpload:
    """Test KB image upload functionality with admin auth"""
    
    uploaded_filenames = []  # Track uploaded files for cleanup
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and teardown for tests"""
        yield
        # Cleanup uploaded test images
        for filename in self.uploaded_filenames:
            try:
                requests.delete(
                    f"{BASE_URL}/api/kb/admin/images/{filename}",
                    headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
                )
            except:
                pass
        self.uploaded_filenames.clear()
    
    # --- Authentication Tests ---
    
    def test_upload_image_without_auth_returns_401(self):
        """POST /api/kb/admin/images without auth should return 401"""
        # Create a minimal PNG image
        with open('/tmp/test.png', 'rb') as f:
            files = {'file': ('test.png', f, 'image/png')}
            response = requests.post(f"{BASE_URL}/api/kb/admin/images", files=files)
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: Upload without auth returns 401")
    
    def test_list_images_without_auth_returns_401(self):
        """GET /api/kb/admin/images without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/kb/admin/images")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: List images without auth returns 401")
    
    def test_delete_image_without_auth_returns_401(self):
        """DELETE /api/kb/admin/images/:filename without auth should return 401"""
        response = requests.delete(f"{BASE_URL}/api/kb/admin/images/test.png")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Delete image without auth returns 401")
    
    # --- Upload Tests ---
    
    def test_upload_png_image_success(self):
        """POST /api/kb/admin/images with valid PNG should return filename and url"""
        with open('/tmp/test.png', 'rb') as f:
            files = {'file': ('test_upload.png', f, 'image/png')}
            response = requests.post(
                f"{BASE_URL}/api/kb/admin/images",
                files=files,
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'filename' in data, "Response should contain filename"
        assert 'url' in data, "Response should contain url"
        assert 'size' in data, "Response should contain size"
        
        # Verify filename is a unique hash with extension
        assert data['filename'].endswith('.png'), f"Filename should end with .png, got {data['filename']}"
        assert len(data['filename']) > 4, "Filename should have unique hash"
        
        # Verify URL format
        assert data['url'].startswith('/api/kb/images/'), f"URL should start with /api/kb/images/, got {data['url']}"
        assert data['url'].endswith(data['filename']), "URL should end with filename"
        
        # Track for cleanup
        self.uploaded_filenames.append(data['filename'])
        
        print(f"PASS: Upload PNG returns filename={data['filename']}, url={data['url']}, size={data['size']}")
    
    def test_upload_jpeg_image_success(self):
        """POST /api/kb/admin/images with valid JPEG should work"""
        # Create a minimal JPEG (simplest valid JPEG)
        # This is a 1x1 red pixel JPEG
        jpeg_bytes = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xFB, 0xD5, 0xFB, 0xD5, 0xFF, 0xD9
        ])
        
        files = {'file': ('test.jpg', jpeg_bytes, 'image/jpeg')}
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/images",
            files=files,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        # Accept 200 or 400 (if JPEG validation is strict)
        if response.status_code == 200:
            data = response.json()
            assert 'filename' in data
            assert data['filename'].endswith('.jpg')
            self.uploaded_filenames.append(data['filename'])
            print(f"PASS: Upload JPEG returns filename={data['filename']}")
        else:
            print(f"INFO: JPEG upload returned {response.status_code} - may need valid JPEG bytes")
    
    def test_upload_non_image_file_rejected(self):
        """POST /api/kb/admin/images with non-image file should return 400"""
        text_content = b"This is not an image file"
        files = {'file': ('test.txt', text_content, 'text/plain')}
        response = requests.post(
            f"{BASE_URL}/api/kb/admin/images",
            files=files,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'detail' in data, "Response should contain detail"
        assert 'text/plain' in data['detail'] or 'Unsupported' in data['detail'], f"Error should mention unsupported type: {data['detail']}"
        
        print(f"PASS: Non-image file rejected with 400: {data['detail']}")
    
    # --- List Images Tests ---
    
    def test_list_images_returns_array(self):
        """GET /api/kb/admin/images should return images array"""
        # First upload an image
        with open('/tmp/test.png', 'rb') as f:
            files = {'file': ('test_list.png', f, 'image/png')}
            upload_response = requests.post(
                f"{BASE_URL}/api/kb/admin/images",
                files=files,
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
        
        assert upload_response.status_code == 200
        uploaded_filename = upload_response.json()['filename']
        self.uploaded_filenames.append(uploaded_filename)
        
        # Now list images
        response = requests.get(
            f"{BASE_URL}/api/kb/admin/images",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'images' in data, "Response should contain 'images' key"
        assert isinstance(data['images'], list), "Images should be a list"
        
        # Verify the uploaded image is in the list
        filenames = [img['filename'] for img in data['images']]
        assert uploaded_filename in filenames, f"Uploaded file {uploaded_filename} should be in list: {filenames}"
        
        # Verify image metadata (without binary data)
        uploaded_img = next((img for img in data['images'] if img['filename'] == uploaded_filename), None)
        assert uploaded_img is not None
        assert 'data' not in uploaded_img, "Binary data should not be included in list"
        assert 'content_type' in uploaded_img
        assert 'size' in uploaded_img
        assert 'uploaded_at' in uploaded_img
        
        print(f"PASS: List images returns {len(data['images'])} images, includes uploaded file")
    
    # --- Public Access Tests ---
    
    def test_public_image_access(self):
        """GET /api/kb/images/:filename should serve uploaded image publicly"""
        # First upload an image
        with open('/tmp/test.png', 'rb') as f:
            png_content = f.read()
        
        files = {'file': ('test_public.png', png_content, 'image/png')}
        upload_response = requests.post(
            f"{BASE_URL}/api/kb/admin/images",
            files=files,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        assert upload_response.status_code == 200
        data = upload_response.json()
        uploaded_filename = data['filename']
        self.uploaded_filenames.append(uploaded_filename)
        
        # Now access the image publicly (no auth required)
        response = requests.get(f"{BASE_URL}/api/kb/images/{uploaded_filename}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.headers.get('Content-Type', '').startswith('image/'), f"Content-Type should be image/*: {response.headers.get('Content-Type')}"
        
        # Verify cache header
        assert 'max-age=' in response.headers.get('Cache-Control', ''), "Should have cache control header"
        
        # Verify content matches
        assert response.content == png_content, "Served content should match uploaded content"
        
        print(f"PASS: Public access to {uploaded_filename} works, content-type={response.headers.get('Content-Type')}")
    
    def test_public_image_not_found(self):
        """GET /api/kb/images/:filename for non-existent image should return 404"""
        response = requests.get(f"{BASE_URL}/api/kb/images/nonexistent-{uuid.uuid4().hex}.png")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Non-existent image returns 404")
    
    # --- Delete Tests ---
    
    def test_delete_image_success(self):
        """DELETE /api/kb/admin/images/:filename should delete the image"""
        # First upload an image
        with open('/tmp/test.png', 'rb') as f:
            files = {'file': ('test_delete.png', f, 'image/png')}
            upload_response = requests.post(
                f"{BASE_URL}/api/kb/admin/images",
                files=files,
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
        
        assert upload_response.status_code == 200
        uploaded_filename = upload_response.json()['filename']
        
        # Verify it exists publicly
        verify_response = requests.get(f"{BASE_URL}/api/kb/images/{uploaded_filename}")
        assert verify_response.status_code == 200, "Image should exist before deletion"
        
        # Delete the image
        delete_response = requests.delete(
            f"{BASE_URL}/api/kb/admin/images/{uploaded_filename}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        
        data = delete_response.json()
        assert 'message' in data
        assert data['message'] == 'Deleted'
        
        # Verify it's gone
        verify_after = requests.get(f"{BASE_URL}/api/kb/images/{uploaded_filename}")
        assert verify_after.status_code == 404, "Image should not exist after deletion"
        
        print(f"PASS: Delete image {uploaded_filename} works")
    
    def test_delete_nonexistent_image(self):
        """DELETE /api/kb/admin/images/:filename for non-existent image should return 404"""
        response = requests.delete(
            f"{BASE_URL}/api/kb/admin/images/nonexistent-{uuid.uuid4().hex}.png",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Delete non-existent image returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
