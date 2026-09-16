#!/usr/bin/env python3
"""Wolf Smart Upload Naming — Phase 2.5B.

Canonical pattern:
  brand_STAGE_type_subject_detail_YYYYMMDD_sequence.ext
  e.g. habitat_RAW_video_habitat-villa_pool-wide_20260915_001.mp4

Rules:
  - lowercase tokens except STAGE (RAW|EDIT|FINAL)
  - RAW uses _001 / _002 … ; EDIT/FINAL use _v01 / _v02 …
  - never trust client original as canonical; always store original_filename
  - slug-normalize all free-text tokens
  - server owns uniqueness; never overwrite
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

BRANDS = ("habitat", "umablu", "atrium", "selo", "tropik")
STAGES = ("RAW", "EDIT", "FINAL")
MEDIA_TYPES = ("video", "audio", "image", "broll", "graphic")

SLUG_RE = re.compile(r"[^a-z0-9]+")
DATE_RE = re.compile(r"^20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$")
SEQ_RAW_RE = re.compile(r"_(\d{3})$")
SEQ_VER_RE = re.compile(r"_v(\d{2})$")


def slug_normalize(token: str | None, *, fallback: str = "item", max_len: int = 48) -> str:
    s = (token or "").strip().lower()
    s = SLUG_RE.sub("-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    if not s:
        s = fallback
    return s[:max_len]


def normalize_shoot_date(raw: str | None) -> str:
    """Accept YYYYMMDD or YYYY-MM-DD → YYYYMMDD. Raises ValueError if bad."""
    if not raw or not str(raw).strip():
        raise ValueError("shoot_date required (YYYYMMDD or YYYY-MM-DD)")
    s = str(raw).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s = s.replace("-", "")
    if not DATE_RE.match(s):
        raise ValueError(f"invalid shoot_date: {raw!r}")
    return s


def normalize_stage(raw: str | None) -> str:
    stage = (raw or "RAW").strip().upper()
    if stage not in STAGES:
        raise ValueError(f"invalid stage {stage!r}; expected RAW|EDIT|FINAL")
    return stage


def normalize_brand(raw: str | None) -> str:
    brand = (raw or "").strip().lower()
    if brand not in BRANDS:
        raise ValueError(f"invalid brand {brand!r}")
    return brand


def normalize_media_type(raw: str | None, *, ext: str | None = None) -> str:
    mt = (raw or "").strip().lower()
    if not mt and ext:
        mt = media_type_from_ext(ext)
    if mt == "photo":
        mt = "image"
    if mt not in MEDIA_TYPES:
        raise ValueError(f"invalid media_type {mt!r}")
    return mt


def media_type_from_ext(ext: str) -> str:
    e = (ext or "").lower()
    if not e.startswith("."):
        e = f".{e}" if e else ""
    if e in (".mp4", ".mov", ".m4v", ".webm"):
        return "video"
    if e in (".mp3", ".m4a", ".wav", ".aac"):
        return "audio"
    if e in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return "image"
    return "graphic"


def sequence_token(stage: str, n: int) -> str:
    if stage == "RAW":
        return f"{n:03d}"
    return f"v{n:02d}"


def parse_sequence_token(token: str | None, stage: str) -> int | None:
    if not token:
        return None
    t = str(token).strip()
    if stage == "RAW":
        m = re.fullmatch(r"0*(\d{1,3})", t) or re.fullmatch(r"_?(\d{3})", t)
        return int(m.group(1)) if m else None
    m = re.fullmatch(r"v?(\d{1,2})", t, re.I) or re.fullmatch(r"_?v(\d{2})", t, re.I)
    return int(m.group(1)) if m else None


def build_stem(
    brand: str,
    stage: str,
    media_type: str,
    subject: str,
    detail: str | None,
    shoot_date: str,
    seq_token: str,
) -> str:
    brand = normalize_brand(brand)
    stage = normalize_stage(stage)
    media_type = normalize_media_type(media_type)
    subject = slug_normalize(subject, fallback="subject")
    detail_s = slug_normalize(detail, fallback="") if detail and str(detail).strip() else ""
    shoot_date = normalize_shoot_date(shoot_date)
    seq_token = str(seq_token).strip()
    parts = [brand, stage, media_type, subject]
    if detail_s:
        parts.append(detail_s)
    parts.append(shoot_date)
    parts.append(seq_token)
    return "_".join(parts)


def build_canonical_filename(
    brand: str,
    stage: str,
    media_type: str,
    subject: str,
    detail: str | None,
    shoot_date: str,
    seq_token: str,
    ext: str,
) -> str:
    stem = build_stem(brand, stage, media_type, subject, detail, shoot_date, seq_token)
    e = (ext or "").lower()
    if not e.startswith("."):
        e = f".{e}" if e else ""
    if not e:
        raise ValueError("extension required")
    return f"{stem}{e}"


def stem_prefix_for_lookup(
    brand: str,
    stage: str,
    media_type: str,
    subject: str,
    detail: str | None,
    shoot_date: str,
) -> str:
    """Prefix before sequence token (includes trailing _)."""
    brand = normalize_brand(brand)
    stage = normalize_stage(stage)
    media_type = normalize_media_type(media_type)
    subject = slug_normalize(subject, fallback="subject")
    detail_s = slug_normalize(detail, fallback="") if detail and str(detail).strip() else ""
    shoot_date = normalize_shoot_date(shoot_date)
    parts = [brand, stage, media_type, subject]
    if detail_s:
        parts.append(detail_s)
    parts.append(shoot_date)
    return "_".join(parts) + "_"


def _collect_used_sequences(
    conn: sqlite3.Connection,
    prefix: str,
    stage: str,
    ext: str,
) -> set[int]:
    used: set[int] = set()
    e = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
    patterns = (f"{prefix}%",)
    # assets.canonical_filename / filename
    cols = []
    try:
        info = {r[1] for r in conn.execute("PRAGMA table_info(assets)").fetchall()}
        if "canonical_filename" in info:
            cols.append("canonical_filename")
        if "filename" in info:
            cols.append("filename")
    except sqlite3.Error:
        cols = ["filename"]
    for col in cols:
        try:
            rows = conn.execute(
                f"SELECT {col} FROM assets WHERE {col} LIKE ?",
                (patterns[0],),
            ).fetchall()
        except sqlite3.Error:
            continue
        for (name,) in rows:
            if not name:
                continue
            stem = Path(str(name)).stem
            if not stem.startswith(prefix.rstrip("_")) and not stem.startswith(prefix):
                # LIKE matched loosely; require exact prefix
                if not stem.startswith(prefix):
                    continue
            # strip prefix → sequence token
            rest = stem[len(prefix) :] if stem.startswith(prefix) else ""
            # rest may be "001" or "v01" possibly with extra _vN from unique_dest
            n = parse_sequence_token(rest.split("_")[0], stage)
            if n is not None:
                used.add(n)
    # staged_assets.canonical_filename
    try:
        info_s = {r[1] for r in conn.execute("PRAGMA table_info(staged_assets)").fetchall()}
        if "canonical_filename" in info_s:
            for (name,) in conn.execute(
                "SELECT canonical_filename FROM staged_assets WHERE canonical_filename LIKE ?",
                (patterns[0],),
            ).fetchall():
                if not name:
                    continue
                stem = Path(str(name)).stem
                if not stem.startswith(prefix):
                    continue
                rest = stem[len(prefix) :]
                n = parse_sequence_token(rest.split("_")[0], stage)
                if n is not None:
                    used.add(n)
    except sqlite3.Error:
        pass
    return used


def _filesystem_used(dest_dirs: list[Path], prefix: str, stage: str, ext: str) -> set[int]:
    used: set[int] = set()
    e = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
    for d in dest_dirs:
        if not d.is_dir():
            continue
        for p in d.glob(f"{prefix}*{e}"):
            stem = p.stem
            if not stem.startswith(prefix):
                continue
            rest = stem[len(prefix) :]
            n = parse_sequence_token(rest.split("_")[0], stage)
            if n is not None:
                used.add(n)
    return used


def allocate_sequence(
    conn: sqlite3.Connection,
    *,
    brand: str,
    stage: str,
    media_type: str,
    subject: str,
    detail: str | None,
    shoot_date: str,
    ext: str,
    dest_dirs: list[Path] | None = None,
) -> tuple[int, str]:
    """Return (n, sequence_token) next unused, collision-safe vs DB + filesystem."""
    stage = normalize_stage(stage)
    prefix = stem_prefix_for_lookup(brand, stage, media_type, subject, detail, shoot_date)
    used = _collect_used_sequences(conn, prefix, stage, ext)
    if dest_dirs:
        used |= _filesystem_used(dest_dirs, prefix, stage, ext)
    n = 1
    while n in used:
        n += 1
        if n > 999:
            raise RuntimeError("sequence space exhausted")
    return n, sequence_token(stage, n)


def unique_library_path(dest_dir: Path, filename: str) -> Path:
    """Never overwrite. If exact name exists, append _x2, _x3… before ext."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    ext = Path(filename).suffix
    n = 2
    while True:
        alt = dest_dir / f"{stem}_x{n}{ext}"
        if not alt.exists():
            return alt
        n += 1
        if n > 10_000:
            raise OSError("could not allocate unique library filename")


