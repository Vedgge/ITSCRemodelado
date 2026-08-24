"""Upload validation and storage.

The original code accepted any file, kept the user's filename, and wrote it
into ``static/`` — so uploading ``payload.svg`` or ``payload.html`` produced a
same-origin document that could run script against the site.

The defence that actually matters here is step 5: **re-encoding**. Extension
and MIME checks are bypassable (a polyglot file is a valid JPEG *and* valid
HTML), but a polyglot does not survive being decoded to a pixel buffer and
re-encoded as WebP. EXIF — including GPS coordinates from a phone camera —
is dropped in the same step.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog
from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

from itsc.extensions import db
from itsc.models import MediaAsset

log = structlog.get_logger("itsc.media")

WEBP_QUALITY = 82
MAX_DIMENSION = 2400
#: A 100x100 PNG can declare gigapixel dimensions and exhaust memory on decode.
MAX_PIXELS = 50_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

PDF_MAGIC = b"%PDF-"


class UploadError(ValueError):
    """Raised when an upload is rejected. The message is user-facing."""


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    mime_type: str
    byte_size: int
    checksum: str
    width: int | None = None
    height: int | None = None


def _upload_root() -> Path:
    root = Path(current_app.config["UPLOAD_ROOT"])
    root.mkdir(parents=True, exist_ok=True)
    return root


def _dated_key(extension: str) -> str:
    """``2026/08/<uuid>.webp`` — the server picks the name and the extension.

    The user's own filename never touches the filesystem, which makes path
    traversal structurally impossible rather than merely filtered.
    """
    now = datetime.now(UTC)
    return f"{now:%Y/%m}/{uuid.uuid4().hex}{extension}"


def _read_limited(storage: FileStorage) -> bytes:
    """Read at most MAX_CONTENT_LENGTH + 1 bytes."""
    limit = current_app.config["MAX_CONTENT_LENGTH"]
    storage.stream.seek(0)
    data = storage.stream.read(limit + 1)
    if len(data) > limit:
        raise UploadError(
            f"El archivo supera el máximo de {current_app.config['MAX_UPLOAD_MB']} MB."
        )
    if not data:
        raise UploadError("El archivo está vacío.")
    return data


def process_image(storage: FileStorage) -> StoredFile:
    """Validate, re-encode to WebP, and store an uploaded image."""
    data = _read_limited(storage)

    extension = Path(storage.filename or "").suffix.lower()
    allowed = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    if extension not in allowed:
        raise UploadError(f"Formato no permitido. Usá: {', '.join(sorted(allowed))}.")

    # 1. Does Pillow agree this is an image at all?
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise UploadError("El archivo no es una imagen válida.") from exc

    # verify() leaves the object unusable; reopen to actually read pixels.
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (OSError, Image.DecompressionBombError) as exc:
        raise UploadError("No pudimos procesar la imagen.") from exc

    if image.width * image.height > MAX_PIXELS:
        raise UploadError("La imagen tiene una resolución demasiado alta.")

    # 2. Reject multi-frame images: an animated payload can smuggle content
    #    past a single-frame inspection.
    if getattr(image, "n_frames", 1) > 1:
        raise UploadError("No se admiten imágenes animadas.")

    # 3. Honour EXIF orientation before discarding EXIF.
    with contextlib.suppress(Exception):
        from PIL import ImageOps

        # Orientation is best-effort: a corrupt EXIF block must not
        # fail an otherwise valid upload.
        image = ImageOps.exif_transpose(image) or image

    # 4. Bound the stored dimensions.
    if max(image.width, image.height) > MAX_DIMENSION:
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    # 5. Re-encode. This is the step that neutralises polyglots and strips EXIF.
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "WEBP", quality=WEBP_QUALITY, method=6)
    encoded = buffer.getvalue()

    key = _dated_key(".webp")
    return _write(key, encoded, "image/webp", image.width, image.height)


def process_pdf(storage: FileStorage) -> StoredFile:
    """Validate and store a PDF (institutional documents)."""
    data = _read_limited(storage)

    if Path(storage.filename or "").suffix.lower() != ".pdf":
        raise UploadError("Solo se admiten archivos PDF.")
    # A PDF cannot be re-encoded the way an image can, so verify the magic
    # bytes and rely on nginx serving /media with nosniff + a sandbox CSP.
    if not data.startswith(PDF_MAGIC):
        raise UploadError("El archivo no es un PDF válido.")

    key = _dated_key(".pdf")
    return _write(key, data, "application/pdf")


def _write(
    key: str, data: bytes, mime: str, width: int | None = None, height: int | None = None
) -> StoredFile:
    destination = _upload_root() / key
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Defence in depth: confirm the resolved path is still inside UPLOAD_ROOT.
    root = _upload_root().resolve()
    if not destination.resolve().is_relative_to(root):
        raise UploadError("Ruta de destino inválida.")

    destination.write_bytes(data)
    return StoredFile(
        storage_key=key,
        mime_type=mime,
        byte_size=len(data),
        checksum=hashlib.sha256(data).hexdigest(),
        width=width,
        height=height,
    )


def store_upload(
    storage: FileStorage, *, alt_text: str = "", user_id: int | None = None, kind: str = "image"
) -> MediaAsset:
    """Process an upload and return a persisted :class:`MediaAsset`.

    Content-addressed: re-uploading the same file reuses the existing row. The
    old repository stored the identical 4.7 MB photograph three times.
    """
    stored = process_image(storage) if kind == "image" else process_pdf(storage)

    existing = db.session.query(MediaAsset).filter_by(checksum_sha256=stored.checksum).first()
    if existing is not None:
        (_upload_root() / stored.storage_key).unlink(missing_ok=True)
        log.info("media_deduplicated", asset_id=existing.id)
        return existing

    asset = MediaAsset(
        original_filename=(storage.filename or "sin-nombre")[:255],
        storage_key=stored.storage_key,
        mime_type=stored.mime_type,
        byte_size=stored.byte_size,
        width=stored.width,
        height=stored.height,
        checksum_sha256=stored.checksum,
        alt_text=alt_text[:255],
        uploaded_by_id=user_id,
    )
    db.session.add(asset)
    db.session.flush()
    log.info("media_stored", asset_id=asset.id, mime=asset.mime_type, size=asset.byte_size)
    return asset
