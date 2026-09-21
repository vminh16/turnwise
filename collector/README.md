# Web thu dữ liệu đóng vai

Người thu mở một link mời, nghe câu tổng đài thu sẵn, nói vào micro; trình duyệt ghi **hai kênh**
(kênh 0 giọng người, kênh 1 giọng bot) rồi gửi lên server. Đây là pha 1.4 của Giai đoạn 1
(`docs/progress.md` §6). Vì sao thu theo cách này, và quy trình một buổi thu đầy đủ:
`docs/runbook/collect-data.md`.

Yêu cầu của người thu: **Chrome trên máy tính** và **tai nghe có dây**. Loa ngoài làm micro thu cả
tiếng bot, hỏng kênh 0.

## Chạy trên máy

```bash
docker build -f collector/Dockerfile -t turnwise-collector .   # chạy ở gốc repo
docker run -d --name turnwise-collector --restart unless-stopped \
  -p 127.0.0.1:8000:8000 -v turnwise-collector-data:/data \
  -e COLLECTOR_ADMIN_TOKEN=<chuỗi ngẫu nhiên ≥ 16 ký tự> \
  -e COLLECTOR_DATA_CONTROLLER="<tên và cách liên hệ>" turnwise-collector
```

Mở <http://localhost:8000/admin>. Thiếu `-v ...:/data` thì app không khởi động: dữ liệu sẽ nằm
trong container và mất khi xoá container.

Chạy thẳng bằng Python khi sửa code: `COLLECTOR_ADMIN_TOKEN=... uv run uvicorn app.main:app_factory
--factory` trong thư mục này. Test: `uv run pytest`, thêm `COLLECTOR_E2E=1` để chạy cả Chrome thật.

## Mời người khác thu, bằng Cloudflare Tunnel (miễn phí)

Server vẫn chạy trên laptop, Cloudflare chỉ cấp cho nó một địa chỉ HTTPS công khai. Dữ liệu không
đi qua server thuê ngoài. Cài một lần: `winget install --id Cloudflare.cloudflared`.

```bash
cloudflared tunnel --url http://localhost:8000
```

Lệnh in ra `https://<tên>.trycloudflare.com` và phải để nguyên cửa sổ đó mở. Mở
`<địa chỉ>/admin`, chép link mời từ bảng **Người thu** rồi gửi cho từng người. Địa chỉ đổi mỗi lần
bật lại tunnel nên phải gửi lại link; mã người nói trong link thì giữ nguyên.

Trong buổi thu: tắt chế độ ngủ của laptop, cắm sạc. Hết buổi: Ctrl+C để tắt tunnel, và tải zip về
làm bản sao lưu.

## Một buổi thu, gọn

1. Nạp giọng bot: `cd tts-check && COLLECTOR_ADMIN_TOKEN=... uv run python render_prompts.py`
   sinh mọi câu bằng giọng đã chốt (`docs/progress.md` §6.8) và nạp vào collector. Nghe lại ở
   `/admin` → **Giọng tổng đài**; câu nào hỏng thì sinh lại riêng bằng `--only <script>/<step>`.
   Tình huống chỉ hiện cho người thu khi mọi câu bot của nó đã có.
2. **Tạo link mời** → gửi mỗi người một link.
3. Người thu: đồng ý → bật micro → chọn tình huống → Bắt đầu → nghe lại → Gửi. Chưa bấm Gửi thì
   chưa có gì lên server; gửi hỏng thì bản thu vẫn còn để bấm Gửi lại.
4. `/admin` → **Bản ghi**: nghe (tai trái người thu, tai phải bot), xoá nếu hỏng.
5. **Tải toàn bộ dữ liệu** (.zip) sau mỗi buổi, rồi `uv run python tools/audit_export.py <zip>`.

## Dữ liệu

Thu và lưu 48 kHz, cả hai kênh, khoảng 11,5 MB mỗi phút. Tất cả nằm trên volume `/data`:
`collector.sqlite3`, `sessions/<mã người>/<tình huống>-<mốc>.wav` kèm file `.json` cùng tên (nhật ký bot phát câu nào ở mẫu nào, phiếu đồng ý, thông tin máy), và
`prompts/` là giọng bot. File zip tải về có đúng các thứ đó.

Thu **raw**: không cắt, không chuẩn hoá âm lượng, không lọc ồn. Xử lý là việc của lúc phân tích.

Rút lại đồng ý: `/admin` → **Rút lại & xoá**. Bản ghi và phiếu đồng ý bị xoá, link hết hiệu lực,
mã người nói không bao giờ cấp lại.
