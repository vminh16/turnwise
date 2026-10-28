# Changelog

Mọi thay đổi đáng kể của Turnwise, nhóm theo giai đoạn của `docs/roadmap.md`, mới nhất ở trên.
Mỗi mục kèm mã commit để tra lại chi tiết; số đo và lý do đầy đủ nằm trong phần mô tả của commit
đó và trong `docs/progress.md`.

Tài liệu này ghi **cái gì đã đổi**. Quyết định và số đo sống ở `docs/progress.md` và `docs/adr/`;
chỗ nào hai bên lệch nhau thì hai tài liệu kia đúng.

## [Chưa phát hành] — nhánh `feat/repo-setup`

Chưa gộp vào `main`, chưa đẩy lên GitHub. 102 commit, 2026-09-10 → 2026-09-27.

### Bộ phân tích — hướng dẫn v2.0 và bốc mẫu (2026-10-28)

- **Thêm** `docs/annotation-guide-conversation.md` v2.0: gán nhãn hội thoại hai người. Mỗi IPU
  mang một nhãn mở đầu theo Gravano & Hirschberg (2011): `H S O PI I BI BC BC_O X`. Kết thúc lượt
  được suy ra, không gán tay. Miền lấy từ nơi sinh trong metadata, không từ tai người gán.
- **Thêm** `evaluation/analysis_sample.py` (`rank`, `prepare`, `status`) và section
  `analysis_sample` trong `configs/default.yaml`. Thứ hạng là `sha256(seed:source:item_id)`;
  mỗi hội thoại một cửa sổ, vị trí tái lập được.
- **Thêm** `data/manifests/analysis-catalog.template.csv`. Nguồn pilot: UCI *Viet Stories*.

### Dữ liệu — đổi hướng (2026-10-28)

**Đổi**

- Dữ liệu tách thành **bộ phân tích** (hội thoại tiếng Việt tự nhiên giữa hai người, ba miền, từ
  corpus đã công bố hoặc nguồn công khai) và **bộ kiểm thử sản phẩm** (đóng vai NetCo). Chỉ số
  chính §9.1 được đo trên bộ phân tích. Không tự thu thêm. ADR-0007; sửa `SPEC.md` §6 và §9.1,
  `AGENTS.md`, `README.md`, `docs/roadmap.md`, `.claude/rules/evaluation.md`.

**Thêm**

- `docs/research/analysis-corpus.md`: nguồn ứng viên theo ba tầng, quy tắc lấy mẫu để không thiên
  lệch, ước lượng cỡ mẫu, và bốn việc chặn trước khi gán nhãn.

**Đã biết**

- Chưa gán nhãn được bộ phân tích: còn chờ quyền truy cập LDC, hướng dẫn gán nhãn mới, chế độ
  người với người cho `evaluation/golden.py`, và một pilot.

### GĐ 4 — Bot chạy thật: khung đã nối (2026-09-27)

**Thêm**

- `uv run turnwise dev [--config ...]`: một cuộc gọi trên micro và loa của máy, decider chọn bằng
  file cấu hình, mặc định hệ đề xuất. Vòng lặp cuộc gọi là chỗ duy nhất ghi mọi `TurnDecision`
  xuống telemetry; ASR, dialog và TTS chạy ở luồng phụ. (`0dd166e`)
- Tầng `audio` sống: bộ đệm vòng cấp phát sẵn, luồng song công micro/loa, khử tiếng vọng WebRTC,
  `LiveFrameSource` và `LiveAudio` ở cùng seam với nguồn đọc file. (`c13d07f`)
- `dialog/`: năm luồng nghiệp vụ N1–N5 bằng máy trạng thái viết tay, backend NetCo giả khớp thẻ đạo
  cụ của kịch bản đóng vai, đọc số thành chữ trước khi đưa cho TTS. Mọi quy tắc SPEC §4.2 có test.
  (`f6a4119`)
