#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/adb/phhims-volte.log
CNT=/data/adb/phhims-volte.bootcount
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 5; done
sleep 60
echo 0 > "$CNT"
log "boot completed, loop counter reset"

if pm list packages | grep -qx "package:me.phh.ims"; then
  pm grant me.phh.ims android.permission.RECORD_AUDIO >> "$LOG" 2>&1
  pm grant me.phh.ims android.permission.READ_PHONE_STATE >> "$LOG" 2>&1
  log "PhhIms installed: $(pm path me.phh.ims)"
else
  log "PhhIms NOT installed (mount or scan failed)"
fi
cmd overlay list 2>/dev/null | grep "me.phh.ims" >> "$LOG" 2>&1

# Diagnostics (o2 edit, Silvertax, 2026-11-09)
if pm list features 2>/dev/null | grep -qx "feature:android.hardware.telephony.ims"; then
  log "IMS feature: declared"
else
  log "IMS feature: MISSING (ImsResolver will not start)"
fi
log "SIM PLMN: $(getprop gsm.sim.operator.numeric)"
log "carrier config: $(cmd phone cc get-value carrier_volte_available_bool 2>&1 | tr -s '\n' ' ')"
log "power-save allowlist: $(dumpsys deviceidle whitelist 2>/dev/null | grep 'me.phh.ims' | tr -s '\n' ' ')"
