"""
Re-import KB content from help.emergent.sh API.
Replaces scraped content with properly formatted markdown + MDX components.
"""
import os
import json
import requests
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "trinity")
SOURCE_API = "https://help.emergent.sh/api/public/default-project"

def main():
    # Fetch from reference API
    print("Fetching from help.emergent.sh API...")
    resp = requests.get(SOURCE_API, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    documents = data.get("documents", [])
    config = data.get("config", {})
    tabs = config.get("navigation", {}).get("tabs", [])

    print(f"  Got {len(documents)} documents, {len(tabs)} tabs")

    # Build slug -> document map
    doc_map = {}
    for doc in documents:
        slug = doc.get("slug", "")
        if slug:
            doc_map[slug] = doc

    # Build slug -> icon map from navigation
    icon_map = {}
    for tab in tabs:
        for group in tab.get("groups", []):
            for page in group.get("pages", []):
                if isinstance(page, dict):
                    icon_map[page.get("page", "")] = page.get("icon", "")

    # Build nav_groups structure for our DB
    nav_groups = []
    for tab in tabs:
        sections = []
        for group in tab.get("groups", []):
            section_key = group["group"].lower().replace(" ", "-").replace("'", "")
            pages = group.get("pages", [])
            page_slugs = [p.get("page") if isinstance(p, dict) else p for p in pages]
            sections.append({
                "key": section_key,
                "label": group["group"],
                "articles": page_slugs,
            })
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

    # Clear existing articles
    old_count = kb_articles.count_documents({})
    print(f"  Clearing {old_count} existing articles...")
    kb_articles.delete_many({})

    # Insert new articles with proper content
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
                # Use document title if available
                doc_title = doc.get("title", title)

                article = {
                    "slug": slug,
                    "title": doc_title,
                    "content_markdown": content,
                    "nav_group_key": tab["id"],
                    "nav_group_label": tab.get("label", tab["id"]),
                    "section_key": section_key,
                    "section_label": group["group"],
                    "icon": icon,
                    "order": order,
                    "published": True,
                    "source_url": f"https://help.emergent.sh/{slug}",
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
    welcome = kb_articles.find_one({"slug": "welcome"}, {"_id": 0, "content_markdown": 1})
    if welcome:
        content = welcome.get("content_markdown", "")
        has_blockquote = content.startswith(">")
        has_double_newlines = "\n\n" in content
        has_mdx = "<Card" in content or "<iframe" in content or "<Columns" in content
        print(f"\n  Verification:")
        print(f"    Total articles in DB: {total}")
        print(f"    Welcome has blockquote: {has_blockquote}")
        print(f"    Welcome has double newlines: {has_double_newlines}")
        print(f"    Welcome has MDX components: {has_mdx}")
        print(f"    Welcome content preview: {content[:200]}...")

    client.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
