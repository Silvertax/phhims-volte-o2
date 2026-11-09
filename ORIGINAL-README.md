# VoLTE + SMS-over-IMS on Galaxy S20 FE 5G (r8q) with PhhIms

Working VoLTE calls and IMS SMS on **Samsung Galaxy S20 FE 5G (SM-G781B, r8q)** running the unofficial
**PixelOS 17** build (20261023) on **Airtel India**, using the open-source
[PhhIms](https://github.com/krazey/ims) userspace IMS stack. No vendor IMS blobs are touched.

Tested by me, once, on one phone and one SIM:

- Registers on Airtel IMS (`REGISTER` → 401 AKA challenge → IPsec SAs → `200 OK`), MMTEL capabilities = voice + SMS.
- Incoming and outgoing VoLTE calls connect, audio flows both ways (~76 s test call, mic uplink sent 3.8k RTP packets).
- Mobile data keeps working during the call (call stays on LTE, no CS fallback).
- SMS send and receive work.
- Not working / not tried: Wi-Fi calling, video calls, other carriers, other devices, VoNR.

## What was wrong (and what fixes it)

| Problem on this ROM | Fix |
|---|---|
| PhhIms is built as a platform-signed `android.uid.system` app; the ROM's platform key is private | Build it **without** `sharedUserId`, install as a **priv-app** and grant what it needs through a `privapp-permissions` allowlist (`READ_PRIVILEGED_PHONE_STATE`, `MODIFY_PHONE_STATE`, `CONNECTIVITY_USE_RESTRICTED_NETWORKS`, `SCHEDULE_EXACT_ALARM`). The ROM runs `ro.control_privapp_permissions=enforce`, so a mismatch bootloops; the allowlist must match the manifest. |
| Telephony does not know a MMTEL provider exists | Runtime resource overlay (RRO) on `com.android.phone`: `config_ims_mmtel_package = me.phh.ims`. Overlay on `android`: `config_device_volte_available` / `config_carrier_volte_available` etc. |
| Carrier config has no VoLTE flags for Airtel; the CarrierConfig app reads Airtel's config from its **assets** and ignores a `vendor.xml` overlay; `cmd phone cc` is blocked | PhhIms calls `CarrierConfigManager.overrideConfig(subId, bundle, persistent=true)` itself, once, when `carrier_volte_available_bool` is false (`ensureVolteCarrierConfig` in the patch). Needs `MODIFY_PHONE_STATE` from the allowlist. The `overlays/cc` vendor.xml overlay in this repo turned out to be unnecessary; it is harmless and can be dropped. |
| Hidden API use | `hidden-api-whitelisted-app` sysconfig for `me.phh.ims` |
| Runtime permissions | `default-permissions` XML for `RECORD_AUDIO`, `READ_PHONE_STATE` |
| `NetworkRegistrationInfo.isNetworkRegistered` / `notifyIncomingCall(session, callId, extras)` do not exist in the stub jar PhhIms compiles against here | Small compat shims (`CompatExt.kt`, old `notifyIncomingCall(session, extras)` overload) |
| `getAllCellInfo()` throws `SecurityException` without location permission | try/catch in `RegistrationCellInfoLogger` |

An IMS APN is required (`apn=ims`, `type=ims`, protocol IPV4V6; P-CSCF address comes from PCO). On my phone IMS registered over it, but I did not record whether it came from the ROM's APN list or from an entry I added by hand while debugging. If the logs show no IMS network request, check that this APN exists for your SIM.

## How it is delivered: a KernelSU module, no system partition edits

The module (`module/`) mounts a small read-only overlayfs over `/system/priv-app`, `/system/etc/{permissions,sysconfig,default-permissions}`
and `/product/overlay` in `post-fs-data.sh`, so nothing on the real partitions changes.

Things I had to learn the hard way:

- overlayfs rejects lowerdirs that live on `/data`, so the files are first copied to a tmpfs (`/dev/phhims_ovl`) and mounted from there.
- Static RROs only registered after building them with `minSdkVersion`/`targetSdkVersion` matching the ROM (37) and `<application android:hasCode="false"/>`, `isStatic=true`, `priority=100`, aapt2 `--keep-raw-values`. They are signed with an ordinary debug key.
- **Boot-loop protection:** `post-fs-data.sh` increments `/data/adb/phhims-volte.bootcount`; after 2 boots that never reach `sys.boot_completed` + 60 s it skips the mounts. `service.sh` resets the counter. Creating `/data/adb/phhims-volte.disable` also skips them. Log: `/data/adb/phhims-volte.log`.

### Install

1. Rooted with KernelSU (tested: AospKSU kernel 4.19.325, KernelSU v3.3.1; no metamodule).
2. Download `phhims_volte-v0.1.zip` from the Releases page, install it in the KernelSU manager, reboot.
3. Check Settings → Network & internet → SIMs → *your SIM* for the VoLTE / 4G calling toggle, then test a call and an SMS.

### Uninstall / rollback

Disable or remove the module in the KernelSU manager and reboot. Calls and SMS go back to the normal CS fallback.

## Building PhhIms yourself

The APK in the release is built from upstream [krazey/ims](https://github.com/krazey/ims) at commit
`a3fec01ebc4f51c39026565c4a451fef454637fa` plus `patches/0001-phhims-for-r8q-pixelos.patch`:

```
git clone https://github.com/krazey/ims && cd ims
git checkout a3fec01ebc4f51c39026565c4a451fef454637fa
git apply /path/to/0001-phhims-for-r8q-pixelos.patch
# edit app/build.gradle: set the SDK path in the bootstrapClasspath line (android-33 platform jar)
./gradlew assembleDebug      # Gradle 8.5, AGP 8.2, Kotlin 1.8.10, NDK 25.1.8937393
```

If you build this into the ROM instead (the real fix), you do not need the patch's `build.gradle` change, the `sharedUserId` removal,
or the compat shims; you can sign with the platform key and keep `android.uid.system`. What the ROM needs is:

1. PhhIms (or equivalent) in `system_ext`/`product` priv-app, platform-signed.
2. `config_ims_mmtel_package` overlay for the phone app.
3. VoLTE availability flags for the carriers (the `ensureVolteCarrierConfig` logic, or carrier-config entries).
4. SELinux: I saw no PhhIms-related denials during the test, so `sepolicy.rule` is empty.

Overlay sources are in `overlays/`; build with `aapt2 compile` + `aapt2 link --min-sdk-version 37 --target-sdk-version 37 --keep-raw-values`, then `apksigner sign`.

## Known gaps

- Downlink jitter: the log shows short concealed playout underruns; I did not notice them in the call but a bigger jitter buffer may help on worse networks.
- Wi-Fi calling throws a `SecurityException` on the SIM info access; not investigated.
- PhhIms is a userspace SIP stack: other carriers need their own IMS quirks (upstream already handles Jio).

## License

PhhIms is GPL-2.0, so is this repo (patch + packaging). Upstream credit: Pierre-Hugues Husson (phh) and the krazey/ims contributors.
