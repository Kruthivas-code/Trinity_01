"""
Phase 5 tests (help-doc-v3 feature port): responsive image support --
`GET /api/kb/images/{filename}?w=<px>&format=<fmt>` server-side resize/
re-encode, backing the frontend's DocImage `srcset` (Media.jsx).

Same mongomock + FastAPI TestClient harness as test_kb_phase4_editor_ux.py /
test_review_phase1.py -- standalone module, run directly with
`python -m pytest backend/tests/test_kb_image_resize_phase5.py`.
"""
import io
import os
import sys

import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_kb_image_resize_phase5")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import server  # noqa: E402
from routes.kb import kb_image_files  # noqa: E402

app = server.app
client = TestClient(app)


def _png_bytes(width=800, height=400, color=(200, 50, 50)):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _seed_image(filename, data=None, content_type="image/png"):
    kb_image_files.insert_one({
        "filename": filename,
        "original_name": filename,
        "content_type": content_type,
        "data": data if data is not None else _png_bytes(),
        "size": len(data) if data is not None else len(_png_bytes()),
    })


@pytest.fixture(autouse=True)
def _clean_state():
    kb_image_files.delete_many({})
    yield
    kb_image_files.delete_many({})


class TestImageResize:
    def test_no_params_returns_original_bytes(self):
        original = _png_bytes(800, 400)
        _seed_image("orig.png", data=original)
        resp = client.get("/api/kb/images/orig.png")
        assert resp.status_code == 200
        assert resp.content == original
        assert resp.headers["content-type"] == "image/png"

    def test_w_param_resizes_down_preserving_aspect_ratio(self):
        _seed_image("wide.png", data=_png_bytes(800, 400))
        resp = client.get("/api/kb/images/wide.png?w=200")
        assert resp.status_code == 200
        img = Image.open(io.BytesIO(resp.content))
        assert img.width == 200
        assert img.height == 100  # 800x400 -> 200x100, same 2:1 ratio

    def test_w_larger_than_original_does_not_upscale(self):
        _seed_image("small.png", data=_png_bytes(100, 50))
        resp = client.get("/api/kb/images/small.png?w=4000")
        assert resp.status_code == 200
        img = Image.open(io.BytesIO(resp.content))
        # Clamped to MAX_IMAGE_TRANSFORM_WIDTH but original is smaller than
        # that anyway, so it should stay at the original width, not upscale.
        assert img.width == 100

    def test_format_webp_reencodes_and_sets_content_type(self):
        _seed_image("photo.png", data=_png_bytes(300, 150))
        resp = client.get("/api/kb/images/photo.png?format=webp")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/webp"
        img = Image.open(io.BytesIO(resp.content))
        assert img.format == "WEBP"

    def test_w_and_format_together(self):
        _seed_image("both.png", data=_png_bytes(1000, 500))
        resp = client.get("/api/kb/images/both.png?w=480&format=webp")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/webp"
        img = Image.open(io.BytesIO(resp.content))
        assert img.width == 480
        assert img.height == 240

    def test_corrupt_image_falls_back_to_original_bytes(self):
        garbage = b"not-a-real-image-just-bytes"
        _seed_image("garbage.png", data=garbage, content_type="image/png")
        resp = client.get("/api/kb/images/garbage.png?w=200")
        assert resp.status_code == 200
        # Transform failed silently -- original bytes served unchanged.
        assert resp.content == garbage

    def test_missing_image_still_404s_with_params(self):
        resp = client.get("/api/kb/images/does-not-exist.png?w=200")
        assert resp.status_code == 404

    def test_width_clamped_to_max(self):
        _seed_image("huge.png", data=_png_bytes(5000, 2500))
        resp = client.get("/api/kb/images/huge.png?w=999999")
        assert resp.status_code == 200
        img = Image.open(io.BytesIO(resp.content))
        assert img.width == 2400  # MAX_IMAGE_TRANSFORM_WIDTH


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
