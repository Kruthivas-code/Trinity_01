"""
Phase 4 tests (help-doc-v3 feature port): editor UX -- stock image search
proxy, and guarded slug-change (redirects + internal-link rewrite + owner
gating).

Same mongomock + FastAPI TestClient harness as test_review_phase1.py /
test_kb_phase2_trash_versions.py / test_assistant_phase3.py -- standalone
module, run directly with
`python -m pytest backend/tests/test_kb_phase4_editor_ux.py`.

No new backend endpoint was needed for the Configurations Panel item (logo/
favicon/OG-image upload reuses the existing POST /api/kb/admin/images
endpoint entirely on the frontend side -- see UnifiedSettings.jsx's
UploadableUrlField) -- so there's nothing new to test there beyond what
test_kb_docs_api.py / test_kb_image_upload.py already cover for those
endpoints individually.
"""
import os
import sys
from unittest.mock import patch, MagicMock

import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_kb_phase4")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from database import users_collection  # noqa: E402
from dependencies import get_current_user  # noqa: E402
from routes.kb import kb_articles, kb_navigation, kb_redirects  # noqa: E402

app = server.app
client = TestClient(app)

OWNER = {"email": "owner@trinity.test", "role": "admin", "name": "Owner"}
AGENT = {"email": "agent@trinity.test", "role": "agent", "name": "Agent"}


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _as_anonymous():
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _clean_state():
    for col in (kb_articles, kb_navigation, kb_redirects, users_collection):
        col.delete_many({})
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _seed_article(slug, **overrides):
    doc = {
        "slug": slug, "title": slug.replace("-", " ").title(), "description": "",
        "content_markdown": "# hi", "nav_group_key": "top", "nav_group_label": "Top",
        "section_key": "sub", "section_label": "Sub", "icon": "", "order": 0,
        "published": True, "sidebar_title": "", "keywords": [], "tags": [],
    }
    doc.update(overrides)
    kb_articles.insert_one(dict(doc))
    return doc


def _seed_nav_with_page(slug, group_key="sub"):
    kb_navigation.insert_one({"schema_version": 2, "groups": [
        {"type": "group", "key": "top", "label": "Top", "icon": "", "published": True, "children": [
            {"type": "group", "key": group_key, "label": "Sub", "icon": "", "published": True, "children": [
                {"type": "page", "slug": slug},
            ]},
        ]},
    ]})


# ─────────────────────── Stock image search proxy ───────────────────────

class TestStockImageSearch:
    def test_requires_signin(self):
        _as_anonymous()
        resp = client.get("/api/kb/admin/images/search-stock?query=rocket")
        assert resp.status_code == 401

    def test_empty_query_returns_empty_without_calling_unsplash(self):
        _as(AGENT)
        with patch("routes.kb.requests.get") as mock_get:
            resp = client.get("/api/kb/admin/images/search-stock?query=")
            assert resp.status_code == 200
            assert resp.json()["images"] == []
            mock_get.assert_not_called()

    def test_successful_search_maps_unsplash_shape(self):
        _as(AGENT)  # any signed-in user -- same tier as POST /admin/images
        fake_resp = MagicMock()
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json.return_value = {
            "total": 1, "total_pages": 1,
            "results": [{
                "id": "abc123",
                "urls": {"regular": "https://images.unsplash.com/abc-regular",
                         "thumb": "https://images.unsplash.com/abc-thumb",
                         "small": "https://images.unsplash.com/abc-small"},
                "alt_description": "a rocket launching",
                "user": {"name": "Jane Doe", "links": {"html": "https://unsplash.com/@jane"}},
            }],
        }
        with patch("routes.kb.requests.get", return_value=fake_resp) as mock_get:
            resp = client.get("/api/kb/admin/images/search-stock?query=rocket&page=1&per_page=12")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["images"]) == 1
        img = data["images"][0]
        assert img["id"] == "abc123"
        assert img["url"] == "https://images.unsplash.com/abc-regular"
        assert img["alt"] == "a rocket launching"
        assert img["author"] == "Jane Doe"
        assert img["source"] == "unsplash"
        # UNSPLASH_ACCESS_KEY defaults to "demo" when unset -- confirm the
        # proxy actually sent that as the Client-ID.
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Client-ID demo"
        assert kwargs["params"]["query"] == "rocket"

    def test_unsplash_failure_returns_empty_with_error_not_500(self):
        _as(AGENT)
        with patch("routes.kb.requests.get", side_effect=ConnectionError("boom")):
            resp = client.get("/api/kb/admin/images/search-stock?query=rocket")
        assert resp.status_code == 200
        data = resp.json()
        assert data["images"] == []
        assert "error" in data


