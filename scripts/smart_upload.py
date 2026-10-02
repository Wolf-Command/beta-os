#!/usr/bin/env python3
"""Phase 2.5B Smart Upload — batch naming + library ingest on beta-os only.

Keeps MIME/staging/path-jail/probe. Never touches wolf-system or :8787.
Never writes Metricool / publish / live AI / semantic match.

CE-CANCEL-UPLOAD-1: Cancel Upload (batch + per-file) + post-upload metadata
correction with audit. Late Cancel never fakes NAS delete.
"""
from __future__ import annotations

import json
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import stage_inspector as _stage_inspector
import wolf_naming as _wn
import phase26_team as _p26
from core import nas_library as _nas

TZ = ZoneInfo("Asia/Makassar")
NAS_PROBE_PATHS = (
    Path("/Volumes/01-Media-Library"),
    Path("/Volumes/01-Media-Library/Brand-Assets"),
)

# Library lifecycle (honest)
LIB_UPLOAD_RECEIVED = "UPLOAD_RECEIVED"
LIB_CHECKING = "CHECKING"
LIB_READY = "LIBRARY_READY"
LIB_FAILED = "FAILED"
LIB_CANCELLED = "CANCELLED"

# UI upload row statuses
UI_UPLOADING = "UPLOADING"
UI_CHECKING = "CHECKING"
UI_READY = "READY"
UI_FAILED = "FAILED"
UI_CANCELLED = "CANCELLED"

STAFF_CANCELLED = "Upload cancelled."
STAFF_ALREADY_UPLOADED_STOPPED = "File already uploaded. Processing stopped."
CANCEL_CONFIRM = (
    "Cancel remaining uploads?\n"
    "Files already uploaded will stay in the Library."
)

# In-process cancel registry (Beta serve is single-process). Keys: batch_id.
_cancel_lock = threading.Lock()
_batch_cancels: dict[str, dict[str, Any]] = {}

def safe_original_basename(name: str) -> str:
    """Strip path traversal only; keep camera basename (underscores OK).

    Extension lowercased. Never treat as canonical Wolf name.
    """
    raw = Path(name or "upload").name
    raw = raw.replace(chr(92), "/").split("/")[-1]
    raw = raw.replace("..", "")
    if not raw or raw in (".", ""):
        return "upload.bin"
    stem = Path(raw).stem or "upload"
    ext = Path(raw).suffix.lower()
    stem = stem.replace(" ", "_")
    stem = "".join(c for c in stem if c.isalnum() or c in ("-", "_", "."))[:120] or "upload"
    return f"{stem}{ext}"


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def nas_status() -> dict[str, Any]:
    """Honest NAS connectivity. Status endpoint never claims a file was received."""
    return _nas.public_nas_status()


def cleanup_temp_partial(path: Path | str | None) -> bool:
    """Remove an incomplete temp upload. Never touches NAS / library_v2 / assets."""
    if not path:
        return False
    try:
        p = Path(path)
        if not p.is_file():
            return False
        # Only allow under incoming_drop-style UUID names (caller jail-checked).
        p.unlink(missing_ok=True)
        return not p.exists()
    except OSError:
        return False


def _normalize_file_key(file_key: str | None) -> str | None:
    if file_key is None:
        return None
    s = str(file_key).strip()
    return s if s else None


def request_batch_cancel(
    batch_id: str,
    *,
    subject: str | None = None,
    file_key: str | None = None,
) -> dict[str, Any]:
    """Mark a batch (or one file in a batch) cancelled. Idempotent."""
    bid = (batch_id or "").strip()
    if not bid:
        return {"ok": False, "error": "batch_id required", "http": 400}
    fk = _normalize_file_key(file_key)
    with _cancel_lock:
        row = _batch_cancels.setdefault(
            bid,
            {
                "batch_id": bid,
                "cancelled_at": now_iso(),
                "subject": subject,
                "batch": False,
                "files": set(),
            },
        )
        if fk:
            row["files"].add(fk)
        else:
            row["batch"] = True
            row["cancelled_at"] = now_iso()
            if subject:
                row["subject"] = subject
        files = sorted(row["files"])
        batch_flag = bool(row["batch"])
    return {
        "ok": True,
        "batch_id": bid,
        "batch_cancelled": batch_flag,
        "cancelled_files": files,
        "confirm_copy": CANCEL_CONFIRM,
        "staff_ready": False,
    }


def clear_batch_cancel(batch_id: str) -> None:
    """Test/helper: drop cancel flag for a batch."""
    bid = (batch_id or "").strip()
    with _cancel_lock:
        _batch_cancels.pop(bid, None)


def is_cancelled(batch_id: str | None, file_key: str | None = None) -> bool:
    bid = (batch_id or "").strip()
    if not bid:
        return False
    fk = _normalize_file_key(file_key)
    with _cancel_lock:
        row = _batch_cancels.get(bid)
        if not row:
            return False
        if row.get("batch"):
            return True
        if fk and fk in row.get("files", set()):
            return True
        return False


