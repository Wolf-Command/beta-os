#!/usr/bin/env python3
"""Habitat Klaviyo read-only reader. Temp sqlite only. No network."""
from __future__ import annotations

import importlib.util
import inspect
import json
import os
import shutil
import sqlite3
import sys
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

_REAL_URLOPEN = urllib.request.urlopen


def _block_urlopen(*_args, **_kwargs):
    raise AssertionError("urlopen called")


urllib.request.urlopen = _block_urlopen

import core.habitat_klaviyo_reader as reader  # noqa: E402
import core.lead_spine as ls  # noqa: E402

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG_SPINE = SCRIPTS / "migrations" / "migrate_lead_spine.py"
MIG_READER = SCRIPTS / "migrations" / "migrate_habitat_klaviyo_reader.py"
READER_PY = SCRIPTS / "core" / "habitat_klaviyo_reader.py"

ENTITY = "ENT-GGV"
BRAND = "habitat"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _fixture_count(path: Path) -> int:
    conn = sqlite3.connect(str(path))
    try:
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "core_leads" not in tabs:
            return 0
        return conn.execute(
            "SELECT COUNT(*) FROM core_leads WHERE source_system='fixture'"
        ).fetchone()[0]
    finally:
        conn.close()


class HabitatKlaviyoReaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["WOLF_TEST_MODE"] = "1"
        cls.live_fixtures = _fixture_count(LIVE_DB)
        cls.td = ROOT / "catalog" / "backups" / f"tmp-klaviyo-reader-{os.getpid()}"
        if cls.td.exists():
            shutil.rmtree(cls.td)
        cls.td.mkdir(parents=True)
        cls.tmp_db = cls.td / "content_library.sqlite"
        shutil.copy2(LIVE_DB, cls.tmp_db)
        cls.addClassCleanup(lambda: shutil.rmtree(cls.td, ignore_errors=True))

        spine = _load(MIG_SPINE, "migrate_lead_spine_for_klaviyo_reader")
        cls.mig = _load(MIG_READER, "migrate_habitat_klaviyo_reader_for_test")
        rc = spine.main([str(cls.tmp_db)])
        if rc != 0:
            raise RuntimeError(f"lead spine migrate rc={rc}")
        rc = cls.mig.main([str(cls.tmp_db)])
        if rc != 0:
            raise RuntimeError(f"klaviyo reader migrate rc={rc}")

        ls.CATALOG_DB = cls.tmp_db
        cls.conn = ls.db_connect(cls.tmp_db)
        ls.ensure_schema(cls.conn)
        reader.ensure_ledger(cls.conn)
        helpers = _load(
            SCRIPTS / "tests" / "test_lead_spine.py",
            "lead_spine_seed_helpers_klaviyo",
        )
        helpers.seed_fixture_org(cls.conn)
        cls.person = helpers.PERS_HAB
        cls.fixtures = cls.conn.execute(
            "SELECT COUNT(*) FROM core_leads WHERE source_system='fixture'"
        ).fetchone()[0]
        if cls.fixtures != 8:
            raise RuntimeError(f"expected 8 fixture leads, found {cls.fixtures}")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()
        urllib.request.urlopen = _REAL_URLOPEN
        if _fixture_count(LIVE_DB) != cls.live_fixtures:
            raise AssertionError("live fixture leads changed")
        live = sqlite3.connect(str(LIVE_DB))
        try:
            tab = live.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='core_lead_ingest_runs'"
            ).fetchone()
            if tab is not None:
                raise AssertionError("live catalog gained core_lead_ingest_runs")
            n = live.execute(
                "SELECT COUNT(*) FROM core_leads WHERE source_system='klaviyo'"
            ).fetchone()[0]
            if n != 0:
                raise AssertionError(f"live klaviyo leads={n}")
        finally:
            live.close()

    def _page(self, rows, nxt):
        data = []
        for pid, created, email in rows:
            attrs = {}
            if created is not None:
                attrs["created"] = created
            if email:
                attrs["email"] = email
            data.append({"id": pid, "attributes": attrs})
        return {"data": data, "links": {"next": nxt}}

    def _ingest(self, pages, boundary, resume=None):
        kwargs = {
            "entity_id": ENTITY,
            "brand_id": BRAND,
            "boundary_at": boundary,
            "conn": self.conn,
        }
        if resume:
            kwargs["resume_run_id"] = resume
        return reader.run_ingest(pages, **kwargs)

    def _run_for(self, boundary):
        row = self.conn.execute(
            """
            SELECT * FROM core_lead_ingest_runs
            WHERE boundary_at=?
            ORDER BY started_at DESC LIMIT 1
            """,
            (boundary,),
        ).fetchone()
        self.assertIsNotNone(row)
        return dict(row)

    def _count_source(self, source_id, system="klaviyo"):
        return self.conn.execute(
            "SELECT COUNT(*) FROM core_leads WHERE source_system=? AND source_id=?",
            (system, source_id),
        ).fetchone()[0]

    def _one(self, source_id, system="klaviyo"):
        row = self.conn.execute(
            "SELECT * FROM core_leads WHERE source_system=? AND source_id=?",
            (system, source_id),
        ).fetchone()
        return dict(row) if row else None

    def _touch_events(self, lead_id):
        return self.conn.execute(
            """
            SELECT COUNT(*) FROM core_lead_events
            WHERE lead_id=? AND event_type='human_touch_recorded'
            """,
            (lead_id,),
        ).fetchone()[0]

    def _make_touch_lead(self, source_id, source_observed_at="2026-09-18T10:00:00+08:00"):
        result = ls.ingest_observation(
            entity_id=ENTITY,
            brand_id=BRAND,
            source_system="fixture-touch",
            source_id=source_id,
            source_observed_at=source_observed_at,
            source_stage=None,
            conn=self.conn,
        )
        return result["lead"]

    def test_system_actor_cannot_record_human_touch(self) -> None:
        lead = self._make_touch_lead("touch-system")
        before = self._touch_events(lead["lead_id"])
        with self.assertRaises(ls.LeadSpineError) as ctx:
            ls.record_human_touch(
                lead["lead_id"],
                touched_at="2026-09-18T11:00:00+08:00",
                verified_person_id=self.person,
                actor_type="SYSTEM",
                conn=self.conn,
            )
        self.assertEqual(ctx.exception.code, "invalid_actor")
        again = ls.get_lead(lead["lead_id"], conn=self.conn)
        self.assertIsNone(again["first_human_touch_at"])
        self.assertEqual(self._touch_events(lead["lead_id"]), before)

    def test_missing_touched_at_cannot_record_human_touch(self) -> None:
        lead = self._make_touch_lead("touch-missing-time")
        before = self._touch_events(lead["lead_id"])
        called = {"n": 0}
        real = ls.now_utc_iso

        def wrapped():
            called["n"] += 1
            return real()

        ls.now_utc_iso = wrapped
        try:
            with self.assertRaises(ls.LeadSpineError):
                ls.record_human_touch(
                    lead["lead_id"],
                    verified_person_id=self.person,
                    actor_type="PERSON",
                    conn=self.conn,
                )
        finally:
            ls.now_utc_iso = real
        self.assertEqual(called["n"], 0)
        again = ls.get_lead(lead["lead_id"], conn=self.conn)
        self.assertIsNone(again["first_human_touch_at"])
        self.assertEqual(self._touch_events(lead["lead_id"]), before)

    def test_missing_source_observed_at_response_time_unavailable(self) -> None:
        result = ls.ingest_observation(
            entity_id=ENTITY,
            brand_id=BRAND,
            source_system="fixture-touch",
            source_id="rt-no-observed",
            conn=self.conn,
        )
        lead = result["lead"]
        self.assertTrue(lead["wolf_ingested_at"])
        self.assertIsNone(lead["source_observed_at"])
        self.conn.execute(
            "UPDATE core_leads SET first_human_touch_at=? WHERE lead_id=?",
            ("2026-09-18T12:00:00+08:00", lead["lead_id"]),
        )
        self.conn.commit()
        fresh = ls.get_lead(lead["lead_id"], conn=self.conn)
        rt = ls.response_time(fresh, conn=self.conn)
        self.assertEqual(rt["status"], "UNAVAILABLE")
        self.assertIsNone(rt["seconds"])

    def test_missing_first_human_touch_response_time_unavailable(self) -> None:
        lead = self._make_touch_lead("rt-no-touch")
        self.assertIsNone(lead["first_human_touch_at"])
        self.assertTrue(lead["source_observed_at"])
        rt = ls.response_time(lead, conn=self.conn)
        self.assertEqual(rt["status"], "UNAVAILABLE")
        self.assertIsNone(rt["seconds"])

    def test_touch_before_source_observed_at_rejected(self) -> None:
        observed = "2026-09-18T10:00:00+08:00"
        lead = self._make_touch_lead("touch-before", source_observed_at=observed)
        before = self._touch_events(lead["lead_id"])
        with self.assertRaises(ls.LeadSpineError) as ctx:
            ls.record_human_touch(
                lead["lead_id"],
                touched_at="2026-09-18T09:00:00+08:00",
                verified_person_id=self.person,
                actor_type="PERSON",
                conn=self.conn,
            )
        self.assertEqual(ctx.exception.code, "invalid_chronology")
        again = ls.get_lead(lead["lead_id"], conn=self.conn)
        self.assertIsNone(again["first_human_touch_at"])
        self.assertEqual(self._touch_events(lead["lead_id"]), before)

    def test_touch_equal_to_source_observed_at_stored(self) -> None:
        observed = "2026-09-18T10:00:00+08:00"
        lead = self._make_touch_lead("touch-equal", source_observed_at=observed)
        result = ls.record_human_touch(
            lead["lead_id"],
            touched_at=observed,
            verified_person_id=self.person,
            conn=self.conn,
        )
        self.assertEqual(result["lead"]["first_human_touch_at"], observed)
        payload = json.loads(result["event"]["payload_json"])
        self.assertEqual(payload["touched_at"], observed)
        self.assertEqual(payload["person_id"], self.person)
        self.assertEqual(result["event"]["actor_type"], "PERSON")
        self.assertEqual(result["event"]["actor_person_id"], self.person)
        self.assertEqual(result["event"]["occurred_at"], observed)

    def test_duplicate_profile_id_is_one_lead(self) -> None:
        boundary = "2026-09-01T00:00:00+08:00"
        created = "2026-09-01T02:00:00+08:00"
        nxt = "https://a.klaviyo.com/api/profiles/?page[cursor]=dup-2"
        pages = [
            self._page([("dup-1", created, "same@example.com")], nxt),
            self._page([("dup-1", created, "same@example.com")], None),
        ]
        run = self._ingest(pages, boundary)
        self.assertEqual(self._count_source("dup-1"), 1)
        self.assertEqual(run["inserted"], 1)
        self.assertEqual(run["already_present"], 1)
        self.assertEqual(run["state"], "COMPLETE")
        lead = self._one("dup-1")
        self.assertEqual(lead["source_id"], "dup-1")
        prov = json.loads(lead["provenance_json"])
        self.assertEqual(prov["email"], "same@example.com")
        self.assertNotEqual(lead["source_id"], prov["email"])

    def test_failed_second_page_does_not_advance_cursor(self) -> None:
        boundary = "2026-09-02T00:00:00+08:00"
        created = "2026-09-02T03:00:00+08:00"
        nxt = "https://a.klaviyo.com/api/profiles/?page[cursor]=fail-2"
        page1 = self._page([("fail-p1", created, None)], nxt)

        class Boom:
            def __iter__(self):
                yield page1
                raise RuntimeError("second page failed")

        with self.assertRaises(RuntimeError):
            self._ingest(Boom(), boundary)
        run = self._run_for(boundary)
        self.assertEqual(run["state"], "INCOMPLETE")
        self.assertNotEqual(run["state"], "COMPLETE")
        self.assertEqual(run["cursor_next"], nxt)
        self.assertEqual(self._count_source("fail-p1"), 1)

    def test_resume_does_not_create_second_lead(self) -> None:
        boundary = "2026-09-03T00:00:00+08:00"
        created = "2026-09-03T04:00:00+08:00"
        nxt = "https://a.klaviyo.com/api/profiles/?page[cursor]=resume-2"
        page1 = self._page([("resume-p1", created, None)], nxt)
        page2 = self._page([("resume-p2", created, None)], None)

        class Boom:
            def __iter__(self):
                yield page1
                raise RuntimeError("second page failed")

        with self.assertRaises(RuntimeError):
            self._ingest(Boom(), boundary)
        failed = self._run_for(boundary)
        self.assertEqual(failed["state"], "INCOMPLETE")
        self.assertEqual(failed["cursor_next"], nxt)
        done = self._ingest([page1, page2], boundary, resume=failed["run_id"])
        self.assertEqual(self._count_source("resume-p1"), 1)
        self.assertEqual(self._count_source("resume-p2"), 1)
        self.assertEqual(done["inserted"], 2)
        self.assertEqual(done["already_present"], 0)
        self.assertEqual(done["state"], "COMPLETE")
        self.assertEqual(int(done["errors"]), 0)

    def test_malformed_next_link_incomplete(self) -> None:
        boundary = "2026-09-04T00:00:00+08:00"
        created = "2026-09-04T05:00:00+08:00"
        page = self._page([("bad-next", created, "a@b.c")], "not-a-url")
        run = self._ingest([page], boundary)
        self.assertEqual(run["state"], "INCOMPLETE")
        self.assertNotEqual(run["state"], "COMPLETE")
        self.assertEqual(self._count_source("bad-next"), 0)
        self.assertIsNone(run["cursor_next"])

    def test_three_page_fixture_complete(self) -> None:
        boundary = "2026-09-05T00:00:00+08:00"
        created = "2026-09-05T06:00:00+08:00"
        ids = ["pg-1a", "pg-1b", "pg-2a", "pg-2b", "pg-3a", "pg-3b"]
        pages = [
            self._page(
                [(ids[0], boundary, "one@example.com"), (ids[1], created, None)],
                "https://a.klaviyo.com/api/profiles/?page[cursor]=two",
            ),
            self._page(
                [(ids[2], created, None), (ids[3], created, None)],
                "https://a.klaviyo.com/api/profiles/?page%5Bcursor%5D=three",
            ),
            self._page(
                [(ids[4], created, None), (ids[5], created, None)],
                None,
            ),
        ]
        run = self._ingest(pages, boundary)
        self.assertEqual(run["state"], "COMPLETE")
        self.assertEqual(run["pages_examined"], 3)
        detail = json.loads(run["detail_json"])
        self.assertEqual(set(detail["examined_ids"]), set(ids))
        self.assertEqual(run["records_examined"], len(ids))
        for pid in ids:
            lead = self._one(pid)
            self.assertIsNotNone(lead, pid)
            self.assertIsNone(lead["source_stage"])
            self.assertIsNone(lead["wolf_stage"])
            self.assertIsNone(lead["current_work_item_id"])
            self.assertNotEqual(lead["source_stage"], "new")
            prov = json.loads(lead["provenance_json"])
            self.assertEqual(prov["source"], "klaviyo")
            self.assertEqual(prov["clock"], "profile.created")
            self.assertEqual(prov["meaning"], "RECEIVED_BY_KLAVIYO_SOURCE")
            self.assertIn("does not prove the instant a human submitted", prov["note"].lower())
        first = self._one(ids[0])
        self.assertEqual(first["source_observed_at"], boundary)
        self.assertNotEqual(first["source_observed_at"], first["wolf_ingested_at"])
        touch = self.conn.execute(
            """
            SELECT COUNT(*) FROM core_lead_events
            WHERE lead_id=? AND event_type='human_touch_recorded'
            """,
            (first["lead_id"],),
        ).fetchone()[0]
        self.assertEqual(touch, 0)

    def test_profile_before_boundary_not_inserted(self) -> None:
        boundary = "2026-09-18T12:00:00+08:00"
        old = self._page(
            [("old-1", "2026-09-18T11:00:00+08:00", None)],
            "https://a.klaviyo.com/api/profiles/?page[cursor]=after-old",
        )
        newer = self._page(
            [("new-after-old", "2026-09-18T13:00:00+08:00", None)],
            None,
        )
        run = self._ingest([old, newer], boundary)
        self.assertEqual(self._count_source("old-1"), 0)
        self.assertEqual(self._count_source("new-after-old"), 0)
        self.assertEqual(run["skipped"], 1)
        self.assertEqual(run["inserted"], 0)
        self.assertEqual(run["pages_examined"], 1)
        self.assertEqual(run["state"], "COMPLETE")
        self.assertEqual(int(run["errors"]), 0)

    def test_mixed_page_skips_early_and_continues(self) -> None:
        boundary = "2026-09-18T12:00:00+08:00"
        mixed = self._page(
            [
                ("mix-new", "2026-09-18T13:00:00+08:00", None),
                ("mix-old", "2026-09-18T11:00:00+08:00", None),
            ],
            "https://a.klaviyo.com/api/profiles/?page[cursor]=mix-next",
        )
        nxt = self._page([("mix-next-id", "2026-09-18T14:00:00+08:00", None)], None)
        run = self._ingest([mixed, nxt], boundary)
        self.assertEqual(self._count_source("mix-old"), 0)
        self.assertEqual(self._count_source("mix-new"), 1)
        self.assertEqual(self._count_source("mix-next-id"), 1)
        self.assertEqual(run["pages_examined"], 2)
        self.assertEqual(run["state"], "COMPLETE")

    def test_missing_created_leaves_incomplete(self) -> None:
        boundary = "2026-09-06T00:00:00+08:00"
        page = self._page([("no-created", None, "a@b.c")], None)
        run = self._ingest([page], boundary)
        self.assertEqual(run["state"], "INCOMPLETE")
        self.assertNotEqual(run["state"], "COMPLETE")
        self.assertEqual(self._count_source("no-created"), 0)

    def test_reader_does_not_set_stage_or_work_item(self) -> None:
        boundary = "2026-09-07T00:00:00+08:00"
        created = "2026-09-07T08:00:00+08:00"
        before_wi = self.conn.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0]
        run = self._ingest(
            [self._page([("stage-1", created, None)], None)],
            boundary,
        )
        self.assertEqual(run["state"], "COMPLETE")
        lead = self._one("stage-1")
        self.assertIsNone(lead["source_stage"])
        self.assertIsNone(lead["wolf_stage"])
        self.assertIsNone(lead["current_work_item_id"])
        self.assertNotEqual(lead["source_stage"], "new")
        after_wi = self.conn.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0]
        self.assertEqual(before_wi, after_wi)

    def test_no_permission_grant_row_created(self) -> None:
        boundary = "2026-09-08T00:00:00+08:00"
        created = "2026-09-08T08:00:00+08:00"
        before = self.conn.execute("SELECT COUNT(*) FROM org_role_permissions").fetchone()[0]
        matt = self.conn.execute(
            "SELECT COUNT(*) FROM org_role_permissions WHERE role_id='ROLE-MATT'"
        ).fetchone()[0]
        self._ingest([self._page([("grant-1", created, None)], None)], boundary)
        after = self.conn.execute("SELECT COUNT(*) FROM org_role_permissions").fetchone()[0]
        matt_after = self.conn.execute(
            "SELECT COUNT(*) FROM org_role_permissions WHERE role_id='ROLE-MATT'"
        ).fetchone()[0]
        self.assertEqual(before, after)
        self.assertEqual(matt, matt_after)

    def test_reader_source_does_not_call_network_or_writers(self) -> None:
        src = READER_PY.read_text(encoding="utf-8").lower()
        for token in ("urlopen", "clickup", "sheets", "telegram"):
            self.assertNotIn(token, src, token)
        self.assertNotIn("habitat-lead-sync", src)
        self.assertNotIn("habitat_lead_sync", src)
        self.assertNotIn("if __name__", src)
        probe_src = inspect.getsource(reader.probe_readonly)
        self.assertNotIn("run_ingest", probe_src)
        self.assertNotIn("core_leads", probe_src)
        self.assertFalse(
            any(name == "klaviyo" or name.startswith("klaviyo.") for name in sys.modules)
        )

    def test_probe_readonly_does_not_write(self) -> None:
        created = "2026-09-09T08:00:00+08:00"
        pages = [
            self._page(
                [("probe-1", created, "p@example.com")],
                "https://a.klaviyo.com/api/profiles/?page[cursor]=probe-2",
            ),
            self._page([("probe-2", created, None)], None),
        ]

        def fetch(cursor):
            if cursor is None:
                return pages[0]
            if cursor.endswith("probe-2"):
                return pages[1]
            return None

        before = self.conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0]
        counts = reader.probe_readonly(fetch)
        after = self.conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0]
        self.assertEqual(before, after)
        self.assertEqual(counts["pages_examined"], 2)
        self.assertEqual(counts["records_examined"], 2)
        self.assertEqual(counts["errors"], 0)
        self.assertEqual(self._count_source("probe-1"), 0)

    def test_fixture_demo_leads_unchanged(self) -> None:
        n = self.conn.execute(
            "SELECT COUNT(*) FROM core_leads WHERE source_system='fixture'"
        ).fetchone()[0]
        self.assertEqual(n, 8)
        self.assertEqual(n, self.fixtures)


if __name__ == "__main__":
    unittest.main()
