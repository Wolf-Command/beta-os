# Owner UI — how to open Wolf Intelligence

## Primary (sidecar — always on via LaunchAgent)

1. On Mac Studio Safari/Chrome: open **http://127.0.0.1:8799/**
   Pass and Fail need your name plus `WOLF_INTELLIGENCE_UI_TOKEN` (Authorization bearer, or cookie `wolf_intelligence_session`). If the token is unset, the page still loads and every POST returns 401. The token is not written to the access log.
2. Phone on same LAN: use Studio’s local IP with port 8799 (or SSH tunnel).
3. LaunchAgent label: `com.wolfcommand.wolf-intelligence-owner-ui` (KeepAlive).
4. Manual restart: `~/beta-os/wolf_intelligence/bin/start_owner_ui.sh`

## Beta path (after Beta reload)

- **http://127.0.0.1:8788/owner/intelligence**
- API: `/api/wolf-intelligence/board`
- Route is wired in `serve_beta.py` + `scripts/core/wolf_intel_routes.py`.
- Reload Beta only in a safe window (not while humans are on Daily Close / Petty). Sidecar works without reload.

## What you see

NEEDS YOU · READY TO TEST · DECISIONS · EXCEPTIONS · RUNNING  
Technical Details is optional and collapsed.
