#!/usr/bin/env python3
"""Phase A forensic inventory extractor. Evidence files only. Does not touch :8787."""
import json, os, re, sqlite3
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path("/Users/wolfterminal/beta-os/state/final-completion/forensic-completeness-20261001")
V1 = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system")
BETA = Path("/Users/wolfterminal/beta-os")
AS_OF = "2026-10-01T19:06:00+08:00"

def blank():
    return {
        "tabs": [], "buttons_actions": [], "forms": [], "tables": [], "apis": [],
        "workflows": [], "integrations": [], "background_processes": [],
        "user_roles": [], "see": [], "do": [], "data_shown": [], "data_source": [],
        "actions_worked_evidence": [], "downstream": [], "business_domains": [],
    }

def F(**kw):
    row = blank()
    row.update(kw)
    row.setdefault("id", "")
    row.setdefault("route_or_path", "")
    row.setdefault("surface_name", "")
    row.setdefault("menu_path", "")
    return row

V1_ROWS = []

def add(row):
    V1_ROWS.append(row)

# --- Owner home / wolf desk (explodes wolf.html + master.status.json) ---
OWNER = [
    ("owner.pulse.money", "Money tile", "wolf.html#money", ["see restricted money status"], ["open money board if allowed"], ["locked/restricted flag"], ["master.status.json tile money", "/api/money"], "PARTIAL", "PERMISSION_WRONG", "/amg/finance + fin shells", "SoD is real; the tile is not a usable money desk. Keep finance auth. Build the desk behind the lock."),
    ("owner.pulse.brief", "Command Brief tile", "wolf.html#brief", ["see today brief ready"], ["open the brief"], ["Ready / date"], ["master.status.json tile brief 2026-10-01"], "MISSING", "MISSING_FROM_BETA", "", "No Command Brief card on /api/owner/pulse-ro (10 tiles, this session)."),
    ("owner.pulse.atrium_occ", "Atrium occupancy glance", "wolf.html → atrium-sales.html", ["see occupancy number"], ["open Atrium sales"], ["V1 tile 1.75% occ at 18:44 WITA", "Beta pulse 89% vacant/114"], ["dashboards/data/master.status.json", "/api/owner/pulse-ro atrium_occ LIVE Yanolja 07:16"], "FUNCTIONAL_REAL_DATA", "DATA_MISSING", "/api/owner/pulse-ro#atrium_occ", "Glance exists. Guest in-house, arrivals, ADR still UNKNOWN on the pulse. V1 number and Beta number are different questions. Link must open the sales board, not only the percent."),
    ("owner.pulse.kuta", "Kuta rates tonight glance", "kuta-rates.html", ["see cheapest official rate tonight"], ["open the rates board"], ["Montana Family Double Queen 1,274,000 IDR"], ["master.status.json kutarates", "pulse kuta_rates LIVE"], "FUNCTIONAL_REAL_DATA", "ACTION_MISSING", "/kuta-rates-1.html", "Tonight price is on the pulse. The V1 board and the competitor pipeline are still prove pages, and Wave 8 dropped Kuta from primary Boards."),
    ("owner.pulse.bzg_night", "BZG last-night sales glance", "uma-blu.html", ["see revenue and covers"], ["open venue board"], ["IDR 15,140,000", "87 covers", "biz 2026-09-30"], ["master.status.json bzg", "pulse bzg_night ESB warehouse"], "FUNCTIONAL_REAL_DATA", "WRITE_WORKFLOW_MISSING", "/bzg", "Number is live from ESB. venue_daily_closes=0 so nobody filed a close. Glance is not the close."),
    ("owner.pulse.content", "Content health tile", "atlas.html", ["see content restricted/health"], ["open content"], ["restricted flag"], ["master.status.json content → /api/atlas/health"], "PARTIAL", "NAVIGATION_WRONG", "/content-2.0", "Content exists as a separate IA item. It is not the Owner pulse tile and it is not the six brand boards."),
    ("owner.pulse.leads", "Leads 24h glance", "wolf.html#leads", ["see new leads by brand"], ["open the lead"], ["V1: 2 new 24h GGV1 Habitat0 Atrium1", "Beta: 271 Habitat sheet rows"], ["master.status.json leads", "pulse leads Habitat sheet"], "FUNCTIONAL_REAL_DATA", "DATA_MISSING", "/lead-spine", "Beta answers Habitat-sheet stock. V1 answered new-in-24h across GGV, Habitat, Atrium. core_leads=8 and was ignored. Both questions are still required."),
    ("owner.pulse.hr", "HR status tile", "hr.html", ["see HR restricted"], ["open HR"], ["restricted"], ["master.status.json hr"], "SHELL", "MISSING_FROM_BETA", "/hr-deferred-hold-stamp-1.html", "HR BOUNDARY — map only. Do not implement HR this wave. Do not count the stamp as done."),
    ("owner.pulse.purchasing", "Purchasing glance", "wolf.html#purchasing", ["see open PRs and supplier count"], ["open purchasing"], ["V1 tile: 2 open PRs, 103 suppliers", "DB: purchase_requests=2, pr_orders=543, suppliers=103"], ["master.status.json", "alchemist/data/alchemist.db", "pulse purchasing"], "FUNCTIONAL_REAL_DATA", "ACTION_MISSING", "/api/owner/pulse-ro#purchasing", "Beta shows Alchemist counts (unpaid 106, PRs 543). It does not receive, match, or pay. Beta bzg_ops_purchase_requests=3 and receipt_events=0."),
    ("owner.pulse.alchemist", "Alchemist owe/paid glance", "wolf.html#alchemist", ["see owe, paid, tin, broken"], ["open the buying desk"], ["owe Rp 195,268,172", "paid Rp 314,695,140"], ["master.status.json", "/api/alchemist", "pulse purchasing shares the sqlite"], "READ_ONLY_MIRROR", "WRITE_WORKFLOW_MISSING", "/api/owner/alchemist-ro", "Read counts are real. Pay and mutate stay off. That is correct until a governed pay workflow exists. The V1 confirm/preview actions are not rebuilt."),
    ("owner.pulse.system", "System 14/14 tile", "wolf.html#system", ["see feeds and daemons green"], ["open the failing job"], ["14/14 green"], ["master.status.json system"], "PARTIAL", "ACTION_MISSING", "/integration-health", "A health page is not the home tile, and green-from-present is still the failure mode the Owner used this tile to catch."),
    ("owner.pulse.backup_b2", "Backup B2 capacity tile", "wolf.html#backup", ["see B2 used vs cap"], ["open backup"], ["5319.43GB (42.6%)"], ["master.status.json backup"], "PARTIAL", "DATA_MISSING", "/ops/backup-health-1", "Pulse backup tile is PARTIAL: atrium snapshot STALE. List-ok is not a fresh backup."),
    ("owner.pulse.r2_gap", "R2 backup gap tile", "wolf.html#r2gap", ["see absent object count"], ["open the gap"], ["0 absent, 13716/13716"], ["master.status.json r2gap"], "MISSING", "MISSING_FROM_BETA", "", "No R2-gap tile on the 10-tile pulse. Connection Cloudflare_R2 is CONFIGURED, not a workflow."),
    ("owner.pulse.spartacus_day", "Spartacus day counter", "spartacus.html", ["see day n/75"], ["open the program"], ["Day 1/75"], ["master.status.json", "/api/owner/fitness-ro"], "FUNCTIONAL_REAL_DATA", "LESS_FUNCTIONAL_THAN_V1", "/owner/fitness", "Day counter is a read. Peptide schedule, breathwork, and the Spartacus board are not the V1 desk. Wave 8 retired it from primary Boards."),
    ("owner.desk.calendar", "Wolf calendar", "wolf.html#today", ["see day agenda"], ["create and edit events on primary calendar"], ["events"], ["/api/wolf/calendar", "Google Calendar primary"], "PARTIAL", "WRITE_WORKFLOW_MISSING", "/api/owner/gws-ro", "Calendar READ is live. Create/update stays off. V1 Wolf is the calendar."),
    ("owner.desk.tasks", "Wolf tasks", "wolf.html#tasks", ["see owner tasks"], ["add, tick, comment"], ["tasks"], ["/api/wolf/task", "/api/wolf/tick", "wolf-desk"], "PARTIAL", "LESS_FUNCTIONAL_THAN_V1", "/my-work", "My Work is a different queue (core_work_items=211). It is not the Wolf desk tick/comment loop, and /my-work is auth-blocked."),
    ("owner.desk.asks", "Asks from the team", "wolf.html#asks", ["see team asks"], ["answer in place"], ["asks"], ["wolf.html tile asks"], "MISSING", "MISSING_FROM_BETA", "", "No team-ask rail on Owner Home."),
    ("owner.desk.needs_you", "Needs you", "wolf.html#needs-you", ["see owner decisions"], ["clear an item"], ["mail and decisions"], ["wolf.html"], "PARTIAL", "MORE_CONFUSING_THAN_V1", "/staff-ops-routing", "Needs You exists as its own route, not as a rail on the home cockpit."),
    ("owner.desk.read_view", "Read / View pile", "wolf.html#read-view", ["see things to read"], ["open the file"], ["pile"], ["wolf.html"], "MISSING", "MISSING_FROM_BETA", "", "No read/view pile."),
    ("owner.desk.diet", "Diet and workouts link", "wolf.html#body", ["see the link"], ["open Spartacus"], ["link"], ["wolf.html"], "PARTIAL", "NAVIGATION_WRONG", "/owner/fitness", "Link target is a partial fitness mirror, not the program."),
    ("owner.desk.shareholders", "Shareholders and holdings", "wolf.html#share", ["see holdings and shareholder pack"], ["open the pack"], ["holdings"], ["wolf.html", "HOLDINGS-PERSONAL"], "PARTIAL", "HISTORY_MISSING", "/owner/trading", "Personal holdings note is not the shareholder report pack."),
    ("owner.desk.edits", "Dashboard edits queue", "wolf.html#edits", ["see edit requests"], ["track a change"], ["edits"], ["wolf.html"], "MISSING", "MISSING_FROM_BETA", "", "No dashboard-edit queue."),
    ("owner.desk.reports", "Reports pile", "wolf.html#reports", ["see generated reports"], ["open a report"], ["reports"], ["wolf.html"], "MISSING", "MISSING_FROM_BETA", "", "No owner report pile on the home."),
    ("owner.desk.coder", "Overnight coder queue", "wolf.html#coder", ["see overnight jobs"], ["see what landed"], ["queue"], ["wolf.html", "System-Registry OVERNIGHT-CODER-QUEUE"], "MISSING", "MISSING_FROM_BETA", "", "No overnight-coder surface."),
    ("owner.desk.peaches", "Talk to Peaches", "peaches.html", ["see threads"], ["ask and get a reply on the same board"], ["threads"], ["peaches-desk/threads.jsonl", "/api/peaches-desk"], "MISSING", "MISSING_FROM_BETA", "", "Peaches desk threads are not on Beta Owner Home."),
    ("owner.desk.mission", "Mission control meter", "wolf.html#wolf-mission-control", ["see progress meter"], ["open the race"], ["meter"], ["wolf-progress"], "PARTIAL", "MORE_CONFUSING_THAN_V1", "/progress", "Progress exists and is a finish scoreboard. It is not the V1 mission meter, and it must not be read as almost done."),
]
for i, name, route, see, do, shown, src, bstate, dclass, brep, repair in OWNER:
    add(F(id=i, surface_name=name, route_or_path=route, menu_path="Wolf → Owner Home",
          see=see, do=do, data_shown=shown, data_source=src, user_roles=["owner"],
          business_domains=["OWNER/WOLF"], buttons_actions=do, apis=[a for a in src if a.startswith("/")],
          beta_state=bstate, beta_replacement=brep, difference_class=dclass, required_repair=repair,
          actions_worked_evidence=["master.status.json generated_at 2026-10-01T18:44:57+08:00", "GET /api/owner/pulse-ro 200 this session"]))

