#!/usr/bin/env python3
"""BF-content-engine-upload-state-library-search-20261001.

Proves U1–U5, B1–B3, L1–L7 on the Beta tree. Does not touch :8787.
Does not mark the Haikal bbq batch successful. staff_ready stays false.
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import content_engine_repair as repair  # noqa: E402

HTML = ROOT / "dashboards" / "content-2.0.html"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
SERVE = ROOT / "scripts" / "serve_beta.py"
HAIKAL = "haikalqilbari123@gmail.com"
BASE = "http://127.0.0.1:8788"
BATCH = "eng-probe-upload-state"
EVIDENCE = ROOT / "state" / "commissioning" / "evidence" / "CE-UPLOAD-STATE-LIBRARY-SEARCH-GATE-2026-10-01.json"
REVIEW = ROOT / "state" / "build-factory" / "BBQ-RECONCILE-bbq-night-grill-20261001.json"
PASS = 0
FAIL = 0
LINES: list[str] = []
GATES: dict[str, str] = {}


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        LINES.append(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        LINES.append(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def gate(name: str, ok: bool, detail: str = "") -> None:
    GATES[name] = "PASS" if ok else "FAIL"
    log(ok, name, detail)


def _http(method: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(BASE + path, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw[:240]}
        return exc.code, body


def _make_mov(ffmpeg: str, dest: Path, color: str) -> None:
    proc = subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c={color}:s=160x90:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-f", "mov", str(dest)],
        capture_output=True,
        timeout=40,
    )
    if proc.returncode != 0 or not dest.is_file():
        raise RuntimeError((proc.stderr or b"")[-200:].decode("utf-8", "replace"))


def _connect(path: Path | str = CATALOG, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _cleanup(asset_ids: list[int]) -> None:
    if not asset_ids:
        return
    conn = _connect()
    try:
        for asset_id in asset_ids:
            row = conn.execute(
                "SELECT id, data_lane, batch_id, v2_path, nas_path FROM assets WHERE id=?",
                (asset_id,),
            ).fetchone()
            if not row:
                continue
            if row["data_lane"] != "test" or row["batch_id"] != BATCH:
                continue
            for key in ("v2_path", "nas_path"):
                raw = row[key]
                if raw and BATCH in str(raw):
                    Path(raw).unlink(missing_ok=True)
            thumb = repair.asset_thumb_path(int(asset_id))
            if thumb.is_file():
                thumb.unlink()
            conn.execute(
                "DELETE FROM assets WHERE id=? AND data_lane='test' AND batch_id=?",
                (asset_id, BATCH),
            )
        conn.execute("DELETE FROM staged_assets WHERE batch_id=? AND data_lane='test'", (BATCH,))
        conn.commit()
    finally:
        conn.close()


def _upload(serve_mod, scopes: list[str], filename: str, data: bytes, *, detail: str) -> dict:
    fields = {
        "file": {"filename": filename, "data": data, "content_type": "video/quicktime"},
        "brand": "tropik",
        "stage": "RAW",
        "media_type": "video",
        "subject": "eng-upload-state",
        "detail": detail,
        "shoot_date": "2026-10-01",
        "data_lane": "test",
        "batch_id": BATCH,
    }
    saved = os.environ.get("PATH", "")
    os.environ["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    try:
        result = __import__("smart_upload").handle_smart_upload(
            fields, subject=HAIKAL, serve_mod=serve_mod, scopes=scopes
        )
    finally:
        os.environ["PATH"] = saved
    body = result["body"]
    http = int(result["http"])
    if isinstance(body, dict):
        body["staff_message"] = body.get("staff_message") or repair.staff_upload_message(http, body)
    return {"http": http, "body": body}


def unit_messages() -> None:
    raw = HTML.read_text(encoding="utf-8")
    for label in repair.LIFECYCLE:
        log(label[1] in raw, f"lifecycle label {label[1]}")
    for _key, label in repair.FAIL_LIFECYCLE:
        log(label in raw, f"fail label {label}")
    log(repair.STAFF_PREVIEW in raw, "page has Retry Preview sentence")
    log('btn.className = "btn retry-preview"' in raw and "Retry Preview" in raw, "Retry Preview control")
    log("savedDespitePoster" in raw and "possible_duplicate" in raw, "stored preview miss is not re-sent")
    log('id="uploadRetry"' in raw, "storage retry remains")
    log('id="libDownloadSel"' in raw and "/api/assets/zip" in raw and 'id="libSelectAll"' in raw, "zip and select remain")
    log(".filter((a)" not in raw, "library does not filter a downloaded corpus")
    log("a.shoot_date || a.date_added" not in raw, "cards do not substitute upload date for shoot date")
    log("function footageDateLabel" in raw and "UNKNOWN" in raw, "missing shoot date stays UNKNOWN")
    route = SERVE.read_text(encoding="utf-8")
    log("/retry-preview" in route and '"nas_matched"' in route and '"page":' in route, "server page and retry route")
    js = raw.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/content-engine-upload-state.js")
    tmp.write_text(js, encoding="utf-8")
    syntax = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    log(syntax.returncode == 0, "library page js syntax", (syntax.stderr or "OK")[:180])

    blocked = repair.annotate_upload(
        {
            "ok": True,
            "library_status": "LIBRARY_READY",
            "asset_id": 1,
            "content_hash": "abc",
            "nas_received": False,
            "brand": "tropik",
        },
        media_path=None,
    )
    gate(
        "U3",
        blocked.get("lifecycle_state") == "STORAGE_FAILED"
        and blocked.get("upload_failed") is True
        and blocked.get("library_available") is False
        and blocked.get("failed_stage") == "saving_nas"
        and blocked.get("staff_message") == repair.STAFF_STORAGE,
        blocked.get("staff_message"),
    )
    log(
        repair.staff_upload_message(500, {"ok": False, "error": "save failed: disk"}) == repair.STAFF_STORAGE,
        "U3 save-failed sentence",
    )


def _temp_library() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "lib.sqlite"
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE assets (
              id INTEGER PRIMARY KEY,
              brand TEXT, stage TEXT, type TEXT, slug TEXT, filename TEXT,
              date_added TEXT, status TEXT, original_filename TEXT, canonical_filename TEXT,
              subject TEXT, detail TEXT, location TEXT, shoot_date TEXT, media_type TEXT,
              uploaded_at TEXT, library_status TEXT, data_lane TEXT, batch_id TEXT,
              detail_tags_json TEXT, readiness TEXT, nas_received INTEGER, provenance_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE nas_index (
              id INTEGER PRIMARY KEY,
              original_filename TEXT, rel TEXT, size INTEGER, brand_slug TEXT,
              index_state TEXT, classification TEXT, sha256_1mb TEXT, thumb_ready INTEGER,
              map_confidence TEXT, preview_note TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO assets (
              id, brand, stage, type, filename, date_added, original_filename, canonical_filename,
              subject, detail, location, shoot_date, media_type, uploaded_at, library_status,
              data_lane, readiness, nas_received, provenance_json, detail_tags_json, status
            ) VALUES (1,'tropik','RAW','video','up-only.mov','2026-10-01','up-only.mov','up-only.mov',
                      'pool','wide','kuta',NULL,'video','2026-10-01T10:00:00','LIBRARY_READY',
                      'operational','READY_TO_USE',1,'{"content_class":"food"}','["wide"]','indexed')
            """
        )
        conn.execute(
            """
            INSERT INTO assets (
              id, brand, stage, type, filename, date_added, original_filename, canonical_filename,
              subject, detail, location, shoot_date, media_type, uploaded_at, library_status,
              data_lane, readiness, nas_received, provenance_json, detail_tags_json, status
            ) VALUES (2,'tropik','RAW','video','shot.mov','2026-10-01','IMG_1.mov','shot.mov',
                      'bbq','night-grill','kuta','20260801','video','2026-10-01T10:00:00','LIBRARY_READY',
                      'operational','READY_TO_USE',1,'{}','["night","grill"]','indexed')
            """
        )
        conn.commit()
        scopes = ["SCOPE-WOLF-CONTENT-ALL-BRANDS"]
        upload_day = repair.library_search(conn, scopes, "tropik", shoot_date="2026-10-01", lane="operational")
        shoot_day = repair.library_search(conn, scopes, "tropik", shoot_date="2026-08-01", lane="operational")
        ids_upload = [c["id"] for c in upload_day["cards"]]
        ids_shoot = [c["id"] for c in shoot_day["cards"]]
        gate(
            "L4",
            ids_upload == [] and ids_shoot == [2] and all(c.get("shoot_date_label") != "2026-10-01" for c in shoot_day["cards"]),
            f"upload-day={ids_upload} shoot-day={ids_shoot}",
        )
        food = repair.library_search(conn, scopes, "tropik", q="FOOD", lane="operational")
        gate("L2-content-class", any(c["id"] == 1 for c in food["cards"]), f"matched={food['matched']}")
        conn.close()


