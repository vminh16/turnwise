# Nhật ký triển khai

Tài liệu này trả lời ba câu: **đã làm gì**, **đang ở đâu**, **kết quả ra sao**. Nó không
thay `SPEC.md` (bài toán) hay `docs/roadmap.md` (thứ tự và lý do); khi mâu thuẫn thì hai
tài liệu kia đúng.

Quyết định kỹ thuật ghi thẳng ở đây thay vì tách thành ADR riêng, để một người mới đọc
một file là nắm được trạng thái. ADR dành cho quyết định kiến trúc lớn của các giai đoạn
sau.

Cập nhật lần cuối: 2026-09-12. Nhánh `feat/repo-setup`.

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
| 0.7 Ngân sách | `tests/latency/test_budget.py` | `b673a3a` | `-m latency` 3 |
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
- `tests/conftest.py` còn rỗng; ba nơi tự sinh wav riêng.
- Cổng `-m latency` có độ dư khoảng 1400 lần: một hồi quy 1000 lần vẫn xanh.

---

## 5. Còn thiếu so với một sản phẩm

Giai đoạn 0 chỉ là đường đo. Theo `SPEC.md` §9.1, bốn trong sáu chỉ số đã đo được (trên
tín hiệu giả); ba chỉ số còn lại cần hệ chạy sống: thời gian từ lúc khách nói đè tới lúc
bot im, tỉ lệ bot nhận nhầm tiếng của chính mình, và chênh lệch lỗi theo thanh điệu. Toàn
bộ §9.2 — thời gian hoàn tất luồng, tỉ lệ không phải chuyển người, số lần khách lặp lại —
chưa có gì vì `dialog/` còn rỗng.

Hai quyết định còn treo, cả hai cỡ một ADR:

- **`praat-parselmouth` là GPLv3 và nằm trong `[project] dependencies`**, tức đường chạy
  chính, trong khi `LICENSE` của repo đang rỗng 0 byte. Chốt trước Giai đoạn 3.
- **Giọng TTS tiếng Việt** chưa có nguồn chính thức: `rhasspy/piper-voices` không có mục
  `vi`, và `piper-tts` trên PyPI đã chuyển sang GPL-3.0-or-later. Chốt trước Giai đoạn 4.

---

## 6. Tiếp theo

**Giai đoạn 1 — Dữ liệu đóng vai.** Đường găng của cả dự án, tốn thời gian thật chứ không
tốn code: kịch bản đóng vai cho năm luồng, thu hai kênh có đồng ý, gán nhãn, manifest kèm
sha256, chia tập **theo người nói**, khoá holdout.

Bằng chứng nền cho các giai đoạn sau — mô hình nào kế thừa được, giấy phép ra sao, chỗ
nào tài liệu repo đang sai — nằm ở `docs/research/reuse-audit.md`.
