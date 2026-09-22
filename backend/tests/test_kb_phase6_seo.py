"""
Phase 6 tests (help-doc-v3 feature port): SEO routes -- /api/kb/robots.txt,
/api/kb/llms.txt, /api/kb/llms-full.txt, and an audit of the existing
/api/kb/sitemap.xml (published-only, already covered by
test_kb_phase2_trash_versions.py's own sitemap assertion; re-verified here
alongside the new routes for a single Phase 6 pass).

Same mongomock + FastAPI TestClient harness as every prior phase's test
module -- standalone, run directly with
`python -m pytest backend/tests/test_kb_phase6_seo.py`.

No sitemap_index.xml: help-doc-v3's own _sitemap_index_body() wraps exactly
one <sitemap> entry pointing at its single sitemap.xml -- it doesn't shard
anything (that only matters past ~50k URLs), it's a bare alias. Trinity's KB
corpus is nowhere near that scale, so a second index file that always points
at the one real sitemap would be pure ceremony; robots.txt below links
straight to /api/kb/sitemap.xml instead. See kb.py's Phase 6 section for the
same note.
"""
import os
import sys

import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_kb_phase6")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from datetime import datetime, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from routes.kb import kb_articles, kb_navigation  # noqa: E402

app = server.app
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_state():
    for col in (kb_articles, kb_navigation):
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


def _seed_nav(pages_by_group):
    """pages_by_group: {(top_key, top_label, sub_key, sub_label): [slug, ...]}"""
    top_index = {}
    groups = []
    for (top_key, top_label, sub_key, sub_label), slugs in pages_by_group.items():
        if top_key not in top_index:
            top_node = {"type": "group", "key": top_key, "label": top_label,
                        "icon": "", "published": True, "children": []}
            top_index[top_key] = top_node
            groups.append(top_node)
        sub_node = {"type": "group", "key": sub_key, "label": sub_label,
                    "icon": "", "published": True, "children": [
                        {"type": "page", "slug": s} for s in slugs
                    ]}
        top_index[top_key]["children"].append(sub_node)
    kb_navigation.insert_one({"schema_version": 2, "groups": groups})


# ─────────────────────────── robots.txt ───────────────────────────

class TestRobotsTxt:
    def test_returns_plaintext_directives(self):
        resp = client.get("/api/kb/robots.txt")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        body = resp.text
        assert "User-agent: *" in body
        assert "Allow: /" in body
        assert "Disallow: /admin" in body

    def test_lists_ai_bots_explicitly(self):
        body = client.get("/api/kb/robots.txt").text
        for bot in ["GPTBot", "ClaudeBot", "anthropic-ai", "PerplexityBot",
                    "Google-Extended", "CCBot", "Bytespider"]:
            assert f"User-agent: {bot}" in body

    def test_links_to_sitemap_and_llms_txt(self):
        body = client.get("/api/kb/robots.txt").text
        assert "Sitemap: " in body and "/api/kb/sitemap.xml" in body
        assert "/api/kb/llms.txt" in body
        assert "/api/kb/llms-full.txt" in body


# ─────────────────────────── llms.txt ───────────────────────────

class TestLlmsTxt:
    def test_includes_only_published_articles(self):
        _seed_article("published-page", title="Published Page", description="A published page.")
        _seed_article("draft-page", title="Draft Page", published=False)
        _seed_nav({
            ("top", "Top", "sub", "Sub"): ["published-page", "draft-page"],
        })
        body = client.get("/api/kb/llms.txt").text
        assert "Published Page" in body
        assert "/docs/published-page" in body
        assert "Draft Page" not in body
        assert "/docs/draft-page" not in body

    def test_excludes_trashed_article(self):
        _seed_article("live-page", title="Live Page")
        _seed_article("trashed-page", title="Trashed Page",
                       deleted_at=datetime.now(timezone.utc))
        _seed_nav({
            ("top", "Top", "sub", "Sub"): ["live-page", "trashed-page"],
        })
        body = client.get("/api/kb/llms.txt").text
        assert "Live Page" in body
        assert "Trashed Page" not in body
        assert "/docs/trashed-page" not in body

    def test_groups_by_nav_section(self):
        _seed_article("a1", title="Alpha One")
        _seed_article("b1", title="Beta One")
        _seed_nav({
            ("guides", "Guides", "getting-started", "Getting Started"): ["a1"],
            ("reference", "Reference", "api", "API"): ["b1"],
        })
        body = client.get("/api/kb/llms.txt").text
        assert "## Guides" in body
        assert "## Reference" in body
        # Alpha One appears after the Guides heading, before Reference's.
        assert body.index("## Guides") < body.index("Alpha One") < body.index("## Reference")
        assert body.index("## Reference") < body.index("Beta One")

    def test_includes_one_line_description_not_full_content(self):
        _seed_article("d1", title="Doc One", description="Short summary.",
                       content_markdown="# Doc One\n\nA very long body of content.")
        _seed_nav({("top", "Top", "sub", "Sub"): ["d1"]})
        body = client.get("/api/kb/llms.txt").text
        assert "Short summary." in body
        assert "A very long body of content." not in body

    def test_no_articles_still_returns_valid_header(self):
        resp = client.get("/api/kb/llms.txt")
        assert resp.status_code == 200
        assert resp.text.startswith("# ")


# ─────────────────────────── llms-full.txt ───────────────────────────

class TestLlmsFullTxt:
    def test_includes_full_content(self):
        _seed_article("f1", title="Full One", description="short",
                       content_markdown="# Heading\n\nFull body text goes here.")
        _seed_nav({("top", "Top", "sub", "Sub"): ["f1"]})
        body = client.get("/api/kb/llms-full.txt").text
        assert "Full One" in body
        assert "Full body text goes here." in body
        assert "/docs/f1" in body

    def test_uses_published_content_over_draft(self):
        _seed_article(
            "f2", title="Draft Title", published_title="Published Title",
            content_markdown="draft body", published_content_markdown="PUBLISHED BODY",
        )
        _seed_nav({("top", "Top", "sub", "Sub"): ["f2"]})
        body = client.get("/api/kb/llms-full.txt").text
        assert "Published Title" in body
        assert "PUBLISHED BODY" in body
        assert "draft body" not in body

    def test_excludes_unpublished_and_trashed(self):
        _seed_article("live", title="Live Doc", content_markdown="live content")
        _seed_article("draft", title="Draft Doc", published=False, content_markdown="draft content")
        _seed_article("trashed", title="Trashed Doc",
                       deleted_at=datetime.now(timezone.utc), content_markdown="trashed content")
        _seed_nav({("top", "Top", "sub", "Sub"): ["live", "draft", "trashed"]})
        body = client.get("/api/kb/llms-full.txt").text
        assert "live content" in body
        assert "draft content" not in body
        assert "trashed content" not in body


# ─────────────────────────── sitemap.xml audit ───────────────────────────

class TestSitemapAudit:
    def test_sitemap_excludes_unpublished_and_trashed(self):
        _seed_article("pub", title="Pub")
        _seed_article("draft", title="Draft", published=False)
        _seed_article("trashed", title="Trashed", deleted_at=datetime.now(timezone.utc))
        body = client.get("/api/kb/sitemap.xml").text
        assert "/docs/pub" in body
        assert "/docs/draft" not in body
        assert "/docs/trashed" not in body

    def test_sitemap_is_valid_xml(self):
        _seed_article("pub", title="Pub")
        resp = client.get("/api/kb/sitemap.xml")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/xml")
        assert resp.text.startswith("<?xml")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
