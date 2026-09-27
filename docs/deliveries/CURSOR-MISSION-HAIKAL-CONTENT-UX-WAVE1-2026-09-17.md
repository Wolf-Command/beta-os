# CURSOR MISSION — Haikal Beta Content UX Wave 1

Workspace: `/Users/wolfterminal/beta-os`
Branch: `build/wolf-command-rebuild`
Commit: `fix(content): Haikal Beta UX wave 1 — titles status library brand tint`

Production sacred. Beta `:8788` / beta-os only. Do NOT touch Upload or Smart Upload.

Read: docs/deliveries/HAIKAL-BETA-CONTENT-FEEDBACK-2026-09-17.md

## Implement (all six)

1. **Plan titles** — human format e.g. `Habitat Fortnight Sep 14—27` wherever plans are titled/displayed (generator + existing display). Apply to all brands with same pattern. Do not mass-rewrite historical DB unless display layer can format on read (prefer format-on-read + new creates).

2. **Page headers** — short human one-liner under each content page title (Habitat board, Library, plan views, etc. that Haikal uses). Plain English. No AI fluff.

3. **List status** — on post/story list rows, show status and allow change without opening Edit first (dropdown or chips). Keep Edit path working. Same status values as existing machine.

4. **Library Select all / Deselect all** — next to existing checkbox zip bulk download. Clear labels.

5. **Brand colour tint** — each brand content page uses that brand’s colour tokens for chrome/accents/header wash. **Do not change fonts** — keep current shared typeface.

6. **Library search** — default: big search + brand filter only. Button/link “Detailed filters” expands accordion with content type (image/video/etc), location, and other filters already supported. Collapse by default.

## Do not
- Change Upload / Smart Upload
- Touch Production / wolf-system / :8787
- Invent Metricool publish
- Broad rewrite of Content Machine

## Prove
- Manual sanity notes in delivery doc
- If automated UI tests exist, extend lightly; else document click path
- Commit exact message. EXIT:0 / EXIT:1
