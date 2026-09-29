#!/usr/bin/env python3
"""GGV Finance — bounded nota / vendor intake (Beta).

Serves Owner directive 2026-09-24 (RULE + SPEC GGV Finance Mobile Nota).
Run BF-ggv-finance-mobile-nota-20260924.

Zayen boundary
--------------
This module is bounded accounts-payable evidence inside Wolf:
nota intake, one Vendor Master for GGV, review workflow, audit.
It is not a ledger. It does not reconcile cash, profit, or aged payables.
It does not execute payment, write bank accounts, or verify bank details.
Full finance stays reserved for Zayen. Records here carry a Wolf id, vendor
id, source file, creator, time, confirmed amount/date, workflow state,
history, and an audit event so a later reconcile can attach them.
BANK DETAILS OBSERVED is not BANK DETAILS VERIFIED.
NOTA ENTERED is not APPROVED, not PAID, and not PAYMENT VERIFIED.

Telegram
--------
Wolf operates without Telegram. This module does not sync either way,
does not create Telegram vendor or nota rows, and does not mark Telegram
retired. Retirement waits until both humans commission.

Permissions are evaluated only through Person → Role → Assignment → Scope
→ Permission. Names are not an allow-list.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import audit as audit_log
from core import evidence as _evidence
from core import nas_library as _nas
from core import rbac as _rbac

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
# Local blobs are not canonical. Migration may read this folder, then the
# verified copy lives on the media library. Do not write new evidence here.
LEGACY_BLOB_DIR = BETA_ROOT / "state" / "ggv-finance-nota" / "blobs"
ENTITY_GGV = "ENT-GGV"
BOUND = "beta-ggv-finance-nota"
STORAGE_ROOT_ID = "01-Media-Library"
FINANCE_REL = Path("Finance") / "GGV" / "Notas"
BACKUP_STATES = frozenset({"BACKED_UP", "PENDING", "UNKNOWN", "FAILED"})
# B2 backup for finance paths is not proven. Nothing in this pack may set BACKED_UP.
B2_FINANCE_PROVEN = False
ROLE_EXTERNAL_ACCOUNTANT = "ROLE-GGV-EXTERNAL-ACCOUNTANT"
SCOPE_GGV_FINANCE = "SCOPE-GGV-FINANCE"
POSITION_EXTERNAL_ACCOUNTANT = "POS-GGV-EXT-ACCT"
_MEDIA_ROOT: Path | None = None
_LEGACY_DIR: Path | None = None

# Operating grants. Roles that already cover GGV for the authorised seats.
# ROLE-MATT = owner assignment. ROLE-CONTENT-MGMT = GGV content lead seat.
# Not granted to editor, crew, venue, or client roles.
OPERATING_ROLES: tuple[str, ...] = ("ROLE-MATT", "ROLE-CONTENT-MGMT")

OPERATING_PERMS: tuple[tuple[str, str, str, str], ...] = (
    ("PERM-FIN-NOTA-READ", "finance.nota.read", "finance.nota", "read"),
    ("PERM-FIN-NOTA-CREATE", "finance.nota.create", "finance.nota", "create"),
    ("PERM-FIN-NOTA-EDIT", "finance.nota.edit", "finance.nota", "edit"),
    ("PERM-VENDOR-READ", "vendor.read", "vendor", "read"),
    ("PERM-VENDOR-CREATE", "vendor.create", "vendor", "create"),
    ("PERM-VENDOR-EDIT", "vendor.edit", "vendor", "edit"),
    # Pack gate for attaching nota files. The evidence spine still checks
    # evidence.record.submit when a row is written there. They are separate codes.
    ("PERM-EVIDENCE-CREATE", "evidence.create", "evidence", "create"),
    ("PERM-FIN-EVIDENCE-EXPORT", "finance.evidence.export", "finance.evidence", "export"),
)

# Seeded on the role. No person is assigned by this pack.
ACCOUNTANT_PERMS: tuple[tuple[str, str, str, str], ...] = (
    ("PERM-FIN-NOTA-READ", "finance.nota.read", "finance.nota", "read"),
    ("PERM-VENDOR-READ", "vendor.read", "vendor", "read"),
    ("PERM-FIN-NOTA-REVIEW", "finance.nota.review", "finance.nota", "review"),
    ("PERM-FIN-EVIDENCE-EXPORT", "finance.evidence.export", "finance.evidence", "export"),
)

# Exist so they can be tested as ungranted. This pack never ALLOWs them.
HELD_BACK_PERMS: tuple[tuple[str, str, str, str], ...] = (
    ("PERM-PAYMENT-APPROVE", "payment.approve", "payment", "approve"),
    ("PERM-PAYMENT-EXECUTE", "payment.execute", "payment", "execute"),
    ("PERM-VENDOR-BANK-CHANGE", "vendor.bank.change", "vendor.bank", "change"),
    ("PERM-FIN-POLICY-ADMIN", "finance.policy.admin", "finance.policy", "admin"),
)

EVIDENCE_CREATE_MAP = (
    "evidence.create is the operating permission checked by GGV Finance before "
    "a nota file is kept. The evidence spine still requires evidence.record.submit "
    "to write core_evidence_records. The codes are not aliases and not a payment right."
)

ZAYEN_NOTE = (
    "Payment and full books live with Finance reconciliation later — "
    "here you capture notas and vendors."
)

STATE_LABEL = {
    "needs_review": "Needs review",
    "ready": "Ready",
    "waiting_approval": "Waiting approval",
    "approved": "Approved",
    "paid_claimed": "Paid — claimed",
    "payment_verified": "Payment verified",
}
# This pack may write only the first three. The rest are reserved and refused.
PACK_WRITE_STATES = frozenset({"needs_review", "ready", "waiting_approval"})
TERMINAL_MONEY_STATES = frozenset({"approved", "paid_claimed", "payment_verified"})

STAGE_LABEL = {
    "uploading": "Uploading",
    "reading": "Reading document",
    "checking_vendor": "Checking vendor",
    "ready_for_review": "Ready for review",
    "saved": "Saved",
    "failed": "Failed",
}

PAGE_PATHS = frozenset(
    {
        "/ggv/finance",
        "/ggv/finance/invoices",
        "/ggv/finance/notas",
        "/ggv/finance/vendors",
        "/ggv/finance/customers",
        "/ggv/finance/history",
        "/ggv/finance/reports",
        "/ggv-finance",
        "/ggv-finance.html",
        "/dashboards/ggv-finance.html",
    }
)

REFUSED_SUFFIXES = frozenset(
    {
        "/pay",
        "/execute",
        "/payment",
        "/approve-payment",
        "/bank",
        "/bank-verify",
        "/ledger",
    }
)

MAX_FILES = 8
MAX_BYTES = 8_000_000
HONESTY = {
    "staff_ready": False,
    "proven": False,
    "ready": False,
    "commissioned": False,
    "telegram_retired": False,
    "telegram_sync": False,
    "money_movement": False,
    "payment_execute": False,
    "bank_write": False,
    "bank_details_verified": False,
    "nota_entered_is_not_paid": True,
    "zayen_is_ledger": False,
    "backup_proven": False,
    "b2_finance_proven": False,
    "canonical_local_blobs": False,
    "auto_zip_storage": False,
    "auto_delete": False,
    "bound": BOUND,
}

SHELL_CHROME_PATHS = frozenset(
    {
        "/api/health",
        "/api/wolf/shell-whoami",
        "/api/staff/home",
        "/my-work",
        "/my-work.html",
        "/wolf-tokens.css",
        "/assets/wolf-shell.css",
        "/assets/sidenav.js",
        "/assets/wolf-truth.css",
        "/assets/wolf-truth.js",
        "/api/dashboard-truth/stamp",
    }
)

BACKUP_LABEL = {
    "PENDING": "Pending",
    "UNKNOWN": "Unknown",
    "FAILED": "Failed",
    "BACKED_UP": "Backed up",
}


class FinanceNotaError(Exception):
    def __init__(self, message: str, *, code: str = "error", http_status: int = 400, extra: dict | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.extra = extra or {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _mint(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def _under_test() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    argv = " ".join(sys.argv).lower()
    return "unittest" in argv or "/tests/" in argv or "test_" in argv


def assert_catalog_writable(db_path: Path) -> None:
    resolved = Path(db_path).resolve()
    text = str(resolved)
    if "wolf-system" in text or "/Production" in text or text.endswith("money.sqlite"):
        raise FinanceNotaError("refusing production database", code="production_refused", http_status=500)
    from core.canonical_guard import assert_write_allowed
    assert_write_allowed(resolved)
    if resolved == LIVE_CATALOG_DB and _under_test():
        raise FinanceNotaError(
            "test mode refuses writes to the live catalog",
            code="live_write_refused",
            http_status=500,
        )


def db_connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    text = str(resolved)
    if "beta-os" not in text:
        raise FinanceNotaError("finance nota refuses a non-beta database", code="bad_db", http_status=500)
    if "wolf-system" in text or "/Production" in text:
        raise FinanceNotaError("finance nota refuses production", code="production_refused", http_status=500)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def matches(path: str) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    if trimmed.startswith("/api/ggv/finance"):
        return True
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def public_payload(data: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    out = dict(HONESTY)
    out["zayen_note"] = ZAYEN_NOTE
    out["evidence_create_map"] = EVIDENCE_CREATE_MAP
    if data:
        out.update(data)
    out.update(extra)
    out["staff_ready"] = False
    out["proven"] = False
    out["ready"] = False
    out["commissioned"] = False
    out["telegram_retired"] = False
    return out


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ggv_vendors (
          vendor_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          display_name TEXT NOT NULL,
          name_norm TEXT NOT NULL,
          category TEXT,
          contact_name TEXT,
          phone TEXT,
          phone_norm TEXT,
          email TEXT,
          email_norm TEXT,
          tax_id TEXT,
          tax_norm TEXT,
          address TEXT,
          notes TEXT,
          status TEXT NOT NULL,
          created_by_person_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ggv_vendors_norm ON ggv_vendors(entity_id, name_norm);
        CREATE TABLE IF NOT EXISTS ggv_vendor_bank_observed (
          observation_id TEXT PRIMARY KEY,
          vendor_id TEXT,
          nota_id TEXT,
          raw_text TEXT NOT NULL,
          status TEXT NOT NULL,
          created_by_person_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ggv_uploads (
          upload_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          created_by_person_id TEXT NOT NULL,
          stage TEXT NOT NULL,
          failure_stage TEXT,
          failure_message TEXT,
          proposals_json TEXT,
          vendor_matches_json TEXT,
          preserved INTEGER NOT NULL DEFAULT 1,
          nota_id TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ggv_nota_files (
          file_id TEXT PRIMARY KEY,
          upload_id TEXT,
          nota_id TEXT,
          filename TEXT,
          content_type TEXT,
          sha256 TEXT NOT NULL,
          rel_path TEXT NOT NULL,
          role TEXT NOT NULL,
          evidence_id TEXT,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ggv_nota_files_hash ON ggv_nota_files(sha256);
        CREATE TABLE IF NOT EXISTS ggv_notas (
          nota_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          vendor_id TEXT,
          invoice_no TEXT,
          nota_date TEXT,
          currency TEXT,
          amount TEXT,
          tax TEXT,
          category TEXT,
          items_json TEXT,
          notes TEXT,
          workflow_state TEXT NOT NULL,
          amount_confirmed INTEGER NOT NULL DEFAULT 0,
          date_confirmed INTEGER NOT NULL DEFAULT 0,
          vendor_confirmed INTEGER NOT NULL DEFAULT 0,
          proposals_json TEXT,
          confidence_json TEXT,
          created_by_person_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          submitted_at TEXT,
          approval_request_id TEXT,
          duplicate_of_nota_id TEXT,
          duplicate_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS ggv_nota_history (
          history_id TEXT PRIMARY KEY,
          nota_id TEXT,
          vendor_id TEXT,
          action TEXT NOT NULL,
          actor_person_id TEXT NOT NULL,
          detail_json TEXT,
          created_at TEXT NOT NULL
        );
        """
    )
    _migrate_file_columns(conn)


