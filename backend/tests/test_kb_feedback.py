"""
KB Article Feedback API Tests
Tests the 'Was this article helpful?' feedback widget feature
- POST /api/kb/articles/{slug}/feedback - submit feedback
- GET /api/kb/articles/{slug}/feedback - get feedback stats
- GET /api/kb/admin/articles - includes feedback_total/feedback_helpful per article
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestKBFeedbackSubmission:
    """Tests for submitting article feedback"""

    def test_submit_helpful_feedback(self):
        """POST /api/kb/articles/{slug}/feedback with helpful=true returns {status: ok}"""
        response = requests.post(
            f"{BASE_URL}/api/kb/articles/welcome/feedback",
            json={"helpful": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("PASS: Submit helpful feedback returns {status: ok}")

    def test_submit_unhelpful_feedback(self):
        """POST /api/kb/articles/{slug}/feedback with helpful=false returns {status: ok}"""
        response = requests.post(
            f"{BASE_URL}/api/kb/articles/first-app/feedback",
            json={"helpful": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("PASS: Submit unhelpful feedback returns {status: ok}")

    def test_submit_feedback_nonexistent_article(self):
        """POST /api/kb/articles/{slug}/feedback returns 404 for non-existent article"""
        response = requests.post(
            f"{BASE_URL}/api/kb/articles/nonexistent-article-xyz/feedback",
            json={"helpful": True}
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        print("PASS: Feedback on non-existent article returns 404")


class TestKBFeedbackRetrieval:
    """Tests for retrieving feedback stats"""

    def test_get_feedback_stats(self):
        """GET /api/kb/articles/{slug}/feedback returns {total, helpful, unhelpful}"""
        response = requests.get(f"{BASE_URL}/api/kb/articles/welcome/feedback")
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "total" in data, "Response should have 'total' field"
        assert "helpful" in data, "Response should have 'helpful' field"
        assert "unhelpful" in data, "Response should have 'unhelpful' field"
        
        # Validate data types
        assert isinstance(data["total"], int)
        assert isinstance(data["helpful"], int)
        assert isinstance(data["unhelpful"], int)
        
        # Validate math: total = helpful + unhelpful
        assert data["total"] == data["helpful"] + data["unhelpful"], "total should equal helpful + unhelpful"
        
        print(f"PASS: Feedback stats - total={data['total']}, helpful={data['helpful']}, unhelpful={data['unhelpful']}")

    def test_get_feedback_stats_article_no_feedback(self):
        """GET /api/kb/articles/{slug}/feedback returns zeros for article without feedback"""
        # Pick an article unlikely to have feedback
        response = requests.get(f"{BASE_URL}/api/kb/articles/deployment-related-issues/feedback")
        assert response.status_code == 200
        data = response.json()
        
        # Should still return proper structure
        assert "total" in data
        assert "helpful" in data
        assert "unhelpful" in data
        print(f"PASS: Article with no/minimal feedback returns proper structure: {data}")


class TestAdminArticlesFeedbackStats:
    """Tests for admin articles endpoint including feedback stats"""

    def test_admin_articles_includes_feedback_fields(self, auth_session):
        """GET /api/kb/admin/articles includes feedback_total and feedback_helpful fields"""
        response = auth_session.get(f"{BASE_URL}/api/kb/admin/articles")
        
        # If unauthorized, skip test (admin requires Google OAuth)
        if response.status_code == 401:
            pytest.skip("Admin endpoint requires Google OAuth - cannot test via curl")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "articles" in data
        articles = data["articles"]
        
        if len(articles) > 0:
            article = articles[0]
            assert "feedback_total" in article, "Admin article should have feedback_total"
            assert "feedback_helpful" in article, "Admin article should have feedback_helpful"
            assert isinstance(article["feedback_total"], int)
            assert isinstance(article["feedback_helpful"], int)
            print(f"PASS: Admin articles include feedback stats - first article: total={article['feedback_total']}, helpful={article['feedback_helpful']}")
        else:
            print("PASS: Admin endpoint returned empty articles list but structure is correct")


@pytest.fixture
def auth_session():
    """Create a session that may include auth cookies if available"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestFeedbackDataIntegrity:
    """Test feedback data integrity - submit and verify counts change"""

    def test_feedback_count_increments_after_submission(self):
        """Verify feedback count increments after submitting feedback"""
        article_slug = "faqs"  # Use a less-trafficked article
        
        # Get current stats
        before = requests.get(f"{BASE_URL}/api/kb/articles/{article_slug}/feedback").json()
        before_total = before.get("total", 0)
        before_helpful = before.get("helpful", 0)
        
        # Submit helpful feedback
        submit_response = requests.post(
            f"{BASE_URL}/api/kb/articles/{article_slug}/feedback",
            json={"helpful": True}
        )
        assert submit_response.status_code == 200
        
        # Get updated stats
        after = requests.get(f"{BASE_URL}/api/kb/articles/{article_slug}/feedback").json()
        after_total = after.get("total", 0)
        after_helpful = after.get("helpful", 0)
        
        # Verify increments
        assert after_total == before_total + 1, f"Total should increment: {before_total} -> {after_total}"
        assert after_helpful == before_helpful + 1, f"Helpful should increment: {before_helpful} -> {after_helpful}"
        
        print(f"PASS: Feedback counts incremented correctly - total: {before_total}->{after_total}, helpful: {before_helpful}->{after_helpful}")

    def test_unhelpful_feedback_increments_correctly(self):
        """Verify unhelpful feedback increments unhelpful count only"""
        article_slug = "how-apps-work"  # Use another article
        
        # Get current stats
        before = requests.get(f"{BASE_URL}/api/kb/articles/{article_slug}/feedback").json()
        before_total = before.get("total", 0)
        before_unhelpful = before.get("unhelpful", 0)
        
        # Submit unhelpful feedback
        submit_response = requests.post(
            f"{BASE_URL}/api/kb/articles/{article_slug}/feedback",
            json={"helpful": False}
        )
        assert submit_response.status_code == 200
        
        # Get updated stats
        after = requests.get(f"{BASE_URL}/api/kb/articles/{article_slug}/feedback").json()
        after_total = after.get("total", 0)
        after_unhelpful = after.get("unhelpful", 0)
        
        # Verify increments
        assert after_total == before_total + 1, f"Total should increment: {before_total} -> {after_total}"
        assert after_unhelpful == before_unhelpful + 1, f"Unhelpful should increment: {before_unhelpful} -> {after_unhelpful}"
        
        print(f"PASS: Unhelpful feedback counts correctly - total: {before_total}->{after_total}, unhelpful: {before_unhelpful}->{after_unhelpful}")
