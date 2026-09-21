# Thu dữ liệu bằng web tự phục vụ

Web ở `collector/`, tách khỏi gói `turnwise`. Người thu tự làm trên Chrome; người quản trị tạo
link mời, thu giọng bot và tải dữ liệu về. Vì sao thu theo cách này: `docs/progress.md` §6.6.

## Chạy tại máy

```bash
cd collector
uv sync
COLLECTOR_ADMIN_TOKEN=<chuỗi ngẫu nhiên ≥ 16 ký tự> uv run uvicorn app.main:app_factory --factory --port 8000
uv run pytest                                  # 34 test API
COLLECTOR_E2E=1 uv run pytest tests/e2e        # Chrome thật, micro giả, giọng bot giả
uv run python tools/audit_export.py <export.zip>   # kiểm chất lượng file tải về
```

Bài e2e chạy vào container: đặt thêm `COLLECTOR_E2E_URL=http://127.0.0.1:<cổng>` và
`COLLECTOR_E2E_ADMIN_TOKEN`.

Mở `http://localhost:8000/admin`. Trình duyệt chỉ cho dùng micro trên `localhost` hoặc HTTPS.
Dữ liệu mặc định ghi vào `data/collector/` ở gốc repo (đã gitignore).

## Chạy bằng Docker

Build từ **gốc repo**, vì kịch bản nằm ở `roleplay/`:

```bash
docker build -f collector/Dockerfile -t turnwise-collector .
docker run -p 8000:8000 -e COLLECTOR_ADMIN_TOKEN=<token> -v turnwise-data:/data turnwise-collector
```

Thiếu `-v ...:/data` thì app **không chịu khởi động**: dữ liệu trong container mất khi xoá container.

## Thu qua laptop (miễn phí)

Server là container Docker trên laptop; Cloudflare Tunnel cho nó một địa chỉ HTTPS công khai. Dữ
liệu nằm trên laptop, không nằm trên server nước ngoài. Laptop phải bật và có mạng suốt buổi thu.

1. Cài một lần: `winget install --id Cloudflare.cloudflared`, mở terminal mới.
2. Mỗi buổi: bật Docker Desktop (container tự chạy lại), rồi
   `cloudflared tunnel --url http://localhost:8000`. Lệnh in ra `https://<tên>.trycloudflare.com`.
3. Mở `<địa chỉ đó>/admin`. Link mời lấy theo địa chỉ đang mở, nên mỗi buổi chép lại link từ bảng
   Người thu (địa chỉ đổi mỗi lần bật tunnel, mã trong link thì giữ nguyên).
4. Hết buổi: Ctrl+C để tắt tunnel, rồi tải zip về làm bản sao lưu.

## Deploy lên Render

Cấu hình nằm ở `render.yaml` (Blueprint): Docker, Singapore, 1 instance, ổ đĩa 5 GB ở `/data`.

1. Push nhánh có trong `render.yaml` lên GitHub.
2. Render Dashboard: **New** → **Blueprint**, chọn repo, Render đọc `render.yaml`.
3. Điền `COLLECTOR_ADMIN_TOKEN` (ít nhất 16 ký tự) và `COLLECTOR_DATA_CONTROLLER` (tên và cách liên
   hệ bên kiểm soát dữ liệu, hiện trên phiếu đồng ý). Render tự cấp `PORT` và HTTPS.
4. Deploy **bằng tay** (Manual Deploy), giữa các buổi thu: có ổ đĩa thì mỗi lần deploy server tắt
   vài giây, bản gửi đúng lúc đó sẽ báo lỗi và người thu phải bấm Gửi lại.

Thiếu ổ đĩa ở `/data` thì app báo lỗi và không chạy, thay vì chạy rồi mất sạch bản ghi ở lần deploy
lại. Container khởi động bằng root, giao `/data` cho uid 10001 rồi bỏ quyền root trước khi chạy app,
nên ổ đĩa của nền tảng thuộc root cũng ghi được.

