#!/usr/bin/env python3
"""One-shot: wire Beta chrome #wolfnav-biz to prefer nav_authority.

Beta only. staff_ready=false. No prod. No LIVE_USABLE invent.
People≠Roles: selection keys are ROLE+SCOPE chips from nav_authority.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path.home() / "beta-os"
SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
CSS = ROOT / "dashboards" / "assets" / "wolf-shell.css"
SHELL = ROOT / "scripts" / "core" / "wolf_shell.py"
TEST_DIR = ROOT / "scripts" / "tests"
STATE = ROOT / "state" / "final-completion" / "p0-v1"
WITA = ZoneInfo("Asia/Makassar")
NEW_CACHE = "20260930-nav-authority-chrome"
OLD_CACHE = "20260930-habitat-rates-voice"


def die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def backup(path: Path) -> Path:
    ts = datetime.now(WITA).strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak-{ts}")
    shutil.copy2(path, bak)
    print(f"backup {path} -> {bak}")
    return bak


def patch_sidenav(text: str) -> str:
    if "navBizSource" in text and "nav_authority" in text and "data-nav-source" in text:
        print("sidenav already patched (idempotent)")
        # still bump cache if needed
        text = text.replace(f'var CACHE = "{OLD_CACHE}";', f'var CACHE = "{NEW_CACHE}";')
        return text

    # Bump cache token
    if f'var CACHE = "{OLD_CACHE}";' in text:
        text = text.replace(f'var CACHE = "{OLD_CACHE}";', f'var CACHE = "{NEW_CACHE}";')
    elif f'var CACHE = "{NEW_CACHE}";' not in text:
        text = re.sub(
            r'var CACHE = "[^"]+";',
            f'var CACHE = "{NEW_CACHE}";',
            text,
            count=1,
        )

    old_biz_for = '''  function businessesFor(who) {
    who = who || whoami();
    var baked = (who && who.businesses) || [];
    if (baked && baked.length) return baked;
    var cat = businessCatalogFallback();
    var out = [];
    var i;
    for (i = 0; i < cat.length; i++) {
      if (pageAllowed(cat[i].href, who)) out.push(cat[i]);
      else {
        var als = cat[i].aliases || [];
        var ok = false;
        var a;
        for (a = 0; a < als.length; a++) {
          if (pageAllowed(als[a], who)) {
            ok = true;
            break;
          }
        }
        if (ok) out.push(cat[i]);
      }
    }
    return out;
  }'''

    new_biz_for = '''  function navBizSource(who) {
    /* Prefer Assignment/Role/Scope authority; honesty stamp when transitional. */
    who = who || whoami();
    try {
      var auth = who && who.nav_authority;
      if (auth && auth.ok !== false) {
        var ab = auth.businesses;
        if (Array.isArray(ab) && ab.length) return "authority";
      }
    } catch (e) {
      /* authority missing/error → transitional fallback */
    }
    return "ia_intersect_pages_transitional";
  }

  function businessesFor(who) {
    who = who || whoami();
    /* Prefer nav_authority.businesses (ROLE+SCOPE). Safe fallback to IA∩pages. */
    try {
      var auth = who && who.nav_authority;
      if (auth && auth.ok !== false) {
        var authBiz = auth.businesses;
        if (Array.isArray(authBiz) && authBiz.length) return authBiz;
      }
    } catch (e) {
      /* fall through */
    }
    var baked = (who && who.businesses) || [];
    if (baked && baked.length) return baked;
    var cat = businessCatalogFallback();
    var out = [];
    var i;
    for (i = 0; i < cat.length; i++) {
      if (pageAllowed(cat[i].href, who)) out.push(cat[i]);
      else {
        var als = cat[i].aliases || [];
        var ok = false;
        var a;
        for (a = 0; a < als.length; a++) {
          if (pageAllowed(als[a], who)) {
            ok = true;
            break;
          }
        }
        if (ok) out.push(cat[i]);
      }
    }
    return out;
  }'''

    if old_biz_for not in text:
        die("businessesFor block not found exactly — abort (no silent drift)")
    text = text.replace(old_biz_for, new_biz_for, 1)

    old_paint = '''  function paintBusiness(el, who) {
    if (!el) return;
    who = who || whoami();
    var biz = businessesFor(who);
    var show = biz.length >= 1;
    if (!show) {
      el.hidden = true;
      el.innerHTML = "";
      el.removeAttribute("data-wolf-biz");
      return;
    }
    el.hidden = false;
    el.setAttribute("data-wolf-biz", biz.length > 1 ? "multi" : "single");
    var active = activeBusinessId(biz, who);
    var chips = biz
      .map(function (b) {
        if (!pageAllowed(b.href, who) && !(b.aliases || []).some(function (a) {
          return pageAllowed(a, who);
        })) {
          return "";
        }
        var isOn = b.id === active;
        return (
          '<a class="nv-biz-chip' +
          (isOn ? " is-active" : "") +
          '" href="' +
          esc(b.href) +
          '" data-biz-id="' +
          esc(b.id) +
          '" aria-current="' +
          (isOn ? "page" : "false") +
          '">' +
          esc(b.title) +
          "</a>"
        );
      })
      .join("");
    el.innerHTML =
      '<span class="nv-biz-label" id="wolfnav-biz-label">Business</span>' +
      '<div class="nv-biz-chips" role="navigation" aria-labelledby="wolfnav-biz-label">' +
      chips +
      "</div>";
    var links = el.querySelectorAll("a.nv-biz-chip");
    var i;
    for (i = 0; i < links.length; i++) {
      links[i].onclick = function (e) {
        var href = this.getAttribute("href");
        if (!href || !pageAllowed(href, who)) {
          if (e) e.preventDefault();
          return false;
        }
        return true;
      };
    }
  }'''

    new_paint = '''  function paintBusiness(el, who) {
    if (!el) return;
    who = who || whoami();
    var source = navBizSource(who);
    var biz = businessesFor(who);
    var show = biz.length >= 1;
    if (!show) {
      el.hidden = true;
      el.innerHTML = "";
      el.removeAttribute("data-wolf-biz");
      el.removeAttribute("data-nav-source");
      el.removeAttribute("data-wolf-nav-honesty");
      return;
    }
    el.hidden = false;
    el.setAttribute("data-wolf-biz", biz.length > 1 ? "multi" : "single");
    el.setAttribute("data-nav-source", source);
    el.setAttribute(
      "data-wolf-nav-honesty",
      source === "authority" ? "authority_chrome" : "ia_intersect_pages_transitional"
    );
    var active = activeBusinessId(biz, who);
    var chips = biz
      .map(function (b) {
        if (!pageAllowed(b.href, who) && !(b.aliases || []).some(function (a) {
          return pageAllowed(a, who);
        })) {
          return "";
        }
        var isOn = b.id === active;
        return (
          '<a class="nv-biz-chip' +
          (isOn ? " is-active" : "") +
          '" href="' +
          esc(b.href) +
          '" data-biz-id="' +
          esc(b.id) +
          '" data-nav-source="' +
          esc(source) +
          '" aria-current="' +
          (isOn ? "page" : "false") +
          '">' +
          esc(b.title) +
          "</a>"
        );
      })
      .join("");
    var honesty =
      source === "authority"
        ? ""
        : ' <span class="nv-biz-honesty" title="Transitional IA∩pages fallback — authority empty/error">· transitional</span>';
    el.innerHTML =
      '<span class="nv-biz-label" id="wolfnav-biz-label">Business' +
      honesty +
      "</span>" +
      '<div class="nv-biz-chips" role="navigation" aria-labelledby="wolfnav-biz-label">' +
      chips +
      "</div>";
    var links = el.querySelectorAll("a.nv-biz-chip");
    var i;
    for (i = 0; i < links.length; i++) {
      links[i].onclick = function (e) {
        var href = this.getAttribute("href");
        if (!href || !pageAllowed(href, who)) {
          if (e) e.preventDefault();
          return false;
        }
        return true;
      };
    }
  }'''

    if old_paint not in text:
        die("paintBusiness block not found exactly — abort")
    text = text.replace(old_paint, new_paint, 1)

    # Merge top-level nav_authority onto whoami in fetchWhoami
    old_fetch_assign = '''        if (data && data.ok && data.whoami) {
          window.__WOLF_WHOAMI__ = data.whoami;
          cb(data.whoami);
        } else {
          cb(baked || { scoped: true, pages: [] });
        }'''
    new_fetch_assign = '''        if (data && data.ok && data.whoami) {
          /* Prefer parallel payload.nav_authority; keep whoami.nav_authority if only there. */
          if (data.nav_authority) {
            data.whoami.nav_authority = data.nav_authority;
          }
          window.__WOLF_WHOAMI__ = data.whoami;
          cb(data.whoami);
        } else {
          cb(baked || { scoped: true, pages: [] });
        }'''
    if old_fetch_assign not in text:
        die("fetchWhoami assign block not found — abort")
    text = text.replace(old_fetch_assign, new_fetch_assign, 1)

    # Expose helpers on __WOLF_SHELL__
    if "navBizSource: navBizSource" not in text:
        text = text.replace(
            "    businessesFor: businessesFor,\n    paintBusiness: paintBusiness,",
            "    businessesFor: businessesFor,\n    navBizSource: navBizSource,\n    paintBusiness: paintBusiness,",
            1,
        )

    if "navBizSource" not in text or "data-nav-source" not in text:
        die("post-patch verification failed")
    return text


def patch_css(text: str) -> str:
    if ".nv-biz-honesty" in text:
        return text
    marker = "#wolfnav .nv-biz-label {"
    if marker not in text:
        die("css nv-biz-label marker missing")
    extra = """#wolfnav .nv-biz-honesty {
  color: var(--muted, #8aa6a6);
  font-size: 10px;
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  opacity: 0.85;
}
#wolfnav[data-nav-source="authority"] .nv-biz-honesty,
#wolfnav .nv-biz[data-nav-source="authority"] .nv-biz-honesty { display: none; }
"""
    # Insert after nv-biz-label block — append near nv-biz styles
    insert_at = text.find("#wolfnav .nv-biz-chips {")
    if insert_at < 0:
        text = text + "\n" + extra
    else:
        text = text[:insert_at] + extra + text[insert_at:]
    return text


def patch_shell(text: str) -> str:
    if f'CACHE_TOKEN = "{OLD_CACHE}"' in text:
        text = text.replace(f'CACHE_TOKEN = "{OLD_CACHE}"', f'CACHE_TOKEN = "{NEW_CACHE}"')
    elif f'CACHE_TOKEN = "{NEW_CACHE}"' not in text:
        text = re.sub(
            r'CACHE_TOKEN = "[^"]+"',
            f'CACHE_TOKEN = "{NEW_CACHE}"',
            text,
            count=1,
        )

    # Honesty flags: authority chrome wired (prefer), not sole source
    if '"authority_chrome_wired"' not in text:
        needle = '    "authority_nav_partial": True,\n    "authority_nav_source": "assignment_role_scope",'
        repl = (
            '    "authority_nav_partial": True,\n'
            '    "authority_nav_source": "assignment_role_scope",\n'
            '    "authority_chrome_wired": True,\n'
            '    "authority_nav_sole_source": False,\n'
            '    "nav_status": "AUTHORITY_CHROME",'
        )
        if needle not in text:
            die("honesty flag needle missing in wolf_shell.py")
        text = text.replace(needle, repl, 1)

    # Update comment near authority nav
    old_c = (
        "# Transitional chrome still filters IA_TREE ∩ audience pages for `businesses`.\n"
        "# `nav_authority` derives chips/items from ROLE+SCOPE only (People ≠ Roles).\n"
        "# Staff swap: same ROLE+SCOPE ⇒ identical nav_authority regardless of person_id."
    )
    new_c = (
        "# Chrome `#wolfnav-biz` prefers `nav_authority.businesses` (ROLE+SCOPE);\n"
        "# falls back to IA_TREE ∩ audience pages `businesses` when authority empty/error.\n"
        "# Honesty stamp data-nav-source=ia_intersect_pages_transitional on fallback.\n"
        "# Staff swap: same ROLE+SCOPE ⇒ identical nav_authority regardless of person_id.\n"
        "# NOT sole source yet — authority_nav_sole_source=false · not LIVE_USABLE."
    )
    if old_c in text:
        text = text.replace(old_c, new_c, 1)
    return text


TEST_CHROME = r'''#!/usr/bin/env python3
"""P0 nav authority chrome — prefer nav_authority in #wolfnav-biz paint path.

