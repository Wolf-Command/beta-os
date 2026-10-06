"""REAL evidence store — separate from synthetic dev evidence and from live WI state.

Vesper M1: tests once wrote junk into live ~/beta-os/state/wolf-intelligence.
Real commissioning/benchmark evidence therefore lives in its own root:

    WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT  (default ~/wi-real-evidence)

Every record is stamped evidence_class=REAL, synthetic=False. Readers (registry,
routing learner) ignore anything that is not REAL, so synthetic history can never
leak into routing. Writes are append-only JSONL plus immutable artifact files.
The root is refused if it sits inside the live Beta WI state or the beta-os tree.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .paths import BETA_ROOT, LIVE_STATE_ROOT

REAL_EVIDENCE_ENV = "WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT"
DEFAULT_REAL_ROOT = Path.home() / "wi-real-evidence"
WITA = timezone(timedelta(hours=8), "WITA")

_SECRET_PATTERNS = (
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"xai-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{24,}"),
    re.compile(r"1//0[0-9A-Za-z_\-]{30,}"),
)


class RealEvidenceError(RuntimeError):
    pass


def now_wita() -> str:
    return datetime.now(WITA).isoformat(timespec="seconds")


def root() -> Path:
    raw = os.environ.get(REAL_EVIDENCE_ENV, "").strip()
    r = (Path(raw).expanduser() if raw else DEFAULT_REAL_ROOT).resolve()
    live = LIVE_STATE_ROOT.resolve()
    beta = BETA_ROOT.resolve()
    if r == live or live in r.parents or r == beta or beta in r.parents:
        raise RealEvidenceError(f"refusing REAL evidence root inside live Beta tree/state: {r}")
    return r


def redact(text: str) -> str:
    out = text or ""
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def contains_secret(text: str) -> bool:
    return any(p.search(text or "") for p in _SECRET_PATTERNS)


def _records_dir() -> Path:
    d = root() / "records"
    d.mkdir(parents=True, exist_ok=True)
    return d


def append(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    """Append one REAL record. Returns the stored record (with id/hash)."""
    if not re.fullmatch(r"[a-z0-9_\-]+", kind):
        raise RealEvidenceError(f"bad kind {kind!r}")
    rec = dict(record)
    rec["evidence_class"] = "REAL"
    rec["synthetic"] = False
    rec.setdefault("recorded_at", now_wita())
    body = json.dumps(rec, sort_keys=True, default=str)
    if contains_secret(body):
        raise RealEvidenceError("record contains secret-shaped material; refusing to write")
    rec["record_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    path = _records_dir() / f"{kind}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
    return rec


def read(kind: str) -> list[dict[str, Any]]:
    path = _records_dir() / f"{kind}.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("evidence_class") == "REAL" and rec.get("synthetic") is False:
            out.append(rec)
    return out


def write_artifact(rel: str, text: str) -> str:
    """Write an immutable artifact (raw output etc.). Returns path relative to root."""
    rel_path = Path(rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise RealEvidenceError("artifact path must be relative")
    path = root() / "artifacts" / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = redact(text)
    if path.exists():
        stem, suf = path.stem, path.suffix
        path = path.with_name(f"{stem}-{int(time.time()*1000)}{suf}")
    path.write_text(clean, encoding="utf-8")
    return str(path.relative_to(root()))


def owner_approved(worker_id: str) -> dict[str, Any] | None:
    """Metered workers need a REAL owner approval record that is unexpired.

    Approvals are only ever written by a human via `python -m wolf_intelligence
    approve-metered` (not by any agent path). No record → gated.
    """
    now = datetime.now(WITA)
    for rec in reversed(read("owner_approvals")):
        if rec.get("worker_id") != worker_id:
            continue
        if rec.get("revoked"):
            return None
        try:
            exp = datetime.fromisoformat(str(rec.get("expires_at")))
        except ValueError:
            return None
        return rec if exp > now else None
    return None


def iter_kind(kinds: Iterable[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for k in kinds:
        out.extend(read(k))
    return out
