"""Grok doorbell: a GitHub issue assigned to the Grok Bot account.

The issue is a *wake-up signal only*. Its title and body carry the WI work-item
id and a one-time nonce, nothing else. No task text, no business data and no
secrets ever go to GitHub. The Grok routine (triggered on issue-assigned) reads
the id and nonce, then claims the work through the WI CLI on the Studio, where
the task content is returned over the local machine pipe.

Uses the Studio's existing `gh` login (no new secret). Off unless
WOLF_INTELLIGENCE_GROK_DOORBELL=github. Every failure raises DoorbellError; the
bridge records it and leaves the item AVAILABLE.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any

DOORBELL_ENV = "WOLF_INTELLIGENCE_GROK_DOORBELL"
REPO_ENV = "WOLF_INTELLIGENCE_GROK_DOORBELL_REPO"
ASSIGNEE_ENV = "WOLF_INTELLIGENCE_GROK_DOORBELL_ASSIGNEE"
DEFAULT_REPO = "wolfcommand/wolf-grok-bridge"
DEFAULT_ASSIGNEE = "wolfcommand"
LABEL = "wi-doorbell"
FORMAT_VERSION = "wi-grok-doorbell/1"

_WID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_NONCE = re.compile(r"^[0-9a-f]{32}$")
_REPO = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")
_ISSUE_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)/issues/(\d+)$")


class DoorbellError(Exception):
    """Ringing or closing failed. The message never contains task content or secrets."""


def issue_title(work_item_id: str) -> str:
    return f"WI doorbell {work_item_id}"


def issue_body(work_item_id: str, nonce: str) -> str:
    """The complete issue body: the format marker, the work-item id and the nonce. Nothing else."""
    if not _WID.match(work_item_id or ""):
        raise DoorbellError("bad work item id")
    if not _NONCE.match(nonce or ""):
        raise DoorbellError("bad nonce")
    return f"{FORMAT_VERSION}\nwork_item_id: {work_item_id}\nnonce: {nonce}\n"


def parse_body(body: str) -> dict[str, str]:
    """Inverse of issue_body (what a Grok routine does). Raises DoorbellError on anything unexpected."""
    lines = [l.strip() for l in (body or "").strip().splitlines() if l.strip()]
    if len(lines) != 3 or lines[0] != FORMAT_VERSION:
        raise DoorbellError("not a WI doorbell body")
    out = {}
    for line in lines[1:]:
        k, sep, v = line.partition(":")
        if not sep:
            raise DoorbellError("bad doorbell line")
        out[k.strip()] = v.strip()
    if set(out) != {"work_item_id", "nonce"} or not _WID.match(out["work_item_id"]) or not _NONCE.match(out["nonce"]):
        raise DoorbellError("bad doorbell fields")
    return out


class GitHubIssueDoorbell:
    kind = "github_issue"

    def __init__(self, repo: str = DEFAULT_REPO, assignee: str = DEFAULT_ASSIGNEE, gh: str | None = None,
                 timeout_s: float = 30.0) -> None:
        if not _REPO.match(repo):
            raise DoorbellError("bad repo name")
        self.repo, self.assignee, self.timeout_s = repo, assignee, timeout_s
        self.gh = gh or shutil.which("gh") or "/opt/homebrew/bin/gh"

    def _run(self, args: list[str]) -> str:
        try:
            proc = subprocess.run([self.gh, *args], capture_output=True, text=True, timeout=self.timeout_s,
                                  stdin=subprocess.DEVNULL)
        except FileNotFoundError:
            raise DoorbellError("gh CLI not found") from None
        except subprocess.TimeoutExpired:
            raise DoorbellError(f"gh timed out after {self.timeout_s:g}s") from None
        if proc.returncode != 0:
            # gh error text can echo request details; keep only a short, generic first line.
            first = (proc.stderr or proc.stdout or "").strip().splitlines()[:1]
            msg = re.sub(r"[^A-Za-z0-9 .,:;_/\-()']", "", first[0])[:160] if first else ""
            raise DoorbellError(f"gh exit {proc.returncode}: {msg}")
        return proc.stdout.strip()

    def ring(self, work_item_id: str, nonce: str) -> dict[str, Any]:
        """Create the issue WITHOUT an assignee, then assign it in a separate call.

        The separate call guarantees a standalone `issues.assigned` webhook event (the event the Grok
        routine listens for), instead of relying on an assignee set at creation time.
        """
        out = self._run(["issue", "create", "--repo", self.repo, "--title", issue_title(work_item_id),
                         "--body", issue_body(work_item_id, nonce), "--label", LABEL])
        url = out.splitlines()[-1].strip() if out else ""
        m = _ISSUE_URL.match(url)
        if not m or m.group(1).lower() != self.repo.lower():
            raise DoorbellError("gh did not return an issue URL in the bridge repo")
        try:
            self._run(["issue", "edit", url, "--repo", self.repo, "--add-assignee", self.assignee])
        except DoorbellError as exc:
            # An unassigned doorbell never wakes Grok: close it so it cannot linger, then report failure.
            try:
                self.close(url, "ASSIGN_FAILED")
            except DoorbellError:
                pass
            raise DoorbellError(f"assign failed: {exc}") from None
        return {"ref": url, "number": int(m.group(2)), "repo": self.repo, "assignee": self.assignee,
                "assigned": "separate_call"}

    def close(self, ref: str, outcome: str) -> None:
        m = _ISSUE_URL.match(ref or "")
        if not m or m.group(1).lower() != self.repo.lower():
            raise DoorbellError("not a bridge issue URL")
        if not re.fullmatch(r"[A-Z_]{1,32}", outcome or ""):
            raise DoorbellError("bad outcome")
        reason = "completed" if outcome == "COMPLETED" else "not planned"
        self._run(["issue", "close", ref, "--repo", self.repo, "--reason", reason, "--comment", f"WI: {outcome}"])


def from_env() -> GitHubIssueDoorbell | None:
    mode = os.environ.get(DOORBELL_ENV, "").strip().lower()
    if mode != "github":
        return None
    return GitHubIssueDoorbell(repo=os.environ.get(REPO_ENV, "").strip() or DEFAULT_REPO,
                               assignee=os.environ.get(ASSIGNEE_ENV, "").strip() or DEFAULT_ASSIGNEE)
