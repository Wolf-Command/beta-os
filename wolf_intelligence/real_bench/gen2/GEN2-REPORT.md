# Gen-2 benchmark report: run gen2-20261006 (WITA)

**Paid spend: OFF. Routing policy: DRAFT - NOT WIRED. No worker is called universally best.**

- Workers: Claude Pro (sub), Codex (sub), Cursor (sub, Ultra), and Ollama local (llama3.2:3b). Each ran 3 repetitions per task, 10 tasks.
- Gemini: **DEFERRED: BILLING UNVERIFIED** (see GEMINI-BILLING-TRUTH.md). Grok: **PENDING BRIDGE**. No pass was confirmed to me.
- Grading: deterministic graders, version 2.1 (the 2.0→2.1 regrade of rep 1 finance and vision supersedes the old records, which are kept).
  UX is scored 0.6 × deterministic (permission F1 plus failure states) + 0.4 × blind cross-worker rubric. A worker never grades itself.
- Tie rule (fixed before any run): two class means TIE when |Δ| ≤ max(0.05, 2·SE). Latency is used only *inside* a tie, and only as a labelled preference.
- A run FAILS when it is incomplete, has no gradeable output, hits a critical semantic failure, or scores below 0.5.

## Results per class (mean ± sd over 3 reps; fr = failure rate; lat = median ms)

| class | Claude Pro | Codex | Cursor | Ollama | leader (confidence) |
|---|---|---|---|---|---|
| coding | 1.000 ± 0.000 · fr 0.00 · 30s | 1.000 ± 0.000 · fr 0.00 · 39s | 0.992 ± 0.014 · fr 0.00 · 64s | 0.381 ± 0.000 · fr 1.00 · 4s | TIE claude/codex/cursor (latency pref within tie: claude) |
| debugging | 1.000 ± 0.000 · fr 0.00 · 28s | 0.975 ± 0.043 · fr 0.00 · 28s | 1.000 ± 0.000 · fr 0.00 · 38s | 0.000 ± 0.000 · fr 1.00 · 4s | TIE claude/cursor/codex (latency pref within tie: claude) |
| security | 1.000 ± 0.000 · fr 0.00 · 23s | 0.893 ± 0.000 · fr 0.00 · 23s | 0.879 ± 0.024 · fr 0.00 · 41s | 0.250 ± 0.000 · fr 1.00 · 1s | **claude_pro_sub** (HIGH; margin 0.1071 > 0.05) |
| finance | 0.983 ± 0.029 · fr 0.00 · 38s | 1.000 ± 0.000 · fr 0.00 · 57s | 0.816 ± 0.144 · fr 0.00 · 59s | 0.000 ± 0.000 · fr 1.00 · 4s | TIE codex/claude (latency pref within tie: claude) |
| ux_product | 0.861 ± 0.030 · fr 0.00 · 53s | 0.881 ± 0.019 · fr 0.00 · 52s | 0.843 ± 0.050 · fr 0.00 · 33s | NOT_ATTEMPTED | TIE codex/claude/cursor (latency pref within tie: cursor) |
| large_context | 1.000 ± 0.000 · fr 0.00 · 49s | 0.867 ± 0.058 · fr 0.00 · 54s | 0.667 ± 0.058 · fr 0.00 · 198s | UNSUPPORTED | **claude_pro_sub** (HIGH; margin 0.1333 > 0.0666) |
| vision_document | 1.000 ± 0.000 · fr 0.00 · 9s | 1.000 ± 0.000 · fr 0.00 · 11s | 0.974 ± 0.044 · fr 0.00 · 38s | UNSUPPORTED | TIE claude/codex/cursor (latency pref within tie: claude) |
| structured_extraction | 1.000 ± 0.000 · fr 0.00 · 8s | 1.000 ± 0.000 · fr 0.00 · 13s | 1.000 ± 0.000 · fr 0.00 · 23s | 0.507 ± 0.000 · fr 0.00 · 2s | TIE claude/codex/cursor (latency pref within tie: claude) |
| reasoning_planning | 1.000 ± 0.000 · fr 0.00 · 13s | 1.000 ± 0.000 · fr 0.00 · 48s | 1.000 ± 0.000 · fr 0.00 · 48s | 0.000 ± 0.000 · fr 1.00 · 3s | TIE claude/codex/cursor (latency pref within tie: claude) |
| regression_daily_close_extraction | 1.000 ± 0.000 · fr 0.00 · 9s | 1.000 ± 0.000 · fr 0.00 · 20s | 1.000 ± 0.000 · fr 0.00 · 24s | 0.500 ± 0.000 · fr 1.00 · 7s | TIE claude/codex/cursor (latency pref within tie: claude) |

