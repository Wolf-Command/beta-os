#!/usr/bin/env python3
"""GGV Content Engine 2.0 — Legacy batch migration & cataloging.

Standalone. Lives only under /Users/wolfterminal/beta-os/.
Does NOT import, call, or spawn anything from wolf-system.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

BETA_ROOT = Path("/Users/wolfterminal/beta-os")
LIBRARY_V2 = BETA_ROOT / "library_v2"
DB_PATH = BETA_ROOT / "catalog" / "content_library.sqlite"
BATCH_SIZE = 50

BRANDS = ("habitat", "umablu", "atrium", "selo", "tropik")
STAGES = ("RAW", "FINAL")
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
    ".jpg": "graphic",
    ".jpeg": "graphic",
    ".png": "graphic",
    ".gif": "graphic",
    ".webp": "graphic",
    ".tif": "graphic",
    ".tiff": "graphic",
    ".svg": "graphic",
    ".psd": "graphic",
    ".ai": "graphic",
}

DATE_RE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")
SLUG_SAFE = re.compile(r"[^a-z0-9]+")


class SkipAsset(Exception):
    pass


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


def detect_source_system(source_root: Path, file_path: Path) -> str:
    parts = [p.lower() for p in file_path.parts]
    joined = "/".join(parts)
    root_name = source_root.name.lower()
    if "obsidian" in joined or root_name == "obsidian" or ".obsidian" in parts:
        return "obsidian"
    if "notion" in joined or "notion-export" in joined or root_name.startswith("notion"):
        return "notion"
    return "local_drive"


def infer_type(path: Path) -> str | None:
    return MEDIA_EXT.get(path.suffix.lower())


def extract_date_yyyymmdd(path: Path) -> str:
    for text in (path.stem, path.parent.name, path.name):
        m = DATE_RE.search(text)
        if m:
            y, mo, d = m.group(1), m.group(2), m.group(3)
            try:
                datetime(int(y), int(mo), int(d))
                return f"{y}{mo}{d}"
            except ValueError:
                pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d")
    except OSError:
        return datetime.now().strftime("%Y%m%d")


def slugify(stem: str) -> str:
    s = stem.lower()
    s = DATE_RE.sub("", s)
    s = SLUG_SAFE.sub("-", s).strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:80] or "asset"


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


def resolve_brand(path: Path, cli_brand: str | None, interactive: bool) -> str:
    if cli_brand:
        b = cli_brand.lower()
        if b not in BRANDS:
            die(f"invalid --brand {cli_brand!r}; choose {', '.join(BRANDS)}")
        return b
    guessed = guess_brand_from_path(path)
    if guessed:
        return guessed
    if not interactive:
        die(
            f"cannot auto-assign brand for {path}. "
            "Pass --brand or run without --yes for prompts."
        )
    while True:
        ans = input(
            f"Brand for {path.name}? [{'/'.join(BRANDS)}] (or skip): "
        ).strip().lower()
        if ans in ("skip", "s", ""):
            raise SkipAsset()
        if ans in BRANDS:
            return ans
        print(f"  pick one of: {', '.join(BRANDS)}")


def build_v2_name(brand: str, stage: str, typ: str, slug: str, ymd: str, ext: str) -> str:
    ext = ext if ext.startswith(".") else f".{ext}"
    return f"{brand}_drop_{stage}_{typ}_{slug}_{ymd}{ext.lower()}"


def collect_media(source: Path) -> list[Path]:
    files: list[Path] = []
    for root, _dirs, names in os.walk(source):
        if any(part.startswith(".") for part in Path(root).parts):
            continue
        for name in names:
            if name.startswith("."):
                continue
            p = Path(root) / name
            if infer_type(p):
                files.append(p)
    files.sort(key=lambda p: str(p).lower())
    return files


def batched(items: list[Path], size: int):
    for i in range(0, len(items), size):
        yield i // size + 1, items[i : i + size]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assets (
          id INTEGER PRIMARY KEY,
          brand TEXT,
          stage TEXT,
          type TEXT,
          slug TEXT,
          filename TEXT,
          original_path TEXT,
          v2_path TEXT,
          source_system TEXT,
          date_added DATETIME,
          status TEXT
        )
        """
    )
    conn.commit()


