#!/usr/bin/env python3
"""obsidian_ops_mirror.py — one-way Obsidian mirror for Wolf operational events.

Read-only from Wolf canonical SQLite (content_library.sqlite, mode=ro) plus
proved BF run/result JSON files. Writes markdown into the Obsidian vault folder
10-Mirror/. Never mutates Wolf DB rows, never deletes or rewrites existing vault
notes (if a deterministic file already exists, it is skipped).

Usage:
  python3 scripts/ops/obsidian_ops_mirror.py
  python3 scripts/ops/obsidian_ops_mirror.py --dry-run
  python3 scripts/ops/obsidian_ops_mirror.py --mirror-dir /tmp/test-mirror
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_DB = ROOT / "catalog" / "content_library.sqlite"
DEFAULT_VAULT = Path("/Users/wolfterminal/WolfCommandSystem/WolfCommand")
DEFAULT_MIRROR_DIR = DEFAULT_VAULT / "10-Mirror"

BF_HISTORY_RUN = ROOT / "state/build-factory/runs/BF-c8050a817e81.json"
BF_HISTORY_RESULT = ROOT / "state/reliability/BZG-HISTORY-IMPORT-1-RESULT-2026-10-05.json"
BF_RECON_RESULT = ROOT / "state/reliability/BZG-BANK-RECON-1-RESULT-2026-10-05.json"
BF_EVIDENCE_RESULT = ROOT / "state/reliability/BZG-EVIDENCE-LINK-1-RESULT-2026-10-05.json"

DISCLAIMER = (
    "Mirror only. Not the source of truth. Wolf canonical database is authoritative."
)

PROVED_PETTY_IDS = ("PETTY-UMA-6D853EEAE0",)
PROVED_CLOSE_PREFIXES = (
    "VDC-8fd544e2",
    "VDC-470e741f",
    "VDC-64f5f529",
)
PROVED_BF_IDS = ("BF-c8050a817e81",)
PROVED_PACKS = (
    ("BZG-BANK-RECON-1", BF_RECON_RESULT),
    ("BZG-EVIDENCE-LINK-1", BF_EVIDENCE_RESULT),
)

ACCOUNT_DIGITS = re.compile(r"\d{4,}")
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),
)

MIRROR_DIR = DEFAULT_MIRROR_DIR


def configure_mirror_dir(path: Path | None) -> None:
    global MIRROR_DIR
    MIRROR_DIR = path or DEFAULT_MIRROR_DIR


def now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%d %H:%M:%S WITA")


def open_ro(db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def redact_account(text: str | None) -> str:
    if not text:
        return ""
    return ACCOUNT_DIGITS.sub("[REDACTED]", text)


def period_from_filename(name: str) -> str:
    m = re.search(r"(20\d{2}-\d{2}-\d{2})_(20\d{2}-\d{2}-\d{2})", name)
    if m:
        return f"{m.group(1)} to {m.group(2)}"
    m = re.search(r"_(20\d{2}-\d{2})\.(?:xls|csv|xlsx)$", name, re.I)
    if m:
        return m.group(1)
    m = re.search(r"(20\d{6})_(20\d{6})", name)
    if m:
        a, b = m.group(1), m.group(2)
        return f"{a[:4]}-{a[4:6]}-{a[6:]} to {b[:4]}-{b[4:6]}-{b[6:]}"
    return "period unknown from filename"


def write_note(path: Path, body: str, dry_run: bool) -> str:
    if path.exists():
        return "skip"
    if dry_run:
        return "would_write"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not body.startswith(DISCLAIMER):
        body = DISCLAIMER + "\n\n" + body
    path.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
    return "wrote"


def petty_balance(con: sqlite3.Connection, venue: str = "BZG-UMA") -> dict[str, Any]:
    row = con.execute(
        "SELECT opening_float FROM bzg_ops_petty_days WHERE venue=? AND business_date=?",
        (venue, "2026-10-02"),
    ).fetchone()
    opening = float(row[0]) if row else 0.0
    mov = con.execute(
        """
        SELECT COALESCE(SUM(
            CASE WHEN direction='IN' THEN amount
                 WHEN direction='OUT' THEN -amount
                 ELSE 0 END
        ), 0)
        FROM bzg_ops_petty_movements
        WHERE venue=? AND business_date >= '2026-10-02'
        """,
        (venue,),
    ).fetchone()[0]
    net = float(mov or 0)
    return {
        "opening_float": opening,
        "movement_net_from_2026_10_02": net,
        "amount_idr": opening + net,
        "venue": venue,
        "formula": (
            "opening_float(bzg_ops_petty_days @ 2026-10-02) + "
            "SUM(IN - OUT) movements since 2026-10-02"
        ),
    }


def mirror_petty(con: sqlite3.Connection, dry_run: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for mid in PROVED_PETTY_IDS:
        row = con.execute(
            "SELECT * FROM bzg_ops_petty_movements WHERE movement_id=?", (mid,)
        ).fetchone()
        if not row:
            out.append((mid, "missing_source"))
            continue
        d = dict(row)
        path = MIRROR_DIR / "petty" / f"{mid}.md"
        evidence_lines = []
        if d.get("evidence_id"):
            evidence_lines.append(f"- evidence_id: `{d['evidence_id']}`")
        if d.get("photo_evidence_id"):
            evidence_lines.append(f"- photo_evidence_id: `{d['photo_evidence_id']}`")
        if d.get("receipt_path"):
            evidence_lines.append(f"- receipt_path: `{d['receipt_path']}`")
        if not evidence_lines:
            evidence_lines.append("- (no evidence path/id on this row)")

        amount = d.get("amount")
        amount_s = f"Rp{amount:,.0f}" if isinstance(amount, (int, float)) else str(amount)
        body = "\n".join(
            [
                DISCLAIMER,
                "",
                f"# Petty movement `{mid}`",
                "",
                f"- mirrored_at: {now_wita()}",
                "- source_table: `bzg_ops_petty_movements`",
                f"- movement_id: `{mid}`",
                f"- venue: `{d.get('venue')}`",
                f"- outlet: {d.get('outlet') or '—'}",
                f"- business_date: `{d.get('business_date')}`",
                f"- direction: **{d.get('direction')}**",
                f"- amount: **{amount_s}** {d.get('currency') or ''}".rstrip(),
                f"- category: {d.get('category') or '—'}",
                f"- purpose: {d.get('purpose') or '—'}",
                f"- logged_by / actor: `{d.get('logged_by')}`",
                f"- created_at (UTC): `{d.get('created_at')}`",
                f"- transaction_time: `{d.get('transaction_time')}`",
                f"- approval_state: `{d.get('approval_state')}`",
                f"- receipt_status: `{d.get('receipt_status')}`",
                f"- proof_status: `{d.get('proof_status')}`",
                "",
                "## Evidence references (as stored)",
                *evidence_lines,
                "",
                "_This note is a copy. Do not edit Wolf rows from Obsidian._",
                "",
            ]
        )
        out.append((str(path), write_note(path, body, dry_run)))
    return out


def mirror_closes(con: sqlite3.Connection, dry_run: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for prefix in PROVED_CLOSE_PREFIXES:
        row = con.execute(
            "SELECT * FROM venue_daily_closes WHERE close_id LIKE ?",
            (prefix + "%",),
        ).fetchone()
        if not row:
            out.append((prefix, "missing_source"))
            continue
        d = dict(row)
        cid = d["close_id"]
        path = MIRROR_DIR / "daily-closes" / f"{cid}.md"
        declared = d.get("declared_cash_amount")
        declared_s = (
            "NULL"
            if declared is None
            else f"Rp{declared:,.0f}"
            if isinstance(declared, (int, float))
            else str(declared)
        )
        evidence_lines = []
        if d.get("declared_cash_evidence_id"):
            evidence_lines.append(
                f"- declared_cash_evidence_id: `{d['declared_cash_evidence_id']}`"
            )
        if d.get("resolve_evidence_id"):
            evidence_lines.append(f"- resolve_evidence_id: `{d['resolve_evidence_id']}`")
        if not evidence_lines:
            evidence_lines.append("- (no evidence id on this row)")

        body = "\n".join(
            [
                DISCLAIMER,
                "",
                f"# Daily close `{cid}`",
                "",
                f"- mirrored_at: {now_wita()}",
                "- source_table: `venue_daily_closes`",
                f"- close_id: `{cid}`",
                f"- business_date: `{d.get('business_date')}`",
                f"- state: **{d.get('state')}**",
                f"- outlet_id / venue_brand_id: `{d.get('outlet_id')}` / `{d.get('venue_brand_id')}`",
                f"- declared_cash_amount: **{declared_s}**",
                f"- variance_cash_amount: `{d.get('variance_cash_amount')}`",
                f"- submitted_by_person_id: `{d.get('submitted_by_person_id')}`",
                f"- created_at: `{d.get('created_at')}`",
                f"- updated_at: `{d.get('updated_at')}` (protected — mirror must not change source)",
                "",
                "## Evidence references (as stored)",
                *evidence_lines,
                "",
                "_Record mirror only. EXCEPTION / DATA_CAPTURED states are not mutated here._",
                "",
            ]
        )
        out.append((str(path), write_note(path, body, dry_run)))
    return out


def mirror_bf_import(con: sqlite3.Connection, dry_run: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for bfid in PROVED_BF_IDS:
        if not BF_HISTORY_RUN.exists() and not BF_HISTORY_RESULT.exists():
            out.append((bfid, "missing_source"))
            continue
        run = json.loads(BF_HISTORY_RUN.read_text()) if BF_HISTORY_RUN.exists() else {}
        result = (
            json.loads(BF_HISTORY_RESULT.read_text()) if BF_HISTORY_RESULT.exists() else {}
        )

        imported = result.get("imported") or {}
        source_counts = result.get("source_counts") or {}
        bank = result.get("bank") or {}
        matched = con.execute(
            "SELECT COUNT(*) FROM bzg_bank_transactions WHERE matched_ledger_source_id IS NOT NULL"
        ).fetchone()[0]
        unmatched = con.execute(
            """
            SELECT COUNT(*) FROM bzg_bank_transactions
            WHERE recon_status='UNMATCHED' OR recon_status IS NULL
            """
        ).fetchone()[0]
        imports = con.execute(
            """
            SELECT bank_label, original_filename, txn_count, parse_status
            FROM bzg_bank_statement_imports ORDER BY original_filename
            """
        ).fetchall()

        bank_lines = []
        for r in imports:
            label, fname, txn_count, parse_status = r
            period = period_from_filename(fname or "")
            safe_name = redact_account(fname or "")
            bank_lines.append(
                f"- {label}: **{safe_name}** · period **{period}** · "
                f"txns={txn_count} · parse={parse_status}"
            )
        if not bank_lines:
            bank_lines = ["- (no bank import rows)"]

        po = imported.get("purchase_orders")
        po_src = source_counts.get("pr_orders")
        lines = imported.get("po_lines")
        lines_src = source_counts.get("pr_order_lines")
        gr_lines = imported.get("gr_lines")
        gr_src = source_counts.get("pr_receipt_lines")
        notas = imported.get("supplier_bills")
        notas_src = source_counts.get("ledger")
        petty_hist = imported.get("petty_cash")
        evidence_q = result.get("evidence_unlinked", imported.get("evidence_unlinked_queued"))

        path = MIRROR_DIR / "imports" / f"{bfid}.md"
        body = "\n".join(
            [
                DISCLAIMER,
                "",
                f"# BZG history import `{bfid}`",
                "",
                f"- mirrored_at: {now_wita()}",
                f"- run_id: `{bfid}`",
                f"- slice: `{run.get('slice') or result.get('pack') or 'BZG-HISTORY-IMPORT-1'}`",
                f"- run_status: `{run.get('status') or result.get('status')}`",
                f"- final_state: `{run.get('final_state')}`",
                f"- finished_at: `{result.get('finished_at')}`",
                f"- source_db: `{result.get('source_db')}`",
                f"- target_db: `{result.get('target_db')}`",
                "",
                "## Summary counts (from proved import result — do not claim complete)",
                f"- PO: **{po}/{po_src}**",
                f"- PO lines: **{lines}/{lines_src}**",
                f"- Receipt lines (GR lines): **{gr_lines}/{gr_src}**",
                f"- Notas / supplier bills: **{notas}/{notas_src}**",
                f"- Petty historical imported: **{petty_hist}**",
                f"- Evidence queue unlinked: **{evidence_q}**",
                f"- Bank: **{bank.get('files_on_disk') or imported.get('bank_imports')} files** / "
                f"**{bank.get('transactions') or imported.get('bank_transactions')} txns** / "
                f"**{matched} matched** (live query; UNMATCHED={unmatched})",
                "",
                "## Bank statement coverage (filename redacted; period only)",
                *bank_lines,
                "",
                "## Explicit gaps (do not invent)",
                "- Sep 2026 bank: **MISSING SOURCE** (not on disk / not imported).",
                "- Oct 2026 bank: **MISSING SOURCE** (not on disk / not imported).",
                "- staff_ready / human_commissioned / zayen_ready: false.",
                "",
                f"_Source files (read-only): `{BF_HISTORY_RUN}` · `{BF_HISTORY_RESULT}`_",
                "",
            ]
        )
        out.append((str(path), write_note(path, body, dry_run)))
    return out


def mirror_reconciliation_pack(
    con: sqlite3.Connection, pack: str, result_path: Path, dry_run: bool
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not result_path.exists():
        out.append((pack, "missing_source"))
        return out

    result = json.loads(result_path.read_text())
    apply = result.get("apply_result") or result.get("summary") or {}
    state_counts = apply.get("state_counts") or {}
    live_counts = dict(
        con.execute(
            "SELECT COALESCE(recon_status, 'NULL'), COUNT(*) "
            "FROM bzg_bank_transactions GROUP BY recon_status"
        ).fetchall()
    )
    matched_ids = apply.get("matched_txn_ids") or result.get("matched_txn_ids") or []
    id_lines = [f"- `{tid}`" for tid in matched_ids[:20]]
    if len(matched_ids) > 20:
        id_lines.append(f"- … and {len(matched_ids) - 20} more (see Wolf DB)")

    path = MIRROR_DIR / "reconciliations" / f"{pack}.md"
    body = "\n".join(
        [
            DISCLAIMER,
            "",
            f"# Bank reconciliation `{pack}`",
            "",
            f"- mirrored_at: {now_wita()}",
            f"- pack: `{pack}`",
            f"- finished_at: `{result.get('finished_at')}`",
            f"- status: `{result.get('status')}`",
            f"- read_only: `{apply.get('read_only', True)}`",
            f"- auto_reconciled: `{apply.get('auto_reconciled', False)}`",
            f"- transaction_count: `{apply.get('transaction_count') or result.get('transaction_count')}`",
            "",
            "## State counts (proved result JSON)",
            *[
                f"- **{state}**: {count}"
                for state, count in sorted(state_counts.items())
            ],
            "",
            "## Live recon_status counts (read-only query; reference only)",
            *[
                f"- **{state}**: {count}"
                for state, count in sorted(live_counts.items())
            ],
            "",
            "## Matched transaction ids (reference list — not a ledger)",
            *(id_lines or ["- (none listed in result)"]),
            "",
            "_Reconciliation states are stored in Wolf DB. This note does not compute balances._",
            f"_Source: `{result_path}`_",
            "",
        ]
    )
    out.append((str(path), write_note(path, body, dry_run)))
    return out


def mirror_evidence_links(con: sqlite3.Connection, dry_run: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    rows = con.execute(
        """
        SELECT link_id, queue_id, file_path, file_kind, record_type, record_id,
               match_rule, confidence, linked_at
        FROM bzg_ops_evidence_links ORDER BY link_id
        """
    ).fetchall()
    for row in rows:
        d = dict(row)
        lid = d["link_id"]
        path = MIRROR_DIR / "evidence-links" / f"{lid}.md"
        body = "\n".join(
            [
                DISCLAIMER,
                "",
                f"# Evidence link `{lid}`",
                "",
                f"- mirrored_at: {now_wita()}",
                "- source_table: `bzg_ops_evidence_links`",
                f"- link_id: `{lid}`",
                f"- queue_id: `{d.get('queue_id')}`",
                f"- file_kind: `{d.get('file_kind')}`",
                f"- record_type: `{d.get('record_type')}`",
                f"- record_id: `{d.get('record_id')}`",
                f"- match_rule: `{d.get('match_rule')}`",
                f"- confidence: `{d.get('confidence')}`",
                f"- linked_at: `{d.get('linked_at')}`",
                "",
                "## Evidence reference (path as stored — not copied)",
                f"- file_path: `{d.get('file_path')}`",
                "",
                "_Reference only. File content stays in Wolf evidence store._",
                "",
            ]
        )
        out.append((str(path), write_note(path, body, dry_run)))
    return out


def mirror_decisions(con: sqlite3.Connection, dry_run: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    rows = con.execute(
        """
        SELECT approval_decision_id, approval_request_id, decision,
               decided_by_person_id, reason, decided_at, authority_allowed,
               authority_reason
        FROM core_approval_decisions ORDER BY decided_at
        """
    ).fetchall()
    for row in rows:
        d = dict(row)
        did = d["approval_decision_id"]
        path = MIRROR_DIR / "decisions" / f"{did}.md"
        body = "\n".join(
            [
                DISCLAIMER,
                "",
                f"# Approval decision `{did}`",
                "",
                f"- mirrored_at: {now_wita()}",
                "- source_table: `core_approval_decisions`",
                f"- approval_decision_id: `{did}`",
                f"- approval_request_id: `{d.get('approval_request_id')}`",
                f"- decision: **{d.get('decision')}**",
                f"- decided_by_person_id: `{d.get('decided_by_person_id')}`",
                f"- decided_at: `{d.get('decided_at')}`",
                f"- authority_allowed: `{d.get('authority_allowed')}`",
                f"- reason: {d.get('reason') or '—'}",
                f"- authority_reason: {d.get('authority_reason') or '—'}",
                "",
                "_Institutional decision record. Wolf DB is authoritative._",
                "",
            ]
        )
        out.append((str(path), write_note(path, body, dry_run)))
    return out


def mirror_exceptions(con: sqlite3.Connection, dry_run: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    rows = con.execute(
        """
        SELECT exception_id, entity_id, governed_object_type, governed_object_id,
               control_type, control_reference, requested_by_person_id,
               authorised_by_person_id, reason, evidence_id, effective_from
        FROM core_governance_exceptions ORDER BY effective_from
        """
    ).fetchall()
    for row in rows:
        d = dict(row)
        eid = d["exception_id"]
        path = MIRROR_DIR / "exceptions" / f"{eid}.md"
        body = "\n".join(
            [
                DISCLAIMER,
                "",
                f"# Governance exception `{eid}`",
                "",
                f"- mirrored_at: {now_wita()}",
                "- source_table: `core_governance_exceptions`",
                f"- exception_id: `{eid}`",
                f"- entity_id: `{d.get('entity_id')}`",
                f"- governed_object_type: `{d.get('governed_object_type')}`",
                f"- governed_object_id: `{d.get('governed_object_id')}`",
                f"- control_type: `{d.get('control_type')}`",
                f"- control_reference: `{d.get('control_reference')}`",
                f"- requested_by_person_id: `{d.get('requested_by_person_id')}`",
                f"- authorised_by_person_id: `{d.get('authorised_by_person_id') or '—'}`",
                f"- effective_from: `{d.get('effective_from')}`",
                f"- evidence_id: `{d.get('evidence_id') or '—'}`",
                f"- reason: {d.get('reason') or '—'}",
                "",
                "_Governance exception mirror. Does not grant new authority._",
                "",
            ]
        )
        out.append((str(path), write_note(path, body, dry_run)))
    return out


def mirror_evidence_pack_summary(result_path: Path, dry_run: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not result_path.exists():
        out.append(("BZG-EVIDENCE-LINK-1", "missing_source"))
        return out
    result = json.loads(result_path.read_text())
    apply = result.get("apply_result") or {}
    counts = result.get("counts_after") or result.get("counts_before") or {}
    pack = result.get("pack") or "BZG-EVIDENCE-LINK-1"
    path = MIRROR_DIR / "evidence-links" / f"{pack}-SUMMARY.md"
    body = "\n".join(
        [
            DISCLAIMER,
            "",
            f"# Evidence link pack `{pack}`",
            "",
            f"- mirrored_at: {now_wita()}",
            f"- pack: `{pack}`",
            f"- finished_at: `{result.get('finished_at')}`",
            f"- status: `{result.get('status')}`",
            f"- linked: `{counts.get('linked')}`",
            f"- unlinked: `{counts.get('unlinked')}`",
            f"- needs_reconciliation: `{counts.get('needs_reconciliation')}`",
            f"- auto_linked: `{apply.get('auto_linked', 0)}`",
            "",
            "_Per-link detail notes live alongside this summary. No guessing._",
            f"_Source: `{result_path}`_",
            "",
        ]
    )
    out.append((str(path), write_note(path, body, dry_run)))
    return out


def write_folder_readme(dry_run: bool) -> tuple[str, str]:
    path = MIRROR_DIR / "README.md"
    body = "\n".join(
        [
            DISCLAIMER,
            "",
            "# 10-Mirror — Wolf operational event copies",
            "",
            "One-way mirror from Wolf canonical `content_library.sqlite` (and proved BF result JSON).",
            "Generated by `beta-os/scripts/ops/obsidian_ops_mirror.py`.",
            "",
            "- Append-only: existing note filenames are never rewritten.",
            "- Deterministic filenames from source ids.",
            "- Secrets / full bank account numbers are not copied.",
            "- Subfolders: petty, daily-closes, imports, reconciliations, evidence-links, decisions, exceptions.",
            "",
            f"Last generator run consideration: {now_wita()}",
            "",
        ]
    )
    return str(path), write_note(path, body, dry_run)


def protected_close_checksums(con: sqlite3.Connection) -> dict[str, str]:
    out: dict[str, str] = {}
    for prefix in PROVED_CLOSE_PREFIXES:
        row = con.execute(
            "SELECT close_id, updated_at FROM venue_daily_closes WHERE close_id LIKE ?",
            (prefix + "%",),
        ).fetchone()
        if row:
            out[row[0]] = row[1]
    return out


def run_mirror(*, dry_run: bool = False) -> dict[str, Any]:
    if not CANONICAL_DB.exists():
        raise FileNotFoundError(f"canonical DB missing: {CANONICAL_DB}")

    con = open_ro(CANONICAL_DB)
    before_closes = protected_close_checksums(con)
    before_petty = dict(
        con.execute(
            "SELECT movement_id, amount, created_at FROM bzg_ops_petty_movements WHERE movement_id=?",
            ("PETTY-UMA-6D853EEAE0",),
        ).fetchone()
    )
    bal = petty_balance(con)

    results: list[tuple[str, str]] = []
    results.append(write_folder_readme(dry_run))
    results.extend(mirror_petty(con, dry_run))
    results.extend(mirror_closes(con, dry_run))
    results.extend(mirror_bf_import(con, dry_run))
    for pack, result_path in PROVED_PACKS:
        if pack == "BZG-BANK-RECON-1":
            results.extend(mirror_reconciliation_pack(con, pack, result_path, dry_run))
        elif pack == "BZG-EVIDENCE-LINK-1":
            results.extend(mirror_evidence_pack_summary(result_path, dry_run))
    results.extend(mirror_evidence_links(con, dry_run))
    results.extend(mirror_decisions(con, dry_run))
    results.extend(mirror_exceptions(con, dry_run))

    after_closes = protected_close_checksums(con)
    after_petty = dict(
        con.execute(
            "SELECT movement_id, amount, created_at FROM bzg_ops_petty_movements WHERE movement_id=?",
            ("PETTY-UMA-6D853EEAE0",),
        ).fetchone()
    )
    bal_after = petty_balance(con)
    con.close()

    return {
        "dry_run": dry_run,
        "mirror_dir": str(MIRROR_DIR),
        "actions": [{"path": p, "action": a} for p, a in results],
        "petty_balance_idr": bal_after["amount_idr"],
        "petty_balance_unchanged": bal == bal_after,
        "protected_closes_before": before_closes,
        "protected_closes_after": after_closes,
        "protected_closes_unchanged": before_closes == after_closes,
        "proved_petty_row_unchanged": before_petty == after_petty,
        "beta_os_db_writes": False,
        "prod_8787_touched": False,
    }


def scan_mirror_for_secrets(mirror_dir: Path) -> list[str]:
    """Flag credential leaks and unredacted bank account labels only."""
    bank_label = re.compile(
        r"(?i)(?:mandiri|bni|bri)[_-][\d]{8,}|(?:BNI|Mandiri|BRI)-[\d]{8,}"
    )
    issues: list[str] = []
    for md in mirror_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                issues.append(f"{md}: secret pattern {pat.pattern}")
        for line in text.splitlines():
            if "[REDACTED]" in line:
                continue
            if bank_label.search(line):
                issues.append(f"{md}: unredacted bank account label: {line[:80]}")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report actions without writing")
    ap.add_argument(
        "--mirror-dir",
        type=Path,
        default=None,
        help="Override vault mirror output directory (tests only)",
    )
    args = ap.parse_args()
    configure_mirror_dir(args.mirror_dir)

    try:
        payload = run_mirror(dry_run=args.dry_run)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 2

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
