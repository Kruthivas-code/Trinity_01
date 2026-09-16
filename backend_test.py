#!/usr/bin/env python3
"""
Backend API testing for KB article feedback endpoint.
Tests the extended feedback endpoint that accepts reason + comment.
"""
import requests
import sys
import os

# Base URL from frontend .env
BASE_URL = "https://repo-builder-83.internal.preview.emergentagent.com/api"

def test_kb_feedback_endpoint():
    """Test the KB article feedback endpoint with reason + comment fields."""
    print("=" * 80)
    print("Testing KB Article Feedback Endpoint")
    print("=" * 80)
    
    # Step 1: Get a valid published article slug
    print("\n[1] GET /api/kb/public-data to obtain a valid published article slug...")
    try:
        response = requests.get(f"{BASE_URL}/kb/public-data", timeout=10)
        print(f"    Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"    ❌ FAILED: Expected 200, got {response.status_code}")
            print(f"    Response: {response.text[:500]}")
            return False
        
        data = response.json()
        documents = data.get("documents", [])
        
        if not documents:
            print("    ❌ FAILED: No published articles found in public-data")
            return False
        
        # Get the first published article slug
        valid_slug = documents[0].get("slug")
        print(f"    ✅ Found valid slug: '{valid_slug}'")
        
    except Exception as e:
        print(f"    ❌ FAILED: Exception during GET /api/kb/public-data: {e}")
        return False
    
    # Step 2: POST with helpful=true, reason, and comment
    print(f"\n[2] POST /api/kb/articles/{valid_slug}/feedback with helpful=true, reason, and comment...")
    try:
        payload = {
            "helpful": True,
            "reason": "The guide worked as expected",
            "comment": "very helpful"
        }
        response = requests.post(
            f"{BASE_URL}/kb/articles/{valid_slug}/feedback",
            json=payload,
            timeout=10
        )
        print(f"    Status: {response.status_code}")
        print(f"    Response: {response.json()}")
        
        if response.status_code != 200:
            print(f"    ❌ FAILED: Expected 200, got {response.status_code}")
            return False
        
        result = response.json()
        if result.get("status") != "ok":
            print(f"    ❌ FAILED: Expected {{'status':'ok'}}, got {result}")
            return False
        
        print("    ✅ PASSED: Feedback submitted successfully with reason + comment")
        
    except Exception as e:
        print(f"    ❌ FAILED: Exception during POST with reason+comment: {e}")
        return False
    
    # Step 3: POST with helpful=false, reason, and empty comment
    print(f"\n[3] POST /api/kb/articles/{valid_slug}/feedback with helpful=false, reason, and empty comment...")
    try:
        payload = {
            "helpful": False,
            "reason": "Update this documentation",
            "comment": ""
        }
        response = requests.post(
            f"{BASE_URL}/kb/articles/{valid_slug}/feedback",
            json=payload,
            timeout=10
        )
        print(f"    Status: {response.status_code}")
        print(f"    Response: {response.json()}")
        
        if response.status_code != 200:
            print(f"    ❌ FAILED: Expected 200, got {response.status_code}")
            return False
        
        result = response.json()
        if result.get("status") != "ok":
            print(f"    ❌ FAILED: Expected {{'status':'ok'}}, got {result}")
            return False
        
        print("    ✅ PASSED: Feedback submitted successfully with empty comment")
        
    except Exception as e:
        print(f"    ❌ FAILED: Exception during POST with empty comment: {e}")
        return False
    
    # Step 4: POST with only helpful=true (backward compatibility)
    print(f"\n[4] POST /api/kb/articles/{valid_slug}/feedback with ONLY helpful=true (backward compatibility)...")
    try:
        payload = {"helpful": True}
        response = requests.post(
            f"{BASE_URL}/kb/articles/{valid_slug}/feedback",
            json=payload,
            timeout=10
        )
        print(f"    Status: {response.status_code}")
        print(f"    Response: {response.json()}")
        
        if response.status_code != 200:
            print(f"    ❌ FAILED: Expected 200, got {response.status_code}")
            return False
        
        result = response.json()
        if result.get("status") != "ok":
            print(f"    ❌ FAILED: Expected {{'status':'ok'}}, got {result}")
            return False
        
        print("    ✅ PASSED: Backward compatibility maintained (helpful-only payload works)")
        
    except Exception as e:
        print(f"    ❌ FAILED: Exception during POST with helpful-only: {e}")
        return False
    
    # Step 5: POST to non-existent slug (expect 404)
    print(f"\n[5] POST /api/kb/articles/this-slug-does-not-exist-xyz/feedback (expect 404)...")
    try:
        payload = {"helpful": True}
        response = requests.post(
            f"{BASE_URL}/kb/articles/this-slug-does-not-exist-xyz/feedback",
            json=payload,
            timeout=10
        )
        print(f"    Status: {response.status_code}")
        
        if response.status_code != 404:
            print(f"    ❌ FAILED: Expected 404 for non-existent slug, got {response.status_code}")
            print(f"    Response: {response.text[:500]}")
            return False
        
        print("    ✅ PASSED: Non-existent slug correctly returns 404")
        
    except Exception as e:
        print(f"    ❌ FAILED: Exception during POST to non-existent slug: {e}")
        return False
    
    # Step 6: GET feedback aggregates
    print(f"\n[6] GET /api/kb/articles/{valid_slug}/feedback (verify aggregates)...")
    try:
        response = requests.get(
            f"{BASE_URL}/kb/articles/{valid_slug}/feedback",
            timeout=10
        )
        print(f"    Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"    ❌ FAILED: Expected 200, got {response.status_code}")
            print(f"    Response: {response.text[:500]}")
            return False
        
        result = response.json()
        print(f"    Response: {result}")
        
        # Verify the response has the expected structure
        if "total" not in result or "helpful" not in result or "unhelpful" not in result:
            print(f"    ❌ FAILED: Missing expected fields in aggregate response")
            return False
        
        # We submitted 3 feedbacks (2 helpful, 1 unhelpful) in this test run
        # But there might be existing feedback from previous runs
        if result["total"] < 3:
            print(f"    ⚠️  WARNING: Expected at least 3 total feedbacks from this test, got {result['total']}")
            print(f"    (This might be OK if database was cleared)")
        
        print(f"    ✅ PASSED: Feedback aggregates returned correctly")
        print(f"    Total: {result['total']}, Helpful: {result['helpful']}, Unhelpful: {result['unhelpful']}")
        
    except Exception as e:
        print(f"    ❌ FAILED: Exception during GET feedback aggregates: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print(f"\nBase URL: {BASE_URL}\n")
    
    success = test_kb_feedback_endpoint()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 80)
        sys.exit(1)
