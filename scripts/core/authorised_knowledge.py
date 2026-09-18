#!/usr/bin/env python3
"""Wolf Core Authorised Knowledge Resolver v1 (Beta).

Deterministic pipeline (no LLM invent, no crawl, no memory_items promote):

  SCOPE → CANONICAL → DISCOVER → RETRIEVE → RECONCILE →
  AUTHORITY → FRESHNESS → CONFLICTS → answer / status

CAP-INTEL-02 (authorised retrieval) + CAP-INTEL-03 (provenance / conflict).
EMPTY FIELD ≠ UNKNOWN. SOURCE FOUND ≠ AUTHORITATIVE ≠ CANONICAL.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- Caps (anti-crawl) -------------------------------------------------------

MAX_SOURCES_PER_RESOLVE = 8
MAX_BYTES_PER_SOURCE = 256 * 1024  # 256 KiB

PDFTOTEXT_BIN = Path("/opt/homebrew/bin/pdftotext")

# Supported live retrieve types. Anything else → INACCESSIBLE (not guessed text).
SUPPORTED_SOURCE_TYPES = frozenset(
    {"json", "pdf", "markdown", "md", "python", "py", "text", "txt"}
)

# --- Status vocabulary (exact strings) ---------------------------------------

STATUS_NOT_CANONICAL = "NOT CANONICAL"
STATUS_NOT_FOUND = "NOT FOUND"
STATUS_INACCESSIBLE = "INACCESSIBLE"
STATUS_CONFLICTED = "CONFLICTED"
STATUS_UNKNOWN = "UNKNOWN"

STATUSES = frozenset(
    {
        STATUS_NOT_CANONICAL,
        STATUS_NOT_FOUND,
        STATUS_INACCESSIBLE,
        STATUS_CONFLICTED,
        STATUS_UNKNOWN,
    }
)

# Higher wins. INFERENCE is never evidence.
AUTHORITY_RANK: dict[str, int] = {
    "CANONICAL": 100,
    "CLIENT_APPROVED": 80,
    "APPROVED": 80,
    "OPERATIONAL": 50,
    "OPERATIONAL_UI": 40,
    "HISTORICAL": 20,
    "INFERENCE": 0,
}

# Lanes that do not conflict with each other (Habitat Manrope vs Inter class).
DISTINCT_LANES = frozenset({"brand_identity", "ui_chrome"})

HONESTY = {
    "authorised_knowledge_resolver": "BUILT",
    "llm_invent": False,
    "memory_items_auto_promote": False,
    "crawl": False,
    "max_sources_per_resolve": MAX_SOURCES_PER_RESOLVE,
    "max_bytes_per_source": MAX_BYTES_PER_SOURCE,
}


class AuthorisedKnowledgeError(ValueError):
    """Fail-closed resolver input error."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


@dataclass
class Attempt:
    step: str
    detail: str
    source_id: str | None = None
    ok: bool = True

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"step": self.step, "detail": self.detail, "ok": self.ok}
        if self.source_id is not None:
            d["source_id"] = self.source_id
        return d


@dataclass
class FactHit:
    source_id: str
    question_key: str
    value: Any
    authority: str
    freshness: str | None
    lane: str
    identity: dict[str, Any]
    path: str | None = None
    bytes_read: int = 0
    page: int | None = None
    sha256: str | None = None
    kind: str | None = None

    @property
    def rank(self) -> int:
        return AUTHORITY_RANK.get(self.authority, 0)

    def as_provenance(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "source_id": self.source_id,
            "authority": self.authority,
            "authority_rank": self.rank,
            "freshness": self.freshness,
            "lane": self.lane,
            "path": self.path,
            "value": self.value,
            "identity": dict(self.identity),
            "bytes_read": self.bytes_read,
            "canonical": self.authority == "CANONICAL",
            "authoritative": self.rank >= AUTHORITY_RANK["APPROVED"],
        }
        if self.page is not None:
            d["page"] = self.page
        if self.sha256 is not None:
            d["sha256"] = self.sha256
        if self.kind is not None:
            d["kind"] = self.kind
        return d


@dataclass
class ResolveResult:
    status: str | None
    answer: dict[str, Any] | None
    provenance: list[dict[str, Any]] = field(default_factory=list)
    confidence: str = "none"
    attempt_log: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    scope: dict[str, Any] = field(default_factory=dict)
    question_key: str = ""
    caps: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "answer": self.answer,
            "provenance": list(self.provenance),
            "confidence": self.confidence,
            "attempt_log": list(self.attempt_log),
            "conflicts": list(self.conflicts),
            "scope": dict(self.scope),
            "question_key": self.question_key,
            "caps": dict(self.caps),
            "honesty": dict(HONESTY),
            "resolved": self.answer is not None and self.status != STATUS_CONFLICTED,
        }


