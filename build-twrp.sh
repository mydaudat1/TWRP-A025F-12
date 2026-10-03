#!/bin/bash
# Build TWRP 12.1 cho SM-A025F (a02q). Chạy lại được nhiều lần: sync/build tiếp tục từ chỗ dừng.
# Dùng:  tmux new -s build && ./build-twrp.sh        (tmux giữ build sống khi mất kết nối)
set -eo pipefail
export PATH="$HOME/.bin:$PATH"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="${TWRP_SRC:-$HOME/twrp}"
TARGET="omni_a02q-eng"

# --- giới hạn số job theo RAM (mỗi job ~2GB) ---
MEM_GB=$(awk '/MemTotal/{printf "%d",$2/1024/1024}' /proc/meminfo)
JOBS=$(( MEM_GB / 2 )); [ "$JOBS" -lt 1 ] && JOBS=1
CPU=$(nproc); [ "$JOBS" -gt "$CPU" ] && JOBS=$CPU
echo ">> RAM=${MEM_GB}GB CPU=${CPU} -> dùng -j${JOBS}"
FREE_GB=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
[ "$FREE_GB" -lt 45 ] && echo "!! Chỉ còn ${FREE_GB}GB trống, cần >= 45GB" && exit 1

# --- 1) sync source ---
mkdir -p "$SRC" && cd "$SRC"
if [ ! -d .repo ]; then
  repo init --depth=1 --no-repo-verify \
    -u https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp.git \
    -b twrp-12.1 -g default,-mips,-darwin,-notdefault
fi
for try in 1 2 3 4 5; do
  repo sync -c --no-clone-bundle --no-tags --optimized-fetch --prune --force-sync -j"$JOBS" && break
  echo ">> sync lỗi (lần $try), thử lại..."; sleep 5
done

# --- 2) đặt device tree từ repo của bạn ---
rm -rf device/samsung
mkdir -p device
cp -r "$REPO_DIR/samsung" device/samsung
chmod +x device/samsung/a02q/recovery/root/system/bin/* 2>/dev/null || true

# --- 3) vá lỗi sprintf (nếu có) ---
F=bootable/recovery/minuitwrp/graphics_fbdev.cpp
if grep -q 'sprintf(brightness' "$F" 2>/dev/null; then
  sed -i 's|sprintf(brightness.*|snprintf(brightness, 4, "%03d", TW_MAX_BRIGHTNESS/2);|' "$F"
  echo ">> đã vá $F"
fi

# --- 4) build ---
export ALLOW_MISSING_DEPENDENCIES=true LC_ALL=C
export USE_CCACHE=1 CCACHE_EXEC="$(command -v ccache)" CCACHE_DIR="$HOME/.ccache"
ccache -M 20G >/dev/null
set +u
source build/envsetup.sh
lunch "$TARGET"
mka recoveryimage -j"$JOBS" 2>&1 | tee "$HOME/build.log"

# --- 5) đóng gói cho Odin ---
OUT=out/target/product/a02q
mkdir -p "$REPO_DIR/out"
cp "$OUT/recovery.img" "$REPO_DIR/out/"
( cd "$REPO_DIR/out" && tar -H ustar -c recovery.img > recovery.tar && md5sum recovery.img )
ls -lh "$REPO_DIR/out"
echo ">> XONG. Tải out/recovery.tar (Odin, slot AP) hoặc out/recovery.img (fastboot/TWRP)."