FILE_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("original_filename", "TEXT"),
    ("canonical_filename", "TEXT"),
    ("size_bytes", "INTEGER"),
    ("vendor_id", "TEXT"),
    ("source_provenance", "TEXT"),
    ("backup_state", "TEXT"),
    ("nas_rel_path", "TEXT"),
    ("storage_root_id", "TEXT"),
    ("upload_timestamp", "TEXT"),
)


def _migrate_file_columns(conn: sqlite3.Connection) -> None:
    have = {row[1] for row in conn.execute("PRAGMA table_info(ggv_nota_files)").fetchall()}
    for name, kind in FILE_EXTRA_COLUMNS:
        if name in have:
            continue
        conn.execute(f"ALTER TABLE ggv_nota_files ADD COLUMN {name} {kind}")


def ensure_rbac(conn: sqlite3.Connection, *, commit: bool = True) -> dict[str, Any]:
    """Idempotent permission rows. Operating ALLOW only. Held-back codes stay ungranted.

    The external accountant role is seeded with GGV Finance permissions and a
    GGV Finance scope. No person is created or assigned.
    """
    assert_catalog_writable(Path(conn.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB))
    ts = _now()
    seen: set[str] = set()
    perm_rows = []
    for row in OPERATING_PERMS + ACCOUNTANT_PERMS + HELD_BACK_PERMS:
        if row[0] in seen:
            continue
        seen.add(row[0])
        perm_rows.append(row)
    for perm_id, code, resource, action in perm_rows:
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code, status='ACTIVE', updated_at=excluded.updated_at
            """,
            (
                perm_id,
                code,
                resource,
                action,
                f"GGV finance nota pack: {code}",
                ts,
                ts,
            ),
        )
        conn.execute(
            "UPDATE org_permissions SET status='ACTIVE', updated_at=? WHERE code=?",
            (ts, code),
        )
    for role_id in OPERATING_ROLES:
        role = conn.execute(
            "SELECT role_id FROM org_roles WHERE role_id=?",
            (role_id,),
        ).fetchone()
        if not role:
            raise FinanceNotaError(f"missing role {role_id}", code="role_missing", http_status=500)
        for perm_id, code, _resource, _action in OPERATING_PERMS:
            conn.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW', updated_at=excluded.updated_at
                """,
                (role_id, perm_id, ts, ts),
            )
    _seed_accountant_role(conn, ts)
    if commit:
        conn.commit()
    return {
        "ok": True,
        "operating_roles": list(OPERATING_ROLES),
        "accountant_role": ROLE_EXTERNAL_ACCOUNTANT,
        "accountant_person_seeded": False,
        "held_back_ungranted": True,
    }


def _seed_accountant_role(conn: sqlite3.Connection, ts: str) -> None:
    """Role, position, and GGV Finance scope only. No person and no assignment."""
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'GGV external accountant', NULL, 'EXTERNAL', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          display_name=excluded.display_name, status='ACTIVE', updated_at=excluded.updated_at
        """,
        (ROLE_EXTERNAL_ACCOUNTANT, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, NULL, NULL, 'GGV external accountant', 'ACTIVE', 1, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          role_id=excluded.role_id, entity_id=excluded.entity_id, status='ACTIVE', updated_at=excluded.updated_at
        """,
        (POSITION_EXTERNAL_ACCOUNTANT, ROLE_EXTERNAL_ACCOUNTANT, ENTITY_GGV, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, 'structural', 'GGV Finance only', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET
          display_name=excluded.display_name, status='ACTIVE', updated_at=excluded.updated_at
        """,
        (SCOPE_GGV_FINANCE, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'entity', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (SCOPE_GGV_FINANCE, ENTITY_GGV, ts),
    )
    for perm_id, _code, _resource, _action in ACCOUNTANT_PERMS:
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW', updated_at=excluded.updated_at
            """,
            (ROLE_EXTERNAL_ACCOUNTANT, perm_id, ts, ts),
        )
    # Held-back and operating-only codes stay off this role.
    denied = [row[0] for row in HELD_BACK_PERMS + OPERATING_PERMS if row[0] not in {p[0] for p in ACCOUNTANT_PERMS}]
    if denied:
        conn.execute(
            f"""
            DELETE FROM org_role_permissions
            WHERE role_id=? AND permission_id IN ({",".join("?" for _ in denied)})
            """,
            (ROLE_EXTERNAL_ACCOUNTANT, *denied),
        )


def _target() -> dict[str, str]:
    return {"entity_id": ENTITY_GGV}


def person_can(person_id: str | None, code: str, conn: sqlite3.Connection) -> bool:
    pid = (person_id or "").strip()
    if not pid:
        return False
    return bool(_rbac.can(pid, code, _target(), conn=conn))


def require(person_id: str | None, code: str, conn: sqlite3.Connection) -> None:
    if not person_can(person_id, code, conn):
        raise FinanceNotaError(
            "You do not have access to GGV notas.",
            code="forbidden",
            http_status=403,
            extra={"required_permission": code},
        )


