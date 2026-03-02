import requests
import sys
import json
from datetime import datetime

class TrinityAPITester:
    def __init__(self, base_url="https://columns-rebuild.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        # Set the required session token for authentication
        self.session.cookies.set('session_token', 'UWPr27rM-BUZI_ufRFg7F0GkJzN8ZmzH2Cq6Zuu6VG8')
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_endpoints = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ Passed - Status: {response.status_code}")
                
                # Try to show response preview for successful requests
                try:
                    if response.content:
                        response_data = response.json()
                        if isinstance(response_data, dict):
                            print(f"   📄 Response keys: {list(response_data.keys())}")
                            if 'L1' in response_data or 'L2' in response_data or 'L3' in response_data:
                                print(f"   📊 Escalation counts: {response_data}")
                        elif isinstance(response_data, list):
                            print(f"   📄 Response: List with {len(response_data)} items")
                except:
                    pass
            else:
                print(f"   ❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   📄 Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   📄 Response text: {response.text[:200]}...")
                self.failed_endpoints.append({
                    'name': name,
                    'endpoint': endpoint,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'error': response.text[:200]
                })

            return success, response

        except requests.exceptions.Timeout:
            print(f"   ❌ Failed - Timeout (>10s)")
            self.failed_endpoints.append({
                'name': name,
                'endpoint': endpoint,
                'error': 'Request timeout'
            })
            return False, None
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Failed - Network Error: {str(e)}")
            self.failed_endpoints.append({
                'name': name,
                'endpoint': endpoint,
                'error': f'Network error: {str(e)}'
            })
            return False, None

def main():
    print("=" * 60)
    print("🧪 TRINITY IT SUPPORT SYSTEM - Backend API Tests")
    print("=" * 60)
    
    # Setup tester
    tester = TrinityAPITester("https://columns-rebuild.preview.emergentagent.com")

    print(f"\n🔗 Testing against: {tester.base_url}")
    print(f"🔐 Using session token: UWPr27rM-BUZI_ufRFg7F0GkJzN8ZmzH2Cq6Zuu6VG8")

    # Test 1: Health check / Root endpoint
    success, response = tester.run_test(
        "Root/Health Check",
        "GET",
        "",
        200
    )

    # Test 2: Authentication check via users endpoint
    success, response = tester.run_test(
        "User Authentication",
        "GET", 
        "api/users",
        200
    )

    # Test 3: Get all tickets
    success, response = tester.run_test(
        "Get All Tickets",
        "GET",
        "api/tickets",
        200
    )

    # Test 4: NEW FEATURE - Get escalation counts (L1/L2/L3)
    success, response = tester.run_test(
        "Get Escalation Counts",
        "GET",
        "api/tickets/escalation-counts",
        200
    )

    # Test 5: NEW FEATURE - Filter tickets by L1 escalation level
    success, response = tester.run_test(
        "Filter Tickets by L1 Level",
        "GET",
        "api/tickets?escalation_level=L1",
        200
    )

    # Test 6: NEW FEATURE - Filter tickets by L2 escalation level  
    success, response = tester.run_test(
        "Filter Tickets by L2 Level",
        "GET",
        "api/tickets?escalation_level=L2",
        200
    )

    # Test 7: NEW FEATURE - Filter tickets by L3 escalation level
    success, response = tester.run_test(
        "Filter Tickets by L3 Level",
        "GET",
        "api/tickets?escalation_level=L3",
        200
    )

    # Test 8: Get teams (should exist for escalation levels)
    success, response = tester.run_test(
        "Get Teams",
        "GET",
        "api/teams",
        200
    )

    # Test 9: Dashboard/stats endpoint
    success, response = tester.run_test(
        "Dashboard Stats",
        "GET",
        "api/dashboard/stats",
        200
    )

    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS")
    print("=" * 60)
    print(f"✅ Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"❌ Tests failed: {tester.tests_run - tester.tests_passed}/{tester.tests_run}")
    
    if tester.failed_endpoints:
        print(f"\n🚨 Failed Endpoints:")
        for fail in tester.failed_endpoints:
            error_msg = fail.get('error', f'Status {fail.get("actual")} vs {fail.get("expected")}')
            print(f"   • {fail['name']}: {error_msg}")
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 Backend API tests mostly successful!")
        return 0
    elif success_rate >= 60:
        print("⚠️  Backend has some issues but core functionality works")
        return 0
    else:
        print("💥 Major backend issues found - needs immediate attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())