- Bảng theo dõi trong terminal (`telemetry/dashboard.py`). (`0dd166e`)
- `scripts/validate_manifests.py` chạy thật, thay cho file rỗng. (`4c5e7b9`)

**Đổi**

- Nhóm tuỳ chọn `tts`: `vieneu` thay `piper-tts` (đã chuyển sang GPL, chưa từng dùng). (`d28b0cf`)

**Đã biết**

- Chưa thử với micro thật; mọi test dùng đồ giả.
- Bot trả lời chậm khoảng 4 giây: TTS 2,38 s, ASR 1,98 s trên laptop dự án. Câu cố định đã được
  nhớ sau lần sinh đầu. (`0dd166e`)

### GĐ 2 và GĐ 3 — Khung benchmark và hệ đề xuất (2026-09-26 → 2026-09-27)

**Thêm**

- `python -m evaluation.run_system <config>`: chạy bất kỳ decider nào trên bộ dữ liệu vàng, mỗi
  đoạn nói đã gán nhãn nhận một phán quyết (đúng kèm độ trễ, cắt lời, nhận nhầm tiếng đệm, quá
  chậm, bot tự ngắt). B1 tự quét dải; `--ablation` chạy thêm một lần cho mỗi scorer bị tắt;
  holdout chỉ mở bằng `--final-report`. (`2116be1`, `65adfeb`)
- **B2** — `pipecat-ai/smart-turn` v3.2, trọng số nguyên bản, vận hành như pipecat. Đặc trưng
  lệch bản gốc tối đa 4,3e-6. (`f0962cd`)
- **B3** — faster-whisper rồi `Namo-Turn-Detector-v1-Vietnamese`, vận hành y như B2. (`353c5e4`)
- **Hệ đề xuất** — bốn scorer (`silence`, `smart_turn`, `final_rise`, `short_ipu`), fusion gộp theo
  từng câu hỏi và cho phép bỏ phiếu trắng, decider `fused`, cấu hình khởi điểm chưa hiệu chỉnh ở
  `configs/proposed/draft.yaml`. (`65adfeb`)
- Nền ồn theo khung ở tầng `audio`, chưa báo khi chưa đủ một cửa sổ 5 giây. (`b68584b`, `f691f80`)

**Đổi**

- Một cổng dò tiếng nói chung cho B1, B2, B3 và hệ đề xuất (`turn/gate.py`), theo nền ồn thay cho
  -45 dBFS cố định. Micro S001 ồn hơn S002 15 dB; với ngưỡng cố định, không baseline nào thấy im
  lặng trên bản thu S001. Đường cong B1 trên kịch bản GĐ 0 không đổi. `turn.silence_floor_dbfs` bị
  thay bằng `turn.gate`. (`f691f80`)
- Cách vận hành "hỏi khi khách im" của B2 tách thành `PauseTriggeredDecider`, dùng chung với B3.
  (`4c7c4d9`)

**Sửa**

- B3 tokenize không đệm, khớp tokenizer gốc 6/6 câu thay vì 0/6. (`bc8c42d`)

**Đã biết**

