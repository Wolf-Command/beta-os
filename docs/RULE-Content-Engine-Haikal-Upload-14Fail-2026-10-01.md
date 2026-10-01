# RULE — Content Engine Haikal Upload 14/14 FAIL Repair (2026-10-01)

## Locks
- Beta only: workdir `/Users/wolfterminal/beta-os`, `scripts/serve_beta.py` on **:8788**.
- Prod **:8787** sacred — never mutate files, process, DB, or configs used by prod serve.
- Do not invent LIVE. Do not set `staff_ready=true`. No Exit Report. No Wolf Intelligence pack from this run.
- Do not ask Haikal or Matt to diagnose.
- Preserve failed-batch provenance: never mark the 14 as successful manually; no duplicate NAS assets on retry.
- Shared-path first (14/14 failed together). Do not guess root cause from screenshot alone.
- SOFTWARE-FIRST: SPEC → data → perms → rules → API → UI → tests. Prefer shared upload/NAS/DB roots over page patches.
- Reuse Wolf Core / existing content upload stack; no new agents, dashboards, or speculative redesign.
- Credit exception: `human_commissioning_fail_repair_P0` only for this bounded repair.

## Stop
Engineering prove on Beta → STOP for Peaches light verify → Haikal retest (small then normal). Content Upload stays FAIL until Haikal PASS.
