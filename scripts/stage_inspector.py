#!/usr/bin/env python3
"""Intelligent Asset Classifier — stage media into staged_assets (STAGED only).

Standalone under /Users/wolfterminal/beta-os/. Does NOT import or touch wolf-system.
Does NOT copy/move into library_v2 — only INSERT status='STAGED' rows.

Probe strategy:
  - Prefer ffprobe (if `which ffprobe` finds it) for width/height/duration on
    video/audio/image.
  - If ffprobe is missing: Pillow (or basic size) for images; duration left null
    and aspect may be unknown with lower confidence.

Usage:
  python3 stage_inspector.py <source_file_or_dir> [--brand habitat] [--stage RAW] [--limit N] [--yes]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

BETA_ROOT = Path("/Users/wolfterminal/beta-os")
DB_PATH = BETA_ROOT / "catalog" / "content_library.sqlite"

BRANDS = ("habitat", "umablu", "atrium", "selo", "tropik")
STAGES = ("RAW", "EDIT", "FINAL")
TYPES = ("video", "audio", "broll", "graphic")

MEDIA_EXT = {
    ".mp4": "video",
    ".mov": "video",
    ".m4v": "video",
    ".avi": "video",
    ".mkv": "video",
    ".webm": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".aac": "audio",
    ".m4a": "audio",
    ".flac": "audio",
    ".ogg": "audio",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".tif": "image",
    ".tiff": "image",
    ".svg": "image",
    ".psd": "image",
    ".ai": "image",
}

DATE_RE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")
SLUG_SAFE = re.compile(r"[^a-z0-9]+")
ASPECT_TOL = 0.08


def die(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def assert_beta_isolation() -> None:
    root = str(BETA_ROOT.resolve())
    if "wolf-system" in root:
        die("BETA_ROOT resolves inside wolf-system — refuse")
    if not BETA_ROOT.is_dir():
        die(f"beta-os root missing: {BETA_ROOT}")
    if not DB_PATH.is_file():
        die(f"catalog DB missing: {DB_PATH}")


def find_ffprobe() -> str | None:
    return shutil.which("ffprobe")


def guess_brand_from_path(path: Path) -> str | None:
    text = "/".join(p.lower() for p in path.parts)
    aliases = [
        ("uma-blu", "umablu"),
        ("uma_blu", "umablu"),
        ("umablu", "umablu"),
        ("habitat", "habitat"),
        ("atrium", "atrium"),
        ("selong", "selo"),
        ("selo", "selo"),
        ("tropik", "tropik"),
    ]
    for needle, brand in aliases:
        if needle in text:
            return brand
    return None


def slugify(stem: str) -> str:
    s = stem.lower()
    s = DATE_RE.sub("", s)
    s = SLUG_SAFE.sub("-", s).strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:80] or "asset"


def detect_mime_kind(path: Path) -> str | None:
    """Return video|image|audio from extension."""
    return MEDIA_EXT.get(path.suffix.lower())


def guess_suggested_type(path: Path, mime: str, aspect: str, duration: float | None) -> str:
    name = path.name.lower()
    if "broll" in name or "b-roll" in name:
        return "broll"
    if mime == "audio":
        return "audio"
    if mime == "image":
        return "graphic"
    # video
    if mime == "video":
        # short vertical stays video unless name says broll
        return "video"
    return "graphic"


def guess_stage(path: Path, cli_stage: str | None) -> str:
    if cli_stage:
        return cli_stage
    text = "/".join(p.lower() for p in path.parts) + "/" + path.name.lower()
    if re.search(r"(^|[/_\-\s])final([/_\-\s.]|$)", text):
        return "FINAL"
    return "RAW"


def bucket_aspect(width: int | None, height: int | None) -> str:
    if not width or not height or width <= 0 or height <= 0:
        return "unknown"
    ratio = width / height
    # 16:9 landscape ≈ 1.777
    if abs(ratio - 16 / 9) <= ASPECT_TOL:
        return "16:9"
    # 9:16 portrait ≈ 0.5625
    if abs(ratio - 9 / 16) <= ASPECT_TOL:
        return "9:16"
    # 1:1
    if abs(ratio - 1.0) <= ASPECT_TOL:
        return "1:1"
    return "unknown"


def ffprobe_meta(ffprobe: str, path: Path) -> dict:
    """Return width, height, duration_sec (any may be None)."""
    out: dict = {"width": None, "height": None, "duration_sec": None, "ok": False}
    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return out
        data = json.loads(proc.stdout)
        streams = data.get("streams") or []
        fmt = data.get("format") or {}
        dur = fmt.get("duration")
        if dur is not None:
            try:
                out["duration_sec"] = float(dur)
            except (TypeError, ValueError):
                pass
        for s in streams:
            codec_type = s.get("codec_type")
            if codec_type == "video" or (
                codec_type is None and s.get("width") and s.get("height")
            ):
                w, h = s.get("width"), s.get("height")
                if w and h:
                    out["width"] = int(w)
                    out["height"] = int(h)
                    break
        if out["duration_sec"] is None:
            for s in streams:
                d = s.get("duration")
                if d is not None:
                    try:
                        out["duration_sec"] = float(d)
                        break
                    except (TypeError, ValueError):
                        pass
        out["ok"] = True
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        pass
    return out


def pillow_size(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image

        with Image.open(path) as im:
            return int(im.size[0]), int(im.size[1])
    except Exception:
        return None, None


def collect_media(source: Path) -> list[Path]:
    files: list[Path] = []
    for root, _dirs, names in os.walk(source):
        if any(part.startswith(".") for part in Path(root).parts):
            continue
        for name in names:
            if name.startswith("."):
                continue
            p = Path(root) / name
            if detect_mime_kind(p):
                files.append(p)
    files.sort(key=lambda p: str(p).lower())
    return files


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS staged_assets (
          id INTEGER PRIMARY KEY,
          temp_path TEXT,
          detected_mime TEXT,
          aspect_ratio TEXT,
          duration_sec REAL,
          suggested_brand TEXT,
          suggested_stage TEXT,
          suggested_type TEXT,
          suggested_slug TEXT,
          confidence_score REAL,
          status TEXT,
          created_at DATETIME
        )
        """
    )
    conn.commit()


