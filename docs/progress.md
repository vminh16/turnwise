# Nhật ký triển khai

Tài liệu này trả lời ba câu: **đã làm gì**, **đang ở đâu**, **kết quả ra sao**. Nó không
thay `SPEC.md` (bài toán) hay `docs/roadmap.md` (thứ tự và lý do); khi mâu thuẫn thì hai
tài liệu kia đúng.

Quyết định kỹ thuật ghi thẳng ở đây thay vì tách thành ADR riêng, để một người mới đọc
một file là nắm được trạng thái. ADR dành cho quyết định kiến trúc lớn của các giai đoạn
sau.

Cập nhật lần cuối: 2026-09-14. Nhánh `feat/repo-setup`.

---

## 1. Giai đoạn 0 — Đường đo: **xong**

Điều kiện xong theo `docs/roadmap.md` §6: *`pytest -m scenario` xanh; `run_baseline.py`
vẽ được đường cong B1*. Cả hai đạt.

| Pha | Sinh ra | Commit | Cổng |
|---|---|---|---|
| 0.1 Cấu hình | `src/turnwise/config.py` | `60b6aed`, `830f265` | 10 test |
| 0.2 Nguồn khung | `src/turnwise/audio/source.py` | `9f3673b`, `b7369ab` | 15 test |
| 0.3 B1 | `turn/deciders/silence_threshold.py` | `9323332` | 13 test |
| 0.4 Ghi vết | `telemetry/collector.py` | `a1c3c5e` | 16 test |
| 0.5 Năm kịch bản | `scenarios/*.yaml`, `evaluation/scenario.py` | `fa6855f`, `2f160e7` | `-m scenario` |
| 0.6 Đo và vẽ | `evaluation/metrics.py`, `run_baseline.py`, `figures.py` | `8b558fe`, `d4d7e32` | CSV + PNG |
| 0.7 Ngân sách | `tests/latency/test_budget.py`, `tests/conftest.py` | `b673a3a`, `b2f6694` | `-m latency` 3 |
| Sửa sau review | sáu chỗ, xem §4 | `fabfacf`, `2f160e7`, `b7369ab` | 111 test |

Trạng thái cổng hiện tại:

```
uv run ruff check . && uv run ruff format --check . && uv run mypy   # xanh, 58 file
uv run pytest                                                        # 111 passed
uv run pytest -m scenario                                            # 10 passed
uv run pytest -m latency                                             # 3 passed
uv run python evaluation/run_baseline.py                             # CSV + PNG
```

Không thêm phụ thuộc runtime nào trong cả giai đoạn. `uv sync --extra research` chỉ phục
vụ `evaluation/figures.py` và các giai đoạn offline về sau.

### 1.1 Chốt: đạt cả bảy điều kiện ra

Chấm ngày 2026-09-12, sau khi sửa xong các phát hiện của review (§4). Cột bằng chứng là
lệnh đã chạy lại tại thời điểm chốt, không phải kết quả nhớ lại.

| Pha | Điều kiện ra | Chốt | Bằng chứng |
|---|---|---|---|
| 0.1 | Hai file YAML nạp thành object đã kiểm kiểu; ngưỡng quyết định vẫn `None`; không module nào ngoài `config.py` đọc YAML hay `os.environ` | đạt | 10 test, trong đó một test tĩnh quét `src/` |
| 0.2 | Wav 16 kHz cho đúng `ceil(len/320)` khung; `index` không nhảy; `start_s` cách đều; kích thước khung từ config | đạt | 15 test, có test đổi `feature_frame_ms` 20→40 |
| 0.3 | `decide()` trả ở mọi khung với `scores == {}`; `reset()` tái lập; đổi ngưỡng chỉ bằng sửa config; `isinstance(obj, TurnDecider)` | đạt | 13 test + 5 test registry; công tắc `turn.decider` có thật từ `fabfacf` |
| 0.4 | Mỗi `TurnDecision` thành đúng một dòng JSONL đủ sáu trường; `turn/` không import `telemetry`; không `print()` | đạt | 16 test, kiểm import bằng `ast`; `ruff` rule `T20` bật toàn repo |
| 0.5 | Marker `scenario` thu được test; năm kịch bản chạy hết; tất định giữa hai lần chạy; không cần micro | đạt | `-m scenario` 10 passed; test tất định băm mẫu tín hiệu, đã kiểm bằng cách bỏ hạt giống |
| 0.6 | Một lệnh sinh đường cong 11 điểm trong `reports/`, hai trục cùng lúc; `evaluation/` không chứa đường ra quyết định; không đọc `data/holdout/` | đạt | `run_baseline.py` sinh CSV + PNG; adapter dựng qua registry; cột `latency_source` trên mọi hàng |
| 0.7 | Mọi lệnh "Before Marking Done" xanh; marker `latency` thu được ít nhất một test | đạt | `-m latency` 3 passed; `tests/conftest.py` có fixture wav dùng chung từ `b2f6694` |

Hai chỗ **cố ý** chấm là đạt dù khác câu chữ ban đầu:

- Điều kiện 0.3 nêu đích danh `AudioProcessor.has_voice()`. Hàm đó không dùng được (§3,
  quyết định 1), nên phần "dò tiếng nói" đạt bằng cổng năng lượng, và lý do ghi ở đây
  thay vì trong một ADR riêng.
- `AGENTS.md` mục 5 đòi một ADR cho lựa chọn phương pháp mới. Quyết định của dự án là ghi
  vào chính tài liệu này (§3) thay vì tách bảy file ADR cho một giai đoạn hạ tầng.

Giai đoạn 0 **đóng**. Những gì còn thiếu ở §4 và §5 không thuộc điều kiện ra của giai
đoạn này; chúng là đầu vào của Giai đoạn 1 và 4.

---

## 2. Kết quả đo

### 2.1 Đường cong B1

`reports/baseline/silence-threshold.csv`, 11 ngưỡng × 5 kịch bản.