# Atrium sales views — one row per view in atrium-sales.html
SALES = [
    ("overview","Overview","see money position","read the board"),
    ("milestones","Milestones","see unit milestones","update milestone"),
    ("payments","Payments","see payment schedule","record payment"),
    ("newsale","New sale","see the form","record this sale"),
    ("inventory","Inventory","see units","open a unit"),
    ("deals","Deal types","see deal types","maintain deal types"),
    ("leads","Leads","see sales leads","work a lead"),
    ("comms","Commissions","see commissions","calculate commission"),
    ("cv","CV Cash","see CV cash","post CV cash"),
    ("payables","CV Payables","see CV payables","pay a vendor"),
    ("tax","Tax Ceiling","see tax ceiling","check the ceiling"),
    ("vendors","Vendors","see vendors","maintain vendor"),
    ("commonarea","Common Area","see common area charges","maintain charges"),
    ("exceptions","Exceptions","see exceptions","clear an exception"),
]
for vid, title, see, do in SALES:
    add(F(id=f"amg.sales.{vid}", surface_name=f"Atrium sales — {title}",
          route_or_path=f"atrium-sales.html#{vid}", menu_path="Atrium → Sales",
          tabs=[title], buttons_actions=[do], see=[see], do=[do],
          data_shown=[title], data_source=["atrium-sales.html view registry", "atrium/atrium_sales.sqlite"],
          user_roles=["atrium"], business_domains=["AMG/ATRIUM","Sales/CRM"],
          apis=["/api/atrium"], workflows=["unit sale → payment → commission"],
          beta_state="SHELL", beta_replacement="/amg-ops-pack",
          difference_class="MORE_CONFUSING_THAN_V1",
          required_repair="One AMG hub with these 14 jobs as tabs. Prove pages are not the sales desk. core_leads=8 is not the 570-row V1 lead table.",
          actions_worked_evidence=["view registry lines atrium-sales.html", "sqlite units=88 payments=399 leads=570 commissions=68 cv_transactions=642"]))

add(F(id="amg.inventory.board", surface_name="Atrium inventory board",
      route_or_path="atrium-inventory.html", menu_path="Atrium → Inventory",
      see=["unit and stock inventory separate from the sales inventory tab"], do=["work inventory"],
      data_source=["atrium-inventory.html"], user_roles=["atrium"], business_domains=["AMG/ATRIUM","Inventory"],
      beta_state="SHELL", beta_replacement="/amg-os-shell", difference_class="MISSING_FROM_BETA",
      required_repair="Inventory is its own V1 board. Do not mark it done because sales has an Inventory tab or because Yanolja room inventory reads."))
