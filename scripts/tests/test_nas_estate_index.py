#!/usr/bin/env python3
"""NAS estate in-place indexer. Temp catalog only. Does not touch :8787 or NAS trees."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import nas_estate_index as idx  # noqa: E402
from core import content_engine_repair as repair  # noqa: E402

PASS = 0
FAIL = 0


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def seed_catalog(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY)")
    conn.execute(
        """
        CREATE TABLE org_brands (
          brand_id TEXT PRIMARY KEY,
          entity_id TEXT,
          display_name TEXT,
          brand_type TEXT,
          status TEXT,
          created_at TEXT,
          updated_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def path_cases(log) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        live = root / "00-Editing-Workspace-3" / "Atrium"
        stub = root / "00-Editing-Workspace" / "Atrium"
        live.mkdir(parents=True)
        pic = live / "a.jpg"
        pic.write_bytes(b"\xff\xd8\xff\xd9")
        stored = str(stub / "a.jpg")
        resolved = idx.resolve_media_path(
            stored,
            mounts=((str(root / "00-Editing-Workspace"), str(root / "00-Editing-Workspace-3")),),
            roots=(),
        )
        log(
            resolved.path is not None and resolved.path == pic and resolved.reason.startswith("remap_"),
            "stale mount remaps onto the live copy",
            resolved.reason,
        )
        literal = live / "hash%2e.jpg"
        literal.write_bytes(b"x")
        decoded = live / "hash.jpg"
        decoded.write_bytes(b"y")
        kept = idx.resolve_media_path(str(literal), mounts=(), roots=())
        log(kept.reason == "raw" and kept.path == literal, "literal percent is not unquoted first", kept.reason)
        spaced = live / "space name.jpg"
        spaced.write_bytes(b"z")
        encoded = str(live / "space%20name.jpg")
        opened = idx.resolve_media_path(encoded, mounts=(), roots=())
        log(
            opened.path is not None and opened.path == spaced and "unquote" in opened.reason,
            "url-encoded path resolves",
            opened.reason,
        )
        nfd_name = unicodedata.normalize("NFD", "café.jpg")
        nfd_file = live / nfd_name
        nfd_file.write_bytes(b"c")
        nfc_lookup = str(live / unicodedata.normalize("NFC", "café.jpg"))
        normalised = idx.resolve_media_path(nfc_lookup, mounts=(), roots=())
        log(normalised.path is not None and normalised.path.is_file(), "unicode path resolves", normalised.reason)
        folder = live / "not-a-file"
        folder.mkdir()
        as_dir = idx.resolve_media_path(str(folder), mounts=(), roots=())
        log(as_dir.reason == "missing_file:not_a_regular_file", "directory is not a media file", as_dir.reason)
        gone = idx.resolve_media_path(str(live / "no-such.jpg"), mounts=(), roots=())
        log(gone.reason == "missing_file:not_found" and gone.path is None, "true miss is not_found", gone.reason)
        rel_root = root / "library"
        rel_file = rel_root / "Atrium" / "rel.jpg"
        rel_file.parent.mkdir(parents=True)
        rel_file.write_bytes(b"r")
        relative = idx.resolve_media_path("Atrium/rel.jpg", mounts=(), roots=(rel_root,))
        log(relative.path == rel_file, "relative path joins a read root", str(relative.path))

        estate = root / "estate"
        estate.mkdir()
        catalog = root / "catalog.sqlite"
        seed_catalog(catalog)
        (estate / "manifest.tsv").write_text("", encoding="utf-8")
        (estate / "discovery.json").write_text("{}", encoding="utf-8")
        cfg = idx.Config(
            catalog=catalog,
            estate=estate,
            manifest=estate / "manifest.tsv",
            discovery=estate / "discovery.json",
        )
        old_mounts = idx.STALE_MOUNTS
        idx.STALE_MOUNTS = ((str(root / "00-Editing-Workspace"), str(root / "00-Editing-Workspace-3")),)
        try:
            conn = idx.connect(cfg)
            conn.execute(
                """
                INSERT INTO nas_index (
                  original_path, original_filename, rel, size, brand_slug, index_state, fail_reason
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (stored, "a.jpg", "Atrium/a.jpg", pic.stat().st_size, "atrium", "FAILED", "missing_file"),
            )
            conn.commit()
            first = idx.requeue_resolved_failures(cfg, conn)
            second = idx.requeue_resolved_failures(cfg, conn)
            row = conn.execute(
                "SELECT original_path, index_state, fail_reason FROM nas_index"
            ).fetchone()
            count = conn.execute("SELECT COUNT(*) FROM nas_index").fetchone()[0]
            conn.close()
        finally:
            idx.STALE_MOUNTS = old_mounts
        log(first["requeued"] == 1 and second["requeued"] == 0, "requeue is idempotent", str((first, second)))
        log(count == 1 and row["index_state"] == "INDEXED", "requeue resets a resolved row to INDEXED", row["index_state"])
        log(row["original_path"] == str(pic), "requeue stores the live path", row["original_path"])


def brand_search_cases(log) -> None:
    """Thumb then promote reaches SEARCHABLE. Search hits atrium, selo, and habitat."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        estate = root / "estate"
        thumbs = root / "thumbs"
        estate.mkdir()
        catalog = root / "catalog.sqlite"
        seed_catalog(catalog)
        library = root / "library"
        folders = {
            "atrium": library / "Atrium" / "atrium.jpg",
            "selo": library / "Selong Selo" / "selo.jpg",
            "habitat": library / "Habitat" / "habitat.jpg",
        }
        lines = []
        for _slug, path in folders.items():
            path.parent.mkdir(parents=True)
            Image.new("RGB", (8, 8), (1, 2, 3)).save(path, "JPEG")
            lines.append(
                "\t".join(
                    [
                        str(path),
                        path.name,
                        "image",
                        str(path.stat().st_size),
                        "1700000000",
                        "UNKNOWN",
                        "review_required",
                        str(library),
                    ]
                )
            )
        manifest = estate / "manifest.tsv"
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        (estate / "discovery.json").write_text(json.dumps({"files": 3}), encoding="utf-8")
        os.environ["NAS_THUMB_DIR"] = str(thumbs)
        try:
            cfg = idx.Config(
                catalog=catalog,
                estate=estate,
                manifest=manifest,
                discovery=estate / "discovery.json",
                ingest_batch=20,
                thumb_batch=10,
                hash_batch=10,
            )
            conn = idx.connect(cfg)
            aliases = idx.load_aliases(conn)
            line, finished = idx.ingest_batch(cfg, conn, aliases, 0)
            log(finished and line == 3, "three brand rows ingested", str(line))
            idx.thumb_batch(cfg, conn)
            promoted = idx.promote_searchable(conn)
            states = {
                row["brand_slug"]: row["index_state"]
                for row in conn.execute("SELECT brand_slug, index_state FROM nas_index")
            }
            log(promoted == 3 and set(states.values()) == {"SEARCHABLE"}, "rows reach SEARCHABLE", str(states))
            scopes = ["SCOPE-WOLF-CONTENT-ALL-BRANDS"]
            for brand in ("atrium", "selo", "habitat"):
                page = repair.nas_library_search(conn, scopes, brand, q=brand, limit=5)
                log(
                    int(page.get("matched") or 0) >= 1 and page.get("staff_ready") is False,
                    f"search hit {brand}",
                    str(page.get("matched")),
                )
            idx.hash_batch(cfg, conn)
            hashed = {
                row["brand_slug"]: row["index_state"]
                for row in conn.execute("SELECT brand_slug, index_state FROM nas_index")
            }
            log(set(hashed.values()) == {"HASHED"}, "SEARCHABLE rows can still be hashed", str(hashed))
            for brand in ("atrium", "selo", "habitat"):
                page = repair.nas_library_search(conn, scopes, brand, q=brand, limit=5)
                log(int(page.get("matched") or 0) >= 1, f"search still hits hashed {brand}", str(page.get("matched")))
            conn.close()
        finally:
            os.environ.pop("NAS_THUMB_DIR", None)


def main() -> None:
    aliases = {"atrium": "atrium", "selo": "selo", "habitat": "habitat", "tropik": "tropik"}
    slug, conf = idx.brand_for(["Atrium", "Footage"], aliases, "01-Media-Library")
    log(slug == "atrium" and conf == "certain", "alias maps Atrium", f"{slug} {conf}")
    slug, conf = idx.brand_for(["Selong Selo"], aliases, "01-Media-Library")
    log(slug == "selo" and conf == "alias_word", "alias word maps Selong Selo", f"{slug} {conf}")
    slug, conf = idx.brand_for(["Tropic at Selong"], aliases, "01-Media-Library")
    log(slug == "tropik" and conf == "folder_rule", "folder rule maps Tropic at Selong", f"{slug} {conf}")
    slug, conf = idx.brand_for(["GGV", "Footage"], aliases, "01-Media-Library")
    log(slug == "UNKNOWN" and conf == "review_required", "GGV stays UNKNOWN", f"{slug} {conf}")
    slug, conf = idx.brand_for(["Misc"], aliases, "02-Stock-Assets-1")
    log(slug == "SHARED_STOCK" and conf == "shared", "stock root maps shared", f"{slug} {conf}")

    try:
        idx.refuse_nas_write(Path("/Volumes/01-Media-Library/GGV/nope.jpg"))
        log(False, "NAS write refused")
    except RuntimeError:
        log(True, "NAS write refused")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        estate = root / "estate"
        thumbs = root / "thumbs"
        estate.mkdir()
        catalog = root / "catalog.sqlite"
        seed_catalog(catalog)
        media = root / "library" / "Atrium"
        media.mkdir(parents=True)
        good_a = media / "same.jpg"
        good_b = root / "library" / "Atrium-Copy" / "same.jpg"
        good_b.parent.mkdir()
        payload = b"\xff\xd8" + b"x" * 64
        # A real tiny jpeg so sips can read it.
        from PIL import Image

        Image.new("RGB", (12, 12), (10, 20, 30)).save(good_a, "JPEG")
        good_b.write_bytes(good_a.read_bytes())
        missing = media / "gone.jpg"
        manifest = estate / "manifest.tsv"
        lines = []
        for path in (good_a, good_b, missing):
            rel_root = root / "library"
            size = path.stat().st_size if path.is_file() else 10
            lines.append(
                "\t".join(
                    [
                        str(path),
                        path.name,
                        "image",
                        str(size),
                        "1700000000",
                        "atrium",
                        "certain",
                        str(rel_root),
                    ]
                )
            )
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        (estate / "discovery.json").write_text(json.dumps({"files": 3}), encoding="utf-8")
        os.environ["NAS_THUMB_DIR"] = str(thumbs)
        try:
            cfg = idx.Config(
                catalog=catalog,
                estate=estate,
                manifest=manifest,
                discovery=estate / "discovery.json",
                ingest_batch=2,
                thumb_batch=2,
                hash_batch=2,
            )
            first = idx.run(cfg)
            log(first.get("staff_ready") is False, "staff_ready false", str(first.get("staff_ready")))
            log(first.get("full_nas_complete") is False, "full NAS not claimed")
            log(int(first.get("catalog_rows") or 0) == 3, "three catalog rows", str(first.get("catalog_rows")))
            log(int(first.get("failed") or 0) >= 1, "missing file failed", str(first.get("failed")))
            log(int(first.get("duplicate_candidates") or 0) >= 1, "duplicate recorded", str(first.get("duplicate_candidates")))
            conn = sqlite3.connect(catalog)
            conn.row_factory = sqlite3.Row
            states = {
                row["original_filename"] + ":" + str(row["index_state"])
                for row in conn.execute("SELECT original_filename, index_state FROM nas_index")
            }
            hashed = conn.execute("SELECT COUNT(*) FROM nas_index WHERE index_state='HASHED'").fetchone()[0]
            log(hashed >= 1, "at least one hashed", str(hashed))
            thumbs_ready = list(thumbs.glob("nas-*.jpg"))
            log(bool(thumbs_ready), "thumb written in cache", str([p.name for p in thumbs_ready]))
            page = repair.nas_library_search(
                conn,
                ["SCOPE-WOLF-CONTENT-ALL-BRANDS"],
                "atrium",
                q="same.jpg",
                limit=10,
            )
            log(page.get("matched") == 2, "search counts both indexed copies", str(page.get("matched")))
            log(
                page.get("full_nas_complete") is False and page.get("staff_ready") is False,
                "search stays unready",
            )
            leaked = json.dumps(page["cards"])
            log("original_path" not in leaked and "/Volumes/" not in leaked, "search hides NAS paths")
            # Resume is a no-op and does not add rows.
            second = idx.run(cfg)
            again = conn.execute("SELECT COUNT(*) FROM nas_index").fetchone()[0]
            log(again == 3 and second.get("phase") == "caught_up", "resume is idempotent", str(again))
            # A row beyond a 1-page window is still counted.
            for n in range(30):
                conn.execute(
                    """
                    INSERT INTO nas_index (
                      original_path, original_filename, rel, size, brand_slug, index_state, classification
                    ) VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        str(root / f"extra-{n}.jpg"),
                        f"extra-{n}.jpg",
                        f"Atrium/extra-{n}.jpg",
                        10 + n,
                        "atrium",
                        "INDEXED",
                        "image",
                    ),
                )
            conn.commit()
            wide = repair.nas_library_search(
                conn,
                ["SCOPE-WOLF-CONTENT-ALL-BRANDS"],
                "atrium",
                q="extra-3.jpg",
                limit=5,
            )
            log(wide.get("matched") == 1, "search finds a row outside the first page sample", str(wide.get("matched")))
            conn.close()
            counts = json.loads((estate / "owner-counts.json").read_text(encoding="utf-8"))
            log(counts.get("staff_ready") is False and counts.get("full_nas_complete") is False, "owner counts honest")
            log((estate / "index-checkpoint.json").is_file(), "checkpoint written")
            src = Path(idx.__file__).read_text(encoding="utf-8")
            log("os.remove" not in src and "shutil.rmtree" not in src, "indexer has no NAS delete helpers")
            # A resolved failure is re-queued. A second pass does not add a row.
            conn = sqlite3.connect(catalog)
            before = conn.execute("SELECT COUNT(*) FROM nas_index").fetchone()[0]
            conn.execute(
                """
                UPDATE nas_index
                SET index_state='FAILED', fail_reason='missing_file'
                WHERE original_path=?
                """,
                (str(good_a),),
            )
            conn.commit()
            conn.close()
            third = idx.run(cfg)
            conn = sqlite3.connect(catalog)
            conn.row_factory = sqlite3.Row
            again = conn.execute("SELECT COUNT(*) FROM nas_index").fetchone()[0]
            healed = conn.execute(
                "SELECT index_state, fail_reason FROM nas_index WHERE original_path=?",
                (str(good_a),),
            ).fetchone()
            log(again == before, "requeue does not duplicate rows", f"{before}->{again}")
            log(
                healed["index_state"] in ("HASHED", "SEARCHABLE", "THUMB_PREVIEW_READY", "INDEXED"),
                "resolved missing_file returns to the pipeline",
                f"{healed['index_state']} phase={third.get('phase')}",
            )
            still = conn.execute(
                "SELECT index_state, fail_reason FROM nas_index WHERE original_path=?",
                (str(missing),),
            ).fetchone()
            log(
                still["index_state"] == "FAILED" and str(still["fail_reason"] or "").startswith("missing_file:"),
                "true miss stays failed with a precise reason",
                f"{still['index_state']} {still['fail_reason']}",
            )
            conn.close()
        finally:
            os.environ.pop("NAS_THUMB_DIR", None)

    path_cases(log)
    brand_search_cases(log)

    print(f"EXIT: {'SUCCESS' if FAIL == 0 else 'FAIL'} PASS={PASS} FAIL={FAIL}")
    if FAIL:
        sys.exit(1)


if __name__ == "__main__":
    main()