def score_confidence(
    *,
    brand_from_path: bool,
    brand_cli: bool,
    probe_ok: bool,
    aspect: str,
    mime: str,
    stage_from_name: bool,
) -> float:
    score = 0.25  # base for recognized media ext
    if brand_cli:
        score += 0.35
    elif brand_from_path:
        score += 0.30
    if probe_ok:
        score += 0.25
    if aspect != "unknown":
        score += 0.10
    if mime in ("video", "audio", "image"):
        score += 0.05
    if stage_from_name:
        score += 0.05
    return round(min(1.0, max(0.0, score)), 3)


def inspect_one(
    path: Path,
    *,
    cli_brand: str | None,
    cli_stage: str | None,
    ffprobe: str | None,
) -> dict:
    mime = detect_mime_kind(path)
    assert mime is not None

    width = height = None
    duration: float | None = None
    probe_ok = False

    if ffprobe:
        meta = ffprobe_meta(ffprobe, path)
        width, height = meta["width"], meta["height"]
        duration = meta["duration_sec"]
        probe_ok = bool(meta["ok"])

    if (width is None or height is None) and mime == "image":
        w2, h2 = pillow_size(path)
        if w2 and h2:
            width, height = w2, h2
            # Pillow fallback is partial probe
            if not probe_ok:
                probe_ok = False  # keep lower confidence without ffprobe

    aspect = bucket_aspect(width, height)
    brand_path = guess_brand_from_path(path)
    brand = (cli_brand.lower() if cli_brand else None) or brand_path or "habitat"
    if brand not in BRANDS:
        brand = "habitat"

    stage = guess_stage(path, cli_stage)
    typ = guess_suggested_type(path, mime, aspect, duration)
    slug = slugify(path.stem)

    text_lower = "/".join(p.lower() for p in path.parts) + "/" + path.name.lower()
    stage_from_name = bool(re.search(r"(^|[/_\-\s])final([/_\-\s.]|$)", text_lower))

    conf = score_confidence(
        brand_from_path=bool(brand_path),
        brand_cli=bool(cli_brand),
        probe_ok=probe_ok,
        aspect=aspect,
        mime=mime,
        stage_from_name=stage_from_name,
    )
    # Without ffprobe on non-image, drop confidence further
    if not ffprobe and mime != "image":
        conf = round(max(0.1, conf - 0.2), 3)
    elif not ffprobe and mime == "image" and aspect == "unknown":
        conf = round(max(0.1, conf - 0.15), 3)

    return {
        "temp_path": str(path.resolve()),
        "detected_mime": mime,
        "aspect_ratio": aspect,
        "duration_sec": duration,
        "suggested_brand": brand,
        "suggested_stage": stage,
        "suggested_type": typ,
        "suggested_slug": slug,
        "confidence_score": conf,
        "status": "STAGED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def insert_staged(conn: sqlite3.Connection, row: dict) -> int:
    cur = conn.execute(
        """
        INSERT INTO staged_assets (
          temp_path, detected_mime, aspect_ratio, duration_sec,
          suggested_brand, suggested_stage, suggested_type, suggested_slug,
          confidence_score, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["temp_path"],
            row["detected_mime"],
            row["aspect_ratio"],
            row["duration_sec"],
            row["suggested_brand"],
            row["suggested_stage"],
            row["suggested_type"],
            row["suggested_slug"],
            row["confidence_score"],
            row["status"],
            row["created_at"],
        ),
    )
    return int(cur.lastrowid)



def stage_file(
    path: Path,
    *,
    brand: str | None = None,
    stage: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict:
    """Inspect one media file and INSERT a STAGED row. Never writes library_v2.

    Returns the staged row dict including ``id`` and ``suggested_slug``.
    """
    path = Path(path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"not a file: {path}")
    resolved = str(path.resolve())
    if "/wolf-system" in resolved or resolved.endswith("wolf-system"):
        raise PermissionError("refuse: path under wolf-system")
    if detect_mime_kind(path) is None:
        raise ValueError(f"not a recognized media file: {path.name}")

    own_conn = conn is None
    if own_conn:
        assert_beta_isolation()
        conn = sqlite3.connect(DB_PATH)
        ensure_schema(conn)
    assert conn is not None
    try:
        ffprobe = find_ffprobe()
        row = inspect_one(
            path,
            cli_brand=brand,
            cli_stage=stage if stage is not None else "RAW",
            ffprobe=ffprobe,
        )
        rid = insert_staged(conn, row)
        row["id"] = rid
        if own_conn:
            conn.commit()
        return row
    finally:
        if own_conn:
            conn.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Classify media into staged_assets (STAGED). Never writes library_v2. "
            "Uses ffprobe when available; else Pillow/basic size for images "
            "(duration null / aspect may be unknown, lower confidence)."
        )
    )
    p.add_argument("source_dir", type=Path, help="Media file or directory to inspect")
    p.add_argument("--brand", choices=BRANDS, default=None, help="Force suggested brand")
    p.add_argument(
        "--stage",
        choices=STAGES,
        default=None,
        help="Force suggested stage (default: RAW unless path/name has FINAL)",
    )
    p.add_argument("--limit", type=int, default=None, help="Max files to stage this run")
    p.add_argument(
        "--yes",
        action="store_true",
        help="Non-interactive (accepted for API/subprocess callers)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    assert_beta_isolation()

    source = args.source_dir.expanduser()
    if not source.exists():
        die(f"source not found: {source}")
    if not (source.is_dir() or source.is_file()):
        die(f"source is not a file or directory: {source}")

    try:
        resolved = str(source.resolve())
    except OSError as e:
        die(f"cannot resolve source: {e}")
    if "/wolf-system" in resolved or resolved.endswith("wolf-system"):
        die("refuse: source path is under wolf-system")

    ffprobe = find_ffprobe()
    if ffprobe:
        print(f"ffprobe: {ffprobe}")
    else:
        print(
            "ffprobe: not found — images use Pillow/size; "
            "video/audio duration/aspect may be unknown (lower confidence)"
        )

    if source.is_file():
        if detect_mime_kind(source) is None:
            die(f"not a recognized media file: {source}")
        media = [source]
    else:
        media = collect_media(source)
    if args.limit is not None:
        media = media[: max(0, args.limit)]

    if not media:
        print(f"No media files found under {source}")
        return 0

    print(f"Inspecting {len(media)} file(s) under {source} → staged_assets only")

    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    rows: list[dict] = []
    try:
        for path in media:
            try:
                row = inspect_one(
                    path,
                    cli_brand=args.brand,
                    cli_stage=args.stage,
                    ffprobe=ffprobe,
                )
                rid = insert_staged(conn, row)
                row["id"] = rid
                rows.append(row)
                print(
                    f"  STAGED #{rid} {path.name} → "
                    f"{row['suggested_brand']}/{row['suggested_stage']}/"
                    f"{row['suggested_type']}/{row['suggested_slug']} "
                    f"conf={row['confidence_score']} aspect={row['aspect_ratio']}"
                )
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {path}: {e}", file=sys.stderr)
        conn.commit()
    finally:
        conn.close()

    brands = Counter(r["suggested_brand"] for r in rows)
    avg_conf = (
        sum(r["confidence_score"] for r in rows) / len(rows) if rows else 0.0
    )
    print("\n=== STAGING SUMMARY ===")
    print(f"[STAGED] {len(rows)}")
    print("[Brand Breakdown]")
    for b, n in sorted(brands.items()):
        print(f"  {b}: {n}")
    print(f"[Avg Confidence] {avg_conf:.3f}")
    print("library_v2 untouched (commit via /api/staging/commit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
