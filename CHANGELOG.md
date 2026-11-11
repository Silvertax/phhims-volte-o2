# Changelog

## v0.2-o2 (2026-11-10)

- Fixed: VoLTE stopped working some time after each registration, because the IMS registration was never refreshed. Calls then fell back to 2G.
- Fixed: outgoing calls connected 8 to 12 seconds late, without ringback and with a dead microphone (workaround for the r8q audio HAL).
- New: the log shows whether the registration refresh is running and adds a line for each outgoing VoLTE call.

## v0.1-o2 (2026-11-09)

- First o2 Germany version, based on buddi0812's r8q-volte-phhims v0.1.
