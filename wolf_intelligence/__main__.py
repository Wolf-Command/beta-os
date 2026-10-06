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
    gb = sub.add_parser("grok-bridge", help="event-driven Grok work bridge (claim/lease protocol)")
    gbs = gb.add_subparsers(dest="gb_cmd", required=True)
    o = gbs.add_parser("offer")
    o.add_argument("work_item_id")
    o.add_argument("--lease-seconds", type=int, default=1800)
    o.add_argument("--max-attempts", type=int, default=3)
    o.add_argument("--dispatcher", default="wi", help="who is dispatching (recorded in audit)")
    cl = gbs.add_parser("claim")
    cl.add_argument("work_item_id")
    cl.add_argument("--nonce", required=True)
    cl.add_argument("--claimant", required=True)
    rn = gbs.add_parser("renew")
    rn.add_argument("work_item_id")
    rn.add_argument("--lease", required=True)
    rn.add_argument("--caller", default=None, help="presenting routine identity (recorded on rejections)")
    co = gbs.add_parser("complete")
    co.add_argument("work_item_id")
    co.add_argument("--lease", required=True)
    src = co.add_mutually_exclusive_group(required=True)
    src.add_argument("--result-file")
    src.add_argument("--result-stdin", action="store_true")
    co.add_argument("--evidence-file")
    co.add_argument("--executed-by", default=None,
                    help="who actually executed the work, if not the lease holder (recorded, never inferred)")
    co.add_argument("--caller", default=None, help="presenting routine identity (recorded on rejections)")
    fa = gbs.add_parser("fail")
    fa.add_argument("work_item_id")
    fa.add_argument("--lease", required=True)
    fa.add_argument("--reason", required=True)
    fa.add_argument("--retryable", action="store_true")
    fa.add_argument("--caller", default=None, help="presenting routine identity (recorded on rejections)")
    gbs.add_parser("release-expired")
    rr = gbs.add_parser("rering")
    rr.add_argument("work_item_id")
    cr = gbs.add_parser("correct")
    cr.add_argument("seq", type=int)
    cr.add_argument("--reason", required=True)
    cr.add_argument("--actor", required=True)
    gbs.add_parser("verify-audit")
    st = gbs.add_parser("status")
    st.add_argument("work_item_id")
    au = gbs.add_parser("audit")
    au.add_argument("work_item_id", nargs="?")

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
    if args.cmd == "grok-bridge":
        return _grok_bridge(args)
    if args.cmd == "serve-ui":
        from . import owner_ui_server
        return owner_ui_server.main()
    return 2


_GB_PROTOCOL_CODES = {"ALREADY_CLAIMED", "STALE_LEASE", "NONCE_MISMATCH", "ITEM_NOT_CLAIMABLE", "ITEM_TERMINAL",
                    "ALREADY_COMPLETED", "ALREADY_FAILED", "SECRET_SHAPED_REJECTED", "RENEWAL_LIMIT",
                    "RESULT_QUARANTINED", "RESERVED_IDENTITY"}


def _grok_bridge(args) -> int:
    from . import grok_bridge as gb
    try:
        c = args.gb_cmd
        if c == "offer":
            out = gb.offer(args.work_item_id, lease_seconds=args.lease_seconds, max_attempts=args.max_attempts,
                           actor=args.dispatcher)
        elif c == "claim":
            out = gb.claim(args.work_item_id, claimant=args.claimant, nonce=args.nonce)
        elif c == "renew":
            out = gb.renew(args.work_item_id, lease_id=args.lease, caller=args.caller)
        elif c == "complete":
            if args.result_stdin:
                result = sys.stdin.buffer.read(gb.MAX_RESULT_BYTES + 1)
            else:
                with open(args.result_file, "rb") as fh:
                    result = fh.read(gb.MAX_RESULT_BYTES + 1)
            evidence = None
            if args.evidence_file:
                with open(args.evidence_file, "rb") as fh:
                    evidence = fh.read(gb.MAX_RESULT_BYTES + 1)
            out = gb.complete(args.work_item_id, lease_id=args.lease, result=result, evidence=evidence,
                              executed_by=args.executed_by, caller=args.caller)
        elif c == "fail":
            out = gb.fail(args.work_item_id, lease_id=args.lease, reason=args.reason, retryable=args.retryable,
                          caller=args.caller)
        elif c == "release-expired":
            out = gb.release_expired(actor="cli")
        elif c == "rering":
            out = gb.rering(args.work_item_id, actor="cli")
        elif c == "correct":
            out = gb.correct(args.seq, reason=args.reason, actor=args.actor)
        elif c == "verify-audit":
            out = {"code": "AUDIT_VERIFY", **gb.verify_audit_chain()}
        elif c == "status":
            out = gb.status(args.work_item_id)
        elif c == "audit":
            rows = gb.audit_rows(args.work_item_id)
            out = {"ok": True, "code": "AUDIT", "work_item_id": args.work_item_id, "rows": rows,
                   "chain": gb.verify_audit_chain()}
        else:
            out = {"ok": False, "code": "USAGE"}
    except (ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "code": "BAD_INPUT", "message": str(exc)[:200]}, sort_keys=True))
        return 2
    except gb.AuditIntegrityError as exc:
        print(json.dumps({"ok": False, "code": "AUDIT_INTEGRITY_ERROR", "message": str(exc)[:200]}, sort_keys=True))
        return 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "code": "INTERNAL_ERROR", "message": type(exc).__name__}, sort_keys=True))
        return 1
    print(json.dumps(out, sort_keys=True, default=str))
    if out.get("ok"):
        return 0
    code = out.get("code")
    if code in _GB_USAGE_CODES:
        return 2
    if code in _GB_PROTOCOL_CODES:
        return 3
    return 3


_GB_USAGE_CODES = {"NOT_FOUND", "NOT_OFFERED", "BAD_LEASE_ID", "EMPTY_RESULT", "RESULT_TOO_LARGE",
                   "NO_SUCH_AUDIT_ROW"}


if __name__ == "__main__":
    raise SystemExit(main())
