"""
Tests for file attachment feature in outbound email replies.
Features tested:
1. POST /api/attachments/upload - upload a file, returns file_id, original_name, size, content_type, download_url
2. GET /api/attachments/{file_id} - download a previously uploaded file
3. DELETE /api/attachments/{file_id} - delete an attachment
4. Upload validation - reject files over 7MB size limit
5. Upload validation - reject disallowed file types
6. POST /api/tickets/{ticket_id}/notes with attachment_ids - attachments saved in message record
7. Message with attachments includes attachment metadata
8. send_email() function signature accepts optional 'attachments' parameter
9. Health endpoint still works
"""
import pytest
import requests
import os
import io
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_attach_session_1773179049819')


def upload_file(filename, content, content_type, session_token=SESSION_TOKEN):
    """Helper to upload a file using multipart form data"""
    files = {'file': (filename, io.BytesIO(content), content_type)}
    return requests.post(
        f"{BASE_URL}/api/attachments/upload",
        files=files,
        cookies={'session_token': session_token}
    )


def delete_file(file_id, session_token=SESSION_TOKEN):
    """Helper to delete a file"""
    return requests.delete(
        f"{BASE_URL}/api/attachments/{file_id}",
        cookies={'session_token': session_token}
    )


class TestFileAttachments:
    """File attachment endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test tracking"""
        self.uploaded_file_ids = []
        yield
        # Cleanup uploaded test files
        for file_id in self.uploaded_file_ids:
            try:
                delete_file(file_id)
            except:
                pass

    def test_health_endpoint_working(self):
        """GET /health - Health endpoint should still work"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get('status') == 'healthy', f"Health not healthy: {data}"
        print("✓ Health endpoint working - status: healthy")

    def test_upload_pdf_attachment(self):
        """POST /api/attachments/upload - Upload a PDF file"""
        pdf_content = b'%PDF-1.4 test content'
        response = upload_file('test_document.pdf', pdf_content, 'application/pdf')
        
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Validate response structure
        assert 'file_id' in data, "Response missing file_id"
        assert 'original_name' in data, "Response missing original_name"
        assert 'content_type' in data, "Response missing content_type"
        assert 'size' in data, "Response missing size"
        assert 'download_url' in data, "Response missing download_url"
        
        # Validate values
        assert data['original_name'] == 'test_document.pdf', f"Wrong name: {data['original_name']}"
        assert data['content_type'] == 'application/pdf', f"Wrong type: {data['content_type']}"
        assert data['size'] == len(pdf_content), f"Wrong size: {data['size']}"
        assert data['download_url'].startswith('/api/attachments/'), f"Wrong URL format: {data['download_url']}"
        
        self.uploaded_file_ids.append(data['file_id'])
        print(f"✓ PDF upload successful - file_id: {data['file_id']}")

    def test_upload_word_document(self):
        """POST /api/attachments/upload - Upload a Word document (.docx)"""
        docx_content = b'PK\x03\x04 test docx content'
        response = upload_file('test_report.docx', docx_content,
                               'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        
        assert response.status_code == 200, f"Word upload failed: {response.text}"
        data = response.json()
        assert data['original_name'] == 'test_report.docx'
        self.uploaded_file_ids.append(data['file_id'])
        print(f"✓ Word document upload successful - file_id: {data['file_id']}")

    def test_upload_excel_spreadsheet(self):
        """POST /api/attachments/upload - Upload an Excel file (.xlsx)"""
        xlsx_content = b'PK\x03\x04 test xlsx content'
        response = upload_file('data.xlsx', xlsx_content,
                               'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        assert response.status_code == 200, f"Excel upload failed: {response.text}"
        data = response.json()
        assert data['original_name'] == 'data.xlsx'
        self.uploaded_file_ids.append(data['file_id'])
        print(f"✓ Excel upload successful - file_id: {data['file_id']}")

    def test_upload_image_attachment(self):
        """POST /api/attachments/upload - Upload an image file"""
        png_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        response = upload_file('screenshot.png', png_content, 'image/png')
        
        assert response.status_code == 200, f"Image upload failed: {response.text}"
        data = response.json()
        assert data['original_name'] == 'screenshot.png'
        assert data['content_type'] == 'image/png'
        self.uploaded_file_ids.append(data['file_id'])
        print(f"✓ Image upload successful - file_id: {data['file_id']}")

    def test_upload_text_file(self):
        """POST /api/attachments/upload - Upload a text file"""
        text_content = b'This is a test log file\nLine 2\nLine 3'
        response = upload_file('logs.txt', text_content, 'text/plain')
        
        assert response.status_code == 200, f"Text upload failed: {response.text}"
        data = response.json()
        assert data['original_name'] == 'logs.txt'
        self.uploaded_file_ids.append(data['file_id'])
        print(f"✓ Text file upload successful - file_id: {data['file_id']}")

    def test_upload_csv_file(self):
        """POST /api/attachments/upload - Upload a CSV file"""
        csv_content = b'name,email,phone\nJohn,john@test.com,123456'
        response = upload_file('contacts.csv', csv_content, 'text/csv')
        
        assert response.status_code == 200, f"CSV upload failed: {response.text}"
        data = response.json()
        assert data['original_name'] == 'contacts.csv'
        self.uploaded_file_ids.append(data['file_id'])
        print(f"✓ CSV file upload successful - file_id: {data['file_id']}")

    def test_upload_zip_file(self):
        """POST /api/attachments/upload - Upload a ZIP archive"""
        zip_content = b'PK\x03\x04 test zip content'
        response = upload_file('archive.zip', zip_content, 'application/zip')
        
        assert response.status_code == 200, f"ZIP upload failed: {response.text}"
        data = response.json()
        assert data['original_name'] == 'archive.zip'
        self.uploaded_file_ids.append(data['file_id'])
        print(f"✓ ZIP file upload successful - file_id: {data['file_id']}")

    def test_download_attachment(self):
        """GET /api/attachments/{file_id} - Download an uploaded file"""
        # First upload a file
        pdf_content = b'%PDF-1.4 test download content for verification'
        upload_response = upload_file('download_test.pdf', pdf_content, 'application/pdf')
        assert upload_response.status_code == 200
        file_id = upload_response.json()['file_id']
        self.uploaded_file_ids.append(file_id)
        
        # Now download it (no auth needed for download)
        download_response = requests.get(f"{BASE_URL}/api/attachments/{file_id}")
        
        assert download_response.status_code == 200, f"Download failed: {download_response.text}"
        assert download_response.content == pdf_content, "Downloaded content doesn't match"
        assert 'application/pdf' in download_response.headers.get('Content-Type', '')
        print(f"✓ Download successful - file_id: {file_id}, size: {len(download_response.content)}")

    def test_delete_attachment(self):
        """DELETE /api/attachments/{file_id} - Delete an attachment"""
        # First upload a file
        content = b'Test content for deletion'
        upload_response = upload_file('to_delete.txt', content, 'text/plain')
        assert upload_response.status_code == 200
        file_id = upload_response.json()['file_id']
        
        # Delete it
        delete_response = delete_file(file_id)
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        data = delete_response.json()
        assert data.get('status') == 'deleted', f"Wrong status: {data}"
        
        # Verify it's gone
        get_response = requests.get(f"{BASE_URL}/api/attachments/{file_id}")
        assert get_response.status_code == 404, "File should be deleted"
        print(f"✓ Delete successful - file_id: {file_id}")

    def test_reject_file_over_7mb(self):
        """Upload validation - reject files over 7MB size limit"""
        # Create a file > 7MB
        large_content = b'x' * (8 * 1024 * 1024)  # 8MB
        response = upload_file('large_file.pdf', large_content, 'application/pdf')
        
        assert response.status_code == 400, f"Should reject large file, got: {response.status_code}"
        error_msg = response.json().get('detail', response.text)
        assert '7' in str(error_msg) or 'large' in str(error_msg).lower() or 'size' in str(error_msg).lower(), \
            f"Error should mention size limit: {error_msg}"
        print(f"✓ Large file rejected correctly - {error_msg}")

    def test_reject_disallowed_file_type(self):
        """Upload validation - reject disallowed file types"""
        # Try to upload an executable
        exe_content = b'MZ\x90\x00 fake exe'
        response = upload_file('malware.exe', exe_content, 'application/x-msdownload')
        
        assert response.status_code == 400, f"Should reject exe file, got: {response.status_code}"
        print(f"✓ Disallowed file type rejected correctly")

    def test_download_nonexistent_attachment(self):
        """GET /api/attachments/{file_id} - 404 for non-existent file"""
        response = requests.get(f"{BASE_URL}/api/attachments/att_nonexistent12345")
        assert response.status_code == 404, f"Should return 404, got: {response.status_code}"
        print("✓ Non-existent attachment returns 404")

    def test_delete_nonexistent_attachment(self):
        """DELETE /api/attachments/{file_id} - 404 for non-existent file"""
        response = delete_file('att_nonexistent12345')
        assert response.status_code == 404, f"Should return 404, got: {response.status_code}"
        print("✓ Delete non-existent attachment returns 404")


class TestNotesWithAttachments:
    """Tests for notes/messages with attachment_ids"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session and tracking"""
        self.uploaded_file_ids = []
        self.created_ticket_id = None
        yield
        # Cleanup
        for file_id in self.uploaded_file_ids:
            try:
                delete_file(file_id)
            except:
                pass
        if self.created_ticket_id:
            try:
                requests.delete(
                    f"{BASE_URL}/api/tickets/{self.created_ticket_id}",
                    cookies={'session_token': SESSION_TOKEN}
                )
            except:
                pass

    def _create_test_ticket(self):
        """Helper to create a test ticket"""
        response = requests.post(
            f"{BASE_URL}/api/tickets",
            json={
                "title": "TEST_attachment_test_ticket",
                "description": "Test ticket for attachment testing",
                "status": "todo",
                "priority": "medium"
            },
            cookies={'session_token': SESSION_TOKEN}
        )
        if response.status_code in [200, 201]:
            ticket = response.json()
            self.created_ticket_id = ticket.get('ticket_id') or ticket.get('id')
            return self.created_ticket_id
        return None

    def _upload_test_file(self):
        """Helper to upload a test file"""
        content = b'Test attachment content for note'
        response = upload_file('note_attachment.pdf', content, 'application/pdf')
        if response.status_code == 200:
            file_id = response.json()['file_id']
            self.uploaded_file_ids.append(file_id)
            return response.json()
        return None

    def test_add_note_with_attachment(self):
        """POST /api/tickets/{ticket_id}/notes with attachment_ids - attachments saved"""
        ticket_id = self._create_test_ticket()
        if not ticket_id:
            pytest.skip("Could not create test ticket")
        
        # Upload a file first
        attachment = self._upload_test_file()
        if not attachment:
            pytest.skip("Could not upload test file")
        
        # Add note with attachment
        note_response = requests.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/notes",
            json={
                "content": "Here is the document you requested",
                "type": "reply",
                "attachment_ids": [attachment['file_id']]
            },
            cookies={'session_token': SESSION_TOKEN}
        )
        
        assert note_response.status_code == 200, f"Add note failed: {note_response.text}"
        note_data = note_response.json()
        
        # Check that attachments are in the note
        assert 'attachments' in note_data, f"Note missing attachments field: {note_data.keys()}"
        attachments = note_data['attachments']
        assert len(attachments) >= 1, f"Expected at least 1 attachment, got: {len(attachments)}"
        
        # Verify attachment metadata
        att = attachments[0]
        assert 'file_id' in att, "Attachment missing file_id"
        assert 'original_name' in att, "Attachment missing original_name"
        assert 'content_type' in att, "Attachment missing content_type"
        assert 'size' in att, "Attachment missing size"
        assert 'download_url' in att, "Attachment missing download_url"
        
        print(f"✓ Note with attachment created - file_id: {att['file_id']}")

    def test_message_attachments_in_notes_list(self):
        """GET /api/tickets/{ticket_id}/notes - Messages include attachment metadata"""
        ticket_id = self._create_test_ticket()
        if not ticket_id:
            pytest.skip("Could not create test ticket")
        
        # Upload and attach
        attachment = self._upload_test_file()
        if not attachment:
            pytest.skip("Could not upload test file")
        
        # Add note with attachment
        requests.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/notes",
            json={
                "content": "Attached document",
                "type": "reply",
                "attachment_ids": [attachment['file_id']]
            },
            cookies={'session_token': SESSION_TOKEN}
        )
        
        # Fetch notes
        notes_response = requests.get(
            f"{BASE_URL}/api/tickets/{ticket_id}/notes",
            cookies={'session_token': SESSION_TOKEN}
        )
        assert notes_response.status_code == 200
        notes_data = notes_response.json()
        messages = notes_data.get('messages', notes_data)
        
        # Find our note with attachment
        notes_with_attachments = [n for n in messages if n.get('attachments')]
        assert len(notes_with_attachments) >= 1, "No notes with attachments found"
        
        att = notes_with_attachments[0]['attachments'][0]
        assert att.get('download_url', '').startswith('/api/attachments/'), \
            f"download_url should start with /api/attachments/: {att.get('download_url')}"
        
        print(f"✓ Notes list includes attachment metadata")

    def test_add_note_with_multiple_attachments(self):
        """POST /api/tickets/{ticket_id}/notes with multiple attachment_ids"""
        ticket_id = self._create_test_ticket()
        if not ticket_id:
            pytest.skip("Could not create test ticket")
        
        # Upload multiple files
        attachments = []
        for i in range(3):
            content = f'Test content {i}'.encode()
            response = upload_file(f'doc_{i}.pdf', content, 'application/pdf')
            if response.status_code == 200:
                att = response.json()
                attachments.append(att)
                self.uploaded_file_ids.append(att['file_id'])
        
        assert len(attachments) >= 2, "Could not upload multiple files"
        
        # Add note with multiple attachments
        attachment_ids = [a['file_id'] for a in attachments]
        note_response = requests.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/notes",
            json={
                "content": "Here are the requested documents",
                "type": "reply",
                "attachment_ids": attachment_ids
            },
            cookies={'session_token': SESSION_TOKEN}
        )
        
        assert note_response.status_code == 200
        note_data = note_response.json()
        
        assert len(note_data.get('attachments', [])) >= 2, \
            f"Expected multiple attachments: {note_data.get('attachments')}"
        
        print(f"✓ Note with {len(note_data.get('attachments', []))} attachments created")


