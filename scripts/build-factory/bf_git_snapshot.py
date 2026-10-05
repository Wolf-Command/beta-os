#!/usr/bin/env python3
"""Versioned Beta snapshot -> GitHub (Owner P0 5 Oct 2026 20:30 WITA).

Purpose: every significant Beta change must exist as a reviewable diff on GitHub
(wolfcommand/beta-os, branch `beta`) BEFORE Beta is reloaded and before READY FOR
HUMAN TEST. Peaches builds; ChatGPT reviews versioned diffs. See
docs/BETA-GITHUB-LIFECYCLE.md.

Safe to run while a factory slice holds WRITER.lock:
  * uses a PRIVATE index file (.git/beta-snapshot.index) + plumbing
    (read-tree / add / write-tree / commit-tree / update-ref);
  * never touches HEAD, the checked-out branch, the worker's index or the worktree;
  * never resets, cleans, stashes, checks out, or force-pushes;
  * respects .gitignore (secrets / raw financial evidence / DBs / backups excluded);
  * refuses to commit if a staged change matches a credential pattern or a file is
    larger than MAX_FILE_MB, and records why.

Usage:
  python3 scripts/build-factory/bf_git_snapshot.py --reason "<slice id / why>" [--no-push] [--message-file F]
Exit: 0 committed+pushed or unchanged+in-sync; 4 committed but push failed;
      5 refused (secret/size); 1 error.
Writes state/build-factory/GIT-SNAPSHOT-LAST.json and appends GIT-SNAPSHOT-LOG.jsonl.
Never prints secrets or process command lines.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
BF = ROOT / "state" / "build-factory"
BRANCH = "beta"
REMOTE = "origin"
INDEX = ROOT / ".git" / "beta-snapshot.index"
LAST = BF / "GIT-SNAPSHOT-LAST.json"
LOG = BF / "GIT-SNAPSHOT-LOG.jsonl"
FLOCK = BF / "GIT-SNAPSHOT.flock"
MAX_FILE_MB = 20
PUSH_TIMEOUT = 180
SECRET_RE = re.compile(
    rb"(?<![A-Za-z0-9-])sk-(?:proj-|ant-)?[A-Za-z0-9_]{32,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}"
    rb"|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"
    rb"|AIza[0-9A-Za-z_-]{35}|ya29\.[0-9A-Za-z_-]{20,}|cfut_[A-Za-z0-9]{20,}"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str, env: dict | None = None, check: bool = True, timeout: int = 120,
        input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    e.update({"GIT_TERMINAL_PROMPT": "0"})
    if env:
        e.update(env)
    return subprocess.run(["git", "-c", "gc.auto=0", "-c", "core.hooksPath=/dev/null", "-C", str(ROOT), *args],
                          env=e, capture_output=True, check=check, timeout=timeout, input=input_bytes)


def out(*args: str, **kw) -> str:
    return git(*args, **kw).stdout.decode().strip()


def rev(ref: str) -> str | None:
    r = git("rev-parse", "--verify", "-q", ref + "^{commit}", check=False)
    return r.stdout.decode().strip() or None


def record(rec: dict) -> None:
    rec.setdefault("at", now_iso())
    BF.mkdir(parents=True, exist_ok=True)
    LAST.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def writer_lock() -> dict:
    try:
        d = json.loads((BF / "WRITER.lock").read_text())
        return {k: d.get(k) for k in ("state", "slice", "run_id")}
    except Exception:  # noqa: BLE001
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reason", default="")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--message-file")
    a = ap.parse_args()

    BF.mkdir(parents=True, exist_ok=True)
    with FLOCK.open("w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print(json.dumps({"result": "BUSY", "reason": "another snapshot running"}))
            return 1
        env = {"GIT_INDEX_FILE": str(INDEX)}
        head = rev("HEAD")
        parent = rev(f"refs/heads/{BRANCH}") or head
        if not parent:
            print(json.dumps({"result": "ERROR", "reason": "no HEAD"})); return 1
        # Build the private index from the parent tree, then stage the live worktree.
        git("read-tree", parent, env=env)
        git("add", "-A", "--", ".", env=env, timeout=600)
        tree = out("write-tree", env=env)
        parent_tree = out("rev-parse", f"{parent}^{{tree}}")
        changed = out("diff-tree", "-r", "--name-only", "--no-renames", parent_tree, tree).splitlines()
        rec = {"reason": a.reason, "branch": BRANCH, "parent": parent, "head": head,
               "writer_lock": writer_lock(), "files_changed": len(changed)}

        # Guards: oversize + credential patterns in changed blobs.
        big, hits = [], []
        for path in changed:
            r = git("ls-tree", tree, "--", path, check=False).stdout.decode().split()
            if len(r) < 3 or r[1] != "blob":
                continue
            size = int(out("cat-file", "-s", r[2]))
            if size > MAX_FILE_MB * 1024 * 1024:
                big.append(path)
                continue
            if size < 5 * 1024 * 1024 and SECRET_RE.search(git("cat-file", "blob", r[2]).stdout):
                hits.append(path)
        if big or hits:
            rec.update({"result": "REFUSED", "oversize": big, "secret_pattern_paths": hits})
            record(rec); print(json.dumps(rec)); return 5

        commit = parent
        if tree != parent_tree:
            msg = (Path(a.message_file).read_text() if a.message_file else
                   f"beta: snapshot before reload — {a.reason or 'factory'}\n\n"
                   f"Factory snapshot of the LIVE Beta tree (/Users/wolfterminal/beta-os, :8788).\n"
                   f"Writer lock: {json.dumps(rec['writer_lock'])}\nFiles changed: {len(changed)}\n")
            parents = ["-p", parent]
            if head and head != parent:
                if git("merge-base", "--is-ancestor", head, parent, check=False).returncode != 0:
                    parents += ["-p", head]
            cenv = {"GIT_AUTHOR_NAME": "Wolf Beta Factory", "GIT_AUTHOR_EMAIL": "factory@wolfcommand.net",
                    "GIT_COMMITTER_NAME": "Wolf Beta Factory", "GIT_COMMITTER_EMAIL": "factory@wolfcommand.net"}
            commit = git("commit-tree", tree, *parents, env=cenv, input_bytes=msg.encode()).stdout.decode().strip()
            old = rev(f"refs/heads/{BRANCH}") or ""
            git("update-ref", "-m", f"bf_git_snapshot: {a.reason}"[:200], f"refs/heads/{BRANCH}", commit,
                *( [old] if old else ["0" * 40] ))
        rec.update({"commit": commit, "committed": commit != parent})

        if a.no_push:
            rec.update({"result": "COMMITTED_NOT_PUSHED", "pushed": False}); record(rec); print(json.dumps(rec)); return 0
        try:
            p = git("push", REMOTE, f"refs/heads/{BRANCH}:refs/heads/{BRANCH}", check=False, timeout=PUSH_TIMEOUT)
            ok = p.returncode == 0
            err = "" if ok else p.stderr.decode()[-300:]
        except subprocess.TimeoutExpired:
            ok, err = False, "push timeout"
        remote = ""
        if ok:
            ls = git("ls-remote", REMOTE, f"refs/heads/{BRANCH}", check=False, timeout=60).stdout.decode().split()
            remote = ls[0] if ls else ""
        rec.update({"pushed": ok and remote == commit, "remote_sha": remote, "push_error": err,
                    "result": "PUSHED" if ok and remote == commit else "PUSH_FAILED",
                    "github": f"https://github.com/wolfcommand/beta-os/commit/{commit}"})
        record(rec); print(json.dumps(rec))
        return 0 if rec["pushed"] else 4


if __name__ == "__main__":
    sys.exit(main())
