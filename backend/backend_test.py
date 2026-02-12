import requests
import sys
import json
import io
from datetime import datetime

class TickFlowAPITester:
    def __init__(self, base_url="https://api-guide-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_result(self, test_name, passed, message="", response_data=None):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED - {message}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message,
            "response": response_data
        })

    def test_health(self):
        """Test health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_result("Health Check", True, response_data=data)
                return True
            else:
                self.log_result("Health Check", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Health Check", False, str(e))
            return False

    def test_register(self):
        """Test user registration"""
        try:
            timestamp = datetime.now().strftime("%H%M%S%f")
            user_data = {
                "email": f"test_{timestamp}@tickflow.com",
                "password": "TestPass123!",
                "name": f"Test User {timestamp}"
            }
            
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=user_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.token = data["access_token"]
                    self.user_id = data["user"].get("id")
                    self.log_result("User Registration", True, response_data={"user_id": self.user_id})
                    return True
                else:
                    self.log_result("User Registration", False, "Missing token or user in response")
                    return False
            else:
                self.log_result("User Registration", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("User Registration", False, str(e))
            return False

    def test_login(self):
        """Test user login with existing credentials"""
        try:
            # Use the same credentials from registration
            timestamp = datetime.now().strftime("%H%M%S%f")
            # Create a new user first
            user_data = {
                "email": f"login_test_{timestamp}@tickflow.com",
                "password": "LoginPass123!",
                "name": f"Login Test {timestamp}"
            }
            
            # Register
            reg_response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=user_data,
                timeout=10
            )
            
            if reg_response.status_code != 200:
                self.log_result("User Login", False, "Failed to create test user for login")
                return False
            
            # Now login
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.log_result("User Login", True)
                    return True
                else:
                    self.log_result("User Login", False, "Missing token in response")
                    return False
            else:
                self.log_result("User Login", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("User Login", False, str(e))
            return False

    def test_get_current_user(self):
        """Test getting current user info"""
        if not self.token:
            self.log_result("Get Current User", False, "No token available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/users/me",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "email" in data:
                    self.log_result("Get Current User", True, response_data=data)
                    return True
                else:
                    self.log_result("Get Current User", False, "Missing user fields")
                    return False
            else:
                self.log_result("Get Current User", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get Current User", False, str(e))
            return False

    def test_get_users(self):
        """Test getting all users"""
        if not self.token:
            self.log_result("Get All Users", False, "No token available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/users",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Get All Users", True, response_data={"count": len(data)})
                    return True
                else:
                    self.log_result("Get All Users", False, "Response is not a list")
                    return False
            else:
                self.log_result("Get All Users", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get All Users", False, str(e))
            return False

    def test_create_ticket(self):
        """Test creating a ticket"""
        if not self.token:
            self.log_result("Create Ticket", False, "No token available")
            return False, None
        
        try:
            ticket_data = {
                "title": "Test Ticket",
                "description": "This is a test ticket",
                "status": "backlog",
                "assignee_id": self.user_id
            }
            
            response = requests.post(
                f"{self.base_url}/api/tickets",
                json=ticket_data,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "title" in data:
                    self.log_result("Create Ticket", True, response_data={"ticket_id": data["id"]})
                    return True, data["id"]
                else:
                    self.log_result("Create Ticket", False, "Missing ticket fields")
                    return False, None
            else:
                self.log_result("Create Ticket", False, f"Status {response.status_code}: {response.text}")
                return False, None
        except Exception as e:
            self.log_result("Create Ticket", False, str(e))
            return False, None

    def test_get_tickets(self):
        """Test getting all tickets"""
        if not self.token:
            self.log_result("Get All Tickets", False, "No token available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tickets",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Get All Tickets", True, response_data={"count": len(data)})
                    return True
                else:
                    self.log_result("Get All Tickets", False, "Response is not a list")
                    return False
            else:
                self.log_result("Get All Tickets", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get All Tickets", False, str(e))
            return False

    def test_get_single_ticket(self, ticket_id):
        """Test getting a single ticket"""
        if not self.token or not ticket_id:
            self.log_result("Get Single Ticket", False, "No token or ticket_id available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tickets/{ticket_id}",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data["id"] == ticket_id:
                    self.log_result("Get Single Ticket", True)
                    return True
                else:
                    self.log_result("Get Single Ticket", False, "Ticket ID mismatch")
                    return False
            else:
                self.log_result("Get Single Ticket", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get Single Ticket", False, str(e))
            return False

    def test_update_ticket(self, ticket_id):
        """Test updating a ticket"""
        if not self.token or not ticket_id:
            self.log_result("Update Ticket", False, "No token or ticket_id available")
            return False
        
        try:
            update_data = {
                "title": "Updated Test Ticket",
                "status": "todo"
            }
            
            response = requests.put(
                f"{self.base_url}/api/tickets/{ticket_id}",
                json=update_data,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("title") == "Updated Test Ticket":
                    self.log_result("Update Ticket", True)
                    return True
                else:
                    self.log_result("Update Ticket", False, "Title not updated")
                    return False
            else:
                self.log_result("Update Ticket", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Update Ticket", False, str(e))
            return False

    def test_analytics(self):
        """Test analytics endpoint"""
        if not self.token:
            self.log_result("Analytics", False, "No token available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/analytics/summary",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "by_status" in data and "total" in data:
                    self.log_result("Analytics", True, response_data=data)
                    return True
                else:
                    self.log_result("Analytics", False, "Missing analytics fields")
                    return False
            else:
                self.log_result("Analytics", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Analytics", False, str(e))
            return False

    def test_export_json(self):
        """Test exporting tickets as JSON"""
        if not self.token:
            self.log_result("Export JSON", False, "No token available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/export?format=json",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        self.log_result("Export JSON", True, response_data={"count": len(data)})
                        return True
                    else:
                        self.log_result("Export JSON", False, "Response is not a list")
                        return False
                except:
                    self.log_result("Export JSON", False, "Invalid JSON response")
                    return False
            else:
                self.log_result("Export JSON", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Export JSON", False, str(e))
            return False

    def test_export_csv(self):
        """Test exporting tickets as CSV"""
        if not self.token:
            self.log_result("Export CSV", False, "No token available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/export?format=csv",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                content = response.text
                if "id,title,description,status" in content or len(content) > 0:
                    self.log_result("Export CSV", True)
                    return True
                else:
                    self.log_result("Export CSV", False, "Invalid CSV content")
                    return False
            else:
                self.log_result("Export CSV", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Export CSV", False, str(e))
            return False

    def test_import_json(self):
        """Test importing tickets from JSON"""
        if not self.token:
            self.log_result("Import JSON", False, "No token available")
            return False
        
        try:
            # Create a test JSON file
            test_data = [
                {
                    "title": "Imported Ticket 1",
                    "description": "Test import",
                    "status": "backlog"
                }
            ]
            
            files = {
                'file': ('test_tickets.json', json.dumps(test_data), 'application/json')
            }
            
            response = requests.post(
                f"{self.base_url}/api/import",
                files=files,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "count" in data and data["count"] > 0:
                    self.log_result("Import JSON", True, response_data=data)
                    return True
                else:
                    self.log_result("Import JSON", False, "No tickets imported")
                    return False
            else:
                self.log_result("Import JSON", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Import JSON", False, str(e))
            return False

    def test_import_csv(self):
        """Test importing tickets from CSV"""
        if not self.token:
            self.log_result("Import CSV", False, "No token available")
            return False
        
        try:
            # Create a test CSV file
            csv_content = "title,description,status\nImported CSV Ticket,Test CSV import,todo"
            
            files = {
                'file': ('test_tickets.csv', csv_content, 'text/csv')
            }
            
            response = requests.post(
                f"{self.base_url}/api/import",
                files=files,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "count" in data and data["count"] > 0:
                    self.log_result("Import CSV", True, response_data=data)
                    return True
                else:
                    self.log_result("Import CSV", False, "No tickets imported")
                    return False
            else:
                self.log_result("Import CSV", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Import CSV", False, str(e))
            return False

    def test_delete_ticket(self, ticket_id):
        """Test deleting a ticket"""
        if not self.token or not ticket_id:
            self.log_result("Delete Ticket", False, "No token or ticket_id available")
            return False
        
        try:
            response = requests.delete(
                f"{self.base_url}/api/tickets/{ticket_id}",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_result("Delete Ticket", True)
                    return True
                else:
                    self.log_result("Delete Ticket", False, "Missing success message")
                    return False
            else:
                self.log_result("Delete Ticket", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Delete Ticket", False, str(e))
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n" + "="*60)
        print("TickFlow Backend API Testing")
        print("="*60 + "\n")
        
        # Test health
        if not self.test_health():
            print("\n⚠️  Health check failed. Backend may not be running.")
            return False
        
        # Test auth
        if not self.test_register():
            print("\n⚠️  Registration failed. Cannot proceed with authenticated tests.")
            return False
        
        self.test_login()
        self.test_get_current_user()
        self.test_get_users()
        
        # Test tickets
        success, ticket_id = self.test_create_ticket()
        if success and ticket_id:
            self.test_get_single_ticket(ticket_id)
            self.test_update_ticket(ticket_id)
        
        self.test_get_tickets()
        
        # Test analytics
        self.test_analytics()
        
        # Test export/import
        self.test_export_json()
        self.test_export_csv()
        self.test_import_json()
        self.test_import_csv()
        
        # Test delete (create a new ticket first)
        success, delete_ticket_id = self.test_create_ticket()
        if success and delete_ticket_id:
            self.test_delete_ticket(delete_ticket_id)
        
        # Print summary
        print("\n" + "="*60)
        print(f"Tests Passed: {self.tests_passed}/{self.tests_run}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print("="*60 + "\n")
        
        return self.tests_passed == self.tests_run

def main():
    tester = TickFlowAPITester()
    success = tester.run_all_tests()
    
    # Save results
    with open('/app/backend/test_results.json', 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": tester.tests_run,
            "passed_tests": tester.tests_passed,
            "failed_tests": tester.tests_run - tester.tests_passed,
            "success_rate": f"{(tester.tests_passed/tester.tests_run*100):.1f}%",
            "results": tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
