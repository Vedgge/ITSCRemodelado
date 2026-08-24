#!/usr/bin/env python3
"""One-shot image optimisation for the ITSC site.

The repository shipped 31 MB of images: DSLR originals up to 7952x5304 served
raw to browsers, a 7533 px logo on every page, and a 2133 px "favicon".  This
script produces the derivatives the site actually needs and writes a JSON map
of old path -> new asset so the template rewrite can be mechanical.

Run once, commit the output, then purge the originals from git history:

    python3 scripts/optimize_images.py --apply

Idempotent: re-running regenerates the same bytes.  Originals are copied to
assets-src/ (gitignored) so derivatives can be regenerated later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "static" / "img"
SRC_ARCHIVE = ROOT / "assets-src"
MAP_FILE = ROOT / "scripts" / "image-map.json"

# Widths generated for full-bleed content images, consumed via <img srcset>.
CONTENT_WIDTHS = (400, 800, 1600)
WEBP_QUALITY = 82
# A 100x100 PNG can declare gigapixel dimensions; refuse to decode those.
Image.MAX_IMAGE_PIXELS = 80_000_000


def slugify_filename(name: str) -> str:
    """'especializacion enfermeros-2.jpg' -> 'especializacion-enfermeros-2'.

    Filenames with spaces and accents require URL-encoding and break on
    case-insensitive filesystems; normalise them once, here.
    """
    stem = Path(name).stem
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    out = []
    for ch in stem.lower():
        out.append(ch if ch.isalnum() else "-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


@dataclass
class Result:
    generated: list[str] = field(default_factory=list)
    mapping: dict[str, dict] = field(default_factory=dict)
    bytes_before: int = 0
    bytes_after: int = 0
    duplicates: dict[str, str] = field(default_factory=dict)


def _save_webp(im: Image.Image, dest: Path, *, lossless: bool = False) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", quality=WEBP_QUALITY, method=6, lossless=lossless)
    return dest.stat().st_size


def _open_flat(path: Path) -> Image.Image:
    """Open, apply EXIF orientation, and flatten transparency onto white."""
    im = Image.open(path)
    im.load()
    try:
        from PIL import ImageOps

        im = ImageOps.exif_transpose(im) or im
    except Exception:  # noqa: BLE001 - orientation is best-effort
        pass
    return im


def process_content(path: Path, res: Result, *, apply: bool) -> None:
    """Emit -400/-800/-1600 WebP derivatives for a content image."""
    slug = slugify_filename(path.name)
    with _open_flat(path) as im:
        src_w = im.width
        variants = {}
        for w in CONTENT_WIDTHS:
            if w > src_w and w != min(CONTENT_WIDTHS):
                continue  # never upscale
            target = min(w, src_w)
            dest = IMG / f"{slug}-{w}.webp"
            if apply:
                ratio = target / im.width
                resized = im.convert("RGB").resize(
                    (target, max(1, round(im.height * ratio))), Image.Resampling.LANCZOS
                )
                size = _save_webp(resized, dest)
                res.bytes_after += size
                res.generated.append(str(dest.relative_to(ROOT)))
            variants[w] = f"img/{slug}-{w}.webp"
    res.mapping[str(path.relative_to(ROOT / "static"))] = {
        "kind": "content",
        "slug": slug,
        "srcset": variants,
        "default": variants.get(800) or next(iter(variants.values())),
    }


def process_fixed(path: Path, res: Result, widths: tuple[int, ...], *, apply: bool) -> None:
    """Emit fixed-width WebP variants (logos, wordmarks)."""
    slug = slugify_filename(path.name)
    with _open_flat(path) as im:
        has_alpha = im.mode in ("RGBA", "LA", "P")
        variants = {}
        for w in widths:
            target = min(w, im.width)
            dest = IMG / f"{slug}-{w}.webp"
            if apply:
                ratio = target / im.width
                base = im.convert("RGBA" if has_alpha else "RGB")
                resized = base.resize(
                    (target, max(1, round(im.height * ratio))), Image.Resampling.LANCZOS
                )
                size = _save_webp(resized, dest)
                res.bytes_after += size
                res.generated.append(str(dest.relative_to(ROOT)))
            variants[w] = f"img/{slug}-{w}.webp"
    res.mapping[str(path.relative_to(ROOT / "static"))] = {
        "kind": "fixed",
        "slug": slug,
        "srcset": variants,
        "default": variants[max(variants)],
    }


def process_favicon(path: Path, res: Result, *, apply: bool) -> None:
    """A 2133x2133 PNG was being served as the favicon on every page."""
    out = IMG / "favicon"
    sizes = {
        "favicon-16.png": 16,
        "favicon-32.png": 32,
        "apple-touch-icon.png": 180,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }
    with _open_flat(path) as im:
        base = im.convert("RGBA")
        if apply:
            out.mkdir(parents=True, exist_ok=True)
            for fname, s in sizes.items():
                d = out / fname
                base.resize((s, s), Image.Resampling.LANCZOS).save(d, "PNG", optimize=True)
                res.bytes_after += d.stat().st_size
                res.generated.append(str(d.relative_to(ROOT)))
            ico = out / "favicon.ico"
            base.resize((64, 64), Image.Resampling.LANCZOS).save(
                ico, "ICO", sizes=[(16, 16), (32, 32), (48, 48)]
            )
            res.bytes_after += ico.stat().st_size
            res.generated.append(str(ico.relative_to(ROOT)))
    res.mapping[str(path.relative_to(ROOT / "static"))] = {
        "kind": "favicon",
        "slug": "favicon",
        "srcset": {k: f"img/favicon/{v}" for k, v in
                   {32: "favicon-32.png", 180: "apple-touch-icon.png",
                    192: "icon-192.png", 512: "icon-512.png"}.items()},
        "default": "img/favicon/favicon-32.png",
    }


# Explicit manifest.  Being explicit beats globbing: it documents intent and
# stops a newly-dropped file from being silently reprocessed.
FIXED_ASSETS = {
    "logo-itsc.png": (600, 1200),
    "icon-reduced.png": (400, 800),
}
FAVICON_ASSETS = {"fav-icon-itsc.png"}
SKIP = {"do2t.png", "upload-img.png", "hero-novedades-bg.jpg"}  # already small / decorative


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write files (default: dry run)")
    args = ap.parse_args()

    if not IMG.is_dir():
        print(f"error: {IMG} not found", file=sys.stderr)
        return 1

    res = Result()
    seen: dict[str, str] = {}
    originals = sorted(
        p for p in IMG.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )

    if args.apply:
        SRC_ARCHIVE.mkdir(exist_ok=True)

    for path in originals:
        if path.name in SKIP:
            continue
        res.bytes_before += path.stat().st_size

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            res.duplicates[str(path.relative_to(ROOT))] = seen[digest]
            continue
        seen[digest] = str(path.relative_to(ROOT))

        if args.apply:
            shutil.copy2(path, SRC_ARCHIVE / path.name)

        if path.name in FAVICON_ASSETS:
            process_favicon(path, res, apply=args.apply)
        elif path.name in FIXED_ASSETS:
            process_fixed(path, res, FIXED_ASSETS[path.name], apply=args.apply)
        else:
            process_content(path, res, apply=args.apply)

    if args.apply:
        MAP_FILE.write_text(json.dumps(res.mapping, indent=2, sort_keys=True) + "\n")

    mb = 1024 * 1024
    print(f"{'APPLIED' if args.apply else 'DRY RUN'}")
    print(f"  sources processed : {len(res.mapping)}")
    print(f"  files generated   : {len(res.generated)}")
    print(f"  duplicates skipped: {len(res.duplicates)}")
    for dup, orig in res.duplicates.items():
        print(f"      {dup}  ==  {orig}")
    print(f"  before            : {res.bytes_before / mb:.1f} MB")
    if args.apply:
        print(f"  after             : {res.bytes_after / mb:.1f} MB")
        pct = 100 * (1 - res.bytes_after / res.bytes_before) if res.bytes_before else 0
        print(f"  reduction         : {pct:.1f}%")
        print(f"  map written to    : {MAP_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
