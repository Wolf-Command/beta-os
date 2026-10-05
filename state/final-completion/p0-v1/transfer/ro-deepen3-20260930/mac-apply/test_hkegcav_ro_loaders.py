#!/usr/bin/env python3
"""Unit tests for deepen3 RO loaders — fail-closed + stamp contract."""
import os, sys, tempfile, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

def test_habitat_missing():
    import owner_habitat_investment_ro as m
    os.environ["BETA_HABITAT_HTML"] = "/tmp/no-such-habitat.html"
    # reload path
    m.HTML_PATH = Path("/tmp/no-such-habitat.html")
    r = m.load_habitat_investment_ro()
    assert r["ok"] is False and r["staff_ready"] is False and r["invent_financials"] is False

def test_habitat_present():
    import owner_habitat_investment_ro as m
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "h.html"
        p.write_text("<html><title>Habitat Test 2026</title><h1>Habitat</h1><h2>Units</h2>"
                     "<a href='mailto:matt@thehabitatlombok.com'>x</a>"
                     "<p>IDR 1.000.000</p></html>")
        m.HTML_PATH = p
        r = m.load_habitat_investment_ro()
        assert r["ok"] is True and r["reason"] == "V1_RO_OK"
        assert r["title"] and "Habitat" in r["title"]
        assert r["staff_ready"] is False

def test_kuta_honesty_empty_db():
    import ops_kuta_rates_ro as m, sqlite3
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "c.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE competitor_rates (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE rate_signals (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE atrium_rates (id INTEGER PRIMARY KEY, scrape_date TEXT, stay_date TEXT, room_name TEXT, rate REAL, currency TEXT)")
        conn.execute("INSERT INTO atrium_rates VALUES (1,'2026-09-30','2026-10-01','Deluxe',1000000,'IDR')")
        conn.commit(); conn.close()
        status = Path(d) / "status.json"
        status.write_text(json.dumps({"headline":"test","status":"ok","generated_at":"2026-09-30"}))
        brief = Path(d) / "kuta-rates-brief-2026-09-30.md"
        brief.write_text("# brief\nLEARN only\n")
        m.STATUS_PATH = status
        m.BRIEF_DIR = Path(d)
        m.DB_PATH = db
        r = m.load_kuta_rates_ro()
        assert r["ok"] is True and r["live_booking"] is False
        assert r["db"]["competitor_rates_empty"] is True
        assert r["db"]["table_counts"]["atrium_rates"] == 1

def test_ads_refuse_spend():
    import seats_ads_studio_ro as m
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ads.html"; p.write_text("<html>ads</html>")
        m.HTML_PATH = p
        m.DEFAULT_BRIEFS = []
        r = m.load_ads_studio_ro()
        assert r["spend"] is False and r["meta_api"] is False and r["mode"] == "LEARN_ONLY"

def test_voice_never_send():
    import voice_boards_ro as m
    r = m.load_voice_ro()
    assert r["never_send"] is True and r["mail_send"] is False and r["telegram_send"] is False

def test_gatekeeper_event_resolve_content_stamp():
    import owner_gatekeeper_ro as g, ops_event_bus_ro as e, seats_resolve_studio_ro as r, seats_content_ro as c
    for fn in (g.load_gatekeeper_ro, e.load_event_bus_ro, r.load_resolve_studio_ro, c.load_content_ro):
        out = fn()
        assert out["staff_ready"] is False
        assert out["read_only"] is True
        assert "as_of_wita" in out

if __name__ == "__main__":
    tests = [v for k,v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t(); print("PASS", t.__name__)
        except Exception as ex:
            failed += 1; print("FAIL", t.__name__, ex)
    print(f"summary {len(tests)-failed}/{len(tests)} pass, {failed} fail")
    sys.exit(1 if failed else 0)
