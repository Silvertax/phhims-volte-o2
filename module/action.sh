#!/system/bin/sh
# Status button: KernelSU and Magisk show an "Action" button for modules that ship this file.
# Prints a short VoLTE status report and saves it to /sdcard/Download/phhims-volte-status.txt
# for bug and carrier reports. Reads only; contains no phone numbers.
MODDIR=${0%/*}
LOG=/data/adb/phhims-volte.log
OUT=/sdcard/Download/phhims-volte-status.txt

prop() { sed -n "s/^$1=//p" "$MODDIR/module.prop"; }
field() { echo "$1" | cut -d, -f"$2"; }

# SIM slot: the first slot that reports a network code
plmns=$(getprop gsm.sim.operator.numeric)
slot=0
[ -z "$(field "$plmns" 1)" ] && [ -n "$(field "$plmns" 2)" ] && slot=1
n=$((slot + 1))
plmn=$(field "$plmns" "$n")
oper=$(field "$(getprop gsm.operator.alpha)" "$n")
net=$(field "$(getprop gsm.network.type)" "$n")

# IMS registration: kept by service.sh from the radio log (see ims-state.sh). If the file is
# missing (service.sh not run yet), read the radio log buffer directly.
. "$MODDIR/ims-state.sh"
radio=$(logcat -d -b radio 2>/dev/null)
if [ ! -s "$IMS_STATE" ]; then
  IMS_STATE=$(mktemp 2>/dev/null || echo /dev/phhims-volte.ims.$$)
  echo "$radio" | grep -E "$IMS_LOG_RE" | while read -r line; do ims_update "$line"; done
  tmp_state=$IMS_STATE
fi
regs=$(sed -n 's/^state=//p' "$IMS_STATE" 2>/dev/null)
since=$(sed -n 's/^since=//p' "$IMS_STATE" 2>/dev/null)
caps=$(sed -n 's/^caps=//p' "$IMS_STATE" 2>/dev/null)
nopcscf=$(sed -n 's/^nopcscf=//p' "$IMS_STATE" 2>/dev/null)
changed=$(sed -n 's/^changed=//p' "$IMS_STATE" 2>/dev/null)
nopcscf_first=$(sed -n 's/^nopcscf_first=//p' "$IMS_STATE" 2>/dev/null)
[ -n "$tmp_state" ] && rm -f "$tmp_state"

# Effective carrier config value: the dump lists the layers in order of precedence
volte_cc=$(dumpsys carrier_config 2>/dev/null | awk -v key=carrier_volte_available_bool -v ph="$slot" '
  /Phone Id = / { inph = ($NF == ph); next }
  /mNoSimConfig/ { inph = 0 }
  inph && / : ( null)? *$/ { sec = $1 }
  inph && $1 == key && $2 == "=" { val = $3; src = sec }
  END { if (val == "") print "unknown"; else print val " (" src ")" }')

# Registration refresh alarm (re-armed by PhhIms each time it is delivered)
alarm=$(dumpsys alarm 2>/dev/null | grep -A1 'tag=.*me\.phh\.ims\.ALARM_PERIODIC_REGISTER')
if [ -n "$alarm" ]; then
  due=$(echo "$alarm" | sed -n 's/.*origWhen=+\([^ ]*\).*/\1/p' | head -n 1 | sed 's/[0-9]*ms$//')
  refresh="scheduled${due:+, next in $due}"
else
  refresh="NOT scheduled"
fi

last_fired=$(echo "$radio" | grep 'Alarm fired with me.phh.ims.ALARM_PERIODIC_REGISTER' | tail -n 1 | cut -c7-14)
failed=$(echo "$radio" | grep -c 'Outgoing call setup failed')
log_since=$(echo "$radio" | grep -v '^-' | head -n 1 | cut -c7-11)

calls=$(awk '/boot completed/ { c = 0 } /outgoing IMS call:/ { c++ } END { print c + 0 }' "$LOG" 2>/dev/null)
dropped=$(awk '/boot attempt/ { c = 0 } /dropped stale package cache entry/ { c++ } END { print c + 0 }' "$LOG" 2>/dev/null)
up=$(cut -d. -f1 /proc/uptime)
uptime_s="$((up / 3600))h $((up % 3600 / 60))min"

if pm path me.phh.ims >/dev/null 2>&1; then installed=yes; else installed=no; fi
# The overlays tell Android to use PhhIms for IMS. They only load on the Android version they
# were built for, so none active usually means the wrong Android version.
overlays=$(cmd overlay list 2>/dev/null | grep -c '\[x\] me\.phh\.ims')
if pm list features 2>/dev/null | grep -qx 'feature:android.hardware.telephony.ims'; then
  feature=declared
else
  feature=MISSING
fi
sdk=$(getprop ro.build.version.sdk)
guard="off"
[ -f /data/adb/phhims-volte.disable ] && guard="ON (disable file)"
[ "$(cat /data/adb/phhims-volte.bootcount 2>/dev/null || echo 0)" -gt 2 ] && guard="ON (boot loop protection)"

rom=$(getprop ro.lineage.version)
[ -n "$rom" ] && rom="LineageOS $rom" || rom=$(getprop ro.build.display.id)

# How long IMS has been in its current state. Without the state file (service.sh has not run
# yet) the uptime is the best guess.
if [ -n "$tmp_state" ] || [ -z "$changed" ]; then
  age=$up
else
  age=$(( $(date +%s) - changed ))
  [ "$age" -lt 0 ] && age=0
fi
# How long the network has been refusing an IMS server address without a registration in between
if [ -n "$tmp_state" ] || [ -z "$nopcscf_first" ]; then
  nopcscf_age=$up
else
  nopcscf_age=$(( $(date +%s) - nopcscf_first ))
fi

if [ "$installed" != yes ]; then
  verdict="PROBLEM: PhhIms is not installed. See the module log."
elif [ "$overlays" -lt 3 ]; then
  verdict="PROBLEM: only $overlays of 3 overlays are active, so Android does not use PhhIms. This module supports Android 17 (SDK 37) and, as a test, Android 16 (SDK 36)."
elif [ "$feature" != declared ]; then
  verdict="PROBLEM: the IMS feature is not declared, so Android does not start IMS. See the module log."
elif [ -z "$regs" ] && [ "$up" -lt 180 ]; then
  verdict="WAIT: the phone started less than 3 minutes ago. Tap again in a minute."
elif [ "$regs" != registered ] && [ -n "$nopcscf" ] && [ "$nopcscf_age" -ge 120 ]; then
  verdict="PROBLEM: the network gives no IMS server address (P-CSCF), so IMS cannot register and calls do not use VoLTE. Usually a separate IMS APN is missing: add an APN with APN \"ims\" and APN type \"ims\" (protocol IPv4/IPv6), remove \"ims\" from the type of your internet APN, then toggle airplane mode. Details: README, IMS APN."
elif [ "$regs" = registering ] && [ "$age" -ge 300 ]; then
  verdict="PROBLEM: IMS has been registering for $((age / 60)) min without success. Please send this report and a radio log (README, Troubleshooting)."
elif [ "$regs" = registering ]; then
  verdict="WAIT: IMS is still registering. Tap the button again in a minute."
elif [ "$regs" = "NOT registered" ]; then
  verdict="PROBLEM: IMS is not registered. Check the IMS APN (README, Troubleshooting)."
elif [ -z "$regs" ]; then
  verdict="CHECK: the IMS state could not be read on this ROM. Please send this report."
elif [ -z "$alarm" ]; then
  verdict="PROBLEM: no registration refresh scheduled. VoLTE will stop within an hour."
else
  verdict="OK: VoLTE is ready."
fi

report=$(cat <<EOF
PhhIms VoLTE status
Module:     $(prop version) ($(date '+%F %H:%M'))
Device:     $(getprop ro.product.model) ($(getprop ro.product.device)), Android $(getprop ro.build.version.release) (SDK $sdk)
ROM:        $rom
Carrier:    $oper ($plmn), SIM slot $((slot + 1)), $net
PhhIms:     installed $installed, overlays $overlays/3, IMS feature $feature, boot guard $guard
IMS:        ${regs:-unknown}${since:+ since $since}${caps:+, $caps}${nopcscf:+
IMS server: none offered by the network (last at $nopcscf)}
VoLTE cfg:  $volte_cc
Refresh:    $refresh
Last fired: ${last_fired:-not in radio log}
Uptime:     $uptime_s
VoLTE calls since boot (outgoing): ${calls:-0}
Failed call setups in radio log since ${log_since:-?}: $failed
Cache entries renewed at boot: $dropped

$verdict
EOF
)

echo "$report"
if echo "$report" > "$OUT" 2>/dev/null; then
  echo
  echo "Saved to $OUT"
fi
