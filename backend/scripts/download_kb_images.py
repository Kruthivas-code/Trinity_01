"""
Download all external images from KB articles and store locally.
Updates article content to reference local paths.
"""
import os
import re
import hashlib
import requests
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = "test_database"
SUPABASE_URL = "https://izkzvlcxzbhawofhormd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6a3p2bGN4emJoYXdvZmhvcm1kIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODY1MDgyMiwiZXhwIjoyMDg0MjI2ODIyfQ.KRDDfwaHJXQxaxQSO1CoWLEDwaxpA6v9AOO95FYClSk"

LOCAL_DIR = "/app/frontend/public/kb-images"
URL_PREFIX = "/kb-images"

os.makedirs(LOCAL_DIR, exist_ok=True)

def get_extension(url):
    """Get file extension from URL."""
    path = url.split("?")[0]
    ext = os.path.splitext(path)[1].lower()
    if ext in [".avif", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]:
        return ext
    return ".png"

def download_image(url):
    """Download image and return local filename."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    ext = get_extension(url)
    filename = f"{url_hash}{ext}"
    filepath = os.path.join(LOCAL_DIR, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"  Already exists: {filename}")
        return filename

    headers = {}
    if "supabase.co" in url:
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
        headers["apikey"] = SUPABASE_KEY

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(resp.content)
            print(f"  Downloaded: {filename} ({len(resp.content)} bytes)")
            return filename
        else:
            # Try without auth for public buckets
            resp2 = requests.get(url, timeout=30)
            if resp2.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp2.content)
                print(f"  Downloaded (public): {filename} ({len(resp2.content)} bytes)")
                return filename
            print(f"  FAILED: {url} -> {resp.status_code}, {resp2.status_code}")
            return None
    except Exception as e:
        print(f"  ERROR: {url} -> {e}")
        return None

def main():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    kb_articles = db["kb_articles"]

    articles = list(kb_articles.find({}, {"_id": 0, "slug": 1, "content_markdown": 1}))
    print(f"Processing {len(articles)} articles...")

    url_to_local = {}
    updated = 0

    for a in articles:
        content = a.get("content_markdown", "")
        slug = a["slug"]

        # Find all external URLs
        urls = set()
        for m in re.finditer(r'!\[([^\]]*)\]\((https?://[^)]+)\)', content):
            urls.add(m.group(2))
        for m in re.finditer(r'src="(https?://[^"]+)"', content):
            url = m.group(1)
            if "youtube" not in url and "loom" not in url:
                urls.add(url)

        if not urls:
            continue

        print(f"\n{slug}: {len(urls)} external URLs")
        new_content = content

        for url in urls:
            if url in url_to_local:
                filename = url_to_local[url]
            else:
                filename = download_image(url)
                url_to_local[url] = filename

            if filename:
                local_path = f"{URL_PREFIX}/{filename}"
                new_content = new_content.replace(url, local_path)

        if new_content != content:
            kb_articles.update_one(
                {"slug": slug},
                {"$set": {"content_markdown": new_content}}
            )
            updated += 1
            print(f"  Updated article content")

    # Also handle URLs with query params that dedupe to same base
    # e.g., image.jpg and image.jpg?fit=max&... should map to same local file
    print(f"\nDone! Updated {updated} articles, downloaded {len(url_to_local)} images")
    print(f"Local images stored in: {LOCAL_DIR}")

    client.close()

if __name__ == "__main__":
    main()