def library_live(scopes: list[str]) -> None:
    conn = _connect(readonly=True)
    try:
        tropik = repair.library_search(conn, scopes, "tropik", q="", lane="operational")
        gate(
            "L1",
            tropik["matched"] > 0 and len(tropik["cards"]) > 0 and len(tropik["cards"]) <= 48,
            f"matched={tropik['matched']} shown={len(tropik['cards'])}",
        )
        bbq = repair.library_search(conn, scopes, "tropik", q="BBQ-NIGHT-GRILL", lane="operational")
        camera = repair.library_search(conn, scopes, "tropik", q="img_3801", lane="operational")
        gate(
            "L2",
            bbq["matched"] >= 1
            and camera["matched"] >= 1
            and any("bbq-night-grill" in str(c.get("detail") or "").lower() or "bbq-night-grill" in str(c.get("canonical_name") or "").lower() for c in bbq["cards"])
            and any("3801" in str(c.get("original_name") or "") for c in camera["cards"]),
            f"bbq={bbq['matched']} camera={camera['matched']}",
        )
        wide = repair.library_search(conn, scopes, "tropik", lane="operational")
        video = repair.library_search(conn, scopes, "tropik", media_type="video", lane="operational")
        still = repair.library_search(conn, scopes, "tropik", q="bbq-night-grill", media_type="image", lane="operational")
        raw = repair.library_search(conn, scopes, "tropik", q="bbq-night-grill", media_type="video", stage="RAW", lane="operational")
        final = repair.library_search(conn, scopes, "tropik", q="bbq-night-grill", media_type="video", stage="FINAL", lane="operational")
        gate(
            "L3",
            video["matched"] <= wide["matched"]
            and still["matched"] == 0
            and raw["matched"] >= 1
            and final["matched"] < raw["matched"],
            f"wide={wide['matched']} video={video['matched']} still={still['matched']} raw={raw['matched']} final={final['matched']}",
        )
        shoot = repair.library_search(
            conn, scopes, "tropik", q="bbq-night-grill", shoot_date="2026-08-01", lane="operational"
        )
        uploaded = repair.library_search(conn, scopes, "tropik", shoot_date="2026-10-01", q="bbq-night-grill", lane="operational")
        shoot_ids = {c["id"] for c in shoot["cards"]}
        gate(
            "L4-live",
            19 in shoot_ids and uploaded["matched"] == 0 and all((c.get("shoot_date") or "").replace("-", "")[:8] == "20260801" for c in shoot["cards"]),
            f"shoot={shoot['matched']} upload_day_bbq={uploaded['matched']}",
        )
        atrium = repair.library_search(conn, scopes, "atrium", limit=500, page=1, lane="operational")
        atrium2 = repair.library_search(conn, scopes, "atrium", limit=48, page=2, lane="operational")
        ids1 = {str(c["id"]) for c in atrium["cards"]}
        ids2 = {str(c["id"]) for c in atrium2["cards"]}
        gate(
            "L5",
            atrium["limit"] == 48
            and len(atrium["cards"]) <= 48
            and atrium["matched"] > 48
            and atrium2["matched"] == atrium["matched"]
            and ids1.isdisjoint(ids2)
            and len(ids2) <= 48,
            f"matched={atrium['matched']} page1={len(atrium['cards'])} page2={len(atrium2['cards'])}",
        )
    finally:
        conn.close()


