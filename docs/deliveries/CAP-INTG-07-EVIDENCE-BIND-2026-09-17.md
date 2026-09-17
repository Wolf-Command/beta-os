# CAP-INTG-07 — EVIDENCE BIND PACK (OVERNIGHT P1)

> **OWNER AUDIT 2026-09-18 — Matt REJECTED PROVEN.**  
> Remains **SPECIFIED**. Gitignore / `.env.example` / sacred-rule checks are evidence, not PROVEN. See `docs/deliveries/EVIDENCE-REMEDIATION-DR01-INTG07-2026-09-18.md`.

**CAP-ID:** CAP-INTG-07 Secrets & Environment Separation
**Prior:** SPECIFIED → **Proposed (overnight):** PROVEN — **REJECTED 2026-09-18**
**Current maturity:** SPECIFIED
**Class:** PROVE WHAT EXISTS

## Implementation (locatable config)

- `.env.example` present (template; no secrets)
- `.gitignore` excludes `.env`, `.env.*`, with `!.env.example` exception
- Also ignores `*.pem`, `*.key`, `*credentials*`, `*secret*`, `*token*.json`
- Canon: `docs/RULE-Beta-Construction-Production-Sacred-2026-09-16.md` (Beta construction / Production sacred)
- Runtime: `scripts/serve_beta.py` + core modules read env; keys not hardcoded in repo samples

## Deterministic verification

- `scripts/tests/test_cap_intg_07_environment_separation.py` (renamed from `test_cap_intg_07_secrets_separation.py` so gitignore `*secret*` does not hide the test)

## Why not PROVEN / READY

- Matt 2026-09-18: repo config checks ≠ PROVEN for secrets/environment separation
- No dedicated secrets vault product / rotation CAP prove
- Production secret store separation is operational practice outside beta-os unit boundary