def normalize_scope(scope: str | dict[str, Any] | None) -> dict[str, Any]:
    """Normalize entity/brand/object scope. Accepts 'brand:habitat' or dict."""
    if scope is None:
        return {"entity": None, "brand": None, "object": None, "raw": None}
    if isinstance(scope, str):
        raw = scope.strip()
        out: dict[str, Any] = {"entity": None, "brand": None, "object": None, "raw": raw}
        if ":" in raw:
            kind, _, rest = raw.partition(":")
            kind = kind.strip().lower()
            rest = rest.strip().lower()
            if kind in ("entity", "brand", "object"):
                out[kind] = rest
            else:
                out["brand"] = raw.lower()
        else:
            out["brand"] = raw.lower()
        return out
    if not isinstance(scope, dict):
        raise AuthorisedKnowledgeError("scope must be str or dict", code="bad_scope")
    return {
        "entity": _norm_id(scope.get("entity")),
        "brand": _norm_id(scope.get("brand")),
        "object": _norm_id(scope.get("object")),
        "raw": scope.get("raw"),
    }


def _norm_id(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().lower()
    return s or None


def _scope_matches(scope: dict[str, Any], source: dict[str, Any]) -> bool:
    """Source allowlisted for this scope if any declared scope tag matches."""
    tags = source.get("scopes") or source.get("scope_tags") or []
    if not tags:
        return False
    brand = scope.get("brand")
    entity = scope.get("entity")
    obj = scope.get("object")
    for tag in tags:
        t = str(tag).strip().lower()
        if brand and t in (f"brand:{brand}", brand):
            return True
        if entity and t in (f"entity:{entity}", entity):
            return True
        if obj and t in (f"object:{obj}", obj):
            return True
        # wildcard allowlist for tests / shared wolf chrome
        if t in ("*", "any"):
            return True
    return False


def _question_matches(question_key: str, source: dict[str, Any]) -> bool:
    keys = source.get("question_keys") or source.get("fields") or []
    q = question_key.strip().lower()
    return any(str(k).strip().lower() == q for k in keys)


def _canonical_value(canonical: dict[str, Any] | None, question_key: str) -> Any:
    if not canonical:
        return None
    # Support nested {"fields": {...}} or flat dict
    fields = canonical.get("fields") if isinstance(canonical.get("fields"), dict) else canonical
    if question_key in fields:
        return fields[question_key]
    # empty-string / null field is EMPTY, not missing-key
    return fields.get(question_key, _SENTINEL)


_SENTINEL = object()


def _is_empty_field(value: Any) -> bool:
    if value is _SENTINEL:
        return True  # treated as absent key → continue search (not UNKNOWN)
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _load_registry(
    sources_registry: list[dict[str, Any]] | Path | str,
) -> list[dict[str, Any]]:
    sources, _roots = _load_registry_bundle(sources_registry)
    return sources


def _load_registry_bundle(
    sources_registry: list[dict[str, Any]] | Path | str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (sources, allowlisted_roots). Roots empty ⇒ no path-root gate (fixture mode)."""
    if isinstance(sources_registry, (str, Path)):
        path = Path(sources_registry)
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict) and "sources" in data:
            roots = data.get("allowlisted_roots") or data.get("allowlist_roots") or []
            return list(data["sources"]), [str(r) for r in roots]
        if isinstance(data, list):
            return list(data), []
        raise AuthorisedKnowledgeError("registry JSON must be list or {sources: [...]}")
    if isinstance(sources_registry, dict) and "sources" in sources_registry:
        roots = sources_registry.get("allowlisted_roots") or sources_registry.get(
            "allowlist_roots"
        ) or []
        return list(sources_registry["sources"]), [str(r) for r in roots]
    if not isinstance(sources_registry, list):
        raise AuthorisedKnowledgeError("sources_registry must be list or path")
    return list(sources_registry), []


def _resolve_source_path(source: dict[str, Any], fixture_root: Path | None) -> Path | None:
    rel = source.get("path") or source.get("fixture_path")
    if not rel:
        return None
    p = Path(str(rel))
    if p.is_absolute():
        return p
    if fixture_root is not None:
        return (fixture_root / p).resolve()
    return p.resolve()


def _raw_path_has_dotdot(raw: str | Path) -> bool:
    """Fail closed on '..' path segments before normalisation."""
    return any(part == ".." for part in Path(str(raw)).parts)


def _path_in_allowlist(path: Path, allowlisted_roots: list[str]) -> bool:
    """True if path is under an allowlisted directory root or equals an allowlisted file."""
    if not allowlisted_roots:
        return True
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in allowlisted_roots:
        root_p = Path(root)
        try:
            root_res = root_p.resolve()
        except OSError:
            continue
        if root_res.is_file() or (not root_res.exists() and root_p.suffix):
            # Single-file allowlist entry (e.g. phase26_team.py)
            if resolved == root_res:
                return True
            continue
        try:
            resolved.relative_to(root_res)
            return True
        except ValueError:
            continue
    return False


def _source_type(source: dict[str, Any], path: Path | None) -> str:
    explicit = source.get("type")
    if explicit:
        return str(explicit).strip().lower()
    if path is None:
        return "json"
    suf = path.suffix.lower().lstrip(".")
    if suf in ("md", "markdown"):
        return "markdown"
    if suf in ("py",):
        return "python"
    if suf in ("pdf",):
        return "pdf"
    if suf in ("json",):
        return "json"
    if suf in ("txt", "text"):
        return "text"
    return suf or "json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _read_text_capped(path: Path, max_bytes: int) -> tuple[str, int, bool]:
    """Read up to max_bytes of UTF-8 text. Returns (text, bytes_read, truncated)."""
    raw = path.read_bytes()
    truncated = len(raw) > max_bytes
    chunk = raw[:max_bytes]
    # Avoid splitting a multibyte char at the end
    text = chunk.decode("utf-8", errors="replace")
    return text, len(chunk), truncated


def _extract_question_from_text(
    question_key: str, text: str, *, source_type: str
) -> tuple[Any, str | None, int | None] | None:
    """Return (value, short_passage, page) or None. Never invents facts."""
    q = question_key.strip().lower()
    pages = text.split("\f")
    for page_idx, page_text in enumerate(pages):
        page_num = page_idx + 1 if source_type == "pdf" else None
        hit = _extract_question_from_page(q, page_text, source_type=source_type)
        if hit is not None:
            value, passage = hit
            return value, passage, page_num
    return None


def _short_passage(text: str, needle: str, *, radius: int = 120) -> str:
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return text[: min(len(text), radius * 2)].strip()
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    snippet = text[start:end].strip()
    snippet = re.sub(r"\s+", " ", snippet)
    return snippet[:280]


def _extract_question_from_page(
    q: str, text: str, *, source_type: str
) -> tuple[Any, str] | None:
    if q in ("brand_font", "font", "typography", "typeface"):
        if re.search(r"\bManrope\b", text):
            # Prefer labelled brand-font lines when present
            labelled = re.search(
                r"(?:Brand font|Primary Typeface)[:\s|*]*\b(Manrope)\b",
                text,
                re.IGNORECASE,
            )
            if labelled:
                return "Manrope", _short_passage(text, labelled.group(0))
            return "Manrope", _short_passage(text, "Manrope")
        return None

    if q in ("ui_font", "ui_typeface", "chrome_font"):
        m = re.search(
            r'_SHARED_FONT\s*=\s*"(Inter[^"]*)"',
            text,
        )
        if m:
            return "Inter", m.group(0)[:200]
        if re.search(r"\bInter\b", text) and source_type in ("python", "py", "text"):
            return "Inter", _short_passage(text, "Inter")
        return None

    if q == "brand_voice":
        # Evidence passage only — no interpretation field.
        m = re.search(
            r"(##\s*ESSENCE\s*&\s*VOICE\b.*?)(?=\n##\s|\n---\s*\n|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            passage = m.group(1).strip()
            # Bound the evidence blob
            if len(passage) > 600:
                passage = passage[:600].rstrip() + "…"
            return passage, passage
        # Fallback: Voice Descriptors block
        m2 = re.search(
            r"(\*\*Voice Descriptors:\*\*.*?)(?=\n\*\*|\n##|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if m2:
            passage = m2.group(1).strip()
            if len(passage) > 400:
                passage = passage[:400].rstrip() + "…"
            return passage, passage
        return None

    if q == "headline_case":
        if re.search(r"lowercase-only", text, re.IGNORECASE):
            return "lowercase", _short_passage(text, "lowercase-only")
        if re.search(
            r"uppercase\s+(?:Manrope\s+)?(?:ExtraBold\s+)?headlines|"
            r"bold\s+\*\*uppercase|"
            r"uppercase\s+headlines",
            text,
            re.IGNORECASE,
        ):
            return "UPPERCASE", _short_passage(text, "uppercase")
        return None

    # Direct JSON-ish key: "question_key": "value" in free text — not used for live prove
    return None


def _retrieve_pdf(
    path: Path,
    *,
    sid: str,
    max_bytes: int,
    attempts: list[Attempt],
) -> tuple[dict[str, Any] | None, str | None]:
    if not PDFTOTEXT_BIN.is_file():
        attempts.append(
            Attempt(
                "RETRIEVE",
                f"pdftotext missing at {PDFTOTEXT_BIN}",
                source_id=sid,
                ok=False,
            )
        )
        return None, STATUS_INACCESSIBLE
    try:
        digest = _sha256_file(path)
    except OSError as exc:
        attempts.append(
            Attempt("RETRIEVE", f"sha256 failed: {exc}", source_id=sid, ok=False)
        )
        return None, STATUS_INACCESSIBLE
    try:
        proc = subprocess.run(
            [str(PDFTOTEXT_BIN), "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        attempts.append(
            Attempt("RETRIEVE", f"pdftotext failed: {exc}", source_id=sid, ok=False)
        )
        return None, STATUS_INACCESSIBLE
    if proc.returncode != 0:
        attempts.append(
            Attempt(
                "RETRIEVE",
                f"pdftotext exit={proc.returncode}",
                source_id=sid,
                ok=False,
            )
        )
        return None, STATUS_INACCESSIBLE
    raw = proc.stdout or b""
    truncated = len(raw) > max_bytes
    capped = raw[:max_bytes]
    text = capped.decode("utf-8", errors="replace")
    attempts.append(
        Attempt(
            "RETRIEVE",
            f"pdf text bytes={len(capped)} truncated={truncated} pages≈{text.count(chr(12)) + 1}",
            source_id=sid,
            ok=True,
        )
    )
    return {
        "text": text,
        "bytes_read": len(capped),
        "path": str(path),
        "sha256": digest,
        "source_type": "pdf",
        "truncated": truncated,
    }, None


def _retrieve_source(
    source: dict[str, Any],
    *,
    fixture_root: Path | None,
    max_bytes: int,
    attempts: list[Attempt],
    allowlisted_roots: list[str] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (payload, error_status). error_status is INACCESSIBLE or size skip."""
    sid = str(source.get("source_id") or source.get("id") or "?")
    roots = allowlisted_roots or []

    # Dynamic accessibility: missing file on disk → INACCESSIBLE
    if source.get("accessible") is False:
        attempts.append(
            Attempt("RETRIEVE", "source marked inaccessible", source_id=sid, ok=False)
        )
        return None, STATUS_INACCESSIBLE
    if (source.get("authority") or "").upper() == "INFERENCE":
        attempts.append(
            Attempt("RETRIEVE", "INFERENCE rejected (AI ≠ evidence)", source_id=sid, ok=False)
        )
        return None, None

    # Inline facts (unit tests / registry-embedded) — still bounded
    if "facts" in source and isinstance(source["facts"], dict):
        blob = json.dumps(source["facts"], ensure_ascii=False).encode("utf-8")
        if len(blob) > max_bytes:
            attempts.append(
                Attempt(
                    "RETRIEVE",
                    f"inline facts exceed max_bytes={max_bytes}",
                    source_id=sid,
                    ok=False,
                )
            )
            return None, None
        attempts.append(
            Attempt("RETRIEVE", f"inline facts bytes={len(blob)}", source_id=sid, ok=True)
        )
        return {
            "facts": dict(source["facts"]),
            "bytes_read": len(blob),
            "path": None,
        }, None

    raw_path = source.get("path") or source.get("fixture_path")
    if raw_path and _raw_path_has_dotdot(raw_path):
        attempts.append(
            Attempt(
                "RETRIEVE",
                "path contains '..' — fail closed",
                source_id=sid,
                ok=False,
            )
        )
        return None, STATUS_INACCESSIBLE

    path = _resolve_source_path(source, fixture_root)
    if path is None:
        attempts.append(Attempt("RETRIEVE", "no path and no inline facts", source_id=sid, ok=False))
        return None, STATUS_INACCESSIBLE

    # Allowlist gate for absolute / live paths (fixture relative paths skip when roots empty)
    if roots:
        if not _path_in_allowlist(path, roots):
            attempts.append(
                Attempt(
                    "RETRIEVE",
                    "path outside allowlisted roots",
                    source_id=sid,
                    ok=False,
                )
            )
            return None, STATUS_INACCESSIBLE

    stype = _source_type(source, path)
    if stype not in SUPPORTED_SOURCE_TYPES:
        attempts.append(
            Attempt(
                "RETRIEVE",
                f"unsupported type={stype}",
                source_id=sid,
                ok=False,
            )
        )
        return None, STATUS_INACCESSIBLE

    if not path.exists() or not path.is_file():
        attempts.append(
            Attempt("RETRIEVE", f"path missing or not file: {path.name}", source_id=sid, ok=False)
        )
        return None, STATUS_INACCESSIBLE

    # PDF: binary size is not the ingested text size — extract via pdftotext, then cap.
    if stype == "pdf":
        return _retrieve_pdf(path, sid=sid, max_bytes=max_bytes, attempts=attempts)

    # Markdown / python / text — bounded read (do not fully ingest oversize)
    if stype in ("markdown", "md", "python", "py", "text", "txt"):
        try:
            text, nbytes, truncated = _read_text_capped(path, max_bytes)
        except OSError as exc:
            attempts.append(
                Attempt("RETRIEVE", f"read failed: {exc}", source_id=sid, ok=False)
            )
            return None, STATUS_INACCESSIBLE
        attempts.append(
            Attempt(
                "RETRIEVE",
                f"text read bytes={nbytes} truncated={truncated} path={path.name}",
                source_id=sid,
                ok=True,
            )
        )
        return {
            "text": text,
            "bytes_read": nbytes,
            "path": str(path),
            "source_type": stype,
            "truncated": truncated,
        }, None

    # JSON / fixture path (legacy) — reject whole file if over cap (existing behaviour)
    size = path.stat().st_size
    if size > max_bytes:
        attempts.append(
            Attempt(
                "RETRIEVE",
                f"source exceeds max_bytes={max_bytes} (size={size})",
                source_id=sid,
                ok=False,
            )
        )
        return None, None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        attempts.append(
            Attempt("RETRIEVE", f"read failed: {exc}", source_id=sid, ok=False)
        )
        return None, STATUS_INACCESSIBLE
    raw = text.encode("utf-8")
    if len(raw) > max_bytes:
        attempts.append(
            Attempt("RETRIEVE", f"decoded bytes exceed cap", source_id=sid, ok=False)
        )
        return None, None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Plain text: treat whole body as opaque note under "text"
        data = {"facts": {"_text": text[:max_bytes]}}
    if isinstance(data, dict) and "facts" not in data:
        # Allow flat JSON as facts
        if any(k in data for k in ("brand_font", "ui_font", "font", "value")):
            data = {"facts": data}
        else:
            data = {"facts": data}
    facts = data.get("facts") if isinstance(data, dict) else None
    if not isinstance(facts, dict):
        attempts.append(Attempt("RETRIEVE", "no facts object", source_id=sid, ok=False))
        return None, None
    attempts.append(
        Attempt("RETRIEVE", f"read ok bytes={len(raw)} path={path.name}", source_id=sid, ok=True)
    )
    return {"facts": facts, "bytes_read": len(raw), "path": str(path)}, None


def _extract_hits(
    source: dict[str, Any],
    payload: dict[str, Any],
    question_key: str,
    scope: dict[str, Any],
) -> list[FactHit]:
    sid = str(source.get("source_id") or source.get("id") or "?")
    authority = str(source.get("authority") or "OPERATIONAL").upper()
    freshness = source.get("freshness") or source.get("mtime") or source.get("version")
    lane = str(source.get("lane") or source.get("scope_lane") or "general").strip().lower()
    identity = dict(source.get("identity") or {})
    if scope.get("brand") and "brand" not in identity:
        identity["brand"] = scope["brand"]
    hits: list[FactHit] = []

    # Live text / PDF payload — extract only the registered question
    if "text" in payload and isinstance(payload.get("text"), str):
        stype = str(payload.get("source_type") or source.get("type") or "text")
        extracted = _extract_question_from_text(
            question_key, payload["text"], source_type=stype
        )
        if extracted is None:
            return hits
        value, _passage, page = extracted
        kind = "EVIDENCE" if question_key.strip().lower() == "brand_voice" else None
        hits.append(
            FactHit(
                source_id=sid,
                question_key=question_key,
                value=value,
                authority=authority,
                freshness=str(freshness) if freshness is not None else None,
                lane=lane,
                identity=identity,
                path=payload.get("path"),
                bytes_read=int(payload.get("bytes_read") or 0),
                page=page,
                sha256=payload.get("sha256"),
                kind=kind,
            )
        )
        return hits

    facts = payload.get("facts")
    if not isinstance(facts, dict):
        return hits
    # Direct key
    if question_key in facts and not _is_empty_field(facts[question_key]):
        hits.append(
            FactHit(
                source_id=sid,
                question_key=question_key,
                value=facts[question_key],
                authority=authority,
                freshness=str(freshness) if freshness is not None else None,
                lane=lane,
                identity=identity,
                path=payload.get("path"),
                bytes_read=int(payload.get("bytes_read") or 0),
            )
        )
    # Aliases for typography / font questions
    aliases = {
        "brand_font": ("font", "typeface", "brand_typeface"),
        "ui_font": ("ui_typeface", "chrome_font"),
        "typography": ("brand_font", "font", "typeface"),
        "font": ("brand_font", "typeface"),
    }
    for alt in aliases.get(question_key, ()):
        if alt in facts and not _is_empty_field(facts[alt]):
            hits.append(
                FactHit(
                    source_id=sid,
                    question_key=question_key,
                    value=facts[alt],
                    authority=authority,
                    freshness=str(freshness) if freshness is not None else None,
                    lane=lane,
                    identity=identity,
                    path=payload.get("path"),
                    bytes_read=int(payload.get("bytes_read") or 0),
                )
            )
    return hits


def _freshness_key(f: str | None) -> str:
    return f or ""


def _pick_winner(hits: list[FactHit]) -> FactHit | None:
    if not hits:
        return None
    return sorted(
        hits,
        key=lambda h: (h.rank, _freshness_key(h.freshness), h.source_id),
        reverse=True,
    )[0]


def _group_by_lane(hits: list[FactHit]) -> dict[str, list[FactHit]]:
    groups: dict[str, list[FactHit]] = {}
    for h in hits:
        groups.setdefault(h.lane, []).append(h)
    return groups


def _values_disagree(hits: list[FactHit]) -> bool:
    vals = {json.dumps(h.value, sort_keys=True, default=str) for h in hits}
    return len(vals) > 1


def _lane_conflict_resolvable(hits: list[FactHit]) -> FactHit | None:
    """Resolve within one lane by authority then freshness; else None."""
    if not hits:
        return None
    if not _values_disagree(hits):
        return _pick_winner(hits)
    ranked = sorted(
        hits,
        key=lambda h: (h.rank, _freshness_key(h.freshness), h.source_id),
        reverse=True,
    )
    top = ranked[0]
    # Strict: only win if strictly higher authority than every disagreeing peer
    for other in ranked[1:]:
        if json.dumps(other.value, sort_keys=True, default=str) == json.dumps(
            top.value, sort_keys=True, default=str
        ):
            continue
        if other.rank >= top.rank:
            return None  # tie or peer authority → CONFLICTED
    return top


def resolve(
    scope: str | dict[str, Any] | None,
    question_key: str,
    sources_registry: list[dict[str, Any]] | Path | str,
    *,
    canonical: dict[str, Any] | None = None,
    fixture_root: Path | str | None = None,
    max_sources: int = MAX_SOURCES_PER_RESOLVE,
    max_bytes_per_source: int = MAX_BYTES_PER_SOURCE,
) -> dict[str, Any]:
    """Resolve question_key for scope against allowlisted sources.

    Returns a dict with status vocabulary (or null status when safely answered
    from canonical), answer, provenance, confidence, attempt_log, conflicts.
    """
    q = (question_key or "").strip()
    if not q:
        raise AuthorisedKnowledgeError("question_key required", code="bad_question")
    if max_sources < 1 or max_sources > MAX_SOURCES_PER_RESOLVE:
        # Cap hard at module max (anti-crawl); allow lower for tests
        if max_sources > MAX_SOURCES_PER_RESOLVE:
            max_sources = MAX_SOURCES_PER_RESOLVE
        if max_sources < 1:
            raise AuthorisedKnowledgeError("max_sources must be >= 1")
    if max_bytes_per_source < 1 or max_bytes_per_source > MAX_BYTES_PER_SOURCE:
        if max_bytes_per_source > MAX_BYTES_PER_SOURCE:
            max_bytes_per_source = MAX_BYTES_PER_SOURCE
        if max_bytes_per_source < 1:
            raise AuthorisedKnowledgeError("max_bytes_per_source must be >= 1")

    attempts: list[Attempt] = []
    norm = normalize_scope(scope)
    attempts.append(Attempt("SCOPE", f"normalized={norm}"))

    root = Path(fixture_root).resolve() if fixture_root else None
    registry, allowlisted_roots = _load_registry_bundle(sources_registry)
    attempts.append(
        Attempt(
            "DISCOVER",
            f"registry_size={len(registry)} allowlisted_roots={len(allowlisted_roots)}",
        )
    )

    caps = {
        "max_sources": max_sources,
        "max_bytes_per_source": max_bytes_per_source,
        "module_max_sources": MAX_SOURCES_PER_RESOLVE,
        "module_max_bytes": MAX_BYTES_PER_SOURCE,
        "sources_matched": 0,
        "sources_retrieved": 0,
        "sources_skipped_cap": 0,
    }

    # --- CANONICAL check -----------------------------------------------------
    canon_val = _canonical_value(canonical, q)
    attempts.append(
        Attempt(
            "CANONICAL",
            "empty"
            if _is_empty_field(canon_val)
            else ("present" if canon_val is not _SENTINEL else "absent_key"),
        )
    )
    if canon_val is not _SENTINEL and not _is_empty_field(canon_val):
        hit = FactHit(
            source_id="canonical",
            question_key=q,
            value=canon_val,
            authority="CANONICAL",
            freshness=None,
            lane="canonical",
            identity={"brand": norm.get("brand")},
        )
        result = ResolveResult(
            status=None,
            answer={
                "question_key": q,
                "value": canon_val,
                "canonical": True,
                "resolution": "canonical",
            },
            provenance=[hit.as_provenance()],
            confidence="high",
            attempt_log=[a.as_dict() for a in attempts],
            scope=norm,
            question_key=q,
            caps=caps,
        )
        return result.as_dict()

    # Empty canonical field → continue; do NOT return UNKNOWN
    if canon_val is not _SENTINEL and _is_empty_field(canon_val):
        attempts.append(
            Attempt(
                "CANONICAL",
                "EMPTY FIELD ≠ UNKNOWN; continuing authorised search",
                ok=True,
            )
        )

    # --- DISCOVER allowlisted -----------------------------------------------
    matched: list[dict[str, Any]] = []
    for src in registry:
        sid = str(src.get("source_id") or src.get("id") or "?")
        if not _scope_matches(norm, src):
            attempts.append(
                Attempt(
                    "DISCOVER",
                    "skipped: scope mismatch",
                    source_id=sid,
                    ok=False,
                )
            )
            continue
        if not _question_matches(q, src):
            attempts.append(
                Attempt(
                    "DISCOVER",
                    "skipped: question_key not listed",
                    source_id=sid,
                    ok=False,
                )
            )
            continue
        matched.append(src)
    caps["sources_matched"] = len(matched)
    attempts.append(Attempt("DISCOVER", f"matched={len(matched)} for question={q}"))

    if len(matched) > max_sources:
        caps["sources_skipped_cap"] = len(matched) - max_sources
        attempts.append(
            Attempt(
                "DISCOVER",
                f"capped to {max_sources} (skipped {caps['sources_skipped_cap']})",
                ok=True,
            )
        )
        matched = matched[:max_sources]

    # --- RETRIEVE + extract --------------------------------------------------
    hits: list[FactHit] = []
    inaccessible_ids: list[str] = []
    any_retrieve_attempt = False

    for src in matched:
        any_retrieve_attempt = True
        payload, err = _retrieve_source(
            src,
            fixture_root=root,
            max_bytes=max_bytes_per_source,
            attempts=attempts,
            allowlisted_roots=allowlisted_roots,
        )
        sid = str(src.get("source_id") or src.get("id") or "?")
        if err == STATUS_INACCESSIBLE:
            inaccessible_ids.append(sid)
            continue
        if payload is None:
            continue
        caps["sources_retrieved"] += 1
        # IDENTITY / RECONCILE: brand mismatch → skip
        identity = dict(src.get("identity") or {})
        src_brand = _norm_id(identity.get("brand"))
        if src_brand and norm.get("brand") and src_brand != norm["brand"]:
            attempts.append(
                Attempt(
                    "IDENTITY",
                    f"brand mismatch source={src_brand} scope={norm['brand']}",
                    source_id=sid,
                    ok=False,
                )
            )
            continue
        attempts.append(Attempt("IDENTITY", "identity ok", source_id=sid))
        authority = str(src.get("authority") or "OPERATIONAL").upper()
        attempts.append(
            Attempt("AUTHORITY", f"class={authority} rank={AUTHORITY_RANK.get(authority, 0)}", source_id=sid)
        )
        extracted = _extract_hits(src, payload, q, norm)
        if not extracted:
            attempts.append(
                Attempt("RETRIEVE", "no fact for question_key", source_id=sid, ok=False)
            )
        hits.extend(extracted)

    attempts.append(Attempt("FRESHNESS", f"hits={len(hits)}"))

    # --- No hits -------------------------------------------------------------
    if not hits:
        log = [a.as_dict() for a in attempts]
        if inaccessible_ids and matched and len(inaccessible_ids) == len(matched):
            # Potentially relevant sources exist but none readable
            return ResolveResult(
                status=STATUS_INACCESSIBLE,
                answer=None,
                confidence="none",
                attempt_log=log,
                scope=norm,
                question_key=q,
                caps=caps,
                provenance=[
                    {"source_id": sid, "status": STATUS_INACCESSIBLE}
                    for sid in inaccessible_ids
                ],
            ).as_dict()
        if any_retrieve_attempt or matched:
            # Allowlisted sources considered; nothing relevant extracted
            return ResolveResult(
                status=STATUS_NOT_FOUND,
                answer=None,
                confidence="none",
                attempt_log=log,
                scope=norm,
                question_key=q,
                caps=caps,
            ).as_dict()
        # Discovery against a non-empty registry found no question match → NOT FOUND
        if registry:
            attempts.append(
                Attempt(
                    "DISCOVER",
                    "no allowlisted source claims this question_key; nothing relevant",
                    ok=True,
                )
            )
            return ResolveResult(
                status=STATUS_NOT_FOUND,
                answer=None,
                confidence="none",
                attempt_log=[a.as_dict() for a in attempts],
                scope=norm,
                question_key=q,
                caps=caps,
            ).as_dict()
        # Empty allowlist — cannot search; UNKNOWN requires this attempt evidence
        attempts.append(
            Attempt(
                "UNKNOWN",
                "no allowlisted sources for scope/question; search evidence logged",
                ok=False,
            )
        )
        return ResolveResult(
            status=STATUS_UNKNOWN,
            answer=None,
            confidence="none",
            attempt_log=[a.as_dict() for a in attempts],
            scope=norm,
            question_key=q,
            caps=caps,
        ).as_dict()

    # --- CONFLICTS / scoped resolution --------------------------------------
    by_lane = _group_by_lane(hits)
    lane_answers: dict[str, FactHit] = {}
    conflict_payloads: list[dict[str, Any]] = []

    for lane, lane_hits in by_lane.items():
        attempts.append(
            Attempt("CONFLICTS", f"lane={lane} n={len(lane_hits)}", ok=True)
        )
        winner = _lane_conflict_resolvable(lane_hits)
        if winner is None:
            conflict_payloads.append(
                {
                    "lane": lane,
                    "values": [
                        {"source_id": h.source_id, "value": h.value, "authority": h.authority}
                        for h in lane_hits
                    ],
                }
            )
        else:
            lane_answers[lane] = winner

    # Same-lane unresolvable conflict → CONFLICTED (even if other lanes ok)
    if conflict_payloads:
        return ResolveResult(
            status=STATUS_CONFLICTED,
            answer=None,
            provenance=[h.as_provenance() for h in hits],
            confidence="low",
            attempt_log=[a.as_dict() for a in attempts],
            conflicts=conflict_payloads,
            scope=norm,
            question_key=q,
            caps=caps,
        ).as_dict()

    # Distinct lanes (brand_identity vs ui_chrome) → scoped resolution
    lanes = set(lane_answers.keys())
    scoped_ok = (
        ("brand_identity" in lane_answers and "ui_chrome" in lane_answers)
        or (len(lane_answers) > 1 and lanes <= DISTINCT_LANES)
    )
    if scoped_ok:
        brand_hit = lane_answers.get("brand_identity")
        ui_hit = lane_answers.get("ui_chrome")
        answer: dict[str, Any] = {
            "question_key": q,
            "canonical": False,
            "resolution": "scoped",
            "note": "Distinct lanes: brand_identity vs ui_chrome — not a brand conflict",
        }
        if brand_hit:
            answer["brand_font"] = brand_hit.value
            answer["value"] = brand_hit.value  # primary brand answer
        if ui_hit:
            answer["ui_font"] = ui_hit.value
        prov = [h.as_provenance() for h in lane_answers.values()]
        return ResolveResult(
            status=STATUS_NOT_CANONICAL,
            answer=answer,
            provenance=prov,
            confidence="high",
            attempt_log=[a.as_dict() for a in attempts],
            scope=norm,
            question_key=q,
            caps=caps,
        ).as_dict()

    # Single-lane (or general) answer from non-canonical sources
    winner = next(iter(lane_answers.values()))
    answer_obj: dict[str, Any] = {
        "question_key": q,
        "value": winner.value,
        "canonical": False,
        "resolution": "authorised_source",
        "lane": winner.lane,
    }
    if winner.kind:
        answer_obj["kind"] = winner.kind
    elif q.strip().lower() == "brand_voice":
        answer_obj["kind"] = "EVIDENCE"
    return ResolveResult(
        status=STATUS_NOT_CANONICAL,
        answer=answer_obj,
        provenance=[winner.as_provenance()],
        confidence="high" if winner.rank >= AUTHORITY_RANK["APPROVED"] else "medium",
        attempt_log=[a.as_dict() for a in attempts],
        scope=norm,
        question_key=q,
        caps=caps,
    ).as_dict()


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)