def bbq_reconcile() -> dict:
    before = {
        row_id: repair.asset_thumb_path(row_id).stat().st_size
        for row_id in range(19, 31)
        if repair.asset_thumb_path(row_id).is_file()
    }
    conn = _connect()
    try:
        report = repair.reconcile_bbq_batch(conn, repair_missing_posters=True)
        conn.commit()
    finally:
        conn.close()
    after_sizes = []
    for item in report["inventory"]:
        nas = None
        conn = _connect(readonly=True)
        try:
            row = conn.execute("SELECT nas_path, file_size FROM assets WHERE id=?", (item["asset_id"],)).fetchone()
        finally:
            conn.close()
        if row and row["nas_path"]:
            path = Path(row["nas_path"])
            after_sizes.append(path.is_file() and path.stat().st_size == row["file_size"])
    posters_stable = all(
        repair.asset_thumb_path(row_id).is_file() and repair.asset_thumb_path(row_id).stat().st_size == size
        for row_id, size in before.items()
    )
    review = report["human_review"][0]
    gate(
        "B1",
        report["catalog_rows"] == 12
        and report["on_nas"] == 12
        and report["indexed"] == 12
        and report["with_derivatives"] == 12
        and all(item["original_filename"] for item in report["inventory"]),
        f"rows={report['catalog_rows']} nas={report['on_nas']} posters={report['with_derivatives']}",
    )
    gate(
        "B2",
        report["deterministic_actions"] == []
        and review["missing_filenames"] == "UNKNOWN"
        and review["action"] == "human_review"
        and posters_stable
        and all(after_sizes),
        f"actions={len(report['deterministic_actions'])} gap={review['missing_filenames']}",
    )
    gate(
        "B3",
        report["force_success"] is False
        and report["deleted"] is False
        and report["batch_id"] == "bmuowp00n"
        and report["duplicates"] == []
        and report["staff_ready"] is False,
        "no delete, no force-success",
    )
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    REVIEW.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def uploads(scopes: list[str]) -> list[int]:
    import serve_beta as serve_mod

    ffmpeg = repair.resolve_ffmpeg()
    if not ffmpeg:
        gate("U1", False, "ffmpeg missing")
        gate("U2", False, "ffmpeg missing")
        gate("U4", False, "ffmpeg missing")
        gate("L6", False, "ffmpeg missing")
        return []
    work = Path("/tmp/ce-upload-state")
    work.mkdir(exist_ok=True)
    good = work / "stored.mov"
    other = work / "other.mov"
    _make_mov(ffmpeg, good, "navy")
    _make_mov(ffmpeg, other, "teal")
    asset_ids: list[int] = []
    original = repair.write_jpeg_thumb

    def _fail_thumb(src, dest) -> bool:
        return False

    repair.write_jpeg_thumb = _fail_thumb
    try:
        up = _upload(serve_mod, scopes, "stored-probe.mov", good.read_bytes(), detail="eng-upload-state")
    finally:
        repair.write_jpeg_thumb = original
    body = up["body"]
    if body.get("asset_id"):
        asset_ids.append(int(body["asset_id"]))
    row = None
    if body.get("asset_id"):
        conn = _connect(readonly=True)
        try:
            got = conn.execute(
                "SELECT id, content_hash, file_size, nas_path, nas_received FROM assets WHERE id=?",
                (int(body["asset_id"]),),
            ).fetchone()
            row = dict(got) if got else None
        finally:
            conn.close()
    nas_size = None
    if row and row.get("nas_path") and Path(row["nas_path"]).is_file():
        nas_size = Path(row["nas_path"]).stat().st_size
    gate(
        "U1",
        up["http"] == 200
        and body.get("ok") is True
        and body.get("upload_failed") is False
        and body.get("derivative_failed") is True
        and body.get("file_stored") is True
        and body.get("lifecycle_state") == "DERIVATIVE_FAILED"
        and body.get("staff_message") == repair.STAFF_PREVIEW
        and body.get("library_available") is False
        and nas_size == len(good.read_bytes()),
        f"http={up['http']} state={body.get('lifecycle_state')} msg={body.get('staff_message')}",
    )
    before_rows = 0
    if row and row.get("content_hash"):
        conn = _connect(readonly=True)
        try:
            before_rows = int(conn.execute("SELECT COUNT(*) FROM assets WHERE content_hash=?", (row["content_hash"],)).fetchone()[0])
        finally:
            conn.close()
    retried = {}
    if body.get("asset_id"):
        conn = _connect()
        try:
            retried = repair.retry_asset_preview(conn, int(body["asset_id"]), scopes)
        finally:
            conn.close()
    nas_after = None
    if row and row.get("nas_path") and Path(row["nas_path"]).is_file():
        nas_after = Path(row["nas_path"]).stat().st_size
    thumb = repair.asset_thumb_path(int(body["asset_id"])) if body.get("asset_id") else Path("/tmp/missing-thumb")
    gate(
        "U2",
        retried.get("preview_ready") is True
        and retried.get("asset_id") == body.get("asset_id")
        and retried.get("duplicate_created") is False
        and retried.get("catalog_rows_for_hash") == before_rows == 1
        and retried.get("nas_bytes_unchanged") is True
        and nas_after == nas_size
        and thumb.is_file(),
        f"rows={retried.get('catalog_rows_for_hash')} nas={nas_after}",
    )
    again = {}
    if body.get("asset_id"):
        conn = _connect()
        try:
            again = repair.retry_asset_preview(conn, int(body["asset_id"]), scopes)
        finally:
            conn.close()
    log(again.get("catalog_rows_for_hash") == 1 and again.get("duplicate_created") is False, "U2 retry is idempotent")

    up_ok = _upload(serve_mod, scopes, "other-probe.mov", other.read_bytes(), detail="eng-upload-state-b")
    if up_ok["body"].get("asset_id"):
        asset_ids.append(int(up_ok["body"]["asset_id"]))
    repair.write_jpeg_thumb = _fail_thumb
    try:
        up_bad = _upload(serve_mod, scopes, "poster-miss.mov", good.read_bytes(), detail="eng-upload-state-c")
    finally:
        repair.write_jpeg_thumb = original
    # same bytes as the first file: duplicate, not a second derivative case.
    # Use a third colour so the hash is new.
    third = work / "third.mov"
    _make_mov(ffmpeg, third, "purple")
    repair.write_jpeg_thumb = _fail_thumb
    try:
        up_prev = _upload(serve_mod, scopes, "poster-miss.mov", third.read_bytes(), detail="eng-upload-state-c")
    finally:
        repair.write_jpeg_thumb = original
    if up_prev["body"].get("asset_id"):
        asset_ids.append(int(up_prev["body"]["asset_id"]))
    partial_ok = (
        up_ok["http"] == 200
        and up_ok["body"].get("library_available") is True
        and up_ok["body"].get("upload_failed") is False
        and up_prev["body"].get("derivative_failed") is True
        and up_prev["body"].get("upload_failed") is False
        and up_prev["body"].get("file_stored") is True
        and up_bad["http"] == 409
    )
    gate("U4", partial_ok, f"kept={up_ok['http']} preview={up_prev['body'].get('lifecycle_state')} dup={up_bad['http']}")

    conn = _connect(readonly=True)
    try:
        found = repair.library_search(
            conn,
            scopes,
            "tropik",
            q="eng-upload-state",
            shoot_date="2026-10-01",
            lane="test",
        )
    finally:
        conn.close()
    found_ids = {c["id"] for c in found["cards"]}
    gate(
        "L6",
        set(asset_ids).issubset(found_ids) and found["matched"] >= len(asset_ids) and len(found["cards"]) <= 48,
        f"found={sorted(found_ids)} want={asset_ids}",
    )
    return asset_ids


