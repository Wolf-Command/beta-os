# Credential discovery

28 Sep 2026. Owner credential rule 06:48 WITA. Names, locations, and status only. No value is printed. No credential was copied into the repo. No permission was widened. No external send was made.

Statuses:

- FOUND AND USABLE — a harmless read inside the existing scope succeeded
- FOUND BUT NEEDS VALIDATION — material is present and this pack did not call the service
- FOUND BUT EXPIRED/INVALID — the stored expiry is past, or the existing read was denied
- REFERENCE FOUND BUT SECRET MISSING — a location names the integration and the secret field is empty
- NOT FOUND AFTER AUTHORISED SEARCH — the authorised locations were searched and nothing for that integration was there

Authorised locations searched: `~/.openclaw/credentials/`, `~/.openclaw/wolf-secrets.env`, `~/.openclaw/wolf-output/decisions.md`, `~/.openclaw/secrets-vault/`, `~/.openclaw/data/esb.sqlite`, `~/.openclaw/state/bank`, Obsidian vault `/Users/wolfterminal/WolfCommandSystem/WolfCommand` (filename hits only), `~/.openclaw/workspace` (filename hits only, scan stopped at 8001 files), `beta-os/.env` and `.env.example` (key names only), `~/Library/LaunchAgents` (labels and env key names), keychain by service name without `-w` or `-g`, `~/.cloudflared/` (entry names and config keys, not file contents), rclone remote names.

## Register and named integrations

