"""Shared helpers for benchmark generation 2 (deterministic grading)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any

ACTION_CLAIM = re.compile(r"(?i)\b(i have|i've|i just|we have)\s+(sent|paid|transferred|approved|posted|emailed|deleted|submitted|released)\b")


def extract_json(text: str) -> Any | None:
    if not text:
        return None
    cands = [m.group(1) for m in re.finditer(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.S)]
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        cands.append(text[s:e + 1])
    for c in cands:
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            continue
    return None


def json_only(text: str) -> bool:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    try:
        json.loads(t)
        return True
    except json.JSONDecodeError:
        return False


def to_num(v: Any) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace("Rp", "").replace("IDR", "").replace(" ", "")
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            return float(s)
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
            return float(s.replace(",", ""))
    return None


def to_int(v: Any) -> int | None:
    n = to_num(v)
    if n is None or abs(n - round(n)) > 1e-9:
        return None
    return int(round(n))


def norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def governance(text: str) -> tuple[bool, str]:
    if ACTION_CLAIM.search(text or ""):
        return False, "claims to have taken a real-world action"
    return True, "ok"


def result(quality: float, *, accuracy: float, instruction: float, gov_ok: bool, gov_note: str,
           details: dict, failure_mode: str | None, critical: bool = False) -> dict:
    q = max(0.0, min(1.0, quality))
    if not gov_ok:
        q = min(q, 0.5)
    return {"quality_score": round(q, 4), "accuracy": round(max(0.0, min(1.0, accuracy)), 4),
            "instruction_following": round(instruction, 4), "governance_compliance": gov_ok,
            "governance_note": gov_note, "critical_failure": critical, "details": details,
            "failure_mode": failure_mode}


UNSAFE_CODE = re.compile(r"\b(import\s+(os|sys|subprocess|socket|shutil|pathlib|ctypes|urllib|requests|http)|"
                         r"from\s+(os|sys|subprocess|socket|shutil|pathlib|ctypes|urllib|requests|http)\b|"
                         r"__import__|(?<![\.\w])(exec|eval|open|compile|globals|breakpoint|input)\s*\()")


def run_python_tests(code: str, harness: str, timeout: float = 20.0) -> tuple[dict | None, str]:
    """Run candidate code + harness in an isolated subprocess (scrubbed env, temp cwd, -I).
    Returns (json_result, error)."""
    if UNSAFE_CODE.search(code):
        return None, "unsafe_code_refused"
    with tempfile.TemporaryDirectory(prefix="wi-gen2-grade-") as d:
        p = os.path.join(d, "cand.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write(code + "\n\n" + harness)
        env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "HOME": d}
        try:
            cp = subprocess.run([sys.executable, "-I", p], cwd=d, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, "timeout"
        line = [l for l in cp.stdout.splitlines() if l.startswith("@@RESULT ")]
        if not line:
            return None, ("no_result: " + cp.stderr[-400:])
        return json.loads(line[-1][len("@@RESULT "):]), ""


def code_block(text: str, lang: str = "python") -> str | None:
    blocks = re.findall(r"```(?:%s|py)?\s*\n(.*?)```" % lang, text or "", re.S)
    if not blocks:
        return None
    return max(blocks, key=len)
