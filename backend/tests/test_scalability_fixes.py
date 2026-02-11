"""
Test suite for Trinity scalability/production-readiness fixes.
Tests all 8 fixes: pagination, analytics aggregation, streaming export, notes pagination, indexes.
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = "http://localhost:8001"

# Setup test session directly in DB
def create_test_session():
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    token = "test_scalability_session"
    user_id = "test-scalability-user"
    
    # Ensure test user exists
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "name": "Test User", "email": "test@test.com", "role": "admin"}},
        upsert=True
    )
    
    # Create session
    db.sessions.update_one(
        {"session_token": token},
        {"$set": {
            "session_token": token,
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24)
        }},
        upsert=True
    )
    
    return token, user_id, db

TOKEN, USER_ID, DB = create_test_session()


@pytest.fixture(scope="module")
def s():
    session = requests.Session()
    session.cookies.set("session_token", TOKEN)
    return session


class TestHealth:
    def test_health(self, s):
        r = s.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


class TestTicketsPagination:
    def test_paginated_format(self, s):
        r = s.get(f"{BASE_URL}/api/tickets?page=1&limit=5")
        assert r.status_code == 200
        data = r.json()
        assert "tickets" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "has_more" in data
        assert isinstance(data["tickets"], list)
        assert data["page"] == 1
        assert data["limit"] == 5

    def test_has_more_flag(self, s):
        r = s.get(f"{BASE_URL}/api/tickets?page=1&limit=2")
        data = r.json()
        if data["total"] > 2:
            assert data["has_more"] is True
        r2 = s.get(f"{BASE_URL}/api/tickets?page=1&limit=10000")
        data2 = r2.json()
        assert data2["has_more"] is False

    def test_page_2_different_from_page_1(self, s):
        r1 = s.get(f"{BASE_URL}/api/tickets?page=1&limit=3")
        r2 = s.get(f"{BASE_URL}/api/tickets?page=2&limit=3")
        d1 = r1.json()
        d2 = r2.json()
        if d1["total"] > 3:
            ids1 = {t["ticket_id"] for t in d1["tickets"]}
            ids2 = {t["ticket_id"] for t in d2["tickets"]}
            assert ids1.isdisjoint(ids2), "Page 1 and Page 2 should have different tickets"

    def test_multiple_status_params(self, s):
        r = s.get(f"{BASE_URL}/api/tickets?status=todo&status=in_progress&limit=100")
        assert r.status_code == 200
        data = r.json()
        for t in data["tickets"]:
            assert t["status"] in ["todo", "in_progress"]

    def test_single_status_param(self, s):
        r = s.get(f"{BASE_URL}/api/tickets?status=todo&limit=100")
        assert r.status_code == 200
        data = r.json()
        for t in data["tickets"]:
            assert t["status"] == "todo"


class TestAnalyticsSummary:
    def test_summary_structure(self, s):
        r = s.get(f"{BASE_URL}/api/analytics/summary")
        assert r.status_code == 200
        data = r.json()
        assert "by_status" in data
        assert "by_assignee" in data
        assert "my_tickets" in data
        assert "total" in data
        assert isinstance(data["by_status"], dict)
        assert isinstance(data["total"], int)
        for status in ["todo", "in_progress", "waiting", "review", "resolved"]:
            assert status in data["by_status"]


class TestAnalyticsOverview:
    def test_overview_structure(self, s):
        r = s.get(f"{BASE_URL}/api/analytics/overview?days=30")
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "priority_breakdown" in data
        assert "status_breakdown" in data
        assert "volume_trend" in data
        assert "top_assignees" in data
        summary = data["summary"]
        assert "total_tickets" in summary
        assert "open_tickets" in summary
        assert isinstance(summary["total_tickets"], int)


class TestNotesPagination:
    def test_notes_paginated_format(self, s):
        # Get a ticket ID first
        r = s.get(f"{BASE_URL}/api/tickets?page=1&limit=1")
        tickets = r.json()["tickets"]
        if not tickets:
            pytest.skip("No tickets to test notes")
        tid = tickets[0]["ticket_id"]
        
        r = s.get(f"{BASE_URL}/api/tickets/{tid}/notes")
        assert r.status_code == 200
        data = r.json()
        assert "messages" in data
        assert "total" in data
        assert "page" in data
        assert "has_more" in data
        assert isinstance(data["messages"], list)

    def test_activity_paginated_format(self, s):
        r = s.get(f"{BASE_URL}/api/tickets?page=1&limit=1")
        tickets = r.json()["tickets"]
        if not tickets:
            pytest.skip("No tickets")
        tid = tickets[0]["ticket_id"]
        
        r = s.get(f"{BASE_URL}/api/tickets/{tid}/activity")
        assert r.status_code == 200
        data = r.json()
        assert "messages" in data
        assert "total" in data


class TestExportStreaming:
    def test_json_export(self, s):
        r = s.get(f"{BASE_URL}/api/export?format=json", stream=True)
        assert r.status_code == 200
        assert "application/json" in r.headers.get("content-type", "")
        content = r.text
        import json
        data = json.loads(content)
        assert isinstance(data, list)

    def test_csv_export(self, s):
        r = s.get(f"{BASE_URL}/api/export?format=csv", stream=True)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        lines = r.text.strip().split("\n")
        assert len(lines) >= 1  # At least header
        assert "ticket_id" in lines[0]


class TestEmailStatus:
    def test_email_status(self, s):
        r = s.get(f"{BASE_URL}/api/email/status")
        assert r.status_code == 200
        data = r.json()
        assert "connected" in data
        assert "email" in data
        if data["connected"]:
            assert data["email"] == "trinitysuccess44@gmail.com"
            assert "inbox_count" in data
