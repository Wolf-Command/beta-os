# S0 — Save the house — 27 Sep 2026

Beta/local only. Production `:8787` stayed pid 15975. Beta `:8788` stayed pid 35844. No restart. No money, bank, payment, ESB, or NAS write. No push. No history rewrite.

This pack saves uncommitted Beta work. It does not change staff readiness, human commissioning, or operating adoption.

TECHNICAL PROOF is the commits, the tag, and the suites below. DEPLOYED ROUTE PROOF was not re-run except where a suite already calls Beta. STAFF READINESS stays unset. HUMAN COMMISSIONING stays unset. OPERATING ADOPTION stays unset.

## Classification

`git status --porcelain` at start: **579** entries (58 modified, 521 untracked directories/files). Expanded with `-uall`: **629** files. Every expanded file is in one class.

| class | files |
| --- | ---: |
| LEGIT | 557 |
| EXCLUDE | 72 |
| **sum** | **629** |

### LEGIT (557), committed

| group | files | commit |
| --- | ---: | --- |
| `.gitignore` | 1 | `df6e8a4` |
| scripts (server, core, tests, migrations, two 159-byte JPEG fixtures) | 144 | `34bfee9` |
| dashboards | 41 | `22f49da` |
| docs, briefs, Progress | 249 | `f41b31d` |
| intended state (claims, registers, commissioning notes, backup `.sha256`) | 122 | `eeb310a` |

### EXCLUDE (72), left on disk and gitignored

| class | files |
| --- | ---: |
| generated delivery screenshots (`.png`) | 15 |
| generated packs (`.tgz`) | 3 |
| NAS estate runtime (large caches, pid/progress, scan checkpoint) | 7 |
| NAS index sample dumps | 26 |
| operator event logs | 15 |
| runtime SQLite backups | 5 |
| watch tick stamp | 1 |

Secret scan of candidate text (patterns: `key=`, `password`, `token`, `BEGIN PRIVATE`, `B2_`, `SESSION_SECRET`). No credential assignment was found. Nothing was excluded for a secret value. Reviewed false positives stayed in LEGIT: `dashboards/wolf-tokens.css` (design tokens), `B2_FINANCE_PROVEN` (a false flag, not a Backblaze key), and the same words in docs and tests.

### Excluded paths

- `state/progress/commissioning-operator-events.jsonl`
- `state/progress/needs-you-operator-events.jsonl`
- `LAST-WATCH-TICK.txt`
- `docs/deliveries/devi-ux-2026-09-19/petty-phone.png`
- `docs/deliveries/devi-ux-2026-09-19/today-phone-tall.png`
- `docs/deliveries/devi-ux-2026-09-19/today-phone.png`
- `docs/deliveries/devi-ux-ready-2026-09-19/bills-phone.png`
- `docs/deliveries/devi-ux-ready-2026-09-19/petty-phone.png`
- `docs/deliveries/devi-ux-ready-2026-09-19/today-phone.png`
- `docs/deliveries/evidence/wolf-rhc-v1-20260922/desktop-bzg-uma.png`
- `docs/deliveries/evidence/wolf-rhc-v1-20260922/desktop-empire.png`
- `docs/deliveries/evidence/wolf-rhc-v1-20260922/desktop-system-progress.png`
- `docs/deliveries/evidence/wolf-rhc-v1-20260922/mobile-bzg-uma.png`
- `docs/deliveries/evidence/wolf-rhc-v1-20260922/mobile-empire.png`
- `docs/deliveries/evidence/wolf-rhc-v1-20260922/mobile-system-progress.png`
- `docs/deliveries/petty-phone.png`
- `docs/deliveries/today-phone-tall.png`
- `docs/deliveries/today-phone.png`
- `state/amg-day-ops/operator-events.jsonl`
- `state/amg-journey-workflow/operator-events.jsonl`
- `state/amg-packages/operator-events.jsonl`
- `state/amg-revenue-yield/operator-events.jsonl`
- `state/amg-service-improve/operator-events.jsonl`
- `state/amg-sla-incident/operator-events.jsonl`
- `state/backups/content_library.sqlite.pre-devi-scope-narrow-20260919-081414`
- `state/backups/content_library.sqlite.pre-devi-scope-narrow-20260919-085039`
- `state/backups/content_library.sqlite.pre-devi-scope-narrow-20260919-085131`
- `state/backups/content_library.sqlite.pre-devi-scope-narrow-20260919-143126`
- `state/backups/content_library.sqlite.pre-ended-scope-norevive-20260919-134322`
- `state/crm-identity/operator-events.jsonl`
- `state/crm-package-intel/operator-events.jsonl`
- `state/ggv-client-profitability/operator-events.jsonl`
- `state/ggv-intercompany-client/operator-events.jsonl`
- `state/model-c-catalog-pack.tgz`
- `state/model-c-v2-pack.tgz`
- `state/msc-asset/operator-events.jsonl`
- `state/msc-compliance/operator-events.jsonl`
- `state/nas-estate/discovery.json`
- `state/nas-estate/duplicate-candidates.jsonl`
- `state/nas-estate/failures.jsonl`
- `state/nas-estate/index-checkpoint.json`
- `state/nas-estate/index.pid.status`
- `state/nas-estate/manifest.tsv`
- `state/nas-estate/progress.txt`
- `state/nas-index/operator-events.jsonl`
- `state/nas-index/sample-_shared-20260922.jsonl`
- `state/nas-index/sample-_shared-20260922.manifest.json`
- `state/nas-index/sample-_shared-20260923.jsonl`
- `state/nas-index/sample-_shared-20260923.manifest.json`
- `state/nas-index/sample-amg-atrium-20260922.jsonl`
- `state/nas-index/sample-amg-atrium-20260922.manifest.json`
- `state/nas-index/sample-amg-atrium-20260923.jsonl`
- `state/nas-index/sample-amg-atrium-20260923.manifest.json`
- `state/nas-index/sample-brand-assets-20260922.jsonl`
- `state/nas-index/sample-brand-assets-20260922.manifest.json`
- `state/nas-index/sample-bzg-20260922.jsonl`
- `state/nas-index/sample-bzg-20260922.manifest.json`
- `state/nas-index/sample-bzg-20260923.jsonl`
- `state/nas-index/sample-bzg-20260923.manifest.json`
- `state/nas-index/sample-clients-20260922.jsonl`
- `state/nas-index/sample-clients-20260922.manifest.json`
- `state/nas-index/sample-clients-20260923.jsonl`
- `state/nas-index/sample-clients-20260923.manifest.json`
- `state/nas-index/sample-continue-20260922.manifest.json`
- `state/nas-index/sample-continue-20260923.manifest.json`
- `state/nas-index/sample-ggv-20260922.jsonl`
- `state/nas-index/sample-ggv-20260922.manifest.json`
- `state/nas-index/sample-ggv-20260923.jsonl`
- `state/nas-index/sample-ggv-20260923.manifest.json`
- `state/nas-index/sample-imports-20260922.jsonl`
- `state/nas-index/sample-imports-20260922.manifest.json`
- `state/progress-404-pack.tgz`

