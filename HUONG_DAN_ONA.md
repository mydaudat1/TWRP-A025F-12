# Build TWRP a02q trên Ona (tên mới của Gitpod)

Gitpod Classic (gitpod.io, `.gitpod.yml`) đã ngừng từ 15/10/2025. Bản thay thế là **Ona** (app.gitpod.io),
dùng `devcontainer.json`. Gói này đã có sẵn cấu hình đó.

## Các bước
1. Tạo repo GitHub trống, giải nén gói này rồi đẩy TOÀN BỘ nội dung lên repo
   (có `.devcontainer/`, `samsung/`, `build-twrp.sh`).
2. Vào https://app.gitpod.io, đăng nhập bằng GitHub, tạo environment từ repo đó.
   Chọn máy lớn nhất mà gói của bạn cho phép (gói Free ghi nhận tối đa 4 vCPU / 16GB RAM / 80GB đĩa
   tại thời điểm mình tra; hạn mức có thể đã đổi, hãy xem trên trang của Ona).
3. Chờ `postCreateCommand` cài xong gói (vài phút).
4. Trong terminal:
   ```
   tmux new -s build
   ./build-twrp.sh
   ```
   Mất kết nối thì vào lại và gõ `tmux attach -t build`.
5. Thời gian ước tính: sync 20–40 phút, build 1–3 giờ với 4 vCPU (ước lượng, không đo).
6. Kết quả ở `out/recovery.tar` (Odin, slot AP, tắt Auto Reboot) và `out/recovery.img`.
   Tải về qua Explorer của editor (chuột phải → Download).

## Sau khi tree chạy được
- Chạy `tools/collect_fbe_blobs.py` (xem GHI_CHU.md) với vendor.img stock TRƯỚC khi build để có giải mã FBE.
- Hết dung lượng: xoá `~/twrp/out` rồi chạy lại; đã build một lần thì ccache giúp lần sau nhanh hơn nhiều.
- Lỗi build: gửi mình 50 dòng cuối của `~/build.log`.
