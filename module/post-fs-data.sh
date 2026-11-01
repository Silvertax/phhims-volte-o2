#!/system/bin/sh
# Mounts the module's files over /system and /product with read-only overlayfs, before system_server starts.
MODDIR=${0%/*}
LOG=/data/adb/phhims-volte.log
CNT=/data/adb/phhims-volte.bootcount
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

n=$(cat "$CNT" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$CNT"
if [ "$n" -gt 2 ] || [ -f /data/adb/phhims-volte.disable ]; then
  log "boot attempt $n without a completed boot, skipping mounts (loop protection)"
  exit 0
fi
log "boot attempt $n, mounting"

# overlayfs refuses lower layers that live on /data, so stage the files in memory (/dev is a tmpfs)
STAGE=/dev/phhims_ovl
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -r "$MODDIR/ovl/." "$STAGE/"
chmod -R a+rX "$STAGE"
chcon -R u:object_r:system_file:s0 "$STAGE" 2>/dev/null

ovmount() {
  src="$1"; dst="$2"
  if [ -d "$src" ] && [ -d "$dst" ]; then
    if mount -t overlay overlay -o "ro,lowerdir=$src:$dst" "$dst"; then
      log "mounted $src over $dst"
    else
      log "FAILED to mount $src over $dst"
    fi
  else
    log "skipped $dst (missing $src or $dst)"
  fi
}

ovmount "$STAGE/system/priv-app" /system/priv-app
ovmount "$STAGE/system/etc/permissions" /system/etc/permissions
ovmount "$STAGE/system/etc/sysconfig" /system/etc/sysconfig
ovmount "$STAGE/system/etc/default-permissions" /system/etc/default-permissions
ovmount "$STAGE/product/overlay" /product/overlay
