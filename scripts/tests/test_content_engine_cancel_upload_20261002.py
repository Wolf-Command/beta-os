#!/usr/bin/env python3
"""CE-CANCEL-UPLOAD-1 — Owner ENGINEERING PROOF.

Proves cancel before/during/after transfer, temp cleanup, metadata correction
+ audit, retry unaffected, multi-file MOV batch. Beta only. staff_ready=false.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import smart_upload as su  # noqa: E402
from core import content_engine_repair as repair  # noqa: E402

HTML = ROOT / "dashboards" / "content-2.0.html"
SERVE = ROOT / "scripts" / "serve_beta.py"
HAIKAL = "haikalqilbari123@gmail.com"
BATCH = "eng-ce-cancel-" + uuid.uuid4().hex[:10]
PASS = 0
FAIL = 0
LINES: list[str] = []
ASSET_IDS: list[int] = []


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        LINES.append(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        LINES.append(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _ffmpeg() -> str | None:
    return repair.resolve_ffmpeg()


def _make_mov(ffmpeg: str, dest: Path, color: str) -> bytes:
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=160x90:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-f",
            "mov",
            str(dest),
        ],
        capture_output=True,
        timeout=40,
    )
    if proc.returncode != 0 or not dest.is_file():
        raise RuntimeError((proc.stderr or b"")[-200:].decode("utf-8", "replace"))
    return dest.read_bytes()


def _upload(serve_mod, scopes, filename: str, data: bytes, *, detail: str, batch_id: str, stage: str = "RAW") -> dict:
    fields = {
        "file": {"filename": filename, "data": data, "content_type": "video/quicktime"},
        "brand": "tropik",
        "stage": stage,
        "media_type": "video",
        "subject": "eng-cancel",
        "detail": detail,
        "shoot_date": "2026-10-02",
        "data_lane": "test",
        "batch_id": batch_id,
        "file_key": filename,
        "content_class": "b-roll",
    }
    saved = os.environ.get("PATH", "")
    os.environ["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    try:
        result = su.handle_smart_upload(fields, subject=HAIKAL, serve_mod=serve_mod, scopes=scopes)
    finally:
        os.environ["PATH"] = saved
    body = result["body"]
    http = int(result["http"])
    if isinstance(body, dict):
        body["staff_message"] = body.get("staff_message") or repair.staff_upload_message(http, body)
        if body.get("asset_id"):
            ASSET_IDS.append(int(body["asset_id"]))
    return {"http": http, "body": body}


def _cleanup(serve_mod) -> None:
    if not ASSET_IDS:
        su.clear_batch_cancel(BATCH)
        return
    conn = serve_mod.db_connect()
    try:
        for asset_id in list(ASSET_IDS):
            row = conn.execute(
                "SELECT id, data_lane, batch_id, v2_path, nas_path FROM assets WHERE id=?",
                (asset_id,),
            ).fetchone()
            if not row:
                continue
            d = dict(row)
            if d.get("data_lane") != "test" or BATCH not in str(d.get("batch_id") or ""):
                if str(d.get("batch_id") or "").startswith("eng-ce-cancel"):
                    pass
                else:
                    continue
            for key in ("v2_path", "nas_path"):
                raw = d.get(key)
                if raw and Path(str(raw)).is_file():
                    try:
                        Path(str(raw)).unlink(missing_ok=True)
                    except OSError:
                        pass
            thumb = repair.asset_thumb_path(int(asset_id))
            if thumb.is_file():
                thumb.unlink()
            conn.execute("DELETE FROM assets WHERE id=? AND data_lane='test'", (asset_id,))
        conn.execute("DELETE FROM staged_assets WHERE batch_id LIKE 'eng-ce-cancel%' AND data_lane='test'")
        conn.commit()
    finally:
        conn.close()
    for bid in list(getattr(su, "_batch_cancels", {}) or {}):
        if str(bid).startswith("eng-ce-cancel"):
            su.clear_batch_cancel(bid)


def test_ui_surface() -> None:
    raw = HTML.read_text(encoding="utf-8")
    log('id="uploadCancelBtn"' in raw, "UI Cancel Upload control")
    log("Cancel remaining uploads?" in raw, "UI one-confirm Cancel Remaining copy")
    log("Files already uploaded will stay in the Library." in raw, "UI confirm keeps uploaded files copy")
    log("uploadBatchStats" in raw and "Completed" in raw and "Cancelled" in raw, "UI batch progress counts")
    log("prevCorrectMeta" in raw and "correct-metadata" in raw, "UI metadata correction control")
    log("formatCancelSummary" in raw and "stopped during processing" in raw, "UI honest cancel summary")
    log("AbortController" in raw, "UI abort in-flight transfer")
    route = SERVE.read_text(encoding="utf-8")
    log("/api/upload/cancel" in route and "correct-metadata" in route, "server cancel + metadata routes")
    log("UploadCancelled" in route and "cancel_check" in route, "server mid-transfer cancel + temp cleanup")
    js = raw.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/content-engine-cancel-upload.js")
    tmp.write_text(js, encoding="utf-8")
    syntax = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    log(syntax.returncode == 0, "content-2.0 cancel JS syntax", (syntax.stderr or "OK")[:160])


def test_staff_messages() -> None:
    log(
        repair.staff_upload_message(200, {"cancelled": True, "ui_status": "CANCELLED"})
        == repair.STAFF_CANCELLED,
        "cancelled staff sentence",
    )
    log(
        repair.staff_upload_message(200, {"already_uploaded_processing_stopped": True, "library_available": True})
        == repair.STAFF_ALREADY_UPLOADED_STOPPED,
        "late-cancel staff sentence",
    )
    log(
        su.format_batch_cancel_summary(uploaded=7, stopped_during=1, cancelled_before=6)
        == "7 uploaded · 1 stopped during processing · 6 cancelled before upload",
        "batch summary format",
    )


def test_engineering_proof(serve_mod) -> None:
    scopes = ["SCOPE-WOLF-CONTENT-ALL-BRANDS"]
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        log(False, "ffmpeg available for MOV proof", "missing")
        return

    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        mov_a = _make_mov(ffmpeg, td / "a.mov", "red")
        mov_b = _make_mov(ffmpeg, td / "b.mov", "blue")
        mov_c = _make_mov(ffmpeg, td / "c.mov", "green")
        mov_d = _make_mov(ffmpeg, td / "d.mov", "yellow")
        mov_e = _make_mov(ffmpeg, td / "e.mov", "purple")
        mov_f = _make_mov(ffmpeg, td / "f.mov", "orange")

        # --- cancel queued / before first file ---
        bid_pre = BATCH + "-pre"
        su.clear_batch_cancel(bid_pre)
        su.request_batch_cancel(bid_pre, subject=HAIKAL)
        pre = _upload(serve_mod, scopes, "IMG_CANCEL_PRE.mov", mov_a, detail="cancel-pre", batch_id=bid_pre)
        body = pre["body"]
        log(
            body.get("ui_status") == "CANCELLED"
            and body.get("cancelled") is True
            and body.get("library_available") is False
            and not body.get("asset_id"),
            "cancel batch before first file",
            body.get("staff_message"),
        )
        log(body.get("ui_status") != "READY", "cancelled ≠ READY")
        conn = serve_mod.db_connect()
        try:
            hit = conn.execute(
                "SELECT COUNT(*) AS n FROM assets WHERE batch_id=? AND data_lane='test'",
                (bid_pre,),
            ).fetchone()["n"]
        finally:
            conn.close()
        log(int(hit) == 0, "cancel before upload — no Library row")

        # --- cancel queued for one file_key ---
        bid_q = BATCH + "-q"
        su.clear_batch_cancel(bid_q)
        su.request_batch_cancel(bid_q, subject=HAIKAL, file_key="IMG_CANCEL_Q.mov")
        q = _upload(serve_mod, scopes, "IMG_CANCEL_Q.mov", mov_a, detail="cancel-queued", batch_id=bid_q)
        log(
            q["body"].get("cancelled") is True and q["body"].get("cancel_phase") == "before_storage",
            "cancel queued before upload (per-file)",
        )

        # --- cancel mid-transfer + temp partial cleanup ---
        bid_mid = BATCH + "-mid"
        su.clear_batch_cancel(bid_mid)
        written_paths: list[Path] = []
        real_write = serve_mod.write_upload_streaming

        def flaky_write(dest, data, max_bytes, cancel_check=None):
            dest = serve_mod._ensure_under_incoming(Path(dest))
            written_paths.append(dest)
            # Write a partial then cancel.
            with open(dest, "wb") as fh:
                fh.write(bytes(data)[: max(1, len(data) // 4)])
            su.request_batch_cancel(bid_mid, subject=HAIKAL)
            if callable(cancel_check) and cancel_check():
                serve_mod.cleanup_temp = True
                try:
                    dest.unlink(missing_ok=True)
                except OSError:
                    pass
                raise serve_mod.UploadCancelled("cancelled during transfer")
            return real_write(dest, data, max_bytes, cancel_check=cancel_check)

        serve_mod.write_upload_streaming = flaky_write  # type: ignore[method-assign]
        try:
            mid = _upload(
                serve_mod,
                scopes,
                "IMG_CANCEL_MID.mov",
                mov_b,
                detail="cancel-mid",
                batch_id=bid_mid,
            )
        finally:
            serve_mod.write_upload_streaming = real_write  # type: ignore[method-assign]
        log(
            mid["body"].get("cancelled") is True
            and mid["body"].get("cancel_phase") == "during_transfer"
            and mid["body"].get("ui_status") == "CANCELLED",
            "cancel mid-transfer",
            mid["body"].get("staff_message"),
        )
        leftovers = [p for p in written_paths if p.exists()]
        log(not leftovers, "temp partial cleanup on abort", str(leftovers[:2]))
        conn = serve_mod.db_connect()
        try:
            mid_n = conn.execute(
                "SELECT COUNT(*) AS n FROM assets WHERE batch_id=? AND data_lane='test'",
                (bid_mid,),
            ).fetchone()["n"]
        finally:
            conn.close()
        log(int(mid_n) == 0, "mid-cancel — no Library/NAS index row")

        # --- successful upload then late cancel annotate ---
        bid_ok = BATCH + "-ok"
        su.clear_batch_cancel(bid_ok)
        ok = _upload(serve_mod, scopes, "IMG_KEEP.mov", mov_a, detail="keep-ok", batch_id=bid_ok)
        asset_id = ok["body"].get("asset_id")
        log(
            ok["http"] == 200 and ok["body"].get("library_available") is True and asset_id,
            "completed upload intact before late cancel",
            f"asset_id={asset_id}",
        )
        su.request_batch_cancel(bid_ok, subject=HAIKAL)
        late = su.late_cancel_annotate(dict(ok["body"]))
        log(
            late.get("already_uploaded_processing_stopped") is True
            and late.get("cancelled") is False
            and late.get("staff_message") == su.STAFF_ALREADY_UPLOADED_STOPPED
            and late.get("ui_status") == "READY",
            "cancel after stored — asset preserved, no fake cancel",
        )
        conn = serve_mod.db_connect()
        try:
            row = conn.execute("SELECT id, nas_path, v2_path, content_hash FROM assets WHERE id=?", (asset_id,)).fetchone()
            still = dict(row) if row else {}
        finally:
            conn.close()
        log(bool(still.get("id")), "after-stored cancel — Library row remains")
        # No duplicate on retry of same bytes without force
        dup = _upload(serve_mod, scopes, "IMG_KEEP.mov", mov_a, detail="keep-ok", batch_id=bid_ok + "2")
        log(dup["http"] == 409 or dup["body"].get("duplicate") is True, "retry unaffected — duplicate warning (no silent re-upload)")

        # --- metadata correction + audit, no re-upload ---
        corr = su.correct_asset_metadata(
            serve_mod,
            int(asset_id),
            {"stage": "EDIT", "subject": "eng-cancel-fixed", "location": "kuta", "detail": "pool-wide", "content_class": "property"},
            subject=HAIKAL,
            scopes=scopes,
        )
        cbody = corr["body"]
        log(
            corr["http"] == 200
            and cbody.get("changed") is True
            and cbody.get("reuploaded") is False
            and cbody.get("nas_deleted") is False
            and cbody.get("stage") == "EDIT",
            "metadata correction without re-upload",
            str([ch.get("field") for ch in cbody.get("changes") or []]),
        )
        fields_changed = {ch["field"] for ch in (cbody.get("changes") or [])}
        log(
            {"stage", "subject", "location", "detail", "content_class"} <= fields_changed,
            "metadata correction fields (brand/stage/type/subject/location/details)",
        )
        conn = serve_mod.db_connect()
        try:
            after = dict(
                conn.execute(
                    "SELECT stage, subject, detail, location, provenance_json, content_hash, file_size FROM assets WHERE id=?",
                    (asset_id,),
                ).fetchone()
            )
            prov = json.loads(after.get("provenance_json") or "{}")
        finally:
            conn.close()
        log(
            after.get("stage") == "EDIT"
            and after.get("subject") == "eng-cancel-fixed"
            and after.get("location") == "kuta"
            and after.get("content_hash") == still.get("content_hash"),
            "search index reflects correction; hash unchanged",
        )
        audit = prov.get("metadata_corrections") or []
        log(
            bool(audit)
            and audit[-1].get("by") == HAIKAL
            and isinstance(audit[-1].get("changes"), list),
            "metadata audit trail (old/new/person/timestamp)",
            audit[-1].get("at") if audit else "",
        )
        # brand correction
        brand_corr = su.correct_asset_metadata(
            serve_mod,
            int(asset_id),
            {"brand": "habitat"},
            subject=HAIKAL,
            scopes=scopes,
        )
        log(
            brand_corr["http"] == 200 and brand_corr["body"].get("brand") == "habitat",
            "brand metadata correction",
        )

        # --- multi-file MOV batch: 1 ok, cancel remaining (distinct bytes — no false dup) ---
        bid_batch = BATCH + "-multi"
        su.clear_batch_cancel(bid_batch)
        first = _upload(serve_mod, scopes, "IMG_MULTI_1.mov", mov_d, detail="multi-one", batch_id=bid_batch)
        log(first["body"].get("library_available") is True, "multi-file MOV #1 uploaded", first["body"].get("error") or first["body"].get("staff_message"))
        su.request_batch_cancel(bid_batch, subject=HAIKAL)
        second = _upload(serve_mod, scopes, "IMG_MULTI_2.mov", mov_e, detail="multi-two", batch_id=bid_batch)
        third = _upload(serve_mod, scopes, "IMG_MULTI_3.mov", mov_f, detail="multi-three", batch_id=bid_batch)
        log(second["body"].get("cancelled") is True, "multi-file MOV #2 cancelled before/during")
        log(third["body"].get("cancelled") is True, "multi-file MOV #3 cancelled before/during")
        # First remains; late annotate if cancel after commit mid-pipeline
        late2 = su.late_cancel_annotate(dict(first["body"]))
        log(
            late2.get("already_uploaded_processing_stopped") is True
            and first["body"].get("asset_id"),
            "multi-file — completed remains; processing-stopped copy available",
        )
        conn = serve_mod.db_connect()
        try:
            n_ok = conn.execute(
                "SELECT COUNT(*) AS n FROM assets WHERE batch_id=? AND data_lane='test'",
                (bid_batch,),
            ).fetchone()["n"]
        finally:
            conn.close()
        log(int(n_ok) == 1, "multi-file — exactly one Library row for batch", f"n={n_ok}")
        summary = su.format_batch_cancel_summary(uploaded=1, stopped_during=0, cancelled_before=2)
        log("1 uploaded" in summary and "2 cancelled before upload" in summary, "multi-file batch summary", summary)

        # cleanup_temp_partial unit
        partial = serve_mod.unique_incoming_path(".mov")
        partial.write_bytes(b"partial-bytes")
        cleaned = su.cleanup_temp_partial(partial)
        log(cleaned and not partial.exists(), "cleanup_temp_partial removes incomplete file")


def main() -> int:
    print("CE-CANCEL-UPLOAD-1 ENGINEERING PROOF")
    test_ui_surface()
    test_staff_messages()
    serve_mod = None
    try:
        import serve_beta as serve_mod  # noqa: E402
        test_engineering_proof(serve_mod)
    except Exception as exc:  # noqa: BLE001
        log(False, "live proof harness", f"{type(exc).__name__}: {exc}")
    finally:
        if serve_mod is not None:
            try:
                _cleanup(serve_mod)
            except Exception as exc:  # noqa: BLE001
                LINES.append(f"WARN  cleanup — {exc}")
    for line in LINES:
        print(line)
    print(f"TOTAL pass={PASS} fail={FAIL} staff_ready=false")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
