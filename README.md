# PhhIms VoLTE for the Galaxy S20 FE (r8q) – o2 Germany

KernelSU / Magisk module that brings VoLTE and SMS over IMS to the Snapdragon Galaxy S20 FE (r8q), using the open-source IMS stack PhhIms. This is a fork of **[buddi0812/r8q-volte-phhims](https://github.com/buddi0812/r8q-volte-phhims)**, adapted for **o2 Germany (Telefónica)**.

## Credits

- **[buddi0812](https://github.com/buddi0812)**: original module ([r8q-volte-phhims](https://github.com/buddi0812/r8q-volte-phhims) v0.1, made for Airtel India on PixelOS 17): the PhhIms patch for r8q, the KernelSU module and the overlays. Nearly everything here is his work; his README is kept as [ORIGINAL-README.md](ORIGINAL-README.md).
- **PhhIms**: Pierre-Hugues Husson ([phhusson/ims](https://github.com/phhusson/ims)) and the [krazey/ims](https://github.com/krazey/ims) contributors
- **o2 adaptation**: [Silvertax](https://github.com/Silvertax)

## Status

Experimental. Tested on one device: Galaxy S20 FE SM-G780G, unofficial LineageOS 24.0 (r8q Cloud), KernelSU v3.3.1 in the kernel, SELinux enforcing, o2 Germany (262-07), with a dedicated IMS APN.

- **Worked:** IMS registration, VoLTE calls in both directions, SMS over IMS, mobile data during calls, re-registration after reboot
- **Not available:** Wi-Fi calling, video calls
- **Fixed:** with v0.1 VoLTE stopped working about an hour after each registration and calls fell back to 2G (mobile data pauses during such a call), and outgoing VoLTE calls connected 8 to 12 seconds late with a dead microphone. The audio fix works from v0.2-o2, the registration fix from v0.2.2-o2. See [Changes in v0.2-o2](#changes-in-v02-o2-2026-11-10).
- **How far this is tested:** for a little over three hours after the correction in v0.2.2-o2 the registration was refreshed on schedule and outgoing calls connected at once. The single 2G fallback noted under v0.2-o2 fits the fault corrected in v0.2.2-o2; there is no log of that call.
- **Magisk:** not tested yet. The zip installs in the Magisk app as is, and the module mounts its files itself (overlayfs in `post-fs-data.sh`) without anything KernelSU-specific, so it should behave the same.

## Requirements

- Galaxy S20 FE Snapdragon (r8q) with a ROM on **Android 17** (the overlays are built with `minSdkVersion 37`)
- Root with KernelSU or Magisk (Magisk not tested yet, see Status)
- Only **one** PhhIms/VoLTE module active at a time

## o2: add a dedicated IMS APN

On the tested ROM, the preset o2 APN `internet` also had the type `ims` and there was no separate IMS APN, so IMS stayed unregistered. Fix:

1. Settings → Network & internet → SIMs → your o2 SIM → Access Point Names
2. Add an APN: APN `ims`, APN type `ims`, APN protocol IPv4/IPv6
3. Remove `ims` from the APN type of the `internet` APN
4. Toggle airplane mode on and off

## Installation

1. Download the latest `phhims_volte-*.zip` from [Releases](../../releases/latest).
2. KernelSU / Magisk → Modules → Install → select the zip → reboot.
3. About a minute after boot, check `/data/adb/phhims-volte.log`: it should list the mounts and the PhhIms overlays, `IMS feature: declared`, and your SIM's network code. About 65 minutes after boot it adds `registration refresh alarm: queued`, and each outgoing VoLTE call adds a `vendor.calls.slot_id0 0 -> 1` line.
4. Turn on VoLTE under Settings → Network & internet → SIMs → your SIM, then test a call and an SMS.

Later versions can be installed from the module list in KernelSU / Magisk: the module carries an update link (`updateJson`), so the manager offers an update when a new release is out. This works from v0.2.1-o2 on.

To uninstall, remove the module in KernelSU / Magisk and reboot.

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
- **Unchanged:** the patch, `post-fs-data.sh`, `uninstall.sh` and the `android`/`phone` overlays. The PhhIms APK is buddi0812's v0.1 build with only its manifest changed (see v0.2-o2 above).

## Other carriers

The bundled PhhIms applies a persistent VoLTE carrier-config override for any SIM on its own (`ensureVolteCarrierConfig` in buddi0812's patch). On PixelOS the CarrierConfig overlay was even ignored, so the carrier list in `overlays/cc` only matters on ROMs that honour it. To add a carrier there, edit `overlays/cc/res/xml/vendor.xml` (keep leading zeros, e.g. `mnc="07"`) and rebuild.

## Troubleshooting

- **Boot-loop protection:** if the phone fails to finish booting twice in a row, the module skips its mounts on the next boot. Creating `/data/adb/phhims-volte.disable` skips them manually.
- **Logs for a call** (PhhIms logs to the radio buffer):
  ```sh
  su -c 'logcat -b all -v threadtime > /sdcard/Download/volte_log.txt'
  ```
  Make a few calls, stop with Ctrl+C and attach the file together with `/data/adb/phhims-volte.log` when [reporting an issue](../../issues/new/choose). The log contains phone numbers.

## Building

**PhhIms APK** (as described by buddi0812): upstream [krazey/ims](https://github.com/krazey/ims) at commit `a3fec01ebc4f51c39026565c4a451fef454637fa` plus [`patches/0001-phhims-for-r8q-pixelos.patch`](patches/0001-phhims-for-r8q-pixelos.patch) and [`patches/0002-drop-protected-broadcast.patch`](patches/0002-drop-protected-broadcast.patch):

```sh
git clone https://github.com/krazey/ims && cd ims
git checkout a3fec01ebc4f51c39026565c4a451fef454637fa
git apply /path/to/0001-phhims-for-r8q-pixelos.patch
git apply /path/to/0002-drop-protected-broadcast.patch
# edit app/build.gradle: set the SDK path in the bootstrapClasspath line (android-33 platform jar)
./gradlew assembleDebug      # Gradle 8.5, AGP 8.2, Kotlin 1.8.10, NDK 25.1.8937393
```

**Overlays and module zip:**

```sh
BUILD_TOOLS=~/Android/Sdk/build-tools/35.0.0 \
ANDROID_JAR=~/Android/Sdk/platforms/android-33/android.jar \
KEYSTORE=my-key.jks \
PHHIMS_APK=path/to/PhhIms.apk ./build.sh
```

The zip ends up in `dist/`. The script needs `python3`: it removes the `<protected-broadcast>` declaration from `PHHIMS_APK` if it is still there and re-signs the APK with `KEYSTORE`; an APK built with patch 0002 is packed as it is. `aapt2 link` needs `--keep-raw-values` (the script sets it): without it, `mnc="07"` is stored as the integer 7, CarrierConfig reads `"7"` and the entry never matches the SIM.

**Releases:** set `version` and `versionCode` in `module/module.prop`, add the changes to `CHANGELOG.md`, merge, then publish a GitHub release whose tag equals `version`. The workflow in `.github/workflows/build.yml` builds the zip, attaches it to the release and updates `update.json`. It signs the overlays with the repository secrets `KEYSTORE_BASE64` and `KEYSTORE_PASSWORD` if they are set, otherwise with a key made for that build.

## License

GPL-2.0, see [LICENSE](LICENSE), like PhhIms and the original module.