def cancel_status(batch_id: str) -> dict[str, Any]:
    bid = (batch_id or "").strip()
    with _cancel_lock:
        row = _batch_cancels.get(bid)
        if not row:
            return {"ok": True, "batch_id": bid, "batch_cancelled": False, "cancelled_files": []}
        return {
            "ok": True,
            "batch_id": bid,
            "batch_cancelled": bool(row.get("batch")),
            "cancelled_files": sorted(row.get("files") or []),
            "cancelled_at": row.get("cancelled_at"),
            "subject": row.get("subject"),
        }


def cancelled_response(
    *,
    original_filename: str | None = None,
    batch_id: str | None = None,
    phase: str = "before_storage",
) -> dict[str, Any]:
    """Honest CANCELLED body — never claims READY / library available."""
    return {
        "ok": False,
        "status": "cancelled",
        "ui_status": UI_CANCELLED,
        "library_status": LIB_CANCELLED,
        "processing_status": LIB_CANCELLED,
        "cancelled": True,
        "cancel_phase": phase,
        "library_available": False,
        "nas_received": False,
        "upload_failed": False,
        "original_filename": original_filename,
        "batch_id": batch_id,
        "staff_message": STAFF_CANCELLED,
        "staff_ready": False,
    }


def late_cancel_annotate(body: dict[str, Any]) -> dict[str, Any]:
    """After commit: do not fake CANCELLED. Keep asset; stop further processing copy."""
    out = dict(body)
    out["already_uploaded_processing_stopped"] = True
    out["cancelled"] = False
    out["ui_status"] = UI_READY if out.get("library_available") else out.get("ui_status")
    out["staff_message"] = STAFF_ALREADY_UPLOADED_STOPPED
    out["staff_ready"] = False
    return out


def format_batch_cancel_summary(
    *,
    uploaded: int = 0,
    stopped_during: int = 0,
    cancelled_before: int = 0,
    failed: int = 0,
) -> str:
    """Human batch outcome — never bare 'Cancelled'."""
    parts = [f"{int(uploaded)} uploaded"]
    if stopped_during:
        parts.append(f"{int(stopped_during)} stopped during processing")
    if cancelled_before:
        parts.append(f"{int(cancelled_before)} cancelled before upload")
    if failed:
        parts.append(f"{int(failed)} failed")
    return " · ".join(parts)


