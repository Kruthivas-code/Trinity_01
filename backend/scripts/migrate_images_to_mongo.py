"""
Migrate KB images from frontend/public/kb-images/ into MongoDB collection,
then update all article content URLs from /kb-images/ to /api/kb/images/.
"""
import os
import mimetypes
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = "test_database"
IMAGE_DIR = "/app/frontend/public/kb-images"

def main():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    kb_image_files = db["kb_image_files"]
    kb_articles = db["kb_articles"]

    # Clear existing
    kb_image_files.delete_many({})

    # Insert all images from disk
    files = [f for f in os.listdir(IMAGE_DIR) if os.path.isfile(os.path.join(IMAGE_DIR, f))]
    print(f"Migrating {len(files)} images to MongoDB...")

    for filename in files:
        filepath = os.path.join(IMAGE_DIR, filename)
        mime, _ = mimetypes.guess_type(filepath)
        if not mime:
            ext = os.path.splitext(filename)[1].lower()
            mime = {"avif": "image/avif", ".png": "image/png", ".jpg": "image/jpeg",
                    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}.get(ext, "application/octet-stream")

        with open(filepath, "rb") as f:
            data = f.read()

        kb_image_files.insert_one({
            "filename": filename,
            "content_type": mime,
            "data": data,
            "size": len(data),
        })
        print(f"  {filename}: {len(data)} bytes ({mime})")

    # Update article content: /kb-images/ -> /api/kb/images/
    articles = list(kb_articles.find({"content_markdown": {"$regex": "/kb-images/"}}, {"_id": 1, "slug": 1, "content_markdown": 1}))
    print(f"\nUpdating {len(articles)} articles...")
    for a in articles:
        new_content = a["content_markdown"].replace("/kb-images/", "/api/kb/images/")
        kb_articles.update_one({"_id": a["_id"]}, {"$set": {"content_markdown": new_content}})
        print(f"  Updated: {a['slug']}")

    # Create index on filename
    kb_image_files.create_index("filename", unique=True)

    print(f"\nDone! {len(files)} images in MongoDB, {len(articles)} articles updated.")
    client.close()

if __name__ == "__main__":
    main()