def _audit(
    conn: sqlite3.Connection,
    *,
    person_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    result: str = "SUCCEEDED",
    reason_code: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    audit_log.record_event(
        action=action,
        result=result,
        source="ggv_finance_nota",
        actor_type="PERSON",
        actor_person_id=person_id,
        verified_person_id=person_id,
        entity_id=ENTITY_GGV,
        resource_type=resource_type,
        resource_id=resource_id,
        reason_code=reason_code,
        metadata=metadata,
        conn=conn,
        commit=False,
    )


def _history(
    conn: sqlite3.Connection,
    *,
    person_id: str,
    action: str,
    nota_id: str | None = None,
    vendor_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO ggv_nota_history (
          history_id, nota_id, vendor_id, action, actor_person_id, detail_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _mint("HST"),
            nota_id,
            vendor_id,
            action,
            person_id,
            json.dumps(detail or {}, default=str),
            _now(),
        ),
    )


def norm_name(value: str | None) -> str:
    text = (value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def norm_phone(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def norm_email(value: str | None) -> str:
    return (value or "").strip().lower()


def norm_tax(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_confirmed_amount(value: Any) -> str | None:
    """Human-typed amount. Blank stays blank. Never invent zero."""
    text = _blank(value)
    if text is None:
        return None
    text = text.replace(" ", "")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", text):
        raise FinanceNotaError(
            "Type the amount as digits, for example 250000. Leave it blank if the nota does not show one.",
            code="bad_amount",
        )
    if text.startswith("0") and text not in {"0", "0.0", "0.00"} and not text.startswith("0."):
        text = str(int(text.split(".", 1)[0])) + (("." + text.split(".", 1)[1]) if "." in text else "")
    return text


def _unambiguous_amount(token: str | None) -> str | None:
    raw = (token or "").strip()
    if re.fullmatch(r"\d+", raw):
        return raw
    if re.fullmatch(r"\d+\.\d{2}", raw):
        return raw
    return None


def extract_text(data: bytes, content_type: str, filename: str) -> str:
    ctype = (content_type or "").lower()
    name = (filename or "").lower()
    if ctype.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif")):
        return ""
    if ctype.startswith("text/") or name.endswith((".txt", ".csv")):
        return data.decode("utf-8", "replace")
    parts: list[str] = []
    if ctype == "application/pdf" or name.endswith(".pdf") or data.startswith(b"%PDF"):
        try:
            from io import BytesIO

            import pypdf

            reader = pypdf.PdfReader(BytesIO(data))
            for page in reader.pages:
                parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
        raw = data.decode("latin-1", "replace")
        parts.extend(re.findall(r"\(([^)\n]{2,180})\)", raw))
        return "\n".join(parts)
    return ""


def propose_from_text(text: str) -> dict[str, Any]:
    """Proposals only. Missing amounts stay missing."""
    body = text or ""
    fields: dict[str, Any] = {
        "vendor_name": None,
        "invoice_no": None,
        "nota_date": None,
        "amount": None,
        "amount_raw": None,
        "tax": None,
        "tax_raw": None,
        "currency": None,
        "items": [],
        "bank_observed": None,
    }
    confidence: dict[str, str] = {}
    vendor = re.search(
        r"(?i)(?:vendor|supplier|from|kepada)\s*[:\-]\s*([A-Za-z][A-Za-z0-9 .,&'()-]{1,80})",
        body,
    )
    if vendor:
        fields["vendor_name"] = vendor.group(1).strip(" .")
        confidence["vendor_name"] = "read_from_document"
    invoice = re.search(
        r"(?i)(?:invoice|nota|inv)\s*(?:no\.?|number|#|:)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
        body,
    )
    if invoice:
        fields["invoice_no"] = invoice.group(1).strip()
        confidence["invoice_no"] = "read_from_document"
    date = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", body) or re.search(
        r"(?i)(?:date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        body,
    )
    if date:
        fields["nota_date"] = date.group(1)
        confidence["nota_date"] = "read_from_document"
    totals = re.findall(
        r"(?i)(?:grand\s*total|jumlah|total)\s*[:\-]?\s*(?:idr|rp\.?|usd|eur)?\s*([0-9][0-9.,]*)",
        body,
    )
    if len(totals) == 1:
        fields["amount_raw"] = totals[0]
        fields["amount"] = _unambiguous_amount(totals[0].replace(",", ""))
        confidence["amount"] = "read_from_document" if fields["amount"] else "check_this"
    elif len(totals) > 1:
        fields["amount_raw"] = totals[-1]
        fields["amount"] = None
        confidence["amount"] = "check_this"
    else:
        confidence["amount"] = "missing"
    taxes = re.findall(
        r"(?i)(?:\bppn\b|\btax\b|\bvat\b)\s*[:\-]?\s*(?:idr|rp\.?|usd|eur)?\s*([0-9][0-9.,]*)",
        body,
    )
    if len(taxes) == 1:
        fields["tax_raw"] = taxes[0]
        fields["tax"] = _unambiguous_amount(taxes[0].replace(",", ""))
        confidence["tax"] = "read_from_document" if fields["tax"] else "check_this"
    elif taxes:
        fields["tax_raw"] = taxes[-1]
        confidence["tax"] = "check_this"
    currency = re.search(r"\b(IDR|USD|EUR)\b", body, re.I)
    if currency:
        fields["currency"] = currency.group(1).upper()
        confidence["currency"] = "read_from_document"
    elif re.search(r"\bRp\.?\b", body):
        fields["currency"] = "IDR"
        confidence["currency"] = "read_from_document"
    bank = re.search(
        r"(?i)((?:bank\s+[a-z][a-z ]{1,30}|bca|bni|bri|mandiri|rekening)\s*[:#-]?\s*[0-9][0-9 \-]{5,24})",
        body,
    )
    if bank:
        fields["bank_observed"] = " ".join(bank.group(1).split())
        confidence["bank_observed"] = "observed_not_verified"
    if not body.strip():
        confidence = {key: "missing" for key in ("vendor_name", "invoice_no", "nota_date", "amount", "tax", "currency")}
    return {
        "fields": fields,
        "confidence": confidence,
        "low_confidence": [key for key, level in confidence.items() if level in {"check_this", "missing"}],
        "read_something": bool(body.strip()),
    }


def propose_from_bytes(data: bytes, content_type: str, filename: str) -> dict[str, Any]:
    text = extract_text(data, content_type, filename)
    proposal = propose_from_text(text)
    if not proposal["read_something"]:
        proposal["message"] = (
            "We could not read amounts from this photo. Type what you see on the nota. "
            "Nothing was invented."
        )
    else:
        proposal["message"] = "Check the reading, then correct anything that is wrong."
    return proposal


def _stage_view(stage: str, *, failed: str | None = None) -> list[dict[str, str]]:
    order = ("uploading", "reading", "checking_vendor", "ready_for_review", "saved")
    anchor = stage if stage in order else "uploading"
    view = []
    for key in order:
        if failed and order.index(key) > order.index(failed):
            state = "pending"
        elif failed and key == failed:
            state = "failed"
        elif order.index(key) <= order.index(anchor):
            state = "done"
        else:
            state = "pending"
        label = "Saved" if key == "saved" and state == "done" else STAGE_LABEL[key]
        view.append({"id": key, "label": label, "status": state})
    return view


def _open_ready(db_path: Path | str | None = None) -> sqlite3.Connection:
    conn = db_connect(db_path)
    ensure_schema(conn)
    ensure_rbac(conn, commit=True)
    migrate_legacy_blobs(conn)
    return conn


def _col(row: sqlite3.Row, name: str, default: Any = None) -> Any:
    if name not in row.keys():
        return default
    value = row[name]
    return default if value is None else value


def _file_row(row: sqlite3.Row) -> dict[str, Any]:
    rel = str(_col(row, "nas_rel_path", "") or "")
    if rel.startswith("/") or ".." in Path(rel).parts:
        rel = ""
    state = str(_col(row, "backup_state", "UNKNOWN") or "UNKNOWN").upper()
    if state not in BACKUP_STATES or (state == "BACKED_UP" and not B2_FINANCE_PROVEN):
        state = "UNKNOWN"
    provenance = _col(row, "source_provenance", "") or ""
    try:
        provenance_obj = json.loads(provenance) if provenance else {}
    except json.JSONDecodeError:
        provenance_obj = {}
    original = _col(row, "original_filename") or row["filename"]
    return {
        "file_id": row["file_id"],
        "filename": original,
        "original_filename": original,
        "canonical_filename": _col(row, "canonical_filename"),
        "content_type": row["content_type"],
        "role": row["role"],
        "evidence_id": row["evidence_id"],
        "sha256": row["sha256"],
        "file_hash": row["sha256"],
        "size_bytes": _col(row, "size_bytes"),
        "nota_id": row["nota_id"],
        "vendor_id": _col(row, "vendor_id"),
        "upload_id": row["upload_id"],
        "upload_timestamp": _col(row, "upload_timestamp") or row["created_at"],
        "created_at": row["created_at"],
        "source_provenance": provenance_obj,
        "backup_state": state,
        "backup_label": BACKUP_LABEL.get(state, "Unknown"),
        "nas_rel_path": rel,
        "storage_root_id": _col(row, "storage_root_id") or STORAGE_ROOT_ID,
    }


def _vendor_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "vendor_id": row["vendor_id"],
        "name": row["display_name"],
        "category": row["category"],
        "contact_name": row["contact_name"],
        "phone": row["phone"],
        "email": row["email"],
        "tax_id": row["tax_id"],
        "address": row["address"],
        "notes": row["notes"],
        "status": row["status"],
    }


def _nota_public(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    vendor = None
    if row["vendor_id"]:
        v = conn.execute("SELECT * FROM ggv_vendors WHERE vendor_id=?", (row["vendor_id"],)).fetchone()
        if v:
            vendor = _vendor_public(v)
    files = [
        _file_row(f)
        for f in conn.execute(
            "SELECT * FROM ggv_nota_files WHERE nota_id=? ORDER BY role, created_at",
            (row["nota_id"],),
        ).fetchall()
    ]
    history = [
        {
            "action": h["action"],
            "at": h["created_at"],
            "by": h["actor_person_id"],
            "detail": json.loads(h["detail_json"] or "{}"),
        }
        for h in conn.execute(
            "SELECT * FROM ggv_nota_history WHERE nota_id=? ORDER BY created_at",
            (row["nota_id"],),
        ).fetchall()
    ]
    bank = conn.execute(
        """
        SELECT raw_text, status FROM ggv_vendor_bank_observed
        WHERE nota_id=? ORDER BY created_at DESC LIMIT 1
        """,
        (row["nota_id"],),
    ).fetchone()
    state = row["workflow_state"]
    return {
        "nota_id": row["nota_id"],
        "vendor_id": row["vendor_id"],
        "vendor": vendor,
        "invoice_no": row["invoice_no"],
        "date": row["nota_date"],
        "currency": row["currency"],
        "amount": row["amount"],
        "tax": row["tax"],
        "category": row["category"],
        "items": json.loads(row["items_json"] or "[]"),
        "notes": row["notes"],
        "state": state,
        "state_label": STATE_LABEL.get(state, state),
        "amount_confirmed": bool(row["amount_confirmed"]),
        "date_confirmed": bool(row["date_confirmed"]),
        "vendor_confirmed": bool(row["vendor_confirmed"]),
        "proposals": json.loads(row["proposals_json"] or "{}"),
        "confidence": json.loads(row["confidence_json"] or "{}"),
        "files": files,
        "history": history,
        "created_by": row["created_by_person_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "submitted_at": row["submitted_at"],
        "approval_request_id": row["approval_request_id"],
        "bank_details": {
            "text": bank["raw_text"] if bank else None,
            "status": "OBSERVED" if bank else None,
            "verified": False,
        },
        "entered": True,
        "approved_for_payment": False,
        "paid": state == "paid_claimed",
        "payment_verified": state == "payment_verified",
        "nota_is_not_payment": True,
    }


def _decode_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not files:
        raise FinanceNotaError("Choose a photo or PDF first.", code="missing_file")
    if len(files) > MAX_FILES:
        raise FinanceNotaError("You can attach up to 8 files on one nota.", code="too_many_files")
    out = []
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise FinanceNotaError("A file could not be read.", code="bad_file")
        raw_b64 = item.get("data_base64") or ""
        try:
            data = base64.b64decode(raw_b64, validate=False)
        except Exception as exc:  # noqa: BLE001
            raise FinanceNotaError("A file could not be read. Try that file again.", code="bad_file") from exc
        if not data:
            raise FinanceNotaError("A file was empty.", code="empty_file")
        if len(data) > MAX_BYTES:
            raise FinanceNotaError("That file is too large. Use a photo or PDF under 8 MB.", code="file_too_large")
        filename = Path(str(item.get("filename") or "nota")).name[:180] or "nota"
        content_type = str(item.get("content_type") or "application/octet-stream")[:120]
        out.append(
            {
                "filename": filename,
                "content_type": content_type,
                "data": data,
                "role": "primary" if index == 0 else "supporting",
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return out


def set_media_root(path: Path | str | None) -> None:
    """Test hook. Production leaves this unset and uses MEDIA_LIBRARY."""
    global _MEDIA_ROOT
    _MEDIA_ROOT = Path(path) if path else None


def set_legacy_blob_dir(path: Path | str | None) -> None:
    global _LEGACY_DIR
    _LEGACY_DIR = Path(path) if path else None


def media_root() -> Path:
    if _MEDIA_ROOT is not None:
        return Path(_MEDIA_ROOT)
    return _nas.MEDIA_LIBRARY


def legacy_blob_dir() -> Path:
    if _LEGACY_DIR is not None:
        return Path(_LEGACY_DIR)
    return LEGACY_BLOB_DIR


def finance_nota_root() -> Path:
    return media_root() / FINANCE_REL


def storage_ready() -> bool:
    root = media_root()
    try:
        return root.exists() and root.is_dir()
    except OSError:
        return False


def _is_legacy_rel(rel: str | None) -> bool:
    text = (rel or "").replace("\\", "/")
    return "state/ggv-finance-nota/blobs" in text or text.startswith("blobs/")


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(name or "nota").name).strip(".-")
    return (cleaned[:80] or "nota")


def _canonical_filename(file_id: str, original: str) -> str:
    return f"{file_id}-{_safe_filename(original)}"


def evidence_path(rel_path: str) -> Path:
    """Resolve a media-library-relative finance path. Does not require the file to exist."""
    rel = (rel_path or "").replace("\\", "/").strip()
    if not rel or rel.startswith("/") or rel.startswith("Volumes/"):
        raise FinanceNotaError(
            "Evidence path must stay relative to the media library.",
            code="absolute_path_refused",
            http_status=500,
        )
    if ".." in Path(rel).parts or _is_legacy_rel(rel):
        raise FinanceNotaError(
            "That file is not in canonical nota storage.",
            code="canonical_local_forbidden",
            http_status=409,
        )
    root = media_root().resolve()
    path = (root / rel).resolve()
    jail = (root / FINANCE_REL).resolve()
    if path != jail and jail not in path.parents:
        raise FinanceNotaError("Saved file path is not available.", code="missing_blob", http_status=404)
    return path


def _require_storage() -> None:
    if storage_ready():
        return
    raise FinanceNotaError(
        "The document store is not connected. Nothing was saved on this computer as the copy of record.",
        code="nas_unmounted",
        http_status=503,
        extra={"preserved": False, "blocked": "NAS_UNMOUNTED"},
    )


def assert_backup_state(value: str | None, *, proof: dict[str, Any] | None = None) -> str:
    """Refuse BACKED_UP until a real backup proof exists. Default is PENDING."""
    state = (value or "PENDING").strip().upper().replace(" ", "_")
    if state == "BACKEDUP":
        state = "BACKED_UP"
    if state not in BACKUP_STATES:
        raise FinanceNotaError("Unknown backup state.", code="bad_backup_state")
    if state == "BACKED_UP":
        proof = proof or {}
        if not B2_FINANCE_PROVEN or not str(proof.get("proof_id") or "").strip():
            raise FinanceNotaError(
                "Backup is not proven. This file is not marked backed up.",
                code="backup_unproven",
                http_status=409,
            )
    return state


def _place_evidence(
    *,
    file_id: str,
    original_filename: str,
    data: bytes,
    when_iso: str,
) -> dict[str, Any]:
    """Stage in the month folder, hash, then publish the canonical name. No local blob."""
    _require_storage()
    digest = hashlib.sha256(data).hexdigest()
    year = when_iso[:4]
    month = when_iso[5:7]
    if not (len(year) == 4 and year.isdigit() and len(month) == 2 and month.isdigit()):
        raise FinanceNotaError("Upload time is not usable for storage.", code="bad_timestamp", http_status=500)
    folder = finance_nota_root() / year / month
    folder.mkdir(parents=True, exist_ok=True)
    canonical = _canonical_filename(file_id, original_filename)
    dest = folder / canonical
    if dest.exists():
        canonical = f"{file_id}-{uuid.uuid4().hex[:6]}-{_safe_filename(original_filename)}"
        dest = folder / canonical
    partial = dest.with_name(dest.name + ".partial")
    partial.write_bytes(data)
    written = partial.read_bytes()
    if hashlib.sha256(written).hexdigest() != digest:
        partial.unlink(missing_ok=True)
        raise FinanceNotaError(
            "The file could not be stored. The upload was not committed.",
            code="store_failed",
            http_status=500,
        )
    partial.replace(dest)
    rel = dest.resolve().relative_to(media_root().resolve()).as_posix()
    if not rel.startswith("Finance/GGV/Notas/"):
        dest.unlink(missing_ok=True)
        raise FinanceNotaError("Finance evidence left its folder.", code="path_jail", http_status=500)
    return {
        "nas_rel_path": rel,
        "canonical_filename": canonical,
        "size_bytes": len(data),
        "file_hash": digest,
        "backup_state": assert_backup_state("PENDING"),
        "storage_root_id": STORAGE_ROOT_ID,
    }


def _load_bytes(rel_path: str) -> bytes:
    path = evidence_path(rel_path)
    if not path.is_file():
        raise FinanceNotaError(
            "The saved file is missing. The upload record is still here — do not start a new upload if you can retry.",
            code="blob_missing",
            http_status=409,
        )
    return path.read_bytes()


def _legacy_source_path(rel_path: str) -> Path | None:
    text = (rel_path or "").replace("\\", "/")
    if not text:
        return None
    candidate = Path(text)
    if candidate.is_file():
        return candidate
    under_beta = (BETA_ROOT / text).resolve()
    if under_beta.is_file():
        return under_beta
    name = Path(text).name
    legacy = legacy_blob_dir()
    if legacy.exists():
        matches = [p for p in legacy.rglob(name) if p.is_file()]
        if len(matches) == 1:
            return matches[0]
    return None


def create_upload(person_id: str, files: list[dict[str, Any]], *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.create", c)
        require(person_id, "evidence.create", c)
        decoded = _decode_files(files)
        upload_id = _mint("UPL")
        ts = _now()
        c.execute(
            """
            INSERT INTO ggv_uploads (
              upload_id, entity_id, created_by_person_id, stage, preserved,
              created_at, updated_at
            ) VALUES (?, ?, ?, 'uploading', 1, ?, ?)
            """,
            (upload_id, ENTITY_GGV, person_id, ts, ts),
        )
        stored = []
        placed_rows = []
        for item in decoded:
            file_id = _mint("FILE")
            meta = _place_evidence(
                file_id=file_id,
                original_filename=item["filename"],
                data=item["data"],
                when_iso=ts,
            )
            provenance = {
                "actor_person_id": person_id,
                "upload_id": upload_id,
                "evidence_id": None,
                "capture_method": "upload",
            }
            placed_rows.append((file_id, item, meta, provenance))
        for file_id, item, meta, provenance in placed_rows:
            c.execute(
                """
                INSERT INTO ggv_nota_files (
                  file_id, upload_id, nota_id, filename, content_type, sha256,
                  rel_path, role, evidence_id, created_at,
                  original_filename, canonical_filename, size_bytes, vendor_id,
                  source_provenance, backup_state, nas_rel_path, storage_root_id,
                  upload_timestamp
                ) VALUES (
                  ?, ?, NULL, ?, ?, ?, ?, ?, NULL, ?,
                  ?, ?, ?, NULL, ?, ?, ?, ?, ?
                )
                """,
                (
                    file_id,
                    upload_id,
                    item["filename"],
                    item["content_type"],
                    item["sha256"],
                    meta["nas_rel_path"],
                    item["role"],
                    ts,
                    item["filename"],
                    meta["canonical_filename"],
                    meta["size_bytes"],
                    json.dumps(provenance),
                    meta["backup_state"],
                    meta["nas_rel_path"],
                    meta["storage_root_id"],
                    ts,
                ),
            )
            stored.append(
                {
                    "file_id": file_id,
                    "filename": item["filename"],
                    "role": item["role"],
                    "nas_rel_path": meta["nas_rel_path"],
                    "backup_state": meta["backup_state"],
                    "storage_root_id": meta["storage_root_id"],
                }
            )
        _history(c, person_id=person_id, action="upload_saved", detail={"upload_id": upload_id, "files": len(stored)})
        _audit(
            c,
            person_id=person_id,
            action="ggv.nota.upload",
            resource_type="ggv_upload",
            resource_id=upload_id,
            metadata={"files": len(stored)},
        )
        c.commit()
        return public_payload(
            {
                "ok": True,
                "upload_id": upload_id,
                "stage": "uploading",
                "stage_label": "Uploading",
                "progress": _stage_view("uploading"),
                "files": stored,
                "preserved": True,
                "message": "Upload saved. Next we read the document.",
            }
        )
    except Exception:
        c.rollback()
        raise
    finally:
        if own:
            c.close()


def _upload_or_404(conn: sqlite3.Connection, upload_id: str, person_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM ggv_uploads WHERE upload_id=?", (upload_id,)).fetchone()
    if not row:
        raise FinanceNotaError("That upload is not here.", code="not_found", http_status=404)
    if row["created_by_person_id"] != person_id and not person_can(person_id, "finance.nota.edit", conn):
        raise FinanceNotaError("You do not have access to this upload.", code="forbidden", http_status=403)
    return row


def read_upload(person_id: str, upload_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.create", c)
        row = _upload_or_404(c, upload_id, person_id)
        primary = c.execute(
            """
            SELECT * FROM ggv_nota_files
            WHERE upload_id=? AND role='primary'
            ORDER BY created_at LIMIT 1
            """,
            (upload_id,),
        ).fetchone()
        if not primary:
            raise FinanceNotaError("The upload has no document to read.", code="missing_file", http_status=409)
        try:
            data = _load_bytes(_col(primary, "nas_rel_path") or primary["rel_path"])
            proposal = propose_from_bytes(data, primary["content_type"] or "", primary["filename"] or "")
        except FinanceNotaError as exc:
            c.execute(
                """
                UPDATE ggv_uploads
                   SET stage='failed', failure_stage='reading', failure_message=?, updated_at=?
                 WHERE upload_id=?
                """,
                (str(exc), _now(), upload_id),
            )
            c.commit()
            raise FinanceNotaError(
                f"Reading the document failed. Your upload is still saved ({upload_id}). Retry reading — do not upload again.",
                code=exc.code,
                http_status=exc.http_status,
                extra={"upload_id": upload_id, "preserved": True, "retry": "read"},
            ) from exc
        c.execute(
            """
            UPDATE ggv_uploads
               SET stage='reading', failure_stage=NULL, failure_message=NULL,
                   proposals_json=?, updated_at=?
             WHERE upload_id=?
            """,
            (json.dumps(proposal), _now(), upload_id),
        )
        c.commit()
        return public_payload(
            {
                "ok": True,
                "upload_id": upload_id,
                "stage": "reading",
                "stage_label": "Reading document",
                "progress": _stage_view("reading"),
                "proposals": proposal,
                "preserved": True,
                "message": proposal.get("message"),
            }
        )
    finally:
        if own:
            c.close()


def _vendor_matches(conn: sqlite3.Connection, proposal: dict[str, Any]) -> list[dict[str, Any]]:
    fields = (proposal or {}).get("fields") or {}
    name = norm_name(fields.get("vendor_name"))
    if not name:
        return []
    rows = conn.execute(
        """
        SELECT * FROM ggv_vendors
        WHERE entity_id=? AND status='ACTIVE'
          AND (name_norm=? OR name_norm LIKE ?)
        ORDER BY display_name
        LIMIT 8
        """,
        (ENTITY_GGV, name, f"%{name}%"),
    ).fetchall()
    return [_vendor_public(row) for row in rows]


def check_vendor(person_id: str, upload_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.create", c)
        require(person_id, "vendor.read", c)
        row = _upload_or_404(c, upload_id, person_id)
        if not row["proposals_json"]:
            raise FinanceNotaError(
                "Read the document before checking the vendor. The upload is still saved.",
                code="read_first",
                http_status=409,
                extra={"upload_id": upload_id, "preserved": True, "retry": "read"},
            )
        proposal = json.loads(row["proposals_json"])
        matches = _vendor_matches(c, proposal)
        hint = (proposal.get("fields") or {}).get("vendor_name")
        c.execute(
            """
            UPDATE ggv_uploads
               SET stage='ready_for_review', vendor_matches_json=?, updated_at=?
             WHERE upload_id=?
            """,
            (json.dumps(matches), _now(), upload_id),
        )
        c.commit()
        if matches:
            message = f"We think this is: {matches[0]['name']}"
        elif hint:
            message = "Vendor not found. Create a new vendor without leaving this nota."
        else:
            message = "No vendor name was read. Search or create one."
        return public_payload(
            {
                "ok": True,
                "upload_id": upload_id,
                "stage": "ready_for_review",
                "stage_label": "Ready for review",
                "progress": _stage_view("ready_for_review"),
                "proposals": proposal,
                "vendor_matches": matches,
                "suggested_vendor": matches[0] if matches else None,
                "preserved": True,
                "message": message,
            }
        )
    finally:
        if own:
            c.close()


def search_vendors(person_id: str, query: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "vendor.read", c)
        q = norm_name(query)
        if not q:
            rows = c.execute(
                """
                SELECT * FROM ggv_vendors
                WHERE entity_id=? AND status='ACTIVE'
                ORDER BY updated_at DESC LIMIT 30
                """,
                (ENTITY_GGV,),
            ).fetchall()
        else:
            like = f"%{q}%"
            rows = c.execute(
                """
                SELECT * FROM ggv_vendors
                WHERE entity_id=? AND status='ACTIVE'
                  AND (
                    name_norm LIKE ? OR ifnull(email_norm,'') LIKE ?
                    OR ifnull(phone_norm,'') LIKE ? OR ifnull(tax_norm,'') LIKE ?
                  )
                ORDER BY display_name LIMIT 30
                """,
                (ENTITY_GGV, like, like, norm_phone(query), norm_tax(query)),
            ).fetchall()
        return public_payload({"ok": True, "vendors": [_vendor_public(row) for row in rows]})
    finally:
        if own:
            c.close()


def _duplicate_vendors(conn: sqlite3.Connection, fields: dict[str, Any]) -> list[dict[str, Any]]:
    name = norm_name(fields.get("display_name") or fields.get("name"))
    phone = norm_phone(fields.get("phone"))
    email = norm_email(fields.get("email"))
    tax = norm_tax(fields.get("tax_id"))
    clauses = []
    params: list[Any] = [ENTITY_GGV]
    if name:
        clauses.append("name_norm=?")
        params.append(name)
    if len(phone) >= 6:
        clauses.append("phone_norm=?")
        params.append(phone)
    if email:
        clauses.append("email_norm=?")
        params.append(email)
    if len(tax) >= 4:
        clauses.append("tax_norm=?")
        params.append(tax)
    if not clauses:
        return []
    rows = conn.execute(
        f"""
        SELECT * FROM ggv_vendors
        WHERE entity_id=? AND status='ACTIVE' AND ({' OR '.join(clauses)})
        """,
        params,
    ).fetchall()
    return [_vendor_public(row) for row in rows]


def create_vendor(person_id: str, body: dict[str, Any], *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "vendor.create", c)
        name = _blank(body.get("display_name") or body.get("name"))
        if not name:
            raise FinanceNotaError("Vendor name is required. Other fields can stay unknown.", code="name_required")
        fields = {
            "display_name": name,
            "category": _blank(body.get("category")),
            "contact_name": _blank(body.get("contact_name")),
            "phone": _blank(body.get("phone")),
            "email": _blank(body.get("email")),
            "tax_id": _blank(body.get("tax_id")),
            "address": _blank(body.get("address")),
            "notes": _blank(body.get("notes")),
        }
        matches = _duplicate_vendors(c, fields)
        decision = _blank(body.get("duplicate_decision"))
        if matches and decision not in {"use_existing", "create_separate"}:
            return public_payload(
                {
                    "ok": False,
                    "error": "possible_duplicate_vendor",
                    "message": "Possible existing vendor. Use the existing one, or create a separate vendor and say why.",
                    "matches": matches,
                    "preserved": True,
                    "_status": 409,
                }
            )
        if decision == "use_existing":
            existing_id = _blank(body.get("existing_vendor_id")) or matches[0]["vendor_id"]
            row = c.execute("SELECT * FROM ggv_vendors WHERE vendor_id=?", (existing_id,)).fetchone()
            if not row:
                raise FinanceNotaError("That vendor was not found.", code="not_found", http_status=404)
            _audit(
                c,
                person_id=person_id,
                action="ggv.vendor.duplicate_decision",
                resource_type="ggv_vendor",
                resource_id=existing_id,
                reason_code="use_existing",
                metadata={"matches": [m["vendor_id"] for m in matches]},
            )
            _history(
                c,
                person_id=person_id,
                vendor_id=existing_id,
                action="vendor_use_existing",
                detail={"matches": [m["vendor_id"] for m in matches]},
            )
            c.commit()
            return public_payload(
                {
                    "ok": True,
                    "created": False,
                    "decision": "use_existing",
                    "vendor": _vendor_public(row),
                    "message": "Using the existing vendor.",
                }
            )
        if decision == "create_separate" and not _blank(body.get("duplicate_reason")):
            raise FinanceNotaError(
                "Say why this is a separate vendor. We will not merge them silently.",
                code="reason_required",
            )
        vendor_id = _mint("VEND")
        ts = _now()
        reason = _blank(body.get("duplicate_reason"))
        notes = fields["notes"]
        if reason:
            notes = (notes + "\n" if notes else "") + f"Separate vendor reason: {reason}"
        c.execute(
            """
            INSERT INTO ggv_vendors (
              vendor_id, entity_id, display_name, name_norm, category, contact_name,
              phone, phone_norm, email, email_norm, tax_id, tax_norm, address, notes,
              status, created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
            """,
            (
                vendor_id,
                ENTITY_GGV,
                name,
                norm_name(name),
                fields["category"],
                fields["contact_name"],
                fields["phone"],
                norm_phone(fields["phone"]),
                fields["email"],
                norm_email(fields["email"]),
                fields["tax_id"],
                norm_tax(fields["tax_id"]),
                fields["address"],
                notes,
                person_id,
                ts,
                ts,
            ),
        )
        _audit(
            c,
            person_id=person_id,
            action="ggv.vendor.create",
            resource_type="ggv_vendor",
            resource_id=vendor_id,
            reason_code=decision or "create",
            metadata={"separate_reason": reason, "possible_matches": [m["vendor_id"] for m in matches]},
        )
        _history(
            c,
            person_id=person_id,
            vendor_id=vendor_id,
            action="vendor_created",
            detail={"separate_reason": reason},
        )
        c.commit()
        row = c.execute("SELECT * FROM ggv_vendors WHERE vendor_id=?", (vendor_id,)).fetchone()
        return public_payload(
            {
                "ok": True,
                "created": True,
                "vendor": _vendor_public(row),
                "message": "Vendor created. You are still on the same nota.",
            }
        )
    finally:
        if own:
            c.close()


def _duplicate_notas(
    conn: sqlite3.Connection,
    *,
    hashes: list[str],
    vendor_id: str | None,
    invoice_no: str | None,
    nota_date: str | None,
    amount: str | None,
    exclude_id: str | None = None,
) -> list[dict[str, Any]]:
    found: dict[str, sqlite3.Row] = {}
    for digest in hashes:
        rows = conn.execute(
            """
            SELECT n.* FROM ggv_notas n
            JOIN ggv_nota_files f ON f.nota_id = n.nota_id
            WHERE f.sha256=? AND n.entity_id=?
            """,
            (digest, ENTITY_GGV),
        ).fetchall()
        for row in rows:
            found[row["nota_id"]] = row
    if vendor_id and invoice_no and nota_date and amount:
        rows = conn.execute(
            """
            SELECT * FROM ggv_notas
            WHERE entity_id=? AND vendor_id=? AND lower(invoice_no)=lower(?)
              AND nota_date=? AND amount=?
            """,
            (ENTITY_GGV, vendor_id, invoice_no, nota_date, amount),
        ).fetchall()
        for row in rows:
            found[row["nota_id"]] = row
    if exclude_id:
        found.pop(exclude_id, None)
    return [
        {
            "nota_id": row["nota_id"],
            "invoice_no": row["invoice_no"],
            "date": row["nota_date"],
            "amount": row["amount"],
            "vendor_id": row["vendor_id"],
            "state_label": STATE_LABEL.get(row["workflow_state"], row["workflow_state"]),
        }
        for row in found.values()
    ]


def _confirm_map(body: dict[str, Any]) -> dict[str, bool]:
    raw = body.get("confirm") if isinstance(body.get("confirm"), dict) else {}
    return {str(key): bool(raw.get(key)) for key in ("vendor", "invoice_no", "date", "amount", "tax", "currency", "category")}


def _apply_nota_fields(body: dict[str, Any]) -> dict[str, Any]:
    confirm = _confirm_map(body)
    amount = parse_confirmed_amount(body.get("amount")) if confirm.get("amount") else None
    if not confirm.get("amount"):
        amount = None
    tax = parse_confirmed_amount(body.get("tax")) if confirm.get("tax") and _blank(body.get("tax")) else None
    return {
        "vendor_id": _blank(body.get("vendor_id")) if confirm.get("vendor") else _blank(body.get("vendor_id")),
        "invoice_no": _blank(body.get("invoice_no")),
        "nota_date": _blank(body.get("date") or body.get("nota_date")),
        "currency": (_blank(body.get("currency")) or "").upper() or None,
        "amount": amount,
        "tax": tax,
        "category": _blank(body.get("category")),
        "items": body.get("items") if isinstance(body.get("items"), list) else [],
        "notes": _blank(body.get("notes")),
        "amount_confirmed": 1 if confirm.get("amount") and amount is not None else 0,
        "date_confirmed": 1 if confirm.get("date") and _blank(body.get("date") or body.get("nota_date")) else 0,
        "vendor_confirmed": 1 if confirm.get("vendor") and _blank(body.get("vendor_id")) else 0,
    }


def _state_for(fields: dict[str, Any]) -> str:
    if fields["vendor_confirmed"] and fields["amount_confirmed"] and fields["date_confirmed"]:
        return "ready"
    return "needs_review"


def _attach_evidence(
    conn: sqlite3.Connection,
    *,
    person_id: str,
    nota_id: str,
    file_row: sqlite3.Row,
) -> str | None:
    if not person_can(person_id, "evidence.record.submit", conn):
        return None
    try:
        saved = _evidence.submit_evidence(
            entity_id=ENTITY_GGV,
            evidence_type="invoice" if file_row["role"] == "primary" else "photo",
            governed_object_type="ggv_nota",
            governed_object_id=nota_id,
            verified_person_id=person_id,
            source_type="HUMAN",
            source_reference=file_row["filename"],
            object_ref=(_col(file_row, "nas_rel_path") or file_row["rel_path"]),
            content_hash=file_row["sha256"],
            metadata={"role": file_row["role"], "pack": BOUND, "bank_status": "not_verified"},
            conn=conn,
            commit=False,
        )
    except _evidence.EvidenceError:
        return None
    return str(saved.get("evidence_id") or "") or None


def _remember_bank(conn: sqlite3.Connection, *, person_id: str, nota_id: str, vendor_id: str | None, proposal: dict[str, Any]) -> None:
    text = _blank(((proposal or {}).get("fields") or {}).get("bank_observed"))
    if not text:
        return
    conn.execute(
        """
        INSERT INTO ggv_vendor_bank_observed (
          observation_id, vendor_id, nota_id, raw_text, status, created_by_person_id, created_at
        ) VALUES (?, ?, ?, ?, 'OBSERVED', ?, ?)
        """,
        (_mint("BANKOBS"), vendor_id, nota_id, text, person_id, _now()),
    )


def save_nota(person_id: str, body: dict[str, Any], *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.create", c)
        upload_id = _blank(body.get("upload_id"))
        if not upload_id:
            raise FinanceNotaError("Save uses the upload you already made. Do not upload the nota again.", code="missing_upload")
        upload = _upload_or_404(c, upload_id, person_id)
        if upload["nota_id"]:
            existing = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (upload["nota_id"],)).fetchone()
            return public_payload(
                {
                    "ok": True,
                    "saved": True,
                    "already_saved": True,
                    "nota": _nota_public(c, existing),
                    "progress": _stage_view("saved"),
                    "message": "Saved",
                }
            )
        fields = _apply_nota_fields(body)
        if fields["vendor_id"]:
            vendor = c.execute(
                "SELECT vendor_id FROM ggv_vendors WHERE vendor_id=? AND entity_id=?",
                (fields["vendor_id"], ENTITY_GGV),
            ).fetchone()
            if not vendor:
                raise FinanceNotaError("Choose a vendor from the list, or create one.", code="unknown_vendor")
        files = c.execute(
            "SELECT * FROM ggv_nota_files WHERE upload_id=?",
            (upload_id,),
        ).fetchall()
        hashes = [row["sha256"] for row in files]
        matches = _duplicate_notas(
            c,
            hashes=hashes,
            vendor_id=fields["vendor_id"],
            invoice_no=fields["invoice_no"],
            nota_date=fields["nota_date"],
            amount=fields["amount"],
        )
        decision = _blank(body.get("duplicate_decision"))
        if matches and decision not in {"use_existing", "create_separate"}:
            return public_payload(
                {
                    "ok": False,
                    "error": "possible_duplicate_nota",
                    "message": "This nota might already be saved. Open the existing one, or save a separate copy and say why.",
                    "matches": matches,
                    "upload_id": upload_id,
                    "preserved": True,
                    "_status": 409,
                }
            )
        if decision == "use_existing":
            existing_id = _blank(body.get("existing_nota_id")) or matches[0]["nota_id"]
            existing = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (existing_id,)).fetchone()
            if not existing:
                raise FinanceNotaError("That nota was not found.", code="not_found", http_status=404)
            _audit(
                c,
                person_id=person_id,
                action="ggv.nota.duplicate_decision",
                resource_type="ggv_nota",
                resource_id=existing_id,
                reason_code="use_existing",
                metadata={"upload_id": upload_id},
            )
            _history(c, person_id=person_id, nota_id=existing_id, action="duplicate_use_existing", detail={"upload_id": upload_id})
            c.execute(
                "UPDATE ggv_uploads SET nota_id=?, stage='saved', updated_at=? WHERE upload_id=?",
                (existing_id, _now(), upload_id),
            )
            c.commit()
            return public_payload(
                {
                    "ok": True,
                    "saved": True,
                    "decision": "use_existing",
                    "nota": _nota_public(c, existing),
                    "progress": _stage_view("saved"),
                    "message": "Saved",
                }
            )
        if matches and decision == "create_separate" and not _blank(body.get("duplicate_reason")):
            raise FinanceNotaError(
                "Say why this copy should be saved separately. We will not reject it silently.",
                code="reason_required",
            )
        proposal = json.loads(upload["proposals_json"] or "{}")
        nota_id = _mint("NOTA")
        state = _state_for(fields)
        ts = _now()
        c.execute(
            """
            INSERT INTO ggv_notas (
              nota_id, entity_id, vendor_id, invoice_no, nota_date, currency, amount, tax,
              category, items_json, notes, workflow_state, amount_confirmed, date_confirmed,
              vendor_confirmed, proposals_json, confidence_json, created_by_person_id,
              created_at, updated_at, submitted_at, approval_request_id, duplicate_of_nota_id,
              duplicate_reason
            ) VALUES (
              ?, ?, ?, ?, ?, ?, ?, ?,
              ?, ?, ?, ?, ?, ?,
              ?, ?, ?, ?,
              ?, ?, NULL, NULL, ?,
              ?
            )
            """,
            (
                nota_id,
                ENTITY_GGV,
                fields["vendor_id"],
                fields["invoice_no"],
                fields["nota_date"],
                fields["currency"],
                fields["amount"],
                fields["tax"],
                fields["category"],
                json.dumps(fields["items"]),
                fields["notes"],
                state,
                fields["amount_confirmed"],
                fields["date_confirmed"],
                fields["vendor_confirmed"],
                upload["proposals_json"],
                json.dumps(proposal.get("confidence") or {}),
                person_id,
                ts,
                ts,
                matches[0]["nota_id"] if matches else None,
                _blank(body.get("duplicate_reason")),
            ),
        )
        for file_row in files:
            evidence_id = _attach_evidence(c, person_id=person_id, nota_id=nota_id, file_row=file_row)
            provenance = _col(file_row, "source_provenance") or ""
            try:
                provenance_obj = json.loads(provenance) if provenance else {}
            except json.JSONDecodeError:
                provenance_obj = {}
            if not isinstance(provenance_obj, dict):
                provenance_obj = {}
            provenance_obj["evidence_id"] = evidence_id
            provenance_obj["nota_id"] = nota_id
            c.execute(
                """
                UPDATE ggv_nota_files
                   SET nota_id=?, evidence_id=?, vendor_id=?, source_provenance=?
                 WHERE file_id=?
                """,
                (
                    nota_id,
                    evidence_id,
                    fields["vendor_id"],
                    json.dumps(provenance_obj),
                    file_row["file_id"],
                ),
            )
        _remember_bank(c, person_id=person_id, nota_id=nota_id, vendor_id=fields["vendor_id"], proposal=proposal)
        c.execute(
            "UPDATE ggv_uploads SET nota_id=?, stage='saved', updated_at=? WHERE upload_id=?",
            (nota_id, ts, upload_id),
        )
        _history(c, person_id=person_id, nota_id=nota_id, action="nota_saved", detail={"state": state})
        _audit(
            c,
            person_id=person_id,
            action="ggv.nota.save",
            resource_type="ggv_nota",
            resource_id=nota_id,
            reason_code=decision or "save",
            metadata={"state": state, "duplicate_of": matches[0]["nota_id"] if matches else None},
        )
        c.commit()
        saved = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()
        return public_payload(
            {
                "ok": True,
                "saved": True,
                "nota": _nota_public(c, saved),
                "progress": _stage_view("saved"),
                "message": "Saved",
            }
        )
    finally:
        if own:
            c.close()


def edit_nota(person_id: str, nota_id: str, body: dict[str, Any], *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.edit", c)
        if _blank(body.get("workflow_state")) in TERMINAL_MONEY_STATES or _blank(body.get("state")) in TERMINAL_MONEY_STATES:
            raise FinanceNotaError(
                "Entering a nota does not approve it, pay it, or verify payment.",
                code="payment_refused",
                http_status=405,
            )
        row = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()
        if not row:
            raise FinanceNotaError("That nota was not found.", code="not_found", http_status=404)
        fields = _apply_nota_fields(body)
        if fields["vendor_id"]:
            vendor = c.execute(
                "SELECT vendor_id FROM ggv_vendors WHERE vendor_id=? AND entity_id=?",
                (fields["vendor_id"], ENTITY_GGV),
            ).fetchone()
            if not vendor:
                raise FinanceNotaError("Choose a vendor from the list, or create one.", code="unknown_vendor")
        state = row["workflow_state"]
        if state in PACK_WRITE_STATES and state != "waiting_approval":
            state = _state_for(fields)
        ts = _now()
        c.execute(
            """
            UPDATE ggv_notas SET
              vendor_id=?, invoice_no=?, nota_date=?, currency=?, amount=?, tax=?,
              category=?, items_json=?, notes=?, workflow_state=?,
              amount_confirmed=?, date_confirmed=?, vendor_confirmed=?, updated_at=?
            WHERE nota_id=?
            """,
            (
                fields["vendor_id"],
                fields["invoice_no"],
                fields["nota_date"],
                fields["currency"],
                fields["amount"],
                fields["tax"],
                fields["category"],
                json.dumps(fields["items"]),
                fields["notes"],
                state,
                fields["amount_confirmed"],
                fields["date_confirmed"],
                fields["vendor_confirmed"],
                ts,
                nota_id,
            ),
        )
        _history(c, person_id=person_id, nota_id=nota_id, action="nota_edited", detail={"state": state})
        _audit(c, person_id=person_id, action="ggv.nota.edit", resource_type="ggv_nota", resource_id=nota_id)
        c.commit()
        saved = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()
        return public_payload({"ok": True, "nota": _nota_public(c, saved), "message": "Saved"})
    finally:
        if own:
            c.close()


def submit_nota(person_id: str, nota_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.edit", c)
        row = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()
        if not row:
            raise FinanceNotaError("That nota was not found.", code="not_found", http_status=404)
        if not (row["vendor_confirmed"] and row["amount_confirmed"] and row["date_confirmed"] and row["vendor_id"] and row["amount"] and row["nota_date"]):
            raise FinanceNotaError(
                "Confirm the vendor, date, and amount before you submit. This still does not pay the nota.",
                code="not_ready",
            )
        approval_id = None
        approval_note = None
        try:
            from core import approvals as _approvals

            created = _approvals.create_approval_request(
                title=f"Review nota {row['invoice_no'] or nota_id}",
                description="Review this nota. This is not a payment and not a bank change.",
                owning_entity_id=ENTITY_GGV,
                required_permission_code="finance.nota.edit",
                verified_person_id=person_id,
                request_type="GENERAL",
                source_type="HUMAN",
                source_id=nota_id,
                governed_object_type="ggv_nota",
                governed_object_id=nota_id,
                bind_policy=False,
                enforce_evidence=False,
                link_work_item=False,
                conn=c,
                commit=False,
            )
            approval_id = created.get("approval_request_id")
        except Exception as exc:  # noqa: BLE001
            approval_note = type(exc).__name__
            approval_id = None
        ts = _now()
        c.execute(
            """
            UPDATE ggv_notas
               SET workflow_state='waiting_approval', submitted_at=?, approval_request_id=?, updated_at=?
             WHERE nota_id=?
            """,
            (ts, approval_id, ts, nota_id),
        )
        _history(
            c,
            person_id=person_id,
            nota_id=nota_id,
            action="nota_submitted",
            detail={"approval_request_id": approval_id, "approval_note": approval_note, "payment": False},
        )
        _audit(
            c,
            person_id=person_id,
            action="ggv.nota.submit",
            resource_type="ggv_nota",
            resource_id=nota_id,
            metadata={"approval_request_id": approval_id, "payment_execute": False},
        )
        c.commit()
        saved = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()
        return public_payload(
            {
                "ok": True,
                "nota": _nota_public(c, saved),
                "message": "Submitted. Waiting approval. This is not a payment.",
            }
        )
    finally:
        if own:
            c.close()


def get_nota(person_id: str, nota_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.read", c)
        row = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()
        if not row:
            raise FinanceNotaError("That nota was not found.", code="not_found", http_status=404)
        return public_payload({"ok": True, "nota": _nota_public(c, row)})
    finally:
        if own:
            c.close()


def list_notas(person_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.read", c)
        rows = c.execute(
            "SELECT * FROM ggv_notas WHERE entity_id=? ORDER BY updated_at DESC LIMIT 100",
            (ENTITY_GGV,),
        ).fetchall()
        return public_payload({"ok": True, "notas": [_nota_public(c, row) for row in rows]})
    finally:
        if own:
            c.close()


def edit_vendor(person_id: str, vendor_id: str, body: dict[str, Any], *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "vendor.edit", c)
        if body.get("bank_verified") or body.get("verify_bank") or _blank(body.get("bank_status")) == "VERIFIED":
            refuse_money(f"/api/ggv/finance/vendors/{vendor_id}/bank")
        row = c.execute(
            "SELECT * FROM ggv_vendors WHERE vendor_id=? AND entity_id=?",
            (vendor_id, ENTITY_GGV),
        ).fetchone()
        if not row:
            raise FinanceNotaError("That vendor was not found.", code="not_found", http_status=404)
        name = _blank(body.get("display_name") or body.get("name")) or row["display_name"]
        fields = {
            "display_name": name,
            "category": _blank(body.get("category")) if "category" in body else row["category"],
            "contact_name": _blank(body.get("contact_name")) if "contact_name" in body else row["contact_name"],
            "phone": _blank(body.get("phone")) if "phone" in body else row["phone"],
            "email": _blank(body.get("email")) if "email" in body else row["email"],
            "tax_id": _blank(body.get("tax_id")) if "tax_id" in body else row["tax_id"],
            "address": _blank(body.get("address")) if "address" in body else row["address"],
            "notes": _blank(body.get("notes")) if "notes" in body else row["notes"],
        }
        ts = _now()
        c.execute(
            """
            UPDATE ggv_vendors SET
              display_name=?, name_norm=?, category=?, contact_name=?, phone=?, phone_norm=?,
              email=?, email_norm=?, tax_id=?, tax_norm=?, address=?, notes=?, updated_at=?
            WHERE vendor_id=?
            """,
            (
                name,
                norm_name(name),
                fields["category"],
                fields["contact_name"],
                fields["phone"],
                norm_phone(fields["phone"]),
                fields["email"],
                norm_email(fields["email"]),
                fields["tax_id"],
                norm_tax(fields["tax_id"]),
                fields["address"],
                fields["notes"],
                ts,
                vendor_id,
            ),
        )
        _history(c, person_id=person_id, vendor_id=vendor_id, action="vendor_edited", detail={"name": name})
        _audit(c, person_id=person_id, action="ggv.vendor.edit", resource_type="ggv_vendor", resource_id=vendor_id)
        c.commit()
        saved = c.execute("SELECT * FROM ggv_vendors WHERE vendor_id=?", (vendor_id,)).fetchone()
        return public_payload({"ok": True, "vendor": _vendor_public(saved), "message": "Vendor saved."})
    finally:
        if own:
            c.close()


def get_vendor(person_id: str, vendor_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "vendor.read", c)
        row = c.execute("SELECT * FROM ggv_vendors WHERE vendor_id=? AND entity_id=?", (vendor_id, ENTITY_GGV)).fetchone()
        if not row:
            raise FinanceNotaError("That vendor was not found.", code="not_found", http_status=404)
        notas = c.execute(
            "SELECT nota_id, invoice_no, nota_date, amount, workflow_state FROM ggv_notas WHERE vendor_id=? ORDER BY updated_at DESC",
            (vendor_id,),
        ).fetchall()
        banks = c.execute(
            "SELECT raw_text, status, created_at FROM ggv_vendor_bank_observed WHERE vendor_id=? ORDER BY created_at DESC",
            (vendor_id,),
        ).fetchall()
        return public_payload(
            {
                "ok": True,
                "vendor": _vendor_public(row),
                "notas": [
                    {
                        "nota_id": n["nota_id"],
                        "invoice_no": n["invoice_no"],
                        "date": n["nota_date"],
                        "amount": n["amount"],
                        "state_label": STATE_LABEL.get(n["workflow_state"], n["workflow_state"]),
                    }
                    for n in notas
                ],
                "bank_observations": [
                    {"text": b["raw_text"], "status": "OBSERVED", "verified": False, "at": b["created_at"]}
                    for b in banks
                ],
            }
        )
    finally:
        if own:
            c.close()


def search_history(person_id: str, qs: dict[str, list[str]], *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.read", c)

        def one(key: str) -> str:
            return ((qs.get(key) or [""])[0] or "").strip()

        clauses = ["n.entity_id=?"]
        params: list[Any] = [ENTITY_GGV]
        vendor = one("vendor")
        if vendor:
            clauses.append("(n.vendor_id=? OR v.name_norm LIKE ? OR v.display_name LIKE ?)")
            params.extend([vendor, f"%{norm_name(vendor)}%", f"%{vendor}%"])
        if one("date"):
            clauses.append("n.nota_date LIKE ?")
            params.append(one("date") + "%")
        if one("amount"):
            clauses.append("n.amount=?")
            params.append(one("amount"))
        status = one("status").lower().replace(" ", "_").replace("—", "")
        label_to_state = {label.lower(): key for key, label in STATE_LABEL.items()}
        label_to_state.update({key: key for key in STATE_LABEL})
        if status:
            state = label_to_state.get(status) or label_to_state.get(status.replace("__", "_"))
            if state:
                clauses.append("n.workflow_state=?")
                params.append(state)
        if one("invoice"):
            clauses.append("lower(ifnull(n.invoice_no,'')) LIKE ?")
            params.append(f"%{one('invoice').lower()}%")
        if one("category"):
            clauses.append("lower(ifnull(n.category,'')) LIKE ?")
            params.append(f"%{one('category').lower()}%")
        logical = "substr(COALESCE(NULLIF(n.nota_date,''), n.created_at), 1, 7)"
        year = one("year")
        month = one("month")
        entity = one("entity")
        if entity and entity not in {ENTITY_GGV, "GGV"}:
            raise FinanceNotaError(
                "This account only covers GGV Finance.",
                code="forbidden",
                http_status=403,
            )
        if year:
            if not re.fullmatch(r"\d{4}", year):
                raise FinanceNotaError("Year should look like 2026.", code="bad_period")
            clauses.append(f"substr({logical}, 1, 4)=?")
            params.append(year)
        if month:
            if not re.fullmatch(r"\d{2}", month):
                raise FinanceNotaError("Month should look like 09.", code="bad_period")
            clauses.append(f"substr({logical}, 6, 2)=?")
            params.append(month)
        q = one("q")
        if q:
            like = f"%{q.lower()}%"
            clauses.append(
                "(lower(ifnull(n.invoice_no,'')) LIKE ? OR lower(ifnull(n.notes,'')) LIKE ? OR lower(ifnull(v.display_name,'')) LIKE ? OR n.nota_id LIKE ?)"
            )
            params.extend([like, like, like, f"%{q}%"])
        rows = c.execute(
            f"""
            SELECT n.* FROM ggv_notas n
            LEFT JOIN ggv_vendors v ON v.vendor_id = n.vendor_id
            WHERE {' AND '.join(clauses)}
            ORDER BY n.updated_at DESC
            LIMIT 100
            """,
            params,
        ).fetchall()
        public_rows = [_nota_public(c, row) for row in rows]
        return public_payload(
            {
                "ok": True,
                "results": public_rows,
                "groups": _group_notas(rows, public_rows),
                "grouping_mutates_evidence": False,
            }
        )
    finally:
        if own:
            c.close()


def overview(person_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.read", c)
        def count(sql: str, params: tuple = ()) -> int:
            return int(c.execute(sql, params).fetchone()[0])

        needs = count("SELECT COUNT(*) FROM ggv_notas WHERE entity_id=? AND workflow_state='needs_review'", (ENTITY_GGV,))
        waiting = count("SELECT COUNT(*) FROM ggv_notas WHERE entity_id=? AND workflow_state='waiting_approval'", (ENTITY_GGV,))
        unverified = count(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id=? AND workflow_state!='payment_verified'",
            (ENTITY_GGV,),
        )
        vendor_issues = count(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id=? AND (vendor_id IS NULL OR vendor_id='')",
            (ENTITY_GGV,),
        )
        recent_rows = c.execute(
            "SELECT * FROM ggv_notas WHERE entity_id=? ORDER BY created_at DESC LIMIT 8",
            (ENTITY_GGV,),
        ).fetchall()
        invoice_desk: dict[str, Any] = {}
        try:
            from core import ggv_finance_invoice as _inv

            invoice_desk = _inv.desk_snapshot(person_id, c)
        except Exception:
            invoice_desk = {}
        books_stamp: dict[str, Any] = {}
        try:
            from core import entity_books as _eb

            books_stamp = _eb.desk_stamp(ENTITY_GGV)
        except Exception:
            books_stamp = {
                "books_enabled": True,
                "books_opened": True,
                "empty": True,
                "shell_kind": "empty_shell",
                "db_file": "atrium-ggv.sqlite",
                "staff_ready": False,
                "human_commissioned": False,
                "pack": "CORE-BOOKS-1",
            }
        return public_payload(
            {
                "ok": True,
                "needs_review": needs,
                "waiting_approval": waiting,
                "payment_unverified": unverified,
                "vendor_issues": vendor_issues,
                "recently_added": [_nota_public(c, row) for row in recent_rows],
                "invoice_desk": invoice_desk,
                "finance_entities": invoice_desk.get("finance_entities") or [],
                "boundary_note": ZAYEN_NOTE,
                "payment_note": "Entering a nota is not the same as paying it.",
                "bank_note": "Bank details seen on a document are not verified.",
                "issued_is_not_paid": True,
                "books_enabled": True,
                "books_opened": True,
                "books_shell": books_stamp,
                "shell_kind": books_stamp.get("shell_kind") or "empty_shell",
                "db_file": books_stamp.get("db_file") or "atrium-ggv.sqlite",
                "accounts": books_stamp.get("accounts", 0),
                "journals": books_stamp.get("journals", 0),
                "staff_ready": False,
                "human_commissioned": False,
                "pack": books_stamp.get("pack") or "FC-SHELL-2",
            }
        )
    finally:
        if own:
            c.close()


def file_bytes(person_id: str, file_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.read", c)
        row = c.execute("SELECT * FROM ggv_nota_files WHERE file_id=?", (file_id,)).fetchone()
        if not row:
            raise FinanceNotaError("That file was not found.", code="not_found", http_status=404)
        data = _load_bytes(_col(row, "nas_rel_path") or row["rel_path"])
        return {
            "_file": {
                "data": data,
                "content_type": row["content_type"] or "application/octet-stream",
                "filename": row["filename"] or "nota",
            }
        }
    finally:
        if own:
            c.close()


def _logical_period(row: sqlite3.Row) -> tuple[str, str]:
    raw = str(row["nota_date"] or "") or str(row["created_at"] or "")
    year = raw[:4] if len(raw) >= 4 and raw[:4].isdigit() else "unknown"
    month = raw[5:7] if len(raw) >= 7 and raw[5:7].isdigit() else "unknown"
    return year, month


def _group_notas(rows: list[sqlite3.Row], public_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Logical year → month → nota. Does not move files."""
    tree: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row, public in zip(rows, public_rows):
        year, month = _logical_period(row)
        tree.setdefault(year, {}).setdefault(month, []).append(public)
    groups = []
    for year in sorted(tree):
        months = [{"month": month, "notas": tree[year][month]} for month in sorted(tree[year])]
        groups.append({"year": year, "months": months})
    return groups


def _period_key(row: sqlite3.Row) -> str:
    year, month = _logical_period(row)
    if year == "unknown" or month == "unknown":
        return ""
    return f"{year}-{month}"


def accountant_desk(person_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.nota.read", c)
        now = _now()
        period = now[:7]
        rows = c.execute(
            "SELECT * FROM ggv_notas WHERE entity_id=? ORDER BY updated_at DESC",
            (ENTITY_GGV,),
        ).fetchall()
        current = []
        missing = []
        unreviewed = []
        vendor_issues = []
        for row in rows:
            public = _nota_public(c, row)
            card = {
                "nota_id": public["nota_id"],
                "vendor": (public.get("vendor") or {}).get("name"),
                "invoice_no": public["invoice_no"],
                "date": public["date"],
                "state_label": public["state_label"],
                "file_count": len(public.get("files") or []),
            }
            if _period_key(row) == period:
                current.append(card)
            if not public.get("files"):
                missing.append(card)
            if row["workflow_state"] == "needs_review":
                unreviewed.append(card)
            if not row["vendor_id"]:
                vendor_issues.append(card)
        return public_payload(
            {
                "ok": True,
                "current_period": period,
                "current_month": current,
                "missing_evidence": missing,
                "unreviewed": unreviewed,
                "vendor_issues": vendor_issues,
                "books_complete": False,
                "accounting_total": None,
                "note": "No accounting total. The books are not complete on this screen.",
                "export_note": "A month evidence pack is a download copy. Original files stay one by one.",
            }
        )
    finally:
        if own:
            c.close()


def review_nota(
    person_id: str,
    nota_id: str,
    body: dict[str, Any],
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _open_ready()
    try:
        if not (
            person_can(person_id, "finance.nota.review", c)
            or person_can(person_id, "finance.nota.edit", c)
        ):
            raise FinanceNotaError(
                "You do not have access to GGV notas.",
                code="forbidden",
                http_status=403,
            )
        if body.get("workflow_state") in TERMINAL_MONEY_STATES or body.get("paid") or body.get("bank_verified"):
            refuse_money(f"/api/ggv/finance/notas/{nota_id}/review")
        row = c.execute(
            "SELECT * FROM ggv_notas WHERE nota_id=? AND entity_id=?",
            (nota_id, ENTITY_GGV),
        ).fetchone()
        if not row:
            raise FinanceNotaError("That nota was not found.", code="not_found", http_status=404)
        comment = _blank(body.get("comment")) or ""
        request_correction = bool(body.get("request_correction"))
        if not comment and not request_correction:
            raise FinanceNotaError("Write a comment, or ask for a correction.", code="missing_comment")
        action = "correction_requested" if request_correction else "nota_reviewed"
        before = [
            _col(f, "nas_rel_path")
            for f in c.execute("SELECT * FROM ggv_nota_files WHERE nota_id=?", (nota_id,)).fetchall()
        ]
        _history(
            c,
            person_id=person_id,
            nota_id=nota_id,
            vendor_id=row["vendor_id"],
            action=action,
            detail={"comment": comment, "request_correction": request_correction},
        )
        _audit(
            c,
            person_id=person_id,
            action="ggv.nota.review",
            resource_type="ggv_nota",
            resource_id=nota_id,
            metadata={"request_correction": request_correction},
        )
        c.commit()
        after = [
            _col(f, "nas_rel_path")
            for f in c.execute("SELECT * FROM ggv_nota_files WHERE nota_id=?", (nota_id,)).fetchall()
        ]
        saved = c.execute("SELECT * FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()
        return public_payload(
            {
                "ok": True,
                "action": action,
                "nota": _nota_public(c, saved),
                "evidence_paths_unchanged": before == after,
                "message": "Correction requested." if request_correction else "Comment saved.",
            }
        )
    finally:
        if own:
            c.close()


def _month_rows(conn: sqlite3.Connection, year: str, month: str) -> list[sqlite3.Row]:
    if not re.fullmatch(r"\d{4}", year or "") or not re.fullmatch(r"\d{2}", month or ""):
        raise FinanceNotaError("Choose a year and month, like 2026 and 09.", code="bad_period")
    if not 1 <= int(month) <= 12:
        raise FinanceNotaError("Month should be 01 to 12.", code="bad_period")
    period = f"{year}-{month}"
    rows = conn.execute(
        "SELECT * FROM ggv_notas WHERE entity_id=? ORDER BY nota_date, created_at",
        (ENTITY_GGV,),
    ).fetchall()
    return [row for row in rows if _period_key(row) == period]


def export_month_pack(
    person_id: str,
    qs: dict[str, list[str]],
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """In-memory ZIP product. Not written to NAS and not canonical storage."""
    own = conn is None
    c = conn or _open_ready()
    try:
        require(person_id, "finance.evidence.export", c)

        def one(key: str) -> str:
            return ((qs.get(key) or [""])[0] or "").strip()

        entity = one("entity")
        if entity and entity not in {ENTITY_GGV, "GGV"}:
            raise FinanceNotaError(
                "This account only covers GGV Finance.",
                code="forbidden",
                http_status=403,
            )
        year, month = one("year"), one("month")
        rows = _month_rows(c, year, month)
        file_meta = []
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for nota in rows:
                files = c.execute(
                    "SELECT * FROM ggv_nota_files WHERE nota_id=? ORDER BY role, created_at",
                    (nota["nota_id"],),
                ).fetchall()
                for file_row in files:
                    public = _file_row(file_row)
                    rel = public.get("nas_rel_path") or ""
                    entry = f"files/{public['file_id']}-{_safe_filename(public.get('original_filename') or 'nota')}"
                    if rel:
                        data = _load_bytes(rel)
                        archive.writestr(entry, data)
                        public["zip_entry"] = entry
                    public.pop("source_provenance", None)
                    file_meta.append(public)
            notas_index = []
            for nota in rows:
                notas_index.append(
                    {
                        "nota_id": nota["nota_id"],
                        "vendor_id": nota["vendor_id"],
                        "invoice_no": nota["invoice_no"],
                        "date": nota["nota_date"],
                        "state": nota["workflow_state"],
                        "amount": nota["amount"],
                    }
                )
            history = []
            if rows:
                ids = [row["nota_id"] for row in rows]
                marks = ",".join("?" for _ in ids)
                history = [
                    {
                        "nota_id": h["nota_id"],
                        "action": h["action"],
                        "at": h["created_at"],
                        "by": h["actor_person_id"],
                    }
                    for h in c.execute(
                        f"SELECT * FROM ggv_nota_history WHERE nota_id IN ({marks}) ORDER BY created_at",
                        ids,
                    ).fetchall()
                ]
            manifest = {
                "product": "MONTH EVIDENCE PACK",
                "canonical_storage": False,
                "zip_is_canonical": False,
                "entity": "GGV",
                "year": year,
                "month": month,
                "generated_at": _now(),
                "files": file_meta,
                "notas": notas_index,
                "accounting_total": None,
                "books_complete": False,
                "staff_ready": False,
                "commissioned": False,
                "telegram_retired": False,
            }
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            archive.writestr(
                "evidence-state.json",
                json.dumps({"history": history, "backup_proven": False}, indent=2),
            )
        payload = zip_buffer.getvalue()
        _audit(
            c,
            person_id=person_id,
            action="ggv.nota.export_month",
            resource_type="ggv_month_pack",
            resource_id=f"{year}-{month}",
            metadata={"files": len(file_meta), "canonical_storage": False},
        )
        c.commit()
        return {
            "_file": {
                "data": payload,
                "content_type": "application/zip",
                "filename": f"ggv-month-evidence-{year}-{month}.zip",
                "disposition": "attachment",
            }
        }
    finally:
        if own:
            c.close()


def migrate_legacy_blobs(conn: sqlite3.Connection) -> dict[str, Any]:
    """Copy local blob files onto NAS after a hash check. Keep the source if verify fails."""
    if _under_test() and _LEGACY_DIR is None:
        return {"ok": True, "migrated": 0, "legacy_files": 0, "skipped": "test_without_legacy_fixture"}
    legacy = legacy_blob_dir()
    disk_files: list[Path] = []
    if legacy.exists():
        disk_files = [p for p in legacy.rglob("*") if p.is_file() and not p.name.endswith(".partial")]
    rows = conn.execute("SELECT * FROM ggv_nota_files").fetchall()
    pending = []
    for row in rows:
        rel = str(row["rel_path"] or "")
        nas_rel = str(_col(row, "nas_rel_path", "") or "")
        if nas_rel.startswith("Finance/GGV/Notas/") and not _is_legacy_rel(rel):
            continue
        if _is_legacy_rel(rel) or _is_legacy_rel(nas_rel) or not nas_rel:
            if _is_legacy_rel(rel) or (not nas_rel and _legacy_source_path(rel)):
                pending.append(row)
    indexed_sources = set()
    if not pending and not disk_files:
        return {"ok": True, "migrated": 0, "legacy_files": 0, "deleted_sources": 0, "preserved": True}
    if not storage_ready():
        for row in pending:
            conn.execute(
                "UPDATE ggv_nota_files SET backup_state=? WHERE file_id=?",
                ("FAILED", row["file_id"]),
            )
        if pending:
            conn.commit()
        return {
            "ok": False,
            "code": "nas_unmounted",
            "migrated": 0,
            "legacy_files": len(disk_files),
            "preserved": True,
        }
    migrated = 0
    deleted = 0
    failed = 0
    ts = _now()
    for row in pending:
        source = _legacy_source_path(str(row["rel_path"] or ""))
        if source is None or not source.is_file():
            conn.execute(
                "UPDATE ggv_nota_files SET backup_state='FAILED' WHERE file_id=?",
                (row["file_id"],),
            )
            failed += 1
            continue
        indexed_sources.add(source.resolve())
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if row["sha256"] and row["sha256"] != digest:
            conn.execute(
                "UPDATE ggv_nota_files SET backup_state='FAILED' WHERE file_id=?",
                (row["file_id"],),
            )
            failed += 1
            continue
        meta = _place_evidence(
            file_id=row["file_id"],
            original_filename=row["filename"] or source.name,
            data=data,
            when_iso=_col(row, "upload_timestamp") or row["created_at"] or ts,
        )
        check = hashlib.sha256(_load_bytes(meta["nas_rel_path"])).hexdigest()
        if check != digest:
            conn.execute(
                "UPDATE ggv_nota_files SET backup_state='FAILED' WHERE file_id=?",
                (row["file_id"],),
            )
            failed += 1
            continue
        provenance = {
            "actor_person_id": None,
            "upload_id": row["upload_id"],
            "evidence_id": row["evidence_id"],
            "capture_method": "legacy_migrate",
        }
        conn.execute(
            """
            UPDATE ggv_nota_files SET
              rel_path=?, nas_rel_path=?, canonical_filename=?, original_filename=?,
              size_bytes=?, backup_state=?, storage_root_id=?, source_provenance=?,
              upload_timestamp=COALESCE(upload_timestamp, ?)
            WHERE file_id=?
            """,
            (
                meta["nas_rel_path"],
                meta["nas_rel_path"],
                meta["canonical_filename"],
                row["filename"] or source.name,
                meta["size_bytes"],
                "PENDING",
                STORAGE_ROOT_ID,
                json.dumps(provenance),
                row["created_at"],
                row["file_id"],
            ),
        )
        source.unlink()
        migrated += 1
        deleted += 1
    for source in disk_files:
        if source.resolve() in indexed_sources or not source.is_file():
            continue
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        file_id = _mint("FILE")
        meta = _place_evidence(
            file_id=file_id,
            original_filename=source.name,
            data=data,
            when_iso=ts,
        )
        if hashlib.sha256(_load_bytes(meta["nas_rel_path"])).hexdigest() != digest:
            failed += 1
            continue
        conn.execute(
            """
            INSERT INTO ggv_nota_files (
              file_id, upload_id, nota_id, filename, content_type, sha256,
              rel_path, role, evidence_id, created_at,
              original_filename, canonical_filename, size_bytes, vendor_id,
              source_provenance, backup_state, nas_rel_path, storage_root_id,
              upload_timestamp
            ) VALUES (
              ?, NULL, NULL, ?, 'application/octet-stream', ?, ?, 'supporting', NULL, ?,
              ?, ?, ?, NULL, ?, 'PENDING', ?, ?, ?
            )
            """,
            (
                file_id,
                source.name,
                digest,
                meta["nas_rel_path"],
                ts,
                source.name,
                meta["canonical_filename"],
                len(data),
                json.dumps({"capture_method": "legacy_migrate", "evidence_id": None, "upload_id": None}),
                meta["nas_rel_path"],
                STORAGE_ROOT_ID,
                ts,
            ),
        )
        source.unlink()
        migrated += 1
        deleted += 1
    if migrated or failed:
        conn.commit()
    return {
        "ok": failed == 0,
        "migrated": migrated,
        "failed": failed,
        "deleted_sources": deleted,
        "legacy_files": len(disk_files),
        "preserved": True,
    }


def active_role_ids(person_id: str | None, conn: sqlite3.Connection) -> set[str]:
    pid = (person_id or "").strip()
    if not pid:
        return set()
    rows = conn.execute(
        """
        SELECT DISTINCT pos.role_id
        FROM org_assignments a
        JOIN org_positions pos ON pos.position_id = a.position_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
          AND pos.status='ACTIVE'
        """,
        (pid,),
    ).fetchall()
    return {str(row[0]) for row in rows}


def accountant_must_deny(person_id: str | None, path: str, conn: sqlite3.Connection) -> bool:
    """Accountant-only people stay on GGV Finance. Other roles keep their own checks."""
    roles = active_role_ids(person_id, conn)
    if roles != {ROLE_EXTERNAL_ACCOUNTANT}:
        return False
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    if matches(raw):
        return False
    base = raw.rstrip("/") or "/"
    return base not in SHELL_CHROME_PATHS


def refuse_money(path: str) -> None:
    raise FinanceNotaError(
        "This screen does not pay, approve payment, or change bank details.",
        code="payment_refused",
        http_status=405,
        extra={"path": path, "money_movement": False},
    )


def dispatch(method: str, path: str, qs: dict[str, list[str]], body: dict | None, person_id: str | None) -> dict[str, Any]:
    raw = (path or "").split("?")[0]
    trimmed = raw.rstrip("/") or "/"
    if trimmed in PAGE_PATHS or raw in PAGE_PATHS:
        page_conn = _open_ready()
        try:
            require(person_id, "finance.nota.read", page_conn)
        finally:
            page_conn.close()
        return {"_html": True}
    if not trimmed.startswith("/api/ggv/finance"):
        raise FinanceNotaError("Not found.", code="not_found", http_status=404)
    for suffix in REFUSED_SUFFIXES:
        if trimmed.endswith(suffix):
            refuse_money(trimmed)
    rest = trimmed[len("/api/ggv/finance"):] or "/"
    body = body or {}
    from core import ggv_finance_invoice as _inv

    invoice_result = _inv.try_dispatch(method, rest, qs, body, person_id)
    if invoice_result is not None:
        return invoice_result
    if method == "GET" and rest in {"", "/"}:
        return overview(person_id)
    if method == "GET" and rest == "/overview":
        return overview(person_id)
    if method == "GET" and rest == "/notas":
        return list_notas(person_id)
    if method == "GET" and rest == "/vendors":
        return search_vendors(person_id, ((qs.get("q") or [""])[0]))
    if method == "GET" and rest in {"/history", "/search"}:
        return search_history(person_id, qs)
    if method == "GET" and rest == "/accountant":
        return accountant_desk(person_id)
    if method == "GET" and rest == "/export/month":
        return export_month_pack(person_id, qs)
    m_review = re.fullmatch(r"/notas/([^/]+)/review", rest)
    if m_review and method == "POST":
        return review_nota(person_id or "", m_review.group(1), body)
    m_nota = re.fullmatch(r"/notas/([^/]+)", rest)
    if m_nota and method == "GET":
        return get_nota(person_id, m_nota.group(1))
    m_vendor = re.fullmatch(r"/vendors/([^/]+)", rest)
    if m_vendor and method == "GET":
        return get_vendor(person_id, m_vendor.group(1))
    m_file = re.fullmatch(r"/files/([^/]+)", rest)
    if m_file and method == "GET":
        return file_bytes(person_id, m_file.group(1))
    m_upload = re.fullmatch(r"/uploads/([^/]+)", rest)
    if m_upload and method == "GET":
        own = _open_ready()
        try:
            require(person_id, "finance.nota.read", own)
            row = _upload_or_404(own, m_upload.group(1), person_id or "")
            return public_payload(
                {
                    "ok": True,
                    "upload_id": row["upload_id"],
                    "stage": row["stage"],
                    "stage_label": STAGE_LABEL.get(row["stage"], row["stage"]),
                    "failure_message": row["failure_message"],
                    "preserved": True,
                    "proposals": json.loads(row["proposals_json"] or "{}"),
                    "vendor_matches": json.loads(row["vendor_matches_json"] or "[]"),
                    "nota_id": row["nota_id"],
                }
            )
        finally:
            own.close()
    if method == "POST" and rest == "/uploads":
        return create_upload(person_id or "", list(body.get("files") or []))
    m_read = re.fullmatch(r"/uploads/([^/]+)/read", rest)
    if m_read and method == "POST":
        return read_upload(person_id or "", m_read.group(1))
    m_check = re.fullmatch(r"/uploads/([^/]+)/check-vendor", rest)
    if m_check and method == "POST":
        return check_vendor(person_id or "", m_check.group(1))
    if method == "POST" and rest == "/vendors":
        return create_vendor(person_id or "", body)
    m_vendor_edit = re.fullmatch(r"/vendors/([^/]+)", rest)
    if m_vendor_edit and method == "POST":
        return edit_vendor(person_id or "", m_vendor_edit.group(1), body)
    if method == "POST" and rest == "/notas":
        return save_nota(person_id or "", body)
    m_edit = re.fullmatch(r"/notas/([^/]+)", rest)
    if m_edit and method == "POST":
        return edit_nota(person_id or "", m_edit.group(1), body)
    m_submit = re.fullmatch(r"/notas/([^/]+)/submit", rest)
    if m_submit and method == "POST":
        return submit_nota(person_id or "", m_submit.group(1))
    m_bank = re.fullmatch(r"/vendors/([^/]+)/bank", rest)
    if m_bank:
        refuse_money(trimmed)
    raise FinanceNotaError("That action is not on this screen.", code="not_found", http_status=404)
