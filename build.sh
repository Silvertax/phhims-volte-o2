#!/bin/sh
# Builds the three overlay APKs from overlays/, patches and re-signs PhhIms.apk and packs the
# module zip (KernelSU / Magisk) into dist/. Needs python3 besides the Android build tools.
# Static overlays are only registered when their SDK version matches the ROM, so the overlays are
# built for Android 17 (SDK 37, in ovl/) and Android 16 (SDK 36, in overlays-sdk36/);
# customize.sh keeps the set that matches the phone at install time.
#
#   BUILD_TOOLS=~/Android/Sdk/build-tools/35.0.0 \
#   ANDROID_JAR=~/Android/Sdk/platforms/android-33/android.jar \
#   KEYSTORE=my-key.jks \
#   PHHIMS_APK=path/to/PhhIms.apk ./build.sh
#
# PhhIms.apk: build it from krazey/ims + patches/ (see README) or take it from a release zip.
# Set KS_PASS to pass the keystore password non-interactively.
set -e
cd "$(dirname "$0")"
: "${BUILD_TOOLS:?set BUILD_TOOLS to an Android build-tools directory}"
: "${ANDROID_JAR:?set ANDROID_JAR to an android.jar}"
: "${KEYSTORE:?set KEYSTORE to your signing keystore}"
: "${PHHIMS_APK:?set PHHIMS_APK to the PhhIms APK}"

VERSION=$(sed -n 's/^version=//p' module/module.prop)
OUT=dist/module
rm -rf dist
mkdir -p dist/tmp "$OUT"
cp -R module/. "$OUT/"
cp LICENSE "$OUT/LICENSE"
mkdir -p "$OUT/ovl/product/overlay" "$OUT/ovl/system/priv-app/PhhIms"

# PhhIms: remove the manifest's <protected-broadcast> and re-sign. With the declaration Android
# rejects the registration refresh alarm, because this build does not run as the system UID
# (see README). An APK that no longer has the declaration is packed as it is.
if python3 tools/strip-protected-broadcast.py "$PHHIMS_APK" dist/tmp/PhhIms-stripped.apk; then
  "$BUILD_TOOLS/zipalign" -p -f 4 dist/tmp/PhhIms-stripped.apk dist/tmp/PhhIms-aligned.apk
  "$BUILD_TOOLS/apksigner" sign --ks "$KEYSTORE" ${KS_PASS:+--ks-pass env:KS_PASS} \
      --v1-signing-enabled false --v4-signing-enabled false \
      --out "$OUT/ovl/system/priv-app/PhhIms/PhhIms.apk" dist/tmp/PhhIms-aligned.apk
else
  [ $? -eq 3 ] || exit 1
  cp "$PHHIMS_APK" "$OUT/ovl/system/priv-app/PhhIms/PhhIms.apk"
fi

# --keep-raw-values keeps mnc="07" as the string "07". Without it aapt2 stores the
# integer 7, CarrierConfig reads "7" and the entry never matches the SIM.
mkdir -p "$OUT/overlays-sdk36"
for sdk in 37 36; do
  if [ "$sdk" = 37 ]; then dest=$OUT/ovl/product/overlay; else dest=$OUT/overlays-sdk$sdk; fi
  for pair in android:PhhImsAndroidOverlay cc:PhhImsCarrierConfigOverlay phone:PhhImsPhoneOverlay; do
    src=overlays/${pair%%:*}
    name=${pair#*:}
    tmp=dist/tmp/$name-$sdk
    mkdir -p "$tmp"
    "$BUILD_TOOLS/aapt2" compile --dir "$src/res" -o "$tmp/res.zip"
    "$BUILD_TOOLS/aapt2" link --min-sdk-version "$sdk" --target-sdk-version "$sdk" --keep-raw-values \
        -I "$ANDROID_JAR" --manifest "$src/AndroidManifest.xml" -o "$tmp/unaligned.apk" "$tmp/res.zip"
    "$BUILD_TOOLS/zipalign" -p -f 4 "$tmp/unaligned.apk" "$tmp/aligned.apk"
    "$BUILD_TOOLS/apksigner" sign --ks "$KEYSTORE" ${KS_PASS:+--ks-pass env:KS_PASS} \
        --v4-signing-enabled false --out "$dest/$name.apk" "$tmp/aligned.apk"
  done
done
rm -rf dist/tmp

(cd "$OUT" && zip -qr -X "../phhims_volte-$VERSION.zip" .)
echo "Built dist/phhims_volte-$VERSION.zip"
