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

# IMS registration and capabilities, one entry per phone in slot order
phone_dump=$(dumpsys phone 2>/dev/null)
reg=$(echo "$phone_dump" | sed -n 's/^ *mImsMmTelRegistrationState = \([0-9]\).*/\1/p' | sed -n "${n}p")
caps=$(echo "$phone_dump" | sed -n 's/.*mMmTelCapabilities=MmTel Capabilities - \[Voice: \([a-z]*\).* SMS: \([a-z]*\).*/voice \1, SMS \2/p' | sed -n "${n}p")
case "$reg" in
  2) regs="registered" ;;
  1) regs="registering" ;;
  0) regs="NOT registered" ;;
  *) regs="unknown" ;;
esac

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

radio=$(logcat -d -b radio 2>/dev/null)
last_fired=$(echo "$radio" | grep 'Alarm fired with me.phh.ims.ALARM_PERIODIC_REGISTER' | tail -n 1 | cut -c7-14)
failed=$(echo "$radio" | grep -c 'Outgoing call setup failed')
log_since=$(echo "$radio" | head -n 1 | cut -c7-11)

calls=$(awk '/boot completed/ { c = 0 } /outgoing IMS call:/ { c++ } END { print c + 0 }' "$LOG" 2>/dev/null)
dropped=$(awk '/boot attempt/ { c = 0 } /dropped stale package cache entry/ { c++ } END { print c + 0 }' "$LOG" 2>/dev/null)
up=$(cut -d. -f1 /proc/uptime)
uptime_s="$((up / 3600))h $((up % 3600 / 60))min"

if pm path me.phh.ims >/dev/null 2>&1; then installed=yes; else installed=no; fi
guard="off"
[ -f /data/adb/phhims-volte.disable ] && guard="ON (disable file)"
[ "$(cat /data/adb/phhims-volte.bootcount 2>/dev/null || echo 0)" -gt 2 ] && guard="ON (boot loop protection)"

rom=$(getprop ro.lineage.version)
[ -n "$rom" ] && rom="LineageOS $rom" || rom=$(getprop ro.build.display.id)

if [ "$installed" != yes ]; then
  verdict="PROBLEM: PhhIms is not installed. See the module log."
elif [ "$reg" = 1 ]; then
  verdict="WAIT: IMS is still registering. Tap the button again in a minute."
elif [ "$reg" = 0 ]; then
  verdict="PROBLEM: IMS is not registered. Check the IMS APN (README, Troubleshooting)."
elif [ -z "$reg" ]; then
  verdict="CHECK: the IMS state could not be read on this ROM. Please send this report."
elif [ -z "$alarm" ]; then
  verdict="PROBLEM: no registration refresh scheduled. VoLTE will stop within an hour."
else
  verdict="OK: VoLTE is ready."
fi

report=$(cat <<EOF
PhhIms VoLTE status
Module:     $(prop version) ($(date '+%F %H:%M'))
Device:     $(getprop ro.product.model), Android $(getprop ro.build.version.release)
ROM:        $rom
Carrier:    $oper ($plmn), SIM slot $((slot + 1)), $net
PhhIms:     installed $installed, boot guard $guard
IMS:        $regs${caps:+, $caps}
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