## Review of tracked diffs

`scripts/serve_beta.py` compiles (`python3 -m py_compile`). Every removed function was added again in the same diff. Added lines had no private-key or secret assignment. `payment` lines are refusals or `null`.

`.gitignore` already ignored nota blobs. This pack adds the EXCLUDE classes above, including `*operator-events.jsonl` so `commissioning-operator-events.jsonl` and `needs-you-operator-events.jsonl` are covered.

`state/build-claims/2026-09-22.json` parses. Claims went from 1 to 44. No prior claim id was dropped. `state/build-claims/owner-autonomous-release-2026-09-19.json` parses.

## Suites

`WOLF_TEST_MODE=1`, this session. Production pid checked before and after: 15975. Beta pid: 35844.

| suite | result |
| --- | --- |
| `scripts/tests/test_dashboard_truth.py` | PASS=62 FAIL=0 exit 0 |
| `scripts/tests/test_owner_command.py` | PASS=66 FAIL=0 exit 0 |
| `scripts/tests/test_business_dashboard.py` | PASS=131 FAIL=0 exit 0 |
| `scripts/tests/test_role_dashboard.py` | PASS=144 FAIL=0 exit 0 |
| `scripts/tests/test_completion_war_room.py` | PASS=227 FAIL=0 exit 0 |
| `scripts/tests/test_lead_spine.py` | PASS=33 FAIL=0 exit 0 |
| `scripts/tests/test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 exit 0 |
| `scripts/tests/test_phase2_5b_smart_upload.py` | PASS=17 FAIL=16 exit 1 |

Smart Upload was already red on live Beta before the repair: upload and preview return `missing_auth` / `Cf-Access-Jwt-Assertion required` (`auth_mode=cloudflare_access`). One repair pass: the suite no longer crashes on the unsigned `GET /content-2.0.html`. That check now records HTTP 403 `Content workspace is not in authorised scope.` and still requires `Smart Upload` and `wizStep1` in `dashboards/content-2.0.html`, with no `:8787` in that file. Auth was not opened. Beta was not restarted.

## Recovery point

Local lightweight tag `recovery-p0-20260927` points at the commit that adds this file. Not pushed.

`git status --porcelain | wc -l` after that commit: **0**. The 72 excluded files remain on disk and do not appear in porcelain.

RESULT: PASS
