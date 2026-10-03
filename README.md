# TWRP for Samsung Galaxy A02s (SM-A025F, a02q) - Android 12

A TWRP 12.1 device tree for the Samsung Galaxy A02s (SM-A025F, codename `a02q`, Qualcomm msm8953),
with fastbootd support, a work-in-progress File-Based Encryption (FBE) setup, MTP fixes, and a
GitHub Actions workflow that builds the recovery image.

Status: this tree has not been verified on a physical device. Treat every build as experimental.

## Introduction

This repository contains the device tree (`samsung/a02q`), build scripts, and a CI workflow needed to
build TWRP for the SM-A025F running Android 12 firmware. It is based on an existing community tree
(see Credits) and targets the `twrp-12.1` branch of the minimal TWRP manifest.

Device summary:

| Item | Value |
| --- | --- |
| Device | Samsung Galaxy A02s (SM-A025F) |
| Codename | `a02q` |
| Platform | Qualcomm msm8953 (Snapdragon 450) |
| Userspace | 32-bit ARM, 64-bit binder |
| Kernel | Prebuilt 4.9.227 (included in `prebuilt/`) |
| Partitions | Dynamic partitions (`super`), separate recovery partition |
| TWRP branch | `twrp-12.1` |
| Lunch target | `omni_a02q-eng` |

## Modifications

Changes made on top of the original tree:

- **fastbootd**: `fastbootd` and the mock fastboot HAL are included, `TW_INCLUDE_FASTBOOTD` is enabled
  so "Reboot to Fastboot" is available, and all `TW_*` flags were moved from `device.mk` to
  `BoardConfig.mk`. Userspace fastboot can be used to flash logical partitions
  (for example `fastboot flash system system.img`).
- **FBE decryption**:
  - The previous security patch and platform version overrides (`2099-12-31` and `16.1.0`) were removed
    and replaced with values that must match the installed firmware, because keymaster rejects keys
    when these do not match. Verify the value with `getprop ro.build.version.security_patch`.
  - Crypto flags were added (`TW_INCLUDE_CRYPTO`, `TW_INCLUDE_CRYPTO_FBE`,
    `BOARD_USES_QCOM_FBE_DECRYPTION`). The kernel only supports fscrypt v1 and has no
    `dm-default-key`, so metadata decryption is intentionally not enabled.
  - `/data` carries `fileencryption=ice` in the fstab, `/metadata` was added, and `/firmware`
    (apnhlos) is mounted from the init script so `qseecomd` can load the keymaster trustlet.
  - `samsung/a02q/tools/collect_fbe_blobs.py` extracts `qseecomd`, keymaster and gatekeeper services,
    their libraries, and a matching VINTF manifest from a stock `vendor.img` into the recovery
    ramdisk and generates `init.recovery.fbe.rc`. Without these blobs decryption cannot work.
- **Wipe and flash system**: `/system` can be wiped from Wipe > Advanced Wipe, and a `/system_image`
  entry allows flashing a system image from Install > Install Image.
- **MTP stability**: USB gadget configuration now waits until the UDC has been detected, and
  `udc_probe.sh` no longer re-sets properties repeatedly, which previously caused the gadget to rebind
  and MTP to disconnect. The Samsung `usb_mtp_gadget` node is linked to `/dev/mtp_usb`.
- **fstab cleanup**: removed duplicated flags and the stray `/sdcard` entry, and synchronized
  `recovery.fstab`, `twrp.flags`, and the root `recovery.fstab`.
- **CI**: a GitHub Actions workflow builds the recovery image and uploads `recovery.img` and
  `recovery.tar` (for Odin) as artifacts.

Known limitations:

- Samsung uses additional proprietary key handling (SDP/Knox), so decrypting `/data` is not guaranteed
  even with a correct configuration.
- `BOARD_SUPER_PARTITION_SIZE` is inherited from the original tree and should be verified against the
  real `super` partition size (`blockdev --getsize64 /dev/block/by-name/super`).
- The keymaster service name and the exact `fileencryption` string depend on the stock firmware and
  may need adjustment.

## Credits

- **Android Open Source Project (AOSP)** - the Android platform, build system, and fastbootd that this
  work depends on. AOSP is licensed under the Apache License 2.0 (with some components under other licenses).
- **TWRP team (Team Win Recovery Project)** - the TWRP recovery source and the minimal manifest used to
  build it. TWRP is licensed under GPLv3.
- **Ragekill3377** - author of the original device tree this repository is based on:
  [TWRP-SM-A025F-OS12](https://github.com/Ragekill3377/TWRP-SM-A025F-OS12).

The device tree files retain their original license headers.

## Build instructions

### Option 1: GitHub Actions

1. Make the repository **public**. Standard runners for public repositories provide 4 vCPU and 16 GB RAM;
   private repositories get fewer resources and the build may be too slow or run out of memory.
2. Extract the stock `vendor.img` from your firmware and run:

   ```
   python3 samsung/a02q/tools/collect_fbe_blobs.py <vendor_dir> [<system_dir>]
   ```

   Commit the generated files. Review any warnings the script prints about missing libraries.
3. Check the security patch values in `samsung/a02q/BoardConfig.mk` against your firmware.
4. Open the **Actions** tab, select **Build TWRP a02q**, and choose **Run workflow**.
5. When it finishes, download the `twrp-a02q` artifact. If it fails, download `build-log`.

A single job is limited to six hours. The first run is the slowest because the compiler cache is empty.

### Option 2: Local build

Requirements: Ubuntu 22.04 (or WSL2), at least 16 GB RAM, and at least 45 GB of free disk space.

```
./scripts/setup-deps.sh
./build-twrp.sh
```

The script syncs the `twrp-12.1` minimal manifest to `~/twrp`, copies the device tree into
`device/samsung`, builds `omni_a02q-eng`, and places the results in `out/`. It can be re-run to resume
an interrupted sync or build.

### Flashing

1. Unlock the bootloader (OEM unlock) and make sure vbmeta verification is disabled.
2. Boot the device into Download mode and flash `out/recovery.tar` with Odin in the AP slot, with
   Auto Reboot disabled.
3. Boot straight into recovery after flashing so the stock recovery does not overwrite TWRP.

## Disclaimer

This software is provided as is, without warranty of any kind. Flashing a custom recovery can brick
your device, trigger Knox and permanently void your warranty, and wipe or corrupt your data. Wiping
`system` or formatting `data` will remove your operating system or personal files. Back up everything
and keep the stock firmware and Odin available before you start. You are solely responsible for what you
do to your device; the authors and contributors accept no liability for any damage or data loss.

This project is not affiliated with or endorsed by Samsung, Google, Qualcomm, or the TWRP team.
All trademarks belong to their respective owners.
