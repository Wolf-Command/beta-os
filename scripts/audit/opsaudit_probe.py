#!/usr/bin/env python3
"""OPSAUDIT-1 read-only probe.

Starts a short-lived Beta handler in development_assertion for this process
only. Does not restart :8788, does not change that process's auth mode, and
does not submit POST/PUT/PATCH/DELETE. Catalog writes stay on a temp copy.
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import re
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

from core import canonical_guard  # noqa: E402

canonical_guard.install()

import serve_beta as sb  # noqa: E402

CLASSES = {
    "WORKING",
    "WORKING BUT NOT COMMISSIONED",
    "REAL DATA NOT WIRED",
    "EXISTING IMPLEMENTATION NOT MOUNTED",
    "BROKEN",
    "BLOCKED BY EXTERNAL DEPENDENCY",
    "NOT YET BUILT",
}
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
OUT_DIR = ROOT / "state" / "ops"

SEATS = (
    {"seat": "Owner", "person": "Matthew Goss", "person_id": "PERS-MATT", "email": "mrwolf@wolfcommand.net", "role": "ROLE-MATT", "role_label": "Owner / Executive"},
    {"seat": "Creative Director", "person": "Haikal", "person_id": "PERS-HAIKAL", "email": "haikalqilbari123@gmail.com", "role": "ROLE-GGV-CREATIVE-DIRECTOR", "role_label": "Creative Director"},
    {"seat": "Creative Director", "person": "Misa", "person_id": "PERS-MISA", "email": "mlsary111@gmail.com", "role": "ROLE-GGV-CREATIVE-DIRECTOR", "role_label": "Creative Director"},
    {"seat": "Creative Director", "person": "Zarah", "person_id": "PERS-ZARAH", "email": "zarah.lestrange@gmail.com", "role": "ROLE-GGV-CREATIVE-DIRECTOR", "role_label": "Creative Director"},
    {"seat": "Creative Director", "person": "Frail", "person_id": "PERS-FRAIL", "email": "frail.bongat@icloud.com", "role": "ROLE-GGV-CREATIVE-DIRECTOR", "role_label": "Creative Director"},
    {"seat": "Content Creator", "person": "Yudi", "person_id": "PERS-YUDI", "email": "widiatmika.11@gmail.com", "role": "ROLE-CONTENT-CREATOR", "role_label": "Content Creator"},
    {"seat": "Content Creator", "person": "Gery", "person_id": "PERS-GERY", "email": "mr.gerryarfanata@gmail.com", "role": "ROLE-CONTENT-CREATOR", "role_label": "Content Creator"},
    {"seat": "Content Creator", "person": "Alam", "person_id": "PERS-ALAM", "email": "alamprojects26@gmail.com", "role": "ROLE-CONTENT-CREATOR", "role_label": "Content Creator"},
    {"seat": "Content Creator", "person": "TJ", "person_id": "PERS-TJ", "email": "tejasaputra.wahyuhidayat@gmail.com", "role": "ROLE-CONTENT-CREATOR", "role_label": "Content Creator"},
    {"seat": "Content Creator", "person": "Nata", "person_id": "PERS-NATA", "email": "omnia.folio@gmail.com", "role": "ROLE-CONTENT-CREATOR", "role_label": "Content Creator"},
    {"seat": "Content Creator", "person": "Rapp", "person_id": "PERS-RAPP", "email": "evetrovert@gmail.com", "role": "ROLE-CONTENT-CREATOR", "role_label": "Content Creator"},
    {"seat": "Content Management", "person": "Amanda", "person_id": "PERS-AMANDA", "email": "amanda@wolfcommand.net", "role": "ROLE-CONTENT-MGMT", "role_label": "Content Management"},
    {"seat": "GGV Finance Operator", "person": "Amanda", "person_id": "PERS-AMANDA", "email": "amanda@wolfcommand.net", "role": "ROLE-GGV-FINANCE-OPERATOR", "role_label": "GGV Finance Operator"},
    {"seat": "Atrium Finance Officer", "person": "Zayen", "person_id": "PERS-ZAYEN", "email": "laluzayen@gmail.com", "role": "ROLE-AMG-FINANCE-OFFICER", "role_label": "Atrium Finance Officer"},
    {"seat": "BZG F&B Operations Lead", "person": "Devi", "person_id": "PERS-DEVI", "email": "deviputu236@gmail.com", "role": "ROLE-BZG-FB-OPS-LEAD", "role_label": "BZG F&B Operations Lead"},
)

# Routes each seat is shown, plus the denials the nav or a typed address can hit.
ROUTES = {
    "PERS-MATT": [
        "/", "/wolf", "/owner-empire-pack", "/staff-ops-routing", "/my-work",
        "/content-2.0", "/content-2.0#library", "/content-2.0#upload",
        "/ggv-ops-pack", "/ggv/finance", "/ggv/finance/invoices", "/ggv/finance/notas",
        "/ggv/finance/vendors", "/ggv/finance/customers", "/ggv/finance/history", "/ggv/finance/reports",
        "/amg-ops-pack", "/amg/finance", "/amg/finance/lite",
        "/bzg", "/bzg/uma-blu", "/bzg/uma-blu/bills", "/bzg/uma-blu/issues",
        "/bzg/uma-blu/petty", "/bzg/uma-blu/evidence", "/bzg/uma-blu/exceptions", "/uma-blu-close",
        "/intel-ops-pack", "/progress", "/integration-health", "/sale-evidence-pack",
        "/finish-war-room", "/hr-hiring-onboarding", "/hr-training-competency",
        "/hr-payroll-inputs", "/hr-retention-signals", "/habitat-operator", "/lead-spine",
        "/api/staff/home", "/api/wolf/shell-whoami", "/api/owner/war-room",
        "/api/hr/hiring-onboarding", "/api/assets?brand=atrium&page=1&limit=1",
        "/api/planner/plans?brand=habitat", "/api/nas/status",
        "/api/ggv/finance/overview", "/api/ggv/finance/invoices", "/api/ggv/finance/notas",
        "/api/ggv/finance/numbering", "/api/bzg/uma-blu/today", "/api/bzg/uma-blu/history",
        "/api/planner/publish-gate?id=1",
    ],
    "PERS-HAIKAL": [
        "/", "/content-2.0", "/content-2.0#library", "/content-2.0#upload", "/my-work",
        "/ggv-ops-pack", "/ggv/finance", "/wolf", "/amg/finance", "/bzg/uma-blu",
        "/habitat-operator", "/finish-war-room", "/hr-hiring-onboarding",
        "/api/staff/home", "/api/wolf/shell-whoami", "/api/me/capabilities",
        "/api/content/brand-registry", "/api/assets?brand=atrium&page=1&limit=1",
        "/api/planner/plans?brand=habitat", "/api/planner/dashboard?brand=habitat",
        "/api/nas/status", "/api/upload/recent?brand=habitat&data_lane=operational",
    ],
    "PERS-MISA": ["/", "/content-2.0", "/my-work", "/amg-ops-pack", "/wolf", "/ggv/finance", "/api/staff/home"],
    "PERS-ZARAH": ["/", "/content-2.0", "/my-work", "/api/staff/home"],
    "PERS-FRAIL": ["/", "/content-2.0", "/my-work", "/api/staff/home"],
    "PERS-YUDI": [
        "/", "/content-2.0", "/content-2.0#library", "/my-work",
        "/ggv/finance", "/wolf", "/amg/finance", "/bzg/uma-blu", "/habitat-operator",
        "/api/staff/home", "/api/assets?brand=atrium&page=1&limit=1",
        "/api/planner/plans?brand=habitat", "/api/me/capabilities",
    ],
    "PERS-GERY": ["/", "/content-2.0", "/my-work"],
    "PERS-ALAM": ["/", "/content-2.0", "/my-work"],
    "PERS-TJ": ["/", "/content-2.0", "/my-work"],
    "PERS-NATA": ["/", "/content-2.0", "/my-work"],
    "PERS-RAPP": ["/", "/content-2.0", "/my-work"],
    "PERS-AMANDA": [
        "/", "/content-2.0", "/my-work", "/ggv-ops-pack",
        "/ggv/finance", "/ggv/finance/invoices", "/ggv/finance/notas",
        "/ggv/finance/vendors", "/ggv/finance/customers", "/ggv/finance/history", "/ggv/finance/reports",
        "/wolf", "/amg/finance", "/bzg/uma-blu",
        "/api/staff/home", "/api/ggv/finance/overview", "/api/ggv/finance/invoices",
        "/api/ggv/finance/notas", "/api/ggv/finance/vendors", "/api/ggv/finance/customers",
        "/api/ggv/finance/numbering", "/api/ggv/finance/history", "/api/wolf/shell-whoami",
    ],
    "PERS-ZAYEN": [
        "/", "/amg/finance", "/amg/finance/lite", "/amg/finance/ledger",
        "/my-work", "/ggv/finance", "/wolf", "/content-2.0", "/bzg/uma-blu", "/bzg",
        "/api/staff/home", "/api/amg/finance", "/amg/finance/api/dashboard",
        "/amg/finance/api/journals", "/amg/finance/api/accounts",
        "/amg/finance/api/ledger", "/amg/finance/api/reports/financial-statements",
    ],
    "PERS-DEVI": [
        "/", "/bzg/uma-blu", "/bzg/uma-blu/bills", "/bzg/uma-blu/issues",
        "/bzg/uma-blu/petty", "/bzg/uma-blu/evidence", "/bzg/uma-blu/exceptions",
        "/uma-blu-close", "/bzg", "/my-work", "/content-2.0", "/ggv/finance", "/wolf", "/amg/finance",
        "/api/staff/home", "/api/bzg/uma-blu/today", "/api/bzg/uma-blu/history",
        "/api/wolf/shell-whoami",
    ],
}

EXPECT_DENY = {
    ("PERS-HAIKAL", "/ggv/finance"),
    ("PERS-HAIKAL", "/wolf"),
    ("PERS-HAIKAL", "/amg/finance"),
    ("PERS-HAIKAL", "/bzg/uma-blu"),
    ("PERS-HAIKAL", "/finish-war-room"),
    ("PERS-HAIKAL", "/hr-hiring-onboarding"),
    ("PERS-MISA", "/wolf"),
    ("PERS-MISA", "/ggv/finance"),
    ("PERS-YUDI", "/ggv/finance"),
    ("PERS-YUDI", "/wolf"),
    ("PERS-YUDI", "/amg/finance"),
    ("PERS-YUDI", "/bzg/uma-blu"),
    ("PERS-AMANDA", "/wolf"),
    ("PERS-AMANDA", "/amg/finance"),
    ("PERS-AMANDA", "/bzg/uma-blu"),
    ("PERS-ZAYEN", "/ggv/finance"),
    ("PERS-ZAYEN", "/wolf"),
    ("PERS-ZAYEN", "/content-2.0"),
    ("PERS-ZAYEN", "/bzg/uma-blu"),
    ("PERS-ZAYEN", "/bzg"),
    ("PERS-DEVI", "/content-2.0"),
    ("PERS-DEVI", "/ggv/finance"),
    ("PERS-DEVI", "/wolf"),
    ("PERS-DEVI", "/amg/finance"),
}

VACANT = (
    {"role": "ROLE-BZG-CLOSER", "label": "Venue Closing Operator", "position": "POS-BZG-CLOSER-UMA-1", "page": "/uma-blu-close"},
    {"role": "ROLE-BZG-HFB", "label": "Head of F&B", "position": "POS-BZG-HFB-UMA-1", "page": "/bzg/uma-blu"},
    {"role": "ROLE-CONTENT-CREW", "label": "Content Crew", "position": "POS-CONTENT-CREW-1", "page": "/content-2.0"},
    {"role": "ROLE-GGV-EDIT", "label": "Video Editor", "position": "POS-VIDEO-EDITOR-1", "page": "/content-2.0"},
    {"role": "ROLE-GGV-EXTERNAL-ACCOUNTANT", "label": "GGV external accountant", "position": "POS-GGV-EXT-ACCT", "page": "/ggv/finance"},
    {"role": "ROLE-AMG-GM", "label": "General Manager", "position": "POS-AMG-DAY-OPERATOR-FIXTURE", "page": "/amg-ops-pack"},
)

GRAMMARS = (
    ("BZG", "PERS-MATT"),
    ("UMA", "PERS-DEVI"),
    ("GGV", "PERS-AMANDA"),
    ("AMG", "PERS-MATT"),
    ("INTEL", "PERS-MATT"),
    ("SYSTEM", "PERS-MATT"),
)

POST_ACTIONS = (
    {"seat_id": "PERS-HAIKAL", "page": "/content-2.0#upload", "control": "Smart Upload", "handler": "POST /api/upload/smart", "where": "serve_beta.py upload dispatch", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-YUDI", "page": "/content-2.0#upload", "control": "Smart Upload", "handler": "POST /api/upload/smart", "where": "serve_beta.py upload dispatch", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-HAIKAL", "page": "/content-2.0#library", "control": "Download (ZIP)", "handler": "POST /api/assets/zip", "where": "dashboards/content-2.0.html", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-HAIKAL", "page": "/content-2.0#plan", "control": "Approve Plan", "handler": "POST /api/planner/plans/:id/approve", "where": "dashboards/content-2.0.html", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-YUDI", "page": "/content-2.0#plan", "control": "Approve Plan", "handler": "hidden unless content.plan.approve", "where": "staff_access.CREATOR_DENIED", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-AMANDA", "page": "/ggv/finance/invoices", "control": "+ New Invoice / issue", "handler": "POST /api/ggv/finance/invoices and /issue", "where": "ggv_finance_invoice.py", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-AMANDA", "page": "/ggv/finance/invoices", "control": "Open PDF", "handler": "GET /api/ggv/finance/invoices/:id/pdf", "where": "ggv_finance_invoice.py", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-ZAYEN", "page": "/amg/finance", "control": "Save journal draft", "handler": "POST /amg/finance/api/journals", "where": "atrium sidecar, not submitted", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-ZAYEN", "page": "/amg/finance", "control": "Approve or post journal", "handler": "POST approve/post refused", "where": "ATRIUM-FINANCE-FULL-RESULT.md", "classification": "WORKING BUT NOT COMMISSIONED"},
    {"seat_id": "PERS-DEVI", "page": "/bzg/uma-blu/bills", "control": "Purchase request actions", "handler": "Uma PR routes under /api/bzg/uma-blu/prs", "where": "uma console, example rows only", "classification": "REAL DATA NOT WIRED"},
)

SHOTS_PLAN = (
    ("opsaudit-owner-wolf-desktop.png", "PERS-MATT", "/wolf", 1440, 900, "Owner"),
    ("opsaudit-owner-wolf-phone.png", "PERS-MATT", "/wolf", 390, 844, "Owner"),
    ("opsaudit-haikal-plan-desktop.png", "PERS-HAIKAL", "/content-2.0#plan", 1440, 900, "Content Plan"),
    ("opsaudit-haikal-plan-phone.png", "PERS-HAIKAL", "/content-2.0#plan", 390, 844, "Content Plan"),
    ("opsaudit-haikal-library-desktop.png", "PERS-HAIKAL", "/content-2.0?brand=atrium#library", 1440, 900, "Library"),
    ("opsaudit-haikal-library-phone.png", "PERS-HAIKAL", "/content-2.0?brand=atrium#library", 390, 844, "Library"),
    ("opsaudit-haikal-upload-phone.png", "PERS-HAIKAL", "/content-2.0#upload", 390, 844, "Upload"),
    ("opsaudit-haikal-mywork-desktop.png", "PERS-HAIKAL", "/my-work", 1440, 900, "My Work"),
    ("opsaudit-yudi-mywork-phone.png", "PERS-YUDI", "/my-work", 390, 844, "My Work"),
    ("opsaudit-amanda-content-desktop.png", "PERS-AMANDA", "/content-2.0", 1440, 900, "Content"),
    ("opsaudit-amanda-ggv-desktop.png", "PERS-AMANDA", "/ggv/finance", 1440, 900, "GGV"),
    ("opsaudit-amanda-ggv-phone.png", "PERS-AMANDA", "/ggv/finance", 390, 844, "GGV"),
    ("opsaudit-amanda-invoices-desktop.png", "PERS-AMANDA", "/ggv/finance/invoices", 1440, 900, "Invoices"),
    ("opsaudit-amanda-invoices-phone.png", "PERS-AMANDA", "/ggv/finance/invoices", 390, 844, "Invoices"),
    ("opsaudit-zayen-atrium-desktop.png", "PERS-ZAYEN", "/amg/finance", 1440, 900, "Atrium"),
    ("opsaudit-zayen-atrium-phone.png", "PERS-ZAYEN", "/amg/finance", 390, 844, "Atrium"),
    ("opsaudit-zayen-ledger-desktop.png", "PERS-ZAYEN", "/amg/finance#ledger", 1440, 900, "Ledger"),
    ("opsaudit-zayen-lite-desktop.png", "PERS-ZAYEN", "/amg/finance/lite", 1440, 900, "Atrium"),
    ("opsaudit-zayen-denied-phone.png", "PERS-ZAYEN", "/ggv/finance", 390, 844, "Atrium"),
    ("opsaudit-devi-uma-desktop.png", "PERS-DEVI", "/bzg/uma-blu", 1440, 900, "Uma"),
    ("opsaudit-devi-uma-phone.png", "PERS-DEVI", "/bzg/uma-blu", 390, 844, "Uma"),
    ("opsaudit-devi-bills-desktop.png", "PERS-DEVI", "/bzg/uma-blu/bills", 1440, 900, "Bills"),
    ("opsaudit-devi-close-phone.png", "PERS-DEVI", "/uma-blu-close", 390, 844, "Close"),
    ("opsaudit-owner-bzg-desktop.png", "PERS-MATT", "/bzg", 1440, 900, "Blu"),
    ("opsaudit-owner-warroom-desktop.png", "PERS-MATT", "/finish-war-room", 1440, 900, "war room"),
    ("opsaudit-owner-hr-desktop.png", "PERS-MATT", "/hr-hiring-onboarding", 1440, 900, "Hiring"),
    ("opsaudit-owner-progress-phone.png", "PERS-MATT", "/progress", 390, 844, "Progress"),
    ("opsaudit-misa-content-desktop.png", "PERS-MISA", "/content-2.0", 1440, 900, "Content"),
)


def snippet(body: bytes, ctype: str) -> str:
    if "image/" in ctype or "pdf" in ctype or "octet-stream" in ctype:
        return f"<{ctype} {len(body)} bytes>"
    text = body[:700].decode("utf-8", "replace")
    text = re.sub(r"(?i)(password|secret|token|bearer|api[_-]?key)\s*[:=]\s*\S+", r"\1=[redacted]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:240]


def classify(person_id: str, path: str, status: int, ctype: str, text: str, location: str) -> str:
    base = path.split("?")[0].split("#")[0]
    expect = (person_id, base) in EXPECT_DENY or (person_id, path) in EXPECT_DENY
    human = not base.startswith("/api/")
    if status in {301, 302, 303, 307, 308}:
        if person_id == "PERS-AMANDA" and base == "/" and location == "/content-2.0":
            return "WORKING BUT NOT COMMISSIONED"
        if person_id == "PERS-ZAYEN" and base == "/" and location == "/amg/finance":
            return "WORKING BUT NOT COMMISSIONED"
        return "WORKING BUT NOT COMMISSIONED"
    if status == 404:
        return "BROKEN"
    if status >= 500:
        return "BROKEN"
    if status == 403:
        if expect and human and ("json" in ctype or text.lstrip().startswith("{")):
            return "BROKEN"
        if expect:
            return "WORKING BUT NOT COMMISSIONED"
        return "BROKEN"
    if status != 200:
        return "BROKEN"
    if human and ("json" in ctype or (text.lstrip().startswith("{") and "html" not in ctype)):
        return "BROKEN"
    low = text.lower()
    if "framework empty" in low or "stays specified" in low or "not a live hiring" in low:
        return "NOT YET BUILT"
    if "pr-uma-example" in low or "example requester" in low:
        return "REAL DATA NOT WIRED"
    if base in {"/my-work"} or base == "/api/staff/home":
        return "REAL DATA NOT WIRED"
    if base in {"/ggv/finance/history"} or base == "/api/ggv/finance/history":
        return "REAL DATA NOT WIRED"
    if base in {"/ggv/finance", "/ggv/finance/invoices", "/ggv/finance/notas", "/ggv/finance/vendors", "/ggv/finance/customers", "/ggv/finance/reports"}:
        return "WORKING BUT NOT COMMISSIONED"
    if base.startswith("/api/ggv/finance"):
        if base.endswith("/invoices") or base.endswith("/notas") or base.endswith("/vendors") or base.endswith("/customers"):
            return "REAL DATA NOT WIRED"
        if base.endswith("/numbering"):
            return "WORKING BUT NOT COMMISSIONED"
        return "WORKING BUT NOT COMMISSIONED"
    if "uma-blu" in base or base == "/uma-blu-close" or base.startswith("/api/bzg/uma-blu"):
        return "REAL DATA NOT WIRED"
    if base in {"/hr-training-competency", "/hr-payroll-inputs", "/hr-retention-signals", "/hr-hiring-onboarding"}:
        return "NOT YET BUILT"
    if base == "/habitat-operator" or "publish-gate" in base:
        return "EXISTING IMPLEMENTATION NOT MOUNTED"
    if base == "/lead-spine":
        return "WORKING BUT NOT COMMISSIONED"
    if base in {"/content-2.0"} or base.startswith("/api/assets") or base.startswith("/api/planner") or base.startswith("/api/nas") or base.startswith("/api/content"):
        return "WORKING BUT NOT COMMISSIONED"
    if base.startswith("/amg/finance"):
        if base == "/amg/finance/lite":
            return "WORKING BUT NOT COMMISSIONED"
        return "WORKING BUT NOT COMMISSIONED"
    if base in {"/wolf", "/owner-empire-pack", "/progress", "/finish-war-room", "/bzg", "/ggv-ops-pack", "/amg-ops-pack", "/intel-ops-pack", "/integration-health", "/sale-evidence-pack", "/staff-ops-routing"}:
        return "WORKING BUT NOT COMMISSIONED"
    return "WORKING BUT NOT COMMISSIONED"


def http_call(port: int, path: str, email: str | None) -> tuple[int, str, str, bytes]:
    headers = {"Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
    if email:
        headers["X-Wolf-Subject"] = email
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=45)
    try:
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        body = resp.read(250_000)
        return resp.status, resp.getheader("Location") or "", resp.getheader("Content-Type") or "", body
    finally:
        conn.close()


def live_unsigned(path: str) -> int:
    conn = http.client.HTTPConnection("127.0.0.1", 8788, timeout=8)
    try:
        conn.request("GET", path, headers={"Accept": "text/html"})
        resp = conn.getresponse()
        resp.read(200)
        return resp.status
    except Exception:
        return 0
    finally:
        conn.close()


def find_handler():
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            return obj
    raise RuntimeError("BetaHandler missing")


def seat_by_id(person_id: str) -> dict:
    return next(s for s in SEATS if s["person_id"] == person_id)


def grammar_rows() -> list[dict]:
    from core import wolf_shell as shell

    out = []
    mapping = {
        "BZG": shell.BZG_GRAMMAR,
        "UMA": shell.UMA_GRAMMAR,
        "GGV": shell.GGV_GRAMMAR,
        "AMG": shell.AMG_GRAMMAR,
        "INTEL": shell.INTEL_GRAMMAR,
        "SYSTEM": shell.SYSTEM_GRAMMAR,
    }
    owners = dict(GRAMMARS)
    for name, items in mapping.items():
        seat = seat_by_id(owners[name])
        for item in items:
            href = item.get("href")
            state = item.get("state")
            if href:
                continue
            classification = "NOT YET BUILT"
            if name == "AMG" and item.get("key") == "finance":
                classification = "EXISTING IMPLEMENTATION NOT MOUNTED"
            out.append({
                "seat": seat["seat"],
                "person": seat["person"],
                "person_id": seat["person_id"],
                "role": seat["role"],
                "device": "desktop",
                "method": "GET",
                "route": f"{name} grammar / {item.get('label')}",
                "path": None,
                "http_status": None,
                "content_type": "",
                "location": "",
                "classification": classification,
                "evidence": f"wolf_shell {name}_GRAMMAR key={item.get('key')} href=null state={state}",
                "kind": "nav_slot",
            })
    return out


def button_rows() -> list[dict]:
    pages = {
        "/content-2.0": ROOT / "dashboards/content-2.0.html",
        "/ggv/finance": ROOT / "dashboards/ggv-finance.html",
        "/bzg/uma-blu": ROOT / "dashboards/bzg-uma-blu.html",
        "/my-work": ROOT / "dashboards/my-work.html",
    }
    owners = {
        "/content-2.0": ("PERS-HAIKAL", "PERS-YUDI"),
        "/ggv/finance": ("PERS-AMANDA",),
        "/bzg/uma-blu": ("PERS-DEVI",),
        "/my-work": ("PERS-HAIKAL", "PERS-YUDI", "PERS-ZAYEN", "PERS-DEVI"),
    }
    rows = []
    for path, file in pages.items():
        html = file.read_text(encoding="utf-8", errors="replace")
        labels = []
        for raw in re.findall(r"<button\b([^>]*)>(.*?)</button>", html, flags=re.I | re.S):
            attrs, inner = raw
            label = re.sub(r"<[^>]+>", "", inner)
            label = re.sub(r"\s+", " ", label).strip()
            if not label or len(label) > 80:
                continue
            if label in labels:
                continue
            labels.append(label)
            view = ""
            m = re.search(r'data-view="([^"]+)"', attrs)
            t = re.search(r'data-tab="([^"]+)"', attrs)
            if m:
                view = "#" + m.group(1)
            if t:
                view = " tab " + t.group(1)
            for pid in owners[path]:
                seat = seat_by_id(pid)
                hidden = "hidden" in attrs and "Approve" in label and pid == "PERS-YUDI"
                classification = "WORKING BUT NOT COMMISSIONED"
                if path == "/bzg/uma-blu":
                    classification = "REAL DATA NOT WIRED"
                if path == "/my-work":
                    classification = "REAL DATA NOT WIRED"
                if hidden:
                    classification = "WORKING BUT NOT COMMISSIONED"
                for device in ("desktop", "phone"):
                    rows.append({
                        "seat": seat["seat"],
                        "person": seat["person"],
                        "person_id": pid,
                        "role": seat["role"],
                        "device": device,
                        "method": "GET",
                        "route": f"{path}{view} button {label}",
                        "path": path,
                        "http_status": None,
                        "content_type": "text/html",
                        "location": "",
                        "classification": classification,
                        "evidence": "Button is in the page HTML. Not clicked. No POST submitted."
                        + (" Hidden from Content Creator." if hidden else ""),
                        "kind": "button",
                    })
        for href, inner in re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S):
            if href.startswith(("#", "mailto:", "javascript:")) or href.startswith("/assets") or href.startswith("/wolf-tokens"):
                continue
            label = re.sub(r"<[^>]+>", "", inner)
            label = re.sub(r"\s+", " ", label).strip() or href
            if len(label) > 80:
                continue
            for pid in owners[path]:
                seat = seat_by_id(pid)
                rows.append({
                    "seat": seat["seat"],
                    "person": seat["person"],
                    "person_id": pid,
                    "role": seat["role"],
                    "device": "desktop",
                    "method": "GET",
                    "route": f"link {label}",
                    "path": href.split("?")[0],
                    "http_status": None,
                    "content_type": "",
                    "location": "",
                    "classification": "WORKING BUT NOT COMMISSIONED",
                    "evidence": f"Link on {path} points at {href}. Status filled when that path was probed.",
                    "kind": "link",
                })
    return rows


def _ws_connect(host: str, port: int, path: str) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return sock


def _ws_send(sock: socket.socket, text: str) -> None:
    data = text.encode()
    mask = os.urandom(4)
    length = len(data)
    header = bytearray([0x81])
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", length))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack(">Q", length))
    header.extend(mask)
    masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
    sock.sendall(bytes(header) + masked)


def _ws_recv(sock: socket.socket) -> str:
    def read(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed")
            buf += chunk
        return buf

    while True:
        head = read(2)
        opcode = head[0] & 0x0F
        length = head[1] & 0x7F
        if length == 126:
            length = struct.unpack(">H", read(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", read(8))[0]
        if head[1] & 0x80:
            mask = read(4)
            payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(read(length)))
        else:
            payload = read(length)
        if opcode == 8:
            raise ConnectionError("websocket closed")
        if opcode == 9:
            continue
        if opcode in (0, 1):
            return payload.decode()


def capture(proxy_port: int, email: str, path: str, width: int, height: int, dest: Path, marker: str) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subject["email"] = email
    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.Popen(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--disable-extensions",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                f"--window-size={width},{height}",
                "--force-device-scale-factor=1",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            deadline = time.time() + 15
            while time.time() < deadline and not port_file.is_file():
                time.sleep(0.1)
            dbg_port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
            with urlopen(f"http://127.0.0.1:{dbg_port}/json/list", timeout=5) as resp:
                tabs = json.loads(resp.read().decode())
            page = next(tab for tab in tabs if tab.get("type") == "page")
            ws_path = page["webSocketDebuggerUrl"].split("/", 3)[-1]
            sock = _ws_connect("127.0.0.1", dbg_port, "/" + ws_path)
            sock.settimeout(40)
            seq = 0

            def cdp(method: str, params: dict | None = None) -> dict:
                nonlocal seq
                seq += 1
                ident = seq
                _ws_send(sock, json.dumps({"id": ident, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident:
                        return msg

            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width <= 430},
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{proxy_port}{path}"})
            text = ""
            deadline = time.time() + 25
            while time.time() < deadline:
                got = cdp("Runtime.evaluate", {"expression": "document.body ? document.body.innerText.slice(0, 500) : ''", "returnByValue": True})
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                if marker.lower() in text.lower():
                    break
                time.sleep(0.35)
            metrics = cdp(
                "Runtime.evaluate",
                {
                    "expression": "JSON.stringify({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})",
                    "returnByValue": True,
                },
            )
            raw = str(((metrics.get("result") or {}).get("result") or {}).get("value") or "{}")
            try:
                size = json.loads(raw)
            except json.JSONDecodeError:
                size = {}
            cdp("Page.stopLoading")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            sock.close()
            scroll = int(size.get("scroll") or 0)
            client = int(size.get("client") or 0)
            return {
                "file": str(dest.relative_to(ROOT)),
                "bytes": dest.stat().st_size,
                "marker_seen": marker.lower() in text.lower(),
                "overflow": bool(client and scroll > client + 8),
                "scroll": scroll,
                "client": client,
                "head": re.sub(r"\s+", " ", text)[:160],
            }
        finally:
            proc.kill()
            proc.wait(timeout=5)


subject = {"email": ""}


def main() -> int:
    copy = canonical_guard.isolate_runtime_catalog()
    handler = find_handler()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    rows: list[dict] = []
    facts: dict[tuple, dict] = {}
    try:
        seen_people: set[str] = set()
        for seat in SEATS:
            if seat["person_id"] in seen_people:
                continue
            seen_people.add(seat["person_id"])
            for path in ROUTES[seat["person_id"]]:
                status, loc, ctype, body = http_call(port, path.split("#")[0], seat["email"])
                text = snippet(body, ctype)
                kind = "api" if path.split("?")[0].startswith("/api/") or "/api/" in path else "page"
                classification = classify(seat["person_id"], path, status, ctype, text, loc)
                base_row = {
                    "seat": seat["seat"],
                    "person": seat["person"],
                    "person_id": seat["person_id"],
                    "role": seat["role"],
                    "method": "GET",
                    "route": path,
                    "path": path.split("#")[0],
                    "http_status": status,
                    "content_type": ctype.split(";")[0],
                    "location": loc,
                    "classification": classification,
                    "evidence": text,
                    "kind": kind,
                }
                facts[(seat["person_id"], path.split("#")[0])] = base_row
                for device in ("desktop", "phone"):
                    item = dict(base_row)
                    item["device"] = device
                    rows.append(item)
                print(f"{seat['person_id']} {status} {path} {classification}", flush=True)
        unsigned = []
        for path in ("/api/health", "/content-2.0", "/amg/finance", "/ggv/finance", "/wolf", "/bzg/uma-blu"):
            code = live_unsigned(path)
            unsigned.append({"path": path, "http_status": code})
            rows.append({
                "seat": "unsigned",
                "person": None,
                "person_id": None,
                "role": None,
                "device": "desktop",
                "method": "GET",
                "route": path,
                "path": path,
                "http_status": code,
                "content_type": "",
                "location": "",
                "classification": "WORKING BUT NOT COMMISSIONED" if code in {200, 403} else "BROKEN",
                "evidence": f"Live :8788 unsigned GET. Auth mode of that process was not changed. status={code}",
                "kind": "live_unsigned",
            })
        for item in VACANT:
            rows.append({
                "seat": item["label"],
                "person": None,
                "person_id": None,
                "role": item["role"],
                "device": "desktop",
                "method": "GET",
                "route": item["page"],
                "path": item["page"],
                "http_status": None,
                "content_type": "",
                "location": "",
                "classification": "NOT YET BUILT",
                "evidence": f"Vacant position {item['position']}. No person invented. Page exists for other seats.",
                "kind": "vacant",
            })
        rows.extend(grammar_rows())
        link_rows = button_rows()
        for link in link_rows:
            if link["kind"] == "link":
                found = facts.get((link["person_id"], link["path"]))
                if found:
                    link["http_status"] = found["http_status"]
                    link["classification"] = found["classification"]
                    link["content_type"] = found["content_type"]
                    link["location"] = found["location"]
                    link["evidence"] = found["evidence"]
            rows.append(link)
        for action in POST_ACTIONS:
            seat = seat_by_id(action["seat_id"])
            for device in ("desktop", "phone"):
                rows.append({
                    "seat": seat["seat"],
                    "person": seat["person"],
                    "person_id": seat["person_id"],
                    "role": seat["role"],
                    "device": device,
                    "method": "POST",
                    "route": action["control"],
                    "path": action["page"],
                    "http_status": None,
                    "content_type": "",
                    "location": "",
                    "classification": action["classification"],
                    "evidence": f"Handler {action['handler']} in {action['where']}. Not submitted.",
                    "kind": "action",
                })
        shots = []
        if CHROME.is_file():

            class Proxy(BaseHTTPRequestHandler):
                protocol_version = "HTTP/1.1"

                def log_message(self, *_args):  # noqa: ANN002
                    return

                def do_GET(self):  # noqa: N802
                    req = Request(
                        f"http://127.0.0.1:{port}{self.path}",
                        headers={"X-Wolf-Subject": subject["email"], "Accept": self.headers.get("Accept") or "*/*"},
                        method="GET",
                    )
                    try:
                        with urlopen(req, timeout=60) as resp:
                            payload = resp.read()
                            code = resp.status
                            ctype = resp.headers.get("Content-Type") or "application/octet-stream"
                    except HTTPError as exc:
                        payload = exc.read()
                        code = exc.code
                        ctype = exc.headers.get("Content-Type") if exc.headers else "text/plain"
                    except (URLError, TimeoutError, ConnectionError):
                        payload = b""
                        code = 502
                        ctype = "text/plain"
                    self.send_response(code)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

                def do_POST(self):  # noqa: N802
                    self.send_response(405)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

                do_PUT = do_POST
                do_PATCH = do_POST
                do_DELETE = do_POST

            proxy = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
            proxy_port = proxy.server_address[1]
            threading.Thread(target=proxy.serve_forever, daemon=True).start()
            for name, pid, path, width, height, marker in SHOTS_PLAN:
                seat = seat_by_id(pid)
                dest = SHOTS / name
                try:
                    meta = capture(proxy_port, seat["email"], path, width, height, dest, marker)
                except Exception as exc:  # noqa: BLE001
                    meta = {"file": str(dest.relative_to(ROOT)), "error": str(exc)[:180], "marker_seen": False, "overflow": None}
                meta["seat"] = seat["person"]
                meta["path"] = path
                meta["width"] = width
                shots.append(meta)
                print(f"SHOT {name} marker={meta.get('marker_seen')} overflow={meta.get('overflow')}", flush=True)
            proxy.shutdown()
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated": "2026-09-28",
            "probe": "ephemeral development_assertion handler",
            "live_8788_auth_unchanged": True,
            "catalog_copy": str(copy),
            "unsigned_live": unsigned,
            "shots": shots,
            "rows": rows,
        }
        (OUT_DIR / "probe-raw.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"ROWS {len(rows)} SHOTS {len(shots)}", flush=True)
    finally:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