| integration | register | mechanism | location | status | this session | remaining ask |
| --- | --- | --- | --- | --- | --- | --- |
| B2 | CAP-DR-01 | rclone remote plus a JSON file in the credential directory | remote `b2`; file `backblaze-b2.json`; launch agents `com.wolfcommand.backup`, `com.wolfcommand.footage-b2-sync`, `com.wolfcommand.b2-archive-proof` | FOUND AND USABLE | `rclone listremotes` exited 0. `rclone lsd b2:` exited 0 and returned one entry. The entry name is not repeated here | none |
| Cloudflare Access | CAP-MSC-02 | cloudflared config and certificate. Beta auth mode is `cloudflare_access` | `~/.cloudflared/config.yml`, `cert.pem`, a tunnel credentials json, a beta hostname token file. Audience name `BETA_CF_ACCESS_AUD` is set in `beta-os/.env`. The audience value was not printed | FOUND BUT NEEDS VALIDATION | Config keys are present. No Cloudflare API call. The public login redirect was already proved in F2 | none |
| Cloudflare R2 | not a separate CAP. Present beside B2 | JSON file and rclone remote `r2` | `cloudflare-r2.json` (status field reads active). Remote `r2` | FOUND BUT EXPIRED/INVALID | `rclone lsd r2:` exited 1. StatusCode 403, `AccessDenied`. Token text was not printed. Do not widen the token | none. The secret is present. This pack does not ask for a broader token |
| Yanolja | CAP-INTG-01 | JSON file. No Wolf reader | `yanolja.json` | REFERENCE FOUND BUT SECRET MISSING | `api_key` empty. `auth_code`, `host`, `hotel_code`, and `property` are set. No API call | The `api_key` field in that existing file is empty. Do not paste a key in chat. Place a key in that field, or record that the empty field is intentional |
| ESB read | CAP-INTG-02 | local warehouse sqlite | `~/.openclaw/data/esb.sqlite` | FOUND AND USABLE | Opened `mode=ro`. `sales` table is present. No amount was read. Settlement API stays unavailable | none |
| ESB API | same capability, different material | JSON files and env names | `esb-core.json`, `esb-production.json`, names in `wolf-secrets.env`. Launch agent `com.wolfcommand.esb-ingest` | FOUND BUT NEEDS VALIDATION | Password and token fields are set. No ESB call. Write-related env names are set; they were not used | none |
| Metricool | CAP-INTG-05 | shared JSON. Beta client refuses that path and is disabled | `metricool.json` (`user_token` and `user_id` set). `beta-os/.env` has `BETA_METRICOOL_ENABLED=false` and `BETA_METRICOOL_WRITE_ENABLED=false`. No Beta credential file | FOUND BUT NEEDS VALIDATION | `metricool_status` path was not required. No network call. Beta will not load the shared file while disabled | none. Do not enable write. Do not copy the shared file into the repo |
| Klaviyo | CAP-CRM-04 | JSON file. Reader is `scripts/core/habitat_klaviyo_reader.py` | `klaviyo.json`. GGV and Atrium status fields read ACTIVE. Habitat has a private key and no status field | FOUND BUT NEEDS VALIDATION | No Klaviyo call. The reader can write the lead spine, so it was not run | none |
| Email / Gmail | CAP-INTG-03 | OAuth token files, plus an SMTP env on one launch agent | `google-oauth.json`, `google-token.json` (expiry unexpired; scopes include gmail.readonly, gmail.modify, gmail.send), `google-token-mrwolf.json` (gmail.readonly, expiry past). Plist `com.wolfcommandsystem.sc-autosend` env keys `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` are set | primary token FOUND BUT NEEDS VALIDATION. Second token FOUND BUT EXPIRED/INVALID. SMTP FOUND BUT NEEDS VALIDATION | No Gmail call. No SMTP send | none. Do not paste a refresh token. The expired second file is not a request for a new password |
| Google Drive | CAP-INTG-03 | same primary token | `google-token.json` scopes include drive, drive.file, drive.readonly. Launch agents include `com.wolfcommand.drive-watcher` | FOUND BUT NEEDS VALIDATION | No Drive call | none |
| Google Calendar | CAP-INTG-03 | same primary token | scope `calendar` on `google-token.json` | FOUND BUT NEEDS VALIDATION | No Calendar call | none |
| Bank read-only | CAP-INTG-04 | file archive. No bank API file in the credential directory | `~/.openclaw/state/bank`. This session counted 65 files: 30 pdf, 16 csv, 7 xls, 7 json, 2 jsonl, 1 xlsx, 1 txt, 1 bak. Contents were not opened. The 27 Sep pack already read the archive | FOUND AND USABLE | Count only. No amount parsed. No bank mutation | none. There is no bank API key to supply. Banks still own the accounts |
| NAS | content library roots, not a CAP-INTG row | mounted volumes and an rclone remote. DSM API account is a separate gap | `/Volumes/01-Media-Library`, `/Volumes/00-Editing-Workspace-3`, `/Volumes/02-Stock-Assets-1`, `/Volumes/03-Templates` are directories. `rclone lsd b2nas:` exited 0, one entry. `synology.json` has host and port set and no password field. Launch agent `com.wolfcommandsystem.nas-keepalive` | mounts and `b2nas` FOUND AND USABLE. DSM API REFERENCE FOUND BUT SECRET MISSING | No NAS write. The working path is the mount | none. Keep the mount. Do not ask for a DSM password for this pack |

## Other files in the same store

The directory also holds files that are not on the P0/P1 integration register: `apify.json`, `calendly.json`, `canva.json`, `canva-login.json`, `clickup.json`, `cloudbeds.json`, `cloudinary.json`, `descript.json`, `discord-pairing.json`, `google-gemini.json`, `notion.json`, `openai.json`, `perplexity.json`, `replicate.json`, `serpapi.json`, `telegram-pairing.json`, `whatsapp-pairing.json`, `youtube.json`, and several token text files. They were not opened beyond key names. They are not asks. They were not migrated.

Obsidian and the workspace have filename hits for yanolja, klaviyo, esb, nas, bank, metricool, and gmail. Those hits were not treated as a second secret store. Line text was not copied.

## Matt

The only credential ask after this search is the empty Yanolja `api_key`, and only as an action in the existing file or a written decision that the empty field is intentional. Every other integration above has material on disk or a working read. Do not send passwords, tokens, or keys in chat.
