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

Hai quyết định còn treo, cả hai cỡ một ADR:

- **`praat-parselmouth` là GPLv3 và nằm trong `[project] dependencies`**, tức đường chạy
  chính, trong khi `LICENSE` của repo đang rỗng 0 byte. Chốt trước Giai đoạn 3.
- **Giọng TTS tiếng Việt** chưa có nguồn chính thức: `rhasspy/piper-voices` không có mục
  `vi`, và `piper-tts` trên PyPI đã chuyển sang GPL-3.0-or-later. Chốt trước Giai đoạn 4.

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
| 1.2 Hướng dẫn gán nhãn + đồng ý | `docs/annotation-guide.md` | chưa |
| 1.3 Đọc được hai kênh | `FeatureFrame`/`WavFrameSource` nhận micro + tiếng bot | chưa |
| 1.4 Công cụ thu + buổi thử | `scripts/collect_session.py`, độ lệch phát–thu đo được | chưa |
| 1.5 Manifest, chia tập, khoá holdout | `scripts/validate_manifests.py`, chia theo người nói | chưa |
| 1.6 Quy trình gán nhãn | nhãn tự động + nhãn người, đo độ đồng thuận | chưa |
| 1.7 Thu thật, đóng giai đoạn | điều kiện xong của `roadmap.md` §6 | chưa |

Việc đã biết trước cho 1.5: `scripts/check_holdout_isolation.py` chặn mọi file trong
`scripts/` có chữ `holdout`, nên bước khoá holdout không thể là một script trong `scripts/`.
Không giải bằng cách nới script chặn.

### 6.3 Pha 1.1 — kịch bản đóng vai

Chín kịch bản cho năm luồng, 46 lượt bot, cộng `roleplay/common.yaml` với các câu dùng
chung khi buổi thu lệch kịch bản. `uv run pytest tests/unit/test_roleplay_scripts.py`: 26
test.

| Kiểm tra | Kết quả |
|---|---|
| Mỗi luồng N1–N5 có kịch bản | đủ năm |
| Mỗi hành vi có ở ít nhất hai luồng | ngập ngừng, tiếng đệm, câu dài: 4 luồng; ngắt lời: 3; gặp nhân viên: 3; câu ngắn: 5 |
| Gặp nhân viên giữa lúc bot đang đọc, ngoài N5 | có ở N2 và N4 |
| Gợi ý câu trả lời ngắn phủ sáu thanh ở âm tiết cuối | ngang 17, sắc 16, nặng 11, huyền 7, hỏi 6, ngã 3 |

Đã thử phá: bỏ ba câu gợi ý kết thúc bằng thanh ngã thì kiểm tra độ phủ thanh báo thiếu.

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

Giới hạn: nội dung kịch bản chưa được người bản ngữ ngoài nhóm đọc thử. Độ phủ thanh điệu
ở đây là của **gợi ý**; thanh thật của lời khách chỉ biết sau khi gán nhãn ở 1.6.
Tiếng ồn nền (`SPEC.md` §4.3) và bot tự nghe tiếng mình (R5) là điều kiện của buổi thu,
không phải nội dung kịch bản, nên thuộc 1.4.
