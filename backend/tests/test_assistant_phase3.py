"""
Phase 3 tests (help-doc-v3 feature port): AI Writing Assistant
(routes/assistant.py) -- tweak / generate / chat.

Same mongomock + FastAPI TestClient harness as test_review_phase1.py and
test_kb_phase2_trash_versions.py -- standalone module, run directly with
`python -m pytest backend/tests/test_assistant_phase3.py`.

The real LLM call (routes.assistant._send, which lazily imports
emergentintegrations) is never exercised here -- every "successful" test
monkeypatches `_send` with an AsyncMock so no network call happens and the
`emergentintegrations` package does not need to be installed to run this
suite. EMERGENT_LLM_KEY is also monkeypatched per-test (module-level, the
same name routes.assistant checks) rather than relying on the environment.
"""
import os
import sys
from unittest.mock import AsyncMock

import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_assistant_phase3")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
import routes.assistant as assistant_module  # noqa: E402
from database import users_collection  # noqa: E402
from dependencies import get_current_user  # noqa: E402
from routes.kb import kb_articles, kb_navigation  # noqa: E402

app = server.app
client = TestClient(app)

OWNER = {"email": "owner@trinity.test", "role": "admin", "name": "Owner"}
AGENT = {"email": "agent@trinity.test", "role": "agent", "name": "Agent"}


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _as_anonymous():
    """No override -- the real get_current_user dependency runs, and with
    no session cookie / API key on the TestClient it raises 401."""
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _clean_state():
    for col in (kb_articles, kb_navigation, users_collection):
        col.delete_many({})
    app.dependency_overrides.clear()
    assistant_module.EMERGENT_LLM_KEY = "test-key"
    yield
    app.dependency_overrides.clear()


# ─────────────────────────── Auth ───────────────────────────

class TestAuthEnforced:
    def test_tweak_requires_signin(self):
        _as_anonymous()
        resp = client.post("/api/assistant/tweak", json={"instruction": "polish", "markdown": "# hi"})
        assert resp.status_code == 401

    def test_generate_requires_signin(self):
        _as_anonymous()
        resp = client.post("/api/assistant/generate", json={"raw_input": "some notes"})
        assert resp.status_code == 401

    def test_chat_requires_signin(self):
        _as_anonymous()
        resp = client.post("/api/assistant/chat", json={"message": "is this clear?"})
        assert resp.status_code == 401


# ───────────────────── Request validation ─────────────────────

class TestValidation:
    def test_tweak_missing_field_is_422(self):
        _as(AGENT)
        resp = client.post("/api/assistant/tweak", json={"instruction": "polish"})  # no markdown
        assert resp.status_code == 422

    def test_tweak_empty_instruction_is_400(self):
        _as(AGENT)
        resp = client.post("/api/assistant/tweak", json={"instruction": "  ", "markdown": "# hi"})
        assert resp.status_code == 400

    def test_tweak_empty_markdown_and_selection_is_400(self):
        _as(AGENT)
        resp = client.post("/api/assistant/tweak", json={"instruction": "polish", "markdown": "  "})
        assert resp.status_code == 400

    def test_generate_missing_field_is_422(self):
        _as(AGENT)
        resp = client.post("/api/assistant/generate", json={})
        assert resp.status_code == 422

    def test_generate_empty_raw_input_is_400(self):
        _as(AGENT)
        resp = client.post("/api/assistant/generate", json={"raw_input": "   "})
        assert resp.status_code == 400

    def test_chat_missing_field_is_422(self):
        _as(AGENT)
        resp = client.post("/api/assistant/chat", json={})
        assert resp.status_code == 422

    def test_chat_empty_message_is_400(self):
        _as(AGENT)
        resp = client.post("/api/assistant/chat", json={"message": ""})
        assert resp.status_code == 400


# ──────────────────── LLM key not configured ────────────────────

class TestNotConfigured:
    def test_tweak_503_when_key_missing(self):
        _as(AGENT)
        assistant_module.EMERGENT_LLM_KEY = ""
        resp = client.post("/api/assistant/tweak", json={"instruction": "polish", "markdown": "# hi"})
        assert resp.status_code == 503

    def test_generate_503_when_key_missing(self):
        _as(AGENT)
        assistant_module.EMERGENT_LLM_KEY = ""
        resp = client.post("/api/assistant/generate", json={"raw_input": "notes"})
        assert resp.status_code == 503

    def test_chat_503_when_key_missing(self):
        _as(AGENT)
        assistant_module.EMERGENT_LLM_KEY = ""
        resp = client.post("/api/assistant/chat", json={"message": "help?"})
        assert resp.status_code == 503


# ───────────── Successful mocked response flows through ─────────────

