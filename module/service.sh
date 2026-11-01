#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/adb/phhims-volte.log
CNT=/data/adb/phhims-volte.bootcount
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 5; done
sleep 60
echo 0 > "$CNT"
log "boot completed, loop counter reset"

if pm list packages | grep -q "package:me.phh.ims"; then
  pm grant me.phh.ims android.permission.RECORD_AUDIO >> "$LOG" 2>&1
  pm grant me.phh.ims android.permission.READ_PHONE_STATE >> "$LOG" 2>&1
  log "PhhIms installed: $(pm path me.phh.ims)"
else
  log "PhhIms NOT installed (mount or scan failed)"
fi
cmd overlay list 2>/dev/null | grep -A1 -E "^(android|com.android.phone)$" | grep phh >> "$LOG" 2>&1
