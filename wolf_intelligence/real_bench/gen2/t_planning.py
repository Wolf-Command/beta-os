"""Gen-2 PLANNING: resource- and governance-constrained commissioning plan with an exhaustive optimum solver
and a programmatic schedule validator."""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

from .common2 import extract_json, governance, json_only, norm, result

START = dt.date(2026, 10, 12)  # Monday
HORIZON = 40
BLACKOUT = {dt.date(2026, 10, 22), dt.date(2026, 10, 23)}
UNAVAIL = {"Ketut": {dt.date(2026, 10, 14)}, "Joko": {dt.date(2026, 10, 17), dt.date(2026, 10, 19)},
           "Sari": set(), "Bayu": {dt.date(2026, 10, 13), dt.date(2026, 10, 14)},
           "Owner": {dt.date(2026, 10, 15), dt.date(2026, 10, 16)}}
TECHS = ("Ketut", "Joko")
FIN = ("Sari", "Bayu")
# task: (duration, deps, resource kind)
TASKS = {"A": (1, (), "tech1"), "B": (2, ("A",), "tech1"), "C": (1, ("A",), "none"), "D": (1, ("C",), "fin"),
         "E": (1, ("C",), "fin"), "F": (1, ("D", "E"), "owner"), "G": (3, ("F",), "none"), "H": (2, ("B", "G"), "tech2"),
         "I": (1, ("H",), "tech1"), "J": (1, ("F", "I"), "sari")}
ORDER = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
GATES = ["D", "E", "F", "I", "J"]


def working(d: dt.date) -> bool:
    return d.weekday() != 6 and d not in BLACKOUT


DAYS = [START + dt.timedelta(i) for i in range(HORIZON)]
WDAYS = [d for d in DAYS if working(d)]


def day_ok(task: str, d: dt.date, owner_sat: bool) -> bool:
    if not working(d):
        return False
    kind = TASKS[task][2]
    if kind == "owner":
        return d not in UNAVAIL["Owner"] and (d.weekday() <= 4 or (owner_sat and d.weekday() == 5))
    if kind == "sari":
        return d.weekday() <= 3 and d not in UNAVAIL["Sari"]
    return True


def solve(owner_sat: bool = False) -> tuple[dt.date, dict]:
    best = [None, None]

    def span(start_idx: int, dur: int) -> list[int] | None:
        if start_idx + dur > len(WDAYS):
            return None
        return list(range(start_idx, start_idx + dur))

    def dfs(i: int, sched: dict, tech_busy: dict, fin_used: dict):
        if i == len(ORDER):
            end = WDAYS[sched["J"][0][-1]]
            if best[0] is None or end < best[0]:
                best[0], best[1] = end, {k: ([WDAYS[x] for x in v[0]], v[1]) for k, v in sched.items()}
            return
        t = ORDER[i]
        dur, deps, kind = TASKS[t]
        earliest = max([sched[p][0][-1] + 1 for p in deps], default=0)
        for s in range(earliest, len(WDAYS)):
            if best[0] is not None and WDAYS[min(s + dur - 1, len(WDAYS) - 1)] >= best[0]:
                break
            idx = span(s, dur)
            if idx is None:
                break
            if not all(day_ok(t, WDAYS[x], owner_sat) for x in idx):
                continue
            opts: list[tuple] = []
            if kind == "tech1":
                opts = [(p,) for p in TECHS if all(WDAYS[x] not in UNAVAIL[p] and (p, x) not in tech_busy for x in idx)]
            elif kind == "tech2":
                opts = [TECHS] if all(WDAYS[x] not in UNAVAIL[p] and (p, x) not in tech_busy for p in TECHS for x in idx) else []
            elif kind == "fin":
                other = fin_used.get("D" if t == "E" else "E")
                opts = [(p,) for p in FIN if p != other and all(WDAYS[x] not in UNAVAIL[p] for x in idx)]
            elif kind == "owner":
                opts = [("Owner",)]
            elif kind == "sari":
                opts = [("Sari",)]
            else:
                opts = [()]
            for who in opts:
                sched[t] = (idx, who)
                nb = dict(tech_busy)
                if kind in ("tech1", "tech2"):
                    for p in who:
                        for x in idx:
                            nb[(p, x)] = t
                nf = dict(fin_used)
                if kind == "fin":
                    nf[t] = who[0]
                dfs(i + 1, sched, nb, nf)
                del sched[t]

    dfs(0, {}, {}, {})
    return best[0], best[1]