def correct_asset_metadata(
    serve_mod: Any,
    asset_id: int,
    patch: dict[str, Any],
    *,
    subject: str,
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    """Correct brand/stage/content type/subject/location/details without re-upload.

    Updates the assets index + audit trail. Does not delete or re-copy NAS bytes.
    """
    from core import content_engine_repair as _ce_repair

    if not asset_id:
        return {"http": 400, "body": {"ok": False, "error": "asset_id required"}}
    allowed = {
        "brand",
        "stage",
        "content_class",
        "content_type",
        "subject",
        "location",
        "detail",
        "details",
    }
    incoming = {k: v for k, v in (patch or {}).items() if k in allowed and v is not None}
    if "content_type" in incoming and "content_class" not in incoming:
        incoming["content_class"] = incoming.pop("content_type")
    if "details" in incoming and "detail" not in incoming:
        incoming["detail"] = incoming.pop("details")
    else:
        incoming.pop("details", None)
        incoming.pop("content_type", None)
    if not incoming:
        return {"http": 400, "body": {"ok": False, "error": "no correctable fields"}}

    conn = serve_mod.db_connect()
    try:
        _nas.migrate_schema(conn)
        row = conn.execute(
            """
            SELECT id, brand, stage, subject, detail, location, media_type, type,
                   original_filename, canonical_filename, filename, provenance_json,
                   library_status, processing_status, nas_path, nas_rel, nas_received,
                   content_hash, file_size, data_lane, batch_id, v2_path
            FROM assets WHERE id=?
            """,
            (int(asset_id),),
        ).fetchone()
        if not row:
            return {"http": 404, "body": {"ok": False, "error": "asset not found"}}
        d = dict(row)
        try:
            prov = json.loads(d.get("provenance_json") or "{}") or {}
        except json.JSONDecodeError:
            prov = {}

        changes: list[dict[str, Any]] = []
        new_brand = d.get("brand")
        new_stage = d.get("stage")
        new_subject = d.get("subject")
        new_detail = d.get("detail")
        new_location = d.get("location")
        new_class = prov.get("content_class") or ""

        if "brand" in incoming:
            try:
                cand = _wn.normalize_brand(str(incoming["brand"]))
            except ValueError as exc:
                return {"http": 400, "body": {"ok": False, "error": str(exc)}}
            if scopes is not None and not _nas.scopes_allow_brand(scopes, cand):
                return {
                    "http": 403,
                    "body": {
                        "ok": False,
                        "error": "forbidden",
                        "message": f"subject lacks scope for brand {cand}",
                    },
                }
            if cand != d.get("brand"):
                changes.append({"field": "brand", "old": d.get("brand"), "new": cand})
                new_brand = cand
        if "stage" in incoming:
            try:
                cand = _wn.normalize_stage(str(incoming["stage"]))
            except ValueError as exc:
                return {"http": 400, "body": {"ok": False, "error": str(exc)}}
            if cand != d.get("stage"):
                changes.append({"field": "stage", "old": d.get("stage"), "new": cand})
                new_stage = cand
        if "subject" in incoming:
            cand = _wn.slug_normalize(str(incoming["subject"]), fallback="subject")
            if cand != (d.get("subject") or ""):
                changes.append({"field": "subject", "old": d.get("subject"), "new": cand})
                new_subject = cand
        if "detail" in incoming:
            raw = str(incoming["detail"]).strip()
            if not _p26.detail_valid(raw):
                return {
                    "http": 400,
                    "body": {"ok": False, "error": "detail required — need ≥1 meaningful slug token"},
                }
            tags = _p26.parse_detail_tags(raw)
            cand = "-".join(tags) if tags else _wn.slug_normalize(raw, fallback="")
            if cand != (d.get("detail") or ""):
                changes.append({"field": "detail", "old": d.get("detail"), "new": cand})
                new_detail = cand
        if "location" in incoming:
            raw_loc = str(incoming["location"]).strip()
            cand = _wn.slug_normalize(raw_loc, fallback="") if raw_loc else ""
            if cand != (d.get("location") or ""):
                changes.append({"field": "location", "old": d.get("location"), "new": cand or None})
                new_location = cand or None
        if "content_class" in incoming:
            cand = str(incoming["content_class"]).strip().lower()
            allowed_classes = {slug for slug, _label in _ce_repair.CONTENT_CLASSES}
            if cand and cand not in allowed_classes:
                return {"http": 400, "body": {"ok": False, "error": f"unknown content_class: {cand}"}}
            if cand != (new_class or ""):
                changes.append({"field": "content_class", "old": new_class or None, "new": cand or None})
                new_class = cand

        if not changes:
            return {
                "http": 200,
                "body": {
                    "ok": True,
                    "asset_id": int(asset_id),
                    "changed": False,
                    "changes": [],
                    "message": "No metadata changes",
                    "staff_ready": False,
                    "reuploaded": False,
                },
            }

        prov["content_class"] = new_class or None
        audit = list(prov.get("metadata_corrections") or [])
        entry = {
            "at": now_iso(),
            "by": subject,
            "changes": changes,
        }
        audit.append(entry)
        prov["metadata_corrections"] = audit[-50:]

        detail_tags = _p26.parse_detail_tags(new_detail) if new_detail else []
        conn.execute(
            """
            UPDATE assets SET
              brand=?, stage=?, subject=?, detail=?, location=?,
              slug=?, detail_tags_json=?, provenance_json=?
            WHERE id=?
            """,
            (
                new_brand,
                new_stage,
                new_subject,
                new_detail,
                new_location,
                new_subject,
                json.dumps(detail_tags),
                json.dumps(prov),
                int(asset_id),
            ),
        )
        conn.commit()
        _ce_repair.log_upload_fault(
            {
                "where": "metadata_correction",
                "kind": "metadata_correction",
                "asset_id": int(asset_id),
                "by": subject,
                "changes": changes,
                "reuploaded": False,
                "nas_deleted": False,
            }
        )
        return {
            "http": 200,
            "body": {
                "ok": True,
                "asset_id": int(asset_id),
                "changed": True,
                "changes": changes,
                "brand": new_brand,
                "stage": new_stage,
                "subject": new_subject,
                "detail": new_detail,
                "location": new_location,
                "content_class": new_class or None,
                "content_class_label": _ce_repair.content_class_label(new_class),
                "audit": entry,
                "reuploaded": False,
                "nas_deleted": False,
                "staff_message": "Details updated. File was not re-uploaded.",
                "staff_ready": False,
            },
        }
    finally:
        conn.close()


def _opt_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _field_str(fields: dict, key: str) -> str | None:
    v = fields.get(key)
    if isinstance(v, (bytes, bytearray)):
        v = v.decode("utf-8", "replace")
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s if s else None


def handle_smart_upload(
    fields: dict,
    *,
    subject: str,
    serve_mod: Any,
    scopes: list[str] | None = None,
) -> dict:
    """Process one smart-upload file with batch metadata.

    Pipeline: staging → validate → hash → dup check → metadata → scope →
    library_v2 mirror → canonical NAS placement → index.
    Returns {http, body} — body never includes raw filesystem paths for UI.
    nas_received=true only when file is verified on NAS.
    """
    file_field = fields.get("file")
    if not isinstance(file_field, dict) or not file_field.get("data"):
        return {"http": 400, "body": {"ok": False, "status": "error", "error": "file field required", "ui_status": UI_FAILED}}

    filename = file_field.get("filename") or "upload"
    data = file_field["data"]
    if not isinstance(data, (bytes, bytearray)):
        return {"http": 400, "body": {"ok": False, "status": "error", "error": "invalid file payload", "ui_status": UI_FAILED}}
    data = bytes(data)
    if len(data) == 0:
        return {"http": 400, "body": {"ok": False, "status": "error", "error": "empty file", "ui_status": UI_FAILED}}
    if len(data) > serve_mod.MAX_UPLOAD_BYTES:
        return {
            "http": 413,
            "body": {
                "ok": False,
                "status": "error",
                "error": f"file exceeds {serve_mod.MAX_UPLOAD_BYTES} byte limit",
                "ui_status": UI_FAILED,
            },
        }

    original_filename = safe_original_basename(filename)
    meta_stem, ext = serve_mod.client_filename_stem_ext(filename)
    if ext not in serve_mod.UPLOAD_ALLOWED_EXT:
        return {
            "http": 415,
            "body": {
                "ok": False,
                "status": "error",
                "error": f"unsupported media type / extension: {ext or '(none)'}",
                "ui_status": UI_FAILED,
                "original_filename": original_filename,
            },
        }

    declared_ct = (file_field.get("content_type") or "application/octet-stream").split(";")[0].strip().lower()
    if declared_ct and declared_ct not in serve_mod.UPLOAD_ALLOWED_CONTENT_TYPES:
        return {
            "http": 415,
            "body": {
                "ok": False,
                "status": "error",
                "error": f"unsupported Content-Type: {declared_ct}",
                "ui_status": UI_FAILED,
                "original_filename": original_filename,
            },
        }

    kind = serve_mod.sniff_media_kind(data)
    if not serve_mod.ext_compatible_with_magic(ext, kind):
        return {
            "http": 415,
            "body": {
                "ok": False,
                "status": "error",
                "error": f"content magic mismatch for extension {ext}",
                "ui_status": UI_FAILED,
                "original_filename": original_filename,
            },
        }

    # Batch metadata
    try:
        brand = _wn.normalize_brand(_field_str(fields, "brand"))
        stage = _wn.normalize_stage(_field_str(fields, "stage") or "RAW")
        shoot_date = _wn.normalize_shoot_date(_field_str(fields, "shoot_date"))
        subject_tok = _field_str(fields, "subject_token") or _field_str(fields, "subject")
        if not subject_tok:
            raise ValueError("subject required")
        subject_slug = _wn.slug_normalize(subject_tok, fallback="subject")
        detail_raw = _field_str(fields, "detail") or _field_str(fields, "default_detail")
        if not detail_raw or not _p26.detail_valid(detail_raw):
            raise ValueError("detail required — need ≥1 meaningful slug token (e.g. pool-wide)")
        detail_tags = _p26.parse_detail_tags(detail_raw)
        detail = "-".join(detail_tags) if detail_tags else _wn.slug_normalize(detail_raw, fallback="")
        if not detail:
            raise ValueError("detail required — need ≥1 meaningful slug token")
        location_raw = _field_str(fields, "location")
        location = _wn.slug_normalize(location_raw, fallback="") if location_raw else ""
        media_type = _wn.normalize_media_type(
            _field_str(fields, "media_type"),
            ext=ext,
        )
        data_lane = (_field_str(fields, "data_lane") or "operational").lower()
        if data_lane not in ("operational", "test"):
            raise ValueError("data_lane must be operational|test")
    except ValueError as exc:
        return {
            "http": 400,
            "body": {
                "ok": False,
                "status": "error",
                "error": str(exc),
                "ui_status": UI_FAILED,
                "original_filename": original_filename,
            },
        }

    # Scope / permission — brand must be in Person→…→Scope (wrong-scope → 403)
    if scopes is not None and not _nas.scopes_allow_brand(scopes, brand):
        return {
            "http": 403,
            "body": {
                "ok": False,
                "status": "error",
                "error": "forbidden",
                "message": f"subject lacks scope for brand {brand}",
                "required_scope_for_brand": brand,
                "ui_status": UI_FAILED,
                "original_filename": original_filename,
                "nas_received": False,
            },
        }

    plan_id = _opt_int(_field_str(fields, "content_plan_id") or _field_str(fields, "plan_id"))
    card_id = _opt_int(_field_str(fields, "content_card_id") or _field_str(fields, "card_id"))
    batch_id = _field_str(fields, "batch_id") or uuid.uuid4().hex[:16]
    file_key = _field_str(fields, "file_key") or original_filename
    content_hash = _p26.file_sha256(data)
    file_size = len(data)
    force = (_field_str(fields, "force") or "").lower() in ("1", "true", "yes")

    # BEFORE storage starts — cancel immediately; no NAS / Library record.
    if is_cancelled(batch_id, file_key):
        return {
            "http": 200,
            "body": cancelled_response(
                original_filename=original_filename,
                batch_id=batch_id,
                phase="before_storage",
            ),
        }

    # Optional per-file detail override already in detail
    dest_dirs = [
        serve_mod.LIBRARY_V2 / stage,
        serve_mod.LIBRARY_V2 / "RAW",
        serve_mod.LIBRARY_V2 / "EDIT",
        serve_mod.LIBRARY_V2 / "FINAL",
    ]

    conn = serve_mod.db_connect()
    try:
        # Validate optional plan/card exist (nullable) — do not invent
        if plan_id is not None:
            row = conn.execute("SELECT id FROM content_plans WHERE id=?", (plan_id,)).fetchone()
            if not row:
                return {
                    "http": 400,
                    "body": {
                        "ok": False,
                        "status": "error",
                        "error": f"content_plan_id {plan_id} not found",
                        "ui_status": UI_FAILED,
                        "original_filename": original_filename,
                    },
                }
        if card_id is not None:
            row = conn.execute("SELECT id FROM content_cards WHERE id=?", (card_id,)).fetchone()
            if not row:
                return {
                    "http": 400,
                    "body": {
                        "ok": False,
                        "status": "error",
                        "error": f"content_card_id {card_id} not found",
                        "ui_status": UI_FAILED,
                        "original_filename": original_filename,
                    },
                }

        dup_hits = _p26.find_duplicates(
            conn,
            content_hash=content_hash,
            file_size=file_size,
            original_filename=original_filename,
            canonical_filename=None,
            data_lane=data_lane,
        )
        if dup_hits and not force:
            return {
                "http": 409,
                "body": {
                    "ok": False,
                    "status": "duplicate_warning",
                    "error": "possible_duplicate",
                    "message": "Possible duplicate — already in Library. Re-submit with force=1 to upload anyway.",
                    "ui_status": UI_FAILED,
                    "duplicate": True,
                    "matches": dup_hits,
                    "original_filename": original_filename,
                    "content_hash": content_hash,
                    "file_size": file_size,
                },
            }

        n, seq_tok = _wn.allocate_sequence(
            conn,
            brand=brand,
            stage=stage,
            media_type=media_type,
            subject=subject_slug,
            detail=detail or None,
            shoot_date=shoot_date,
            ext=ext,
            dest_dirs=dest_dirs,
        )
        canonical = _wn.build_canonical_filename(
            brand, stage, media_type, subject_slug, detail or None, shoot_date, seq_tok, ext
        )
    finally:
        conn.close()

    # Write to incoming_drop (UUID path jail) then stage + commit to library
    uploaded_at = now_iso()
    dest: Path | None = None
    try:
        dest = serve_mod.unique_incoming_path(ext)

        def _cancel_check() -> bool:
            return is_cancelled(batch_id, file_key)

        if is_cancelled(batch_id, file_key):
            cleanup_temp_partial(dest)
            return {
                "http": 200,
                "body": cancelled_response(
                    original_filename=original_filename,
                    batch_id=batch_id,
                    phase="before_storage",
                ),
            }
        serve_mod.write_upload_streaming(
            dest, data, serve_mod.MAX_UPLOAD_BYTES, cancel_check=_cancel_check
        )
        dest = serve_mod._ensure_under_incoming(dest)
        if is_cancelled(batch_id, file_key):
            cleanup_temp_partial(dest)
            return {
                "http": 200,
                "body": cancelled_response(
                    original_filename=original_filename,
                    batch_id=batch_id,
                    phase="during_transfer",
                ),
            }
    except serve_mod.UploadCancelled:
        cleanup_temp_partial(dest)
        return {
            "http": 200,
            "body": cancelled_response(
                original_filename=original_filename,
                batch_id=batch_id,
                phase="during_transfer",
            ),
        }
    except serve_mod.UploadTooLarge as exc:
        cleanup_temp_partial(dest)
        return {"http": 413, "body": {"ok": False, "status": "error", "error": str(exc), "ui_status": UI_FAILED, "original_filename": original_filename}}
    except serve_mod.UnsupportedMedia as exc:
        cleanup_temp_partial(dest)
        return {"http": 415, "body": {"ok": False, "status": "error", "error": str(exc), "ui_status": UI_FAILED, "original_filename": original_filename}}
    except PermissionError as exc:
        cleanup_temp_partial(dest)
        return {"http": 400, "body": {"ok": False, "status": "error", "error": str(exc), "ui_status": UI_FAILED, "original_filename": original_filename}}
    except OSError as exc:
        cleanup_temp_partial(dest)
        return {"http": 500, "body": {"ok": False, "status": "error", "error": f"save failed: {exc}", "ui_status": UI_FAILED, "original_filename": original_filename}}

    # Stage (probe / MIME) — status STAGED initially
    if is_cancelled(batch_id, file_key):
        cleanup_temp_partial(dest)
        return {
            "http": 200,
            "body": cancelled_response(
                original_filename=original_filename,
                batch_id=batch_id,
                phase="during_transfer",
            ),
        }
    try:
        row = _stage_inspector.stage_file(dest, brand=brand, stage=stage)
    except Exception as exc:  # noqa: BLE001
        cleanup_temp_partial(dest)
        return {
            "http": 500,
            "body": {
                "ok": False,
                "status": "error",
                "error": f"staging failed: {exc}",
                "ui_status": UI_FAILED,
                "original_filename": original_filename,
                "library_status": LIB_FAILED,
                "processing_status": LIB_FAILED,
            },
        }

    staged_id = row["id"]
    if is_cancelled(batch_id, file_key):
        cleanup_temp_partial(dest)
        return {
            "http": 200,
            "body": cancelled_response(
                original_filename=original_filename,
                batch_id=batch_id,
                phase="during_transfer",
            ),
        }
    # Prefer media_type from batch; keep probe type as fallback for assets.type compat
    asset_type = media_type if media_type in ("video", "audio", "broll", "graphic", "image") else (row.get("suggested_type") or "graphic")
    if asset_type == "image":
        # assets.type historically graphic for stills — keep both: media_type=image, type=graphic for query compat
        type_col = "graphic"
    else:
        type_col = asset_type if asset_type in serve_mod.ASSET_TYPES else "graphic"

    conn = serve_mod.db_connect()
    try:
        conn.execute(
            """
            UPDATE staged_assets SET
              suggested_brand=?, suggested_stage=?, suggested_type=?, suggested_slug=?,
              original_filename=?, canonical_filename=?, subject=?, detail=?, location=?,
              shoot_date=?, sequence_token=?, media_type=?, uploaded_by=?, uploaded_at=?,
              content_plan_id=?, content_card_id=?, processing_status=?, library_status=?,
              data_lane=?, batch_id=?
            WHERE id=?
            """,
            (
                brand,
                stage,
                type_col,
                subject_slug,
                original_filename,
                canonical,
                subject_slug,
                detail or None,
                location or None,
                shoot_date,
                seq_tok,
                media_type,
                subject,
                uploaded_at,
                plan_id,
                card_id,
                LIB_CHECKING,
                LIB_UPLOAD_RECEIVED,
                data_lane,
                batch_id,
                staged_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Commit into library_v2 with Wolf canonical name (never overwrite)
    lib_dir = serve_mod.LIBRARY_V2 / stage
    try:
        lib_dir.mkdir(parents=True, exist_ok=True)
        serve_mod._ensure_under_beta(lib_dir)
        final_path = _wn.unique_library_path(lib_dir, canonical)
        final_name = final_path.name
        # Re-check jail
        final_path = serve_mod._ensure_under_beta(final_path)
        if final_path.exists():
            raise OSError(f"refuse overwrite: {final_name}")
        try:
            shutil.move(str(dest), str(final_path))
        except OSError:
            shutil.copy2(str(dest), str(final_path))
            try:
                dest.unlink()
            except OSError:
                pass

        now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        # Canonical NAS placement (additive under _Imports/Wolf-Library only)
        nas_place = _nas.place_on_nas(
            final_path,
            brand=brand,
            stage=stage,
            shoot_date=shoot_date,
            canonical_filename=final_name,
            data_lane=data_lane,
            content_hash=content_hash,
            original_filename=original_filename,
        )
        nas_received = bool(nas_place.get("nas_received"))
        # Double-check honesty — never true unless file really on NAS
        if nas_received and not _nas.verify_nas_received(
            nas_place.get("nas_path"), expected_size=file_size
        ):
            nas_received = False
            nas_place = {
                **nas_place,
                "nas_received": False,
                "message": "NAS verify failed after copy — refuse nas_received",
            }
        provenance = {
            "original_filename": original_filename,
            "canonical_filename": final_name,
            "source_system": "smart_upload",
            "beta_library_mirror": True,
            "nas_rel": nas_place.get("nas_rel"),
            "nas_received": nas_received,
            "data_lane": data_lane,
            "test_marked": data_lane == "test",
        }
        from core import content_engine_repair as _ce_repair

        content_class = (_field_str(fields, "content_class") or "").strip().lower()
        if content_class in {slug for slug, _label in _ce_repair.CONTENT_CLASSES}:
            provenance["content_class"] = content_class
        conn = serve_mod.db_connect()
        try:
            _nas.migrate_schema(conn)
            cur = conn.execute(
                """
                INSERT INTO assets (
                  brand, stage, type, slug, filename,
                  original_path, v2_path, source_system, date_added, status,
                  original_filename, canonical_filename, subject, detail, location,
                  shoot_date, sequence_token, media_type, uploaded_by, uploaded_at,
                  content_plan_id, content_card_id, processing_status, library_status,
                  data_lane, batch_id,
                  content_hash, file_size, detail_tags_json, readiness, readiness_note,
                  nas_path, nas_rel, nas_received, nas_received_at, nas_verified_size,
                  provenance_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    brand,
                    stage,
                    type_col,
                    subject_slug,
                    final_name,
                    None,  # do not expose raw temp path as original_path for smart uploads
                    str(final_path),
                    "smart_upload",
                    now,
                    "indexed",
                    original_filename,
                    final_name,
                    subject_slug,
                    detail or None,
                    location or None,
                    shoot_date,
                    seq_tok,
                    media_type,
                    subject,
                    uploaded_at,
                    plan_id,
                    card_id,
                    LIB_READY,
                    LIB_READY,
                    data_lane,
                    batch_id,
                    content_hash,
                    file_size,
                    __import__("json").dumps(detail_tags),
                    "READY_TO_USE",
                    (
                        "Verified on NAS and Beta library."
                        if nas_received
                        else "Verified in Beta library; NAS not confirmed."
                    ),
                    nas_place.get("nas_path") if nas_received else None,
                    nas_place.get("nas_rel") if nas_received else None,
                    1 if nas_received else 0,
                    nas_place.get("nas_received_at") if nas_received else None,
                    nas_place.get("verified_size") if nas_received else None,
                    __import__("json").dumps(provenance),
                ),
            )
            asset_id = cur.lastrowid
            conn.execute(
                """
                UPDATE staged_assets SET
                  status='VERIFIED',
                  processing_status=?,
                  library_status=?,
                  canonical_filename=?
                WHERE id=?
                """,
                (LIB_READY, LIB_READY, final_name, staged_id),
            )
            conn.commit()
        finally:
            conn.close()

        nas = nas_status()
        nas_public = {
            "connected": bool(nas.get("connected")),
            "message": nas.get("message"),
            "nas_received": False,  # connectivity banner never claims this file
            "wolf_write_prefix_name": "_Imports/Wolf-Library",
        }
        from core import content_engine_repair as _ce_repair

        body = _ce_repair.annotate_upload(
            {
                "ok": True,
                "status": "success",
                "ui_status": UI_READY,
                "library_status": LIB_READY,
                "processing_status": LIB_READY,
                "staged_id": staged_id,
                "asset_id": asset_id,
                "original_filename": original_filename,
                "canonical_filename": final_name,
                "brand": brand,
                "stage": stage,
                "media_type": media_type,
                "subject": subject_slug,
                "detail": detail or None,
                "detail_tags": detail_tags,
                "location": location or None,
                "shoot_date": shoot_date,
                "sequence_token": seq_tok,
                "batch_id": batch_id,
                "content_plan_id": plan_id,
                "content_card_id": card_id,
                "data_lane": data_lane,
                "uploaded_by": subject,
                "uploaded_at": uploaded_at,
                "content_hash": content_hash,
                "file_size": file_size,
                "readiness": "READY_TO_USE",
                "readiness_label": "READY TO USE",
                "nas": nas_public,
                "nas_received": nas_received,
                "nas_rel": nas_place.get("nas_rel") if nas_received else None,
                "nas_message": nas_place.get("message"),
                "provenance": {
                    "original_filename": original_filename,
                    "canonical_filename": final_name,
                    "nas_rel": nas_place.get("nas_rel") if nas_received else None,
                    "nas_received": nas_received,
                    "source_system": "smart_upload",
                    "data_lane": data_lane,
                },
            },
            media_path=final_path,
        )
        # AFTER safely stored — do not fake CANCELLED; stop subsequent processing copy.
        if is_cancelled(batch_id, file_key):
            body = late_cancel_annotate(body)
        return {"http": 200, "body": body}
    except Exception as exc:  # noqa: BLE001
        conn = serve_mod.db_connect()
        try:
            conn.execute(
                """
                UPDATE staged_assets SET
                  status='FAILED',
                  processing_status=?,
                  library_status=?
                WHERE id=?
                """,
                (LIB_FAILED, LIB_FAILED, staged_id),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "http": 500,
            "body": {
                "ok": False,
                "status": "error",
                "error": f"library commit failed: {exc}",
                "ui_status": UI_FAILED,
                "library_status": LIB_FAILED,
                "processing_status": LIB_FAILED,
                "staged_id": staged_id,
                "original_filename": original_filename,
                "canonical_filename": canonical,
                "nas_received": False,
            },
        }


def preview_batch(serve_mod: Any, body: dict) -> dict:
    try:
        brand = _wn.normalize_brand(body.get("brand"))
        stage = _wn.normalize_stage(body.get("stage") or "RAW")
        shoot_date = _wn.normalize_shoot_date(body.get("shoot_date"))
        subject_tok = body.get("subject") or body.get("subject_token")
        if not subject_tok:
            raise ValueError("subject required")
        files = body.get("files") or []
        if not isinstance(files, list) or not files:
            raise ValueError("files array required")
        detail_raw = body.get("detail") or body.get("default_detail") or ""
        if not str(detail_raw).strip():
            # UI may only send detail on files[].detail (content-2.0 buildReview).
            for f in files:
                if isinstance(f, dict):
                    cand = f.get("detail") or f.get("default_detail") or ""
                    if str(cand).strip():
                        detail_raw = cand
                        break
        if not _p26.detail_valid(str(detail_raw)):
            raise ValueError("detail required — need ≥1 meaningful slug token")
        media_type = _wn.normalize_media_type(body.get("media_type") or "video")
        if len(files) > 50:
            raise ValueError("max 50 files per batch")
        dest_dirs = [
            serve_mod.LIBRARY_V2 / stage,
            serve_mod.LIBRARY_V2 / "RAW",
            serve_mod.LIBRARY_V2 / "EDIT",
            serve_mod.LIBRARY_V2 / "FINAL",
        ]
        conn = serve_mod.db_connect()
        try:
            previews = _wn.preview_names(
                conn,
                brand=brand,
                stage=stage,
                media_type=media_type,
                subject=str(subject_tok),
                shoot_date=shoot_date,
                files=files,
                dest_dirs=dest_dirs,
            )
        finally:
            conn.close()
        return {
            "http": 200,
            "body": {
                "ok": True,
                "brand": brand,
                "stage": stage,
                "media_type": media_type,
                "subject": _wn.slug_normalize(str(subject_tok)),
                "shoot_date": shoot_date,
                "previews": previews,
                "count": len(previews),
            },
        }
    except ValueError as exc:
        return {"http": 400, "body": {"ok": False, "error": str(exc)}}


def list_smart_uploads(serve_mod: Any, qs: dict) -> list[dict]:
    """Recent smart uploads for UI — no filesystem paths."""
    brand = ((qs.get("brand") or [""])[0] or "").strip().lower()
    lane = ((qs.get("data_lane") or ["operational"])[0] or "operational").strip().lower()
    limit = 30
    try:
        limit = min(100, max(1, int((qs.get("limit") or ["30"])[0])))
    except ValueError:
        limit = 30
    conn = serve_mod.db_connect()
    try:
        clauses = ["source_system = 'smart_upload'"]
        params: list[Any] = []
        if brand:
            clauses.append("brand = ?")
            params.append(brand)
        if lane == "operational":
            clauses.append("ifnull(data_lane,'operational') = 'operational'")
        elif lane == "test":
            clauses.append("ifnull(data_lane,'operational') = 'test'")
        # lane=all → no filter
        where = " AND ".join(clauses)
        rows = conn.execute(
            f"""
            SELECT id, brand, stage, type, media_type, subject, detail, location,
                   shoot_date, sequence_token, original_filename, canonical_filename,
                   filename, uploaded_by, uploaded_at, content_plan_id, content_card_id,
                   processing_status, library_status, data_lane, batch_id, status, date_added,
                   content_hash, nas_received
            FROM assets
            WHERE {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        from core import content_engine_repair as _ce_repair

        out = []
        for r in rows:
            d = dict(r)
            available = _ce_repair.row_library_available(d)
            out.append(
                {
                    "id": d["id"],
                    "brand": d.get("brand"),
                    "stage": d.get("stage"),
                    "type": d.get("type"),
                    "media_type": d.get("media_type") or d.get("type"),
                    "subject": d.get("subject"),
                    "detail": d.get("detail"),
                    "location": d.get("location"),
                    "shoot_date": d.get("shoot_date"),
                    "sequence_token": d.get("sequence_token"),
                    "original_filename": d.get("original_filename"),
                    "canonical_filename": d.get("canonical_filename") or d.get("filename"),
                    "name": d.get("canonical_filename") or d.get("filename"),
                    "uploaded_by": d.get("uploaded_by"),
                    "uploaded_at": d.get("uploaded_at") or d.get("date_added"),
                    "content_plan_id": d.get("content_plan_id"),
                    "content_card_id": d.get("content_card_id"),
                    "processing_status": d.get("processing_status"),
                    "library_status": d.get("library_status"),
                    "status": d.get("library_status") or d.get("status"),
                    "data_lane": d.get("data_lane") or "operational",
                    "batch_id": d.get("batch_id"),
                    "ui_status": (
                        "COMPLETE"
                        if available
                        else (
                            UI_FAILED
                            if d.get("library_status") == LIB_FAILED
                            else UI_CHECKING
                        )
                    ),
                    "staff_outcome": _ce_repair.staff_upload_outcome(d),
                    "staff_title": _ce_repair.library_display_title(
                        d.get("subject"), d.get("detail"), d.get("original_filename")
                    ),
                    "library_available": available,
                }
            )
        return out
    finally:
        conn.close()