add(F(id="amg.management.day", surface_name="Atrium management day board",
      route_or_path="atrium-management.html", menu_path="Atrium → Management",
      see=["day ops"], do=["run the management board"], data_source=["atrium-management.html","atrium-management.status.json"],
      user_roles=["atrium"], business_domains=["AMG/ATRIUM","Hotel Ops"],
      beta_state="PARTIAL", beta_replacement="/amg-daily-ops-state", difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="Daily ops state is a shell/prove relative to the management board. Guest journey is not closed."))
add(F(id="amg.kuta.board", surface_name="Kuta rates board",
      route_or_path="kuta-rates.html", menu_path="Atrium → Kuta rates",
      see=["tonight competitor grid"], do=["read the brief"], buttons_actions=["open brief"],
      data_source=["kuta-rates.html","dashboards/data/kuta-rates.status.json","kuta-rates-brief-2026-10-01.md"],
      background_processes=["com.wolfcommand rate calendar / competitor rates"],
      user_roles=["atrium","owner"], business_domains=["AMG/ATRIUM","Sales/CRM"],
      beta_state="SHELL", beta_replacement="/kuta-rates-1.html", difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="Keep the tonight board. Prove pipeline pages are not the board. Wave 8 retired it from primary IA."))
add(F(id="amg.voice", surface_name="AMG voice seat",
      route_or_path="amg-voice.html", menu_path="Atrium → Voice",
      see=["voice queue"], do=["work a voice item"], apis=["/api/amg/voice"],
      data_source=["amg-voice.html"], user_roles=["atrium"], business_domains=["AMG/ATRIUM"],
      beta_state="SHELL", beta_replacement="/amg-voice-1.html", difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="Prior PARITY called voice seats equivalent. The Beta file is a -1 prove page."))

# Finance screens from atrium-finance.html data-go
FIN = [
    ("control","Command centre","status, queue, exceptions"),
    ("nightaudit","Night audit","revenue in, journal out"),
    ("flash","GM morning flash","one page before coffee"),
    ("procure","Procurement and AP","request → order → receipt → pay"),
    ("assets","Pre-opening and assets","capitalise, register, maintain"),
    ("cash","Cash and bank","position, matching, float"),
    ("payrun","Payment run","batch, withhold, approve, pay"),
    ("payroll","Payroll and service charge","HR feed, pool, distribution"),
    ("tax","Tax and compliance","calendar, packs, receipts"),
    ("close","Month-end close","checklist, accruals, lock"),
    ("owner","Owner reporting","pack, fees, distributions"),
    ("core","Accounting core","journal, GL, trial balance, approvals"),
    ("core-rpt","PSAK and USALI","statutory and management report pack"),
    ("master","Master data and controls","accounts, roles, limits, audit log"),
    ("handoff","Handoff and bot tools","pack index, internal actions"),
]
for vid, title, see in FIN:
    hr = vid == "payroll"
    add(F(id=f"amg.finance.{vid}", surface_name=f"Atrium finance — {title}",
          route_or_path=f"atrium-finance.html#{vid}", menu_path="Atrium → Finance",
          tabs=[title], see=[see], do=[f"operate {title}"],
          data_source=["atrium-finance.html data-go", "atrium_finance.py screens", "atrium-finance/atrium_finance.sqlite"],
          apis=["/api/atrium-finance","/api/accounting"], user_roles=["atrium_finance"],
          business_domains=["Finance","AMG/ATRIUM"] + (["HR boundary"] if hr else []),
          beta_state="SHELL" if vid != "payroll" else "SHELL",
          beta_replacement="/amg/finance" if vid in ("control","flash","owner") else "/fin-"+vid if False else {
              "cash":"/fin-cash-truth-1.html","tax":"/fin-tax-shell-1.html","procure":"/fin-ap-ar-shell-1.html",
              "core":"/atrium-fc-truth-deepen-1.html","payroll":"/hr-deferred-hold-stamp-1.html",
          }.get(vid, "/amg/finance"),
          difference_class="MISSING_FROM_BETA" if hr else "LESS_FUNCTIONAL_THAN_V1",
          required_repair=("HR BOUNDARY — payroll distribution stays blocked. Do not implement HR. Do not count a finance shell as payroll done."
                           if hr else "Prior audit called Atrium finance BETA_BETTER. The Beta files are shells and deepen pages (fin-tax-shell, fin-recon-shell, fin-ap-ar-shell, fc-truth-deepen). SoD must stay. The 15 V1 screens are not tabs yet."),
          actions_worked_evidence=["atrium-finance.html nav buttons", "REPORT_MODULES command/ar/financials/scorecard/preopen/cash"]))

add(F(id="amg.finance.report_export", surface_name="Atrium finance report export",
      route_or_path="/api/atrium-finance report pack", menu_path="Atrium → Finance → Reports",
      see=["simple list or sectioned pack"], do=["build a draft pack"], buttons_actions=["export"],
      data_source=["atrium_finance.py REPORT_MODULES"], user_roles=["atrium_finance"],
      business_domains=["Finance"], beta_state="SHELL", beta_replacement="/amg/finance",
      difference_class="WRITE_WORKFLOW_MISSING",
      required_repair="Export exists in V1 as draft HTML. Beta has no proved pack that a shareholder can open."))

add(F(id="ggv.books", surface_name="GGV books board",
      route_or_path="ggv-finance.html", menu_path="GGV → Books",
      see=["GGV money board"], do=["work books"], apis=["/api/books","/api/money-board","/api/ggv/xero-final"],
      data_source=["ggv-finance.html","ggv-finance/money.sqlite"], user_roles=["ggv_finance"],
      business_domains=["GGV","Finance"], beta_state="PARTIAL", beta_replacement="/ggv-finance",
      difference_class="MORE_CONFUSING_THAN_V1",
      required_repair="Prior MORE_CONFUSING stands. Xero connection is ABSENT. ggv_notas and ggv_invoices in Beta catalog are 0 rows."))
add(F(id="ggv.notas", surface_name="GGV nota intake",
      route_or_path="/api/ggv-notas", menu_path="GGV → Notas",
      see=["supplier notas"], do=["upload and file a nota"], buttons_actions=["upload"],
      forms=["nota upload"], apis=["/api/ggv-notas","/api/ggv-notas/upload"],
      data_source=["serve.py ggv-notas", "scripts/ggv_nota_menu.py"], user_roles=["ggv_finance"],
      business_domains=["GGV","Procurement","Finance"],
      beta_state="MISSING", beta_replacement="", difference_class="MISSING_FROM_BETA",
      required_repair="Catalog ggv_notas=0, ggv_uploads=0. V1 upload path is not a Beta workflow."))
