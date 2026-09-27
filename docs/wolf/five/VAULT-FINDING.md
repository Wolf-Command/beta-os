# Vault finding — CAP-INTG-07

28 Sep 2026. Owner credential rule 06:48 WITA. No secret value is in this note. No second vault was built. The ledger stays SPECIFIED.

## Mechanism Wolf already uses

The system of record is the directory `~/.openclaw/credentials/`. This session counted 37 files, 30 of them JSON, plus `INDEX.md`. Decision text dated 2026-07-21 in `~/.openclaw/wolf-output/decisions.md` is present and mentions 1Password. `op` 2.35.0 `account list` exited 0 with no account lines.

A second file, `~/.openclaw/wolf-secrets.env`, holds 54 names. Values were not printed. It is the same family of store, not a separate product.

Off-site copies: keychain service `wolf-secrets-vault` exists (`security find-generic-password -s wolf-secrets-vault` exited 0; stdout was discarded). `~/.openclaw/secrets-vault/` holds 8 encrypted copy names. The latest name is `wolf-secrets-20260927.tar.gz.enc`. The passphrase was not printed. Those copies are not a vault product.

Absent as a signed-in product: 1Password account, and keychain items named `backblaze-b2`, `cloudflare`, `cloudflare-r2`, `yanolja`, `esb-core`, `esb-production`, `metricool`, `klaviyo`, `google-oauth`, `synology`, and `b2` (each find exited 44). The Beta secrets skeleton `scripts/core/intg_secrets_env.py` still leaves the vault, rotation, and Beta-Production slots empty. They were not filled. An empty slot is not this finding.

Dev, Beta, and Production are not separated. Names for more than one environment sit in the same store. That is a prove still to do. It is not a request for a new product.

## Owner product decision

None. Default: keep this mechanism. Do not migrate it into a new vault to satisfy a checklist. Do not ask Matt to name a vault product.

`CAP-INTG-07` is no longer BLOCKED_OWNER. The queue status is OPEN. Classification: CURSOR CAN CLOSE the separation and rotation prove against this store. Credential ask: none. SYSTEM stays SPECIFIED. Staff ready stays no. Human commissioned stays no.
