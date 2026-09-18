"""
Phase 2 tests (help-doc-v3 feature port): KB Trash (soft-delete) and Version
History.

Same mongomock + FastAPI TestClient harness as test_review_phase1.py --
standalone module, run directly with
`python -m pytest backend/tests/test_kb_phase2_trash_versions.py`.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_kb_phase2")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from database import users_collection  # noqa: E402
from dependencies import get_current_user  # noqa: E402
from routes.kb import kb_articles, kb_navigation, kb_article_versions  # noqa: E402
from routes.review import review_assignments  # noqa: E402

app = server.app
client = TestClient(app)

OWNER = {"email": "owner@trinity.test", "role": "admin", "name": "Owner"}
AGENT = {"email": "agent@trinity.test", "role": "agent", "name": "Agent"}


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
def _clean_state():
    for col in (kb_articles, kb_navigation, kb_article_versions, review_assignments, users_collection):
        col.delete_many({})
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _seed_article(slug, **overrides):
    doc = {
        "slug": slug, "title": slug, "description": "", "content_markdown": "# hi",
        "nav_group_key": "top", "nav_group_label": "Top", "section_key": "sub",
        "section_label": "Sub", "icon": "", "order": 0, "published": True,
        "sidebar_title": "", "keywords": [], "tags": [],
    }
    doc.update(overrides)
    kb_articles.insert_one(dict(doc))
    return doc


def _seed_nav_with_page(slug, group_key="sub"):
    kb_navigation.insert_one({"schema_version": 2, "groups": [
        {"type": "group", "key": "top", "label": "Top", "icon": "", "published": True, "children": [
            {"type": "group", "key": group_key, "label": "Sub", "icon": "", "published": True, "children": [
                {"type": "page", "slug": "sibling-before"},
                {"type": "page", "slug": slug},
                {"type": "page", "slug": "sibling-after"},
            ]},
        ]},
    ]})


# ─────────────────────────── Trash ───────────────────────────

class TestSoftDelete:
    def test_delete_is_owner_gated(self):
        _seed_article("p1")
        _as(AGENT)
        resp = client.delete("/api/kb/admin/articles/p1")
        assert resp.status_code == 403

    def test_soft_delete_keeps_doc_but_flags_it(self):
        _seed_article("p1")
        _seed_nav_with_page("p1")
        _as(OWNER)
        resp = client.delete("/api/kb/admin/articles/p1")
        assert resp.status_code == 200
        doc = kb_articles.find_one({"slug": "p1"})
        assert doc is not None
        assert doc["deleted_at"] is not None
        assert doc["deleted_by"] == OWNER["email"]
        assert doc["deleted_by_name"] == OWNER["name"]
        assert doc["trash_nav"] == {"parent_key": "sub", "index": 1}

    def test_soft_deleted_removed_from_nav_tree(self):
        _seed_article("p1")
        _seed_nav_with_page("p1")
        _as(OWNER)
        client.delete("/api/kb/admin/articles/p1")
        nav = kb_navigation.find_one({}, {"_id": 0})
        sub = nav["groups"][0]["children"][0]
        slugs_left = [c["slug"] for c in sub["children"]]
        assert "p1" not in slugs_left
        assert slugs_left == ["sibling-before", "sibling-after"]

    def test_soft_deleted_excluded_from_listings(self):
        _seed_article("p1")
        _seed_nav_with_page("p1")
        _as(OWNER)
        client.delete("/api/kb/admin/articles/p1")

        # admin list
        resp = client.get("/api/kb/admin/articles")
        assert "p1" not in [a["slug"] for a in resp.json()["articles"]]
        # admin get single
        assert client.get("/api/kb/admin/articles/p1").status_code == 404
        # public list/get/search/sitemap/public-data
        assert "p1" not in [a["slug"] for a in client.get("/api/kb/articles").json()["articles"]]
        assert client.get("/api/kb/articles/p1").status_code == 404
        search_slugs = [r["slug"] for r in client.get("/api/kb/search?q=hi").json()["results"]]
        assert "p1" not in search_slugs
        assert "p1" not in client.get("/api/kb/sitemap.xml").text
        pd = client.get("/api/kb/public-data").json()
        assert "p1" not in [d["slug"] for d in pd["documents"]]

    def test_soft_delete_cascades_unassign_from_review(self):
        _seed_article("p1")
        _seed_article("p2")
        _seed_nav_with_page("p1")
        review_assignments.insert_one({
            "id": "asg-1", "scope_type": "page", "scope_id": "p1", "scope_label": "p1",
            "assignee_email": AGENT["email"], "assigned_by": OWNER["email"], "assigned_by_name": "Owner",
            "status": "in_review", "slugs": ["p1", "p2"], "delegated_from": None, "due_date": None,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
        })
        _as(OWNER)
        client.delete("/api/kb/admin/articles/p1")
        a = review_assignments.find_one({"id": "asg-1"})
        assert a is not None
        assert "p1" not in a["slugs"]
        assert "p2" in a["slugs"]

    def test_soft_delete_cascade_deletes_assignment_when_it_becomes_empty(self):
        _seed_article("p1")
        _seed_nav_with_page("p1")
        review_assignments.insert_one({
            "id": "asg-1", "scope_type": "page", "scope_id": "p1", "scope_label": "p1",
            "assignee_email": AGENT["email"], "assigned_by": OWNER["email"], "assigned_by_name": "Owner",
            "status": "in_review", "slugs": ["p1"], "delegated_from": None, "due_date": None,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
        })
        _as(OWNER)
        client.delete("/api/kb/admin/articles/p1")
        assert review_assignments.find_one({"id": "asg-1"}) is None

    def test_double_delete_404s(self):
        _seed_article("p1")
        _as(OWNER)
        assert client.delete("/api/kb/admin/articles/p1").status_code == 200
        assert client.delete("/api/kb/admin/articles/p1").status_code == 404


class TestTrashListing:
    def test_list_trash_owner_gated(self):
        _as(AGENT)
        assert client.get("/api/kb/admin/trash").status_code == 403

    def test_list_trash_newest_deleted_first(self):
        _seed_article("old", deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
                       deleted_by="x@x.com", deleted_by_name="X")
        _seed_article("new", deleted_at=datetime.now(timezone.utc) - timedelta(days=1),
                       deleted_by="x@x.com", deleted_by_name="X")
        _as(OWNER)
        resp = client.get("/api/kb/admin/trash")
        assert resp.status_code == 200
        slugs = [t["slug"] for t in resp.json()["trash"]]
        assert slugs == ["new", "old"]

    def test_days_left_computed(self):
        _seed_article("p1", deleted_at=datetime.now(timezone.utc) - timedelta(days=10),
                       deleted_by="x@x.com", deleted_by_name="X")
        _as(OWNER)
        item = client.get("/api/kb/admin/trash").json()["trash"][0]
        assert item["days_left"] == 80

    def test_lazy_purge_past_90_days(self):
        _seed_article("stale", deleted_at=datetime.now(timezone.utc) - timedelta(days=91),
                       deleted_by="x@x.com", deleted_by_name="X")
        _seed_article("fresh", deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
                       deleted_by="x@x.com", deleted_by_name="X")
        _as(OWNER)
        resp = client.get("/api/kb/admin/trash")
        slugs = [t["slug"] for t in resp.json()["trash"]]
        assert "stale" not in slugs
        assert "fresh" in slugs
        assert kb_articles.find_one({"slug": "stale"}) is None
        assert kb_articles.find_one({"slug": "fresh"}) is not None


class TestRestore:
    def test_restore_owner_gated(self):
        _seed_article("p1", deleted_at=datetime.now(timezone.utc), deleted_by="x", deleted_by_name="X",
                       trash_nav={"parent_key": "sub", "index": 1})
        _as(AGENT)
        assert client.post("/api/kb/admin/trash/p1/restore").status_code == 403

    def test_restore_puts_page_back_at_recorded_position(self):
        _seed_article("p1")
        _seed_nav_with_page("p1")
        _as(OWNER)
        client.delete("/api/kb/admin/articles/p1")

        resp = client.post("/api/kb/admin/trash/p1/restore")
        assert resp.status_code == 200
        assert resp.json()["fell_back_to_top_level"] is False

        doc = kb_articles.find_one({"slug": "p1"})
        assert doc["deleted_at"] is None
        assert doc["deleted_by"] is None
        assert doc["trash_nav"] is None

        nav = kb_navigation.find_one({}, {"_id": 0})
        sub = nav["groups"][0]["children"][0]
        slugs = [c["slug"] for c in sub["children"]]
        assert slugs == ["sibling-before", "p1", "sibling-after"]

    def test_restore_falls_back_to_top_level_when_parent_group_gone(self):
        _seed_article("p1")
        _seed_nav_with_page("p1")
        _as(OWNER)
        client.delete("/api/kb/admin/articles/p1")

        # Simulate the parent group having been removed/renamed while p1 sat in Trash.
        kb_navigation.update_one({}, {"$set": {"groups": [
            {"type": "group", "key": "top", "label": "Top", "icon": "", "published": True, "children": []},
        ]}})

        resp = client.post("/api/kb/admin/trash/p1/restore")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fell_back_to_top_level"] is True
        assert "note" in body

        nav = kb_navigation.find_one({}, {"_id": 0})
        top_level_slugs = [n.get("slug") for n in nav["groups"] if n.get("type") == "page"]
        assert "p1" in top_level_slugs

    def test_restore_nonexistent_trash_404s(self):
        _seed_article("p1")  # never deleted
        _as(OWNER)
        assert client.post("/api/kb/admin/trash/p1/restore").status_code == 404
        assert client.post("/api/kb/admin/trash/no-such-slug/restore").status_code == 404


class TestPermanentDelete:
    def test_purge_owner_gated(self):
        _seed_article("p1", deleted_at=datetime.now(timezone.utc), deleted_by="x", deleted_by_name="X")
        _as(AGENT)
        assert client.delete("/api/kb/admin/trash/p1").status_code == 403

    def test_purge_removes_doc_permanently(self):
        _seed_article("p1", deleted_at=datetime.now(timezone.utc), deleted_by="x", deleted_by_name="X")
        _as(OWNER)
        resp = client.delete("/api/kb/admin/trash/p1")
        assert resp.status_code == 200
        assert kb_articles.find_one({"slug": "p1"}) is None

    def test_purge_refuses_a_non_trashed_article(self):
        _seed_article("p1")  # live, not trashed
        _as(OWNER)
        resp = client.delete("/api/kb/admin/trash/p1")
        assert resp.status_code == 404
        assert kb_articles.find_one({"slug": "p1"}) is not None


# ─────────────────────────── Version history ───────────────────────────

class TestVersionCreateAndList:
    def test_create_version_owner_gated(self):
        _seed_article("p1")
        _as(AGENT)
        assert client.post("/api/kb/admin/articles/p1/versions", json={}).status_code == 403

    def test_create_version_snapshot_matches_article(self):
        _seed_article("p1", title="Original Title", content_markdown="original body")
        _as(OWNER)
        resp = client.post("/api/kb/admin/articles/p1/versions", json={"label": "v1"})
        assert resp.status_code == 200
        version = resp.json()["version"]
        assert version["article_slug"] == "p1"
        assert version["label"] == "v1"
        assert version["snapshot"]["title"] == "Original Title"
        assert version["snapshot"]["content_markdown"] == "original body"
        assert version["created_by"] == OWNER["email"]

    def test_create_version_default_label_when_none_given(self):
        _seed_article("p1")
        _as(OWNER)
        resp = client.post("/api/kb/admin/articles/p1/versions", json={})
        assert resp.status_code == 200
        assert resp.json()["version"]["label"]  # non-empty default

    def test_list_versions_newest_first_and_no_snapshot_payload(self):
        _seed_article("p1")
        _as(OWNER)
        client.post("/api/kb/admin/articles/p1/versions", json={"label": "first"})
        client.post("/api/kb/admin/articles/p1/versions", json={"label": "second"})
        resp = client.get("/api/kb/admin/articles/p1/versions")
        assert resp.status_code == 200
        versions = resp.json()["versions"]
        assert [v["label"] for v in versions] == ["second", "first"]
        assert "snapshot" not in versions[0]

    def test_update_article_does_not_auto_create_a_version(self):
        # Deviation from the task brief, confirmed against help-doc-v3's own
        # server.py: version snapshots there are an explicit, user-named
        # action (POST .../versions), never automatic on every save. Trinity
        # mirrors that exactly rather than diverging from the real reference.
        _seed_article("p1")
        _as(OWNER)
        client.put("/api/kb/admin/articles/p1", json={"title": "Edited"})
        assert kb_article_versions.count_documents({"article_slug": "p1"}) == 0


class TestVersionRestore:
    def test_restore_owner_gated(self):
        _seed_article("p1")
        _as(OWNER)
        vid = client.post("/api/kb/admin/articles/p1/versions", json={"label": "v1"}).json()["version"]["id"]
        _as(AGENT)
        assert client.post(f"/api/kb/admin/articles/p1/versions/{vid}/restore").status_code == 403

    def test_restore_creates_auto_backup_and_overwrites_content(self):
        _seed_article("p1", title="V1 Title", content_markdown="v1 body",
                       nav_group_key="top", section_key="sub", order=7, published=True)
        _as(OWNER)
        v1 = client.post("/api/kb/admin/articles/p1/versions", json={"label": "v1"}).json()["version"]

        # Change content, then restore back to v1.
        client.put("/api/kb/admin/articles/p1", json={"title": "V2 Title", "content_markdown": "v2 body"})
        resp = client.post(f"/api/kb/admin/articles/p1/versions/{v1['id']}/restore")
        assert resp.status_code == 200
        assert "v1" in resp.json()["message"]

        article = kb_articles.find_one({"slug": "p1"}, {"_id": 0})
        assert article["title"] == "V1 Title"
        assert article["content_markdown"] == "v1 body"
        # Structural fields must NOT be touched by a content restore.
        assert article["nav_group_key"] == "top"
        assert article["section_key"] == "sub"
        assert article["order"] == 7

        versions = client.get("/api/kb/admin/articles/p1/versions").json()["versions"]
        labels = [v["label"] for v in versions]
        assert any(l.startswith("Auto-backup before restore to 'v1'") for l in labels)
        # Original v1 + the new auto-backup = 2 versions.
        assert len(versions) == 2

    def test_restore_nonexistent_version_404s(self):
        _seed_article("p1")
        _as(OWNER)
        assert client.post("/api/kb/admin/articles/p1/versions/does-not-exist/restore").status_code == 404


class TestVersionDelete:
    def test_delete_version_owner_gated(self):
        _seed_article("p1")
        _as(OWNER)
        vid = client.post("/api/kb/admin/articles/p1/versions", json={"label": "v1"}).json()["version"]["id"]
        _as(AGENT)
        assert client.delete(f"/api/kb/admin/articles/p1/versions/{vid}").status_code == 403

    def test_delete_removes_only_that_version(self):
        _seed_article("p1")
        _as(OWNER)
        v1 = client.post("/api/kb/admin/articles/p1/versions", json={"label": "v1"}).json()["version"]
        v2 = client.post("/api/kb/admin/articles/p1/versions", json={"label": "v2"}).json()["version"]

        resp = client.delete(f"/api/kb/admin/articles/p1/versions/{v1['id']}")
        assert resp.status_code == 200
        remaining = client.get("/api/kb/admin/articles/p1/versions").json()["versions"]
        assert [v["id"] for v in remaining] == [v2["id"]]

    def test_delete_nonexistent_version_404s(self):
        _seed_article("p1")
        _as(OWNER)
        assert client.delete("/api/kb/admin/articles/p1/versions/nope").status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
