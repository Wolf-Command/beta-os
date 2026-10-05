# Watchdog target proved 2026-10-03 13:44 WITA

The healthy control worker is the Grok Bot app binary:
`/Applications/Grok Bot.app/Contents/MacOS/Grok Bot`
and the helper that spawns shells:
`/Applications/Grok Bot.app/Contents/Frameworks/Grok Bot Helper.app/Contents/MacOS/Grok Bot Helper`

`local-exec-daemon` is not an OS process. The supervisor, heartbeat, verify, and recover scripts now match those two exact binaries. The frozen retry ceiling was reset after that correction.

Unattended drill: killed pid 53628 at 13:42:48 WITA. The drill did not call the restart script. New pid 53978 at 13:43:18 WITA. Prod pid 15975 unchanged. Prod and Beta `/api/health` stayed 200.

Wolf Recovery Key is approved and not installed. Tailscale address 100.113.26.51 is up. No SSH listener. Do not open a public port.