| Ngưỡng | Cắt lời (÷4) | Đáp trung vị | Không đáp (÷4) | Tiếng đệm nhận nhầm (÷1) |
|---|---|---|---|---|
| 200–800ms | 25% | bằng ngưỡng | 0 | 100% |
| 900ms | 0% | 900ms | 0 | 100% |
| 1000ms | 0% | 1000ms | 1 | 100% |
| 1100–1200ms | 0% | 1100–1200ms | 2 | 100% |

Đọc: hẹp thì cắt lời khách đang ngập ngừng giữa dãy số; rộng thì hết cắt lời nhưng đáp
chậm thêm nửa giây; quá 900ms thì có kịch bản bot không đáp gì trong cả clip. Cột cuối
không đổi ở bất kỳ ngưỡng nào.

Đó là `SPEC.md` §1 được **đo** chứ không được phát biểu: không giá trị ngưỡng nào thắng
cả hai trục, và không ngưỡng nào cứu được R4, vì cổng năng lượng không có trục để phân
biệt tiếng đệm.

### 2.2 Ngân sách mỗi khung

```
ngân sách một khung đặc trưng 20ms      10,00 ms   (hệ số thời gian thực 0,5)
B1 decide()  trung vị                    0,0072 ms
             p95 / max                   0,0078 / 0,0287 ms
phát lại 10s audio                       0,005 s
```

B1 dùng khoảng một phần nghìn ngân sách. Ghi lại để mỗi mili giây hệ đề xuất tiêu về sau
là một lựa chọn có chủ ý.

### 2.3 Ba giới hạn của mọi con số ở trên

1. **Độ trễ tính trên file.** `SPEC.md` §9.3 quy tắc 4 đòi số đo trên hệ chạy trực tiếp;
   cách tính hiện tại bỏ qua đệm audio, TTS khởi động và jitter. Cột `latency_source`
   trong CSV ghi `file-based` trên mọi hàng. Số báo cáo được thuộc Giai đoạn 4.
2. **Âm thanh là nhiễu trắng tổng hợp.** Các con số nói về đường ống, không nói gì về độ
   chính xác trên tiếng Việt thật. Dữ liệu thật là Giai đoạn 1.
3. **Chưa có chỉ số theo thanh điệu** — kết quả khoa học chính ở §9.1. Nhiễu trắng không
   có âm tiết nào để gán thanh.

Ngoài ra `interruption_rate` có mẫu số 4, `backchannel_error_rate` có mẫu số **1**. Một
tỉ lệ 100% ở cột cuối nghĩa là một kịch bản sai một lần, không phải cả bộ sai. Hai cột
`turn_scenarios` và `backchannel_scenarios` trong CSV nói rõ điều đó.

---

## 3. Quyết định kỹ thuật đã chốt

**1. B1 dùng cổng năng lượng, không dùng `AudioProcessor.has_voice()`.**
Đo ngày 2026-09-10: `has_voice()` trả `False` cho mọi đầu vào, kể cả tín hiệu giống tiếng
nói ở 16 kHz, ở mọi mức aggressiveness — bản WebRTC APM này đã bỏ module
`voice_detection`. Ngoài ra tổng đài mà §1 bác bỏ vốn chạy bằng năng lượng; một baseline
dùng VAD học máy sẽ mạnh hơn thứ đang bị bác bỏ.
→ `configs/baseline/silence-threshold.yaml`

**2. Giai đoạn 0 dùng kích thích tổng hợp thay năm phép thử §10.**
Chưa có dữ liệu đóng vai. Đủ để kiểm đường ống, cổng năng lượng và tính tất định; không
đủ để nói gì về độ chính xác. Mỗi file kịch bản tự ghi giới hạn đó trong header.
→ `evaluation/scenario.py`, `scenarios/*.yaml`

**3. Ngân sách mỗi khung suy ra từ hệ số thời gian thực.**
`budget_per_frame_ms` đặt trên khung capture 10ms; khung đặc trưng dài gấp đôi nên ngân
sách gấp đôi. Đổi `feature_frame_ms` thì ngân sách đi theo, không phải sửa test.
→ `tests/latency/test_budget.py`

**4. Adapter chọn bằng registry theo config, không import thẳng tên lớp.**
ADR-0003: công tắc đó mới làm "cùng ASR, TTS, kịch bản" của R8 thành sự thật cấu trúc.
Một điểm trên đường cong là một `TurnConfig` trọn vẹn.
→ `src/turnwise/turn/deciders/__init__.py`

**5. Mốc nhận lượt là cuối khung.**
`at_s` là mốc đầu khung, nhưng thông tin biện minh cho quyết định phủ cả khung. Lấy đầu
khung làm mốc khiến mọi số độ trễ thấp đi đúng một khung.
→ `evaluation/metrics.py`

**6. Khung cuối đệm không, và mang theo `padded_samples`.**
Bỏ đuôi đi là mất đúng đoạn quyết định lượt nói xảy ra. Nhưng đệm làm loãng RMS 15 dB,
nên khung phải nói thật phần nào là tín hiệu.
→ `src/turnwise/types.py`, `src/turnwise/audio/source.py`

**7. Telemetry ghi ở một chỗ cho mỗi đường chạy.**
ADR-0003 viết "ở `transport/`"; Giai đoạn 0 chưa có `transport/` nên người gọi là hai bộ
chạy offline. Câu chữ ADR sẽ cần sửa ở Giai đoạn 4, không phải code.
→ `src/turnwise/telemetry/collector.py`

---

## 4. Review độc lập và những gì đã sửa

Một agent độc lập soát lại toàn bộ Giai đoạn 0: chạy lại mọi lệnh, quét dải hai lần, thử
phá. Nó xác nhận kết quả tái lập được — CSV, PNG và cả 55 file JSONL giống nhau từng
byte — và tìm ra hai lỗi chặn cùng tám lỗi nặng.

**Đã sửa:**

