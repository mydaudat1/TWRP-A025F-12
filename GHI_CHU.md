# Đã sửa gì trong device tree a02q

## Fastbootd
- device.mk: giữ `fastbootd` + `fastboot@1.0-impl-mock`, thêm `PRODUCT_BUILD_SUPER_PARTITION := false`
- BoardConfig.mk: thêm `TW_INCLUDE_FASTBOOTD := true` (nút Reboot → Fastboot trong TWRP)
- Tất cả `TW_*` chuyển từ device.mk sang BoardConfig.mk, bỏ trùng lặp
- fstab: partition logical (system/vendor/product/odm) khai báo gọn, bỏ `backup=1` bị lặp

## FBE
Kernel prebuilt (4.9.227) có: fscrypt v1, qcom_ice, qseecom. Không có fscrypt v2, không có dm-default-key.
=> Dùng FBE v1, KHÔNG bật metadata decrypt.
- BoardConfig: `TW_INCLUDE_CRYPTO`, `TW_INCLUDE_CRYPTO_FBE`, `BOARD_USES_QCOM_FBE_DECRYPTION`
- **Xoá hack patch level 2099 và PLATFORM_VERSION 16.1.0** -> đặt khớp ROM (12, 2023-05-01).
  Đây là nguyên nhân hàng đầu khiến keymaster từ chối key. XÁC NHẬN lại bằng
  `getprop ro.build.version.security_patch` trên ROM stock.
- fstab: `/data` thêm `fileencryption=ice`; thêm `/metadata`; xoá `/sdcard` thừa
- init.recovery.qcom.rc: mount `/firmware` (apnhlos) và `import /init.recovery.fbe.rc`

## Phải tự kiểm tra trên máy (mình không thể xác minh khi không có máy)
1. Chuỗi mã hoá thật: `grep -r fileencryption /vendor/etc/fstab*` -> chép đúng vào dòng /data
2. Tên service keymaster: `ls /vendor/etc/init | grep -i -E "keymaster|qseecom"` -> sửa đường dẫn trong rc
3. Kích thước super: `blockdev --getsize64 /dev/block/by-name/super` -> sửa BOARD_SUPER_PARTITION_SIZE
4. Sau khi build, nếu decrypt lỗi: `adb pull /tmp/recovery.log` và xem dòng keymaster/fscrypt

## Cảnh báo
Samsung dùng SDP/Knox riêng; giải mã /data trên A02s không đảm bảo 100% dù đã cấu hình đúng.
Không giải mã được thì phải Format Data (mất dữ liệu). Luôn giữ firmware stock + Odin để cứu máy.

## Wipe system / flash system.img
- fstab: dòng `/system ext4` thêm `wipeingui` (hiện trong Wipe → Advanced Wipe) và `backup=1`
- dòng `/system emmc` đã có `flashimg` (hiện trong Install → Install Image → chọn Partition: System)
- BoardConfig: `TW_INCLUDE_LPTOOLS := true` để TWRP resize logical partition khi ảnh lớn hơn
- Cách khác, không cần TWRP: vào Fastboot rồi `fastboot flash system system.img` (fastbootd)
- Sau khi flash system: vbmeta phải là bản disabled, nếu không máy bootloop

## Wipe system + Flash system image
- fstab: `/system` (ext4, logical) thêm `wipeingui;canbewiped` -> hiện trong Wipe > Advanced Wipe
- fstab: mục emmc của system đổi tên `/system_image` (có `flashimg`) -> hiện trong Install > Install Image
  (trùng mount point `/system` với mục ext4 sẽ khiến TWRP bỏ một trong hai)
- Khuyến nghị: dùng `fastboot flash system system.img` trong fastbootd; fastbootd tự resize
  phân vùng logical. Flash bằng TWRP chỉ chắc chắn khi image nhỏ hơn hoặc bằng kích thước phân vùng hiện tại.
- Giữ vbmeta đã disable, nếu không máy sẽ không boot sau khi thay system.

## BẮT BUỘC cho FBE: lấy blob từ vendor stock
Tree không chứa qseecomd/keymaster/gatekeeper nên chưa thể giải mã nếu thiếu bước này.
1. Giải nén vendor.img từ firmware stock (`simg2img vendor.img v.raw && mkdir v && sudo mount -o loop,ro v.raw v`)
2. `python3 samsung/a02q/tools/collect_fbe_blobs.py <thư_mục_vendor> [<thư_mục_system>]`
   - copy service + lib vào `recovery/root/system/{bin,lib,lib64}`
   - sinh `init.recovery.fbe.rc` và `recovery/root/vendor/etc/vintf/manifest.xml`
3. Đọc phần CẢNH BÁO của script (lib thiếu), rồi build lại.

## Permission denied
- Chạy script: `chmod +x build.sh samsung/a02q/tools/*.py` hoặc `bash build.sh` / `python3 tools/...`
- Trong recovery: rc có `chmod 0755` cho từng binary; kernel cmdline thêm `androidboot.selinux=permissive`
- build.sh tự chmod blob trước khi build
- Nếu còn lỗi: gửi dòng log chứa "denied" (`adb shell dmesg | grep -i -E "avc|denied"` và `/tmp/recovery.log`)

## Ổn định MTP
Phát hiện từ kernel/dtb: controller là `ssusb@7000000` (dwc3-msm), node MTP Samsung là `usb_mtp_gadget`.
- init.recovery.usb.rc: các trigger cấu hình gadget (mtp, mtp+adb, adb, fastboot) giờ chỉ chạy khi
  `sys.usb.controller` đã có giá trị -> hết lỗi ghi UDC rỗng khi TWRP bật MTP quá sớm lúc boot
- udc_probe.sh: chỉ `setprop sys.usb.controller` khi giá trị đổi (setprop cùng giá trị vẫn kích hoạt lại
  trigger và làm gadget rebind -> MTP rớt giữa chừng); chỉ ghi `mode` khi chưa là peripheral;
  dừng dò UDC/MTP ngay khi đã tìm thấy; chờ tối đa 30s thay vì 20s
- Bỏ `setprop vendor.usb.controller` chạy khi controller còn rỗng
- Giữ nguyên: PTP tạo sau MTP (yêu cầu của f_mtp Samsung), `TW_MTP_DEVICE := /dev/mtp_usb`

Nếu MTP vẫn rớt: `adb logcat -d | grep -i -E "udc_probe|mtp"` và `adb shell dmesg | grep -i -E "mtp|ci13xxx|ssusb"`.
