"""
Re-import KB content from help.emergent.sh API.
Replaces all existing articles with fresh content including full metadata.

Usage: cd /app/backend && python scripts/reimport_kb.py
"""
import os
import sys
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "trinity")
SOURCE_API = "https://help.emergent.sh/api/public/default-project"


def _parse_api_date(val):
    """Parse a date string from the API, falling back to now()."""
    if not val:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def _generate_description(content: str) -> str:
    """Generate a short description from markdown content."""
    text = content.replace("#", "").replace(">", "").replace("*", "").strip()
    lines = [l.strip() for l in text.split("\n") if l.strip() and not l.strip().startswith("<")]
    if not lines:
        return ""
    return (lines[0][:160] + "...") if len(lines[0]) > 160 else lines[0]


def main():
    if not MONGO_URL:
        print("ERROR: MONGO_URL not set")
        sys.exit(1)

    print("Fetching from help.emergent.sh API...")
    resp = requests.get(SOURCE_API, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    documents = data.get("documents", [])
    config = data.get("config", {})
    tabs = config.get("navigation", {}).get("tabs", [])

    print(f"  Got {len(documents)} documents, {len(tabs)} tabs")

    doc_map = {doc["slug"]: doc for doc in documents if doc.get("slug")}

    # Build nav_groups
    nav_groups = []
    for tab in tabs:
        sections = []
        for group in tab.get("groups", []):
            section_key = group["group"].lower().replace(" ", "-").replace("'", "")
            pages = group.get("pages", [])
            page_slugs = [p.get("page") if isinstance(p, dict) else p for p in pages]
            sections.append({"key": section_key, "label": group["group"], "articles": page_slugs})
        nav_groups.append({
            "key": tab["id"],
            "label": tab.get("label", tab["id"]),
            "icon": tab.get("icon", "file-text"),
            "sections": sections,
        })

    # Connect to MongoDB
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    kb_articles = db["kb_articles"]
    kb_navigation = db["kb_navigation"]

    old_count = kb_articles.count_documents({})
    print(f"  Clearing {old_count} existing articles...")
    kb_articles.delete_many({})

    # Insert articles with full metadata
    order = 0
    inserted = 0
    for tab in tabs:
        for group in tab.get("groups", []):
            section_key = group["group"].lower().replace(" ", "-").replace("'", "")
            for page in group.get("pages", []):
                slug = page.get("page") if isinstance(page, dict) else page
                title = page.get("title", slug) if isinstance(page, dict) else slug
                icon = page.get("icon", "") if isinstance(page, dict) else ""

                doc = doc_map.get(slug)
                if not doc:
                    print(f"  WARNING: No content for slug '{slug}', skipping")
                    continue

                content = doc.get("content", "")
                doc_title = doc.get("title", title)
                doc_icon = doc.get("icon", "") or icon

                article = {
                    "slug": slug,
                    "title": doc_title,
                    "description": _generate_description(content),
                    "content_markdown": content,
                    "nav_group_key": tab["id"],
                    "nav_group_label": tab.get("label", tab["id"]),
                    "section_key": section_key,
                    "section_label": group["group"],
                    "icon": doc_icon,
                    "order": order,
                    "published": True,
                    "source_url": f"https://help.emergent.sh/{slug}",
                    "created_at": _parse_api_date(doc.get("created_at")),
                    "updated_at": _parse_api_date(doc.get("updated_at")),
                }
                kb_articles.insert_one(article)
                inserted += 1
                order += 1

    print(f"  Inserted {inserted} articles")

    # Update navigation
    kb_navigation.delete_many({})
    kb_navigation.insert_one({"nav_groups": nav_groups})
    print(f"  Updated navigation with {len(nav_groups)} groups")

    # Verify
    total = kb_articles.count_documents({})
    sample = kb_articles.find_one({"slug": "welcome"}, {"_id": 0, "title": 1, "description": 1, "created_at": 1, "updated_at": 1})
    if sample:
        print(f"\n  Verification:")
        print(f"    Total articles in DB: {total}")
        print(f"    Sample — title: {sample.get('title')}")
        print(f"    Sample — description: {sample.get('description', '')[:80]}")
        print(f"    Sample — created_at: {sample.get('created_at')}")
        print(f"    Sample — updated_at: {sample.get('updated_at')}")

    client.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
