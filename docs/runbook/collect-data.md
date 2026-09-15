# Thu dữ liệu bằng web tự phục vụ

Web ở `collector/`, tách khỏi gói `turnwise`. Người thu tự làm trên Chrome; người quản trị tạo
link mời, thu giọng bot và tải dữ liệu về. Vì sao thu theo cách này: `docs/progress.md` §6.6.

## Chạy tại máy

```bash
cd collector
uv sync
COLLECTOR_ADMIN_TOKEN=<chuỗi ngẫu nhiên ≥ 16 ký tự> uv run uvicorn app.main:app_factory --factory --port 8000
uv run pytest                                  # 24 test API
```

Mở `http://localhost:8000/admin`. Trình duyệt chỉ cho dùng micro trên `localhost` hoặc HTTPS.
Dữ liệu mặc định ghi vào `data/collector/` ở gốc repo (đã gitignore).

## Chạy bằng Docker

Build từ **gốc repo**, vì kịch bản nằm ở `roleplay/`:

```bash
docker build -f collector/Dockerfile -t turnwise-collector .
docker run -p 8000:8000 -e COLLECTOR_ADMIN_TOKEN=<token> -v turnwise-data:/data turnwise-collector
```

## Deploy (Railway, Render)

- Nguồn: repo này, Dockerfile `collector/Dockerfile`, build context là gốc repo.
- Gắn **ổ đĩa bền** vào `/data`. Không có ổ bền thì mỗi lần deploy lại mất sạch bản ghi.
- Biến môi trường: `COLLECTOR_ADMIN_TOKEN` (bắt buộc), `COLLECTOR_DATA_CONTROLLER` (tên và cách
  liên hệ bên kiểm soát dữ liệu, hiện trên phiếu đồng ý). Nền tảng tự cấp `PORT` và HTTPS.
- Container chạy bằng user không phải root. Nếu ổ đĩa của nền tảng chỉ cho root ghi, app báo lỗi
  quyền ghi ngay lúc khởi động; khi đó chỉnh quyền ổ theo hướng dẫn của nền tảng.

Các biến khác có giá trị mặc định trong `collector/app/settings.py`.

## Trước khi thu người khác

- [ ] Kiểm tra quy định chuyển dữ liệu cá nhân ra nước ngoài trong Luật 91/2025/QH15 nếu server
      đặt ngoài Việt Nam. Chưa kiểm trong repo này.
- [ ] Điền `COLLECTOR_DATA_CONTROLLER`.
- [ ] Người đọc giọng bot đã ký phụ lục B của `docs/annotation-guide.md`.
- [ ] Đã tự thu thử một tình huống và nghe lại cả hai kênh.

## Quy trình

1. **Thu giọng bot** ở `/admin`: đeo tai nghe có dây, đọc đúng từng chữ, `/` là chỗ ngắt hơi.
   Một tình huống chỉ hiện cho người thu khi mọi câu bot của nó đã thu.
2. **Tạo link mời** ở `/admin`, gửi mỗi người một link. Mã trong link là mã người nói (`S001`...).
3. **Người thu** mở link bằng Chrome trên máy tính, đeo tai nghe có dây: đồng ý, thử micro, chọn
   tình huống, bấm nghe câu bot, nói, bấm khi đã nói xong. Xong tình huống nào, web gửi lên tình
   huống đó.
4. **Tải về** ở `/admin` bằng nút tải toàn bộ dữ liệu (.zip).

## Mỗi bản ghi gồm

```
sessions/S001/n1-a-outage-reading-number-<thời điểm>.wav    PCM 16-bit, 16 kHz, kênh 0 khách, kênh 1 bot
sessions/S001/n1-a-outage-reading-number-<thời điểm>.json   nhật ký phát, trình duyệt, bản đồng ý, sha256
collector.sqlite3                                            link mời, đồng ý, danh sách bản ghi
```

Đọc bằng `WavFrameSource` với `bot_intervals` lấy từ nhật ký:
`(start_sample / 16000, end_sample / 16000)` cho từng mục.
