# CONNECTION TRUTH MATRIX — Beta House — 1 Oct 2026 WITA

Generated: `2026-10-01T07:17:29+08:00` · Executor: Peaches · Prod :8787 untouched

## Rules
- CONFIGURED ≠ CONNECTED ≠ TESTED ≠ COMMISSIONED
- No invent occupancy/sales · ESB sales = theoretical consumption only
- No ESB/Yanolja/Metricool/Klaviyo/Gmail writes

## Re-prove deltas
- **ESB**: prior ABSENT claim overturned — credentials + LIVE oms-prod + sqlite fresh
- **Yanolja**: prior BLOCKED_EXTERNAL overturned — live Inventory+RoomInfo 200

## Matrix

| System | precise_state | CRED | AUTH | BETA | LIVE_READ | WRITE_CAP | WRITE_OK | COMMISSIONED | LAST_SUCCESS | OWNER_ACTION |
|---|---|---|---|---|---|---|---|---|---|---|
| ESB | LIVE_READ_OK | True | True | False | True | False | False | False | 2026-10-01T07:05:46+08:00 esb-inline OK oms-prod; sqlite sal | None for READ (authorised). Approve Beta wire pack to bind e |
| Yanolja | LIVE_READ_OK | True | True | False | True | False | False | False | 2026-10-01T07:16:15+08:00 first_read ok http=200 room_types= | None for Inventory+RoomInfo READ. Optional: confirm AuthCode |
| Metricool | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01T07:14 WITA MCP getBrandSettings → 6 brands | Confirm flip BETA_METRICOOL_ENABLED=true (READ). Keep WRITE  |
| Klaviyo | CREDENTIAL_PRESENT_UNTESTED | True | False | False | False | True | False | False |  | Approve bounded Klaviyo READ prove (lists/metrics) — push st |
| Canva | CREDENTIAL_PRESENT_UNTESTED | True | False | False | False | True | False | False | authorized_at 2026-06-03 (historical) | Run/approve canva token refresh (or re-auth). Capability exi |
| NAS_Synology | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01 mounts OK; 01-Media-Library ls brands AMG/BZG/GGV | Inventory READ continue; staff-ready remains false; fix perm |
| Backblaze_B2 | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01 rclone lsd b2: wolf-cold-archive; wolfb2: 3 bucke | Optional: commission restore-read prove pack. DELETE remains |
| Gmail | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01 list_labels LIVE (INBOX/Sent/labels) | Approve draft-only workflow wire (create_draft). Keep send_m |
| Google_Drive | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01 list_recent_files LIVE (Alchemist Control sheet e | Wire READ into Wolf desks; write stays NO default |
| Google_Calendar | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01 list_calendars LIVE | Wire READ; create/update NO default |
| Notion | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01 notion-list-recent-pages LIVE | Optional Wolf surface bind; create/update NO default |
| Slack | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01 slack_list_user_channels LIVE | Read DEFER→now proved; send remains NO |
| Jotform | CONNECTED | True | True | False | False | True | False | False | MCP ready (serverStatus ready); content search not run this  | Optional bounded form list prove |
| Alchemist | LIVE_READ_OK | True | True | False | True | True | False | False | DB mtime 2026-09-30T15:41; launchd alchemist PID up 16d+; Dr | Approve Alchemist READ tile into Beta; pay/mutate stays NO w |
| Bank_Import | CONFIGURED | False | False | False | False | False | False | False | June-2026-CIMB-transactions.csv historical | Commission file-import SOP into atrium-finance :8790 identit |
| Cloudflare_R2 | CONFIGURED | True | False | False | False | True | False | False |  | Leave parked unless cost YES |
| Cloudflare_Access | CONNECTED | True | True | True | True | False | False | False | 2026-10-01 :8788 / → 403 Access; /api/health 200 | CF Access screenshot session optional for UX packs — not blo |
| Atrium_Finance_8790 | CONNECTED | False | True | True | True | True | False | False | 2026-10-01 /api/health 200 | Human identity-matrix prove next (not new connector) |
| Xero | ABSENT | False | False | False | False | False | False | False |  | Human re-auth if needed |
| ClickUp | RETIRED | True | False | False | False | False | False | False |  | Stay RETIRED |
| Telegram | RETIRED | True | False | False | False | False | False | False |  | Stay RETIRED |
| Cloudbeds | RETIRED | True | False | False | False | False | False | False |  | Confirm keep retired |
| Mews | ABSENT | False | False | False | False | False | False | False |  | None |
| AI_Providers_Beta | ABSENT | False | False | False | False | False | False | False |  | Seat keys + dry-run YES before spend |
| Meta_Google_Ads | ABSENT | False | False | False | False | False | False | False |  | HOLD — LEARN-only |
| Calendly | BLOCKED_EXTERNAL | True | False | False | False | False | False | False |  | Not this week's cheap wire |
| GitHub | CONNECTED | True | True | False | False | True | False | False | MCP catalog ready | Push remains human gate |
| GitLab | BLOCKED_EXTERNAL | True | False | False | False | False | False | False |  | Fix PAT scope if needed |
| Prod_8787 | LIVE_READ_OK | True | True | False | True | True | False | False | 2026-10-01 LISTEN PID 15975 | Mutate remains NO forever this mission |

## State counts
```
{
  "LIVE_READ_OK": 12,
  "CREDENTIAL_PRESENT_UNTESTED": 2,
  "CONNECTED": 4,
  "CONFIGURED": 2,
  "ABSENT": 4,
  "RETIRED": 3,
  "BLOCKED_EXTERNAL": 2
}
```

*staff_ready=false · human_commissioned=false · desktop_gate_ready=false*

## Wire packs applied 2026-10-01

# CONNECTION TRUTH MATRIX — wire update

Updated: 2026-10-01T07:25:35+08:00 · packs: WIRE-ESB-READ-HOUSE-1, WIRE-YANOLJA-READ-HOUSE-1, WIRE-METRICOOL-READ-BETA-1, PROVE-NAS-B2-INVENTORY-1-LIGHT

| id | precise_state | BETA_CONNECTED | LIVE_READ_TESTED | LAST_SUCCESS | BLOCKER |
|---|---|---|---|---|---|
| ESB | LIVE_READ_OK | True | True | 2026-10-01T07:25:04+08:00 pulse bzg_night LIVE from esb.sqlite biz_date 2026-09- | Warehouse LIVE on Owner pulse; settlement API still EXTERNAL; venue_daily_closes=0 |
| Yanolja | LIVE_READ_OK | True | True | 2026-10-01T07:25:04+08:00 pulse atrium_occ LIVE 88.6% (13 vacant / 114) from las | Inventory+RoomInfo LIVE on Beta; arrivals/in-house/ADR/RevPAR guest depth still UNKNOWN |
| Metricool | LIVE_READ_OK | True | True | 2026-10-01 list_profiles 6 brands after BETA_METRICOOL_ENABLED=true | WRITE false; engagement may stay NOT_RUNTIME until analytics sync |
| NAS_Synology | LIVE_READ_OK | True | True | 2026-10-01 mounts OK; 01-Media-Library ls brands AMG/BZG/GGV/_Imports | Inventory-first until staff prove; Haikal human test not started; DSM API user still TODO  |
| Backblaze_B2 | LIVE_READ_OK | True | True | 2026-10-01 rclone lsd b2: wolf-cold-archive; wolfb2: 3 buckets; restore drill 20 | List OK ≠ restore re-proved today |

## Wire packs applied 2026-10-01T07:36:26+08:00 (deepen)

| id | precise_state | BETA_CONNECTED | LAST_SUCCESS | BLOCKER |
|---|---|---|---|---|
| Alchemist | LIVE_READ_OK | True | 2026-10-01T07:36:26+08:00 alchemist-ro + pulse DB counts | Pay/mutate NO; legacy PARTIAL |
| ESB | LIVE_READ_OK | True | 2026-10-01T07:36:26+08:00 pulse covers 87 | Settlement EXTERNAL; closes=0 |
| Yanolja | LIVE_READ_OK | True | occ LIVE; guest_depth UNKNOWN | Bookings 302 |
| Gmail | LIVE_READ_OK | True | MCP list_labels; DRAFT_ONLY | send NO |
| Google_Drive | LIVE_READ_OK | True | MCP list_recent_files | write NO |
| Google_Calendar | LIVE_READ_OK | True | MCP list_calendars (2) | create/update NO |


## Refresh 2026-10-01T07:42:49+08:00
- beta_connected_true now **11** (added Alchemist, Gmail, Drive, Calendar after wire packs)
- IA-HIDE-DEAD-1 applied on Beta :8788; Prod :8787 untouched
- FINISH-WOLF-QUEUE Matt cards: 5
- staff_ready=false · desktop_gate_ready=false · no Exit Report · no WOLF DESKTOP READY

# CONNECTION TRUTH MATRIX — end-state deepen — 2026-10-01T09:46:44+08:00

## End-state counts
```
{
  "LIVE+TESTED": 15,
  "OPTIONAL_NON_GATING": 1,
  "OWNER ACTION REQUIRED": 2,
  "CONNECTED, COMMISSIONING REQUIRED": 6,
  "INTENTIONALLY DISABLED": 10,
  "OBSOLETE/SUPERSEDED": 6,
  "EXTERNAL BLOCKER": 2
}
```

Matrix rows: 42 · discovery systems: 42 · added: ['Beta_OS', 'Discord', 'Obsidian', 'Time_Machine', 'Apify', 'SerpAPI', 'YouTube_API', 'Cloudinary', 'Descript', 'ActiveCampaign', 'Event_Bus', 'Spartacus_Fitness', 'Trading_Desk']

| System | precise_state | end_state | note |
|---|---|---|---|
| ESB | LIVE_READ_OK | LIVE+TESTED |  |
| Yanolja | LIVE_READ_OK | LIVE+TESTED | Inventory LIVE+TESTED; Bookings guest-depth is separate Matt card |
| Metricool | LIVE_READ_OK | LIVE+TESTED |  |
| Klaviyo | CREDENTIAL_PRESENT_UNTESTED | OPTIONAL_NON_GATING | OPTIONAL / NON-GATING; Habitat sheet covers Owner leads READ |
| Canva | CREDENTIAL_PRESENT_UNTESTED | OWNER ACTION REQUIRED | Finish Wolf — OAuth re-auth |
| NAS_Synology | LIVE_READ_OK | LIVE+TESTED | 00/02 stubs NOT_REQUIRED deblocked |
| Backblaze_B2 | LIVE_READ_OK | LIVE+TESTED |  |
| Gmail | LIVE_READ_OK | LIVE+TESTED |  |
| Google_Drive | LIVE_READ_OK | LIVE+TESTED | Habitat Leads sheet READ proved |
| Google_Calendar | LIVE_READ_OK | LIVE+TESTED |  |
| Notion | LIVE_READ_OK | LIVE+TESTED |  |
| Slack | LIVE_READ_OK | LIVE+TESTED |  |
| Jotform | CONNECTED | CONNECTED, COMMISSIONING REQUIRED |  |
| Alchemist | LIVE_READ_OK | LIVE+TESTED |  |
| Bank_Import | CONFIGURED | CONNECTED, COMMISSIONING REQUIRED |  |
| Cloudflare_R2 | CONFIGURED | INTENTIONALLY DISABLED | Parked unless cost YES |
| Cloudflare_Access | CONNECTED | LIVE+TESTED | Access enforcing; CF shots Matt last |
| Atrium_Finance_8790 | CONNECTED | CONNECTED, COMMISSIONING REQUIRED | Finance soft-bleed other executor |
| Xero | ABSENT | OWNER ACTION REQUIRED |  |
| ClickUp | RETIRED | OBSOLETE/SUPERSEDED |  |
| Telegram | RETIRED | OBSOLETE/SUPERSEDED |  |
| Cloudbeds | RETIRED | OBSOLETE/SUPERSEDED |  |
| Mews | ABSENT | OBSOLETE/SUPERSEDED | Superseded by Yanolja |
| AI_Providers_Beta | ABSENT | INTENTIONALLY DISABLED |  |
| Meta_Google_Ads | ABSENT | INTENTIONALLY DISABLED | HOLD LEARN-only |
| Calendly | BLOCKED_EXTERNAL | EXTERNAL BLOCKER |  |
| GitHub | CONNECTED | CONNECTED, COMMISSIONING REQUIRED |  |
| GitLab | BLOCKED_EXTERNAL | EXTERNAL BLOCKER |  |
| Prod_8787 | LIVE_READ_OK | LIVE+TESTED |  |
| Beta_OS | LIVE_READ_OK | LIVE+TESTED | :8788 LIVE |
| Discord | RETIRED | OBSOLETE/SUPERSEDED | Not in active house wire |
| Obsidian | ABSENT | INTENTIONALLY DISABLED | Local vault |
| Time_Machine | LIVE_READ_OK | LIVE+TESTED | Local TM present; not Wolf API |
| Apify | ABSENT | INTENTIONALLY DISABLED |  |
| SerpAPI | ABSENT | INTENTIONALLY DISABLED |  |
| YouTube_API | ABSENT | INTENTIONALLY DISABLED |  |
| Cloudinary | ABSENT | INTENTIONALLY DISABLED |  |
| Descript | ABSENT | INTENTIONALLY DISABLED |  |
| ActiveCampaign | RETIRED | OBSOLETE/SUPERSEDED | Superseded by Klaviyo path |
| Event_Bus | ABSENT | INTENTIONALLY DISABLED |  |
| Spartacus_Fitness | CONNECTED | CONNECTED, COMMISSIONING REQUIRED |  |
| Trading_Desk | CONNECTED | CONNECTED, COMMISSIONING REQUIRED |  |

*staff_ready=false · desktop_gate_ready=false*



# CONNECTION TRUTH MATRIX — commissioning deepen — 2026-10-01T09:53:41+08:00

## End-state counts
```
{
  "LIVE+TESTED": 17,
  "OPTIONAL_NON_GATING": 1,
  "OWNER ACTION REQUIRED": 2,
  "CONNECTED, COMMISSIONING REQUIRED": 2,
  "INTENTIONALLY DISABLED": 12,
  "OBSOLETE/SUPERSEDED": 6,
  "EXTERNAL BLOCKER": 2
}
```

| System | was | now | note |
|---|---|---|---|
| Jotform | COMMISSIONING | LIVE+TESTED | MCP form list 4 |
| GitHub | COMMISSIONING | LIVE+TESTED | get_me wolfcommand |
| Bank_Import | COMMISSIONING | COMMISSIONING | OWNER/STAFF file-import |
| Atrium_Finance_8790 | COMMISSIONING | COMMISSIONING | staff prove + entity isolation |
| Spartacus_Fitness | COMMISSIONING | INTENTIONALLY DISABLED | no credentials |
| Trading_Desk | COMMISSIONING | INTENTIONALLY DISABLED | no credentials |

Remaining COMMISSIONING: **2** (Bank_Import, Atrium_Finance_8790)
staff_ready=false · desktop_gate_ready=false
