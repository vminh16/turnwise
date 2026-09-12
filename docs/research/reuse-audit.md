# Rà soát khả năng kế thừa, và cách chia nhỏ Giai đoạn 0

Tài liệu này là **bằng chứng, không phải quyết định**. Nó trả lời đúng một câu hỏi: *cái gì
đã có sẵn ngoài kia mà Turnwise không phải viết lại?* Quyết định chọn cái nào thuộc về
`docs/adr/`; ở đây chỉ có nguồn, giấy phép, hợp đồng đầu vào, và một phán quyết dùng-hay-không
kèm lý do.

Thứ tự ưu tiên khi đọc: `SPEC.md` đúng hơn tài liệu này; `docs/roadmap.md` và `docs/adr/` đúng
hơn mọi thứ tra được trên mạng. Chỗ nào bằng chứng ngoài mạng **mâu thuẫn** với tài liệu trong
repo thì §3 nói rõ, và việc sửa tài liệu nào là một ADR chứ không phải một lần sửa chữ.

---

## 1. Nguồn và ngày tra cứu

**Mọi con số dưới đây tra ngày 2026-09-10.** Phiên bản mô hình và bảng benchmark của cả hai
endpointer mã nguồn mở đều đang chuyển động — `smart-turn` đã đi từ v3.0 tới v3.2 trong vòng
chín tháng — nên số ở đây có hạn sử dụng. Tra lại trước khi trích vào báo cáo cuối.

Nguyên tắc thu thập: **chỉ nguồn gốc**. Cụ thể là README trong chính repo, file `LICENSE`,
`config.json`, file benchmark do tác giả sinh ra, metadata của Hugging Face Hub API, metadata
`.dist-info` của gói đã cài trong `.venv`, và mã nguồn. Không lấy từ bài tóm tắt, bài blog hay
bảng so sánh của bên thứ ba. Chỗ nào không kiểm chứng được thì ghi vào §9 chứ không đoán.

Hai kết luận dưới đây kiểm chứng **bằng cách chạy thật trên máy này**, không phải bằng cách đọc
tài liệu:

- `aec_audio_processing.AudioProcessor(...).get_frame_size()` trả về `160` ở 16 kHz — đúng như
  `configs/default.yaml` khẳng định — và `vad_enabled()` trả về `True`, `has_voice()` gọi được
  sau mỗi lần `process_stream()`.
- Sáu thanh điệu tiếng Việt tách được khỏi chữ viết chỉ bằng `unicodedata.normalize("NFD", …)`
  của thư viện chuẩn: `da → LEVEL`, `dà → FALLING`, `dá → RISING`, `dả → DIPPING`,
  `dã → BROKEN`, `dạ → DROP`, và dấu mũ trong `đấy` không gây nhiễu.

Ngoài lề nhưng đáng ghi: lần chạy thử đầu tiên của đoạn mã trên **đã chết đúng bằng lỗi mà
`AGENTS.md` mô tả** — `UnicodeEncodeError: 'charmap' codec ... cp1258`. Cạm bẫy đó là thật, và
`agent.py::force_utf8_stdio` không phải đề phòng thừa.

---

## 2. Hiện trạng repo — cái gì đã thật sự tồn tại

Đếm bằng `wc -l` trên toàn bộ `src/`, `evaluation/`, `scenarios/`, `tests/`, `training/`,
`configs/`. Toàn repo có **682 dòng**, và phần lớn là hợp đồng chứ không phải hành vi.

| File | Dòng | Nội dung |
|---|---|---|
| `src/turnwise/types.py` | 148 | `TurnOutcome`, `Tone` (6 thanh + `UNKNOWN`), `FeatureFrame`, `TurnDecision` |
| `src/turnwise/turn/base.py` | 111 | `Prediction`, `Scorer`, `TurnDecider` — hai `Protocol` |
| `src/turnwise/agent.py` | 77 | CLI `turnwise dev`, `force_utf8_stdio()`; `run_dev()` trả về lỗi có chủ ý |
| `configs/default.yaml` | 78 | audio, AEC, latency, turn, telemetry; `take_threshold`/`backchannel_threshold` để `null` |
| `configs/baseline/silence-threshold.yaml` | 19 | dải quét 11 giá trị 200–1200ms |
| `tests/unit/*.py` | 219 | 5 file: types, turn_base, configs, agent_cli, packaging |

**Rỗng hoàn toàn (0 byte):** toàn bộ `src/turnwise/audio/`, `src/turnwise/dialog/`,
`src/turnwise/telemetry/`, `src/turnwise/transport/`, `src/turnwise/turn/deciders/`,
`src/turnwise/turn/scorers/`, `src/turnwise/turn/fusion.py`, `src/turnwise/config.py`, cả bốn
file trong `evaluation/`, cả ba file trong `training/`, `tests/conftest.py`,
`docs/annotation-guide.md`, cả hai file `docs/runbook/`, `Dockerfile`, `LICENSE`.

`scenarios/` chỉ có `.gitkeep`. `tests/latency/`, `tests/scenarios/`, `tests/integration/`,
`tests/fixtures/` cũng vậy — nghĩa là hai marker `latency` và `scenario` đã khai báo trong
`pyproject.toml` hiện **không thu được test nào**.

Đọc thẳng ra: repo đang có **từ vựng và hợp đồng, chưa có đường ống**. Đó đúng là trạng thái mà
GĐ 0 tồn tại để thay đổi.

> Ảnh chụp này lấy lúc 13:00 ngày 2026-09-10, trên nhánh `feat/repo-setup`. Cây thư mục đang
> chuyển động: tới 13:29 cùng ngày đã có `src/turnwise/config.py` và `tests/unit/test_config.py`
> xuất hiện — tức **pha 0.1 ở §7 đang được làm dở**. Bảng ở §8 phân loại theo *hạng mục*, không
> theo số dòng, nên nó không hỏng vì chuyện đó; nhưng đừng trích số dòng ở bảng trên như số hiện
> tại. Chạy lại `wc -l` trước khi dùng.

---

## 3. Ba chỗ bằng chứng mâu thuẫn với tài liệu trong repo

Đặt lên đầu vì đây là phần có sức nặng nhất, và vì cả ba đều làm thay đổi chi phí của GĐ 2.

### 3.1 `smart-turn` **đã** công bố số liệu riêng cho tiếng Việt — và tiếng Việt xếp bét

`docs/roadmap.md` §3 viết: *"Cả hai mô hình có sẵn đều không công bố dữ liệu tiếng Việt của họ
và không tách số liệu riêng cho tiếng Việt."* ADR-0002 nói tương tự.

