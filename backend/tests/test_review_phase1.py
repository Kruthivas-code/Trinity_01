"""
Phase 1 review-hardening tests (help-doc-v3 feature port): owner-gated KB
CRUD, nested/recursive scope resolution, owner-contact messaging, and the
assignment "done" gate.

No live MongoDB exists in this sandbox, so this harness patches pymongo's
MongoClient with mongomock BEFORE importing the app, then drives the real
FastAPI app (server.app) through fastapi.testclient.TestClient, overriding
get_current_user to stand in for different signed-in users. This is
deliberately a standalone module (not sharing the existing test_kb_*.py
files, which hit a live BASE_URL via `requests` and need a running server) --
run directly with `python -m pytest backend/tests/test_review_phase1.py`.
"""
import os
import sys

import mongomock
import pymongo

# Patch BEFORE anything imports database.py (which constructs a MongoClient
# at module import time).
pymongo.MongoClient = mongomock.MongoClient

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_review_phase1")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402  -- builds `app` against the mongomock-backed db
from database import users_collection  # noqa: E402
from dependencies import get_current_user  # noqa: E402
from routes.kb import kb_articles, kb_navigation  # noqa: E402
from routes.review import (  # noqa: E402
    review_assignments,
    review_comments_col,
    _find_group_node,
    _collect_node_slugs,
    resolve_group_scope_slugs,
    flatten_scope_slugs,
)

app = server.app
client = TestClient(app)

OWNER = {"email": "owner@trinity.test", "role": "admin", "name": "Owner"}
AGENT = {"email": "agent@trinity.test", "role": "agent", "name": "Agent"}
OTHER_AGENT = {"email": "other-agent@trinity.test", "role": "agent", "name": "Other Agent"}


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
def _clean_state():
    for col in (kb_articles, kb_navigation, review_assignments, review_comments_col, users_collection):
        col.delete_many({})
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _seed_article(slug, **overrides):
    doc = {
        "slug": slug, "title": slug, "description": "", "content_markdown": "# hi",
        "nav_group_key": "top", "nav_group_label": "Top", "section_key": "top",
        "section_label": "Top", "icon": "", "order": 0, "published": True,
    }
    doc.update(overrides)
    kb_articles.insert_one(dict(doc))
    return doc


# ─────────────────────── 1. Owner-gated CRUD ───────────────────────

class TestOwnerGatedCRUD:
    def test_create_article_403_for_non_owner(self):
        _as(AGENT)
        resp = client.post("/api/kb/admin/articles", json={
            "title": "New Page", "slug": "new-page", "nav_group_key": "top",
        })
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"].lower()

    def test_create_article_200_for_owner(self):
        _as(OWNER)
        resp = client.post("/api/kb/admin/articles", json={
            "title": "New Page", "slug": "new-page", "nav_group_key": "top",
        })
        assert resp.status_code == 200
        assert resp.json()["slug"] == "new-page"

    def test_delete_article_403_for_non_owner(self):
        _seed_article("to-delete")
        _as(AGENT)
        resp = client.delete("/api/kb/admin/articles/to-delete")
        assert resp.status_code == 403
        # article must still exist
        assert kb_articles.find_one({"slug": "to-delete"}) is not None

    def test_delete_article_200_for_owner(self):
        # Phase 2: delete_article is now a SOFT delete (moves to Trash rather
        # than destroying the row) — see test_kb_phase2_trash_versions.py for
        # full soft-delete/restore/purge coverage. This just confirms the
        # owner-gating on the endpoint itself still holds.
        _seed_article("to-delete")
        _as(OWNER)
        resp = client.delete("/api/kb/admin/articles/to-delete")
        assert resp.status_code == 200
        doc = kb_articles.find_one({"slug": "to-delete"})
        assert doc is not None
        assert doc.get("deleted_at") is not None

    def test_update_navigation_403_for_non_owner(self):
        _as(AGENT)
        resp = client.put("/api/kb/admin/navigation", json={"groups": []})
        assert resp.status_code == 403

    def test_update_navigation_200_for_owner(self):
        _as(OWNER)
        resp = client.put("/api/kb/admin/navigation", json={"groups": [
            {"type": "group", "key": "top", "label": "Top", "icon": "", "published": True, "children": []}
        ]})
        assert resp.status_code == 200
        assert resp.json()["groups"][0]["key"] == "top"

    def test_docs_settings_and_design_config_owner_gated(self):
        _as(AGENT)
        assert client.put("/api/kb/admin/docs-settings", json={"meta_title": "x"}).status_code == 403
        assert client.put("/api/kb/admin/design-config", json={"accent_color": "#000"}).status_code == 403
        _as(OWNER)
        assert client.put("/api/kb/admin/docs-settings", json={"meta_title": "x"}).status_code == 200
        assert client.put("/api/kb/admin/design-config", json={"accent_color": "#000"}).status_code == 200

    def test_bulk_move_owner_gated(self):
        kb_navigation.insert_one({"schema_version": 2, "groups": [
            {"type": "group", "key": "src", "label": "Src", "icon": "", "published": True, "children": []},
            {"type": "group", "key": "dst", "label": "Dst", "icon": "", "published": True, "children": []},
        ]})
        _as(AGENT)
        resp = client.post("/api/kb/admin/articles/bulk-move", json={"source_key": "src", "target_key": "dst"})
        assert resp.status_code == 403
        _as(OWNER)
        resp = client.post("/api/kb/admin/articles/bulk-move", json={"source_key": "src", "target_key": "dst"})
        assert resp.status_code == 200

    def test_can_edit_endpoint_reflects_role(self):
        _as(AGENT)
        resp = client.get("/api/kb/admin/can-edit/any-slug")
        assert resp.status_code == 200
        assert resp.json()["is_owner"] is False
        assert resp.json()["can_delete"] is False
        assert resp.json()["can_edit_content"] is True

        _as(OWNER)
        resp = client.get("/api/kb/admin/can-edit/any-slug")
        assert resp.json()["is_owner"] is True
        assert resp.json()["can_delete"] is True