add(F(id="ggv.onboard", surface_name="GGV client onboard and invite",
      route_or_path="ggv-onboarding.html", menu_path="GGV → Onboarding",
      see=["invite form and agreement"], do=["create invite","submit onboard"],
      apis=["/api/ggv-onboard","/api/ggv-onboard/invite/create","/api/ggv-onboard/invite/submit"],
      data_source=["ggv-onboarding.html","ggv-intake-invite.html"], user_roles=["ggv"],
      business_domains=["GGV","Sales/CRM"], beta_state="SHELL", beta_replacement="/ggv-ops-pack",
      difference_class="WRITE_WORKFLOW_MISSING",
      required_repair="Client onboard is a V1 form pair. A GGV ops pack hub does not replace invite → agreement."))
add(F(id="ggv.voice", surface_name="GGV voice seat",
      route_or_path="ggv-voice.html", menu_path="GGV → Voice",
      apis=["/api/ggv/voice"], see=["voice queue"], do=["work voice"],
      data_source=["ggv-voice.html"], user_roles=["ggv"], business_domains=["GGV"],
      beta_state="SHELL", beta_replacement="/ggv-voice-1.html", difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="Overturn voice PARITY. Beta is a -1 prove page."))
add(F(id="ggv.supplier_dedupe", surface_name="GGV supplier dedupe",
      route_or_path="scripts/ggv_nota_merge_suppliers.py", menu_path="GGV → Suppliers",
      see=["duplicate suppliers"], do=["merge with alias file"],
      data_source=["scripts/ggv_nota_supplier_aliases.json"], user_roles=["ggv_finance"],
      business_domains=["GGV","Procurement"], beta_state="MISSING", beta_replacement="",
      difference_class="MISSING_FROM_BETA",
      required_repair="Supplier identity work exists in V1 scripts. Beta ggv_vendors=0."))

# BZG / Uma
UMA = [
    ("uma.today","Uma Blu venue board","uma-blu.html","see venue today","run the board","PARTIAL","/bzg/uma-blu","LESS_FUNCTIONAL_THAN_V1","Today route exists. GET /api/bzg/uma-blu/today returned 403 this session. venue_daily_closes=0."),
    ("uma.recipes.read","Uma Blu recipes read","uma-blu-recipes.html","see 127 recipes and 756 lines","open a recipe","PARTIAL","/bzg-recipe-builder","LESS_FUNCTIONAL_THAN_V1","Beta bzg_recipes.sqlite has the same 127/756 counts. UI not proven (sibling uma API 403)."),
    ("uma.recipes.write","Uma Blu recipe photo and edit","/api/uma-blu-recipes","edit recipe and photo","save recipe","MISSING","","WRITE_WORKFLOW_MISSING","V1 POST photo and recipe save. No proved Beta write."),
    ("uma.tasks","Uma Blu task tick","/api/uma-blu-tasks","see tasks","tick a task","PARTIAL","/bzg-uma-blu-issues.html","ACTION_MISSING","Issues page exists. bzg_ops_operator_issues=0."),
    ("uma.pr","Uma Blu purchase request","alchemist PR","see PRs","raise and receive","PARTIAL","/bzg-uma-blu-pr.html","WRITE_WORKFLOW_MISSING","V1 alchemist has pr_orders=543 and pr_receipt_lines=477. Beta receipt_events=0 and pr_lines=0."),
    ("uma.petty","Uma Blu petty cash","alchemist petty_cash","see petty","record petty","SHELL","/bzg-uma-blu-petty.html","DATA_MISSING","V1 petty_cash=443. Beta bzg_ops_petty_movements=0."),
    ("uma.evidence","Uma Blu evidence loop","uma evidence","see evidence","attach evidence","PARTIAL","/bzg-uma-blu-evidence.html","HISTORY_MISSING","core_evidence_records=28 is not the operating evidence loop."),
    ("uma.bills","Uma Blu bills","bills","see bills","match a bill","SHELL","/bzg-uma-blu-bills.html","ACTION_MISSING","Bills page is not three-way match."),
    ("uma.week","Uma Blu week","/api/uma-blu-week","see the week","plan the week","MISSING","","MISSING_FROM_BETA","V1 week API has no Beta replacement proved."),
    ("uma.console","Uma Blu console","uma-blu-console.html","see console","operate console","MISSING","","MISSING_FROM_BETA","Separate V1 console page has no Beta twin."),
]
for i, name, route, see, do, st, rep, dc, repair in UMA:
    add(F(id=i, surface_name=name, route_or_path=route, menu_path="BZG → Uma Blu",
          see=[see], do=[do], buttons_actions=[do], user_roles=["uma_blu"],
          business_domains=["BZG","UMA BLU","Procurement"],
          data_source=["uma-blu.html / recipes.sqlite / alchemist.db", "catalog/content_library.sqlite counts"],
          beta_state=st, beta_replacement=rep, difference_class=dc, required_repair=repair,
          actions_worked_evidence=["recipes 127/756 both sides", "Beta ops tables mostly 0", "uma today API 403"]))
add(F(id="bzg.voice", surface_name="BZG voice seat", route_or_path="bzg-voice.html", menu_path="BZG → Voice",
      apis=["/api/bzg/voice"], see=["voice queue"], do=["work voice"], user_roles=["uma_blu"],
      business_domains=["BZG"], data_source=["bzg-voice.html"],
      beta_state="SHELL", beta_replacement="/bzg-voice-1.html", difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="Overturn voice PARITY."))
add(F(id="bzg.group", surface_name="Blu Zone group board", route_or_path="blu-zone-group.html", menu_path="BZG → Group",
      see=["group board"], do=["open group"], user_roles=["uma_blu"], business_domains=["BZG"],
      data_source=["blu-zone-group.html","nav-entities.json"],
      beta_state="PARTIAL", beta_replacement="/bzg", difference_class="MORE_CONFUSING_THAN_V1",
      required_repair="Group hub exists. Outlet registry has 7 rows and 6 are PRE-OPENING with no ops."))
add(F(id="bzg.month.july", surface_name="BZG July 2026 board", route_or_path="bzg-july-2026.html", menu_path="BZG → Monthly",
      see=["frozen July board"], do=["read history"], business_domains=["BZG","Finance"], user_roles=["owner"],
      data_source=["bzg-july-2026.html"], beta_state="MISSING", beta_replacement="",
      difference_class="HISTORY_MISSING", required_repair="Historical monthly board. Preserve. Do not pretend a live PnL shell replaces it."))
add(F(id="bzg.month.august", surface_name="BZG August 2026 board", route_or_path="bzg-august-2026.html", menu_path="BZG → Monthly",
      see=["frozen August board"], do=["read history"], business_domains=["BZG","Finance"], user_roles=["owner"],
      data_source=["bzg-august-2026.html"], beta_state="MISSING", beta_replacement="",
      difference_class="HISTORY_MISSING", required_repair="Same as July. Historical preserve."))
add(F(id="bzg.shareholder", surface_name="BZG shareholder reports", route_or_path="bzg-shareholder-reports.html",
      menu_path="BZG → Shareholders", see=["shareholder pack"], do=["open a report"],
      apis=["/api/shareholder-bank-statements"], business_domains=["BZG","Finance"], user_roles=["owner"],
      data_source=["bzg-shareholder-reports.html"], beta_state="SHELL", beta_replacement="/bzg-finance",
      difference_class="HISTORY_MISSING", required_repair="Prior PARITY on BZG monthly is overturned for the shareholder file itself."))