**Với `smart-turn`, câu đó không còn đúng.** Repo mô hình chứa năm file benchmark do chính tác
giả sinh ra, trong đó `benchmarks/smart-turn-v3.2-cpu.md` (sinh ngày 2026-01-07 từ
`/data/smart-turn-v3.2-cpu.onnx`) có bảng tách theo từng ngôn ngữ với Accuracy, Precision,
Recall, F1, FPR và FNR.

Nguồn: <https://huggingface.co/pipecat-ai/smart-turn-v3/blob/main/benchmarks/smart-turn-v3.2-cpu.md>

Tổng thể: **92,63%** trên 31.527 mẫu, 23 ngôn ngữ, 12 bộ dữ liệu (Precision 0,909; Recall 0,947;
F1 0,927).

Dòng tiếng Việt:

| Ngôn ngữ | Mẫu | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|
| Vietnamese | 1.004 | **79,38%** | 0,811 | 0,764 | 0,786 | 8,86% | 11,75% |

Xếp hạng đầy đủ 23 ngôn ngữ theo accuracy: Korean 96,96 · Turkish 96,79 · German 96,37 ·
Japanese 96,16 · Dutch 95,92 · Polish 95,38 · Indonesian 95,16 · Italian 94,50 · Portuguese
94,49 · English 94,26 · Ukrainian 94,19 · Finnish 94,16 · French 94,09 · Russian 93,53 · Danish
92,81 · Norwegian 91,81 · Hindi 90,11 · Arabic 89,76 · Spanish 89,57 · Chinese 85,79 · Bengali
83,80 · Marathi 82,43 · **Vietnamese 79,38**.

**Tiếng Việt đứng cuối cùng trong 23 ngôn ngữ, thấp hơn mức trung bình 13,25 điểm.** Ngôn ngữ
thanh điệu còn lại trong danh sách — tiếng Trung — đứng thứ 20 với 85,79%.

Điều này không làm hỏng đề tài. Nó làm ba việc, và cả ba đều có lợi:

1. **Củng cố tiền đề.** Giả thuyết "ngôn ngữ thanh điệu khác" ở `SPEC.md` §7 giờ có một quan sát
   độc lập đứng sau, do chính tác giả mô hình công bố, không phải do nhóm tự nói.
2. **Không thay thế được phép đo của nhóm.** Con số 79,38% đo trên dữ liệu của họ, phân bố của
   họ, định nghĩa nhãn của họ — không phải trên năm luồng nghiệp vụ NetCo, không phải trên hội
   thoại đóng vai có ngập ngừng và tiếng đệm. Quy tắc ở `SPEC.md` §9.3 và câu chốt cuối
   `SPEC.md` vẫn giữ nguyên: **số baseline phải do nhóm tự đo.**
3. **Đóng góp còn trống vẫn còn trống.** Bảng của họ tách theo *ngôn ngữ*; chỉ số chính ở
   `SPEC.md` §9.1 tách theo *thanh điệu của âm tiết cuối*. Không nguồn nào có bảng đó. Điểm 1
   trong bốn điểm của ADR-0002 **không** bị bằng chứng này chạm tới.