Nguồn khác: image `mixp123/turnwise-collector:<commit>` trên Docker Hub, build bằng
`docker build -f collector/Dockerfile -t mixp123/turnwise-collector:$(git rev-parse --short HEAD) .`.

Các biến khác có giá trị mặc định trong `collector/app/settings.py`.

## Trước khi thu người khác

- [ ] Kiểm tra quy định chuyển dữ liệu cá nhân ra nước ngoài trong Luật 91/2025/QH15 nếu server
      đặt ngoài Việt Nam. Chưa kiểm trong repo này.
- [ ] Điền `COLLECTOR_DATA_CONTROLLER`.
- [ ] Người đọc giọng bot đã ký phụ lục B của `docs/annotation-guide.md`.
- [ ] Đã tự thu thử một tình huống và nghe lại cả hai kênh.
- [ ] Đã redeploy một lần sau khi thu thử, và bản ghi thử vẫn còn (ổ đĩa bền hoạt động thật).

## Quy trình

1. **Thu giọng bot** ở `/admin`: đeo tai nghe có dây, đọc đúng từng chữ, `/` là chỗ ngắt hơi.
   Một tình huống chỉ hiện cho người thu khi mọi câu bot của nó đã thu.
2. **Tạo link mời** ở `/admin`, gửi mỗi người một link. Mã trong link là mã người nói (`S001`...).
3. **Người thu** mở link bằng Chrome trên máy tính, đeo tai nghe có dây: đồng ý, bật micro (nút
   tiếp tục chỉ mở khi micro nghe thấy giọng), chọn tình huống, bấm Bắt đầu, nói xong mới bấm nút.
   Hết tình huống thì **nghe lại** rồi **gửi** hoặc thu lại; chưa bấm gửi thì chưa có gì lên server.
   Tình huống đã gửi không hiện lại cho người đó, trừ khi quản trị xoá bản ghi.
4. **Nghe và xoá bản ghi** ở `/admin`, mục Bản ghi. Mỗi bản ghi là trọn cuộc gọi của một tình
   huống, file wav 2 kênh: nghe bằng tai nghe thì tai trái là người thu, tai phải là bot. Xoá thì
   tình huống hiện lại cho người thu đó.
5. **Tải về** ở `/admin` bằng nút tải toàn bộ dữ liệu (.zip), rồi chạy `tools/audit_export.py`.
   Tải sau **mỗi buổi thu**: bản zip trên máy là bản sao lưu, server hỏng thì vẫn còn nó.
   Trong zip: `sessions/<mã người>/<tình huống>-<thời điểm>.wav` kèm `.json` cùng tên (nhật ký phát
   bot, đồng ý), `prompts/` và `collector.sqlite3`. Mở wav bằng Audacity để thấy hai kênh.
   Muốn biết một bản ghi chứa lời gì: `cd asr-check && uv run python transcribe.py <export.zip>`
   (chỉ để kiểm thử, xem `docs/progress.md` §6.7).
6. **Rút lại đồng ý**: người thu liên hệ, quản trị bấm "Rút lại & xoá" ở `/admin`. Bản ghi và bản
   đồng ý bị xoá, link hết hiệu lực, mã người nói không bao giờ được cấp lại.

## Mỗi bản ghi gồm

```
sessions/S001/n1-a-outage-reading-number-<thời điểm>.wav    PCM 16-bit, 48 kHz, kênh 0 khách, kênh 1 bot
sessions/S001/n1-a-outage-reading-number-<thời điểm>.json   nhật ký phát, trình duyệt, bản đồng ý, sha256
collector.sqlite3                                            link mời, đồng ý, danh sách bản ghi
```

Lưu 48 kHz là raw. `WavFrameSource` chạy ở 16 kHz của `configs/default.yaml` và từ chối file lệch
tần số, nên pha 1.5 phải hạ tần số trước khi đọc; `bot_intervals` lấy từ nhật ký là
`(start_sample / 48000, end_sample / 48000)` cho từng mục, tính bằng giây nên không đổi khi hạ.
