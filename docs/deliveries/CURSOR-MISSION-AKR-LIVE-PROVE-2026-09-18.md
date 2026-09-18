# CURSOR MISSION — Authorised Knowledge Resolver live read-only prove

Date: 2026-09-18
Repo: /Users/wolfterminal/beta-os
Branch: build/wolf-command-rebuild
Start HEAD: c58cc62
Preserve pipeline from commit 2908dad. Do not replace scripts/core/authorised_knowledge.py. Extend it.

This is not CRM. Do not touch lead spine, Klaviyo reader, cutover, staff grants, or ClickUp.

## Do not

- Do not crawl the filesystem, Drive, Notion, or the public web.
- Do not write NAS, Drive, Obsidian, or any file outside this repo.
- Do not edit scripts/phase26_team.py, scripts/migrations/migrate_phase2_6_team_readiness.py, scripts/skills/__init__.py, scripts/wolf_intelligence.py.
- Do not git add .
- Do not put customer names, emails, or phones in tests or logs.
- Do not treat model text as evidence.
- Do not change the status words: NOT CANONICAL, NOT FOUND, INACCESSIBLE, CONFLICTED, UNKNOWN.
- Do not make an empty canonical field return UNKNOWN.
- Do not merge brand_identity and ui_chrome into one conflict.

## Keep

resolve(scope, question_key, sources_registry, canonical=..., fixture_root=...).
Pipeline order stays: scope, canonical, discovery, retrieve, identity, authority, freshness, conflict, status plus provenance.
INFERENCE authority is not evidence.
SOURCE FOUND is not AUTHORITATIVE.
UNKNOWN only after the attempt log shows the bounded search.

## Live registry

New file: scripts/core/data/akr_habitat_live_registry.json
Explicit sources only. Authority is written in the registry. Do not infer it from the filename.

Allowlisted roots. A path outside these roots is INACCESSIBLE. `..` fails closed.

1. /Volumes/01-Media-Library/Brand-Assets/GGV/Habitat/
2. /Users/wolfterminal/WolfCommandSystem/WolfCommand/01-Wolf-Command/Brands/Habitat-Villas/
3. The single file /Users/wolfterminal/beta-os/scripts/phase26_team.py

Register exactly these sources:

- source_id habitat-nas-brand-guide
  type pdf
  scope brand:habitat and entity:ggv
  path /Volumes/01-Media-Library/Brand-Assets/GGV/Habitat/style-guide/Habitat_brand_guide.pdf
  authority CLIENT_APPROVED
  lane brand_identity
  question_keys brand_font
  canonical false
  accessible true when the file exists, else INACCESSIBLE

- source_id habitat-vault-brand
  type markdown
  path /Users/wolfterminal/WolfCommandSystem/WolfCommand/01-Wolf-Command/Brands/Habitat-Villas/Habitat-Brand.md
  authority OPERATIONAL
  lane brand_identity
  question_keys brand_font, brand_voice, headline_case
  scope brand:habitat

- source_id habitat-vault-strategy
  type markdown
  path .../Habitat-Villas/Habitat-Strategy.md
  authority OPERATIONAL
  lane brand_identity
  question_keys headline_case
  scope brand:habitat

- source_id wolf-ui-chrome
  type python
  path /Users/wolfterminal/beta-os/scripts/phase26_team.py
  authority OPERATIONAL_UI
  lane ui_chrome
  question_keys ui_font
  scope brand:habitat
  This file is read only. Do not edit it.

Do not add Drive or Notion in this slice.

## Retrieval

PDF: use /opt/homebrew/bin/pdftotext. Keep page text. Provenance includes source_id, path, page, and sha256 of the file. A PDF existing is not the fact. The passage that contains Manrope is the fact.
Markdown and the python file: read text, bounded by the existing max_bytes. Extract only the registered question. If the tool or file is missing, status INACCESSIBLE. Do not invent the passage.
Oversized input stays capped. Unsupported type is INACCESSIBLE, not guessed text.

## Prove cases

Tests in scripts/tests/test_authorised_knowledge_live.py
Existing fixture tests in test_authorised_knowledge.py must still pass. Do not delete them.

1. Font lanes. Question brand_font on brand:habitat returns Manrope from the PDF or the brand note, lane brand_identity, authority CLIENT_APPROVED when the PDF is read. Question ui_font returns Inter, lane ui_chrome. These are two answers. Status is not CONFLICTED.

2. Brand voice. Question brand_voice returns a short passage from Habitat-Brand.md with source_id habitat-vault-brand. Mark the output kind EVIDENCE. Do not add an interpretation field that states a new fact.

3. Conflict. Question headline_case. Habitat-Brand.md says lowercase-only. Habitat-Strategy.md says uppercase headlines. Same lane, same authority OPERATIONAL. Result CONFLICTED. Do not pick a winner. Do not raise one authority to hide the conflict.

4. Empty field. canonical brand_voice is empty or blank. The vault note has the voice passage. Status NOT CANONICAL, not UNKNOWN. Answer may still carry the source passage as non-canonical evidence. Do not write it into a canonical store.

5. Absent. Question habitat_submarine_policy, no source lists that key. Bounded search runs. Status NOT FOUND or UNKNOWN exactly as the current resolver already does for no hits. attempt_log lists the sources considered and why each was skipped. Do not add a fake source to force UNKNOWN.

## Security tests

- path ../ outside an allowlisted root is INACCESSIBLE
- a source scoped brand:uma-blu is not retrieved for brand:habitat
- bytes over the cap do not get fully ingested
- a .png or other unsupported type is INACCESSIBLE
- logs and provenance do not include secret file contents

## Commit

One commit. Message: feat(intel): prove Habitat authorised knowledge on live sources
Stage only this slice. Do not push.

## Done line

COMMIT: <hash>
TESTS: PASS=<n> FAIL=0
LIVE: font=<status> voice=<status> conflict=<status> empty=<status> absent=<status>
EXIT:0
