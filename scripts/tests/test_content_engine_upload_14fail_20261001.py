#!/usr/bin/env python3
"""BF-content-engine-haikal-upload-14fail-20261001 — shared upload repair.

Unit checks always. Live E1–E8 against Beta :8788 when --live is passed.
Does not touch :8787. Does not mark the Haikal bbq batch successful.
staff_ready stays false.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import content_engine_repair as repair  # noqa: E402

HTML = ROOT / "dashboards" / "content-2.0.html"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
HAIKAL = "haikalqilbari123@gmail.com"
BASE = "http://127.0.0.1:8788"
PASS = 0
FAIL = 0
LINES: list[str] = []


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        LINES.append(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        LINES.append(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def unit() -> None:
    saved = os.environ.get("PATH", "")
    os.environ["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    try:
        ffmpeg = repair.resolve_ffmpeg()
    finally:
        os.environ["PATH"] = saved
    log(bool(ffmpeg) and Path(ffmpeg).is_file(), "ffmpeg resolves when PATH is launchd-stripped", str(ffmpeg))

    log(repair.staff_upload_message(413, {"error": "upload exceeds 1 byte limit"}) == repair.STAFF_TOO_LARGE, "staff too-large")
    log(repair.staff_upload_message(415, {"error": "unsupported media type / extension: .txt"}) == repair.STAFF_UNSUPPORTED, "staff unsupported")
    log(repair.staff_upload_message(409, {"error": "possible_duplicate", "duplicate": True}) == repair.STAFF_ALREADY, "staff already in library")
    log(repair.staff_upload_message(500, {"failed_stage": "saving_nas", "ok": False}) == repair.STAFF_STORAGE, "staff storage")
    log(repair.staff_upload_message(200, {"ok": True, "failed_stage": "thumbnail", "library_available": False}) == repair.STAFF_PREVIEW, "staff preview miss")
    log(repair.staff_upload_message(200, {"library_available": True}) == repair.STAFF_SAVED, "staff saved")

    raw = HTML.read_text(encoding="utf-8")
    for sentence in (
        repair.STAFF_TOO_LARGE,
        repair.STAFF_UNSUPPORTED,
        repair.STAFF_STORAGE,
        repair.STAFF_INTERRUPTED,
        repair.STAFF_ALREADY,
        repair.STAFF_PREVIEW,
        repair.STAFF_RETRY,
    ):
        log(sentence in raw, f"page has staff sentence: {sentence[:40]}")
    log('id="uploadRetry"' in raw, "retry control remains")
    log("possible_duplicate" in raw and "savedDespitePoster" in raw, "retry will not re-send a file that already landed")
    js = raw.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/content-engine-14fail.js")
    tmp.write_text(js, encoding="utf-8")
    syntax = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    log(syntax.returncode == 0, "upload page js syntax", (syntax.stderr or "OK")[:200])

    if not ffmpeg:
        log(False, "video poster under stripped PATH", "no ffmpeg binary")
        return
    probe = Path("/tmp/ce-14fail-unit.mov")
    made = subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=black:s=160x90:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-f", "mov", str(probe)],
        capture_output=True,
        timeout=30,
    )
    log(made.returncode == 0 and probe.is_file(), "synthetic mov for poster", (made.stderr or b"")[-180:].decode("utf-8", "replace"))
    dest = Path("/tmp/ce-14fail-unit.jpg")
    dest.unlink(missing_ok=True)
    os.environ["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    try:
        ok = repair.write_jpeg_thumb(probe, dest)
    finally:
        os.environ["PATH"] = saved
    log(ok and dest.is_file() and dest.read_bytes()[:2] == b"\xff\xd8", "poster jpeg written without ffmpeg on PATH")


def _http(method: str, path: str, *, raw: bytes | None = None, content_type: str | None = None, headers: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(BASE + path, data=raw, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = {"raw": raw_body[:300]}
        return exc.code, body


def _multipart(fields: dict, filename: str, data: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = "----Wolf14Fail"
    chunks = []
    for key, val in fields.items():
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{val}\r\n".encode()
        )
    chunks.append(
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        + data
        + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _make_mov(ffmpeg: str, dest: Path, color: str) -> None:
    proc = subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c={color}:s=160x90:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-f", "mov", str(dest)],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0 or not dest.is_file():
        raise RuntimeError((proc.stderr or b"")[-200:].decode("utf-8", "replace"))


def _row(asset_id: int) -> dict | None:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, brand, canonical_filename, content_hash, file_size, nas_path, nas_received, v2_path, data_lane, batch_id, library_status FROM assets WHERE id=?",
            (asset_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _count_hash(content_hash: str) -> int:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM assets WHERE content_hash=?", (content_hash,)).fetchone()[0])
    finally:
        conn.close()


def _cleanup(asset_ids: list[int], batch_id: str) -> None:
    conn = sqlite3.connect(str(CATALOG))
    conn.row_factory = sqlite3.Row
    try:
        for asset_id in asset_ids:
            row = conn.execute(
                "SELECT id, data_lane, batch_id, v2_path, nas_path FROM assets WHERE id=?",
                (asset_id,),
            ).fetchone()
            if not row:
                continue
            if row["data_lane"] != "test" or row["batch_id"] != batch_id:
                continue
            for key in ("v2_path", "nas_path"):
                p = row[key]
                if p and "eng-probe-14fail" in str(p):
                    Path(p).unlink(missing_ok=True)
            conn.execute("DELETE FROM assets WHERE id=? AND data_lane='test' AND batch_id=?", (asset_id, batch_id))
        conn.execute("DELETE FROM staged_assets WHERE batch_id=? AND data_lane='test'", (batch_id,))
        conn.commit()
    finally:
        conn.close()


def _inprocess_upload(serve_mod, scopes: list[str], fields: dict, filename: str, data: bytes, content_type: str = "video/quicktime") -> dict:
    payload = {
        "file": {"filename": filename, "data": data, "content_type": content_type},
        **fields,
    }
    saved = os.environ.get("PATH", "")
    os.environ["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    try:
        result = __import__("smart_upload").handle_smart_upload(
            payload, subject=HAIKAL, serve_mod=serve_mod, scopes=scopes
        )
    finally:
        os.environ["PATH"] = saved
    body = result["body"]
    http = int(result["http"])
    if isinstance(body, dict):
        body["staff_message"] = body.get("staff_message") or repair.staff_upload_message(http, body)
    return {"http": http, "body": body}


def live() -> dict:
    """E1–E8. HTTP on :8788 is fail-closed without a Cloudflare JWT.

    The byte pipeline is proved in-process with the launchd PATH
    (/usr/bin:/bin:/usr/sbin:/sbin) against the same modules the restarted
    serve loaded. Probe rows are removed afterwards. The bbq batch is not marked successful.
    """
    evidence: dict = {"gates": {}, "staff_ready": False, "http_note": ""}
    ffmpeg = repair.resolve_ffmpeg()
    if not ffmpeg:
        log(False, "E1 live", "ffmpeg missing")
        return evidence
    work = Path("/tmp/ce-14fail-live")
    work.mkdir(exist_ok=True)
    single = work / "single.mov"
    _make_mov(ffmpeg, single, "black")
    batch_id = "eng-probe-14fail"
    fields = {
        "brand": "tropik",
        "stage": "RAW",
        "media_type": "video",
        "subject": "eng-probe-14fail",
        "detail": "eng-probe-14fail",
        "shoot_date": "2026-10-01",
        "data_lane": "test",
        "batch_id": batch_id,
    }
    headers = {"X-Wolf-Subject": HAIKAL}
    st_deny, deny_body = _http("POST", "/api/upload/smart", raw=b"{}", content_type="application/json", headers=headers)
    evidence["http_without_jwt"] = {"status": st_deny, "error": deny_body.get("error")}
    log(st_deny == 403 and deny_body.get("error") == "missing_auth", "deployed :8788 denies upload without Cloudflare JWT", str(deny_body.get("error")))
    st_stat, stat_body = _http("GET", "/api/content/repair-status")
    evidence["repair_status"] = {
        "http": st_stat,
        "ffmpeg_resolved": stat_body.get("ffmpeg_resolved"),
        "staff_ready": stat_body.get("staff_ready"),
        "run_id": stat_body.get("run_id"),
    }
    log(
        st_stat == 200 and stat_body.get("ffmpeg_resolved") is True and stat_body.get("staff_ready") is False,
        "deployed repair-status sees ffmpeg and stays unready",
        str(evidence["repair_status"]),
    )
    import serve_beta as serve_mod
    from core import wolf_shell as shell

    who = shell.build_whoami(person_id="PERS-HAIKAL", email=HAIKAL)
    scopes = list(who.get("scopes") or [])
    from core import nas_library as nas
    log(nas.scopes_allow_brand(scopes, "tropik") is True, "haikal scope allows tropik", str(scopes)[:180])
    up = _inprocess_upload(serve_mod, scopes, fields, "single-probe.mov", single.read_bytes())
    st, body = up["http"], up["body"]
    e1 = st == 200 and body.get("ok") is True and body.get("library_available") is True
    log(e1, "E1 single MOV upload", f"http={st} ok={body.get('ok')} library_available={body.get('library_available')} stage={body.get('failed_stage')} msg={body.get('staff_message')}")
    evidence["gates"]["E1"] = "PASS" if e1 else "FAIL"
    evidence["e1_body_keys"] = sorted(body.keys())
    asset_ids = []
    if body.get("asset_id"):
        asset_ids.append(int(body["asset_id"]))
    canon = body.get("canonical_filename") or ""
    e3 = "tropik_RAW_video_eng-probe-14fail" in canon and canon.endswith(".mov")
    log(e3, "E3 generated naming", canon)
    evidence["gates"]["E3"] = "PASS" if e3 else "FAIL"
    e4 = body.get("brand") == "tropik"
    log(e4, "E4 brand tropik", str(body.get("brand")))
    evidence["gates"]["E4"] = "PASS" if e4 else "FAIL"
    row = _row(int(body["asset_id"])) if body.get("asset_id") else None
    nas_ok = False
    if row and row.get("nas_path"):
        nas = Path(row["nas_path"])
        disk = nas.read_bytes() if nas.is_file() else b""
        digest = hashlib.sha256(disk).hexdigest() if disk else ""
        nas_ok = nas.is_file() and nas.stat().st_size == row.get("file_size") == len(single.read_bytes()) and digest == row.get("content_hash")
        evidence["e5"] = {"nas_rel_tail": nas.name, "size": nas.stat().st_size if nas.is_file() else None, "hash_match": digest == row.get("content_hash")}
    log(nas_ok, "E5 NAS dest size and checksum", str(evidence.get("e5")))
    evidence["gates"]["E5"] = "PASS" if nas_ok else "FAIL"
    content_hash = (row or {}).get("content_hash") or ""
    before = _count_hash(content_hash) if content_hash else 0
    up2 = _inprocess_upload(serve_mod, scopes, fields, "single-probe.mov", single.read_bytes())
    st2, body2 = up2["http"], up2["body"]
    after = _count_hash(content_hash) if content_hash else 0
    nas_still = bool(row and row.get("nas_path") and Path(row["nas_path"]).is_file())
    e6 = st2 == 409 and body2.get("staff_message") == repair.STAFF_ALREADY and before == after == 1 and nas_still
    log(e6, "E6 one DB row and retry does not duplicate", f"http={st2} before={before} after={after} msg={body2.get('staff_message')}")
    evidence["gates"]["E6"] = "PASS" if e6 else "FAIL"

    colors = ("navy", "teal", "olive")
    multi_ids = []
    multi_ok = True
    for i, color in enumerate(colors, start=1):
        path = work / f"batch-{i}.mov"
        _make_mov(ffmpeg, path, color)
        up_i = _inprocess_upload(serve_mod, scopes, fields, f"batch-{i}.mov", path.read_bytes())
        st_i, body_i = up_i["http"], up_i["body"]
        if body_i.get("asset_id"):
            multi_ids.append(int(body_i["asset_id"]))
            asset_ids.append(int(body_i["asset_id"]))
        if not (st_i == 200 and body_i.get("library_available") is True and body_i.get("brand") == "tropik"):
            multi_ok = False
            evidence.setdefault("e2_fail", []).append({"i": i, "http": st_i, "stage": body_i.get("failed_stage"), "msg": body_i.get("staff_message")})
    log(multi_ok and len(multi_ids) == 3, "E2 multi-video batch", str(multi_ids))
    evidence["gates"]["E2"] = "PASS" if multi_ok and len(multi_ids) == 3 else "FAIL"

    good = work / "partial-good.mov"
    _make_mov(ffmpeg, good, "purple")
    up_g = _inprocess_upload(serve_mod, scopes, fields, "partial-good.mov", good.read_bytes())
    st_g, body_g = up_g["http"], up_g["body"]
    if body_g.get("asset_id"):
        asset_ids.append(int(body_g["asset_id"]))
    good_hash = (_row(int(body_g["asset_id"])) or {}).get("content_hash") if body_g.get("asset_id") else ""
    up_b = _inprocess_upload(serve_mod, scopes, fields, "notes.txt", b"not a video", content_type="text/plain")
    st_b, body_b = up_b["http"], up_b["body"]
    up_b2 = _inprocess_upload(serve_mod, scopes, fields, "notes.txt", b"not a video", content_type="text/plain")
    st_b2, body_b2 = up_b2["http"], up_b2["body"]
    good_after = _count_hash(good_hash) if good_hash else 0
    e7 = (
        st_g == 200
        and body_g.get("library_available") is True
        and st_b == 415
        and body_b.get("staff_message") == repair.STAFF_UNSUPPORTED
        and st_b2 == 415
        and good_after == 1
    )
    log(e7, "E7 partial batch safe and failed item retryable", f"good={st_g} bad={st_b}/{body_b.get('staff_message')} retry={st_b2} good_rows={good_after}")
    evidence["gates"]["E7"] = "PASS" if e7 else "FAIL"

    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + "/content-2.0.html", headers=headers), timeout=15) as resp:
            page_status = resp.status
    except urllib.error.HTTPError as exc:
        page_status = exc.code
    page = HTML.read_text(encoding="utf-8")
    e8 = (
        repair.STAFF_INTERRUPTED in page
        and repair.STAFF_TOO_LARGE in page
        and repair.STAFF_UNSUPPORTED in page
        and repair.STAFF_STORAGE in page
        and repair.STAFF_ALREADY in page
        and 'id="uploadRetry"' in page
        and page_status == 403
    )
    log(e8, "E8 staff errors and Retry are in the page Beta serves; unsigned GET stays 403", f"http={page_status}")
    evidence["gates"]["E8"] = "PASS" if e8 else "FAIL"
    evidence["probe_asset_ids"] = asset_ids
    evidence["bbq_batch_untouched"] = True
    _cleanup(asset_ids, batch_id)
    left = 0
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        left = int(conn.execute("SELECT COUNT(*) FROM assets WHERE batch_id=?", (batch_id,)).fetchone()[0])
        bbq = int(conn.execute("SELECT COUNT(*) FROM assets WHERE batch_id='bmuowp00n'").fetchone()[0])
    finally:
        conn.close()
    log(left == 0, "probe rows removed", str(left))
    log(bbq == 12, "haikal bbq batch still 12 rows", str(bbq))
    evidence["probe_rows_left"] = left
    evidence["bbq_rows"] = bbq
    posters = []
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        landed = conn.execute(
            "SELECT id, v2_path, nas_path, file_size FROM assets WHERE id BETWEEN 19 AND 32 ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    saved_path = os.environ.get("PATH", "")
    os.environ["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    try:
        for row in landed:
            nas = Path(row["nas_path"]) if row["nas_path"] else None
            before_size = nas.stat().st_size if nas and nas.is_file() else None
            dest = repair.asset_thumb_path(int(row["id"]))
            wrote = repair.write_jpeg_thumb(Path(row["v2_path"]), dest) if row["v2_path"] else False
            after_size = nas.stat().st_size if nas and nas.is_file() else None
            posters.append(
                {
                    "id": row["id"],
                    "poster": wrote and dest.is_file(),
                    "nas_size_unchanged": before_size == after_size == row["file_size"],
                }
            )
    finally:
        os.environ["PATH"] = saved_path
    evidence["poster_backfill"] = posters
    log(all(p["poster"] and p["nas_size_unchanged"] for p in posters) and len(posters) == 14, "posters for landed videos; NAS bytes unchanged", str(len(posters)))
    return evidence


def main() -> int:
    unit()
    evidence = None
    if "--live" in sys.argv:
        evidence = live()
        out = ROOT / "state" / "commissioning" / "evidence" / "CE-HAIKAL-UPLOAD-14FAIL-GATE-2026-10-01.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"staff_ready": False, "run_id": "BF-content-engine-haikal-upload-14fail-20261001", **(evidence or {})}, indent=2) + "\n", encoding="utf-8")
    print("\n".join(LINES))
    print(f"\n{PASS} pass / {FAIL} fail")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