def insert_asset(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        """
        INSERT INTO assets (
          brand, stage, type, slug, filename,
          original_path, v2_path, source_system, date_added, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["brand"],
            row["stage"],
            row["type"],
            row["slug"],
            row["filename"],
            row["original_path"],
            row["v2_path"],
            row["source_system"],
            row["date_added"],
            row["status"],
        ),
    )


def unique_dest(dest_dir: Path, filename: str) -> Path:
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    ext = Path(filename).suffix
    n = 2
    while True:
        alt = dest_dir / f"{stem}_v{n}{ext}"
        if not alt.exists():
            return alt
        n += 1


def migrate_one(
    path: Path,
    source_root: Path,
    stage: str,
    cli_brand: str | None,
    interactive: bool,
    dry_run: bool,
    conn: sqlite3.Connection | None,
) -> dict:
    typ = infer_type(path)
    if not typ:
        raise SkipAsset()

    brand = resolve_brand(path, cli_brand, interactive)
    ymd = extract_date_yyyymmdd(path)
    slug = slugify(path.stem)
    filename = build_v2_name(brand, stage, typ, slug, ymd, path.suffix)
    dest_dir = LIBRARY_V2 / stage
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = unique_dest(dest_dir, filename)
    filename = dest.name
    source_system = detect_source_system(source_root, path)
    now = datetime.now().isoformat(timespec="seconds")

    row = {
        "brand": brand,
        "stage": stage,
        "type": typ,
        "slug": slug,
        "filename": filename,
        "original_path": str(path.resolve()),
        "v2_path": str(dest),
        "source_system": source_system,
        "date_added": now,
        "status": "indexed",
    }

    if dry_run:
        print(f"  DRY  {path.name} -> {dest}")
        return row

    shutil.copy2(path, dest)
    assert conn is not None
    insert_asset(conn, row)
    print(f"  OK   {path.name} -> {dest.name} [{brand}/{source_system}]")
    return row


def print_summary(rows: list[dict]) -> None:
    brands = Counter(r["brand"] for r in rows)
    sources = Counter(r["source_system"] for r in rows)
    print("\n=== BATCH SUMMARY ===")
    print(f"[Total Ingested] {len(rows)}")
    print("[Brand Breakdown]")
    for b in BRANDS:
        if brands.get(b):
            print(f"  {b}: {brands[b]}")
    for b, n in brands.items():
        if b not in BRANDS:
            print(f"  {b}: {n}")
    print("[Source Systems]")
    for s, n in sorted(sources.items()):
        print(f"  {s}: {n}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Migrate legacy media into beta-os library_v2 + catalog (batches of 50)."
    )
    p.add_argument(
        "source",
        type=Path,
        help="Source folder (legacy media, Obsidian attachments, Notion export, etc.)",
    )
    p.add_argument(
        "--stage",
        choices=STAGES,
        default="RAW",
        help="Target stage folder under library_v2 (default: RAW)",
    )
    p.add_argument(
        "--brand",
        choices=BRANDS,
        default=None,
        help="Force brand for all files in this run",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Files per batch (default {BATCH_SIZE})",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Non-interactive: auto brand from path, fail if unknown",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan only — no copy, no DB writes",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max files to process this run",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    assert_beta_isolation()

    source = args.source.expanduser()
    if not source.is_dir():
        die(f"source is not a directory: {source}")

    try:
        resolved = str(source.resolve())
    except OSError as e:
        die(f"cannot resolve source: {e}")
    if "/wolf-system" in resolved or resolved.endswith("wolf-system"):
        die("refuse: source path is under wolf-system (use an export/copy outside legacy)")

    media = collect_media(source)
    if args.limit is not None:
        media = media[: max(0, args.limit)]

    if not media:
        print(f"No media files found under {source}")
        return 0

    print(
        f"Found {len(media)} media file(s). "
        f"Batch size={args.batch_size}. Stage={args.stage}."
    )
    interactive = not args.yes
    ingested: list[dict] = []
    skipped = 0

    conn: sqlite3.Connection | None = None
    if not args.dry_run:
        conn = sqlite3.connect(DB_PATH)
        ensure_schema(conn)

    try:
        for batch_num, batch in batched(media, max(1, args.batch_size)):
            print(f"\n--- Batch {batch_num} ({len(batch)} files) ---")
            for path in batch:
                try:
                    row = migrate_one(
                        path=path,
                        source_root=source,
                        stage=args.stage,
                        cli_brand=args.brand,
                        interactive=interactive,
                        dry_run=args.dry_run,
                        conn=conn,
                    )
                    ingested.append(row)
                except SkipAsset:
                    skipped += 1
                    print(f"  SKIP {path}")
                except Exception as e:
                    skipped += 1
                    print(f"  FAIL {path}: {e}", file=sys.stderr)
            if conn is not None:
                conn.commit()
    finally:
        if conn is not None:
            conn.close()

    print_summary(ingested)
    if skipped:
        print(f"[Skipped/Failed] {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