class TestMockedSuccess:
    def test_tweak_whole_doc(self, monkeypatch):
        _as(AGENT)
        monkeypatch.setattr(assistant_module, "_send", AsyncMock(return_value="# Polished\n\nBetter text."))
        resp = client.post("/api/assistant/tweak", json={
            "instruction": "Improve writing", "markdown": "# Draft\n\nrough text.",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["markdown"] == "# Polished\n\nBetter text."
        assert body["applied_to_selection"] is False

    def test_tweak_selection_flag(self, monkeypatch):
        _as(AGENT)
        monkeypatch.setattr(assistant_module, "_send", AsyncMock(return_value="rewritten slice"))
        resp = client.post("/api/assistant/tweak", json={
            "instruction": "Shorten", "markdown": "# Doc\n\nfull body", "selection": "full body",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["markdown"] == "rewritten slice"
        assert body["applied_to_selection"] is True

    def test_generate_returns_markdown_and_title(self, monkeypatch):
        _as(AGENT)
        monkeypatch.setattr(assistant_module, "_send", AsyncMock(return_value="## Overview\n\nGenerated body."))
        resp = client.post("/api/assistant/generate", json={
            "raw_input": "webhooks fire on payment.succeeded", "title": "Webhooks", "style": "tutorial",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["markdown"] == "## Overview\n\nGenerated body."
        assert body["title"] == "Webhooks"

    def test_chat_returns_reply(self, monkeypatch):
        _as(AGENT)
        monkeypatch.setattr(assistant_module, "_send", AsyncMock(return_value="The intro could be tighter."))
        resp = client.post("/api/assistant/chat", json={
            "message": "Is the intro clear?", "markdown": "# Doc\n\nSome intro text.",
        })
        assert resp.status_code == 200
        assert resp.json() == {"reply": "The intro could be tighter."}

    def test_send_receives_component_guide_in_system_message(self, monkeypatch):
        """The system prompt actually reaches the LLM call with Trinity's own
        component vocabulary (not help-doc-v3's), e.g. Tab's `label` prop and
        the bare (no-attributes) <CardGroup> tag."""
        _as(AGENT)
        captured = {}

        async def _fake_send(system_message, user_prompt, session_prefix):
            captured["system_message"] = system_message
            return "ok"

        monkeypatch.setattr(assistant_module, "_send", _fake_send)
        resp = client.post("/api/assistant/generate", json={"raw_input": "notes"})
        assert resp.status_code == 200
        assert '<Tab label="' in captured["system_message"]
        assert "<CardGroup>" in captured["system_message"]
        # Explicitly warns the model away from help-doc-v3's dialect, which
        # this platform's parser does not recognize.
        assert "never `title`" in captured["system_message"].lower() or "no `<tab title=" in captured["system_message"].lower()


# ───────── New-Page owner-gating decision: no backdoor around Phase 1 ─────────

class TestNewPageOwnerGatingDecision:
    """This router has no page-creation endpoint of its own. /generate is
    open to any signed-in user (content-level AI help, Phase 1 philosophy),
    but the actual creation step is still the existing, unmodified,
    owner-gated POST /api/kb/admin/articles (routes/kb.py's create_article).
    These tests prove that combination holds: a non-owner can draft, but
    still cannot create."""

    def test_agent_can_generate_a_draft(self, monkeypatch):
        _as(AGENT)
        monkeypatch.setattr(assistant_module, "_send", AsyncMock(return_value="## Draft body"))
        resp = client.post("/api/assistant/generate", json={"raw_input": "notes", "title": "New Page"})
        assert resp.status_code == 200
        assert resp.json()["markdown"] == "## Draft body"

    def test_agent_still_403s_creating_the_article_from_that_draft(self, monkeypatch):
        _as(AGENT)
        monkeypatch.setattr(assistant_module, "_send", AsyncMock(return_value="## Draft body"))
        draft = client.post("/api/assistant/generate", json={"raw_input": "notes", "title": "New Page"}).json()

        create_resp = client.post("/api/kb/admin/articles", json={
            "title": "New Page", "slug": "new-page", "content_markdown": draft["markdown"],
            "nav_group_key": "top", "nav_group_label": "Top",
        })
        assert create_resp.status_code == 403
        assert kb_articles.find_one({"slug": "new-page"}) is None

    def test_owner_can_create_the_article_from_that_draft(self, monkeypatch):
        _as(OWNER)
        monkeypatch.setattr(assistant_module, "_send", AsyncMock(return_value="## Draft body"))
        draft = client.post("/api/assistant/generate", json={"raw_input": "notes", "title": "New Page"}).json()

        create_resp = client.post("/api/kb/admin/articles", json={
            "title": "New Page", "slug": "new-page", "content_markdown": draft["markdown"],
            "nav_group_key": "top", "nav_group_label": "Top",
        })
        assert create_resp.status_code == 200
        assert kb_articles.find_one({"slug": "new-page"}) is not None
