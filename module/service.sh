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
log "Android $(getprop ro.build.version.release) (SDK $(getprop ro.build.version.sdk)), device $(getprop ro.product.device)"
log "SIM PLMN: $(getprop gsm.sim.operator.numeric)"
# "cmd phone cc" is refused on user builds, so read the effective value from the dump instead
log "carrier config: carrier_volte_available_bool = $(dumpsys carrier_config 2>/dev/null | awk -v key=carrier_volte_available_bool '
  /Phone Id = / { inph = ($NF == "0"); next }
  /mNoSimConfig/ { inph = 0 }
  inph && / : ( null)? *$/ { sec = $1 }
  inph && $1 == key && $2 == "=" { val = $3; src = sec }
  END { if (val == "") print "unknown"; else print val " (" src ")" }')"
log "power-save allowlist: $(dumpsys deviceidle whitelist 2>/dev/null | grep 'me.phh.ims' | tr -s '\n' ' ')"

# Registration refresh check (v0.2-o2, 2026-11-10). PhhIms renews its IMS registration from an
# alarm that re-arms itself each time it is delivered. 65 minutes after boot the first one has
# fired, so another must be queued. If none is, the refresh has stopped: the registration then
# expires and calls fall back to 2G (this is what v0.1 did, see README).
(
  while [ "$(cut -d. -f1 /proc/uptime)" -lt 3900 ]; do sleep 120; done
  if dumpsys alarm 2>/dev/null | grep -q 'tag=.*me\.phh\.ims\.ALARM_PERIODIC_REGISTER'; then
    log "registration refresh alarm: queued"
  else
    log "registration refresh alarm: NOT queued (registration will expire)"
  fi
) &

# Outgoing call audio workaround (v0.2-o2, 2026-11-10). When a call is dialled Telecom first sets
# MODE_IN_CALL and only ~0.1 s later the VoIP mode. On r8q the audio HAL's setMode(IN_CALL) loops
# until vendor.calls.slot_id0/1 leaves "0" (the RIL sets it to 1 for a circuit-switched call). A
# PhhIms call has no modem call, so the HAL spins until the audioserver watchdog kills
# audioserver ~6 s later: the call connects late and the microphone never opens.
# Release the HAL by reporting the calling slot ourselves while PhhIms sets up an outgoing call.
# Also keeps the IMS registration state for the status button (see ims-state.sh).
. "$MODDIR/ims-state.sh"
rm -f "$IMS_STATE"

set_slot_prop() {
  if command -v resetprop >/dev/null 2>&1; then resetprop -n "$1" "$2"; else setprop "$1" "$2"; fi
}
(
  held=
  while true; do
    # IMS registration so far (it usually happens before this script runs), then follow the log
    logcat -d -b radio -e "^($IMS_LOG_RE)\$" 2>/dev/null | while read -r line; do ims_update "$line"; done
    # -e matches the message text only, not the tag; the tag is checked below.
    logcat -b radio -T 1 -e "^([0-9]+ createCallSession|Closing call|$IMS_LOG_RE)\$" 2>/dev/null |
    while read -r line; do
      ims_update "$line"
      case "$line" in
        *"PHH MmTelFeature"*createCallSession*)
          slot=${line##*MmTelFeature: }; slot=${slot%% *}
          prop=vendor.calls.slot_id$slot
          if [ "$(getprop "$prop")" = "0" ]; then
            set_slot_prop "$prop" 1
            held=$prop
            log "outgoing IMS call: $prop 0 -> 1 (releases audio HAL setMode)"
          fi
          ;;
        *"PHH MmTelFeature"*"Closing call"*)
          if [ -n "$held" ]; then
            sleep 3
            # Leave it alone if a call is still up (e.g. 2G retry): the RIL owns the value then.
            if ! dumpsys telephony.registry 2>/dev/null | grep -q 'mCallState=[12]'; then
              set_slot_prop "$held" 0
            fi
            held=
          fi
          ;;
      esac
    done
    sleep 5
  done
) &