# Content — shared workflows plus one board per brand
BRANDS = ["atrium","habitat","uma-blu","selong-selo","tropik","goss-group"]
for b in BRANDS:
    add(F(id=f"content.board.{b}", surface_name=f"Content board — {b}",
          route_or_path=f"content-{b}.html", menu_path=f"Content → {b}",
          see=["glance, week 1/2, post cards, stories"], do=["edit a card via comment"],
          tabs=["glance","week 1","week 2"], user_roles=["content"],
          business_domains=["Content/Marketing", b],
          data_source=[f"content-{b}.html","dashboards/data/content-plans"],
          apis=["/api/content","/api/content/plan"],
          beta_state="PARTIAL", beta_replacement="/content-2.0",
          difference_class="LESS_FUNCTIONAL_THAN_V1",
          required_repair="Prior PARITY lumped all brand boards. Each board is its own cadence. Content 2.0 does not replace the six boards. Library assets=48 vs NAS shallow 38091."))
CONTENT_FN = [
    ("content.hub","Content hub doors","content.html","open brand, atlas, ads, training"),
    ("content.cycle.print","Printable 14-day cycle","/api/content/cycle/print","download the cycle"),
    ("content.cycle.comment","Card comment","/api/content/cycle/comment","comment on a card"),
    ("content.cycle.apply","Amanda apply","/api/content/cycle/apply","apply a comment to the brief"),
    ("content.machine.tick","Tick sends Metricool draft","/api/content/machine/status","tick a finished card"),
    ("content.machine.pack","Machine pack if Metricool fails","/api/content/machine/pack","land files on Misa desk"),
    ("content.ads","Ads studio","ads-studio.html","brief, upload, fill, packet"),
    ("content.review","Creative review","/api/content/review","verdict and comment"),
    ("content.briefs","Briefs approval","/api/content/briefs","approve a brief"),
    ("content.ideas","Ideas inbox","/api/content/ideas","upload an idea"),
    ("content.demand","Content demand","/api/content/demand","see demand"),
    ("content.library","Content library scan","/api/content/library/scan","scan and open a file"),
    ("content.studio","Content studio upload","/api/content/studio/upload","upload to studio"),
    ("content.training","Training centre","/api/training","open training file"),
    ("content.reviews.google","Google review reply","/api/google-reviews","write the reply that updates Google"),
    ("content.atlas","Atlas health and produce","/api/atlas","see atlas health"),
    ("content.catalogue","Media catalogue","catalogue.html","browse catalogue"),
    ("content.habitat.today","Habitat content today","/api/content/habitat/today","see habitat today"),
    ("content.plan.chat","Plan chat","/api/content/plan-chat","chat a plan change"),
    ("content.resolve","Resolve studio","resolve-studio/","edit a film job"),
]
for i, name, route, do in CONTENT_FN:
    add(F(id=i, surface_name=name, route_or_path=route, menu_path="Content",
          see=[name], do=[do], buttons_actions=[do], user_roles=["content"],
          business_domains=["Content/Marketing"],
          data_source=[route, "serve.py content routes"],
          beta_state="PARTIAL" if i in ("content.hub","content.library","content.atlas") else "SHELL",
          beta_replacement="/content-2.0" if "cycle" in i or i=="content.hub" else "/seat-ads-studio-1.html" if i=="content.ads" else "/seat-resolve-studio-1.html" if i=="content.resolve" else "/content-engine-live",
          difference_class="WRITE_WORKFLOW_MISSING" if i in ("content.machine.tick","content.cycle.apply","content.reviews.google","content.ads") else "LESS_FUNCTIONAL_THAN_V1",
          required_repair="Overturn content PARITY. Metricool READ is live (6 brands, schedules) and WRITE is off. Tick→draft→Misa is not operational. NAS full_tree_indexed=false."))

# Personal
TRADING = ["Holdings","Trade journal","TTC paper method","Morning brief","Filings","Earnings","Sector","Insider","Chatter","Floor","Research desk","8-step desk","Sandbox","Agent OS"]
for t in TRADING:
    slug = re.sub(r"[^a-z0-9]+","-", t.lower()).strip("-")
    add(F(id=f"owner.trading.{slug}", surface_name=f"Trading — {t}",
          route_or_path="trading.html", menu_path="Wolf Tools → Trading",
          tabs=[t], see=[t], do=["read"] + (["save tickers","add journal line"] if t in ("Holdings","Trade journal") else ["read"]),
          forms=["holdings-add"] if t=="Holdings" else [],
          apis=["/api/trading","/api/trading/journal","/api/trading/holdings"],
          data_source=["dashboards/assets/trading-desk.js","trading-desk/journal.jsonl"],
          user_roles=["owner"], business_domains=["Personal/Trading/Fitness/Travel/Learning"],
          beta_state="READ_ONLY_MIRROR", beta_replacement="/owner/trading",
          difference_class="LESS_FUNCTIONAL_THAN_V1",
          required_repair="Wave 8 retired Trading from primary Boards. /api/owner/trading-ro is PARTIAL, paper, no broker, NOT_REBUILT_PLUS_PROVEN. One RO page is not 14 cards. Nothing may trade."))
add(F(id="owner.fitness.program", surface_name="Spartacus program board",
      route_or_path="spartacus.html", menu_path="Wolf Tools → Spartacus",
      see=["Sparta/Wolf75, peptides, breathwork"], do=["log the day"],
      apis=["/api/spartacus","/api/spartacus/board"],
      data_source=["spartacus.html","~/.openclaw/personal/health/spartacus.sqlite"],
      user_roles=["owner"], business_domains=["Personal/Trading/Fitness/Travel/Learning"],
      beta_state="READ_ONLY_MIRROR", beta_replacement="/owner/fitness",
      difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="Fitness glance is LIVE day 1. The program board is not. Fitness is not HR."))
add(F(id="owner.travel.board", surface_name="Travel board",
      route_or_path="travel.html", menu_path="Wolf Tools → Travel",
      see=["itineraries"], do=["edit a trip"], data_source=["travel.html"],
      user_roles=["owner"], business_domains=["Personal/Trading/Fitness/Travel/Learning"],
      beta_state="READ_ONLY_MIRROR", beta_replacement="/owner/travel",
      difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="travel-ro returned draft tiles (Europe, Vegas, Holiday ideas) with outbound_link_count mostly 0. Nobody books from it. Wave 8 retired the board."))
add(F(id="owner.learning.desk", surface_name="Learning desk",
      route_or_path="learning.html", menu_path="Wolf Tools → Learning",
      see=["TTC and acquisition lessons"], do=["drop a lesson","start research"],
      apis=["/api/learning","/api/learning/research","/api/learning/start","/api/learning/file"],
      data_source=["learning.html"], user_roles=["owner"],
      business_domains=["Personal/Trading/Fitness/Travel/Learning"],
      beta_state="READ_ONLY_MIRROR", beta_replacement="/owner/learning",
      difference_class="MISSING_FROM_BETA",
      required_repair="learning-ro honesty says PARTIAL and not /intel/learning. No lesson drop, no 48h calendar action."))
