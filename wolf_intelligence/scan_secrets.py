"""Secret scan for wolf_intelligence commits — never commit secrets."""
from __future__ import annotations

import re
from pathlib import Path

from . import events
from .paths import BETA_ROOT, PKG_ROOT

PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"), "key_assignment"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "openai_like"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "anthropic_like"),
    (re.compile(r"xai-[A-Za-z0-9]{20,}"), "xai_like"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), "google_like"),
    (re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"), "private_key"),
]


def scan_tree(root: Path | None = None) -> dict:
    root = root or PKG_ROOT
    hits = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pyc", ".sqlite"}:
            continue
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"(?i)(API_KEY|TOKEN|SECRET)\s+(configured|present|name)", line):
                continue
            if "KEY NAME" in line or "value not read" in line or "value redacted" in line.lower():
                continue
            # Detector literals / presence checks — not live secrets
            if re.search(r'["\']sk-ant-["\']|["\']sk-["\']|in txt|in at\.lower|appears to embed|auth-profiles references', line):
                continue
            for pat, kind in PATTERNS:
                if pat.search(line):
                    hits.append({"file": str(path.relative_to(BETA_ROOT)), "line": i, "kind": kind})
                    break
    ok = len(hits) == 0
    events.emit("audit.secret_scan", {"ok": ok, "hits": len(hits), "root": str(root)})
    return {"ok": ok, "hits": hits}
