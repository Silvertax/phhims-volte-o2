# Changelog

## v0.3.1 (2026-11-12)

- New: Android 16 support as a test. The module carries overlays for Android 17 (SDK 37) and Android 16 (SDK 36) and installs the matching set. Untested on Android 16 so far.
- New: the installation stops with a clear message on other Android versions. Before, the module installed but could not work there.
- Status button: shows the Android version, how many of the three overlays are active and whether the IMS feature is declared, with a matching verdict. Tapped within 3 minutes of boot, it says to wait instead of reporting a problem.

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