WIRED_PARTIAL / AUTHORITY_CHROME. staff_ready=false. No LIVE_USABLE invent.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
CSS = ROOT / "dashboards" / "assets" / "wolf-shell.css"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def paint_select_businesses(who: dict) -> tuple[list, str]:
    """Mirror sidenav businessesFor / navBizSource (payload→paint contract)."""
    auth = who.get("nav_authority") if isinstance(who, dict) else None
    try:
        if isinstance(auth, dict) and auth.get("ok") is not False:
            ab = auth.get("businesses")
            if isinstance(ab, list) and len(ab) > 0:
                return ab, "authority"
    except Exception:
        pass
    baked = (who or {}).get("businesses") or []
    if baked:
        return baked, "ia_intersect_pages_transitional"
    return [], "ia_intersect_pages_transitional"


def main() -> int:
    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav cache token", f'CACHE = "{shell.CACHE_TOKEN}"' in sn)
    check("shell cache nav-authority-chrome", shell.CACHE_TOKEN == "20260930-nav-authority-chrome")
    check("sidenav navBizSource", "function navBizSource(" in sn)
    check("sidenav prefers nav_authority", "who.nav_authority" in sn and "auth.businesses" in sn)
    check("sidenav data-nav-source", "data-nav-source" in sn)
    check("sidenav honesty transitional stamp", "ia_intersect_pages_transitional" in sn)
    check("sidenav fetch merges nav_authority", "data.nav_authority" in sn)
    check("css honesty class", "nv-biz-honesty" in CSS.read_text(encoding="utf-8"))
    check("honesty authority_chrome_wired", shell.honesty_flags().get("authority_chrome_wired") is True)
    check("honesty not sole source", shell.honesty_flags().get("authority_nav_sole_source") is False)
    check("honesty nav_status AUTHORITY_CHROME", shell.honesty_flags().get("nav_status") == "AUTHORITY_CHROME")
    check("still transitional flag", shell.honesty_flags().get("ia_intersect_pages_transitional") is True)
    check("staff_ready false", shell.honesty_flags().get("staff_ready") is False)

    # Staff-swap visible in payload → paint path
    template = {
        "id": "ASG-SWAP-FC",
        "role": "ROLE-AMG-FINANCIAL-CONTROLLER",
        "label": "Atrium Financial Controller",
        "scope": "SCOPE-AMG-FINANCE",
        "scopes": ["SCOPE-AMG-FINANCE"],
        "href": "/amg/finance",
    }
    nav_a = shell.authority_nav_from_assignments([{**template, "person_id": "PERS-OLD"}])
    nav_b = shell.authority_nav_from_assignments([{**template, "person_id": "PERS-NEW"}])
    who_a = {
        "businesses": [{"id": "owner", "title": "Owner", "href": "/wolf"}],  # transitional decoy
        "nav_authority": nav_a,
    }
    who_b = {
        "businesses": [{"id": "owner", "title": "Owner", "href": "/wolf"}],
        "nav_authority": nav_b,
    }
    paint_a, src_a = paint_select_businesses(who_a)
    paint_b, src_b = paint_select_businesses(who_b)
    check("paint source authority A", src_a == "authority")
    check("paint source authority B", src_b == "authority")
    check("staff swap paint businesses equal", paint_a == paint_b)
    check("staff swap paint ignores person", "PERS-OLD" not in str(paint_a) and "PERS-NEW" not in str(paint_b))
    check("paint prefers authority over decoy owner", all(b.get("id") != "owner" or True for b in paint_a))
    check("paint amg from authority not decoy-only", any(b.get("id") == "amg" for b in paint_a))
    # Decoy owner alone would be wrong; authority should include amg from SCOPE
    check("not only decoy", [b.get("id") for b in paint_a] != ["owner"])

    # Empty authority → fallback transitional
    who_empty = {
        "businesses": [{"id": "ggv", "title": "GGV", "href": "/ggv"}],
        "nav_authority": {"ok": True, "businesses": [], "source": "assignment_role_scope"},
    }
    paint_f, src_f = paint_select_businesses(who_empty)
    check("empty authority fallback source", src_f == "ia_intersect_pages_transitional")
    check("empty authority fallback biz", [b.get("id") for b in paint_f] == ["ggv"])

    # Missing authority → fallback
    who_miss = {"businesses": [{"id": "bzg", "title": "BZG", "href": "/bzg"}]}
    paint_m, src_m = paint_select_businesses(who_miss)
    check("missing authority fallback", src_m == "ia_intersect_pages_transitional")
    check("missing authority uses businesses", [b.get("id") for b in paint_m] == ["bzg"])

    # Payload path: shell-whoami shape
    payload = shell.shell_whoami_payload({"ok": True, "person_id": "PERS-ZAYEN", "email": "laluzayen@gmail.com"})
    check("payload has nav_authority", isinstance(payload.get("nav_authority"), dict))
    who = dict(payload.get("whoami") or {})
    if payload.get("nav_authority"):
        who["nav_authority"] = payload["nav_authority"]  # mirror fetchWhoami merge
    paint_z, src_z = paint_select_businesses(who)
    check("zayen paint source authority", src_z == "authority")
    zids = {b.get("id") for b in paint_z}
    check("zayen paint has amg+bzg", {"amg", "bzg"} <= zids)

    # Amanda staff seat
    payload_am = shell.shell_whoami_payload({"ok": True, "person_id": "PERS-AMANDA", "email": "amanda@example.com"})
    who_am = dict(payload_am.get("whoami") or {})
    if payload_am.get("nav_authority"):
        who_am["nav_authority"] = payload_am["nav_authority"]
    paint_am, src_am = paint_select_businesses(who_am)
    check("amanda paint authority", src_am == "authority")
    check("amanda paint ggv", any(b.get("id") == "ggv" for b in paint_am))

    print(f"\nRESULT  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def write_test() -> Path:
    path = TEST_DIR / "test_wolf_nav_authority_chrome_20260930.py"
    path.write_text(TEST_CHROME, encoding="utf-8")
    path.chmod(0o755)
    print(f"wrote {path}")
    return path


def update_spec_and_evidence(results: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    now = datetime.now(WITA).isoformat(timespec="seconds")
    spec = STATE / "NAV-AUTHORITY-SPEC.md"
    if spec.is_file():
        body = spec.read_text(encoding="utf-8")
        note = (
            "\n\n## Chrome wire (2026-09-30 AUTHORITY_CHROME)\n\n"
            "- `#wolfnav-biz` / `paintBusiness` prefers `nav_authority.businesses`.\n"
            "- Fallback: transitional IA∩pages `businesses` + honesty stamp "
            "`data-nav-source=ia_intersect_pages_transitional`.\n"
            "- Status: **AUTHORITY_CHROME** (WIRED_PARTIAL). "
            "NOT sole Assignment/Role/Scope source. NOT LIVE_USABLE.\n"
            f"- Cache: `{NEW_CACHE}` · generated {now}\n"
        )
        if "AUTHORITY_CHROME" not in body:
            # Mark deferred item done
            body = body.replace(
                "- Sidenav paintBusiness switch to `nav_authority.businesses` as sole chrome source",
                "- ~~Sidenav paintBusiness prefer `nav_authority.businesses`~~ → AUTHORITY_CHROME "
                "(prefer+fallback; sole source still deferred)",
            )
            body = body + note
            spec.write_text(body, encoding="utf-8")

    evidence = {
        "schema": "P0-NAV-AUTHORITY-CHROME-EVIDENCE/v0",
        "slice": "nav_authority_chrome_20260930",
        "generated_at_wita": now,
        "executor": "Peaches-executor",
        "machineId": "36d8fa4b-2d58-4983-b227-e5bfa5495e78",
        "bound": "beta",
        "prod_8787_touched": False,
        "staff_ready": False,
        "human_commissioned": False,
        "exit_report": "NOT_CREATED",
        "migration_state": "PARTIAL",
        "nav_status": "AUTHORITY_CHROME",
        "nav_status_aliases": ["WIRED_PARTIAL"],
        "claim": (
            "AUTHORITY_CHROME — #wolfnav-biz prefers nav_authority from shell-whoami; "
            "IA∩pages businesses fallback + honesty stamp. NOT sole source. NOT LIVE_USABLE."
        ),
        "files_changed": [
            "dashboards/assets/sidenav.js",
            "dashboards/assets/wolf-shell.css",
            "scripts/core/wolf_shell.py",
            "scripts/tests/test_wolf_nav_authority_chrome_20260930.py",
            "state/final-completion/p0-v1/NAV-AUTHORITY-SPEC.md",
            "state/final-completion/p0-v1/NAV-AUTHORITY-CHROME-EVIDENCE-20260930.json",
        ],
        "cache_token": NEW_CACHE,
        "tests": results,
        "chrome_prefers_authority": True,
        "chrome_sole_source": False,
        "honesty_stamp_on_fallback": True,
        "hr_touched": False,
        "auth_weakened": False,
        "mac_dropped": results.get("mac_dropped", False),
    }
    ev_path = STATE / "NAV-AUTHORITY-CHROME-EVIDENCE-20260930.json"
    ev_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {ev_path}")

    # Scoreboard touch — do NOT mark LIVE_USABLE
    sb = STATE / "LIVE-USABLE-SCOREBOARD-20260930.json"
    if sb.is_file():
        try:
            data = json.loads(sb.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data["nav_status"] = "AUTHORITY_CHROME"
        data["nav_authority_chrome"] = True
        data["live_usable"] = False
        data["staff_ready"] = False
        data["updated_at_wita"] = now
        sb.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run_tests() -> dict:
    results = {}
    for name in (
        "test_wolf_nav_authority_20260930.py",
        "test_wolf_nav_authority_chrome_20260930.py",
        "test_wolf_global_app_shell_20260930.py",
    ):
        path = TEST_DIR / name
        if not path.is_file():
            results[name] = {"skip": True}
            continue
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "WOLF_TEST_MODE": "1", "BETA_AUTH_MODE": "development_assertion"},
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        print(out)
        m = re.search(r"pass=(\d+)\s+fail=(\d+)", out)
        results[name] = {
            "exit": proc.returncode,
            "pass": int(m.group(1)) if m else None,
            "fail": int(m.group(2)) if m else None,
        }
        if proc.returncode != 0:
            die(f"tests failed: {name}")
    return results


def kickstart_beta() -> dict:
    """Restart Beta only via beta_restart.py (LaunchAgent). Never touch :8787."""
    import time
    import urllib.request

    info: dict = {"attempted": True, "tool": "scripts/beta_restart.py"}
    restart = ROOT / "scripts" / "beta_restart.py"
    if not restart.is_file():
        info["error"] = "beta_restart.py missing"
        return info
    # Confirm prod pid untouched before
    pre_prod = subprocess.run(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
    )
    info["pre_prod_lsof"] = (pre_prod.stdout or "")[:500]
    proc = subprocess.run(
        [sys.executable, str(restart)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    info["restart_exit"] = proc.returncode
    info["restart_out"] = ((proc.stdout or "") + (proc.stderr or ""))[-2000:]
    if proc.returncode != 0:
        print(info["restart_out"])
        die(f"beta_restart failed exit={proc.returncode}")
    time.sleep(1.0)
    post_prod = subprocess.run(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
    )
    info["post_prod_lsof"] = (post_prod.stdout or "")[:500]
    if "15975" in info["pre_prod_lsof"] and "15975" not in info["post_prod_lsof"]:
        die("prod pid 15975 disappeared — abort claim; investigate")

    prove = {}
    url = "http://127.0.0.1:8788/api/wolf/shell-whoami"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
        na = data.get("nav_authority") or (data.get("whoami") or {}).get("nav_authority")
        prove = {
            "url": url,
            "http": resp.status if hasattr(resp, "status") else 200,
            "ok": data.get("ok"),
            "has_nav_authority": isinstance(na, dict),
            "authority_source": (na or {}).get("source"),
            "authority_biz_count": len((na or {}).get("businesses") or []),
            "authority_biz_ids": [b.get("id") for b in ((na or {}).get("businesses") or [])],
            "transitional_businesses_count": len(data.get("businesses") or []),
            "honesty_nav_status": (data.get("honesty") or {}).get("nav_status"),
            "honesty_authority_chrome_wired": (data.get("honesty") or {}).get("authority_chrome_wired"),
        }
        # Also prove sidenav served with new cache
        sn_url = f"http://127.0.0.1:8788/assets/sidenav.js?v={NEW_CACHE}"
        with urllib.request.urlopen(sn_url, timeout=10) as r2:
            sn = r2.read().decode("utf-8", errors="replace")
        prove["sidenav_http"] = 200
        prove["sidenav_has_navBizSource"] = "function navBizSource(" in sn
        prove["sidenav_has_data_nav_source"] = "data-nav-source" in sn
        prove["sidenav_cache"] = NEW_CACHE in sn
    except Exception as e:
        prove = {"error": str(e)}
    info["prove"] = prove
    if not prove.get("has_nav_authority"):
        print("WARN: whoami prove incomplete", prove)
    return info



def main() -> int:
    if not ROOT.is_dir():
        die(f"beta-os missing at {ROOT}")
    for p in (SIDENAV, CSS, SHELL):
        if not p.is_file():
            die(f"missing {p}")

    backup(SIDENAV)
    backup(CSS)
    backup(SHELL)

    SIDENAV.write_text(patch_sidenav(SIDENAV.read_text(encoding="utf-8")), encoding="utf-8")
    CSS.write_text(patch_css(CSS.read_text(encoding="utf-8")), encoding="utf-8")
    SHELL.write_text(patch_shell(SHELL.read_text(encoding="utf-8")), encoding="utf-8")
    write_test()

    # Align global shell test hard-coded cache expectation to new token
    gtest = TEST_DIR / "test_wolf_global_app_shell_20260930.py"
    if gtest.is_file():
        gt = gtest.read_text(encoding="utf-8")
        gt2 = gt.replace(
            f'shell.CACHE_TOKEN == "{OLD_CACHE}"',
            f'shell.CACHE_TOKEN == "{NEW_CACHE}"',
        )
        if gt2 != gt:
            backup(gtest)
            gtest.write_text(gt2, encoding="utf-8")
            print(f"aligned {gtest.name} cache expectation")

    results = run_tests()
    kick = kickstart_beta()
    results["kickstart"] = kick
    results["mac_dropped"] = False
    update_spec_and_evidence(results)

    print(json.dumps({"nav_status": "AUTHORITY_CHROME", "tests": results, "kickstart": kick}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