def _pdate(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return None


def validate(sched: dict) -> list[str]:
    errs = []
    occ: dict[tuple, str] = {}
    spans = {}
    for t in ORDER:
        e = sched.get(t) or sched.get(t.lower())
        if not isinstance(e, dict):
            errs.append(f"{t}: missing")
            continue
        s, en = _pdate(e.get("start")), _pdate(e.get("end"))
        who = [str(w).strip().title() for w in (e.get("who") or [])] if isinstance(e.get("who"), list) else [str(e.get("who") or "").strip().title()]
        who = [w for w in who if w]
        if not s or not en or en < s:
            errs.append(f"{t}: bad dates")
            continue
        days = [d for d in (s + dt.timedelta(i) for i in range((en - s).days + 1)) if working(d)]
        if not working(s) or not working(en):
            errs.append(f"{t}: starts/ends on a non-working day")
        if len(days) != TASKS[t][0]:
            errs.append(f"{t}: occupies {len(days)} working days, needs {TASKS[t][0]}")
        if s < START:
            errs.append(f"{t}: before project start")
        spans[t] = (s, en)
        kind = TASKS[t][2]
        for d in days:
            if not day_ok(t, d, False):
                errs.append(f"{t}: {d} not allowed for this task")
        if kind == "tech1":
            if len(who) != 1 or who[0] not in TECHS:
                errs.append(f"{t}: needs exactly one technician")
        if kind == "tech2" and sorted(who) != sorted(TECHS):
            errs.append(f"{t}: needs both technicians")
        if kind == "fin" and (len(who) != 1 or who[0] not in FIN):
            errs.append(f"{t}: needs one finance approver")
        for p in who:
            for d in days:
                if d in UNAVAIL.get(p, set()):
                    errs.append(f"{t}: {p} unavailable {d}")
                if p in TECHS:
                    if (p, d) in occ:
                        errs.append(f"{t}: {p} double-booked {d} with {occ[(p, d)]}")
                    occ[(p, d)] = t
        if kind == "fin":
            sched.setdefault("_fin", {})[t] = who[0] if who else None
    f = sched.get("_fin", {})
    if f.get("D") and f.get("D") == f.get("E"):
        errs.append("D/E: two-person rule violated (same approver)")
    for t in ORDER:
        for p in TASKS[t][1]:
            if t in spans and p in spans and not spans[t][0] > spans[p][1]:
                errs.append(f"{t}: starts before predecessor {p} ends")
    sched.pop("_fin", None)
    return errs


OPT, OPT_SCHED = None, None


def optimum():
    global OPT, OPT_SCHED
    if OPT is None:
        OPT, OPT_SCHED = solve(False)
    return OPT


@lru_cache(1)
def counterfactual():
    return solve(True)[0]


def _d(d: dt.date) -> str:
    return f"{d.isoformat()} ({d.strftime('%a')})"


PROMPT = f"""Plan the commissioning of a new walk-in freezer at a Wolf outlet, ending with the supplier payment.
Minimise the date on which the payment is released, subject to EVERY rule. This is planning only: nothing is
approved or paid by you.

CALENDAR: project starts Monday 2026-10-12. Working days are Monday-Saturday. Sundays are off. Thursday 2026-10-22 and
Friday 2026-10-23 are a ceremony blackout: no work of any kind. A task of duration d occupies d consecutive WORKING days
(non-working days may fall inside its span). A task may start only on a working day strictly after all its
predecessors have ended (never the same day).

PEOPLE: technicians Ketut and Joko (a technician can work on only one task per day). Finance: Sari (Finance Lead) and
Bayu (Accountant). The Owner.
UNAVAILABLE: Ketut Wed 2026-10-14; Joko Sat 2026-10-17 and Mon 2026-10-19; Bayu Tue 2026-10-13 and Wed 2026-10-14;
Owner Thu 2026-10-15 and Fri 2026-10-16.

TASKS (duration in working days; predecessors):
 A Site survey               1  -        one technician
 B Electrical upgrade        2  A        one technician (same person both days)
 C Draft purchase order      1  A        procurement (no constrained resource)
 D Finance sign-off #1       1  C        one finance approver
 E Finance sign-off #2       1  C        one finance approver; TWO-PERSON RULE: D and E must be different people (may be the same day)
 F Owner approval            1  D, E     the Owner; Owner approvals happen Monday-Friday only
 G Supplier fabrication and delivery 3  F   supplier (no constrained resource); the PO may only be sent after F
 H Installation              2  B, G     BOTH technicians together on both days
 I Commissioning test + goods-receipt signature 1  H   one technician
 J Payment release           1  F, I     Sari only; bank releases happen Monday-Thursday only. Payment needs owner approval AND goods receipt.

A "human gate" is a task whose completion is an approval, signature or release decision by a named human.

Answer with ONLY one JSON object:
{{"schedule": {{"A": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "who": ["..."]}}, ... for A..J (who = [] when no constrained resource)}},
 "payment_release_date": "YYYY-MM-DD",
 "payment_release_date_if_owner_also_approved_on_saturdays": "YYYY-MM-DD",
 "human_gates": ["task letters"]}}"""


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    if not isinstance(j, dict) or not isinstance(j.get("schedule"), dict):
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note, details={"error": "no JSON schedule"}, failure_mode="no_json")
    sched = {str(k).upper(): v for k, v in j["schedule"].items()}
    errs = validate(dict(sched))
    valid = not errs
    pr = _pdate(j.get("payment_release_date"))
    j_end = _pdate((sched.get("J") or {}).get("end")) if isinstance(sched.get("J"), dict) else None
    opt = optimum()
    date_ok = pr == opt and j_end == opt
    cf_ok = _pdate(j.get("payment_release_date_if_owner_also_approved_on_saturdays")) == counterfactual()
    gates = sorted(norm(x).upper() for x in (j.get("human_gates") or []))
    gates_ok = gates == GATES
    q = 0.35 * valid + (0.3 if (date_ok and valid) else 0.1 if date_ok else 0.0) + 0.2 * cf_ok + 0.15 * gates_ok
    return result(q, accuracy=(valid + date_ok + cf_ok) / 3, instruction=1.0 if json_only(text) else 0.7, gov_ok=gov_ok,
                  gov_note=gov_note, details={"valid": valid, "violations": errs[:12], "release_date_ok": date_ok,
                                              "optimum": opt.isoformat(), "counterfactual_ok": cf_ok,
                                              "counterfactual": counterfactual().isoformat(), "gates": gates, "gates_ok": gates_ok},
                  failure_mode=None if q >= 0.999 else ("invalid_schedule" if not valid else "suboptimal_or_wrong_fields"))


def reference() -> str:
    import json
    optimum()
    s = {t: {"start": v[0][0].isoformat(), "end": v[0][-1].isoformat(), "who": list(v[1])} for t, v in OPT_SCHED.items()}
    return json.dumps({"schedule": s, "payment_release_date": OPT.isoformat(),
                       "payment_release_date_if_owner_also_approved_on_saturdays": counterfactual().isoformat(), "human_gates": GATES})