add(F(id="owner.radar.board", surface_name="Wolf radar",
      route_or_path="radar.html", menu_path="Wolf Tools → Radar",
      see=["owner plan"], do=["add a radar task"], apis=["/api/radar","/api/radar/task"],
      data_source=["radar.html"], user_roles=["owner"], business_domains=["OWNER/WOLF"],
      beta_state="READ_ONLY_MIRROR", beta_replacement="/owner/radar",
      difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="radar-ro is a honesty page. It is not the V1 plan board. No invented Mars meter."))

# Desks
DESKS = [
    ("desk.amanda.tasks","Amanda tasks","amanda.html","/api/amanda/task","tick and comment"),
    ("desk.amanda.invoices","Amanda invoices","amanda.html","/api/amanda/invoices","file an invoice"),
    ("desk.amanda.reviews","Amanda Google review reply","amanda.html","/api/amanda/review-reply","send the reply"),
    ("desk.mila","Mila desk","mila.html","/api/mila/task","tick and note"),
    ("desk.haikal","Haikal desk","haikal-desk.html","","work the desk"),
    ("desk.misa","Misa publish queue","misa.html","/api/content/machine","publish in Metricool"),
    ("desk.peaches.threads","Peaches threads","peaches.html","/api/peaches-desk","reply on the board"),
]
for i, name, route, api, do in DESKS:
    add(F(id=i, surface_name=name, route_or_path=route, menu_path=name,
          see=[name], do=[do], apis=[api] if api else [], user_roles=["staff"],
          business_domains=["My Work/Approvals/Evidence"],
          data_source=[route],
          beta_state="PARTIAL", beta_replacement="/my-work",
          difference_class="LESS_FUNCTIONAL_THAN_V1",
          required_repair="Person-named desks should not return as primary IA. The jobs they did (invoice, review reply, Misa publish, Peaches thread) are not in My Work. core_approval_requests=0."))

add(F(id="legal.desk", surface_name="Legal desk", route_or_path="legal.html", menu_path="Legal",
      see=["matters, stock, suggestions"], do=["suggest","upload"],
      apis=["/api/legal","/api/legal/suggest","/api/legal/upload"],
      user_roles=["legal"], business_domains=["OWNER/WOLF"],
      data_source=["legal.html","dashboards/data/legal.status.json"],
      beta_state="MISSING", beta_replacement="", difference_class="MISSING_FROM_BETA",
      required_repair="No Beta legal desk in this inventory pass."))
add(F(id="admin.access", surface_name="Admin access editor", route_or_path="admin-access.html", menu_path="Wolf → Admin",
      see=["who can see what"], do=["change an allow list"], apis=["/api/admin-access"],
      user_roles=["owner"], business_domains=["OWNER/WOLF","Backup/Infra"],
      data_source=["admin-access.html","dashboards/access-config.json"],
      beta_state="PARTIAL", beta_replacement="/staff-access-truth-1.html",
      difference_class="PERMISSION_WRONG",
      required_repair="Staff access truth is a prove page. V1 editor is live and dangerous; Beta must not copy it open. Authority engine is the replacement and it is not proved (org_authority_limits=0)."))
add(F(id="owner.habitat.investment", surface_name="Habitat investment 2026",
      route_or_path="habitat-investment-2026.html", menu_path="Owner → Habitat investment",
      see=["investment board"], do=["read"], user_roles=["owner"], business_domains=["GGV","OWNER/WOLF"],
      data_source=["habitat-investment-2026.html"],
      beta_state="SHELL", beta_replacement="/habitat-investment-1.html",
      difference_class="LESS_FUNCTIONAL_THAN_V1",
      required_repair="Overturn PARITY. Beta file is habitat-investment-1."))
add(F(id="brands.doors", surface_name="Brand doors", route_or_path="brands.html", menu_path="Brands",
      see=["brand entry doors"], do=["open a brand"], user_roles=["content","owner"],
      business_domains=["Content/Marketing"],
      data_source=["brands.html","brands-*.html","nav-entities.json"],
      beta_state="PARTIAL", beta_replacement="/owner-empire-pack",
      difference_class="NAVIGATION_WRONG",
      required_repair="V1 has per-brand doors including Habitat and Selong Selo. Beta IA is business chips, not those doors."))

# n8n
N8N = [
    ("01-ggv-new-lead","GGV new lead"),
    ("02-amg-pre-arrival","AMG pre-arrival"),
    ("03-bzg-daily-sales-xero","BZG daily sales to Xero"),
    ("04-media-auto-catalogue","Media auto catalogue"),
    ("05-amg-post-stay-review","AMG post-stay review"),
    ("06-monthly-pnl-summary","Monthly PnL summary"),
    ("07-bzg-cogs-alert","BZG COGS alert"),
    ("08-weekly-content-gap","Weekly content gap"),
    ("09-xero-bill-webhook","Xero bill webhook"),
    ("10-xero-payment-received","Xero payment received"),
    ("11-xero-daily-pl-digest","Xero daily P&L digest"),
]
for fn, title in N8N:
    add(F(id=f"n8n.{fn}", surface_name=f"n8n — {title}",
          route_or_path=f"n8n-templates/{fn}.json", menu_path="Automations",
          see=[title], do=["run the workflow"], workflows=[title],
          integrations=["n8n"] + (["Xero"] if "xero" in fn else []),
          business_domains=["Backup/Infra"], user_roles=["system"],
          data_source=[f"n8n-templates/{fn}.json"],
          beta_state="MISSING", beta_replacement="",
          difference_class="INTEGRATION_MISSING",
          required_repair="Template exists. Xero connection state is ABSENT. Do not mark a template file as an operating workflow."))

# Launchd families — one function per live plist stem, plist-only
la_dir = Path.home()/"Library/LaunchAgents"
plists = sorted(p for p in la_dir.glob("com.wolfcommand*.plist") if p.suffix==".plist" and ".plist." not in p.name)
# glob *.plist may still include? suffix check. parked files end with .disabled not .plist if we used suffix
# The 169 are real plists. bak files end with .plist.bak-... so suffix is not .plist if name is file.bak
# Path.suffix for "x.plist.bak-foo" is .bak-foo? actually suffix is last suffix only if? 
# "foo.plist.bak-x" suffix is the part after last dot. Good.
stems = defaultdict(list)
for p in plists:
    stems[p.name].append(p.name)
add(F(id="infra.launchd.live_plists", surface_name="Live LaunchAgent set",
      route_or_path=str(la_dir), menu_path="System",
      see=[f"{len(plists)} live plist files", "280 names including bak/parked/disabled"],
      do=["run scheduled jobs"], background_processes=sorted(p.name for p in plists)[:40],
      data_source=["~/Library/LaunchAgents/com.wolfcommand*"],
      user_roles=["system"], business_domains=["Backup/Infra"],
      beta_state="PARTIAL", beta_replacement="/integration-health",
      difference_class="INTEGRATION_MISSING",
      required_repair=f"This session: {len(plists)} files whose name ends in .plist, and 280 names matching com.wolfcommand* once bak/parked/disabled siblings are included. Prior parity said ~283. Beta does not operate this schedule. A health page is not the jobs.",
      actions_worked_evidence=[f"plist_count={len(plists)}"]))

