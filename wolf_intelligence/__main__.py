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
    sub.add_parser("learn-demo")
    sub.add_parser("shadow-compare")
    sub.add_parser("serve-ui")

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
    if args.cmd == "learn-demo":
        from . import learning
        print(json.dumps(learning.demo_cycle(), indent=2))
        return 0
    if args.cmd == "shadow-compare":
        from . import shadow_compare
        print(json.dumps(shadow_compare.run_compare(), indent=2))
        return 0
    if args.cmd == "serve-ui":
        from . import owner_ui_server
        return owner_ui_server.main()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
