# Staff placeholder audit — 28 Sep 2026

Report only. No page in this list was rebuilt. ATRIUMFIN-UX-1 replaced the Atrium Finance placeholder on `/amg/finance`. These are the same class of defect on the other staff landings, for the commissioning register.

Pattern: engineering or debug copy on a page a person opens for their job. Counts that are real records are not listed. Input placeholders such as "YYYY-MM-DD" are not listed.

## Atrium hotel desk

| File | Line | Quoted string | Suggested fix |
| --- | --- | --- | --- |
| `dashboards/amg-ops-pack.html` | 84 | `Hotel books are not open on this desk.` (title on `Finance · EMPTY`) | Say the Atrium books are not open yet, with no balance on this desk. |
| `dashboards/amg-ops-pack.html` | 89 | `Hotel books are not open on this desk.` | Same sentence, in the note under the nav. Use the same staff line as the finance desk empty state. |
| `scripts/core/fin_entity_boards.py` | 48 | `Hotel books are not open on this desk.` | This is the sentence the board check still requires on the ops pack. Change it only together with that check, and point it at the staff sentence. |
| `dashboards/amg-ops-pack.html` | 97 | `AMG commissioning, day-ops, and recorded SLA rows for this seat. Counts are the in-scope length. EMPTY when none. Not staff_ready. Not live hotel occupancy. Haikal human is not started. Devi retest stays parked.` | Replace with what the person can do on the hotel desk today. Keep commissioning names out of the page. |
| `dashboards/amg-ops-pack.html` | 192 | `Bound beta-amg-ops-safe · day loop beta-amg-day-safe · connective beta-amg-loop-safe. Not PROVEN. Not READY. CAP-AMG-04 stays SPECIFIED. CR-bc5785d66c981fd4 stays OPEN. staff_ready false. Haikal human not started. Devi retest parked. An empty slot is not live occupancy, ADR, or RevPAR. Empty SLA is not a live incident. This desk has no payment, folio, bank, or settlement action.` | Drop bound ids, CAP, CR, and person-test status. One quiet line is enough if payment is not on this desk. |
| `dashboards/amg-ops-pack.html` | 269 | `No in-scope AMG Needs-You rows. EMPTY — not invented work.` | `Nothing on this desk needs you right now.` |

## GGV finance

| File | Line | Quoted string | Suggested fix |
| --- | --- | --- | --- |
| `dashboards/ggv-finance.html` | 320 | `Not paid from this screen` | Use a staff label such as `Not verified as paid` for that count. |
| `dashboards/ggv-finance.html` | 914 | `This step is not built. Do not send unless the owner says so.` | Say the Gmail draft is not sent from this page, and name the next human step without the build note. |

## GGV ops

| File | Line | Quoted string | Suggested fix |
| --- | --- | --- | --- |
| `dashboards/ggv-ops-pack.html` | 97 | `GGV commissioning, content, and lead rows for this seat. Counts are the in-scope length. EMPTY when none. Not staff_ready. Haikal human is not started. Devi retest stays parked.` | Describe the work on the desk. Remove seat-test names. |
| `dashboards/ggv-ops-pack.html` | 128 | `Bound beta-ggv-ops-safe · loop beta-ggv-loop-safe. Not PROVEN. Not READY. staff_ready false. Haikal human not started. Devi retest parked. Performance is a DERIVE read. Closed is not a sale. This page does not write Metricool, Klaviyo, or an external CRM. This page does not resolve the completion row.` | Keep `Closed is not a sale` if that is the operating rule. Remove bound ids and commissioning status. |
| `dashboards/ggv-ops-pack.html` | 287 | `No in-scope GGV Needs-You rows. EMPTY — not invented work.` | `Nothing on this desk needs you right now.` |

## Content

`dashboards/content-2.0.html` lines 645 and 651 sit inside `<!--STAFF_OMIT_ENG-->` … `<!--/STAFF_OMIT_ENG-->`. `scripts/core/wolf_shell.py` removes that block for a non-owner audience. Owner still receives it. The strings are still in the file.

| File | Line | Quoted string | Suggested fix |
| --- | --- | --- | --- |
| `dashboards/content-2.0.html` | 645 | `Library detail + note / tag / next-action / handoff / dismiss. No Metricool/Klaviyo publish. No Haikal human fake. No NAS destroy. proven=false · ready=false · staff_ready=false` | Delete the block, or rewrite it as library actions with no commissioning flags. |
| `dashboards/content-2.0.html` | 651 | `Browse/filter sampled nas_index (folder · brand · type · recent). Rel paths only. full_tree_indexed=false · staff_ready=false · no Haikal human fake · no NAS destroy` | Same. |
| `dashboards/content-2.0.html` | 1854 | `Operator note (no publish)` | `Note` |
| `dashboards/content-2.0.html` | 2035 | `_needs_sorting EMPTY — not invent.` | `Nothing in this folder yet.` |

## Uma Blu

| File | Line | Quoted string | Suggested fix |
| --- | --- | --- | --- |
| `dashboards/bzg-uma-blu.html` | 123 | `No stock count is on this screen. Stock stays in ESB.` | `Stock is counted in ESB. This screen does not show a stock count.` |
| `dashboards/bzg-uma-blu.html` | 155 | `Overview · EMPTY` with title `No page yet` | Hide the slot until the page exists, or say `Overview is not on this desk yet.` |
| `dashboards/bzg-uma-blu.html` | 156 | `Operations · EMPTY` with title `No page yet` | Same. |
| `dashboards/bzg-uma-blu.html` | 159 | `BZG / Uma commissioning and recorded ops-loop rows for this seat. Counts are the in-scope length. EMPTY when none. Not staff_ready. Not money. Haikal human is not started. Devi retest stays parked.` | Say what Uma Blu today is for. Remove commissioning status. |
| `dashboards/bzg-uma-blu.html` | 276 | `No in-scope BZG Needs-You rows. EMPTY — not invented work.` | `Nothing on this desk needs you right now.` |
| `dashboards/bzg-uma-blu.html` | 356 | `No stock count is on this screen. Stock stays in ESB.` | Same staff line as line 123. |
| `dashboards/uma-blu-close.html` | 552 | `Variance needs an exception handover. Acceptance is not built on this screen.` | `Record the variance and hand it to the person who accepts the close.` |

## My Work

Rendered for Zayen from `scripts/core/staff_home.py`. It names ledger and chart reads that have grants and no Beta route.

| File | Line | Quoted string | Suggested fix |
| --- | --- | --- | --- |
| `scripts/core/staff_home.py` | 421–424 | `You work in Atrium Finance. You can open the board, read the ledger and the chart, and send work for approval. You cannot approve or post a journal, pay, change a bank account, or open another company.` | Say she can open the Atrium board and send a decision for approval. Drop the ledger and chart until those routes exist. One quiet line covers who approves. |

The same function has the same shape of restriction paragraph for Content Creator (line 412), Creative Director (line 418), GGV finance (line 429), BZG operations (line 434), closer (line 439), and hotel manager (line 444). Suggested fix: keep the job in the first sentence and leave payment and bank off the page.
