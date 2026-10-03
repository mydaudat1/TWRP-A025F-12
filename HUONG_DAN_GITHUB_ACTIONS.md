# Build TWRP a02q bằng GitHub Actions

## Chuẩn bị
1. Đẩy repo lên GitHub. **Nên để repo PUBLIC**: runner miễn phí cho repo public là 4 vCPU / 16GB RAM,
   còn repo private chỉ 2 vCPU / 8GB (theo tài liệu GitHub), build sẽ rất chậm và dễ hết RAM hoặc quá 6 giờ.
2. Trước khi build, chạy `samsung/a02q/tools/collect_fbe_blobs.py` với vendor.img stock rồi commit kết quả
   (nếu không, workflow sẽ hiện cảnh báo và bản build không giải mã được /data).

## Chạy
- Tab **Actions** -> **Build TWRP a02q** -> **Run workflow** (tick "release" nếu muốn tạo Release).
- Xong: tải artifact **twrp-a02q** (`recovery.img`, `recovery.tar` cho Odin, slot AP).
- Lỗi: tải artifact **build-log** (300 dòng cuối) và gửi lại.

## Giới hạn cần biết
- Một job tối đa 6 giờ. Lần đầu chưa có cache có thể mất nhiều giờ; ccache (4GB) được lưu giữa các lần chạy.
- Đĩa runner chỉ ~14GB trống ban đầu; workflow xoá dotnet/android/ghc... để lấy thêm chỗ. Nếu vẫn báo thiếu
  dung lượng, `build-twrp.sh` sẽ dừng với thông báo rõ ràng.
- Source TWRP (~15GB) được sync lại mỗi lần chạy, chưa cache được vì vượt giới hạn cache 10GB của repo.