Thêm một chi tiết cần sửa: dữ liệu huấn luyện của `smart-turn` **có** công bố, dưới dạng bộ dữ
liệu công khai `pipecat-ai/smart-turn-data-v3.1-train` (270.429 mẫu, ~38,5 GB, 77 shard parquet)
với schema có cả trường `language` lẫn trường `synthetic`
(<https://huggingface.co/datasets/pipecat-ai/smart-turn-data-v3.1-train>). Cái *chưa* biết là
**tỉ lệ tiếng Việt trong đó là bao nhiêu và bao nhiêu phần là tổng hợp** — xem §9.

### 3.2 NAMO: model card tiếng Việt **có** số, và kiến trúc ghi trong ADR-0002 sai

ADR-0002 mô tả B3 là *"mmBERT + classifier trên văn bản ASR"*. Kiểm tra `config.json` của chính
model tiếng Việt: `"model_type": "distilbert"`,
`"architectures": ["DistilBertForSequenceClassification"]`, 6 lớp, 12 đầu, `dim` 768,
`vocab_size` 119547, `max_position_embeddings` 512.

Nguồn: <https://huggingface.co/videosdk-live/Namo-Turn-Detector-v1-Vietnamese/blob/main/config.json>

Đối chiếu toàn bộ họ model qua Hub API: **chỉ bản `Namo-Turn-Detector-v1-Multilingual` dùng
`jhu-clsp/mmBERT-base`**; 23 model đơn ngữ còn lại — trong đó có bản tiếng Việt — đều là
`distilbert-base-multilingual-cased`. ADR-0002 gộp hai thứ làm một.

Về số liệu: ADR-0002 nói đúng rằng `RESEARCH.md` trên GitHub chỉ liệt kê Turkish 97,3 · Korean
96,8 · Japanese 94,3 · Hindi 93,9 · German 94,2 và một con số trung bình 90,25% trên 23 ngôn ngữ,
**không có tiếng Việt**
(<https://github.com/videosdk-live/NAMO-Turn-Detector-v1/blob/main/RESEARCH.md>). Nhưng **model
card của chính bản tiếng Việt thì có**: Accuracy 82,37%, F1 83,44%, Precision 78,24%, Recall
89,37%, trên "1000+ Vietnamese utterances"
(<https://huggingface.co/videosdk-live/Namo-Turn-Detector-v1-Vietnamese>).

Cần nói rõ giới hạn của con số đó: tập test không công khai kiểm tra được, và bộ dữ liệu huấn
luyện `videosdk-live/Namo-Turn-Detector-v1-Train` **trả về HTTP 401 khi truy cập qua Hub API vào
ngày 2026-09-10** — nghĩa là phần công bố dữ liệu của NAMO vẫn đóng, đúng như ADR-0002 nói. Chỉ
riêng câu "không tách số liệu riêng cho tiếng Việt" là cần sửa.

### 3.3 `piper-tts` **không** có giọng vi_VN chính thức, và nó là GPL-3.0

`pyproject.toml` ghi chú bên cạnh `piper-tts>=1.2`: `# local ONNX VITS, has a vi_VN voice`.

Danh mục giọng chính thức `rhasspy/piper-voices/voices.json` **không có mục nào cho `vi_VN` hay
mã ngôn ngữ `vi`** (<https://huggingface.co/rhasspy/piper-voices/blob/main/voices.json>). Tìm
trên Hub chỉ ra hai giọng tiếng Việt do cộng đồng tự huấn luyện (`hungmd321/piper1_vietnamese`,
Apache-2.0; `vongocanhthi/acut-piper-vietnamese`, licence "other"), cả hai **0 lượt tải**, không
có model card mô tả nguồn dữ liệu.

Đồng thời, gói `piper-tts` trên PyPI hiện ở phiên bản 1.8.0, trỏ về
`github.com/OHF-voice/piper1-gpl`, và licence là **GPL-3.0-or-later**
(<https://pypi.org/pypi/piper-tts/json>) — không phải MIT như phần lớn người dùng vẫn tưởng.

Hệ quả: dòng bình luận trong `pyproject.toml` cần sửa, và **TTS tiếng Việt là một rủi ro chưa
đóng của GĐ 4**, không phải một việc đã xong. Nó không chặn GĐ 0.

### 3.4 Ba chỗ bằng chứng **xác nhận** roadmap

Để cân bằng, ba khẳng định sau tra lại và **đúng**:

- *"Không có corpus hội thoại hai kênh tiếng Việt công khai"* (§5) — **xác nhận.** Chi tiết ở §5.
- *"VIVOS, VLSP, BUD500 đều đơn kênh"* (§5) — **xác nhận**, kèm một chi tiết roadmap chưa nói:
  cả VIVOS lẫn BUD500 đều là **CC-BY-NC-SA-4.0**, tức phi thương mại và có điều khoản lây lan.
- *"LiveKit turn-detector: không hỗ trợ tiếng Việt, plugin đã bị đánh dấu deprecated"*
  (ADR-0002) — **xác nhận**, và còn nặng hơn thế: giấy phép trọng số cấm dùng ngoài LiveKit
  Agents. Chi tiết ở §4.

Một chỗ **nới lỏng** được: roadmap §5 viết *"Nếu chọn hướng VAP thì bắt buộc tự thu"* dựa trên
ràng buộc hai kênh. `MaAI-Kyoto/MaAI` nay có **model VAP đơn kênh** huấn luyện riêng cho đầu vào
một kênh. Điều đó không xoá nhu cầu dữ liệu tiếng Việt — MaAI chỉ có trọng số Anh/Trung/Nhật —
nhưng nó gỡ ràng buộc *hai kênh* ra khỏi phía suy luận. Câu ở roadmap nên đọc là "bắt buộc tự
thu **dữ liệu tiếng Việt**", không phải "bắt buộc tự thu **hai kênh**".

---

## 4. Bảng phán quyết kế thừa

Ba mức phán quyết:

- **Kế thừa làm phụ thuộc** — dùng trực tiếp, giấy phép cho phép, hợp đồng đầu vào khớp.
- **Kế thừa hình dạng** — đọc mã của họ để lấy ý, tự viết lại. Thường vì hợp đồng lệch, hoặc vì
  phần dùng được quá nhỏ so với chi phí một phụ thuộc.
- **Không dùng được** — kèm lý do.

Ký hiệu ⚠ nghĩa là **cần bạn phê duyệt trước khi thêm**, theo `AGENTS.md` mục Off-Limits: *"Do
not add dependencies without asking."* Ký hiệu ⛔ là xung đột giấy phép cần một quyết định.

| Ứng viên | Giấy phép (đọc từ file) | Cho gì | CPU laptop? | Tiếng Việt? | Hợp đồng vào | Phán quyết |
|---|---|---|---|---|---|---|
| `pipecat-ai/smart-turn` v3.2 (`smart-turn-v3.2-cpu.onnx`) | BSD-2-Clause, © Daily 2024–2025 | Trọng số B2: Whisper-Tiny encoder + head tuyến tính, ~8M tham số | Có — 8 MB int8 / 32 MB fp32; tác giả nói 10ms trên vài CPU, <100ms trên đa số | Có, 1/23 ngôn ngữ; 79,38% acc | 16 kHz **mono**, ≤ **8 giây**, `WhisperFeatureExtractor(chunk_length=8)`, ONNX input `input_features`, ngưỡng 0,5 | **Kế thừa làm phụ thuộc** (trọng số; chạy qua `onnxruntime` đã khai báo) |
| `pipecat-ai/pipecat` — `audio/turn/smart_turn/base_smart_turn.py` | BSD-2-Clause | Hình dạng bộ phân tích lượt: `append_audio(buffer, is_speech)`, `analyze_end_of_turn()`, `stop_secs`, `pre_speech_ms`, `max_duration_secs` | — | — | Cần một VAD bên ngoài cấp cờ `is_speech` | **Kế thừa hình dạng** — xem §4.1 |
| `Namo-Turn-Detector-v1-Vietnamese` | Apache-2.0 | Trọng số B3: DistilBERT đa ngữ + phân loại nhị phân trên văn bản ASR; `model.onnx` + `model_quant.onnx` | Có — ~135 MB, tác giả nói <13ms | Có, model riêng; 82,37% acc | Văn bản, `max_length=512` token, **cần tokenizer WordPiece** (`tokenizer.json`, `vocab.txt`) | **Kế thừa làm phụ thuộc** ⚠ — tokenizer là phụ thuộc mới |
| LiveKit `turn-detector` | Mã: Apache-2.0. **Trọng số: LiveKit Model License** | Endpointer ngữ nghĩa (Qwen2.5-0.5B) | Có, <500 MB RAM | **Không** — 14 ngôn ngữ, không có `vi` | — | **Không dùng được** ⛔ — plugin đã deprecated; giấy phép cấm dùng "on a standalone basis or with any frameworks other than LiveKit Agents" |
| `snakers4/silero-vad` | MIT | VAD chất lượng cao, ONNX, ~2 MB | Có, <1ms/chunk | Không tuyên bố riêng | 8k/16k Hz, **đúng 512 mẫu** ở 16 kHz (`ValueError: Provided number of samples is X`) | **Kế thừa hình dạng** ⚠ — xem §4.2; 512 mẫu không chia hết cho khung 160 mẫu của repo |
| `wiseman/py-webrtcvad` | MIT | VAD WebRTC | Có | — | 8/16/32 kHz, khung 10/20/30ms, PCM16 mono | **Không cần** — cùng thuật toán đã có sẵn trong `aec-audio-processing`; bản PyPI mới nhất 2.0.10 phát hành **07/01/2017** |
| `aec-audio-processing` **(đã khai báo)** | BSD-3-Clause | AEC + NS + AGC **+ VAD**: `enable_vad`, `set_vad_aggressiveness()`, `has_voice()`, `get_frame_size() → 160` | Có, đã cài, có wheel Windows | Không phụ thuộc ngôn ngữ | 16 kHz mono, **đúng 160 mẫu/lần** = 10ms | **Kế thừa làm phụ thuộc** — và nó giải quyết luôn nhu cầu VAD của B1 |
| `ErikEkstedt/VoiceActivityProjection` | MIT | Kiến trúc VAP gốc, một checkpoint mẫu | Chưa rõ — hướng dẫn cài trỏ `cudatoolkit=11.6`; cập nhật lần cuối 29/05/2024 | Không | **Stereo 16 kHz**; huấn luyện cần `waveform (B,2,n)` + `vad (B, n_frames+horizon, 2)` ở 50 Hz, cửa sổ 20s, chân trời 2s | **Kế thừa hình dạng** — định dạng nhãn là thứ đáng chép; dữ liệu huấn luyện của họ (Switchboard/Fisher/Candor) không công khai |
| `MaAI-Kyoto/MaAI` | MIT (mã); trọng số theo từng model, encoder Mimi là CC BY 4.0 | VAP thời gian thực + backchannel + nodding; **có model VAP đơn kênh** | Có — "operates efficiently, even exclusively on CPU" | **Không** — Anh, Trung, Nhật | `pip install maai` | **Kế thừa hình dạng** ⚠ — ứng viên cho hướng §7 ở GĐ 3, không phải baseline (không có trọng số tiếng Việt ⇒ so sánh không công bằng) |
| `faster-whisper` (extra `asr`, đã khai báo) | MIT | ASR cho B3 và cho tầng `dialog` | Có, CTranslate2, không cần torch | Whisper có `vi`; PhoWhisper cho chất lượng tiếng Việt cao hơn | 16 kHz mono | **Kế thừa làm phụ thuộc** |
| `vinai/PhoWhisper` (+ bản CTranslate2 cộng đồng) | BSD-3-Clause (bản gốc VinAI) | ASR chuyên tiếng Việt | Có, qua CTranslate2 | Có | 16 kHz mono | **Kế thừa làm phụ thuộc** — nhưng bản CT2 là do cộng đồng chuyển, lượt tải hai chữ số; phải khoá bằng sha256 trong `data/manifests/` |
| `piper-tts` (extra `tts`, đã khai báo) | **GPL-3.0-or-later** | TTS cục bộ ONNX | Có | **Không có giọng vi_VN chính thức** | — | **Rủi ro chưa đóng** ⛔ — xem §3.3 và §9 |
| `praat-parselmouth` **(đã khai báo, runtime)** | **GPLv3** (`.dist-info` ghi `GPLv3`; `Classifier: GNU General Public License v3 or later`) | F0 và phân tích thanh điệu — tín hiệu nghiên cứu lõi | Có | Không phụ thuộc ngôn ngữ | Mảng mẫu + sample rate | **Kế thừa làm phụ thuộc** ⛔ — copyleft trên đường chạy chính; xem §7 |
| `onnxruntime`, `sounddevice`, `soundfile` (đã khai báo) | MIT, MIT, BSD-3-Clause | Chạy ONNX; PortAudio; đọc/ghi wav | Có | — | — | **Kế thừa làm phụ thuộc** |
| VIVOS (`AILAB-VNUHCM/vivos`) | **CC-BY-NC-SA-4.0** | ~15 giờ, 65 người nói, 16 kHz | — | Có | **Đọc câu rời trong phòng yên tĩnh** — không phải hội thoại | **Không dùng được cho `turn`** — không có lượt nói, không có chồng lấn |
| BUD500 (`linhtran92/viet_bud500`) | **CC-BY-NC-SA-4.0** | ~500 giờ podcast/sách/du lịch, 3 miền | — | Có | Đơn kênh, cắt thành phát ngôn | **Không dùng được cho `turn`** — không giữ ranh giới lượt |
| VietSuperSpeech (arXiv 2603.01894) | Chưa nêu trong abstract | 267,39 giờ, 52.023 cặp audio–text | — | Có | **Mono 16 kHz**, cắt 3–30 giây, nguồn YouTube độc thoại/vlog; không có nhãn turn-taking, chồng lấn hay diarization | **Không dùng được cho `turn`** — và nó là bằng chứng mạnh nhất xác nhận roadmap §5 |
| Common Voice `vi` | CC-0 | Câu đọc | — | Có | Đơn kênh, câu rời | **Không dùng được cho `turn`**; ngoài ra từ 10/2025 truy cập chuyển sang Mozilla Data Collective |
| Nexdata 500h VN Conversational, DataoceanAI Vietnamese Conversational (213h) | Thương mại, phải mua | Hội thoại tiếng Việt thật | — | Có | Không công bố | **Không dùng được** — không công khai, và `SPEC.md` §6 chỉ cho phép hội thoại đóng vai có đồng ý |

### 4.1 Vì sao B2 là "kế thừa hình dạng" ở phía adapter, dù trọng số thì kế thừa thẳng

Đọc `base_smart_turn.py` của pipecat lộ ra một điều mà model card không nói:
**`smart-turn` không phải mô hình chấm điểm theo khung.** Nó là bộ phân loại một *đoạn*, được
kích hoạt khi một VAD bên ngoài báo im lặng. Vòng đời của nó là: đệm audio theo `pre_speech_ms`,
đếm im lặng, tới `stop_secs` thì cắt một đoạn ≤ `max_duration_secs` và chạy `_predict_endpoint()`
một lần, trên `ThreadPoolExecutor`.

Hợp đồng của Turnwise thì ngược lại: `TurnDecider.decide(frame) -> TurnDecision` phải trả về ở
**mọi** khung (ADR-0004 quyết định 3, và `base.py` nói rõ lý do).

Hai thứ đó không xung khắc, nhưng chúng bắt `acoustic_onnx.py` phải làm một việc cụ thể: tự giữ
vòng đệm và bộ đếm im lặng bên trong, trả `HOLD` ở phần lớn khung, và chỉ chạy ONNX ở các khung
ứng viên. Đó là lý do phán quyết tách đôi — **trọng số kế thừa thẳng, adapter tự viết** — và là
lý do `latency.budget_per_frame_ms: 5.0` cần đọc là ngân sách *trung bình*, không phải ngân sách
*đỉnh*: khung nào chạy ONNX sẽ vượt xa 5ms. Chuyện đó thuộc GĐ 2, nhưng phải biết từ bây giờ.

### 4.2 Vì sao **không** thêm `silero-vad`

B1 cần một bộ dò tiếng nói/im lặng. Ba lựa chọn, và lựa chọn rẻ nhất đã nằm sẵn trong repo:

| | Khung yêu cầu | Khớp `capture_frame_ms: 10`? | Phụ thuộc mới? |
|---|---|---|---|
| `aec_audio_processing.has_voice()` | 160 mẫu = 10ms (đã kiểm chứng) | **Khớp chính xác** | **Không** — đã khai báo |
| `py-webrtcvad` | 10/20/30ms | Khớp | Có ⚠ (và bản mới nhất từ 2017) |
| `silero-vad` | **đúng 512 mẫu** = 32ms | **Không** — 512 / 160 = 3,2 | Có ⚠ |

`silero-vad` chính xác hơn trong tiếng ồn, và điều đó có thể quan trọng với `SPEC.md` §4.3 mục
"tiếng ồn nền". Nhưng nó đòi một tầng đệm lại riêng chỉ để khớp 512 mẫu, và nó là một phụ thuộc
mới. **Đề nghị: GĐ 0 dùng `has_voice()` của gói AEC.** Nếu GĐ 2 cho thấy VAD là chỗ hỏng chính,
lúc đó mới xin phê duyệt `silero-vad`, với số đo đứng sau yêu cầu — đúng tinh thần "thích ứng
cái đã có trước" của ADR-0005.

Một hệ quả phụ đáng giá: dùng VAD của gói AEC nghĩa là **cùng một `AudioProcessor` vừa khử vọng
vừa dò tiếng nói, trên cùng khung 160 mẫu, trong cùng một lần gọi**. Không có chỗ để hai đường
lệch pha nhau — mà lệch pha giữa AEC và VAD chính là loại lỗi làm `SPEC.md` R5 hỏng âm thầm.

### 4.3 Vì sao gán nhãn thanh điệu **không** cần thư viện

Chỉ số chính ở `SPEC.md` §9.1 cần `TurnDecision.final_tone`. Chính tả tiếng Việt ghi thanh điệu
tường minh bằng dấu, nên với văn bản từ ASR, thanh điệu suy ra được **bằng thư viện chuẩn**:
chuẩn hoá NFD rồi tra năm dấu thanh kết hợp (U+0300 huyền, U+0301 sắc, U+0309 hỏi, U+0303 ngã,
U+0323 nặng); không dấu nào trong năm dấu đó thì là thanh ngang. Dấu mũ và dấu móc (U+0302,
U+0306, U+031B) là dấu chất lượng nguyên âm, phải bỏ qua — đã kiểm chứng ở §1.

Nghĩa là **không cần `underthesea`, `viphoneme` hay bất kỳ bộ NLP tiếng Việt nào** cho chỉ số
chính. Ba giới hạn phải ghi vào tài liệu, không được lờ đi:

1. Chỉ đúng khi có **văn bản**. Không có ASR thì `final_tone` phải là `None`, không phải đoán.
2. ASR sai chữ thì sai thanh. `Tone.UNKNOWN` tồn tại đúng cho chỗ này.
3. Đây là thanh điệu *chính tả*, không phải thanh điệu *thực hiện*. Hà & Grice (dẫn trong
   ADR-0002) cho thấy ở vị trí nhường lượt, ngữ điệu ghi đè lên thanh điệu từ vựng — nên hai
   thứ có thể lệch nhau, và chính chỗ lệch đó là thứ đề tài muốn đo. Đừng để nhãn chính tả bị
   hiểu nhầm thành mô tả đường F0 thật.

---

## 5. Về khẳng định "không có corpus hội thoại hai kênh tiếng Việt công khai"

Roadmap §5 nêu đây là *"ràng buộc thật, không phải một lựa chọn còn để ngỏ"*. Tra lại từ nguồn
gốc: **khẳng định đó đứng vững.**

Đã kiểm tra và loại từng cái:

- **VIVOS** — đọc câu rời, phòng yên tĩnh, 65 người nói. Không có lượt nói.
- **BUD500** — 500 giờ từ podcast, sách nói, nội dung du lịch/ẩm thực; cắt thành phát ngôn cho
  ASR. Không giữ ranh giới lượt, không có kênh riêng cho từng người.
- **Common Voice `vi`** — câu đọc, đơn kênh.
- **VLSP** — khoảng 250 giờ, phần công khai ~100 giờ (≈20 giờ đọc + ≈80 giờ tự phát). Vẫn là
  ASR đơn kênh, không phải hội thoại hai bên đã tách kênh.
- **VietSuperSpeech** (arXiv 2603.01894, 2026) — cái gần nhất về ngữ cảnh, và tác giả nói thẳng
  là hướng tới *"Chatbot, Customer Support, and Call Center Applications"*. Nhưng: **mono 16 kHz**,
  cắt 3–30 giây, nguồn YouTube thiên về độc thoại và vlog, **không có nhãn turn-taking, chồng lấn
  hay diarization**. Không dùng được cho VAP.
- **Nexdata 500h / DataoceanAI 213h** — là hội thoại thật, nhưng là hàng bán, không công khai; và
  `SPEC.md` §6 giới hạn dữ liệu ở hội thoại đóng vai có đồng ý.

Nói cho chặt: **không tìm thấy** một corpus hội thoại tiếng Việt công khai có kênh tách riêng
cho từng người nói và có chồng lấn giữ nguyên. Đó là một mệnh đề *không tìm thấy*, không phải
một mệnh đề *không tồn tại* (xem §9). Nhưng với mức chi tiết đã tra, nó đủ để giữ nguyên kết
luận vận hành của roadmap: **hướng VAP đòi phải tự thu.**

Cái *có thể* kế thừa nếu chọn hướng VAP là **định dạng nhãn**, không phải dữ liệu: cấu trúc
`waveform (B, 2, n_samples)` + `vad (B, n_frames + horizon_frames, 2)` ở 50 Hz với chân trời 2
giây, lấy từ `ErikEkstedt/VoiceActivityProjection` (MIT). Chép đúng hình dạng đó ngay từ GĐ 1
nghĩa là dữ liệu tự thu nạp thẳng được vào mã VAP có sẵn mà không cần viết bộ chuyển đổi — và
`docs/annotation-guide.md` hiện đang rỗng, tức chưa có gì phải phá đi.

---

## 6. Giai đoạn 0 là gì

Thuật lại từ `docs/roadmap.md` §6, không thêm gì.

**Mục tiêu.** *"Dựng đủ hạ tầng để đo được, trước khi có bất kỳ mô hình nào."*

**Thứ tự đã ghi**, bảy mắt xích, theo đúng câu chữ của roadmap:

1. `config.py` đọc `configs/default.yaml` đã có
2. `audio/source.py` và một adapter đọc file wav
3. `deciders/silence_threshold.py` (B1, đơn giản nhất)
4. `telemetry/collector.py`
5. năm file `scenarios/*.yaml`
6. `evaluation/metrics.py`

**Lý do B1 đi đầu**, trích nguyên văn: *"B1 đi trước mọi thứ vì nó vừa là baseline bắt buộc, vừa
là bài kiểm tra rẻ nhất cho toàn bộ seam: nếu B1 không cắm vừa `TurnDecider` thì thiết kế sai, và
biết điều đó bây giờ rẻ hơn nhiều so với biết sau khi đã viết fusion."*

**Ranh giới.** *"Chưa mô hình nào. Chưa micro. Chưa dữ liệu thật."*

**Điều kiện xong**, từ bảng giai đoạn: *"`pytest -m scenario` xanh; `run_baseline.py` vẽ được
đường cong B1."*

Ba ràng buộc nữa áp lên GĐ 0 nhưng nằm ở tài liệu khác, cần nhắc vì chúng định hình từng bước:

- `SPEC.md` §9.3 quy tắc 1 — đường cong B1 phải đặt tỉ lệ cắt lời và độ trễ trên cùng một mặt
  phẳng. Một trục đơn lẻ không phải kết quả.
- `SPEC.md` §9.3 quy tắc 2 và `configs/baseline/silence-threshold.yaml` — B1 **quét** 11 giá trị
  200–1200ms, không chọn một.
- `AGENTS.md` — mọi ngưỡng ở `configs/`, log qua `logging`, không `print()`, không ghi audio ra
  đĩa trên đường chạy.

---

## 7. Chia GĐ 0 thành các pha nhỏ

Nguyên tắc chia: **mỗi pha kết thúc bằng một lệnh đã tồn tại trong `AGENTS.md` hoặc
`pyproject.toml`, chạy được và cho câu trả lời đúng/sai.** Không pha nào kết thúc bằng "đã viết
xong file X". Thứ tự giữ nguyên lý do của roadmap: B1 là phép thử seam rẻ nhất, nên mọi thứ trước
nó chỉ là cái tối thiểu để B1 chạy được.

| Pha | Sinh ra cái gì | Lệnh kiểm chứng | Điều kiện ra |
|---|---|---|---|
| **0.1 Cấu hình** | `src/turnwise/config.py`: model pydantic-settings, nạp `configs/default.yaml`, phủ bằng `TURNWISE_*`, đọc được lớp phủ `configs/baseline/silence-threshold.yaml` | `uv run pytest tests/unit/test_configs.py` · `uv run mypy` | Cả hai file YAML nạp thành object đã kiểm kiểu; `take_threshold` và `backchannel_threshold` vẫn là `None`; không module nào ngoài `config.py` đọc YAML hay `os.environ` |
| **0.2 Nguồn khung** | `audio/source.py` (seam) + adapter đọc wav; `FeatureFrame` phát ra mỗi 20ms, `index` liên tục, `samples` mono float32 | `uv run pytest tests/unit -k source` | Một wav 16 kHz cho ra đúng `ceil(len/320)` khung; `index` không nhảy; `start_s` cách đều `duration_s`; kích thước khung lấy từ config, không có literal nào trong `audio/` |
| **0.3 B1 — phép thử seam** | `turn/deciders/silence_threshold.py` cài `TurnDecider`; im lặng dò bằng `AudioProcessor.has_voice()`; ngưỡng đọc từ `silence_threshold_sweep_ms` | `uv run pytest tests/unit -k silence` | `decide()` trả `TurnDecision` ở **mọi** khung với `decider="silence_threshold"` và `scores == {}`; `reset()` cho kết quả giống hệt trên cùng đầu vào; đổi ngưỡng chỉ bằng sửa config; `isinstance(obj, TurnDecider)` là `True` |
| **0.4 Ghi vết** | `telemetry/collector.py`: một chỗ duy nhất ghi `TurnDecision` ra JSONL trong `telemetry.dir` | `uv run pytest tests/unit -k telemetry` | Mỗi `TurnDecision` thành đúng một dòng JSONL mang `outcome`, `decider`, `frame_index`, `at_s`, `scores`, `final_tone`; `turn/` không import `telemetry` (kiểm bằng test tĩnh); không có `print()` |
| **0.5 Năm kịch bản** | `scenarios/*.yaml` cho đúng năm phép thử `SPEC.md` §10 + runner ở `tests/scenarios/`, chạy qua nguồn khung đọc file | `uv run pytest -m scenario` | Marker `scenario` thu được test; năm kịch bản chạy hết với `decider: silence_threshold`; kết quả tất định giữa hai lần chạy; **không cần micro** |
| **0.6 Đo và vẽ** | `evaluation/metrics.py` (tỉ lệ cắt lời, độ trễ, tách theo `final_tone`) + `run_baseline.py` + `figures.py` | `uv run python evaluation/run_baseline.py` | Một lệnh sinh ra đường cong 11 điểm trong `reports/`, **hai trục cùng lúc** theo §9.3 quy tắc 1; `evaluation/` không chứa đường ra quyết định nào; không đọc `data/holdout/` |
| **0.7 Cổng chất lượng** | `tests/conftest.py`, fixture wav sinh tại chỗ, khung `tests/latency/` | `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` · `uv run pytest -m latency` | Toàn bộ lệnh ở `AGENTS.md` mục "Before Marking Done" chạy xanh; marker `latency` thu được ít nhất một test |

Ba ghi chú về chỗ bảng này **suy ra** thay vì **thuật lại**, để không lẫn hai loại:

- **Pha 0.7 không có trong câu chữ GĐ 0 của roadmap.** Nó suy ra từ `AGENTS.md`: hai marker đã
  khai báo mà không thu được test nào là một cái bẫy — `uv run pytest -m latency` hiện *đi qua*
  chứ không *kiểm* gì cả, và `AGENTS.md` lại bắt chạy nó cho mọi thay đổi dưới `audio/` và
  `turn/`.
- **Độ trễ thật không đo được ở GĐ 0.** `SPEC.md` §9.3 quy tắc 4 nói số độ trễ phải đến từ hệ
  chạy trực tiếp, mà GĐ 0 cố ý *"chưa micro"*. Nên pha 0.7 chỉ dựng **khung đo**, và trục độ trễ
  của đường cong 0.6 là **độ trễ tính trên file**, phải ghi nhãn đúng như vậy trong `reports/`.
  Số độ trễ thật thuộc GĐ 4. Không ghi rõ chỗ này là tự tạo ra một con số trông giống kết quả
  nhưng không phải.
- **Lệnh trong bảng đều đã tồn tại.** `pytest -k`, `-m latency`, `-m scenario`,
  `evaluation/run_baseline.py`, ruff, mypy — tất cả đã có trong `AGENTS.md` hoặc
  `pyproject.toml`. Không đề xuất lệnh mới, không đề xuất task runner.

---

## 8. Bảng phân loại từng hạng mục GĐ 0

Ba nhóm, mỗi hạng mục vào đúng một nhóm.

| # | Hạng mục | Nhóm | Bằng chứng / nguồn |
|---|---|---|---|
| 1 | Từ vựng chung: `FeatureFrame`, `TurnDecision`, `Tone`, `TurnOutcome` | **Đã có** | `src/turnwise/types.py`, 148 dòng |
| 2 | Hợp đồng `Scorer`, `TurnDecider`, `Prediction` | **Đã có** | `src/turnwise/turn/base.py`, 111 dòng, hai `Protocol` `runtime_checkable` |
| 3 | Hằng số thiết kế (sample rate, khung, ngân sách, dải quét) | **Đã có** | `configs/default.yaml` 78 dòng; `configs/baseline/silence-threshold.yaml` 19 dòng |
| 4 | CLI + sửa UTF-8 cho console Windows | **Đã có** | `src/turnwise/agent.py`, 77 dòng, `force_utf8_stdio()` |
| 5 | Test cho hợp đồng và cấu hình | **Đã có** | `tests/unit/`, 219 dòng / 5 file |
| 6 | Khung nạp cấu hình có kiểm kiểu | **Kế thừa được** | `pydantic-settings` (MIT), đã khai báo. Phần dán vào repo (~50 dòng) tự viết |
| 7 | Đọc file wav cho nguồn khung | **Kế thừa được** | `soundfile` (BSD-3-Clause), đã khai báo, đã cài |
| 8 | Dò tiếng nói / im lặng cho B1 | **Kế thừa được** | `aec-audio-processing` (BSD-3-Clause), đã khai báo. `has_voice()` + `get_frame_size() == 160`, **đã chạy thử ngày 2026-09-10** |
| 9 | Khử vọng cho `SPEC.md` R5 | **Kế thừa được** | cùng gói trên; `AudioProcessor(enable_aec=True)` |
| 10 | Chạy ONNX trên CPU | **Kế thừa được** | `onnxruntime` (MIT), đã khai báo, đã cài (1.29.0) |
| 11 | F0 cho scorer thanh điệu (GĐ 3, không phải GĐ 0) | **Kế thừa được** ⛔ | `praat-parselmouth` **GPLv3**, đã khai báo — xem §9 |
| 12 | Trọng số B2 | **Kế thừa được** | `smart-turn-v3.2-cpu.onnx`, BSD-2-Clause. Dùng ở GĐ 2 |
| 13 | Trọng số B3 | **Kế thừa được** ⚠ | `Namo-Turn-Detector-v1-Vietnamese`, Apache-2.0. Dùng ở GĐ 2; tokenizer là phụ thuộc mới cần phê duyệt |
| 14 | ASR nuôi B3 | **Kế thừa được** | `faster-whisper` (MIT, extra `asr`) + `vinai/PhoWhisper` (BSD-3-Clause) |
| 15 | Bộ phát khung đều 20ms từ khung capture 10ms | **Phải viết từ đầu** | Không thư viện nào phát `FeatureFrame` của repo này. Logic ~30 dòng; một phụ thuộc cho nó là lỗ hổng, không phải tiết kiệm |
| 16 | Ring buffer cấp phát sẵn, an toàn trong callback | **Phải viết từ đầu** | `.claude/rules/audio.md` cấm cấp phát, khoá và log trong callback PortAudio. Không gói phổ dụng nào bảo đảm điều đó; `collections.deque` cấp phát |
| 17 | `deciders/silence_threshold.py` (B1) | **Phải viết từ đầu** | pipecat `BaseSmartTurn` (BSD-2) cho *hình dạng* đếm im lặng, nhưng hợp đồng ngược nhau: họ phân loại đoạn, bất đồng bộ; ta trả quyết định mỗi khung, đồng bộ. ~40 dòng |
| 18 | Adapter B2 quanh ONNX (GĐ 2) | **Phải viết từ đầu** | Cùng lý do §4.1: `smart-turn` là bộ phân loại đoạn kích hoạt bởi VAD, không phải mô hình theo khung |
| 19 | `telemetry/collector.py` (JSONL, một chỗ duy nhất) | **Phải viết từ đầu** | ADR-0003 quyết định 2 bắt đúng một điểm ghi. `json` + `logging` của thư viện chuẩn là đủ; thêm gói log có cấu trúc là phụ thuộc mới không đổi lấy gì |
| 20 | Gán nhãn thanh điệu âm tiết cuối | **Phải viết từ đầu** | `unicodedata` thư viện chuẩn, **đã chạy thử**: sáu thanh tách đúng bằng NFD. `underthesea`/`viphoneme` là phụ thuộc mới cho việc mà 15 dòng làm xong |
| 21 | Năm `scenarios/*.yaml` + runner | **Phải viết từ đầu** | Năm phép thử ở `SPEC.md` §10 gắn với nghiệp vụ NetCo. `pyyaml` + `pytest` đã có; phần đặc thù thì không tồn tại ở đâu |
| 22 | `evaluation/metrics.py` | **Phải viết từ đầu** | Chưa nguồn nào tách lỗi theo thanh điệu âm tiết cuối (điểm 1 của ADR-0002 vẫn đứng). Đường cong đánh đổi hai trục theo §9.3 quy tắc 1 cũng vậy |
| 23 | `evaluation/figures.py` | **Phải viết từ đầu** | `matplotlib` (extra `research`) vẽ; hình dạng đồ thị là của đề tài |
| 24 | Corpus hội thoại hai kênh tiếng Việt (GĐ 1) | **Phải viết từ đầu** (tự thu) | §5: không tìm thấy nguồn công khai nào. Chỉ **định dạng nhãn** VAP là kế thừa được (MIT) |
| 25 | Giọng TTS tiếng Việt (GĐ 4) | **Chưa xác định** ⛔ | §3.3: không có giọng vi_VN chính thức trong `rhasspy/piper-voices`; hai giọng cộng đồng 0 lượt tải. Cần một quyết định riêng |

**Đếm cho GĐ 0 (hạng mục 1–10, 15–17, 19–23):** 5 đã có, 5 kế thừa được và **đã khai báo sẵn**,
9 phải viết từ đầu — và cả 9 đều nhỏ, đều nằm trong `src/` hoặc `evaluation/`, đều không cần
phụ thuộc mới.

**Kết luận vận hành: GĐ 0 không cần thêm một phụ thuộc Python nào.** Mọi thứ nó chạm tới đã có
trong `pyproject.toml`. Nhu cầu phê duyệt sớm nhất là tokenizer cho B3, và nó thuộc GĐ 2.

---

## 9. Ràng buộc và cờ đỏ cần bạn quyết

### 9.1 Phụ thuộc cần phê duyệt trước khi thêm

`AGENTS.md` mục Off-Limits: *"Do not add dependencies without asking."* Danh sách dưới đây là
**đề nghị**, chưa ai thêm gì.

| Gói | Cần cho | Khi nào | Có tránh được không |
|---|---|---|---|
| `tokenizers` **hoặc** `transformers` | Tách token WordPiece cho B3 (`Namo`) | GĐ 2 | Khó. `model_quant.onnx` nhận id token, không nhận chữ. `tokenizers` (Rust, nhẹ) đủ dùng — **đừng kéo cả `transformers`** |
| `huggingface_hub` | Tải trọng số B2/B3 | GĐ 2 | **Có.** Tải tay một lần, để trong `TURNWISE_MODEL_DIR`, khoá bằng sha256 trong `data/manifests/` — đúng cách `.env.example` đã dựng sẵn |
| `silero-vad` | VAD chính xác hơn trong ồn | Chỉ khi GĐ 2 chứng minh VAD là chỗ hỏng | **Có, ở GĐ 0** — xem §4.2 |
| `maai` | Hướng VAP | Chỉ nếu GĐ 2 chốt hướng VAP | Không áp dụng ở GĐ 0 |

### 9.2 Cờ giấy phép

Repo là đồ án sinh viên / nghiên cứu ứng dụng, nên phần lớn cờ dưới đây **không chặn việc học
tập**. Chúng chặn việc phát hành hoặc thương mại hoá, và `LICENSE` ở gốc repo đang **rỗng 0
byte** — nghĩa là hiện chưa có quyết định nào.

- ⛔ **`praat-parselmouth` là GPLv3, và nó nằm trên đường chạy chính** (`[project] dependencies`,
  không phải extra). Bản `.dist-info` đã cài ghi `License: GPLv3` và
  `Classifier: ... GNU General Public License v3 or later`. Một ảnh container GĐ 5 có
  parselmouth bên trong sẽ kéo theo nghĩa vụ GPLv3 cho toàn bộ phần liên kết với nó. Hai lối ra,
  cả hai đều là ADR chứ không phải một lần sửa: (a) chấp nhận và đặt `LICENSE` gốc là GPLv3;
  (b) đẩy parselmouth xuống extra `research` và trích F0 trên đường chạy bằng cách khác. Cần
  quyết **trước GĐ 3**, vì scorer thanh điệu là chỗ parselmouth vào sâu nhất.
- ⛔ **`piper-tts` là GPL-3.0-or-later** (PyPI 1.8.0 → `OHF-voice/piper1-gpl`). Ở extra `tts`
  nên nhẹ hơn, nhưng cùng bản chất.
- ⛔ **LiveKit Model License** cấm dùng trọng số ngoài LiveKit Agents. Đây là lý do đủ để loại,
  độc lập với chuyện không có tiếng Việt.
- ⚠ **VIVOS và BUD500 là CC-BY-NC-SA-4.0.** Phi thương mại, và ShareAlike có thể lây sang corpus
  phái sinh. Cả hai đằng nào cũng không dùng được cho tầng `turn` (§5), nhưng nếu có lúc nào
  dùng để hiệu chỉnh ASR thì phải ghi rõ.
- ✅ Không có xung đột: BSD-2 (`smart-turn`, `pipecat`), Apache-2.0 (`Namo`), MIT
  (`onnxruntime`, `sounddevice`, `faster-whisper`, `silero-vad`, VAP, MaAI), BSD-3-Clause
  (`aec-audio-processing`, `soundfile`, `PhoWhisper`).

### 9.3 Ràng buộc của đề tài mà mọi đề xuất ở trên đều tôn trọng

Mọi thứ tài liệu này đề nghị đều nằm gọn trong: không đọc `data/holdout/`; `src/` không import
`training/` hay `evaluation/`; mọi ngưỡng ở `configs/`; đường chạy chính CPU-only, không dịch vụ
đám mây; không nghiệp vụ thứ sáu; không mục nào trong `SPEC.md` §11. Không đề xuất nào ở đây
thêm mô hình sinh ngôn ngữ, thêm luồng nghiệp vụ, hay đấu nối tổng đài thật.

---

## 10. Câu hỏi bằng chứng chưa trả lời được

Ghi ra để không ai tưởng chúng đã xong.

1. **Bao nhiêu phần dữ liệu tiếng Việt của `smart-turn` là tổng hợp?** Bộ
   `smart-turn-data-v3.1-train` có trường `synthetic: bool` và trường `language`, nhưng bảng
   thống kê chéo hai trường đó không được công bố. Phải tải 38,5 GB parquet mới đếm được. **Đây
   là câu hỏi đáng đầu tư nhất còn lại**: nếu 1.004 mẫu tiếng Việt phần lớn là TTS tổng hợp thì
   con số 79,38% nói về TTS chứ không nói về người Việt nói thật, và điều đó đổi hẳn cách đọc
   §3.1.
2. **Nguồn dữ liệu huấn luyện của NAMO.** `videosdk-live/Namo-Turn-Detector-v1-Train` trả HTTP
   401 ngày 2026-09-10. Không kiểm chứng được cả kích thước lẫn thành phần lẫn cách sinh nhãn.
3. **Tập test tiếng Việt của NAMO.** Model card nói "1000+ Vietnamese utterances from diverse
   conversational contexts" và báo 82,37%, nhưng không có cách tái dựng.
4. **Không có bảng lỗi theo thanh điệu ở bất kỳ đâu.** Đã tìm ở benchmark của `smart-turn`,
   `RESEARCH.md` của NAMO, và tài liệu MaAI. Điểm 1 trong bốn đóng góp còn trống của ADR-0002
   **vẫn đứng vững** — đây là chỗ duy nhất trong tài liệu này mà việc *không tìm thấy* là một
   tin tốt.
5. **Ngân sách 5ms/khung có sống nổi khi B2 chạy ONNX không?** `smart-turn` chạy một lần trên
   đoạn ≤ 8 giây, không phải mỗi khung, nên chi phí dồn cục. Chỉ `uv run pytest -m latency` trên
   đường chạy thật mới trả lời, tức GĐ 2 trở đi.
6. **`MaAI` chạy CPU thật ở mức nào?** README nói *"operates efficiently, even exclusively on
   CPU"* nhưng không công bố hệ số thời gian thực hay cấu hình máy.
7. **VAP gốc của Ekstedt có chạy CPU không?** README chỉ có hướng dẫn cài `cudatoolkit=11.6`;
   không có phát biểu về CPU. Cập nhật lần cuối 29/05/2024.
8. **Corpus hai kênh tiếng Việt: "không tìm thấy", không phải "không tồn tại".** Đã tra Hugging
   Face, OpenSLR, ACL Anthology, arXiv, GitHub. Chưa tra: kho của các trường đại học Việt Nam
   không đánh chỉ mục, và catalog LDC ở mức chi tiết từng mục.
9. **Giấy phép của VietSuperSpeech.** Abstract không nêu; phải đọc repo Hugging Face
   `thanhnew2001/VietSuperSpeech` để biết. Không chặn gì, vì đằng nào nó cũng là mono đã cắt.
10. **Chất lượng của các bản chuyển CTranslate2 của PhoWhisper.** Đều do cá nhân đăng, lượt tải
    hai chữ số, không có bản chuyển chính thức từ VinAI. Nếu dùng thì phải tự đo WER và khoá
    sha256.

---

*Tài liệu này chỉ mang bằng chứng. Mọi lựa chọn suy ra từ nó — thêm phụ thuộc, chốt giấy phép,
chọn hướng ở `SPEC.md` §7 — đều cần một ADR riêng.*