- B3 tốn trung vị 1 750 ms mỗi lần hỏi, B2 22 ms. Namo chấm các câu trả lời ngắn trọn vẹn ("Sáng
  mai.", "dạ") là chưa xong. (`1ee1fc9`)
- Chưa có nhãn, nên mọi lần chạy benchmark đang chấm 0 đoạn nói.

### GĐ 1 — Dữ liệu vàng (2026-09-14 → 2026-09-27)

**Thêm**

- Pha 1.6: bản nháp TextGrid cho Praat (khoảng bot nói, đoạn nói của khách, chép lời nháp) và bộ
  đọc nhãn; hướng dẫn gán nhãn ở `docs/runbook/annotate.md`. (`6c6ba16`, `a8842af`)
- Pha 1.5: nạp gói export thành manifest có sha256, chia tập theo người nói, khoá holdout một lần,
  từ chối tác giả kịch bản. Manifest 18 bản thu thử của S001 và S002. (`ffb8ad4`, `d61769b`,
  `3cd256d`)
- Web thu tự phục vụ `collector/` (FastAPI, SQLite, Docker): thu hai kênh ở 48 kHz, nghe lại trước
  khi gửi, gửi lỗi không mất bản thu, trang quản trị xuất và nghe lại, chạy qua Cloudflare Tunnel.
  (`fa66532`, `a258c52`, `74d60a0`, `d94d524`, `68f86e9`)
- Chín kịch bản đóng vai cho năm luồng, mỗi lượt có câu mẫu, mỗi cuộc gọi có lời giới thiệu và lời
  chào kết thúc. (`111577e`, `57fac70`, `6ab85e6`)
- Giọng bot VieNeu-TTS v3 Turbo "Minh Quân Pro" int8, sinh sẵn toàn bộ 57 câu bot; cuộc gọi mẫu để
  nghe thử trước khi thu (`tts-check/`, chỉ để thử). (`6a0f72d`, `2789c0a`, `e7bb277`)
- Chép lời chỉ để kiểm dữ liệu thu (`asr-check/`). (`5f63615`)
- Hướng dẫn gán nhãn và mẫu đồng ý tham gia. (`d489ad8`)

**Đổi**

- Web thu hiển thị câu mẫu và lời giới thiệu thay cho gợi ý tình huống. (`417bfbd`, `d9a2601`)
- Nói đè được chấm từ đầu đoạn nói đè. (`4fb5c8d`)

**Sửa**

- `.gitignore` bỏ qua `data/*` để `data/manifests/` commit được; trước đó không file nào trong
  `data/` vào được git. (`b810ed7`)
- Ngưỡng dò đoạn nói trong bản nháp theo nền ồn từng bản; trước đó mỗi bản thu của S001 thành một
  đoạn nói duy nhất. (`3cd256d`)
- Web thu từ chối khởi động nếu không có volume ghi được. (`7ad6dec`)

### Quyết định và nghiên cứu (2026-09-12 → 2026-09-25)

- ADR-0006: chấp nhận giấy phép phi thương mại vì đồ án không thương mại hoá; chỉ từ chối tinh
  chỉnh rồi công bố trọng số có điều khoản ND. (`9766d3e`)
- Khảo sát phương pháp turn-taking cho tiếng Việt ít dữ liệu, gồm đánh giá bài Map Task.
  (`bd87675`)
- Khảo sát TTS tiếng Việt: giấy phép và số đo trên CPU. (`31c035d`)
- SPEC R12: bot phải nghe giống người, không chỉ chuyển lượt đúng. (`54e585c`)
- Timeline tạm, không phải nguồn chân lý. (`f80bf09`)

### GĐ 0 — Đường đo (2026-09-10 → 2026-09-12)

**Thêm**

- Khung dự án: `uv`, CI, chặn holdout, luật theo thư mục, bốn tầng một chiều. (`5ab8a3b`,
  `01f89da`, `a299962`)
- Seam ngoài của `turn` và của `audio`; hợp đồng scorer và decider (ADR-0003, ADR-0004).
  (`860ab8a`, `d6639f2`, `e103cf6`)
- Một cửa nạp cấu hình duy nhất, có test giữ luật đó. (`60b6aed`, `830f265`)
- B1 — ngưỡng im lặng cố định, quét 200–1200 ms. (`9323332`, `8b558fe`)
- Telemetry ghi mỗi quyết định một dòng JSONL. (`a1c3c5e`)
- Năm kịch bản SPEC §10 phát lại không cần micro; kiểm tra ngân sách độ trễ. (`fa6855f`,
  `b673a3a`)
- Ba baseline cho R8 (ADR-0002). (`21200b8`)

**Sửa**

- Đuôi khung được đệm không còn bị đọc thành im lặng. (`b7369ab`)
- Độ trễ trên đường cong B1 bỏ sai lệch một khung. (`fabfacf`)
- CLI chạy được trên console cp1258 của Windows. (`1bc50e4`)
