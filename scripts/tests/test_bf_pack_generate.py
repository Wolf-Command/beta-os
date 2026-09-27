#!/usr/bin/env python3
"""bf_pack_generate — continuous pack gen from fixture CR. No Matt invent.

Proves: generator produces pack from fixture CR; refuses FIN/HR/Trading;
blocks NEEDS_POLICY / unknown policy and continues elsewhere; Peaches veto
gate auto-accepts only when safety_ok + bound known. No Production. No money.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "build-factory"))

import bf_pack_generate as gen  # noqa: E402
from core import completion_register as cr  # noqa: E402
from core import founder_dep_routing as fdr  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _seed_fixture(db: Path) -> None:
    conn = cr.db_connect(db)
    # Safe engineering CRs (BZG cluster should win as largest coherent)
    for i, (cap, title, na) in enumerate(
        [
            ("CAP-BZG-01", "BZG POS orchestration", "Full POS orchestration + ESB connector maturity"),
            ("CAP-BZG-04", "BZG variance", "Variance/waste analysis machinery"),
            ("CAP-BZG-05", "BZG allocation", "Allocation engine"),
            ("CAP-GGV-04", "GGV speed-to-lead", "Governed speed-to-lead capability with tests"),
            ("CAP-AMG-04", "AMG daily ops", "Machine-generated daily ops"),
        ],
        start=1,
    ):
        cr.upsert(
            conn,
            capability=cap,
            title=title,
            entity="fixture",
            domain=f"D-{cap.split('-')[1]}",
            view_key=cap.split("-")[1],
            state="OPEN",
            blocker_class="NEEDS_ENGINEERING",
            next_action=na,
            source="test_bf_pack_generate",
        )
    # Reserved FIN / HR — must be excluded
    cr.upsert(
        conn,
        capability="CAP-FIN-01",
        title="Finance ledger",
        entity="fixture",
        domain="D-FIN — Finance",
        view_key="Core",
        state="OPEN",
        blocker_class="NEEDS_ENGINEERING",
        next_action="Build finance controls",
        source="test_bf_pack_generate",
    )
    cr.upsert(
        conn,
        capability="CAP-HR-01",
        title="HRIS broaden",
        entity="fixture",
        domain="D-HR — HR",
        view_key="Core",
        state="OPEN",
        blocker_class="NEEDS_ENGINEERING",
        next_action="HRIS broaden",
        source="test_bf_pack_generate",
    )
    # Trading-flavoured engineering row
    cr.upsert(
        conn,
        capability="CAP-CORE-11",
        title="Trading paper bridge",
        entity="fixture",
        domain="D-CORE — Core",
        view_key="Core",
        state="OPEN",
        blocker_class="NEEDS_ENGINEERING",
        next_action="Wire trading live bridge",
        dependency="trading live",
        source="test_bf_pack_generate",
    )
    # NEEDS_POLICY — block branch, continue elsewhere
    cr.upsert(
        conn,
        capability="CAP-MSC-01",
        title="MSC policy gap",
        entity="fixture",
        domain="D-MSC",
        view_key="Core",
        state="OPEN",
        blocker_class="NEEDS_POLICY",
        next_action="Unknown policy requirement for MFA",
        source="test_bf_pack_generate",
    )
    # Engineering row that mentions unknown policy in next_action — also blocked
    cr.upsert(
        conn,
        capability="CAP-INTG-07",
        title="Vault policy unknown",
        entity="fixture",
        domain="D-INTG",
        view_key="Integrations",
        state="OPEN",
        blocker_class="NEEDS_ENGINEERING",
        next_action="Blocked on unknown policy for vault rotation",
        source="test_bf_pack_generate",
    )
    conn.close()


def test_architecture_pointers() -> None:
    arch = gen.load_architecture_pointers(ROOT)
    check("architecture ok", arch["ok"] is True)
    check("master spec pointer present", any("MASTER-SPECIFICATION" in p["path"] for p in arch["pointers"]))
    check("dependency graph pointer present", any("DEPENDENCY-GRAPH" in p["path"] for p in arch["pointers"]))


def test_founder_dep_classify() -> None:
    e = fdr.classify_text("needs matt invent next pack; factory idle", has_staff_seat=True)
    check("eliminate when staff seat", e["class"] == "ELIMINATE", str(e))
    a = fdr.classify_text("continuous pack gen without matt; deterministic", has_staff_seat=True)
    check("automate continuous", a["class"] == "AUTOMATE", str(a))
    aug = fdr.classify_text("needs matt invent", has_staff_seat=False)
    check("no seat stays augment", aug["class"] == "AUGMENT", str(aug))
    ret = fdr.classify_text("retain owner control; must not agent widen CF Access", has_staff_seat=True)
    check("retain intentional", ret["class"] == "RETAIN", str(ret))
    check("retain not safe_implement", ret["safe_implement"] is False)
    raised = False
    try:
        fdr.classify_text("finance payroll trading")
    except fdr.FounderDepError:
        raised = True
    check("founder dep refuses reserved", raised)


def test_generator_from_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        db = td / "fixture.sqlite"
        deliveries = td / "docs" / "deliveries"
        bf = td / "state" / "build-factory"
        deliveries.mkdir(parents=True)
        bf.mkdir(parents=True)
        # Stub architecture pointers under temp root
        for rel in gen.ARCHITECTURE_POINTERS:
            p = td / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"# stub {rel}\n", encoding="utf-8")

        _seed_fixture(db)

        # Selection honesty
        conn = cr.db_connect(db)
        selection = gen.load_open_engineering_crs(conn)
        conn.close()
        check(
            "fixture eligible excludes reserved",
            selection["counts"]["reserved_excluded"] >= 2,
            str(selection["counts"]),
        )
        check(
            "fixture policy blocked",
            selection["counts"]["policy_blocked"] >= 1,
            str(selection["counts"]),
        )
        caps = {r.get("capability") for r in selection["eligible"]}
        check("FIN not eligible", "CAP-FIN-01" not in caps)
        check("HR not eligible", "CAP-HR-01" not in caps)
        check("trading row not eligible", "CAP-CORE-11" not in caps or all(
            "trading" not in str(r.get("next_action") or "").lower()
            and "trading" not in str(r.get("dependency") or "").lower()
            for r in selection["eligible"]
            if r.get("capability") == "CAP-CORE-11"
        ))
        # INTG policy-in-next-action should be blocked from eligible
        check(
            "unknown policy engineering blocked",
            "CAP-INTG-07" not in caps,
            str(caps),
        )
        check("BZG still eligible", "CAP-BZG-01" in caps, str(caps))
        check("GGV still eligible after policy block", "CAP-GGV-04" in caps, str(caps))

        result = gen.generate_pack(
            db_path=db,
            root=td,
            write_files=True,
            deliveries_dir=deliveries,
            proposal_path=bf / "PACK-PROPOSAL-LATEST.json",
            mission_id="test-mission",
        )
        check("generate ok", result.get("ok") is True, str(result.get("cluster")))
        check("cluster BZG family", result["cluster"].get("family") == "BZG", str(result["cluster"]))
        check("matt invent not required", result.get("matt_invent_required") is False)
        check("safety_ok", result["safety"].get("safety_ok") is True, str(result["safety"]))
        check("bound known", result["safety"].get("bound_known") is True)
        check(
            "auto accepted",
            result["proposal_gate"].get("auto_accepted") is True,
            str(result["proposal_gate"]),
        )
        check("plan written", result.get("plan") is not None and (td / result["plan"]).is_file())
        proposal = json.loads((bf / "PACK-PROPOSAL-LATEST.json").read_text(encoding="utf-8"))
        check("proposal safety_ok", proposal.get("safety_ok") is True)
        check("proposal auto_accepted", proposal.get("auto_accepted") is True)
        check("proposal veto AUTO_ACCEPTED", proposal.get("veto_status") == "AUTO_ACCEPTED")
        check("lane proposed", proposal["lane_proposal"]["lane"]["id"].startswith("auto-pack-"))
        check("no proven invent", proposal["honesty"]["invented_proven"] is False)
        check("no ready invent", proposal["honesty"]["invented_ready"] is False)
        check("no money", proposal["honesty"]["money"] is False)

        # Reserved refusal path: force FIN-only cluster must fail safety
        fin_only = {
            "ok": True,
            "family": "FIN",
            "members": [
                {
                    "id": "CR-fin",
                    "capability": "CAP-FIN-01",
                    "title": "Finance",
                    "next_action": "money",
                    "domain": "D-FIN",
                }
            ],
            "member_ids": ["CR-fin"],
            "capabilities": ["CAP-FIN-01"],
            "bound": "beta-finance-unsafe",
        }
        bad = gen.validate_safety(fin_only, plan_text="restart finance")
        check("refuses reserved FIN cluster", bad["safety_ok"] is False, str(bad))
        check("unknown bound fails", bad.get("bound_known") is False)

        # Unknown bound with otherwise safe cluster → pending veto, not auto-accept
        weird = {
            "ok": True,
            "family": "BZG",
            "members": selection["eligible"][:1],
            "member_ids": [selection["eligible"][0]["id"]],
            "capabilities": [selection["eligible"][0].get("capability")],
            "bound": "beta-unknown-bound-xyz",
        }
        weird_safety = gen.validate_safety(weird, plan_text="safe bzg loop")
        check("unknown bound not safety_ok", weird_safety["safety_ok"] is False)
        check("unknown bound not known", weird_safety["bound_known"] is False)

        # Founder dep read-model on cluster members
        rm = fdr.build_routing_read_model(result["cluster"].get("member_ids") and selection["eligible"][:3])
        # rebuild with full rows
        bzg_rows = [r for r in selection["eligible"] if str(r.get("capability") or "").startswith("CAP-BZG-")]
        rm = fdr.build_routing_read_model(bzg_rows)
        check("founder read-model ok", rm.get("ok") is True)
        check("no invent owner controls away", rm.get("invented_owner_control_away") is False)


def test_refuse_production_bound() -> None:
    cluster = {
        "ok": True,
        "family": "BZG",
        "members": [{"id": "CR-x", "capability": "CAP-BZG-01", "title": "x", "next_action": "y"}],
        "bound": "production",
    }
    safety = gen.validate_safety(cluster, plan_text="loop")
    check("production bound refused", safety["safety_ok"] is False, str(safety))


def test_empire_handoff_labels() -> None:
    from core import owner_empire_pack as empire

    packs = empire.handoffs()
    check("handoffs ok", packs.get("ok") is True)
    for card in packs.get("cards") or []:
        check(
            f"handoff {card.get('pack')} has founder_dep_class",
            card.get("founder_dep_class") in fdr.CLASSES,
            str(card),
        )
        check(
            f"handoff {card.get('pack')} no invent away",
            card.get("invented_owner_control_away") is False,
        )


def main() -> int:
    global PASS, FAIL
    test_architecture_pointers()
    test_founder_dep_classify()
    test_generator_from_fixture()
    test_refuse_production_bound()
    test_empire_handoff_labels()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
