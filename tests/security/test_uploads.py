"""Upload-validation regressions.

The original saved whatever it received, under the user's own filename, into
static/ (`main.py:141-158`). Uploading `payload.svg` or `payload.html` produced
a same-origin document that could run script against the site, and there was no
MAX_CONTENT_LENGTH at all.
"""

from __future__ import annotations

import io

import pytest

from itsc.services.media import UploadError, process_image, store_upload


def _fs(data: bytes, filename: str):
    from werkzeug.datastructures import FileStorage

    return FileStorage(stream=io.BytesIO(data), filename=filename)


@pytest.mark.security
def test_rejects_html_disguised_as_jpg(app, db, html_file, upload_dir):
    before = set(upload_dir.rglob("*"))
    with app.test_request_context(), pytest.raises(UploadError):
        process_image(_fs(html_file, "evil.jpg"))
    assert set(upload_dir.rglob("*")) == before, "a rejected upload was written to disk"


@pytest.mark.security
@pytest.mark.parametrize("filename", ["evil.svg", "evil.html", "evil.php", "evil.js", "shell.sh"])
def test_rejects_disallowed_extensions(app, db, svg_file, filename):
    with app.test_request_context(), pytest.raises(UploadError):
        process_image(_fs(svg_file, filename))


@pytest.mark.security
def test_reencoding_strips_embedded_payload(app, db, jpeg_with_payload, upload_dir):
    """The defence that actually matters.

    Extension and MIME checks are bypassable -- a polyglot is a valid JPEG
    *and* valid HTML. A polyglot does not survive being decoded to pixels and
    re-encoded.
    """
    assert b"<script>" in jpeg_with_payload, "fixture must actually carry the payload"

    with app.test_request_context():
        stored = process_image(_fs(jpeg_with_payload, "photo.jpg"))

    raw = (upload_dir / stored.storage_key).read_bytes()
    assert b"<script>" not in raw, "payload survived re-encoding"
    assert raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    assert stored.mime_type == "image/webp"


@pytest.mark.security
def test_filename_is_server_generated(app, db, real_jpeg):
    """Path traversal is structurally impossible when the user's filename never
    reaches the filesystem."""
    with app.test_request_context():
        stored = process_image(_fs(real_jpeg, "../../../../etc/passwd.jpg"))
    assert "etc" not in stored.storage_key
    assert "passwd" not in stored.storage_key
    assert ".." not in stored.storage_key
    assert stored.storage_key.endswith(".webp")


@pytest.mark.security
def test_stored_file_is_not_reachable_under_static(client, app, db, real_jpeg):
    with app.test_request_context():
        stored = process_image(_fs(real_jpeg, "photo.jpg"))
    name = stored.storage_key.rsplit("/", 1)[-1]
    for path in (
        f"/static/{name}",
        f"/static/imagenes-novedades/{name}",
        f"/static/{stored.storage_key}",
    ):
        assert client.get(path).status_code == 404, f"{path} should not be servable"


@pytest.mark.security
def test_rejects_oversize_upload(app, db):
    with app.test_request_context():
        oversize = b"\xff\xd8\xff" + b"\x00" * (app.config["MAX_CONTENT_LENGTH"] + 10)
        with pytest.raises(UploadError, match="supera"):
            process_image(_fs(oversize, "big.jpg"))


@pytest.mark.security
def test_rejects_empty_upload(app, db):
    with app.test_request_context(), pytest.raises(UploadError):
        process_image(_fs(b"", "empty.jpg"))


@pytest.mark.security
def test_rejects_decompression_bomb(app, db):
    """A small file declaring gigapixel dimensions must not be decoded."""
    from PIL import Image

    with app.test_request_context():
        original = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = 10  # simulate the guard tripping
        try:
            buffer = io.BytesIO()
            Image.new("RGB", (200, 200), "blue").save(buffer, "PNG")
            with pytest.raises((UploadError, Image.DecompressionBombError)):
                process_image(_fs(buffer.getvalue(), "bomb.png"))
        finally:
            Image.MAX_IMAGE_PIXELS = original


@pytest.mark.security
def test_pdf_must_have_pdf_magic_bytes(app, db, html_file):
    from itsc.services.media import process_pdf

    with app.test_request_context(), pytest.raises(UploadError):
        process_pdf(_fs(html_file, "fake.pdf"))


@pytest.mark.security
def test_identical_uploads_are_deduplicated(app, db, real_jpeg):
    """The old repo stored the same 4.7 MB photograph three times."""
    from itsc.models import MediaAsset

    with app.test_request_context():
        first = store_upload(_fs(real_jpeg, "a.jpg"))
        db.session.commit()
        second = store_upload(_fs(real_jpeg, "b.jpg"))
        db.session.commit()

    assert first.id == second.id
    assert (
        db.session.query(MediaAsset).filter_by(checksum_sha256=first.checksum_sha256).count() == 1
    )
