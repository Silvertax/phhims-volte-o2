# PhhIms VoLTE for the Galaxy S20 FE (r8q) – o2 Germany

KernelSU module that brings VoLTE and SMS over IMS to the Snapdragon Galaxy S20 FE (r8q), using the open-source IMS stack PhhIms. This is a fork of **[buddi0812/r8q-volte-phhims](https://github.com/buddi0812/r8q-volte-phhims)**, adapted for **o2 Germany (Telefónica)**.

## Credits

- **[buddi0812](https://github.com/buddi0812)**: original module ([r8q-volte-phhims](https://github.com/buddi0812/r8q-volte-phhims) v0.1, made for Airtel India on PixelOS 17): the PhhIms patch for r8q, the KernelSU module and the overlays. Nearly everything here is his work; his README is kept as [ORIGINAL-README.md](ORIGINAL-README.md).
- **PhhIms**: Pierre-Hugues Husson ([phhusson/ims](https://github.com/phhusson/ims)) and the [krazey/ims](https://github.com/krazey/ims) contributors
- **o2 adaptation**: [Silvertax](https://github.com/Silvertax)

## Status

Experimental. Tested on one device: Galaxy S20 FE SM-G780G, unofficial LineageOS 24.0 (r8q Cloud), KernelSU v3.3.1 in the kernel, SELinux enforcing, o2 Germany (262-07), with buddi0812's v0.1 plus a dedicated IMS APN.

- **Worked:** IMS registration, VoLTE calls in both directions, SMS over IMS, mobile data during calls, re-registration after reboot
- **Not available:** Wi-Fi calling, video calls
- **Seen later:** not every call went over VoLTE. Calls that don't use VoLTE fall back to 2G, where mobile data pauses for the duration of the call.

## Requirements

- Galaxy S20 FE Snapdragon (r8q) with a ROM on **Android 17** (the overlays are built with `minSdkVersion 37`)
- Root with KernelSU
- Only **one** PhhIms/VoLTE module active at a time

## o2: add a dedicated IMS APN

On the tested ROM, the preset o2 APN `internet` also had the type `ims` and there was no separate IMS APN, so IMS stayed unregistered. Fix:

1. Settings → Network & internet → SIMs → your o2 SIM → Access Point Names
2. Add an APN: APN `ims`, APN type `ims`, APN protocol IPv4/IPv6
3. Remove `ims` from the APN type of the `internet` APN
4. Toggle airplane mode on and off

## Installation

1. Download `phhims_volte-v0.1-o2.zip` from [Releases](../../releases).
2. KernelSU → Modules → Install → select the zip → reboot.
3. About a minute after boot, check `/data/adb/phhims-volte.log`: it should list the mounts and the PhhIms overlays, `IMS feature: declared`, your SIM's network code and a `carrier config` line ending in `true`.
4. Turn on VoLTE under Settings → Network & internet → SIMs → your SIM, then test a call and an SMS.

To uninstall, remove the module in KernelSU and reboot.

## Changes compared to buddi0812's v0.1 (2026-11-09)

- **Carrier config:** the Airtel India network codes (404/405-xx) were replaced with o2 / Telefónica Germany: 262-07, 262-08, 262-11, 262-03 and 262-77.
- **IMS feature:** the module declares `android.hardware.telephony.ims`. Telephony only starts its ImsResolver, which binds PhhIms, if the ROM declares this feature. If the ROM already does, nothing changes.
- **Power management:** PhhIms is on the system power-save allowlist (`allow-in-power-save`), so Doze and App Standby don't restrict it.
- **Diagnostics:** the log also shows the IMS feature state, the SIM network code, the VoLTE carrier-config value and the power-save state. The package check now matches `me.phh.ims` exactly instead of also matching the overlays.
- **Build script:** `build.sh` builds the overlays and the module zip.
- **Unchanged:** the PhhIms APK (taken from buddi0812's v0.1 release), the patch, `post-fs-data.sh`, `uninstall.sh` and the `android`/`phone` overlays.

## Other carriers

The bundled PhhIms applies a persistent VoLTE carrier-config override for any SIM on its own (`ensureVolteCarrierConfig` in buddi0812's patch). On PixelOS the CarrierConfig overlay was even ignored, so the carrier list in `overlays/cc` only matters on ROMs that honour it. To add a carrier there, edit `overlays/cc/res/xml/vendor.xml` (keep leading zeros, e.g. `mnc="07"`) and rebuild.

## Troubleshooting

- **Boot-loop protection:** if the phone fails to finish booting twice in a row, the module skips its mounts on the next boot. Creating `/data/adb/phhims-volte.disable` skips them manually.
- **Logs for a call** (PhhIms logs to the radio buffer):
  ```sh
  su -c 'logcat -b all -v threadtime > /sdcard/Download/volte_log.txt'
  ```
  Make a few calls, stop with Ctrl+C and attach the file together with `/data/adb/phhims-volte.log` when reporting an issue.

## Building

**PhhIms APK** (as described by buddi0812): upstream [krazey/ims](https://github.com/krazey/ims) at commit `a3fec01ebc4f51c39026565c4a451fef454637fa` plus [`patches/0001-phhims-for-r8q-pixelos.patch`](patches/0001-phhims-for-r8q-pixelos.patch):

```sh
git clone https://github.com/krazey/ims && cd ims
git checkout a3fec01ebc4f51c39026565c4a451fef454637fa
git apply /path/to/0001-phhims-for-r8q-pixelos.patch
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

The zip ends up in `dist/`. `aapt2 link` needs `--keep-raw-values` (the script sets it): without it, `mnc="07"` is stored as the integer 7, CarrierConfig reads `"7"` and the entry never matches the SIM.

## License

GPL-2.0, see [LICENSE](LICENSE), like PhhIms and the original module.
