# 42 connections — operational re-audit
**Source of the 42 ids:** `state/final-completion/beta-house-20261001/CONNECTION-TRUTH-MATRIX.json` (unique `id` count **42** this session).  
**Rule:** `LIVE_READ_OK` means a read happened. It does not mean a staff workflow consumes it, fails visibly, respects permission, and writes only what was approved.

`staff_ready=false`. No connection below is commissioned as an operating loop.

## State on the matrix file
| precise_state | ids |
|---|---|
| LIVE_READ_OK (16) | ESB, Yanolja, Metricool, NAS_Synology, Backblaze_B2, Gmail, Google_Drive, Google_Calendar, Notion, Slack, Jotform, Alchemist, GitHub, Prod_8787, Beta_OS, Time_Machine |
| CONNECTED (2) | Cloudflare_Access, Atrium_Finance_8790 |
| CONFIGURED (2) | Bank_Import, Cloudflare_R2 |
| CREDENTIAL_PRESENT_UNTESTED (2) | Klaviyo, Canva |
| BLOCKED_EXTERNAL (2) | Calendly, GitLab |
| RETIRED (5) | ClickUp, Telegram, Cloudbeds, Discord, ActiveCampaign |
| ABSENT (13) | Xero, Mews, AI_Providers_Beta, Meta_Google_Ads, Obsidian, Apify, SerpAPI, YouTube_API, Cloudinary, Descript, Event_Bus, Spartacus_Fitness, Trading_Desk |

## Read that landed in a card this session
Checked with `GET /api/owner/pulse-ro` and the RO routes, not by trusting the matrix alone.

| Id | Workflow consumer | Freshness | Failure behaviour | Permission | Approved write |
|---|---|---|---|---|---|
| Yanolja | Owner pulse occ card only | Last read 07:16 WITA | Arrivals/in-house stamped UNKNOWN | Read | No booking write |
| ESB | Owner pulse BZG night | Warehouse freshness on the card | Settlement still external. Closes table 0 | Read | No |
| Alchemist | Pulse purchasing counts | DB mtime on the card (15:37 WITA) | Pay/mutate refused | Read | No |
| Metricool | Pulse schedule card | Schedule counts, engagement not invented | WRITE off | Read | No post |
| NAS | Pulse stamp | Shallow 38,091. `full_tree_indexed=false`. Shares 00/02 denied | Index ≠ library | Read | No staff publish |
| Gmail / Drive / Calendar | `gws-ro` card | MCP read stamped on the pulse | Send and calendar/drive write off | Read, Gmail draft only | Draft is the only write, and it is not a Wolf desk workflow |
| Backblaze_B2 | Backup tile | Pulse says PARTIAL, atrium snap STALE | Stale stays PARTIAL | Read | No |
| Prod_8787 | Sacred read | Health 200 this session | Do not restart | Read | No |

## Live read with no Wolf workflow found
Notion, Slack, Jotform, GitHub, Time_Machine. A successful API call is not a desk. Jotform’s four forms are not lead→sale. GitHub `get_me` is not a release workflow. Slack send stays off.

## Matrix says ABSENT while a mirror exists
`Spartacus_Fitness` and `Trading_Desk` are **ABSENT** on the connection matrix. This session `fitness-ro` and `trading-ro` returned 200, `migration_state=PARTIAL`, `claim=NOT_REBUILT_PLUS_PROVEN`. The matrix and the RO routes disagree. Operational answer: **not operationalised**. The matrix should be updated in a later wave so ABSENT does not hide a partial mirror, and the mirror must not be upgraded to LIVE just because HTTP 200.

## Not operational, by design or by gap
- **Xero ABSENT.** n8n templates 03, 09, 10, 11 have no feed. GGV books cannot close to Xero from Beta.
- **Event_Bus ABSENT.** V1 `state/event_bus.db` exists. Beta page is `ops-event-bus-1` (shell class).
- **Calendly BLOCKED_EXTERNAL.** V1 sync job is not a Beta booking flow.
- **Klaviyo, Canva:** credential present, untested. No consumer.
- **Bank_Import CONFIGURED.** Not a weekly statement→match loop. V1 cash screen still expects a human file.
- **R2 CONFIGURED.** V1 home had an R2-gap tile. Beta pulse has no R2-gap card.
- **Cloudflare Access CONNECTED.** It is the lock. Peaches recorded page `/` as 403. That is the gate working, not a business feature.
- **Atrium_Finance_8790 CONNECTED.** Port up is not the 15 finance screens.
- **ClickUp, Telegram, Cloudbeds, Discord, ActiveCampaign RETIRED.** Do not rebuild them as Beta product unless a later decision un-retires one. V1 person desks must be replaced by Wolf work, not by turning ClickUp back on.
- **SerpAPI ABSENT** on Beta. Standing rule: content plans only, inside the free tier, via `scripts/serpapi_budget.py` on V1. Not a Beta workflow.
- **Meta/Google Ads ABSENT.** Ads studio write path is a V1 function with no feed.

## Verdict
Zero of the 42 are an end-to-end operational workflow (consumer, freshness, failure, permission, approved write). The honest live set is a handful of **read cards** on the Owner pulse.
