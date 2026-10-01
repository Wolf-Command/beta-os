# Wave 2.03 — CRM identity

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No master person table was written. Prod `:8787` was health-checked and not restarted. The Habitat sheet was not written.

## Three stores, not one record

`one_crm` is false. `catalog/crm_identity.sqlite` is not a file. `master_table_written` is false.

### Habitat sheet

Source: `state/habitat-leads-glance.json`, schema `habitat-leads-glance/v1`, as of `2026-10-01T09:43:42+08:00`. Sheet `1HMNAXUQ_seF4RGff66N402wp25rBOvfucaDNToRzEZM`, title `Habitat Leads & Owners `, tab `Leads`, Drive modified `2026-09-30T08:09:03.001Z`. `real_lead_count` 271. `raw_data_rows` 286. Prior snapshot count on 2026-08-21 was 232. `authorised_read` true. `write` false. `excluded_test_junk` true.

This glance is a count. `email_rows` and `phone_rows` are null. Join keys UNAVAILABLE. The sheet was not fetched again and was not written.

### core_leads

Catalog `catalog/content_library.sqlite`, table `core_leads`, opened read-only. Count 8. `source_system` is `fixture` only. Provenance has no email or phone keys. Email rows 0. Phone rows 0. These rows are not the Habitat sheet.

### Guest profile

Source: `/Users/wolfterminal/.openclaw/workspace/wolf-system/state/guest-profiles.db`, opened read-only. Guests 1. Visits 1. Observations 2. Visit business `AMG`. Email rows 1. Phone rows 1. `values_omitted` true. The name, email, and phone were not copied into the API, the page, or this file.

### GGV onboard

The catalog has no invite or onboard identity table. State SHELL. Count is null. That is not zero clients. The invite flow was not built.

## Join

State UNAVAILABLE. `compared` false. `matched_pairs` null. Null is not a completed dedupe of zero matches.

No two of these reads carry email or phone together. The AMG guest has both fields. The Habitat glance does not carry row keys. The fixture leads do not carry them. No pair was compared and no link was written.

## HTTP

Verified 2026-10-01T22:00:18+08:00 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed.

| Path | Result |
|---|---|
| `GET /api/crm/identity` | 200, join UNAVAILABLE, matched_pairs null, one_crm false, habitat 271 |
| `GET /crm/identity` | 200, title CRM identity, four tiles, none start open |
| `POST /api/crm/identity` | 405 `writes_off` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON and adds the GGV onboard tile in the browser. A browser click-through was not done.

## Tests

`scripts/tests/test_crm_identity_wave2_03.py`: 12 passed, 0 failed. The test asserts the glance, the catalog, and `guest-profiles.db` mtimes are unchanged, and that `crm_identity.sqlite` is still absent.

## Left undone

A real email or phone join across Habitat, GGV, and AMG. A master person. The GGV invite flow. `staff_ready`.

## NEXT — Wave 2.04, not started

Menu engineering, register row `need.menu.engineering`. Not started.
