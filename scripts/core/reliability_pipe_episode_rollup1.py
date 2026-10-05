#!/usr/bin/env python3
"""RELIABILITY-PIPE-EPISODE-ROLLUP-1 — Mac pipe flap episode rollup (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave10 pack
RELIABILITY-PIPE-EPISODE-ROLLUP-1 (armed 2026-09-30 after HR-DEFERRED-HOLD-STAMP-1
PASS_VERIFIED 135/0).

Rolls up Wave7–10 Mac local-exec pipe flaps from CLASSIFICATION-LOG pipe_flaps
plus prior PIPE-RELIABILITY-AUTO-1 episodes into an evidence-only rollup board.
Live probe stays GREEN/DOWN/UNKNOWN via pipe_reliability_auto1 — never invents
uptime %. Ceiling BUILT only. Preserves PIPE-RELIABILITY-AUTO-1 + RELIABILITY-1.
staff_ready / human_commissioned stay false.
Does not auto-chain WAVE11-SYNTH-CONTINUE / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CLASSIFICATION_LOG = (
    BETA_ROOT / "state" / "final-completion" / "CLASSIFICATION-LOG-20260930.json"
)
PIPE_EPISODES_PATH = (
    BETA_ROOT
    / "state"
    / "final-completion"
    / "packs"
    / "PIPE-RELIABILITY-AUTO-1-EPISODES.json"
)
ROLLUP_EPISODES_PATH = (
    BETA_ROOT
    / "state"
    / "final-completion"
    / "packs"
    / "RELIABILITY-PIPE-EPISODE-ROLLUP-1-EPISODES.json"
)

PACK_ID = "RELIABILITY-PIPE-EPISODE-ROLLUP-1"
SCHEMA_ID = "wolf.reliability-pipe-episode-rollup-1.v1"
BOUND = "beta-pipe-episode-rollup-safe"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "INTERNALLY_SOLVABLE"
CLOSES_TOWARD = ("IL-R8", "reliability pipe", "Mac local-exec", "pipe flaps")
PRESERVED_PACKS = ("PIPE-RELIABILITY-AUTO-1", "RELIABILITY-1")
NEXT_PACK = "WAVE11-SYNTH-CONTINUE"
EXPECTED_MIN_EPISODES = 10  # overnight + 07:28 observed + 8 classification flaps

PAGE_PATHS = frozenset(
    {
        "/ops/reliability-pipe-episode-rollup-1",
        "/ops/reliability-pipe-episode-rollup-1/",
        "/ops/reliability-pipe-episode-rollup",
        "/ops/reliability-pipe-episode-rollup/",
        "/ops/pipe-episode-rollup-1",
        "/ops/pipe-episode-rollup-1/",
        "/ops/pipe-episode-rollup",
        "/ops/pipe-episode-rollup/",
        "/reliability-pipe-episode-rollup-1",
        "/reliability-pipe-episode-rollup-1/",
        "/reliability-pipe-episode-rollup-1.html",
        "/dashboards/reliability-pipe-episode-rollup-1.html",
    }
)
API_PATH = "/api/ops/reliability-pipe-episode-rollup-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/reliability-pipe-episode-rollup",
        "/api/ops/pipe-episode-rollup-1",
        "/api/ops/pipe-episode-rollup",
    }
)

STATUS_VOCAB = frozenset({"GREEN", "DOWN", "UNKNOWN"})


class ReliabilityPipeEpisodeRollup1Error(ValueError):
    """Fail closed. Does not invent uptime or paint pipe GREEN falsely."""

    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/")
    return trimmed in API_PATHS or raw in API_PATHS


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "fake_uptime": False,
        "invented_uptime": False,
        "fake_pipe_up": False,
        "painted_green": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "prod_probe_read_only": True,
        "no_push": True,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "closes_toward": list(CLOSES_TOWARD),
        "proven_claimed": False,
        "ready_claimed": False,
        "complete_claimed": False,
        "pipe_reliability_auto1_preserved": True,
        "reliability1_preserved": True,
        "next_pack_for_parent_only": NEXT_PACK,
        "cursor_did_not_auto_start_next": True,
        "exit_report_forbidden": True,
        "headchef_forbidden": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "status_vocab": "GREEN|DOWN|UNKNOWN",
        "episodes_are_evidence_only": True,
    }


def refuse_fake_uptime(_body: dict | None = None) -> None:
    raise ReliabilityPipeEpisodeRollup1Error(
        "Uptime / fake GREEN cannot be invented on RELIABILITY-PIPE-EPISODE-ROLLUP-1.",
        code="uptime_refused",
    )


def refuse_fake_pipe_up(_body: dict | None = None) -> None:
    raise ReliabilityPipeEpisodeRollup1Error(
        "Fake pipe-up refused. Live probe stays GREEN/DOWN/UNKNOWN only.",
        code="fake_pipe_up_refused",
    )


def refuse_prod_mutate(_body: dict | None = None) -> None:
    raise ReliabilityPipeEpisodeRollup1Error(
        "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
        code="prod_mutate_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise ReliabilityPipeEpisodeRollup1Error(
            "Write payload refused.", code="write_refused"
        )
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "uptime",
            "uptime-pct",
            "uptime-percent",
            "fake-uptime",
            "invent-uptime",
            "invent-up",
            "green",
            "force-green",
            "paint-green",
        }:
            refuse_fake_uptime(payload)
        if token in {
            "fake-pipe-up",
            "force-up",
            "force-pipe-up",
            "paint-pipe-up",
            "invent-pipe-up",
        }:
            refuse_fake_pipe_up(payload)
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "kill",
            "restart-prod",
            "8787",
            "15975",
        }:
            refuse_prod_mutate(payload)
        if token in {"staff-ready", "human-commissioned", "proven", "ready", "complete"}:
            raise ReliabilityPipeEpisodeRollup1Error(
                "Commissioning flags / PROVEN / READY / COMPLETE are refused.",
                code="ready_refused",
            )
    raise ReliabilityPipeEpisodeRollup1Error(
        "RELIABILITY-PIPE-EPISODE-ROLLUP-1 is a read-only evidence board. Writes refused.",
        code="write_refused",
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _slug_at(at_wita: str) -> str:
    digits = re.sub(r"[^0-9]", "", at_wita or "")
    # Prefer HHMM from WITA timestamp when present
    if len(digits) >= 12:
        return digits[8:12]
    if len(digits) >= 4:
        return digits[-4:]
    return digits or "xxxx"


def _wave_for_during(during: str | None) -> str:
    text = (during or "").upper()
    if any(
        tok in text
        for tok in (
            "BACKUP",
            "PIPE-RELIABILITY",
            "METRICOOL",
            "ESB-SETTLEMENT",
            "SOP-CATALOG",
            "FIN-BANK",
            "POST PIPE",
        )
    ):
        return "Wave7"
    if any(
        tok in text
        for tok in (
            "FIN-TAX",
            "INV-CASH",
            "CRM-PIPELINE",
            "CONTENT-PUBLISH",
            "OCCUPANCY",
            "STAFF-ACCESS",
            "APPROVALS",
            "WEEKLY-CASH",
            "CONNECTOR-HEALTH",
        )
    ):
        return "Wave8-9"
    if any(
        tok in text
        for tok in (
            "OWNER-DASH",
            "ATRIUM",
            "HR-DEFERRED",
            "WAVE10",
        )
    ):
        return "Wave10"
    return "Wave7-10"


def _pin_honesty(ep: dict[str, Any]) -> dict[str, Any]:
    out = dict(ep)
    out["uptime_pct"] = None
    out["invented_uptime"] = False
    out["fake_pipe_up"] = False
    return out


def load_classification_flaps() -> list[dict[str, Any]]:
    log = _read_json(CLASSIFICATION_LOG) or {}
    rows: list[dict[str, Any]] = []
    observed = log.get("pipe_flap_observed")
    if isinstance(observed, dict) and observed.get("at_wita"):
        at = str(observed["at_wita"])
        rows.append(
            _pin_honesty(
                {
                    "id": f"ep-20260930-{_slug_at(at)}-flap-observed",
                    "at_wita": at,
                    "at_wita_end": None,
                    "from_state": "PIPE_OK",
                    "to_state": "PIPE_OK",
                    "flap": True,
                    "during": "unpark / early Wave7",
                    "wave": "Wave7",
                    "hostname_proven": "Wolfs-Mac-Studio",
                    "recovered": True,
                    "source": "CLASSIFICATION-LOG#pipe_flap_observed",
                    "evidence": [
                        "state/final-completion/CLASSIFICATION-LOG-20260930.json#pipe_flap_observed",
                    ],
                    "notes": str(
                        observed.get("note")
                        or "Brief unreachable then PIPE_OK — evidence stamp only."
                    ),
                }
            )
        )
    flaps = log.get("pipe_flaps") or []
    if isinstance(flaps, list):
        for raw in flaps:
            if not isinstance(raw, dict) or not raw.get("at_wita"):
                continue
            at = str(raw["at_wita"])
            during = raw.get("during")
            recovered_at = raw.get("recovered_at")
            rows.append(
                _pin_honesty(
                    {
                        "id": f"ep-20260930-{_slug_at(at)}-flap",
                        "at_wita": at,
                        "at_wita_end": recovered_at,
                        "from_state": "PIPE_OK",
                        "to_state": "PIPE_OK",
                        "flap": True,
                        "during": during,
                        "wave": _wave_for_during(str(during) if during else None),
                        "hostname_proven": "Wolfs-Mac-Studio",
                        "recovered": bool(raw.get("recovered", True)),
                        "source": "CLASSIFICATION-LOG#pipe_flaps",
                        "evidence": [
                            "state/final-completion/CLASSIFICATION-LOG-20260930.json#pipe_flaps",
                        ],
                        "notes": (
                            f"Flap during {during or 'ops babysit'} — recovered PIPE_OK. "
                            "Evidence stamp only; no uptime % invented."
                        ),
                    }
                )
            )
    return rows


def load_pipe_auto_episodes() -> list[dict[str, Any]]:
    data = _read_json(PIPE_EPISODES_PATH) or {}
    eps = data.get("episodes") or []
    if not isinstance(eps, list) or not eps:
        # Fall back to canon via module if stamp missing
        try:
            from core import pipe_reliability_auto1 as _pipe

            eps = list(_pipe.CANON_EPISODES)
        except Exception:  # noqa: BLE001
            eps = []
    out: list[dict[str, Any]] = []
    for ep in eps:
        if not isinstance(ep, dict):
            continue
        row = _pin_honesty(ep)
        row.setdefault("source", "PIPE-RELIABILITY-AUTO-1-EPISODES")
        row.setdefault("wave", "Wave7")
        out.append(row)
    return out


def merge_episodes() -> list[dict[str, Any]]:
    """Merge PIPE-AUTO episodes + classification flaps; dedupe by at_wita."""
    by_at: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def _ingest(ep: dict[str, Any], *, prefer_existing: bool = False) -> None:
        at = str(ep.get("at_wita") or "").strip()
        if not at:
            return
        if at in by_at:
            if prefer_existing:
                return
            # Enrich existing with flap/wave fields when missing
            cur = by_at[at]
            for key in ("during", "wave", "recovered", "recovered_at", "flap", "source"):
                if cur.get(key) in (None, "", False) and ep.get(key) not in (None, ""):
                    cur[key] = ep[key]
            # Merge evidence lists
            ev = list(cur.get("evidence") or [])
            for item in ep.get("evidence") or []:
                if item not in ev:
                    ev.append(item)
            cur["evidence"] = ev
            by_at[at] = _pin_honesty(cur)
            return
        by_at[at] = _pin_honesty(ep)
        order.append(at)

    # Prefer richer PIPE-AUTO overnight / early stamps first
    for ep in load_pipe_auto_episodes():
        _ingest(ep)
    for ep in load_classification_flaps():
        _ingest(ep)

    merged = [by_at[k] for k in sorted(order)]
    return merged


def ensure_rollup_stamped() -> dict[str, Any]:
    episodes = merge_episodes()
    payload = {
        "pack": PACK_ID,
        "schema": "wolf.reliability-pipe-episode-rollup-1.episodes.v1",
        "stamped_at_wita": _now_wita(),
        "honesty": {
            "uptime_pct": None,
            "invented_uptime": False,
            "fake_pipe_up": False,
            "note": "Episodes are evidence stamps only — not continuous uptime.",
        },
        "sources": [
            "state/final-completion/CLASSIFICATION-LOG-20260930.json#pipe_flaps",
            "state/final-completion/CLASSIFICATION-LOG-20260930.json#pipe_flap_observed",
            "state/final-completion/packs/PIPE-RELIABILITY-AUTO-1-EPISODES.json",
        ],
        "overnight_transition": {
            "from": "PARKED_MAC_PIPE",
            "to": "UNPARKED_PIPE_OK",
            "date": "2026-09-30",
            "approx_wita": "07:23",
            "hostname_proven": "Wolfs-Mac-Studio",
        },
        "wave_span": "Wave7-10",
        "episodes": episodes,
        "episode_count": len(episodes),
        "flap_count": sum(1 for e in episodes if e.get("flap")),
        "staff_ready": False,
        "human_commissioned": False,
        "classification": CLASSIFICATION,
        "ceiling": CEILING,
    }
    ROLLUP_EPISODES_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROLLUP_EPISODES_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return payload


def load_rollup_episodes() -> dict[str, Any]:
    if not ROLLUP_EPISODES_PATH.is_file():
        return ensure_rollup_stamped()
    try:
        data = json.loads(ROLLUP_EPISODES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ensure_rollup_stamped()
    if not isinstance(data, dict) or not data.get("episodes"):
        return ensure_rollup_stamped()
    # Re-merge if classification log grew past stamped count
    live = merge_episodes()
    stamped_count = len(data.get("episodes") or [])
    if len(live) > stamped_count:
        return ensure_rollup_stamped()
    data["honesty"] = {
        "uptime_pct": None,
        "invented_uptime": False,
        "fake_pipe_up": False,
        "note": "Episodes are evidence stamps only — not continuous uptime.",
    }
    for ep in data.get("episodes") or []:
        if isinstance(ep, dict):
            ep["uptime_pct"] = None
            ep["invented_uptime"] = False
            ep["fake_pipe_up"] = False
    return data


def live_probe() -> dict[str, Any]:
    """Delegate to PIPE-RELIABILITY-AUTO-1 probe — never invent GREEN/uptime."""
    from core import pipe_reliability_auto1 as _pipe

    pipe = _pipe.probe_mac_pipe()
    pipe["uptime_pct"] = None
    pipe["uptime_invented"] = False
    pipe["painted_green"] = False
    pipe["fake_pipe_up"] = False
    return pipe


def pipe_is_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    if pack.get("fake_uptime") is True or pack.get("invented_uptime") is True:
        return False
    if pack.get("fake_pipe_up") is True:
        return False
    pipe = pack.get("mac_pipe") if isinstance(pack.get("mac_pipe"), dict) else pack
    if not isinstance(pipe, dict):
        return False
    if pipe.get("uptime_pct") is not None or pipe.get("uptime_invented") is True:
        return False
    if pipe.get("painted_green") is True or pipe.get("fake_pipe_up") is True:
        return False
    status = pipe.get("status")
    if status not in STATUS_VOCAB:
        return False
    if status == "GREEN" and not pipe.get("hostname_match"):
        return False
    if status == "GREEN" and not pipe.get("beta_root_present"):
        return False
    for ep in pack.get("episodes") or []:
        if isinstance(ep, dict) and (
            ep.get("uptime_pct") is not None or ep.get("invented_uptime") is True
        ):
            return False
    return True


def build_board() -> dict[str, Any]:
    """Public rollup board. Auth gating is caller's responsibility."""
    stamped = ensure_rollup_stamped()
    pipe = live_probe()
    flags = honesty_flags()
    episodes = list(stamped.get("episodes") or [])
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": pipe.get("last_probe_at") or _now_wita(),
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "fake_uptime": False,
        "invented_uptime": False,
        "fake_pipe_up": False,
        "painted_green": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "closes_toward": list(CLOSES_TOWARD),
        "mac_pipe": pipe,
        "status": pipe.get("status"),
        "last_probe_at": pipe.get("last_probe_at"),
        "episodes": episodes,
        "episode_count": len(episodes),
        "flap_count": int(stamped.get("flap_count") or 0),
        "wave_span": stamped.get("wave_span") or "Wave7-10",
        "overnight_transition": stamped.get("overnight_transition"),
        "sources": list(stamped.get("sources") or []),
        "honesty": {
            "uptime_policy": "null_never_invent",
            "status_vocab": "GREEN|DOWN|UNKNOWN",
            "probe": "hostname+date",
            "prod_probe": "read_only",
            "episodes_are_evidence_only": True,
            "roll_up_only": True,
        },
        "preserved_packs": list(PRESERVED_PACKS),
        "next_pack_for_parent_only": NEXT_PACK,
        "cursor_did_not_auto_start_next": True,
        "exit_report_forbidden": True,
        "headchef_forbidden": True,
        **{
            k: flags[k]
            for k in (
                "operating_adoption",
                "proven_claimed",
                "ready_claimed",
                "complete_claimed",
                "pipe_reliability_auto1_preserved",
                "reliability1_preserved",
                "no_push",
            )
        },
    }


def public_payload() -> dict[str, Any]:
    return build_board()
