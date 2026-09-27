# Cursor brief — BF-content-engine-staff-ux-20260924

Read and execute:
`docs/deliveries/SPEC-Content-Engine-Staff-UX-Redesign-2026-09-24.md`

Also obey:
- `docs/RULE-Content-Engine-Staff-UX-2026-09-24.md`
- Audit findings in `docs/deliveries/AUDIT-Content-Engine-Staff-Jargon-Leak-2026-09-24.md`

Constraints:
- Workspace `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild`
- Soft head `f3ab8f7` has uncommitted work — do not destroy it; Beta only
- Production :8787 sacred — do not mutate (PID must stay)
- No `--trust` needed beyond existing launch flags; do not invent staff_ready=true
- No new agents; no speculative breadth; no PR merge
- CAP / CR stay SPECIFIED; staff_ready=false

Deliver:
1. Staff UX changes per SPEC (nav, jargon strip, library, upload progress, plan declutter, WI shell)
2. Tests FAIL=0
3. `docs/deliveries/GROK-REVIEW-Content-Engine-Staff-UX-2026-09-24.md`
4. End with `EXIT: SUCCESS` or `EXIT: FAIL` and PASS=/FAIL= counts
