#!/usr/bin/env python3
"""CAP-INTG-07 Secrets & Environment Separation — prove existing config. CLAIMED ≠ VERIFIED.

Filename uses environment_separation (not *secret*) so gitignore *secret* does not hide this test.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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


def main() -> int:
    env_ex = ROOT / ".env.example"
    check("env_example_exists", env_ex.is_file())
    if env_ex.is_file():
        bad = []
        for line in env_ex.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            _, _, val = s.partition("=")
            val = val.strip().strip('"').strip("'")
            if not val:
                continue
            if val.lower().startswith("sk-") or "begin private" in val.lower():
                bad.append(val[:12])
        check("env_example_no_live_secrets", not bad, str(bad))

    gi = (ROOT / ".gitignore").read_text()
    gil = gi.lower()
    check("gitignore_has_dotenv", ".env" in gi)
    check("gitignore_has_dotenv_star", ".env.*" in gi)
    check("gitignore_keeps_env_example", "!.env.example" in gi)
    check("gitignore_pem", "*.pem" in gil)
    check("gitignore_key", "*.key" in gil)
    check("gitignore_credentials", "*credentials*" in gil)
    check("gitignore_secret", "*secret*" in gil)

    r = subprocess.run(
        ["git", "ls-files", ".env", ".env.local"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    tracked = [x for x in r.stdout.splitlines() if x.strip()]
    check("dotenv_not_git_tracked", tracked == [], str(tracked))

    sacred = ROOT / "docs/RULE-Beta-Construction-Production-Sacred-2026-09-16.md"
    check("beta_prod_sacred_rule_exists", sacred.is_file())
    if sacred.is_file():
        check("beta_prod_sacred_text", "PRODUCTION IS SACRED" in sacred.read_text().upper())

    print(f"\nCAP-INTG-07 RESULT: PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
