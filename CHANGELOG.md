# Changelog

## v0.3.9 (2026-11-23)

- Fixed: on some dual-SIM boots PhhIms started before the SIM was loaded and never registered with IMS until it was restarted by hand. The module now restarts PhhIms once the SIM is loaded. Contributed by undekasteam, tested with Turkcell (Turkey).
- New tested setups: Turkcell (Turkey) and A1 (Bulgaria). On A1, incoming calls arrive over 3G; see Known issues in the README.

## v0.3.8 (2026-11-20)

- Fixed: two ringing tones at once while an outgoing call rang, on networks that send their own ringback tone (seen on VIVACOM, Bulgaria). The phone played its own tone on top of the network's. Now the network's tone replaces the phone's own as soon as it arrives; networks without their own tone (o2, ONDO) keep the phone's tone as before. Found in a tester's log; the module patches PhhIms.

## v0.3.7 (2026-11-20)

- Module list: author and description no longer call this an o2 edit; it runs with several carriers and ROMs now. No functional change.

## v0.3.6 (2026-11-20)

- Fixed: the speakerphone button did nothing during a call. PhhIms took over the call's audio mode, and Android then ignored the speaker request from the phone app. PhhIms now leaves the audio mode to the phone app when it has already set it. Found in a tester's audio dump; the module patches PhhIms.

## v0.3.5 (2026-11-19)

- Status button: in the first minute after a reboot it showed the IMS state and call count from before the reboot, and could report "PROBLEM: IMS is not registered" although IMS was fine. It now only shows the current boot.

## v0.3.4 (2026-11-19)

- Fixed: when you hung up an incoming call first, the other phone could stay in the call. PhhIms sent its hang-up message on the connection the call had come in on, and some networks silently ignore requests there (seen on VIVACOM, Bulgaria). The hang-up now goes over the regular connection, like for outgoing calls, where it was always answered. Found in a tester's log; the module patches PhhIms.

## v0.3.3 (2026-11-13)

- Fixed: a stuck call screen after an outgoing call that the network answered without sending audio, or that the other side ended before any audio arrived. PhhIms ended such a call but did not tell Android, so the screen stayed on "dialing", hanging up did nothing and only a reboot helped. The call now ends normally. Found in a tester's log (Android 16, ONDO); the cause is in PhhIms, the module patches it.
- The PhhIms app is now signed by the build. Android accepts the new signature of a system app on the next boot and keeps its data.

## v0.3.2 (2026-11-13)

- Status button: recognises when the network offers no IMS server address (P-CSCF), the usual sign of a missing IMS APN, and shows the APN steps. Before, it kept saying "WAIT: IMS is still registering", even hours after boot.
- Status button: reports a problem when IMS has been registering for more than 5 minutes.

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