def preview_names(
    conn: sqlite3.Connection,
    *,
    brand: str,
    stage: str,
    media_type: str,
    subject: str,
    shoot_date: str,
    files: list[dict],
    dest_dirs: list[Path] | None = None,
) -> list[dict]:
    """Preview canonical names for a batch. files: [{original_filename, detail?}].

    Allocates sequences in-order without persisting (simulates batch).
    """
    stage = normalize_stage(stage)
    brand = normalize_brand(brand)
    shoot_date = normalize_shoot_date(shoot_date)
    out: list[dict] = []
    # Track provisional allocations per prefix
    provisional: dict[str, set[int]] = {}
    for f in files:
        orig = Path(str(f.get("original_filename") or f.get("name") or "upload.bin")).name
        ext = Path(orig).suffix.lower() or ".bin"
        detail = f.get("detail")
        mt = normalize_media_type(f.get("media_type") or media_type, ext=ext)
        prefix = stem_prefix_for_lookup(brand, stage, mt, subject, detail, shoot_date)
        used = set(provisional.get(prefix) or set())
        used |= _collect_used_sequences(conn, prefix, stage, ext)
        if dest_dirs:
            used |= _filesystem_used(dest_dirs, prefix, stage, ext)
        n = 1
        while n in used:
            n += 1
        provisional.setdefault(prefix, set()).add(n)
        tok = sequence_token(stage, n)
        canon = build_canonical_filename(brand, stage, mt, subject, detail, shoot_date, tok, ext)
        out.append(
            {
                "original_filename": orig,
                "detail": slug_normalize(detail, fallback="") if detail else "",
                "media_type": mt,
                "sequence_token": tok,
                "canonical_filename": canon,
            }
        )
    return out