| Phát hiện | Ảnh hưởng thật |
|---|---|
| Độ trễ thấp hơn đúng một khung trên mọi hàng | Thước đo có sai số hệ thống trên chính trục nó đo. 180 thành 200, 1180 thành 1200 |
| CSV và log không ghi nhãn `file-based` | Hai đường một con số thoát ra sổ tay người khác mà mất ngữ cảnh |
| Tỉ lệ không đi kèm mẫu số | `1.0` đọc như cả bộ sai, thật ra là một kịch bản |
| `run_baseline` import thẳng tên lớp | Công tắc R8 là lời hứa, không phải cấu trúc |
| Test tất định rỗng | Bỏ hẳn hạt giống, test cũ vẫn xanh. Bản mới băm mẫu tín hiệu |
| `with_suffix` cắt tên sau dấu chấm; `C:` thoát khỏi `telemetry.dir` | Hai lần chạy đè lên nhau; file ghi ra ngoài thư mục |
| `scenarios/*.yaml` không kiểm kiểu | Gõ nhầm `turn_end_ms: null` lặng lẽ đổi mẫu số từ 1/4 thành 1/3 |
| Khung đệm làm loãng năng lượng 15 dB | Giai đoạn 1 sẽ sinh lượt "đã xong" không có thật |

**Chưa sửa, có chủ ý** — đều là việc của Giai đoạn 1; làm bây giờ là đoán trước dữ liệu:

- `p90` bằng y hệt trung vị vì B1 cho độ trễ hằng số. Giữ cột để Giai đoạn 1 điền phương
  sai thật.
- Chốt TAKE hiện là **một lượt một clip**. Ghi âm thật có nhiều lượt, nên cả decider lẫn
  mẫu số của `metrics.py` (hiện theo kịch bản, không theo từng khoảng ngừng) phải làm
  lại, và mọi con số Giai đoạn 0 sẽ không so sánh trực tiếp được qua mốc đó.
- `synthesize()` gắn liền với `Scenario`; đổi sang wav thu thật cần tách nguồn kích thích
  khỏi mô tả kịch bản.
- `WavFrameSource` từ chối file nhiều kênh. Hội thoại hai kênh cần một adapter mới **và**
  một quyết định về chính kiểu của seam — `FeatureFrame` hiện mang đúng một mảng mẫu.
- Cổng `-m latency` có độ dư khoảng 1400 lần: một hồi quy 1000 lần vẫn xanh. Ngưỡng ở
  đó là **ngân sách**, không phải mốc hồi quy; đặt thêm một mốc chặt hơn bây giờ là bịa
  ra một con số chưa ai đo. Khi có hệ chạy sống ở Giai đoạn 4 thì mốc hồi quy mới có cơ
  sở.

---

## 5. Còn thiếu so với một sản phẩm

Giai đoạn 0 chỉ là đường đo. Theo `SPEC.md` §9.1, bốn trong sáu chỉ số đã đo được (trên
tín hiệu giả); ba chỉ số còn lại cần hệ chạy sống: thời gian từ lúc khách nói đè tới lúc
bot im, tỉ lệ bot nhận nhầm tiếng của chính mình, và chênh lệch lỗi theo thanh điệu. Toàn
bộ §9.2 — thời gian hoàn tất luồng, tỉ lệ không phải chuyển người, số lần khách lặp lại —
chưa có gì vì `dialog/` còn rỗng.

Hai quyết định trước đây còn treo, nay đã đóng:

- **Giấy phép** — ADR-0006: đồ án phi thương mại nên chấp nhận cả NC và GPL, kể cả đường
  chạy chính; `praat-parselmouth` ở lại; `LICENSE` giữ rỗng và repo không công khai trong
  học kỳ này. Chỉ trọng số có điều khoản ND là không được tinh chỉnh rồi công bố.
- **Giọng TTS tiếng Việt** — §6.8: VieNeu-TTS v3 Turbo, preset "Minh Quân Pro", int8,
  Apache-2.0. `piper-tts` trong nhóm `tts` của `pyproject.toml` thành thừa, chờ gỡ.

**Chưa có bot.** Tính tới 2026-09-15: `dialog/`, `transport/` và toàn bộ `audio/` trừ
`source.py` đều rỗng; chưa cài gói ASR hay TTS nào. Bot giống người là yêu cầu R12, không phải
phần trang trí làm sau cùng.

---

## 6. Giai đoạn 1 — Bộ dữ liệu vàng: **đang làm**

Bằng chứng nền: `docs/research/reuse-audit.md` và `docs/research/data-and-method.md`.

### 6.1 Dữ liệu này dùng để làm gì

**Giai đoạn 1 thu bộ dữ liệu vàng để kiểm thử**: người thật nói chuyện với bot, gán nhãn
cẩn thận, dùng để đo. Nó **không** phải dữ liệu huấn luyện.

**Fine-tune không bị loại trừ, nhưng phải có lý do chính đáng.** Sau khi có bộ dữ liệu và
Giai đoạn 2 đã đo B1, B2, B3 trên đó, chỉ tinh chỉnh khi số đo chỉ ra một chỗ hỏng cụ thể
mà cách rẻ hơn (chỉnh ngưỡng, kết hợp tín hiệu có sẵn) không vá được. Lý do đó ghi vào
tài liệu này kèm con số. Không có lý do thì không tinh chỉnh. Nếu tinh chỉnh, dữ liệu
huấn luyện phải lấy từ nguồn khác; bộ dữ liệu vàng không bao giờ được dùng để huấn luyện.

**Giả định cần bạn xác nhận ở pha 1.5.** Holdout mở đúng một lần (`SPEC.md` §9.3), nên
Giai đoạn 2 không thể chọn hướng trên chính holdout. Giả định: bộ dữ liệu vàng chia hai
phần rời nhau về người nói — phần **dev** để Giai đoạn 2 quét B1, so sánh và chọn hướng;
phần **holdout** khoá lại cho báo cáo cuối. Cả hai đều chỉ dùng để đo.

### 6.2 Các pha