# HR boundary map — not done
HRB = [
    ("hr.roster","HR roster read","/api/hr"),
    ("hr.edit","HR employee edit","/api/hr/edit"),
    ("hr.documents","HR documents","/api/hr/documents"),
    ("hr.shifts","HR shifts","/api/hr/shifts"),
    ("hr.payments","HR payments","/api/hr/payments"),
    ("hr.service_charge","Service charge calculate and confirm","/api/hr/sc/calculate"),
    ("hr.reviews","PRF reviews","/api/hr/reviews"),
    ("hr.payslips","Payslips","/api/hr/payslips"),
    ("hr.exec","HR exec report","/api/hr/exec-report"),
    ("hr.tasks","HR tasks","/api/hr/tasks"),
]
for i, name, api in HRB:
    add(F(id=i, surface_name=name, route_or_path="hr.html", menu_path="HR (deferred)",
          see=[name], do=["deferred"], apis=[api], user_roles=["hr"],
          business_domains=["HR boundary"],
          data_source=["serve.py HR routes","~/.openclaw/hr/state"],
          beta_state="SHELL", beta_replacement="/hr-deferred-hold-stamp-1.html",
          difference_class="MISSING_FROM_BETA",
          required_repair="HR BOUNDARY — identified, not implemented, not counted as done anywhere else."))

# Business needs with no V1 product surface
NEEDS = [
    ("need.pool-bar","Pool Bar operating desk","F&B","Rainforest / Pool Bar","Outlet registry OU-BZG-RAIN-POOL PRE-OPENING. No V1 board."),
    ("need.merah","Merah operating desk","F&B","Merah","Registry BZG-MERAH PRE-OPENING. No board."),
    ("need.rooftop","Rooftop operating desk","F&B","Rooftop","Registry BZG-ROOF PRE-OPENING. No board."),
    ("need.room-service","Room service desk","Hotel Ops","Room Service","Registry BZG-RS PRE-OPENING. No board."),
    ("need.catering","Catering desk","Events/Ballroom","Catering","Registry BZG-CAT PRE-OPENING. No board."),
    ("need.rainforest","Blu Zone Restaurant pre-open","F&B","Rainforest","Registry still says Rainforest, target note ~7 Oct 2026. Standing name is Blu Zone Restaurant ~mid-Oct. No live ops to invent."),
    ("need.maintenance","Cross-entity maintenance and PM","Maintenance","Maintenance","Interview round 8. No V1 board. No Beta work orders that match assets screen."),
    ("need.security","Security / CCTV evidence","Security","Security","Interview round 8. No surface."),
    ("need.events","Events and ballroom","Events/Ballroom","Events/Ballroom","No V1 or Beta board found this pass."),
    ("need.tours","Tours and concierge","Tours/Concierge","Tours/Concierge","No surface. Guest requests are not a concierge desk."),
    ("need.guest.journey","Guest pre-arrival to departure","Hotel Ops","Guest Experience","n8n templates 02 and 05 exist. reservations.db rows=1. Not a journey."),
    ("need.recipe.variance","Recipe to theoretical vs actual variance","Recipes/Costing","UMA BLU","recipe_compare=0 in V1. No variance policy rows that fire (venue_close_variance_policies=0)."),
    ("need.monthend.shareholder","Month-end close to shareholder pack","Finance","Finance","Finance close screen exists in V1 and is not proved. Beta close is a shell. Chain broken."),
    ("need.content.learn","Publish result back into the next brief","Content/Marketing","Content/Marketing","Metricool analytics write path off. performance_records=1103 is not the learning loop."),
    ("need.approvals","Universal approval with segregation","My Work/Approvals/Evidence","My Work/Approvals/Evidence","core_approval_requests=0, core_delegations=0, org_authority_limits=0."),
    ("need.crm.identity","Canonical customer identity","Sales/CRM","Sales/CRM","guest-profiles.db guests=1. core_leads=8. Habitat sheet 271 is a different store."),
    ("need.housekeeping","Housekeeping and room status","Hotel Ops","Hotel Ops","Interview round 4. No board."),
    ("need.cash.theft","Cash theft control and daily close","Finance","Finance","Interview round 2. Petty exists in Alchemist. Beta petty table is empty. No control workflow."),
    ("need.menu.engineering","Menu engineering","Recipes/Costing","BZG","Interview round 5. Recipes copied. Engineering is not."),
    ("need.sale.readiness","Sale readiness data room","OWNER/WOLF","OWNER/WOLF","Interview round 13. /sale-evidence-pack is a system page, not a buyer room."),
]
for i, name, dom, dom2, repair in NEEDS:
    add(F(id=i, surface_name=name, route_or_path="NO_V1_SURFACE", menu_path="Business need — not a V1 page",
          see=["nothing in the product"], do=["not available"], user_roles=["owner"],
          business_domains=[dom, dom2], data_source=["org_outlet_registry","Interview_Ledger.csv rounds 2-13"],
          beta_state="MISSING", beta_replacement="", difference_class="MISSING_FROM_BETA",
          required_repair=repair + " Newly discovered relative to the 22-surface parity audit.",
          actions_worked_evidence=["not a reconstructed V1 feature"]))

# Attach beta fields already set. Dump.
def dump(path, rows):
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

dump(OUT/"V1-SURFACE-INVENTORY.jsonl", V1_ROWS)

# Beta pages
beta_pages = []
htmls = sorted((BETA/"dashboards").glob("*.html"))
def classify_page(name, text):
    n = name.lower()
    head = text[:5000].lower()
    if "hr-deferred" in n or "deferred" in n:
        return "SHELL"
    if n in ("owner-trading-1.html","owner-fitness-1.html","owner-travel-1.html","owner-learning-1.html","owner-radar-1.html"):
        return "READ_ONLY_MIRROR"
    if any(s in n for s in ("shell","prove","deepen","stamp")) or n.endswith("-1.html"):
        return "SHELL"
    if "migration_state" in head and "partial" in head:
        return "PARTIAL"
    return "PARTIAL"

for p in htmls:
    text = p.read_text(errors="replace")
    cls = classify_page(p.name, text)
    beta_pages.append({
        "id": "beta.page."+p.stem,
        "record_kind": "page_surface",
        "route_or_path": "/"+p.stem if not p.stem.endswith(".html") else "/"+p.stem,
        "surface_name": p.stem,
        "classification": cls,
        "staff_ready": False,
        "human_proven": False,
        "evidence": f"dashboards/{p.name} filename+head classify; default PARTIAL when not an obvious shell",
    })