# ─────────────────────── Guarded slug change ───────────────────────

class TestSlugChangeGating:
    def test_content_only_edit_stays_open_to_any_signed_in_user(self):
        """Sanity check that Phase 4 didn't accidentally tighten the
        Phase 1 content-edit gate: a PUT with no slug change is still open
        to a non-owner."""
        _seed_article("getting-started")
        _as(AGENT)
        resp = client.put("/api/kb/admin/articles/getting-started", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_slug_change_by_non_owner_is_403(self):
        _seed_article("getting-started")
        _as(AGENT)
        resp = client.put("/api/kb/admin/articles/getting-started", json={"slug": "quickstart"})
        assert resp.status_code == 403
        # nothing changed
        assert kb_articles.find_one({"slug": "getting-started"}) is not None
        assert kb_articles.find_one({"slug": "quickstart"}) is None

    def test_slug_change_by_owner_succeeds(self):
        _seed_article("getting-started")
        _as(OWNER)
        resp = client.put("/api/kb/admin/articles/getting-started", json={"slug": "quickstart"})
        assert resp.status_code == 200
        assert resp.json()["slug"] == "quickstart"
        assert kb_articles.find_one({"slug": "getting-started"}) is None
        assert kb_articles.find_one({"slug": "quickstart"}) is not None

    def test_invalid_new_slug_is_rejected(self):
        _seed_article("getting-started")
        _as(OWNER)
        resp = client.put("/api/kb/admin/articles/getting-started", json={"slug": "Not A Valid Slug!"})
        assert resp.status_code == 400

    def test_conflicting_new_slug_is_rejected(self):
        _seed_article("getting-started")
        _seed_article("quickstart")
        _as(OWNER)
        resp = client.put("/api/kb/admin/articles/getting-started", json={"slug": "quickstart"})
        assert resp.status_code == 409


class TestSlugChangeRedirectAndLinkRewrite:
    def test_redirect_created_and_resolves_via_public_articles_endpoint(self):
        _seed_article("getting-started")
        _as(OWNER)
        resp = client.put("/api/kb/admin/articles/getting-started", json={"slug": "quickstart"})
        assert resp.status_code == 200
        assert resp.json()["slug_change"] == {
            "old_slug": "getting-started", "new_slug": "quickstart",
            "pages_touched": 0, "links_updated": 0,
        }
        redirect = kb_redirects.find_one({"old_slug": "getting-started"}, {"_id": 0})
        assert redirect["new_slug"] == "quickstart"

        # The old slug now resolves via the public single-article endpoint's
        # redirect fallback instead of a bare 404.
        resp2 = client.get("/api/kb/articles/getting-started")
        assert resp2.status_code == 200
        assert resp2.json() == {"redirect_to": "quickstart"}

    def test_redirect_appears_in_public_data_only_when_target_is_live(self):
        _seed_article("getting-started", published=True)
        _as(OWNER)
        client.put("/api/kb/admin/articles/getting-started", json={"slug": "quickstart"})

        data = client.get("/api/kb/public-data").json()
        assert {"from_slug": "getting-started", "to_slug": "quickstart"} in data["redirects"]

        # Unpublish the target -- the redirect should no longer resolve to a
        # live article, so it drops out of public-data (nothing useful to
        # send a visitor to).
        kb_articles.update_one({"slug": "quickstart"}, {"$set": {"published": False}})
        data2 = client.get("/api/kb/public-data").json()
        assert data2["redirects"] == []

    def test_internal_links_rewritten_across_other_articles(self):
        _seed_article(
            "getting-started",
            content_markdown="# Start\n\nSee the [full guide](/docs/getting-started) for details.",
            published=True,
        )
        _seed_article(
            "overview",
            content_markdown="Read [getting started](/docs/getting-started#setup) first.\n\n"
                              "<Card title=\"Start\" href=\"/docs/getting-started\">Go</Card>",
            published_content_markdown="Read [getting started](/docs/getting-started) first.",
            published=True,
        )
        # A slug that merely starts with the same prefix must NOT be touched
        # (boundary check).
        _seed_article(
            "getting-started-advanced",
            content_markdown="See [advanced](/docs/getting-started-advanced) too.",
            published=True,
        )
        _as(OWNER)
        resp = client.put("/api/kb/admin/articles/getting-started", json={"slug": "quickstart"})
        assert resp.status_code == 200
        sc = resp.json()["slug_change"]
        assert sc["pages_touched"] == 1  # only "overview" carries the link
        assert sc["links_updated"] == 3  # 2 in content_markdown + 1 in published_content_markdown

        overview = kb_articles.find_one({"slug": "overview"}, {"_id": 0})
        assert "/docs/getting-started" not in overview["content_markdown"]
        assert "/docs/quickstart#setup" in overview["content_markdown"]
        assert 'href="/docs/quickstart"' in overview["content_markdown"]
        assert overview["published_content_markdown"] == "Read [getting started](/docs/quickstart) first."

        # Boundary case untouched.
        advanced = kb_articles.find_one({"slug": "getting-started-advanced"}, {"_id": 0})
        assert "/docs/getting-started-advanced)" in advanced["content_markdown"]

        # The renamed article's OWN content (which also links to itself) is
        # excluded from the "other articles" rewrite scan, but that's fine --
        # it's not a broken link, just self-referential text a human can fix.

    def test_slug_preview_dry_run_does_not_mutate(self):
        _seed_article("getting-started", content_markdown="See [x](/docs/getting-started).")
        _seed_article("overview", content_markdown="See [x](/docs/getting-started) and [y](/docs/getting-started).")
        _as(OWNER)
        resp = client.get("/api/kb/admin/articles/getting-started/slug-preview?new_slug=quickstart")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {
            "old_slug": "getting-started", "new_slug": "quickstart",
            "slug_valid": True, "slug_available": True,
            "pages_count": 1, "links_count": 2,
        }
        # Nothing actually changed.
        assert kb_articles.find_one({"slug": "getting-started"}) is not None
        assert kb_redirects.count_documents({}) == 0

    def test_slug_preview_requires_owner(self):
        _seed_article("getting-started")
        _as(AGENT)
        resp = client.get("/api/kb/admin/articles/getting-started/slug-preview?new_slug=quickstart")
        assert resp.status_code == 403

    def test_slug_preview_flags_unavailable_slug(self):
        _seed_article("getting-started")
        _seed_article("quickstart")
        _as(OWNER)
        resp = client.get("/api/kb/admin/articles/getting-started/slug-preview?new_slug=quickstart")
        assert resp.json()["slug_available"] is False

    def test_nav_tree_repointed_on_slug_change(self):
        _seed_article("getting-started")
        _seed_nav_with_page("getting-started")
        _as(OWNER)
        client.put("/api/kb/admin/articles/getting-started", json={"slug": "quickstart"})
        nav = kb_navigation.find_one({}, {"_id": 0})
        slugs = [p["slug"] for g in nav["groups"] for sg in g["children"] for p in sg["children"]]
        assert slugs == ["quickstart"]

    def test_rename_chain_repoints_earlier_redirect(self):
        """a -> b -> c: renaming b to c should leave a redirect a->c that
        resolves in one hop, not a broken a->b chain."""
        _seed_article("page-a")
        _as(OWNER)
        client.put("/api/kb/admin/articles/page-a", json={"slug": "page-b"})
        client.put("/api/kb/admin/articles/page-b", json={"slug": "page-c"})

        assert kb_redirects.find_one({"old_slug": "page-a"}, {"_id": 0})["new_slug"] == "page-c"
        assert kb_redirects.find_one({"old_slug": "page-b"}, {"_id": 0})["new_slug"] == "page-c"

        resp = client.get("/api/kb/articles/page-a")
        assert resp.json() == {"redirect_to": "page-c"}

    def test_rename_back_to_original_slug_drops_self_loop_redirect(self):
        _seed_article("page-a")
        _as(OWNER)
        client.put("/api/kb/admin/articles/page-a", json={"slug": "page-b"})
        client.put("/api/kb/admin/articles/page-b", json={"slug": "page-a"})
        # a->a would be a no-op self-loop -- must not exist.
        assert kb_redirects.find_one({"old_slug": "page-a"}) is None

    def test_unresolvable_slug_still_404s(self):
        resp = client.get("/api/kb/articles/does-not-exist")
        assert resp.status_code == 404