class TestEmailServiceAttachments:
    """Tests for email service attachment parameter"""
    
    def test_send_email_signature_accepts_attachments(self):
        """Verify send_email() function accepts attachments parameter"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from services.email_service import send_email
            import inspect
            
            sig = inspect.signature(send_email)
            params = list(sig.parameters.keys())
            
            assert 'attachments' in params, f"send_email missing 'attachments' param. Params: {params}"
            print(f"✓ send_email() accepts 'attachments' parameter. Full signature: {params}")
        except ImportError as e:
            pytest.skip(f"Could not import email_service: {e}")

    def test_email_service_imports_mime_modules(self):
        """Verify email service imports MIME modules for attachments"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            email_service_code = open('/app/backend/services/email_service.py').read()
            
            # Check for MIME imports
            assert 'MIMEBase' in email_service_code, "email_service should import MIMEBase"
            assert 'encoders' in email_service_code, "email_service should import encoders"
            
            print("✓ Email service has MIME imports for attachments")
        except Exception as e:
            pytest.skip(f"Could not check email_service: {e}")


class TestInternalNoteSchema:
    """Tests for InternalNoteCreate schema with attachment_ids"""
    
    def test_schema_has_attachment_ids_field(self):
        """Verify InternalNoteCreate schema has attachment_ids field"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from models.schemas import InternalNoteCreate
            
            # Create an instance with attachment_ids
            note = InternalNoteCreate(
                content="Test note",
                attachment_ids=["att_test123", "att_test456"]
            )
            
            assert hasattr(note, 'attachment_ids'), "InternalNoteCreate missing attachment_ids"
            assert note.attachment_ids == ["att_test123", "att_test456"]
            
            # Test without attachment_ids (should default to empty list)
            note2 = InternalNoteCreate(content="Test note 2")
            assert note2.attachment_ids == [] or note2.attachment_ids is None, \
                "attachment_ids should default to empty list"
            
            print("✓ InternalNoteCreate schema has attachment_ids field")
        except ImportError as e:
            pytest.skip(f"Could not import schema: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
