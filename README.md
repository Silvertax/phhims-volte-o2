# PhhIms VoLTE for the Galaxy S20 FE (r8q)

KernelSU / Magisk module that brings VoLTE and SMS over IMS to the Snapdragon Galaxy S20 FE (r8q), using the open-source IMS stack PhhIms. This is a fork of **[buddi0812/r8q-volte-phhims](https://github.com/buddi0812/r8q-volte-phhims)**, adapted and tested with **o2 Germany (Telefónica)**. **Testers are wanted**: other carriers, other ROMs and Android 16, see [Testers wanted](#testers-wanted).

## Credits

- **[buddi0812](https://github.com/buddi0812)**: original module ([r8q-volte-phhims](https://github.com/buddi0812/r8q-volte-phhims) v0.1, made for Airtel India on PixelOS 17): the PhhIms patch for r8q, the KernelSU module and the overlays. Nearly everything here is his work; his README is kept as [ORIGINAL-README.md](ORIGINAL-README.md).
- **PhhIms**: Pierre-Hugues Husson ([phhusson/ims](https://github.com/phhusson/ims)) and the [krazey/ims](https://github.com/krazey/ims) contributors
- **o2 adaptation**: [Silvertax](https://github.com/Silvertax)

## Status

Experimental. Tested so far:

- **o2 Germany (262-07):** Galaxy S20 FE SM-G780G, unofficial LineageOS 24.0 (r8q Cloud, Android 17), KernelSU v3.3.1 in the kernel, SELinux enforcing, with a dedicated IMS APN. In daily use since v0.2.2-o2.
- **ONDO Mongolia (428-33), reported by a tester:** SM-G781N, Lunaris AOSP (Android 16), KernelSU 3.3.1 with the Shadow kernel, v0.3.2. IMS registers and calls work in both directions once an IMS APN is added. The stuck call screen seen there is fixed in v0.3.3, see [Known issues](#known-issues).

The details below refer to the o2 setup.

- **Worked:** IMS registration, VoLTE calls in both directions, SMS over IMS, mobile data during calls, re-registration after reboot
- **Not available:** Wi-Fi calling, video calls
- **Fixed:** with v0.1 VoLTE stopped working about an hour after each registration and calls fell back to 2G (mobile data pauses during such a call), and outgoing VoLTE calls connected 8 to 12 seconds late with a dead microphone. The audio fix works from v0.2-o2, the registration fix from v0.2.2-o2. See [Changes in v0.2-o2](#changes-in-v02-o2-2026-11-10). From v0.3.3 an outgoing call that gets no audio no longer leaves a stuck call screen, see [Changes in v0.3.3](#changes-in-v033-2026-11-13).
- **How far this is tested:** with v0.2.2-o2, incoming and outgoing calls still went over VoLTE 13 hours after boot, and the registration was refreshed on schedule. The single 2G fallback noted under v0.2-o2 fits the fault corrected in v0.2.2-o2; there is no log of that call.
- **Magisk:** not tested yet; both setups above use KernelSU. The zip installs in the Magisk app as is, and the module mounts its files itself (overlayfs in `post-fs-data.sh`) without anything KernelSU-specific, so it should behave the same.

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

Later versions can be installed from the module list in KernelSU / Magisk: the module carries an update link (`updateJson`), so the manager offers an update when a new release is out. This works from v0.2.1-o2 on.

To uninstall, remove the module in KernelSU / Magisk and reboot.

## Status button

From v0.3 the module has an **Action** button in the module list of KernelSU and Magisk (Magisk 28 or later). It changes nothing and shows:

- module version, device, ROM, carrier and network code
- whether IMS is registered and offers voice and SMS (tracked from the radio log by `service.sh`, since not every ROM dumps this state)
- the effective `carrier_volte_available_bool` and which config layer sets it
- whether the registration refresh is scheduled, when it is due and when it last ran
- outgoing VoLTE calls since boot and failed call setups in the radio log
- a verdict: `OK`, `WAIT`, `CHECK` or `PROBLEM`

The report is also saved to `/sdcard/Download/phhims-volte-status.txt`. It contains no phone numbers, so a screenshot or the file can be posted as it is.

## Known issues

- **Stuck call screen, fixed in v0.3.3** (one tester, Android 16, ONDO): after an outgoing call, the call screen stayed on "dialing" and could not be ended; only a reboot helped. The tester's log showed the cause, see [Changes in v0.3.3](#changes-in-v033-2026-11-13). Not yet confirmed on the tester's phone. If it still happens, save a radio log (see Troubleshooting) **before** rebooting.
- **Outgoing calls without audio** (same tester, once): the network answered, but no audio arrived within 2 seconds, so PhhIms ended the call. Why the audio was missing is not known yet.
- The fix for the late, silent outgoing calls is a workaround in the module (see v0.2-o2, fix 2); the proper fix belongs in the ROM's audio HAL.

## Testers wanted

The goal is VoLTE on the r8q with as many custom ROMs and carriers as possible. So far it runs on two setups (see [Status](#status)). Every report helps, whether it works or not:

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
- **Unchanged:** the patch, `post-fs-data.sh`, `uninstall.sh` and the `android`/`phone` overlays. The PhhIms APK is buddi0812's v0.1 build with its manifest changed (see v0.2-o2 above) and, from v0.3.3, two cancellation reports extended (see v0.3.3).

## Building

**PhhIms APK** (as described by buddi0812): upstream [krazey/ims](https://github.com/krazey/ims) at commit `a3fec01ebc4f51c39026565c4a451fef454637fa` plus [`patches/0001-phhims-for-r8q-pixelos.patch`](patches/0001-phhims-for-r8q-pixelos.patch), [`patches/0002-drop-protected-broadcast.patch`](patches/0002-drop-protected-broadcast.patch) and [`patches/0003-report-no-media-outgoing-end.patch`](patches/0003-report-no-media-outgoing-end.patch):

```sh
git clone https://github.com/krazey/ims && cd ims
git checkout a3fec01ebc4f51c39026565c4a451fef454637fa
git apply /path/to/0001-phhims-for-r8q-pixelos.patch
git apply /path/to/0002-drop-protected-broadcast.patch
git apply /path/to/0003-report-no-media-outgoing-end.patch
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

The zip ends up in `dist/`. The script needs `python3` and `java`, and in `SMALI_DIR` the baksmali/smali 2.5.2 jars with their dependencies (the list with checksums is in the workflow). It removes the `<protected-broadcast>` declaration from `PHHIMS_APK` and applies the v0.3.3 bytecode fix if they are not there yet, and re-signs the APK with `KEYSTORE` if it changed anything; an APK built with patches 0002 and 0003 is packed as it is. `aapt2 link` needs `--keep-raw-values` (the script sets it): without it, `mnc="07"` is stored as the integer 7, CarrierConfig reads `"7"` and the entry never matches the SIM.

**Releases:** set `version` and `versionCode` in `module/module.prop`, add the changes to `CHANGELOG.md`, merge, then publish a GitHub release whose tag equals `version`. The workflow in `.github/workflows/build.yml` builds the zip, attaches it to the release and updates `update.json`. It signs the overlays with the repository secrets `KEYSTORE_BASE64` and `KEYSTORE_PASSWORD` if they are set, otherwise with a key made for that build.

## License

GPL-2.0, see [LICENSE](LICENSE), like PhhIms and the original module.