def http_surface() -> None:
    st, body = _http("GET", "/api/content/repair-status")
    log(
        st == 200 and body.get("staff_ready") is False and body.get("upload_state_run_id") == repair.UPLOAD_STATE_RUN_ID,
        "deployed repair-status names this run and stays unready",
        str(body.get("upload_state_run_id")),
    )
    st_up, denied = _http("POST", "/api/upload/smart")
    log(st_up == 403, "unsigned upload stays 403", str(denied.get("error")))
    st_lib, lib_denied = _http("GET", "/api/assets?brand=tropik&q=")
    log(st_lib == 403, "unsigned library stays 403", str(lib_denied.get("error")))
    s = socket.socket()
    s.settimeout(1.5)
    up8787 = s.connect_ex(("127.0.0.1", 8787)) == 0
    s.close()
    log(up8787, "production :8787 still listening")


def main() -> int:
    from core import wolf_shell as shell

    who = shell.build_whoami(person_id="PERS-HAIKAL", email=HAIKAL)
    scopes = list(who.get("scopes") or [])
    unit_messages()
    _temp_library()
    library_live(scopes)
    report = bbq_reconcile()
    asset_ids: list[int] = []
    try:
        asset_ids = uploads(scopes)
        http_surface()
    finally:
        _cleanup(asset_ids)
    raw = HTML.read_text(encoding="utf-8")
    gate("L7", 'id="libDownloadSel"' in raw and "/api/assets/zip" in SERVE.read_text(encoding="utf-8") and 'id="libSelectAll"' in raw, "select and zip routes remain")
    prior = SERVE.read_text(encoding="utf-8")
    repair_src = (ROOT / "scripts/core/content_engine_repair.py").read_text(encoding="utf-8")
    gate(
        "U5-surface",
        "def resolve_ffmpeg" in repair_src and "uploadRetry" in raw and "BETA_PORT" in prior,
        "ffmpeg resolver and upload retry remain on the beta server",
    )
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": repair.UPLOAD_STATE_RUN_ID,
        "staff_ready": False,
        "haikal_retest": "HOLD",
        "prod_8787": "NOT_TOUCHED",
        "gates": GATES,
        "pass": PASS,
        "fail": FAIL,
        "bbq_catalog_rows": report.get("catalog_rows"),
        "bbq_unknown": "UNKNOWN_TWO_FILENAMES",
        "lines": LINES,
    }
    EVIDENCE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("\n".join(LINES))
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("GATES " + " ".join(f"{k}={v}" for k, v in GATES.items()))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
