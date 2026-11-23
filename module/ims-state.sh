# IMS registration tracking, sourced by service.sh and action.sh (v0.3, 2026-11-12).
# Not every ROM dumps the IMS registration state ("dumpsys phone" on the test ROM does not), so
# service.sh follows the radio log and keeps the latest state in $IMS_STATE, which outlives the
# log buffer. Sources: the framework's ImsPhone (every registration change goes through it) and
# PhhIms' own messages.
# Keys: state, since (log time of the latest confirmation), changed (epoch when the state last
# changed, for "registering for too long"), caps, nopcscf (log time of the latest "no IMS server
# address" message since the last successful registration), nopcscf_first (epoch of the first one).
IMS_STATE=/data/adb/phhims-volte.ims

# logcat -e patterns, matched against the whole radio log line, for the lines ims_update understands
IMS_LOG_RE='\[[0-9]+\] handleIms(Registered|Registering|Unregistered):.*|IMS SIP (registered|registering), reporting.*|Reporting IMS deregistered.*|\[[0-9]+\] handleFeatureCapabilityChanged: MmTel Capabilities.*|No P-CSCF and all fallbacks failed.*|java\.lang\.NullPointerException: imsi must not be null.*'

ims_write() { # key value: replace one key in the state file
  { grep -v "^$1=" "$IMS_STATE" 2>/dev/null; echo "$1=$2"; } > "$IMS_STATE.tmp" && mv "$IMS_STATE.tmp" "$IMS_STATE"
}

restart_phhims_for_null_imsi() {
  [ -n "$IMS_RESTART_ON_NULL_IMSI" ] || return 0  # service.sh only, not the status button
  err_pid="$1"
  [ -n "$err_pid" ] || return 0
  [ "$err_pid" = "$(pidof me.phh.ims 2>/dev/null)" ] || return 0

  # Wait up to 15s for inserted SIMs to finish loading IMSI records. Only restart once a SIM is
  # loaded; before that (e.g. PIN not entered) the next NPE line retries.
  i=0
  while :; do
    case "$(getprop gsm.sim.state)" in *LOADED*) break ;; esac
    [ "$i" -ge 15 ] && return 0
    sleep 1
    i=$((i + 1))
  done

  [ "$err_pid" = "$(pidof me.phh.ims 2>/dev/null)" ] || return 0
  kill -9 "$err_pid" 2>/dev/null
  echo "$(date '+%F %T') restarted me.phh.ims (pid $err_pid) after early-boot null IMSI" >> /data/adb/phhims-volte.log
  sleep 4
}

ims_update() { # one threadtime log line
  case "$1" in
    *"imsi must not be null"*)
      restart_phhims_for_null_imsi "$(echo "$1" | awk '{print $3}')"
      return ;;
    *"handleImsRegistered:"*|*"IMS SIP registered, reporting"*) st=registered ;;
    *"handleImsRegistering:"*|*"IMS SIP registering, reporting"*) st=registering ;;
    *"handleImsUnregistered:"*|*"Reporting IMS deregistered"*) st="NOT registered" ;;
    *"handleFeatureCapabilityChanged: MmTel Capabilities"*)
      caps=$(echo "$1" | sed -n 's/.*\[Voice: \([a-z]*\).* SMS: \([a-z]*\).*/voice \1, SMS \2/p')
      [ -n "$caps" ] && ims_write caps "$caps"
      return ;;
    *"No P-CSCF and all fallbacks failed"*)
      [ -z "$(sed -n 's/^nopcscf_first=//p' "$IMS_STATE" 2>/dev/null)" ] && ims_write nopcscf_first "$(date +%s)"
      ims_write nopcscf "$(echo "$1" | cut -c7-14)"
      return ;;
    *) return ;;
  esac
  if [ "$(sed -n 's/^state=//p' "$IMS_STATE" 2>/dev/null)" != "$st" ]; then
    ims_write changed "$(date +%s)"
  fi
  if [ "$st" = registered ]; then
    ims_write nopcscf ""
    ims_write nopcscf_first ""
  fi
  ims_write state "$st"
  ims_write since "$(echo "$1" | cut -c1-14)"
}