| Pha | Sinh ra | Trạng thái |
|---|---|---|
| 1.1 Kịch bản đóng vai | `roleplay/*.yaml`, `evaluation/roleplay.py`, test độ phủ | **xong** |
| 1.2 Hướng dẫn gán nhãn + đồng ý | `docs/annotation-guide.md` | **xong**, ba giả định chờ chốt ở 1.6 |
| 1.3 Đọc được hai kênh | `FeatureFrame.bot_speaking`, `WavFrameSource` đọc file khách + bot kèm log phát | **xong** |
| 1.4 Web thu tự phục vụ + buổi thử | `collector/` (FastAPI + SQLite + Docker), `docs/runbook/collect-data.md` | code **xong**; chờ deploy và buổi thử |
| 1.5 Manifest, chia tập, khoá holdout | `evaluation/dataset.py`, `data/manifests/recordings.csv` | **xong** bản gọn; holdout chưa khoá, chờ đủ người |
| 1.6 Quy trình gán nhãn | `evaluation/annotation.py`, `docs/runbook/annotate.md`; Praat | **xong** bản gọn: bản nháp TextGrid và đọc lại nhãn; chưa đo độ đồng thuận |
| 1.7 Thu thật, đóng giai đoạn | điều kiện xong của `roadmap.md` §6 | chưa |

Việc đã biết trước cho 1.5: `scripts/check_holdout_isolation.py` chặn mọi file trong
`scripts/` có chữ `holdout`, nên bước khoá holdout không thể là một script trong `scripts/`.
Không giải bằng cách nới script chặn.

### 6.3 Pha 1.1 — kịch bản đóng vai

Chín kịch bản cho năm luồng, 57 lượt bot, cộng `roleplay/common.yaml` với các câu dùng
chung khi buổi thu lệch kịch bản. `uv run pytest tests/unit/test_roleplay_scripts.py`: 28
test. Commit `111577e`, sửa theo rà soát độ tự nhiên ở `17dace2`.

| Kiểm tra | Kết quả |
|---|---|
| Mỗi luồng N1–N5 có kịch bản | đủ năm |
| Mỗi hành vi có ở ít nhất hai luồng | ngập ngừng, tiếng đệm, câu dài: 4 luồng; ngắt lời: 3; gặp nhân viên: 3; câu ngắn: 5 |
| Gặp nhân viên giữa lúc bot đang đọc, ngoài N5 | có ở N2 và N4 |
| "Dạ." là một câu trả lời trọn, không chỉ là tiếng đệm | có ở bốn luồng |
| Gợi ý câu trả lời ngắn phủ sáu thanh ở âm tiết cuối | nặng 17, sắc 15, ngang 15, huyền 9, hỏi 7, ngã 5 |
| Mọi cuộc gọi do bot khép lại: chào kết thúc, hoặc chuyển máy nếu khách đòi gặp nhân viên | đủ chín |
| Mọi đoạn bot đọc có dấu `/` đánh chỗ ngắt hơi | kiểm lúc nạp |

Đã thử phá: bỏ ba câu gợi ý kết thúc bằng thanh ngã thì kiểm tra độ phủ thanh báo thiếu.

