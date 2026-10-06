"""CLI: python -m wolf_intelligence <cmd>"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from .paths import ensure_dirs

TEST_CLOCK_ENV = "WOLF_INTELLIGENCE_GOVERNANCE_TEST_CLOCK"


def _qa_isolated_state() -> bool:
    root = os.environ.get("WOLF_INTELLIGENCE_STATE_ROOT", "")
    if not root:
        return False
    p = Path(root).resolve()
    text = str(p)
    if "/.tmp/" in text or "/qa-" in text or p.name.startswith("qa-"):
        return True
    try:
        return p.is_relative_to(Path(tempfile.gettempdir()).resolve())
    except (ValueError, OSError):
        return False


def main(argv: list[str] | None = None) -> int:
    ensure_dirs()
    p = argparse.ArgumentParser(prog="wolf_intelligence")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create")
    c.add_argument("--title", required=True)
    c.add_argument("--kind", default="generic")
    c.add_argument("--isolated", action="store_true", default=True)

    sub.add_parser("dispatch").add_argument("work_item_id")
    sub.add_parser("list")
    sub.add_parser("buckets")
    sub.add_parser("ledger")
    sub.add_parser("secret-scan")
    sub.add_parser("accept-phase1")
    sub.add_parser("worker-status")
    sub.add_parser("benchmark")
    sub.add_parser("benchmark-local")
    sub.add_parser("learn-demo")
    sub.add_parser("shadow-compare")
    shadow_real = sub.add_parser("shadow-real")
    shadow_real.add_argument("--n", type=int, default=3)
    shadow_real.add_argument("--primary", default=None)
    shadow_real.add_argument("--shadow", default=None)
    live = sub.add_parser("live-submit")
    live.add_argument("--worker", required=True)
    live.add_argument("--execute", action="store_true")
    sub.add_parser("overnight-tick")
    sub.add_parser("stats")
    sub.add_parser("serve-ui")

    orch_p = sub.add_parser("orchestrate")
    orch_sub = orch_p.add_subparsers(dest="orch_cmd", required=True)
    o_submit = orch_sub.add_parser("submit")
    o_submit.add_argument("--file", required=True, help="JSON work item file")
    orch_sub.add_parser("run")
    o_race = orch_sub.add_parser("race-proof")
    o_race.add_argument("--trials", type=int, default=250)
    o_race.add_argument("--state-root", required=True)
    o_race.add_argument("--out", default=None)
    orch_sub.add_parser("status")
    o_show = orch_sub.add_parser("show")
    o_show.add_argument("item_id")
    o_run = orch_sub.add_parser("health")
    o_run.add_argument("--now", default=None)

    fo = sub.add_parser("failover")
    fo_sub = fo.add_subparsers(dest="fo_cmd", required=True)
    fo_proof = fo_sub.add_parser("proof")
    fo_proof.add_argument("--state-root", required=True)

    gov = sub.add_parser("governance")
    gov_sub = gov.add_subparsers(dest="gov_cmd", required=True)
    gov_sub.add_parser("status")
    g_reset = gov_sub.add_parser("reset-penalty")
    g_reset.add_argument("--actor", required=True)
    g_reset.add_argument("--reason", default=None)
    g_dec = gov_sub.add_parser("decide")
    g_dec.add_argument("--task-class", required=True)
    g_dec.add_argument("--id", default=None)
    g_dec.add_argument("--requested-worker", default=None)
    g_dec.add_argument("--grok-reason", default=None)
    g_dec.add_argument("--justification", default=None)
    g_dec.add_argument("--now", default=None)
    g_scope = gov_sub.add_parser("scope-check")
    g_scope.add_argument("argv", nargs=argparse.REMAINDER)
    g_obs = gov_sub.add_parser("observe")
    g_obs.add_argument("--worker", required=True)
    g_obs.add_argument("--pool", required=True)
    g_obs.add_argument("--pct", type=float, required=True)
    g_obs.add_argument("--observed-at", required=True)
    g_obs.add_argument("--source", default="owner_observed")

    args = p.parse_args(argv)

    if args.cmd == "create":
        from . import work_items
        wi = work_items.create(title=args.title, kind=args.kind, isolated_safe=True)
        print(json.dumps(wi, indent=2))
        return 0
    if args.cmd == "dispatch":
        from . import dispatcher
        print(json.dumps(dispatcher.dispatch(args.work_item_id), indent=2))
        return 0
    if args.cmd == "list":
        from . import work_items
        print(json.dumps(work_items.list_items(), indent=2))
        return 0
    if args.cmd == "buckets":
        from . import work_items
        print(json.dumps(work_items.by_ui_bucket(), indent=2))
        return 0
    if args.cmd == "ledger":
        from . import ledger
        print(json.dumps(ledger.snapshot(), indent=2))
        return 0
    if args.cmd == "secret-scan":
        from . import scan_secrets
        r = scan_secrets.scan_tree()
        print(json.dumps(r, indent=2))
        return 0 if r["ok"] else 1
    if args.cmd == "accept-phase1":
        from . import accept_phase1
        return accept_phase1.main()
    if args.cmd == "worker-status":
        from . import phase2_workers
        print(json.dumps(phase2_workers.report(), indent=2))
        return 0
    if args.cmd == "benchmark":
        from . import benchmark
        print(json.dumps(benchmark.run_all(), indent=2))
        return 0
    if args.cmd == "benchmark-local":
        from . import benchmark_local
        print(json.dumps(benchmark_local.run_ollama_safe(), indent=2))
        return 0
    if args.cmd == "learn-demo":
        from . import learning
        print(json.dumps(learning.demo_cycle(), indent=2))
        return 0
    if args.cmd == "shadow-compare":
        from . import shadow_compare
        print(json.dumps(shadow_compare.run_compare(), indent=2))
        return 0
    if args.cmd == "shadow-real":
        from . import shadow_compare
        print(json.dumps(shadow_compare.run_real_shadow(args.n, primary_worker=args.primary, shadow_worker=args.shadow), indent=2))
        return 0
    if args.cmd == "live-submit":
        from .adapters import get_adapter
        from .adapters.live_gate import env_enabled
        from .shadow_compare import TINY_PROMPT
        from . import work_items
        if not args.execute or not env_enabled():
            print(json.dumps({
                "ok": False,
                "status": "LIVE_DISABLED",
                "provider_called": False,
                "message": "Pass --execute and set WOLF_INTELLIGENCE_LIVE_SUBMIT=1. Default is off. No provider call.",
            }, indent=2))
            return 2
        adapter = get_adapter(args.worker)
        if adapter is None:
            print(json.dumps({"ok": False, "status": "UNAVAILABLE", "message": "unknown worker"}, indent=2))
            return 2
        wi = work_items.create(
            title=f"Live submit {args.worker}",
            kind="code_debug",
            payload={"prompt": TINY_PROMPT},
            isolated_safe=True,
            tags=["live_submit", "SHADOW"],
        )
        result = adapter.submit({
            "execute": True,
            "prompt": TINY_PROMPT,
            "work_item_id": wi["id"],
            "shadow_mode": False,
            "label": "LIVE_SUBMIT",
            "ledger_note": "live submit tiny task; took_action false",
            "num_predict": 64,
        })
        public = {
            "ok": result.ok,
            "status": result.status,
            "message": result.message,
            "work_item_id": wi["id"],
            "worker": args.worker,
            "data": result.data,
            "took_action": False,
            "mode": "SHADOW",
        }
        print(json.dumps(public, indent=2))
        return 0 if result.ok else 1
    if args.cmd == "overnight-tick":
        from . import overnight_tick
        print(json.dumps(overnight_tick.run(), indent=2))
        return 0
    if args.cmd == "stats":
        from . import stats_store
        print(json.dumps(stats_store.recompute(), indent=2))
        return 0
    if args.cmd == "serve-ui":
        from . import owner_ui_server
        return owner_ui_server.main()
    if args.cmd == "orchestrate":
        from . import orchestrator as orch

        if args.orch_cmd == "submit":
            item = json.loads(Path(args.file).read_text(encoding="utf-8"))
            print(json.dumps(orch.submit(item), indent=2))
            return 0
        if args.orch_cmd == "run":
            out = orch.run_until_idle()
            print(json.dumps(out, indent=2))
            return 1 if out.get("error") else 0
        if args.orch_cmd == "race-proof":
            from .race_proof import run_race_proof

            result = run_race_proof(trials=args.trials, state_root=args.state_root, out_file=args.out)
            print(json.dumps(result, indent=2))
            return 0 if result.get("pass") else 1
        if args.orch_cmd == "status":
            print(json.dumps(orch.status(), indent=2))
            return 0
        if args.orch_cmd == "show":
            rec = orch.show(args.item_id)
            if rec is None:
                print(json.dumps({"ok": False, "error": "not_found"}, indent=2))
                return 1
            print(json.dumps(rec, indent=2))
            return 0
        if args.orch_cmd == "health":
            h = orch.health(now=args.now)
            print(json.dumps(h, indent=2))
            return 0 if h.get("ok") else 1
    if args.cmd == "failover":
        from . import failover as fo_mod
        from .paths import rebind_state_paths

        if args.fo_cmd == "proof":
            os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = args.state_root
            rebind_state_paths()
            from . import orchestrator as orch

            orch.rebind_orchestrator_paths()
            out = fo_mod.run_proof(args.state_root)
            print(json.dumps(out, indent=2))
            return 0 if all(v == "PASS" for v in out["scenarios"].values()) else 1
    if args.cmd == "governance":
        if args.gov_cmd == "status":
            from .allocation import load_tightening, new_orchestrator_session
            ctx = new_orchestrator_session()
            pl = ctx["policy_load"]
            tightening = load_tightening(pl.policy)
            policy = pl.policy or {}
            print(json.dumps({
                "policy_mode": pl.mode,
                "policy_sha256": pl.sha256,
                "policy_sha256_prefix": pl.sha256[:12] if pl.sha256 else "",
                "policy_id": policy.get("policy_id"),
                "capacity": ctx["capacity"],
                "grok_routing_penalty": tightening.get("grok_routing_penalty", 0.0),
                "grok_conserve_conduct": policy.get("grok_conserve_conduct"),
                "velocity": policy.get("velocity"),
                "errors": pl.errors,
            }, indent=2))
            return 0
        if args.gov_cmd == "reset-penalty":
            from .allocation import ResetPenaltyError, reset_penalty
            from .governance import load_policy
            pl = load_policy()
            try:
                result = reset_penalty(args.actor, pl.policy, reason=args.reason)
            except ResetPenaltyError as exc:
                print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
                return 1
            print(json.dumps(result, indent=2))
            return 0
        if args.gov_cmd == "decide":
            from .allocation import decide_and_record
            test_clock = (
                os.environ.get(TEST_CLOCK_ENV) == "1"
                or (args.now and _qa_isolated_state())
            )
            if args.now and not test_clock:
                print(json.dumps({
                    "ok": False,
                    "error": "test_clock_refused",
                    "hint": "set WOLF_INTELLIGENCE_GOVERNANCE_TEST_CLOCK=1 to inject --now for capacity only",
                }, indent=2))
                return 2
            wi = {
                "id": args.id or "cli-decide",
                "task_class": args.task_class,
                "grok_reason_code": args.grok_reason,
                "grok_justification": args.justification,
            }
            if args.requested_worker:
                wi["requested_worker"] = args.requested_worker
            dec, meta = decide_and_record(wi, now=args.now if test_clock else None)
            out = dec.to_dict()
            out.update({"clock": "test"} if test_clock and args.now else {"clock": "server"})
            print(json.dumps(out, indent=2))
            return 0
        if args.gov_cmd == "scope-check":
            from .scope_guard import scope_check_json
            argv = list(args.argv)
            if argv and argv[0] == "--":
                argv = argv[1:]
            payload = scope_check_json(argv, os.getcwd(), dict(os.environ))
            print(json.dumps(payload, indent=2))
            return 0 if payload["ok"] else 1
        if args.gov_cmd == "observe":
            from datetime import datetime

            from .capacity import TZ, record_observation

            allowed_sources = {"owner_observed", "api", "ledger_derived"}
            source = (args.source or "owner_observed").strip()
            if source not in allowed_sources:
                print(json.dumps({
                    "ok": False,
                    "error": "invalid_source",
                    "allowed": sorted(allowed_sources),
                }, indent=2))
                return 2
            if not (0 <= args.pct <= 100):
                print(json.dumps({"ok": False, "error": "invalid_pct", "pct": args.pct}, indent=2))
                return 2
            try:
                observed_dt = datetime.fromisoformat(args.observed_at)
            except ValueError:
                print(json.dumps({
                    "ok": False,
                    "error": "invalid_observed_at",
                    "observed_at": args.observed_at,
                }, indent=2))
                return 2
            if observed_dt.tzinfo is None:
                print(json.dumps({
                    "ok": False,
                    "error": "naive_observed_at",
                    "observed_at": args.observed_at,
                }, indent=2))
                return 2
            rec = record_observation(
                worker_id=args.worker.strip(),
                included_usage_pct={args.pool.strip(): float(args.pct)},
                source=source,
                observed_at=args.observed_at,
            )
            print(json.dumps({"ok": True, "observation": rec}, indent=2))
            return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