# Exploded beta functions with honest class
BETA_FN = [
    ("beta.fn.pulse.atrium_occ","Atrium occ glance","/api/owner/pulse-ro","FUNCTIONAL_REAL_DATA","89% vacant/114 from Yanolja last-read. Arrivals UNKNOWN."),
    ("beta.fn.pulse.kuta","Kuta tonight glance","/api/owner/pulse-ro","FUNCTIONAL_REAL_DATA","Cheapest official 1,274,000 IDR."),
    ("beta.fn.pulse.bzg","BZG night glance","/api/owner/pulse-ro","FUNCTIONAL_REAL_DATA","ESB warehouse. venue_daily_closes=0."),
    ("beta.fn.pulse.leads","Habitat lead stock glance","/api/owner/pulse-ro","FUNCTIONAL_REAL_DATA","271 sheet rows. Not the V1 24h multi-brand tile."),
    ("beta.fn.pulse.purchasing","Alchemist count glance","/api/owner/pulse-ro","FUNCTIONAL_REAL_DATA","Unpaid 106, pr_orders treated as PRs 543. No receive/pay."),
    ("beta.fn.pulse.fitness","Fitness day glance","/api/owner/pulse-ro","FUNCTIONAL_REAL_DATA","Day 1 from fitness-ro. Not the program."),
    ("beta.fn.pulse.metricool","Metricool schedule glance","/api/owner/pulse-ro","FUNCTIONAL_REAL_DATA","6 brands, schedules. WRITE OFF."),
    ("beta.fn.pulse.nas","NAS/B2 desk stamp","/api/owner/pulse-ro","FUNCTIONAL_REAL_DATA","Media 38091. full_tree_indexed=false. Library assets table this session=48."),
    ("beta.fn.pulse.gws","GWS read card","/api/owner/gws-ro","READ_ONLY_MIRROR","Draft-only Gmail. Calendar write off."),
    ("beta.fn.pulse.backup","Backup tile","/api/owner/pulse-ro","PARTIAL","Stale atrium snap. Not LIVE."),
    ("beta.fn.trading.ro","Trading read mirror","/api/owner/trading-ro","READ_ONLY_MIRROR","PARTIAL paper. No 14-card desk."),
    ("beta.fn.learning.ro","Learning read mirror","/api/owner/learning-ro","READ_ONLY_MIRROR","Not the learning desk."),
    ("beta.fn.travel.ro","Travel read mirror","/api/owner/travel-ro","READ_ONLY_MIRROR","Draft tiles. Nobody books."),
    ("beta.fn.radar.ro","Radar read mirror","/api/owner/radar-ro","READ_ONLY_MIRROR","Honesty page."),
    ("beta.fn.alchemist.ro","Alchemist read","/api/owner/alchemist-ro","READ_ONLY_MIRROR","Counts real. Pay off."),
    ("beta.fn.uma.today","Uma today","/api/bzg/uma-blu/today","PARTIAL","HTTP 403 without JWT this session. Not proved."),
    ("beta.fn.uma.pr","Uma PR page","/bzg-uma-blu-pr","PARTIAL","Page exists. Beta PR lines 0."),
    ("beta.fn.uma.petty","Uma petty page","/bzg-uma-blu-petty","SHELL","petty_movements=0 against V1 443."),
    ("beta.fn.uma.issues","Uma issues","/bzg-uma-blu-issues","SHELL","operator_issues=0."),
    ("beta.fn.uma.evidence","Uma evidence","/bzg-uma-blu-evidence","PARTIAL","evidence_records=28. Loop not proved."),
    ("beta.fn.uma.bills","Uma bills","/bzg-uma-blu-bills","SHELL","Not match-to-pay."),
    ("beta.fn.recipes","Recipe library copy","catalog/bzg_recipes.sqlite","PARTIAL","127 recipes, 756 lines copied. Variance not built."),
    ("beta.fn.content2","Content 2.0 hub","/content-2.0","PARTIAL","Hub. Not six boards, not tick-to-publish."),
    ("beta.fn.mywork","My Work","/my-work","PARTIAL","core_work_items=211. Approvals 0. Page auth-blocked in prior sample."),
    ("beta.fn.finance.shells","Finance shells","/fin-tax-shell-1.html","SHELL","Tax, recon, AP/AR, bank shells. Not the 15 V1 screens."),
    ("beta.fn.ggv.pack","GGV ops pack","/ggv-ops-pack","PARTIAL","Hub. Notas 0. Xero ABSENT."),
    ("beta.fn.amg.pack","AMG ops pack","/amg-ops-pack","PARTIAL","Hub of prove pages. Not 14 sales views."),
    ("beta.fn.approvals","Approvals","core_approval_requests","MISSING","0 requests, 0 delegations."),
    ("beta.fn.closes","Venue daily close","venue_daily_closes","MISSING","0 closes."),
    ("beta.fn.hr","HR hold","/hr-deferred-hold-stamp-1.html","SHELL","Boundary only."),
]
for i, name, route, cls, ev in BETA_FN:
    beta_pages.append({
        "id": i, "record_kind": "function", "surface_name": name, "route_or_path": route,
        "classification": cls, "staff_ready": False, "human_proven": False,
        "evidence": ev, "menu_path": "Beta", "actions_worked_evidence": [ev],
    })

dump(OUT/"BETA-SURFACE-INVENTORY.jsonl", beta_pages)

# Difference matrix from V1 rows
matrix = []
for r in V1_ROWS:
    matrix.append({
        "v1_ref": r["id"],
        "user": ",".join(r.get("user_roles") or ["owner"]),
        "function": r["surface_name"],
        "source_data": "; ".join(r.get("data_source") or []),
        "action": "; ".join(r.get("do") or []),
        "downstream": "; ".join(r.get("downstream") or []) or r.get("required_repair",""),
        "beta_replacement": r.get("beta_replacement") or "",
        "beta_state": r.get("beta_state"),
        "difference_class": r.get("difference_class"),
        "required_repair": r.get("required_repair"),
    })
dump(OUT/"V1-BETA-DIFFERENCE-MATRIX.jsonl", matrix)

missing = []
for r in V1_ROWS:
    st = r.get("beta_state")
    if st in ("FUNCTIONAL","FUNCTIONAL_REAL_DATA","HUMAN_PROVEN") and r.get("difference_class") in ("SUPERSEDED_CORRECTLY","BETA_BETTER"):
        continue
    # glances that are real-data still have a gap class — keep them in the register
    if r.get("difference_class") in ("SUPERSEDED_CORRECTLY",) :
        continue
    missing.append({
        "id": r["id"],
        "function": r["surface_name"],
        "beta_state": st,
        "difference_class": r.get("difference_class"),
        "business_domains": r.get("business_domains"),
        "required_repair": r.get("required_repair"),
        "v1_route": r.get("route_or_path"),
        "discovered": "code/route/db this session" if not str(r["id"]).startswith("need.") else "business/interview — absent from 22-surface parity",
        "staff_ready": False,
    })
dump(OUT/"MISSING-FUNCTION-REGISTER.jsonl", missing)

# stats
v1_dom = Counter()
for r in V1_ROWS:
    for d in r.get("business_domains") or ["unassigned"]:
        v1_dom[d]+=1
beta_cls = Counter(r["classification"] for r in beta_pages)
beta_kind = Counter(r["record_kind"] for r in beta_pages)
diff = Counter(r["difference_class"] for r in matrix)
bst = Counter(r["beta_state"] for r in V1_ROWS)
stats = {
    "as_of": AS_OF,
    "v1_functions": len(V1_ROWS),
    "v1_by_domain": dict(v1_dom),
    "beta_records": len(beta_pages),
    "beta_by_kind": dict(beta_kind),
    "beta_by_class": dict(beta_cls),
    "matrix": len(matrix),
    "diff": dict(diff),
    "beta_state_on_v1": dict(bst),
    "missing": len(missing),
    "human_proven": 0,
    "plist_live": len(plists),
    "prior_parity_surfaces": 22,
    "v1_html": 55,
    "manifest": 23,
    "beta_html": len(htmls),
}
(OUT/"INVENTORY-STATS.json").write_text(json.dumps(stats, indent=2))
print(json.dumps(stats, indent=2))