Variance is in `gen2-report.json` (`variance`, `min`, `max`, `accuracy_mean`, `instruction_mean`, `governance_pass_rate`). Governance pass rate was 1.0 for every supported run.
Raw outputs are in `artifacts/raw/<worker>/<request_id>.txt`, and every call is in `records/dispatch.jsonl`.

## Regression task: Daily Close semantic extraction (isolated ESB-style fixture; the real Daily Close was not touched)
Three adversarial variants: reordered rows, an extra unknown method, and a look-alike 'Avg per bill' line. Scoring is deterministic: labels/sections, averages ≠ counts, raw payment labels, UNKNOWN kept, no positional guessing.

| worker | reps | mean | critical failures | notes |
|---|---|---|---|---|
| Claude Pro | 3 | 1.000 | 0 | all scalars correct incl. avg_per_bill vs bill_count; unknown methods kept UNKNOWN |
| Codex | 3 | 1.000 | 0 | same |
| Cursor | 3 | 1.000 | 0 | same |
| Ollama | 3 | 0.500 | **3/3** | remapped unknown methods (`QRIS Mandiri→QRIS`, `Voucher Hotel GGV→None`, `Debit BCA→None`), confused avg_per_pax, added an extra row. The same failure every rep. |

## Is gen-2 evidence materially stronger than gen-1?
**Partly.** It is stronger in method: 3 reps with variance and failure rates, deterministic graders, adversarial fixtures, a pre-declared tie rule, and blind UX review.
It is stronger in result for **3 classes**: security and large-context have a HIGH-confidence leader, and finance cleanly separates Cursor below the Claude/Codex tie.
It also gives a hard, repeatable Ollama exclusion signal. It is **not** stronger for the other 7 classes: Claude Pro scored 1.000 on 8 of 10 classes and
Codex and Cursor sit within the immaterial threshold. Those tasks are still at the ceiling for the top subscription workers, so gen-3 needs longer, multi-step, tool-using tasks.

## PROPOSED routing change (DRAFT - NOT WIRED; file `routing-policy-gen2-PROPOSED.json`)
Justified: **YES, but narrowly.**
1. Remove `gemini_free` from every class order (billing unverified; Owner SPEND BLOCKED). This is required, not a quality judgement.
2. `large_context`: claude_pro_sub > codex_sub > cursor_sub (HIGH; Claude 1.000 vs Codex 0.867 vs Cursor 0.667; Cursor median 199 s). Gen-1 had gemini > claude > codex > cursor.
3. `security`: claude_pro_sub first (HIGH). Codex and Cursor both missed `check_webhook_sig` in 3/3 reps. This matches gen-1's order once Gemini is removed, so it confirms rather than changes it.
4. Ollama: excluded from `regression_daily_close_extraction` and from any semantic-extraction role (3/3 critical). It stays only as a local fallback where it is not gated by semantics.
Not justified: any reorder in coding, debugging, finance (Claude/Codex tie), ux_product, vision_document, structured_extraction, reasoning_planning, or the regression class among the top three. Those orders stay as gen-1 minus Gemini.

## Subscription allowance (before → after)
| worker | pre 09:32 | mid1 09:47 | mid2 09:59 | post 10:10 |
|---|---|---|---|---|
| Claude Pro 5-h session | 5% | 15% | 24% | 46% (resets 12:50 WITA) |
| Claude Pro week (all models) | 0% | 1% | 2% | 4% (resets Oct 10 19:00 WITA); usage credits OFF |
| Codex (team) weekly window | 1% | 2% | 2% | 4% |
| Cursor | Ultra | Ultra | Ultra | Ultra; no on-demand/usage-based wording seen, no stop triggered |
Stop thresholds were never approached. One caution: the run used ~41 points of the current Claude 5-h session.
