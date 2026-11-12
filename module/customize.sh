# Install-time check (v0.3.1, 2026-11-12). Sourced by KernelSU / Magisk after unpacking.
# Static overlays are only registered when their SDK version matches the ROM. Without them
# Android never hands IMS over to PhhIms, so refuse other Android versions instead of
# installing something that cannot work.
sdk=$(getprop ro.build.version.sdk)
release=$(getprop ro.build.version.release)
case "$sdk" in
  37)
    ui_print "- Android $release (SDK $sdk): tested"
    rm -rf "$MODPATH/overlays-sdk36"
    ;;
  36)
    ui_print "- Android $release (SDK $sdk): using the SDK 36 overlays"
    ui_print "  Android 16 is a test, untested so far. Please report"
    ui_print "  the status button result in the XDA thread or on GitHub."
    rm -rf "$MODPATH/ovl/product/overlay"
    mv "$MODPATH/overlays-sdk36" "$MODPATH/ovl/product/overlay"
    ;;
  *)
    abort "! Needs Android 17 (SDK 37) or Android 16 (SDK 36). This ROM: Android $release (SDK $sdk)."
    ;;
esac
case "$(getprop ro.product.device)" in
  r8q*) ;;
  *) ui_print "! Made for the Galaxy S20 FE Snapdragon (r8q). This device: $(getprop ro.product.device)" ;;
esac
