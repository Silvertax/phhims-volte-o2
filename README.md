# PhhIms VoLTE for the Galaxy S20 FE (r8q)

KernelSU / Magisk module that brings VoLTE and SMS over IMS to the Snapdragon Galaxy S20 FE (r8q), using the open-source IMS stack PhhIms. It started as an o2 Germany (Telefónica) version of **[buddi0812/r8q-volte-phhims](https://github.com/buddi0812/r8q-volte-phhims)** and now runs with several carriers and ROMs; nine faults in the setup and in PhhIms are fixed along the way (see [Fixed faults](#fixed-faults)). **Testers are wanted**: other carriers, other ROMs and Android 16, see [Testers wanted](#testers-wanted).

## Credits

- **[buddi0812](https://github.com/buddi0812)**: original module ([r8q-volte-phhims](https://github.com/buddi0812/r8q-volte-phhims) v0.1, made for Airtel India on PixelOS 17): the PhhIms patch for r8q, the KernelSU module and the overlays, which this project builds on. His README is kept as [ORIGINAL-README.md](ORIGINAL-README.md).
- **PhhIms**: Pierre-Hugues Husson ([phhusson/ims](https://github.com/phhusson/ims)) and the [krazey/ims](https://github.com/krazey/ims) contributors
- **Maintainer**: [Silvertax](https://github.com/Silvertax): o2 adaptation, the fixes since v0.2, status button, builds
- **Testers** on ONDO (Mongolia) and VIVACOM (Bulgaria): their logs found the faults fixed in v0.3.3, v0.3.4, v0.3.6 and v0.3.8
- **Contributors**: [undekasteam](https://github.com/undekasteam): restart of PhhIms after an early-boot null IMSI on dual-SIM setups (v0.3.9), tested on Turkcell

## Status

Experimental. Tested so far:

- **o2 Germany (262-07):** Galaxy S20 FE SM-G780G, unofficial LineageOS 24.0 (r8q Cloud, Android 17), KernelSU v3.3.1 in the kernel, SELinux enforcing, with a dedicated IMS APN. In daily use since v0.2.2-o2.
- **ONDO Mongolia (428-33), reported by a tester:** SM-G781N, Lunaris AOSP (Android 16), KernelSU 3.3.1 with the Shadow kernel, v0.3.2. IMS registers and calls work in both directions once an IMS APN is added. The stuck call screen seen there is fixed in v0.3.3.
- **VIVACOM Bulgaria (284-03), reported by a tester:** SM-G781B, LineageOS 24.0 nightly (Android 17), v0.3.3 to v0.3.8. IMS registers and calls work in both directions over VoLTE; the speakerphone works with v0.3.6. HD voice works between VIVACOM phones in both directions; calls with A1 use normal quality, see [Known issues](#known-issues). The caller staying in the call after a local hangup is fixed in v0.3.4 (confirmed); with v0.3.8 outgoing calls ring with one tone instead of two (confirmed).
- **A1 Bulgaria (284-01), reported by the same tester:** same phone, v0.3.8. IMS registers once the ROM's default APNs are restored, and outgoing calls go over VoLTE. Incoming calls arrive over 3G instead, see [Known issues](#known-issues).
- **Turkcell Turkey (286-01), reported by a contributor:** SM-G780G, official LineageOS 24.0 nightly (Android 17), Magisk 28.1. IMS registers and VoLTE calls work once the `ims` APN is added. On dual-SIM boots PhhIms could start before the SIM was loaded and stay unregistered; fixed in v0.3.9.
- **Vodafone Turkey (286-02), reported by a tester:** LineageOS 24.0 (Android 17), SukiSU. VoLTE calls in both directions and SMS work over 24 hours. The speakerphone can be switched on outgoing calls but not on incoming ones, see [Known issues](#known-issues).
- **Reliance Jio India (405-870), reported by a tester:** SM-G781B, official LineageOS 24.0 nightly (Android 17), KernelSU, v0.3.9. No APN had to be added (the ROM's Jio APNs include `ims`), and PhhIms uses its built-in Jio profile. IMS registration, calls in both directions, SMS, airplane mode, reboot and the periodic re-registration all work. IMS only registers on LTE, not on 5G standalone, and calls use normal quality, see [Known issues](#known-issues).

The details below refer to the o2 setup.

- **Worked:** IMS registration, VoLTE calls in both directions, SMS over IMS, mobile data during calls, speakerphone (from v0.3.6), re-registration after reboot
- **Not available:** Wi-Fi calling, video calls
- **Fixed:** nine faults so far, see [Fixed faults](#fixed-faults).
- **How far this is tested:** with v0.2.2-o2, incoming and outgoing calls still went over VoLTE 13 hours after boot, and the registration was refreshed on schedule. The single 2G fallback noted under v0.2-o2 fits the fault corrected in v0.2.2-o2; there is no log of that call.
- **Magisk:** works on the Turkcell setup (Magisk 28.1); the others use KernelSU or a fork of it. The module mounts its files itself (overlayfs in `post-fs-data.sh`) without anything KernelSU-specific.

## Requirements

- Galaxy S20 FE Snapdragon (r8q) with a ROM on **Android 17**, or Android 16 as a test from v0.3.1. Static overlays only load when their SDK version matches the ROM, so the module carries overlays for SDK 37 and SDK 36 and `customize.sh` installs the matching set. Other Android versions are refused at install time.
- Root with KernelSU or Magisk (Magisk not tested yet, see Status)
- Only **one** PhhIms/VoLTE module active at a time

## IMS APN

If IMS does not register, check the APNs first: many carriers need a separate APN `ims` with the type `ims`, and no other APN may carry that type. Otherwise the phone uses the internet APN for IMS, the network gives no IMS server address (P-CSCF), PhhIms never registers and calls go out as classic calls. On an LTE-only network such calls stay silent. From v0.3.2 the status button names this case (`IMS server: none offered by the network`).

Seen so far with o2 Germany (the preset APN `internet` also had the type `ims`) and with ONDO Mongolia, where IMS registered once the IMS APN was added (reported by a tester). Fix:

1. Settings → Network & internet → SIMs → your SIM → Access Point Names
2. Add an APN: APN `ims`, APN type `ims`, APN protocol IPv4/IPv6
3. Open your internet APN: if its APN type is empty or contains `ims`, set it to `default,supl,mms`
4. Toggle airplane mode on and off, wait two minutes, tap the status button

`ims` is the usual name of the IMS APN. If IMS still does not register, ask your carrier for theirs.

## Installation

1. Download the latest `phhims_volte-*.zip` from [Releases](../../releases/latest).
2. KernelSU / Magisk → Modules → Install → select the zip → reboot.
3. Two minutes after boot, tap the module's **Action** button in KernelSU / Magisk (see [Status button](#status-button)). It should end with `OK: VoLTE is ready.`
4. Turn on VoLTE under Settings → Network & internet → SIMs → your SIM, then test a call and an SMS.

Later versions can be installed from the module list in KernelSU / Magisk: the module carries an update link (`updateJson`), so the manager offers an update when a new release is out. This works from v0.2.1-o2 on. If no update shows up, check that the manager's automatic update check is on in its settings and reload the module list; a module that waits for a reboot after an install is not checked. You can always install the zip from [Releases](../../releases/latest) by hand.

To uninstall, remove the module in KernelSU / Magisk and reboot.

## Status button

From v0.3 the module has an **Action** button in the module list of KernelSU and Magisk (Magisk 28 or later). It changes nothing and shows:

- module version, device, ROM, carrier and network code
- whether IMS is registered and offers voice and SMS (tracked from the radio log by `service.sh`, since not every ROM dumps this state)
- the effective `carrier_volte_available_bool` and which config layer sets it
- whether the registration refresh is scheduled, when it is due and when it last ran
- outgoing VoLTE calls since boot and failed call setups in the radio log
- from v0.3.10, a hint when IMS is not registered because the phone is on 5G standalone
- a verdict: `OK`, `WAIT`, `CHECK` or `PROBLEM`

Before v0.3.5 it could show the state from before a reboot during the first minute after boot. The report is also saved to `/sdcard/Download/phhims-volte-status.txt`. It contains no phone numbers, so a screenshot or the file can be posted as it is.

## Known issues

- **No IMS on 5G standalone (NR SA):** PhhIms has no voice over 5G (VoNR). On a 5G standalone network (seen on Jio True5G) Android reports voice as out of service, and PhhIms never registers (`not ready for IMS after service state callback: state=1` in the radio log). Set the preferred network type to LTE (Settings, Network & internet, SIMs, Preferred network type); the Jio tester used `cmd phone set-allowed-network-types-for-users -s 0 1000001000000000000` (LTE and LTE-CA), which survives reboots. 5G non-standalone, where the phone shows 5G but voice runs over LTE, is not affected. From v0.3.10 the status button says so when IMS is not registered on 5G standalone.
- **No HD voice on Jio:** Jio offers AMR-WB only in octet-aligned mode (`octet-align=1`), and PhhIms only supports the bandwidth-efficient mode, so it falls back to AMR-NB in both directions. Support for octet-aligned AMR-WB is being looked into.
- **Speakerphone does not switch on incoming calls** (Vodafone Turkey tester): it works on outgoing calls since v0.3.6. PhhIms may be taking over the call's audio mode on incoming calls the same way it did on outgoing ones before v0.3.6; this is being looked into.
- **No HD voice between VIVACOM and A1:** Calls between the tester's S20 FE and another VIVACOM phone use HD voice in both directions, with the HD icon on both phones. Calls with his family on A1 stay in normal quality: VIVACOM answers PhhIms' HD offer with AMR-NB, and on incoming calls it converts, so the S20 FE shows HD while the A1 phone does not. Whether a stock phone with the same SIM gets HD with A1 is still being checked; if not, it is the connection between the two networks and not the module.
- **Incoming calls on A1 arrive over 3G:** A1 delivers incoming calls to this phone over 3G instead of VoLTE (CS fallback), so IMS drops during the call and registers again afterwards. Outgoing calls use VoLTE. The likely cause is the modem: Android tries to tell it that IMS is registered, but the S20 FE's radio does not offer that interface (`updateImsRegistrationInfo ... service IMS is not available` in the radio log), so the modem keeps reporting a preference for 3G calls, which A1 follows. o2 and VIVACOM deliver calls over VoLTE regardless. Changing this would need a modem setting, which is not planned.
- **Outgoing call without audio** (ONDO tester, once): the network answered, but no audio arrived within 2 seconds, so PhhIms ended the call. Since v0.3.3 such a call ends normally instead of hanging. There is no radio log of the call setup; it may have been fault 9 (fixed in v0.3.10), which looks the same.
- **Speakerphone switching takes about a second** after tapping the button: Android moves the running call audio to the other device. The module is not involved in that.
- The fix for the late, silent outgoing calls is a workaround in the module (see [Changes in v0.2-o2](#changes-in-v02-o2-2026-11-10), fix 2); the proper fix belongs in the ROM's audio HAL.

## Fixed faults

These probably affect anyone running PhhIms on this phone without the system UID. Details in the change notes below and in [CHANGELOG.md](CHANGELOG.md).

| # | Fault | Fixed in | Confirmed |
|---|---|---|---|
| 1 | The IMS registration was never refreshed, calls fell back to 2G after an hour | v0.2-o2 | yes (o2) |
| 2 | Fix 1 did not take effect: Android kept a cached manifest | v0.2.2-o2 | yes (o2) |
| 3 | Outgoing calls connected 8 to 12 seconds late with a dead microphone (audio HAL workaround) | v0.2-o2 | yes (o2) |
| 4 | Stuck call screen after an outgoing call that got no audio | v0.3.3 | not seen again (ONDO) |
| 5 | Other phone stayed in the call after hanging up an incoming call first | v0.3.4 | yes (VIVACOM) |
| 6 | Speakerphone button did nothing | v0.3.6 | yes (VIVACOM) |
| 7 | Two ringback tones at once on outgoing calls (the network's and the phone's own) | v0.3.8 | yes (VIVACOM) |
| 8 | On dual-SIM boots PhhIms could start before the SIM was loaded and stay unregistered (`imsi must not be null`) | v0.3.9 | yes (Turkcell) |
| 9 | Outgoing calls stayed on "dialing" and ended 2 seconds after the other side answered, when the SDP answer came in the `180 Ringing` and not in the `200 OK` | v0.3.10 | not yet (o2) |

## Testers wanted

The goal is VoLTE on the r8q with as many custom ROMs and carriers as possible. So far it runs on seven setups (see [Status](#status)). Every report helps, whether it works or not:

- **Other carriers:** nothing in the fixes depends on the carrier, and the bundled PhhIms applies a persistent VoLTE carrier-config override for any SIM on its own (`ensureVolteCarrierConfig` in buddi0812's patch), so other carriers may well work already. A carrier that does not work yet can often be added once its log shows what it expects.
- **Other ROMs:** any AOSP-based ROM on Android 17 or 16 (LineageOS, Lunaris, PixelOS, …). buddi0812's original module was made on PixelOS 17.
- **Android 16:** supported as a test since v0.3.1, working for one tester so far.
- **Other Android versions:** not supported yet, because the overlays have to be built for each Android version. If you run another version and want to test, say so in a report.

The carrier list in `overlays/cc/res/xml/vendor.xml` additionally enables VoLTE for o2 (262-03, -07, -08, -11, -77) and, since v0.3, Telekom (262-01), Vodafone (262-02) and 1&1 (262-23). Brands on these networks use the same codes. The list only matters on ROMs that honour the overlay; the status button shows which layer sets the value.

**How to report:** install the module, add the IMS APN if needed (see [IMS APN](#ims-apn)), tap the status button two minutes after boot and open a [test report](../../issues/new?template=carrier_report.yml) with a screenshot of it. If calls fail, add a radio log taken right after the failing call (see [Troubleshooting](#troubleshooting)). The status report contains no phone numbers; the radio log does unless you use the masking command.

## Troubleshooting

- **Start with the status button.** Its last line names the most likely problem.
- **Boot-loop protection:** if the phone fails to finish booting twice in a row, the module skips its mounts on the next boot. Creating `/data/adb/phhims-volte.disable` skips them manually.
- **Logs for a call** (PhhIms logs to the radio buffer):
  ```sh
  su -c 'logcat -b all -v threadtime > /sdcard/Download/volte_log.txt'
  ```
  Make a few calls, stop with Ctrl+C and attach the file together with `/data/adb/phhims-volte.log` when [reporting an issue](../../issues/new/choose). The log contains phone numbers.
- **Radio log right after a failing call**, with phone numbers masked (in Termux or `adb shell`):
  ```sh
  su -c "logcat -d -b radio | sed -E 's/[0-9]{7,}/NUM/g' > /sdcard/Download/volte-radio.txt"
  ```
  Look it over before posting it publicly.

## Changes in v0.3.10 (2026-11-26)

**Outgoing calls without audio, ended 2 seconds after the answer** (o2, in my own radio log). An evening of outgoing calls to a landline exchange all stayed on "dialing" with no ringing tone; the other side picked up, heard nothing, and the call ended about 2 seconds later. The log shows the exchange of one of them: o2 sent the `180 Ringing` reliably (`Require: 100rel`, answered with `PRACK`) and with the SDP answer in it, so the `200 OK` came without SDP, as RFC 3262 allows. PhhIms starts its media threads only from a `183` with SDP or from a `200 OK` with SDP, so neither the decoder nor the encoder ran: no RTP went either way, and after 2 seconds the post-answer RTP check ended the call (`No post-answer RTP within 2000ms`). It also reports an `18x` as progressing only without SDP, so Android stayed on "dialing" and played no ringback. After airplane mode on and off, the phone registered at a different P-CSCF, which sent the `180` without `100rel` and the SDP again in the `200 OK`, and the same number worked.

- Fix: a `200 OK` without SDP starts the media threads from the SDP answer of the early dialog if they are not running yet (after a `183`, they already are, so nothing changes there). A `180 Ringing` with SDP is reported as progressing like one without, so the phone shows "ringing" and plays its ringback tone. Other `18x` with SDP are handled as before. [`patches/0007-media-on-final-answer-without-sdp.patch`](patches/0007-media-on-final-answer-without-sdp.patch) is the source change; `build.sh` applies it to the bytecode like the earlier fixes.

## Changes in v0.3.9 (2026-11-23)

**PhhIms unregistered after some dual-SIM boots** (contributed by undekasteam, tested on Turkcell). `SipHandler` reads the IMSI once, when it is created (`private val imsi = subTelephonyManager.subscriberId`). On dual-SIM boots, PhhIms can start about 3 seconds before the SIM records are loaded, so the IMSI stays empty for the whole process and every registration attempt fails with `java.lang.NullPointerException: imsi must not be null`.

- Fix: `service.sh` watches the radio log for that exception. If it comes from the running PhhIms process, it waits up to 15 seconds for `gsm.sim.state` to report `LOADED` and then restarts PhhIms, which reads the IMSI again. Before the SIM is loaded (for example while the PIN is not entered yet) nothing is restarted; the next exception tries again. The status button never restarts anything. Each restart is noted in the module log.
- The radio log filters in `service.sh` are no longer anchored with `^…$`: the exception is part of a longer, multi-line message, which an anchored pattern does not match. The lines are still checked by tag and text afterwards.

## Changes in v0.3.8 (2026-11-20)

**Two ringback tones on outgoing calls.** A tester on VIVACOM heard two ringing tones at once while his outgoing calls rang. His radio log shows why: after the `183 Session Progress`, VIVACOM sends its own ringback tone as early media (RTP with speech frames before the call is answered), and PhhIms plays it. On every `180 Ringing` without SDP, PhhIms also reports the call as progressing with the audio direction `INACTIVE`, which makes Telephony play the phone's own ringback tone (`ImsPhoneCall.isLocalTone`, `maybeChangeRingbackState: start ringback` in the log). o2 and ONDO send no early media, so only the phone's own tone plays there.

- Fix: the first early-media frame of an outgoing call that carries speech (AMR frame types 0 to 7, not comfort noise or empty frames) reports the call as progressing with the direction `SEND_RECEIVE`, and later `180`s of that call do the same. Telephony then stops its own tone or does not start it. VIVACOM sent comfort noise until the `180` and the tone only afterwards, so the phone's own tone can still sound for about a second before the network's takes over. Without early media nothing changes. [`patches/0006-network-ringback-replaces-local.patch`](patches/0006-network-ringback-replaces-local.patch) is the source change; `build.sh` applies it to the bytecode like the earlier fixes. The patch tool now also edits PhhIms' second dex file, where `PhhMmTelFeature` lives.

## Changes in v0.3.6 (2026-11-20)

**Speakerphone button does nothing.** A tester's `dumpsys audio` during a call (VIVACOM, LineageOS 24.0) showed: Telecom puts the call in `MODE_IN_COMMUNICATION` itself, then PhhIms sets the same mode again when its microphone starts (`SipAudioRecordStarter`). AudioService makes the most recent privileged requester the audio mode owner (`Mode owner: me.phh.ims`), and only the mode owner's communication device counts. Telecom's `setCommunicationDevice(speaker)` was recorded but not applied (`updateCommunicationRoute, preferredCommunicationDevice: null`, active device: earpiece). Whenever Telecom briefly became the owner again (hold, end of call), the speaker switched on at once. The original PhhIms runs as the system UID, the same as Telecom, which hides the problem there.

- Fix: PhhIms sets `MODE_IN_COMMUNICATION` only if the mode is not already set, as its downlink thread already does. If Telecom still has `MODE_IN_CALL` at that moment, nothing changes. [`patches/0005-keep-telecom-audio-mode-owner.patch`](patches/0005-keep-telecom-audio-mode-owner.patch) is the source change; `build.sh` applies it to the bytecode like the earlier fixes.

## Changes in v0.3.4 (2026-11-19)

**Other phone stays in the call after a local hangup of an incoming call.** A tester's radio log (VIVACOM, 284-03) showed: for an incoming call that the user ended first, PhhIms wrote the BYE on the TCP flow the INVITE had arrived on (`Routing local BYE on dialog flow: … incomingWriter=true`). That flow runs from the phone's protected server port to the P-CSCF's client port; TS 33.203 has the phone send requests from its protected client port to the P-CSCF's server port instead. The P-CSCF never answered that BYE, so the caller stayed in the call. BYEs for outgoing calls already used the main flow (`incomingWriter=false`) and were answered with 200 OK every time.

- Fix: `SipRemoteDialogTermination.localDialogRequestWriter` always returns the main outbound flow, which PhhIms reopens if it went dormant. [`patches/0004-local-bye-on-main-flow.patch`](patches/0004-local-bye-on-main-flow.patch) is the source change; `build.sh` applies it to the bytecode like the v0.3.3 fix.
- Networks that accepted the BYE on the incoming flow, if any, also accept it on the main flow: it is the same path the BYE of an outgoing call takes.

## Changes in v0.3.3 (2026-11-13)

**Stuck call screen after an outgoing call.** A tester's radio log showed the sequence: the network answered an outgoing call (200 OK), but no RTP arrived within 2 seconds, so PhhIms sent BYE and ended the call. It then reported the end with only the SIP Call-ID. `PhhMmTelFeature` matches such a report to the outgoing call only if it already knows that Call-ID, which it learns when the call is reported as progressing or connected; neither had happened. The report was taken for an unknown incoming call (`No IMS call listener for cancellation … not falling back to another call`), Android was never told, and the call screen stayed on "dialing". Hanging up did nothing either (`terminateCall without currentCall or pending outgoing INVITE`). The same applies when the other side hangs up before any RTP arrived.

- Fix: both reports now carry `outgoingCall=true`, as PhhIms already does for a local CANCEL, so `PhhMmTelFeature` routes them to the outgoing call and calls `callSessionTerminated()`. [`patches/0003-report-no-media-outgoing-end.patch`](patches/0003-report-no-media-outgoing-end.patch) is the source change; `build.sh` applies the same change to the prebuilt APK's bytecode with [`tools/patch-phhims-dex.py`](tools/patch-phhims-dex.py) (baksmali/smali) and re-signs it.
- Open: why the network sent no audio on that call. The fix makes such a call end cleanly instead of hanging.
- The module's audio workaround did not act on that call (`vendor.calls.slot_id0` was already `2`, not `0`), so it is not involved.

## Changes in v0.2-o2 (2026-11-10)

Two separate faults, both found on the test device. See the correction for fix 1 below.

**1. The IMS registration was never refreshed.** PhhIms renews its registration from an alarm that sends the broadcast `me.phh.ims.ALARM_PERIODIC_REGISTER` through a PendingIntent, and its manifest declares that action as a `<protected-broadcast>`. Android only lets system UIDs send protected broadcasts. Upstream PhhIms runs as `android.uid.system`; this build has no `sharedUserId`, so Android rejected the alarm's broadcast and, because the alarm is re-armed only when it is delivered, it never ran again. The registration expired, the phone still showed it as active, and calls in both directions fell back to 2G until something forced a new registration.

- Fix: the `<protected-broadcast>` declaration is removed from the APK manifest ([`tools/strip-protected-broadcast.py`](tools/strip-protected-broadcast.py), run by `build.sh`, which then re-signs the APK; [`patches/0002-drop-protected-broadcast.patch`](patches/0002-drop-protected-broadcast.patch) does the same when building from source). The receiver is registered as not exported, so still only PhhIms and the system can deliver the broadcast.
- Check on a device: `su -c 'dumpsys alarm | grep -c "tag=.*ALARM_PERIODIC_REGISTER"'` more than an hour after boot prints `0` with the fault and `1` without it.

**2. Outgoing calls crashed audioserver.** When a call is dialled, Telecom first sets `MODE_IN_CALL` and switches to the VoIP mode about 0.1 s later. The r8q audio HAL's `setMode(IN_CALL)` loops until `vendor.calls.slot_id0` or `vendor.calls.slot_id1` leaves `0`; the RIL sets it to `1` for a circuit-switched call. A PhhIms call has no modem call, so the HAL spun until the audioserver watchdog killed audioserver about 6 s later. The call connected late, without ringback, and PhhIms failed to open the microphone.

- Workaround: `service.sh` watches the radio log for PhhIms starting an outgoing call, sets the calling slot's property to `1` and puts it back to `0` after the call unless another call is still up. A proper fix belongs in the ROM's audio HAL.

Also new: `service.sh` logs 65 minutes after boot whether the refresh alarm is queued.

**Correction in v0.2.2-o2 (2026-11-11):** fix 1 did not take effect on phones that had v0.1 installed before. Android caches the parsed manifest of system packages and reuses the entry while the package file is older than the cache file. The module stages its files before the clock is set, so they are dated 2019 and always looked older than the cache entry written when v0.1 was first installed. Android therefore kept the old manifest, including the `<protected-broadcast>`. `post-fs-data.sh` now deletes the module's cache entries on every boot. The earlier "confirmed fixed" for fix 1 was wrong: the refresh alarm was seen queued once, but the registration still expired after an hour.

Checked on the test device on 2026-11-11 with the cache entry removed by hand: Android rewrote the entry at boot, the refresh alarm was still being delivered 150 minutes after boot (`Alarm fired with me.phh.ims.ALARM_PERIODIC_REGISTER` in the radio log; it is only re-armed when it is delivered), and outgoing calls 70 minutes and about three hours after boot connected at once. On every boot the module log now lists the entries it removed (`dropped stale package cache entry …`).

## Changes compared to buddi0812's v0.1 (2026-11-09)

- **Carrier config:** the Airtel India network codes (404/405-xx) were replaced with o2 / Telefónica Germany: 262-07, 262-08, 262-11, 262-03 and 262-77.
- **IMS feature:** the module declares `android.hardware.telephony.ims`. Telephony only starts its ImsResolver, which binds PhhIms, if the ROM declares this feature. If the ROM already does, nothing changes.
- **Power management:** PhhIms is on the system power-save allowlist (`allow-in-power-save`), so Doze and App Standby don't restrict it.
- **Diagnostics:** the log also shows the IMS feature state, the SIM network code, the VoLTE carrier-config value and the power-save state. The package check now matches `me.phh.ims` exactly instead of also matching the overlays.
- **Build script:** `build.sh` builds the overlays and the module zip.
- **Unchanged:** the patch, `post-fs-data.sh`, `uninstall.sh` and the `android`/`phone` overlays. The PhhIms APK is buddi0812's v0.1 build with its manifest changed (see v0.2-o2 above) and, from v0.3.3, two cancellation reports extended (see v0.3.3), from v0.3.4 the local BYE sent over the main flow (see v0.3.4), from v0.3.6 the audio mode left to Telecom (see v0.3.6) and from v0.3.8 the network's ringback tone replacing the phone's own (see v0.3.8).

## Building

**PhhIms APK** (as described by buddi0812): upstream [krazey/ims](https://github.com/krazey/ims) at commit `a3fec01ebc4f51c39026565c4a451fef454637fa` plus [`patches/0001-phhims-for-r8q-pixelos.patch`](patches/0001-phhims-for-r8q-pixelos.patch), [`patches/0002-drop-protected-broadcast.patch`](patches/0002-drop-protected-broadcast.patch), [`patches/0003-report-no-media-outgoing-end.patch`](patches/0003-report-no-media-outgoing-end.patch), [`patches/0004-local-bye-on-main-flow.patch`](patches/0004-local-bye-on-main-flow.patch), [`patches/0005-keep-telecom-audio-mode-owner.patch`](patches/0005-keep-telecom-audio-mode-owner.patch), [`patches/0006-network-ringback-replaces-local.patch`](patches/0006-network-ringback-replaces-local.patch) and [`patches/0007-media-on-final-answer-without-sdp.patch`](patches/0007-media-on-final-answer-without-sdp.patch):

```sh
git clone https://github.com/krazey/ims && cd ims
git checkout a3fec01ebc4f51c39026565c4a451fef454637fa
git apply /path/to/0001-phhims-for-r8q-pixelos.patch
git apply /path/to/0002-drop-protected-broadcast.patch
git apply /path/to/0003-report-no-media-outgoing-end.patch
git apply /path/to/0004-local-bye-on-main-flow.patch
git apply /path/to/0005-keep-telecom-audio-mode-owner.patch
git apply /path/to/0006-network-ringback-replaces-local.patch
git apply /path/to/0007-media-on-final-answer-without-sdp.patch
# edit app/build.gradle: set the SDK path in the bootstrapClasspath line (android-33 platform jar)
./gradlew assembleDebug      # Gradle 8.5, AGP 8.2, Kotlin 1.8.10, NDK 25.1.8937393
```

**Overlays and module zip:**

```sh
BUILD_TOOLS=~/Android/Sdk/build-tools/35.0.0 \
ANDROID_JAR=~/Android/Sdk/platforms/android-33/android.jar \
KEYSTORE=my-key.jks SMALI_DIR=path/to/smali-jars \
PHHIMS_APK=path/to/PhhIms.apk ./build.sh
```

The zip ends up in `dist/`. The script needs `python3` and `java`, and in `SMALI_DIR` the baksmali/smali 2.5.2 jars with their dependencies (the list with checksums is in the workflow). It removes the `<protected-broadcast>` declaration from `PHHIMS_APK` and applies the bytecode fixes of v0.3.3 to v0.3.10 that are not there yet, and re-signs the APK with `KEYSTORE` if it changed anything; an APK built with patches 0002 to 0007 is packed as it is. `aapt2 link` needs `--keep-raw-values` (the script sets it): without it, `mnc="07"` is stored as the integer 7, CarrierConfig reads `"7"` and the entry never matches the SIM.

**Releases:** set `version` and `versionCode` in `module/module.prop`, add the changes to `CHANGELOG.md`, merge, then publish a GitHub release whose tag equals `version`. The workflow in `.github/workflows/build.yml` builds the zip, attaches it to the release and updates `update.json`. It signs the overlays with the repository secrets `KEYSTORE_BASE64` and `KEYSTORE_PASSWORD` if they are set, otherwise with a key made for that build.

## License

GPL-2.0, see [LICENSE](LICENSE), like PhhIms and the original module.