# ─────────────────── 2. Content-edit stamping (open to any signed-in user) ───────────────────

class TestContentEditStamping:
    def test_non_owner_can_edit_content_and_gets_stamped(self):
        _seed_article("edit-me", title="Original")
        _as(AGENT)
        resp = client.put("/api/kb/admin/articles/edit-me", json={"title": "Edited by agent"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Edited by agent"
        assert data["reviewer_edited_by"] == AGENT["email"]
        assert data.get("reviewer_edited_at")

    def test_owner_edit_also_stamped(self):
        _seed_article("edit-me-2", title="Original")
        _as(OWNER)
        resp = client.put("/api/kb/admin/articles/edit-me-2", json={"title": "Edited by owner"})
        assert resp.status_code == 200
        assert resp.json()["reviewer_edited_by"] == OWNER["email"]


# ─────────────────── 3. Owner-contact messaging ───────────────────

class TestOwnerContactMessaging:
    def test_403_names_actual_owner_emails(self):
        users_collection.insert_one({"user_id": "u1", "email": "boss@trinity.test", "role": "admin"})
        users_collection.insert_one({"user_id": "u2", "email": "agent@trinity.test", "role": "agent"})
        _as(AGENT)
        resp = client.post("/api/kb/admin/articles", json={"title": "X", "slug": "x", "nav_group_key": "top"})
        assert resp.status_code == 403
        assert "boss@trinity.test" in resp.json()["detail"]

    def test_403_message_graceful_with_no_owners_in_db(self):
        _as(AGENT)  # no admin users seeded at all
        resp = client.post("/api/kb/admin/articles", json={"title": "X", "slug": "x", "nav_group_key": "top"})
        assert resp.status_code == 403
        assert "Only an admin can do this." in resp.json()["detail"]


# ─────────────────── 4. Nested/recursive scope resolution ───────────────────

def _tree_leaf_group():
    return [
        {"type": "group", "key": "leaf", "label": "Leaf", "icon": "", "published": True, "children": [
            {"type": "page", "slug": "p1"},
            {"type": "page", "slug": "p2"},
        ]},
    ]


def _tree_multilevel():
    # top -> mid -> deep -> pages, so a scope on "mid" must recurse two levels.
    return [
        {"type": "group", "key": "top", "label": "Top", "icon": "", "published": True, "children": [
            {"type": "group", "key": "mid", "label": "Mid", "icon": "", "published": True, "children": [
                {"type": "group", "key": "deep", "label": "Deep", "icon": "", "published": True, "children": [
                    {"type": "page", "slug": "deep-page-1"},
                    {"type": "page", "slug": "deep-page-2"},
                ]},
                {"type": "page", "slug": "mid-page"},
            ]},
        ]},
    ]


def _tree_mixed():
    # A group with BOTH direct pages and nested subgroups.
    return [
        {"type": "group", "key": "mixed", "label": "Mixed", "icon": "", "published": True, "children": [
            {"type": "page", "slug": "direct-1"},
            {"type": "group", "key": "sub-a", "label": "Sub A", "icon": "", "published": True, "children": [
                {"type": "page", "slug": "sub-a-page"},
            ]},
            {"type": "page", "slug": "direct-2"},
            {"type": "group", "key": "sub-b", "label": "Sub B", "icon": "", "published": True, "children": [
                {"type": "group", "key": "sub-b-nested", "label": "Sub B Nested", "icon": "", "published": True,
                 "children": [{"type": "page", "slug": "sub-b-nested-page"}]},
            ]},
        ]},
    ]


class TestNestedScopeResolutionPureFunction:
    """Exercises resolve_group_scope_slugs()/_find_group_node()/_collect_node_slugs()
    directly over hand-built tree dicts -- no DB involved."""

    def test_leaf_group(self):
        slugs = resolve_group_scope_slugs(_tree_leaf_group(), "leaf")
        assert sorted(slugs) == ["p1", "p2"]

    def test_group_with_nested_subgroups_multilevel(self):
        # Scoping on the middle group must pick up pages nested two levels
        # further down (the "deep" subgroup's pages), plus its own direct page.
        slugs = resolve_group_scope_slugs(_tree_multilevel(), "mid")
        assert sorted(slugs) == ["deep-page-1", "deep-page-2", "mid-page"]

        # Scoping on "top" (one level further up) must pick up everything.
        slugs_top = resolve_group_scope_slugs(_tree_multilevel(), "top")
        assert sorted(slugs_top) == ["deep-page-1", "deep-page-2", "mid-page"]

        # Scoping on the innermost "deep" group returns just its own pages.
        slugs_deep = resolve_group_scope_slugs(_tree_multilevel(), "deep")
        assert sorted(slugs_deep) == ["deep-page-1", "deep-page-2"]

    def test_group_with_mix_of_direct_pages_and_subgroups(self):
        slugs = resolve_group_scope_slugs(_tree_mixed(), "mixed")
        assert sorted(slugs) == ["direct-1", "direct-2", "sub-a-page", "sub-b-nested-page"]

        # A qualified scope_id ("top::nested") should resolve via its last segment.
        slugs_qualified = resolve_group_scope_slugs(_tree_mixed(), "mixed::sub-b")
        assert sorted(slugs_qualified) == ["sub-b-nested-page"]

    def test_nonexistent_scope_id_returns_empty(self):
        assert resolve_group_scope_slugs(_tree_mixed(), "does-not-exist") == []
        assert resolve_group_scope_slugs([], "anything") == []
        assert resolve_group_scope_slugs(_tree_mixed(), "") == []
        assert resolve_group_scope_slugs(_tree_mixed(), None) == []


class TestFlattenScopeSlugsEndToEnd:
    """flatten_scope_slugs() itself, reading a real (mongomock) kb_navigation doc."""

    def test_group_scope_through_live_nav_doc(self):
        kb_navigation.insert_one({"schema_version": 2, "groups": _tree_multilevel()})
        assert sorted(flatten_scope_slugs("group", "mid")) == ["deep-page-1", "deep-page-2", "mid-page"]

    def test_tab_scope_is_same_lookup_as_group(self):
        kb_navigation.insert_one({"schema_version": 2, "groups": _tree_multilevel()})
        assert sorted(flatten_scope_slugs("tab", "top")) == sorted(flatten_scope_slugs("group", "top"))

    def test_page_scope_returns_itself(self):
        assert flatten_scope_slugs("page", "some-slug") == ["some-slug"]

    def test_nonexistent_group_scope_empty_not_error(self):
        kb_navigation.insert_one({"schema_version": 2, "groups": _tree_leaf_group()})
        assert flatten_scope_slugs("group", "no-such-key") == []

    def test_no_nav_doc_at_all_returns_empty(self):
        assert flatten_scope_slugs("group", "leaf") == []


# ─────────────────── 5. Done gate ───────────────────

class TestDoneGate:
    def _make_assignment(self, slugs):
        a = {
            "id": "asg-1", "scope_type": "page", "scope_id": slugs[0], "scope_label": "test",
            "assignee_email": AGENT["email"], "assigned_by": OWNER["email"], "assigned_by_name": "Owner",
            "status": "in_review", "slugs": slugs, "delegated_from": None, "due_date": None,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
        }
        review_assignments.insert_one(dict(a))
        return a

    def test_400_with_unresolved_comments(self):
        self._make_assignment(["page-a", "page-b"])
        review_comments_col.insert_one({
            "id": "c1", "doc_slug": "page-a", "author_email": AGENT["email"], "body": "fix this",
            "resolved": False, "read_by": [], "created_at": "2026-01-01T00:00:00",
        })
        _as(AGENT)
        resp = client.put("/api/review/assignments/asg-1", json={"status": "done"})
        assert resp.status_code == 400
        assert "unresolved comment" in resp.json()["detail"].lower()
        assert review_assignments.find_one({"id": "asg-1"})["status"] == "in_review"

    def test_200_once_comments_resolved(self):
        self._make_assignment(["page-a", "page-b"])
        review_comments_col.insert_one({
            "id": "c1", "doc_slug": "page-a", "author_email": AGENT["email"], "body": "fix this",
            "resolved": True, "read_by": [], "created_at": "2026-01-01T00:00:00",
        })
        _as(AGENT)
        resp = client.put("/api/review/assignments/asg-1", json={"status": "done"})
        assert resp.status_code == 200
        assert review_assignments.find_one({"id": "asg-1"})["status"] == "done"

    def test_200_with_no_comments_at_all(self):
        self._make_assignment(["page-c"])
        _as(AGENT)
        resp = client.put("/api/review/assignments/asg-1", json={"status": "done"})
        assert resp.status_code == 200

    def test_non_done_status_change_unaffected_by_open_comments(self):
        self._make_assignment(["page-a"])
        review_comments_col.insert_one({
            "id": "c1", "doc_slug": "page-a", "author_email": AGENT["email"], "body": "note",
            "resolved": False, "read_by": [], "created_at": "2026-01-01T00:00:00",
        })
        _as(AGENT)
        resp = client.put("/api/review/assignments/asg-1", json={"status": "in_review"})
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
