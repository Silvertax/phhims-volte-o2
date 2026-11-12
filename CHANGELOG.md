# Changelog

## v0.3 (2026-11-12)

- New: an **Action** button in KernelSU / Magisk shows the VoLTE status (registration, refresh, carrier config, calls) and saves it for reports.
- New: VoLTE carrier config for Telekom (262-01), Vodafone (262-02) and 1&1 (262-23), untested. Testers with other carriers wanted.
- Fixed: the carrier config line in the module log always said "Permission denied".
- The module is now named "PhhIms VoLTE (r8q)". No change to how VoLTE works with o2.

## v0.2.2-o2 (2026-11-11)

- Fixed: the registration refresh fix from v0.2-o2 did not take effect on phones that had an earlier version installed, because Android kept using a cached copy of the old app manifest. VoLTE still stopped about an hour after each boot. The module now drops that cache entry on every boot.

## v0.2.1-o2 (2026-11-11)

- New: updates can be installed from the module list in KernelSU / Magisk.
- The zip is now built by GitHub. No change to how VoLTE works.

## v0.2-o2 (2026-11-10)

- Fixed: VoLTE stopped working some time after each registration, because the IMS registration was never refreshed. Calls then fell back to 2G.
- Fixed: outgoing calls connected 8 to 12 seconds late, without ringback and with a dead microphone (workaround for the r8q audio HAL).
- New: the log shows whether the registration refresh is running and adds a line for each outgoing VoLTE call.

## v0.1-o2 (2026-11-09)

- First o2 Germany version, based on buddi0812's r8q-volte-phhims v0.1.