**Rà soát độ tự nhiên (`17dace2`).** Bản đầu dặn người tham gia *diễn* hành vi ("dừng hẳn
lại vài giây", "chêm dạ hai ba lần"). Ngập ngừng và tiếng đệm diễn ra không có nhịp của thứ
thật, mà nhịp chính là thứ bộ dữ liệu đo. Bản sửa để **nhiệm vụ** sinh ra hành vi: số thuê bao
lẫn giữa mã khách hàng và số hợp đồng trên hoá đơn giả (cách nhà mạng thật hỏi thông tin: họ tên
chủ hợp đồng, số điện thoại, địa chỉ lắp đặt, tình trạng đèn modem — trang báo hỏng của VNPT);
mã lịch hẹn nằm trong tin nhắn không dấu; người tham gia ghi giờ hẹn và từng khoản cước ra giấy
trong lúc bot đọc. Thêm "Dạ." trọn lượt, vì bản đầu chỉ có "dạ" kiểu tiếng đệm nên ca khó nhất
của R4 không đo được. Câu bot mở đầu bằng "Dạ" giảm từ 41/46 xuống 3/46.

Giới hạn của rà soát: các diễn đàn công khai (tinhte, voz) chặn truy cập tự động nên không đọc
được lời kể cuộc gọi thật từ người dùng. Bằng chứng về cách nói thật chỉ gồm trang hướng dẫn
của nhà mạng và báo chí về trải nghiệm tổng đài tự động. Nội dung vẫn cần người bản ngữ ngoài
nhóm đọc thử và một buổi thu thử (1.4).

Quyết định và lý do:

- **Lời bot viết đủ từng chữ, lời khách chỉ là chỉ dẫn.** Bot được đóng bằng câu thu sẵn,
  người điều khiển bấm phát (Wizard-of-Oz), vì `dialog/` còn rỗng và giọng TTS tiếng Việt
  chưa chốt. Khách mà đọc thuộc lòng thì mất đúng thứ cần đo: ngập ngừng, tiếng đệm, nói đè
  tự nhiên. Ngoại lệ là câu trả lời ngắn, có danh sách gợi ý để phủ đủ thanh điệu.
- **Số thuê bao, mã lịch hẹn, địa chỉ in trên thẻ giả.** Câu bot đọc lại thu sẵn nên phải
  khớp với thứ khách đọc. Phải dò số trên thẻ cũng tự sinh ra ngập ngừng thật như phép thử
  `SPEC.md` §10.1. Hai kịch bản cố ý cho bot đọc sai (số thuê bao, địa chỉ) để có ca ngắt
  lời có nội dung.
- **Bot xưng "em", gọi khách là "quý khách".** Câu thu sẵn không đổi được "anh/chị" theo
  giọng người gọi.
- **Tiếng đệm và ngắt lời bắt buộc rơi vào bước bot đang đọc đoạn dài** (`reading`: số,
  số tiền, địa chỉ, điều khoản), kiểm lúc nạp. Không có đoạn đọc thì không có chỗ để chêm.
- **Có `long_answer`**, vì phép thử §10.5 là so sánh câu ngắn với câu dài; thiếu câu dài
  thì không có mốc so.
- **Kịch bản ở `roleplay/`, schema ở `evaluation/roleplay.py`**, đặt song song với
  `scenarios/` và `evaluation/scenario.py`. Không để trong `scenarios/` vì `-m scenario`
  nạp mọi file ở đó. Schema ở `evaluation/` vì mục đích của dữ liệu là đo, và để công cụ thu
  ở 1.4 chỉ là lớp CLI mỏng như `PROJECT-STRUCTURE.md` quy định cho `scripts/`.
- **`final_syllable_tone()` đọc thanh từ chữ viết** bằng `unicodedata` của thư viện chuẩn.
  Hiện nằm trong `evaluation/roleplay.py`; pha 1.6 cần đúng hàm này để gán thanh cho lời
  khách, lúc đó mới quyết định chỗ đặt chung.

**Bước kết thúc.** Bản đầu dừng ở câu hỏi cuối của bot: câu chào kết thúc nằm ở
`common.yaml` cho người điều khiển bấm, mà web tự phục vụ không có người điều khiển, nên cuộc
gọi cụt. Nay mỗi kịch bản tự khép lại: sáu luồng chào kết thúc, ba luồng có đòi gặp nhân viên thì
chuyển máy. N3 và N4 thêm câu "còn cần hỗ trợ gì thêm" như tổng đài thật, lấy thêm câu trả lời
ngắn (thanh ngã từ 3 lên 5). Ở N3 đổi lịch, bỏ gợi ý "Đổi sang chiều." vì câu bot kế tiếp thu
sẵn không đáp lại được yêu cầu đó. Test `test_every_call_is_closed_by_the_bot` giữ quy tắc này.

Giới hạn: nội dung kịch bản chưa được người bản ngữ ngoài nhóm đọc thử. Độ phủ thanh điệu
ở đây là của **gợi ý**; thanh thật của lời khách chỉ biết sau khi gán nhãn ở 1.6.
Tiếng ồn nền (`SPEC.md` §4.3) và bot tự nghe tiếng mình (R5) là điều kiện của buổi thu,
không phải nội dung kịch bản, nên thuộc 1.4.

### 6.4 Pha 1.2 — hướng dẫn gán nhãn và mẫu đồng ý

`docs/annotation-guide.md`, phiên bản 1.0.

Quyết định và lý do:

- **Nhãn trung tâm `caller_act` hỏi "bot lẽ ra phải làm gì" ở cuối mỗi đoạn khách nói**:
  `hold`, `take`, `backchannel` (đúng ba giá trị của `TurnDecision`), cộng `barge_in` và
  `aside`. Nhãn khớp thẳng với chỗ chấm điểm, không cần bảng đổi.
- **Nhãn gán sau khi nghe đoạn phía sau**, không gán theo từ. "Dạ." và "dạ" cùng chuỗi âm,
  khác nhãn.
- **Thuộc tính `cut_in`** giữ lại những lần người điều khiển nói chen khi khách chưa xong. Đó là
  những lần cắt lời thật, không được sửa thành `take`.
- **Pause, gap, overlap và bốn trạng thái `self/other/none/both` lấy nguyên từ Heldner &
  Edlund (2010)**, không tự đặt. Ngưỡng 180 ms và 90 ms của bài báo là mặc định tham khảo; giá
  trị thật đặt trong `configs/` ở pha 1.6.
- **Thanh điệu không gán tay**, đọc từ lời chép bằng `final_syllable_tone`. Vì vậy số phải
  chép bằng chữ. `dialect` là trường bắt buộc, vì giọng Nam nhập thanh hỏi và ngã.
- **Chỉ thu metadata phép đo cần**: mã người nói, vùng giọng, xác nhận đủ 18 tuổi. Không thu
  giới tính, vì F0 chuẩn hoá theo từng người chứ không theo giới.
- **Mẫu đồng ý bám Luật 91/2025/QH15** (Điều 9, 10, 11, 14; đọc từ bản có chữ ký số), có ô
  đồng ý riêng cho từng mục đích. Mẫu nói rõ "tổng đài" do người bấm phát, và ghi rằng dữ liệu
  **không** dùng để huấn luyện; muốn dùng khác thì phải xin đồng ý lại. Điều đó khoá quy tắc ở
  §6.1 bằng một văn bản người tham gia đã ký, không chỉ bằng một dòng trong tài liệu này.

Ba giả định chờ chốt ở pha 1.6: gán kép **20%** số buổi; ngưỡng chấp nhận **κ ≥ 0,7** trên
`caller_act`, báo riêng cho các đoạn chỉ gồm một tiếng đệm; công cụ gán nhãn là Praat hay ELAN.

**Cách thu: bot là câu thu sẵn, không cần bot thật.** Người thật đóng khách; lời bot là câu một
người đọc sẵn một lần. (Ban đầu định có người điều khiển bấm phát; pha 1.4 đổi sang web tự phục vụ,
xem §6.6.) Không dùng bot thật vì dữ liệu sẽ
lệch về decider đã thu nó. Không dùng hai người đóng vai vì người gọi nói với người khác với nói
với máy (`SPEC.md` §3), và "tổng đài viên" thật sẽ chêm tiếng đệm như bot không bao giờ làm.
Ba giới hạn đã chấp nhận:

- Bot chỉ đáp khi người thu bấm, nên khoảng lặng trước câu bot là độ trễ bấm nút, không phải
  độ trễ của một hệ. Nhãn ghi ý định của khách nên không sai; log ghi mốc bấm nút.
- Bản ghi chỉ có một diễn biến: đo được từng quyết định đúng hay sai, không đo được khách phản
  ứng thế nào sau một quyết định sai. Phần đó đo trực tiếp ở Giai đoạn 4.
- Giọng bot thu sẵn khác giọng TTS của Giai đoạn 4; khi chốt TTS, thu lại một phần nhỏ để đo
  độ lệch.

Người đọc giọng bot cũng ký đồng ý (phụ lục B của hướng dẫn).

Giới hạn: mẫu đồng ý không phải tư vấn pháp lý. Luật để Chính phủ ban hành danh mục dữ liệu
nhạy cảm; danh mục đó chưa kiểm chứng, nên mẫu xử lý giọng nói như dữ liệu nhạy cảm. Nguồn về
việc nhập thanh hỏi–ngã ở giọng Nam mới đọc qua trích đoạn, chưa đọc toàn văn.

### 6.5 Pha 1.3 — đọc file hai kênh

`FeatureFrame` thêm cờ `bot_speaking`; `WavFrameSource` đọc file hai kênh (khách + bot) kèm
`bot_intervals` lấy từ log phát. File một kênh chạy như cũ. 12 test mới.

- **Khung mang cờ, không mang tiếng bot.** Decider cần biết bot có đang nói ("dạ" khi bot nói
  là tiếng đệm, khi bot im là câu trả lời), nhưng scorer không được nghe tiếng bot (R5).
- **Cờ theo log phát, không theo năng lượng**: trong chỗ ngắt hơi `/` kênh bot im mà bot vẫn
  giữ lượt. Cờ bật nếu bot phát ở bất kỳ phần nào của khung; khoảng nửa mở, tính trên chỉ số
  mẫu nguyên.
- **File hai kênh thiếu log thì từ chối**, vì chạy tiếp thì cờ luôn tắt mà không có gì báo.
  Log chồng nhau, rỗng, ngược hay âm cũng từ chối.
- Thứ tự kênh ở `audio.recording_caller_channel` trong `configs/default.yaml`.
- B1 **không** dùng cờ: tổng đài cũ không biết bot có đang nói.

Bằng chứng: đường cong B1 `reports/baseline/silence-threshold.csv` trùng từng byte trước và
sau (sha256 `0eaf9258…`). Thử phá hai chỗ (bỏ qua kênh trong config, nhận log chồng nhau), mỗi
chỗ đều có test đỏ. Cổng: ruff, mypy (61 file), pytest 151, `-m latency` 3, `-m scenario` 10.

Chưa làm: khử vọng cho file (`audio/aec.py` còn rỗng; buổi thu bằng tai nghe chưa cần, buổi
thu bằng loa thì cần trước khi dùng cho R5).

### 6.6 Pha 1.4 — web thu tự phục vụ

`collector/`: thư mục riêng, môi trường `uv` riêng, `Dockerfile` riêng, không import `turnwise`.
FastAPI + SQLite + thư mục file trên một volume. Cách chạy và deploy: `docs/runbook/collect-data.md`.

Người thu mở link riêng, ký đồng ý điện tử, thử micro, chọn tình huống. Web hiện thẻ giả và chỉ dẫn,
**không** hiện lời bot. Người thu bấm để nghe câu bot, nói, bấm khi đã nói xong. Chrome ghi file
**2 kênh**: kênh 0 micro, kênh 1 chính tín hiệu bot đã phát, cùng đồng hồ AudioContext, nên nhật ký
phát khớp từng mẫu mà không cần đo độ lệch bằng tiếng tách.

- Tắt khử vọng, lọc ồn, tự chỉnh âm lượng của Chrome; bắt buộc tai nghe có dây.
- **Thu raw, không tiền xử lý** (quyết định 2026-09-16): không cắt khoảng im, không chuẩn hoá âm
  lượng, kể cả giọng bot. Khoảng im trước khi nói là tự nhiên. Chỗ bot thật sự bắt đầu nói trong
  một câu được xác định lúc phân tích từ kênh bot, không bằng cách sửa file.
- Server từ chối file sai định dạng, nhật ký chồng nhau hoặc vượt độ dài file, ghi âm khi chưa đồng
  ý. Quy tắc nhật ký trùng `WavFrameSource`.
- Mỗi bản ghi có file `.json` đi kèm (nhật ký, thông tin trình duyệt, bản đồng ý, sha256).
- Giao diện (2026-09-16): một trang, ba bước; thanh sóng nhảy theo giọng khi ghi; người thu nghe lại
  rồi mới gửi (chưa gửi thì chưa lên server); tình huống đã gửi ẩn với người đó, gửi trùng bị từ
  chối (409), quản trị nghe và xoá được bản ghi, xoá xong tình huống hiện lại.
- Bot **không** dừng khi khách nói chen, và **không** tự cắt lời. Nhãn vẫn đúng vì ghi ý định của
  khách; mất các ca "bot cắt lời thật".

Bằng chứng (2026-09-15): 28 test API; bài e2e lái Chrome thật với micro giả 1500 Hz và giọng bot
giả 440/660 Hz, chạy cả tại chỗ lẫn trong container Docker. Kênh bot trùng file đã upload tới từng
mẫu (sai số tối đa 1), im tuyệt đối ngoài nhật ký, kênh khách không lẫn tiếng bot. Bốn buổi thu
trong container, một lần rút lại đồng ý, khởi động lại container: `tools/audit_export.py` báo 0 lỗi
(integrity, khoá ngoại, sha256 file = DB = sidecar, không file mồ côi). Đọc lại bằng `WavFrameSource`:
số khung có cờ `bot_speaking` đúng bằng số tính từ nhật ký (102/102), B1 chạy qua mọi khung.

Lỗi tìm ra khi kiểm, đã sửa kèm test: nút gọi tổng đài bấm được trong lúc đang tải giọng bot, cú
bấm bị nuốt mất; chưa có đường thực hiện quyền rút lại đồng ý và xoá (Luật 91 Điều 10, 14); header
admin có ký tự ngoài ASCII làm server trả 500 thay vì 401.

Chưa kiểm: ghi âm với micro thật và tai nghe thật — đó là buổi thử. Luật 91/2025/QH15 có quy định riêng về chuyển dữ liệu cá nhân ra nước
ngoài, chưa đọc; phải kiểm trước khi thu người khác trên server đặt ở nước ngoài.

### 6.7 ASR kiểm thử — chỉ để nghe ngược dữ liệu thu

`asr-check/`: thư mục riêng, môi trường `uv` riêng, `faster-whisper` với mô hình
`Systran/faster-whisper-small` (MIT) khoá ở revision `536b0662`, tải vào `asr-check/models/`
(gitignore). `uv run python transcribe.py <export.zip>` chép lời câu bot và kênh khách, in kèm
`avg_logprob`/`no_speech_prob`, không sửa file nào.

**Chỉ phục vụ kiểm thử dữ liệu thu.** Không phải ASR của sản phẩm, không phải B3 (`SPEC.md` R8),
không thay người gán nhãn. Chọn ASR cho các vai đó là quyết định riêng ở pha 1.6 và Giai đoạn 2.

Đã thấy trên bản ghi thật đầu tiên: tắt bộ lọc tiếng nói thì Whisper small bịa ra một câu quảng
cáo YouTube trên đoạn im lặng; bật bộ lọc (chỉ trong bộ nhớ, mốc thời gian vẫn theo file gốc) thì
hết. Với câu ngắn, nhỏ tiếng, kết quả dao động giữa các cách chạy ("ồ ồ", "à lâu quá", "alô alô")
— đó là giới hạn của mô hình nhỏ, nên kết quả chỉ dùng để gợi ý, phải nghe lại bằng tai.

### 6.8 Giọng bot và tần số thu

**Giọng bot: VieNeu-TTS v3 Turbo, preset "Minh Quân Pro", int8.** Bằng chứng giấy phép và tốc độ:
`docs/research/tts-voice.md` (Apache-2.0, audio sinh ra không bị ràng buộc thêm; các lựa chọn
tiếng Việt nổi tiếng khác đều phi thương mại). Chọn bằng tai trên 3 giọng × 3 câu. Cùng engine sẽ
dùng cho Giai đoạn 4, để bộ dữ liệu vàng đo đúng giọng của sản phẩm. Một giọng cho cả bộ dữ liệu:
hai giọng là thêm một biến mà 24–30 người không đủ để tách.

Đo trên laptop này (i5-11400H, 6 nhân, `tts-check/synth.py`), trung vị 2 lần: int8 RTF 0,33–0,55,
tiếng đầu tiên sau 168–334 ms; fp32 RTF 0,39–0,55, 212–400 ms. int8 nghe không khác fp32; khác
biệt nghe được giữa hai lần sinh chủ yếu do mô hình lấy mẫu ngẫu nhiên, nên câu nào hỏng thì sinh
lại riêng câu đó.

Quyết định và lý do:

- **Dấu `/` đổi thành dấu phẩy, không chèn khoảng lặng.** Chèn khoảng lặng giữa các đoạn nghe có
  nhịp hơn, nhưng lúc bot chạy thật không làm vậy; dữ liệu phải đo đúng thứ sẽ chạy.
- **Không giao việc đọc ngày, giờ, tiền, số thuê bao cho TTS.** VieNeu đọc "25/9" thành "hai lăm
  chín". Giai đoạn 4, `dialog/` tự viết slot thành chữ trước khi đưa cho TTS, và test bằng unit
  test. Kịch bản Giai đoạn 1 đã viết sẵn bằng chữ nên không bị ảnh hưởng.
- **Giữ watermark mặc định của VieNeu**: đánh dấu giọng AI, tai không nghe thấy. Chưa kiểm chứng
  nó không ảnh hưởng phép đo.
- **Collector thu và lưu 48 kHz thay vì 16 kHz.** Ở 16 kHz người thu nghe bot như loa điện thoại,
  tệ hơn sản phẩm thật (WebRTC phát đầy đủ), và phần trên 8 kHz của cả hai kênh mất vĩnh viễn —
  trái nguyên tắc thu raw. Giá: ~11,5 MB mỗi phút thay vì ~3,8 MB; tự host trên laptop nên chấp
  nhận. Hạ về 16 kHz là việc của bước đọc dữ liệu ở pha 1.5.

**Người thu `S001` là tác giả kịch bản** (thu từ 2026-09-22). Biết trước chỗ bot đọc sai và
dự án đo gì, nên bản ghi của `S001` chỉ vào phần dev hoặc làm bản thu thử, **không bao giờ vào
holdout**. Pha 1.5 phải áp quy tắc này khi chia tập.

`tts-check/render_prompts.py` sinh mọi câu từ `/api/admin/lines` và nạp thẳng vào collector,
ghi `tts-check/prompts/manifest.json` (giọng, phiên bản, sha256 từng câu; gitignore).

---

## 7. Giai đoạn 2 — Đo cái có sẵn: **đang làm**

### 7.1 B2 — `smart-turn` v3.2

`src/turnwise/turn/deciders/acoustic_onnx.py`, cấu hình `configs/baseline/acoustic-onnx.yaml`.
Trọng số nguyên bản, khoá revision và sha256 trong file cấu hình. Vận hành chép từ pipecat: hỏi
mô hình khi khách im 200 ms, nhận lượt khi xác suất > 0,5 hoặc khi im 3 giây. Cổng có tiếng dùng
chung với B1 thay cho Silero VAD, để hai baseline khác nhau ở đúng một chỗ.

Đặc trưng lấy từ `faster_whisper.feature_extractor` (nhóm `asr`), đối chiếu với
`transformers.WhisperFeatureExtractor` của bản gốc trên bốn đoạn thật: lệch tối đa 4,3e-6.

**Đo trên chín bản thu thử của S002, i5-11400H, chạy lại từ file, 2026-09-26:**

| | |
|---|---|
| Số lần hỏi mô hình | 64 |
| Thời gian một lần hỏi | trung vị 22,3 ms, p95 23,5 ms, tối đa 24,4 ms |
| Tỉ lệ trả "xong" | 83% |

Chưa có nhãn nên chưa biết lần nào đúng. Hai điều đã biết chắc:

- **Một lần hỏi tốn 22 ms, gấp đôi ngân sách 10 ms mỗi khung.** Trên đường chạy sống, phần nối dây
  phải đẩy lời gọi ra khỏi thread tiêu thụ, như pipecat đẩy sang executor. Chạy lại từ file thì
  không sao.
- **Tiếng bot lọt vào micro chạm cổng im lặng.** Lần chạy đầu, cả 64 lần hỏi đều rơi vào lúc bot
  đang nói: tiếng bot vọng ở −44 dBFS, vượt cổng −45 dBFS của B1 và B2, và mô hình chấm một đoạn
  gần như im lặng thành "xong" (0,985). Cổng này ảnh hưởng cả B1. Khi viết `run_system.py`, mỗi
  lượt khách bắt đầu **lúc bot dứt lời**, và khung trong lúc bot nói chỉ dùng cho phép đo nói đè.

### 7.2 Khung benchmark — 2026-09-27

Một lệnh chạy mọi decider trên bộ dữ liệu vàng, chọn bằng file cấu hình:

```bash
uv run python -m evaluation.run_system configs/baseline/silence-threshold.yaml   # B1, quét dải
uv run python -m evaluation.run_system configs/baseline/acoustic-onnx.yaml       # B2
uv run python -m evaluation.run_system configs/baseline/semantic-onnx.yaml       # B3
uv run python -m evaluation.run_system configs/proposed/draft.yaml --ablation    # hệ đề xuất
```

| Thành phần | Ở đâu | Trạng thái |
|---|---|---|
| Chấm theo từng đoạn nói đã gán nhãn | `evaluation/golden.py`, `run_system.py` | chạy được; 0 đoạn được chấm vì chưa có nhãn |
| B1 | `deciders/silence_threshold.py` | xong từ GĐ 0 |
| B2 | `deciders/acoustic_onnx.py` | xong, mô hình đã tải |
| B3 | `deciders/semantic_onnx.py` | xong, trọng số đã tải; tokenizer khớp bản gốc trên 6/6 câu |
| Hệ đề xuất | `deciders/fused.py`, `fusion.py`, `scorers/` | khung: `silence`, `smart_turn`, `final_rise`, `short_ipu`; số khởi điểm chưa hiệu chỉnh |
| Nền ồn theo khung | `audio/features.py` | xong, cổng của hệ đề xuất dùng nó |

**Cổng chung (đã quyết 2026-09-27).** Trước đó B1, B2, B3 dùng -45 dBFS cố định trong khi nền ồn
micro của S001 là -34 dBFS, nên với S001 không baseline nào thấy được im lặng. Giờ cả bốn hệ dùng
`turn/gate.py`: ngưỡng = max(-45, nền ồn + 12 dB). Đường cong B1 trên kịch bản GĐ 0 không đổi.

**B3 đo trên 18 bản thu thử, i5-11400H, chạy từ file (2026-09-27):** một lần hỏi (faster-whisper
small, beam 5, rồi Namo) mất trung vị **1 750 ms**, lâu nhất 35 882 ms. Gần như toàn bộ là ASR. B2
cùng việc đó mất 22 ms. Đọc chữ đắt hơn nghe âm thanh gần 80 lần trên máy này.

Namo chấm các câu trả lời ngắn trọn vẹn là **chưa xong**: "Sáng mai." 0,001, "dạ" 0,000, "Cho tôi
gặp nhân viên luôn đi" 0,000 (cùng kết quả với tokenizer gốc của transformers). Nếu nhãn xác nhận,
B3 sẽ hỏng đúng ở hành vi "trả lời ngắn" của SPEC §4.3.

### 7.3 Đường chạy sống (GĐ 4) — khung đã nối, 2026-09-27

`uv run turnwise dev [--config ...]` chạy một cuộc gọi trên micro và loa của máy, với decider mà
file cấu hình chọn (mặc định hệ đề xuất).

| Tầng | File | Ghi chú |
|---|---|---|
| audio | `ring_buffer.py`, `capture.py`, `aec.py`, `source.py` (`LiveFrameSource`, `LiveAudio`) | AEC 0,10 ms mỗi khung 10 ms, ngân sách 5 ms |
| dialog | `slots.py`, `templates.py`, `backend_stub.py`, `machine.py` | năm luồng, mọi quy tắc §4.2 có test |
| transport | `speech.py`, `wiring.py` | ASR, dialog, TTS chạy ở luồng phụ |
| telemetry | `dashboard.py` | bảng trong terminal, vẽ lại năm lần mỗi giây |

**Chưa thử với micro thật.** Mọi test dùng đồ giả; chưa có ai gọi vào.

**Độ trễ đáp đo được là khoảng 4 giây — nối đúng, nhưng chưa dùng được.** Lần gọi đầu, không phát
theo luồng: TTS 2,38 s để sinh câu chào dài 2,96 s; ASR (whisper-small, beam 5) 1,98 s cho cùng câu,
và chép "Tổng đài NetCo" thành "Tổng đại nét con". Câu cố định giờ được nhớ sau lần sinh đầu. Việc
kế tiếp về độ trễ: phát TTS theo luồng (TTFA đo ở §6.8 là 168–334 ms), và ASR nhanh hơn — beam
nhỏ, mô hình nhỏ hơn, hoặc một mô hình CTC chạy theo luồng (ADR-0006 mục 5).

**Cố ý để rỗng:** `transport/webrtc.py` (cắt theo `docs/roadmap.md` §8, dùng micro và loa tại
máy); `scripts/collect_session.py` (web thu `collector/` đã thay); `training/` (chưa có lý do đo được
để huấn luyện, `docs/progress.md` §6.1).
