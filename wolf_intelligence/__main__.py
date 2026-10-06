"""CLI: python -m wolf_intelligence <cmd>"""
from __future__ import annotations

import argparse
import json
import sys

from .paths import ensure_dirs


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

    gov = sub.add_parser("governance")
    gov_sub = gov.add_subparsers(dest="gov_cmd", required=True)
    gov_sub.add_parser("status")
    g_reset = gov_sub.add_parser("reset-penalty")
    g_reset.add_argument("--actor", required=True)
    g_dec = gov_sub.add_parser("decide")
    g_dec.add_argument("--task-class", required=True)
    g_dec.add_argument("--id", default=None)
    g_dec.add_argument("--grok-reason", default=None)
    g_dec.add_argument("--justification", default=None)
    g_dec.add_argument("--now", default=None)

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
    if args.cmd == "governance":
        if args.gov_cmd == "status":
            from .allocation import load_tightening, new_orchestrator_session
            ctx = new_orchestrator_session()
            pl = ctx["policy_load"]
            tightening = load_tightening(pl.policy)
            print(json.dumps({
                "policy_mode": pl.mode,
                "policy_sha256": pl.sha256,
                "policy_sha256_prefix": pl.sha256[:12] if pl.sha256 else "",
                "policy_id": (pl.policy or {}).get("policy_id"),
                "capacity": ctx["capacity"],
                "grok_routing_penalty": tightening.get("grok_routing_penalty", 0.0),
                "errors": pl.errors,
            }, indent=2))
            return 0
        if args.gov_cmd == "reset-penalty":
            from .allocation import reset_penalty
            from .governance import load_policy
            pl = load_policy()
            result = reset_penalty(args.actor, pl.policy)
            print(json.dumps(result, indent=2))
            return 0
        if args.gov_cmd == "decide":
            from .allocation import decide_and_record
            wi = {
                "id": args.id or "cli-decide",
                "task_class": args.task_class,
                "grok_reason_code": args.grok_reason,
                "grok_justification": args.justification,
            }
            dec = decide_and_record(wi, now=args.now)
            print(json.dumps(dec.to_dict(), indent=2))
            return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
