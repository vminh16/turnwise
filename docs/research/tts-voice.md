# Giọng bot: chọn TTS tiếng Việt nào, và với giấy phép gì

Tài liệu này là **bằng chứng, không phải quyết định**. Nó trả lời đúng một câu hỏi: *engine TTS
tiếng Việt nào dùng được cho Turnwise, với giấy phép nào, và có chạy nổi trên laptop CPU không?*
Việc chốt engine thuộc về `docs/adr/`.

TTS ở đây là **linh kiện mua sẵn**. `SPEC.md` §11 cấm "huấn luyện… tổng hợp giọng nói mới", nên
mọi phương án dưới đây là *dùng trọng số có sẵn*; R12 đòi giọng **tự nhiên, không vô cảm** và nói
rõ cách đạt được là "chọn giọng TTS có sẵn theo độ tự nhiên".

Hai lần dùng, cùng một engine, khác hẳn ràng buộc:

- **GĐ 1 (bây giờ).** Render offline 46 câu thoại cố định trong `roleplay/*.yaml` ra WAV. Các
  file này phát cho người đóng vai nghe và **nằm trong kênh 1 của mọi bản ghi** — nghĩa là giọng
  bot bị **nướng cứng vào tập đánh giá vàng**. Đổi giọng sau GĐ 1 = thu lại. Không cần thời gian
  thực. Cần 16 kHz (hoặc lấy mẫu lại được), mono.
- **GĐ 4 (sau).** `dialog/` render câu mẫu có slot (số thuê bao, số tiền, địa chỉ, giờ hẹn) theo
  thời gian thực trong cuộc gọi WebRTC, trên laptop Windows 11 ~16 GB RAM, **không GPU**. Cần
  RTF < 1 và tốt nhất là có streaming.

---

## 1. Nguồn và ngày tra cứu

**Mọi con số dưới đây tra ngày 2026-09-20.** Nguồn chỉ là nguồn gốc: trường `license` trong
model card, file `LICENSE` trong chính repo, metadata Hugging Face Hub API và PyPI JSON API,
README của tác giả, trang giá/điều khoản chính thức. Không lấy từ blog so sánh hay bài "top 10".
Chỗ nào không đọc được vì phải đăng nhập thì ghi vào §7 chứ không đoán.

Cảnh báo về cách tìm: bộ lọc `pipeline_tag=text-to-speech&language=vi` của Hugging Face **báo
thừa**. Ba model đứng đầu bảng đó — `hexgrad/Kokoro-82M` (`language: ["en"]`),
`Qwen/Qwen3-TTS-12Hz-0.6B-Base` (`["zh","en","ja","ko","de","fr","ru","pt","es","it"]`) và
`coqui/XTTS-v2` — **không khai tiếng Việt trong `cardData.language` của chính chúng**.

---

## 2. Trả lời ngắn

| Hạng | Ứng viên | Giấy phép | Laptop CPU? | Dùng được cho |
|---|---|---|---|---|
| **1** | **VieNeu-TTS v3 Turbo** (`pnnbao-ump/VieNeu-TTS-v3-Turbo`) | **Apache-2.0**, tác giả nói rõ audio sinh ra dùng thương mại được | **Có** — ONNX, torch-free, RTF 0,55–0,61 fp32 / 0,35 int8, tác giả tự đo | **Cả hai giai đoạn** |
| 2 | Piper, giọng `vi_VN-vais1000-medium` | Trọng số theo dataset **CC BY 4.0**; runtime `piper-tts` **GPL-3.0-or-later** | Có — ONNX, rất nhẹ | GĐ 1; GĐ 4 vướng GPL khi phát hành |
| 3 | Dịch vụ hosted (FPT.AI free 100k ký tự/tháng) | Điều khoản không đọc được hết nếu không có tài khoản | Không tự host | Dự phòng GĐ 1 |
| ✗ | viXTTS / XTTS-v2 | **CPML — phi thương mại**, kèm điều khoản lan truyền sang *output* | Có | Rủi ro giấy phép, xem §4.2 |
| ✗ | F5-TTS-Vietnamese-ViVoice | **CC BY-NC-SA 4.0** | Có | Phi thương mại + share-alike |
| ✗ | vietTTS (NTT123) | MIT | Có | **Tác giả đã bỏ** từ 2021 |

**Phát hiện nặng nhất:** model người dùng hỏi — "vieneu" — **có thật**, đúng như mô tả (fine-tune
tiếng Việt của NeuTTS Air), **Apache-2.0**, và hiện đã đi xa hơn bản gốc rất nhiều. Nó là ứng
viên duy nhất thoả *đồng thời* cả bốn ràng buộc của dự án: giấy phép sạch, chạy CPU không GPU,
có streaming, và có chuẩn hoá số/ngày/tiền cho tiếng Việt. Xem §3.

**Phát hiện thứ hai:** mọi lựa chọn tiếng Việt "nổi tiếng" còn lại đều **dính đúng loại bệnh đã
giết MaAI VAP** — phi thương mại, và ở XTTS thì điều khoản còn bám theo cả *audio sinh ra*, tức
bám vào tập dữ liệu đánh giá. Xem §4.2.

---

## 3. "vieneu" — có tồn tại, và đây là tên thật của nó

Xác nhận: **có**. Tác giả `pnnbao-ump` (GitHub `pnnbao97`). Không phải một cái tên người dùng
nhớ nhầm.

| Bản | Repo | Giấy phép | Base | Sample rate | Cập nhật |
|---|---|---|---|---|---|
| v1 (0.5B) | `pnnbao-ump/VieNeu-TTS` | apache-2.0 | `neuphonic/neutts-air` | 24 kHz | 2026-05-06 |
| v2 (0.3B) | `pnnbao-ump/VieNeu-TTS-v2` | apache-2.0 | (qwen3, dựng lại) | 24 kHz | 2026-05-09 |
| **v3 Turbo** | `pnnbao-ump/VieNeu-TTS-v3-Turbo` | apache-2.0 | — | **48 kHz** | **2026-09-16** |

Nguồn metadata: Hugging Face Hub API, `https://huggingface.co/api/models/pnnbao-ump/VieNeu-TTS-v3-Turbo`
(tra 2026-09-20; `downloads` = 605.161, `gated` = `false`).

**Liên hệ với NeuTTS Air là có thật và đã đứt.** v1 khai `base_model: ["neuphonic/neutts-air"]`;
v3 Turbo không còn khai base_model nào, dùng codec `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` +
phonemizer `sea-g2p`. Đáng ghi: **`neuphonic/neutts-air` là repo gated** (`gated: "auto"`,
`extra_gated_fields` hỏi "Affiliation" và "Role", `raw/main/README.md` trả **HTTP 401**). Chạm
vào *bản gốc* phải có tài khoản HF; chạm vào **v3 Turbo thì không** — nó không gated.

### 3.1 Giấy phép, trích nguyên văn

Model card `pnnbao-ump/VieNeu-TTS-v3-Turbo`, mục "Usage Rights & Licensing FAQ"
(<https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo>, tra 2026-09-20):

> Yes. The license applies to **all** artifacts shipped here — `model.safetensors`, the ONNX
> exports, configs and tokenizers, and the bundled **preset-voice assets** […]

> Yes. The bundled preset voices are distributed under the same Apache-2.0 license as the rest of
> the repository, and audio generated with them **may be used in commercial and monetized
> content** (voice-over, videos, products, services) — no additional license or fee.

> The speakers (or rightsholders) behind the shipped preset-voice assets granted appropriate
> rights and consent […] for **AI training and synthetic speech generation**.

**Trả lời thẳng câu hỏi của dự án:** audio sinh ra bằng **giọng preset** được phép nằm trong một
tập đánh giá nghiên cứu không công bố. Apache-2.0 không có điều khoản phi thương mại, không có
no-derivatives, và tác giả nói rõ output không bị ràng buộc thêm. Nghĩa vụ duy nhất là **giữ
notice khi redistribute trọng số** — không phải khi phát ra audio.

Hai cảnh báo tác giả tự nêu, cả hai đều áp vào Turnwise:

> **Voice cloning is your responsibility.** The consent confirmation above covers the **bundled
> preset voices only**.

⇒ **Dùng giọng preset, không clone.** Clone đưa một câu hỏi đồng thuận mới vào tập dữ liệu mà
`docs/annotation-guide.md` chưa trả lời.

> The detailed internal data-collection and processing pipeline for the training corpus is **not
> publicly disclosed**, and the [VieNeu-TTS-10k-ENVI] dataset is gated.

⇒ Xuất xứ 10.000 giờ huấn luyện **không kiểm chứng được** (§7).

### 3.2 Chạy CPU — số liệu do chính tác giả đo

`docs/streaming.md` trong repo GitHub
(<https://github.com/pnnbao97/VieNeu-TTS/blob/main/docs/streaming.md>, tra 2026-09-20). Máy đo:
**12th-gen i5, 6 P-core, 6 ORT thread**, câu 27 / 88 / 147 ký tự. Bảng nguyên văn:

| Precision | TTFA | RTF, 1 stream | Min lead | 2 requests at once |
|---|---|---|---|---|
| **fp32** (default) | 264–282 · 313–357 · 345–401 ms | 0,61 · 0,57 · 0,55 | +320 ms | TTFA 399 / 564 ms, **RTF 1,19 / 1,19 → both stall** |
| **int8** | 141–144 · 163–169 · 192–194 ms | 0,35 · 0,35 · 0,35 | +320 ms | TTFA 224 / 336 ms, RTF 0,58 / 0,67 → still real-time |

Và hai câu quyết định được-hay-không trên laptop, nguyên văn:

> TTFA depends on the **length of the first sentence** […] and the **core count**: a 4-core laptop
> will see fp32 ~400–600 ms, int8 ~200–300 ms; on 2–4 cores fp32 RTF can exceed 1 → use int8 only.

> int8 **needs a CPU with VNNI** (Intel from Cascade Lake / Ice Lake / Alder Lake, AMD Zen 4).
> Without VNNI the int8 acoustic decoder saturates and babbles — use fp32.

Đọc thẳng ra cho GĐ 4: **RTF < 1 là có thật trên CPU, nhưng đúng một luồng**, và **320 ms lead-in
là chi phí cố định**. Đây là chi phí *khởi động câu nói của bot*, không phải chi phí mỗi khung của
tầng `turn` — đừng cộng nhầm vào cùng một budget ở `configs/default.yaml`.

Cài đặt: `pip install vieneu` (PyPI 3.8.1, `requires_python >=3.10`, `license` = Apache-2.0,
<https://pypi.org/pypi/vieneu/json>). Phụ thuộc gốc **không có torch**: `sea-g2p`, `onnxruntime`,
`numpy`, `soundfile`, `soxr`, `kaldi-native-fbank`, `tokenizers`, `huggingface_hub`, `PyYAML`,
`gradio`, `librosa`; torch chỉ ở extras (`cuda`, `finetune`, `legacy`).

> ⚠ `gradio` và `librosa` nằm trong **phụ thuộc gốc**, không phải extra. Với quy tắc "Do not add
> dependencies without asking", đây là thứ phải nêu trong ADR. Trên `src/` thì `gradio` thừa hẳn.

Streaming: `infer_stream()` trả `np.float32 @ 48 kHz`, cộng server tương thích OpenAI
`POST /v1/audio/speech` (`pcm`/`wav`, chunked hoặc SSE) mà tác giả nói chạy được với Pipecat và
LiveKit. 48 kHz → 16 kHz là một lần `soxr`, vốn đã là phụ thuộc sẵn.

---

## 4. Bảng phán quyết — TTS tự host

### 4.1 Tổng hợp

| Model | `license` (từ model card) | Phi thương mại? | CPU | Sample rate | Phán quyết |
|---|---|---|---|---|---|
| `pnnbao-ump/VieNeu-TTS-v3-Turbo` | `apache-2.0` | Không | ONNX, RTF 0,35–0,61 (tác giả đo) | 48 kHz | **Dùng** |
| `pnnbao-ump/VieNeu-TTS-v2` | `apache-2.0` | Không | GGUF Q4 trên CPU | 24 kHz | Dự phòng nếu v3 nặng |
| Piper `vi_VN-vais1000-medium` | dataset **CC BY 4.0**; runtime GPL-3.0+ | Không, nhưng **copyleft** | ONNX, rất nhẹ | 22.050 Hz | GĐ 1 được |
| Piper `vi_VN-25hours_single-low` | dataset **"License: Unknown"** | Không rõ | ONNX | **16.000 Hz** | Tránh — xuất xứ mù |
| Piper `vi_VN-vivos-x_low` | dataset **CC BY-NC-SA 4.0** | **Có** | ONNX | 16.000 Hz | Tránh |
| `capleaf/viXTTS` | `other` → CPML | **Có** | Có, nặng | 24 kHz | Xem §4.2 |
| `coqui/XTTS-v2` | `other` → CPML | **Có** | Có, nặng | 24 kHz | Xem §4.2 |
| `hynt/F5-TTS-Vietnamese-ViVoice` | `cc-by-nc-sa-4.0` | **Có** + share-alike | Chậm trên CPU | 24 kHz | Tránh |
| `NTT123/vietTTS` | MIT | Không | Có | 16 kHz | **Đã bỏ** (xem dưới) |

Nguồn: Hugging Face Hub API cho từng repo, tra 2026-09-20. Piper: file `MODEL_CARD` và
`*.onnx.json` trong `rhasspy/piper-voices`, tra cùng ngày. `piper-tts` PyPI 1.8.0,
`license = "GPL-3.0-or-later"`, `requires_python >=3.9` (<https://pypi.org/pypi/piper-tts/json>).

`vietTTS` loại vì chính README của tác giả, nguyên văn
(<https://github.com/NTT123/vietTTS>, tra 2026-09-20):

> 🔔 **Notice**: This project is no longer being updated.

### 4.2 XTTS / viXTTS — bệnh cũ, chỗ mới

`capleaf/viXTTS` và `coqui/XTTS-v2` khai `license: other` trỏ tới `https://coqui.ai/cpml`. **Link
đó trả HTTP 404** (Coqui đã đóng cửa) — nhưng bản gốc còn nằm trong chính repo model tại
<https://huggingface.co/coqui/XTTS-v2/raw/main/LICENSE.txt>. Nguyên văn ba chỗ quan trọng:

> This license allows only non-commercial use of a machine learning model **and its outputs**.

> Use by commercial or for-profit entities **for testing, evaluation, or non-commercial research
> and development**. Use of the model to train other models for commercial use is not a
> non-commercial purpose.

> **Notices.** You must ensure that anyone who gets a copy of any part of the model, or any
> modification of the model, **or their output**, from you also gets a copy of these terms or the
> URL for them above.

Đọc cho đúng, không phóng đại: **một đồ án nghiên cứu không sinh doanh thu thì CPML cho phép** —
câu "testing, evaluation, or non-commercial research and development" bao đúng trường hợp này.
Cái làm nó thành rủi ro là mệnh đề **Notices**: giấy phép **bám theo output**, nên mọi bản ghi
GĐ 1 có kênh 1 do XTTS sinh ra mang nghĩa vụ CPML mãi mãi. Muốn phát hành tập dữ liệu, hay dự án
đổi sang bất kỳ dạng thương mại nào, **phải thu lại toàn bộ**.

Đây đúng là hình dạng của vấn đề đã loại trọng số MaAI VAP. Khác biệt: NC-ND cấm ngay từ đầu,
CPML cho phép hôm nay và khoá tương lai. Với dữ liệu **nướng cứng vào tập đánh giá vàng**, khoá
tương lai còn tệ hơn.

---

## 5. Bảng phán quyết — dịch vụ hosted ("cái người ta hay dùng để lồng tiếng AI")

| Dịch vụ | Cần thẻ tín dụng? | Quota miễn phí | Có API? | Quyền trên audio sinh ra |
|---|---|---|---|---|
| **FPT.AI** | Không thấy yêu cầu | **100.000 ký tự/tháng**, "phiên bản 5 — các giọng đọc chất lượng tốt nhất" | Có, REST | Không đọc được (§7) |
| **Vbee** | Không rõ | ~3.000 ký tự/ngày (nguồn thứ cấp) | Có, gói riêng ~799.000 ₫/tháng | Không đọc được (§7) |
| **Viettel AI** | Không rõ | Dùng thử 1 tháng (nguồn thứ cấp) | Có | Không đọc được (§7) |
| **Zalo AI** | Không rõ | Không đọc được | Có | Không đọc được (§7) |
| **ElevenLabs** | Không, cho gói Free | 10k credit/tháng | Có | **Free = phi thương mại** (dưới) |
| **Google Cloud TTS** | **Có** — cần billing account | 4 triệu ký tự/tháng (Standard), 1 triệu (WaveNet) | Có | Theo Google Cloud ToS |
| **Azure Speech** | Không rõ cho F0 | **0,5 triệu ký tự/tháng** (Neural, F0) | Có | Theo Microsoft ToS |
| **CapCut** | Không | Có, trong app | **Không có API công khai** | Không đọc được từ ToS (§7) |

Nguồn đọc được tận gốc, tra 2026-09-20:

- **FPT.AI** — <https://docs.fpt.ai/docs/vi/speech/documentation/tts-pricing/>. Gói Free:
  **"100.000 kí tự (phiên bản 5 - các giọng đọc chất lượng tốt nhất)"**, kèm hạn chế nguyên văn
  **"Tốc độ chuyển đổi thấp"**, **"Giới hạn thời gian sử dụng"**, giới hạn request/ngày, không
  hỗ trợ kỹ thuật. Premium 500.000 ₫ / 1.500.000 ký tự.
- **ElevenLabs** — <https://elevenlabs.io/terms-of-use>: *"as between you and ElevenLabs, you
  retain all rights in and to your Output."* Nhưng người dùng gói Free *"may only use the Services
  for non-commercial purposes"*. Trang giá (<https://elevenlabs.io/pricing>): Free = "10k credits
  per month", "Commercial License" chỉ từ gói Starter trở lên.
- **Azure** — <https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/>:
  **"0.5 million characters free per month"** cho giọng Neural bậc F0.
- **Google Cloud** — <https://cloud.google.com/text-to-speech/pricing>: 4 triệu ký tự Standard và
  1 triệu ký tự WaveNet miễn phí mỗi tháng.

**Kết luận cho câu hỏi "người ta lồng tiếng AI bằng gì":** CapCut và ElevenLabs là cái đa số dùng,
và **cả hai đều sai cho Turnwise** — CapCut không có API nên vô dụng ở GĐ 4, ElevenLabs gói Free
tự nó cấm thương mại. Trong nhóm hosted, **FPT.AI là phương án miễn phí hợp lý nhất cho GĐ 1**:
46 câu thoại cỡ vài nghìn ký tự, nằm gọn trong 100.000 ký tự/tháng ở giọng tốt nhất. Nhưng **mọi
dịch vụ hosted đều không dùng được cho GĐ 4**, vì lý do nằm ngoài giá: một vòng HTTP ra Internet
giữa cuộc gọi WebRTC thêm jitter mạng vào đúng chỗ `AGENTS.md` cảnh báo ("Latency measured offline
is not real latency"), và biến TTS thành phụ thuộc mạng trên đường chạy thời gian thực.

---

## 6. Đọc số, tiền, địa chỉ, ngày — chỗ kịch bản `roleplay/` dày đặc nhất

Đây là tiêu chí duy nhất mà đa số model card **không nói gì**. Piper đẩy sang `espeak-ng`
(`espeak: {"voice": "vi"}` trong cả ba `*.onnx.json`), tức chuẩn hoá số là của espeak-ng, không
phải của model. viXTTS, F5-TTS và XTTS-v2 không nêu gì về chuẩn hoá văn bản tiếng Việt.

VieNeu là ngoại lệ, và nó có bằng chứng chạy được. Phonemizer `sea-g2p` (Apache-2.0, xác nhận
bằng `https://raw.githubusercontent.com/pnnbao97/sea-g2p/main/LICENSE`) mô tả nguyên văn:

> **Smart Normalization**: Staged pipelines per language — **17 stages for Vietnamese (numbers,
> dates, units, formulas, technical terms)** […]

Và README đưa luôn output thật, nguyên văn
(<https://github.com/pnnbao97/sea-g2p>, tra 2026-09-20):

```
input : "Giá cổ phiếu tăng từ $0.000045 lên $1,234.5678 trong 3.5×10^6 giao dịch."
output: "giá cổ phiếu tăng từ không chấm không không không không bốn lăm <en>u s d</en> lên
         một nghìn hai trăm ba mươi bốn phẩy năm sáu bảy tám <en>u s d</en> trong
         ba chấm năm nhân mười mũ sáu giao dịch."
```

Ba điều đọc ra được từ đúng ví dụ này, cả ba đều quan trọng cho kịch bản tổng đài:

1. **"bốn lăm" chứ không phải "bốn năm"** — đúng quy tắc đọc số tự nhiên của tiếng Việt, dấu hiệu
   bộ chuẩn hoá do người biết tiếng Việt viết, không phải map chữ số thẳng.
2. **Phân biệt "chấm" và "phẩy"** theo ngữ cảnh: `0.000045` đọc từng chữ số sau "chấm",
   `1,234.5678` đọc phần nguyên thành số rồi "phẩy". Số thuê bao và số tiền cần đúng hai lối đọc
   khác nhau này.
3. `Normalizer(lang="vi")` **gọi riêng được**, tách khỏi G2P ⇒ GĐ 4 chuẩn hoá slot value trước rồi
   mới đưa vào TTS, và **kiểm thử bằng unit test không cần audio** — khớp với "scenario replay is
   deterministic and runs in CI".

Ví dụ này **không** chứng minh: đọc địa chỉ Việt Nam ("số 12 ngõ 45 Trần Duy Hưng"), giờ hẹn
("14 giờ 30 thứ Năm"), hay số thuê bao 10 chữ số. Ghi vào §7.

---

## 7. Chưa kiểm chứng được

Chín mục. Không đoán, không suy.

1. **Chất lượng nghe thật của mọi model.** Không tải trọng số, không phát audio. Mọi xếp hạng
   "tự nhiên" ở đây *suy từ giấy phép và số tác giả công bố*, **không phải từ nghe**. R12 đòi điểm
   do người nghe chấm; tài liệu này không thay được phép đo đó.
2. **RTF của VieNeu trên đúng laptop của dự án.** Số 0,55–0,61 đo trên i5 gen 12, 6 P-core. Không
   biết laptop mục tiêu mấy nhân vật lý, và **không biết CPU đó có VNNI không** — mà VNNI là ranh
   giới giữa int8 (0,35) và fp32 (0,55–0,61, có thể > 1 trên 2–4 nhân).
3. **Xuất xứ 10.000 giờ dữ liệu huấn luyện VieNeu** — *"not publicly disclosed"*, dataset gated.
   Cam kết đồng thuận chỉ phủ **giọng preset**, không phủ corpus.
4. **Điều khoản FPT.AI, Vbee, Viettel AI, Zalo AI về quyền trên audio sinh ra.** Trang giá FPT.AI
   đọc được, trang điều khoản thì không. `viettelai.vn/vi/bang-gia` trả trang rỗng (SPA);
   `zalo.ai/docs/api/text-to-speech` chuyển 302 sang `ai.zalo.solutions`, cũng SPA không render.
   **Phải có tài khoản mới đọc được.**
5. **Quota Vbee và Viettel AI.** "3.000 ký tự/ngày" và "dùng thử 1 tháng" đến từ **nguồn thứ cấp**.
   Không dùng làm căn cứ.
6. **ToS của CapCut về TTS.** Các trang nói "commercial license" đều là marketing
   (`capcut.com/resource/...`), không phải `capcut.com/clause/terms-of-service`. CapCut cũng
   **không có API công khai**, nên với GĐ 4 câu hỏi này là moot.
7. **Google Cloud / Azure có bắt buộc thẻ tín dụng không.** Bậc miễn phí có thật; điều kiện mở
   billing account không đọc được từ chính trang giá.
8. **Chuẩn hoá địa chỉ, giờ hẹn, số thuê bao của `sea-g2p`.** README chỉ có một ví dụ tiền tệ và
   một ví dụ email. 17 stage được *liệt kê*, không được *chứng minh* từng cái.
9. **Giấy phép dataset "InfoRe Technology 1"** mà giọng Piper `25hours_single` dùng: `MODEL_CARD`
   ghi đúng chữ **"License: Unknown"**. Một giọng 16 kHz sẵn sàng dùng, nhưng xuất xứ mù.

### Những thứ phải tải về mới trả lời được

| Cần tải | Dung lượng ước | Nó chứng minh gì |
|---|---|---|
| `pnnbao-ump/VieNeu-TTS-v3-Turbo` ONNX + `vieneu` | vài trăm MB | Mục 1, 2, 8 — RTF thật trên laptop này, và 46 câu `roleplay/` nghe ra sao |
| `vi_VN-vais1000-medium.onnx` + `piper-tts` | ~60 MB | Mốc so sánh chất lượng thấp, và kiểm tra espeak-ng đọc số Việt |

Cả hai đều là **quyết định thêm phụ thuộc**, nên theo `AGENTS.md` phải hỏi trước, không tự làm.

---

## 8. Khuyến nghị

### Chỉ cho GĐ 1 (render offline 46 câu)

**VieNeu-TTS v3 Turbo, giọng preset, fp32.** Không có ràng buộc thời gian thực ở GĐ 1, nên VNNI
và RTF đều không thành vấn đề — cứ để chạy chậm. Đổi lại được giấy phép Apache-2.0 sạch, 48 kHz
hạ xuống 16 kHz bằng `soxr`, và 23 giọng preset để chọn theo R12.

*Phương án dự phòng nếu không muốn thêm phụ thuộc vào lúc này:* **FPT.AI gói Free**. 46 câu nằm
gọn trong 100.000 ký tự/tháng, không cần cài gì, không cần thẻ. Đổi lại: giọng bị khoá vào một
nhà cung cấp mà điều khoản về output ta **chưa đọc được** (§7 mục 4) — và giọng này sẽ nằm vĩnh
viễn trong kênh 1 của tập đánh giá.

### Cho cả hai giai đoạn

**VieNeu-TTS v3 Turbo.** Đây là ứng viên duy nhất không phải đổi giữa chừng: Apache-2.0, ONNX
torch-free, RTF < 1 một luồng trên CPU, streaming qua `infer_stream()` và server tương thích
OpenAI, và `sea-g2p` xử lý đúng chỗ khó nhất là đọc số tiếng Việt. Một engine cho cả hai lần dùng
cũng loại bỏ một biến gây nhiễu: giọng ở GĐ 4 **giống hệt** giọng đã nướng vào tập đánh giá GĐ 1,
nên điểm tự nhiên R12 của hai giai đoạn so sánh được với nhau.

### Đánh đổi — nói thẳng

| Đánh đổi | Nội dung |
|---|---|
| **Phụ thuộc** | `vieneu` kéo theo `gradio` và `librosa` ở tầng gốc. Thừa cho `src/`. Hoặc chấp nhận, hoặc gọi `onnxruntime` + `sea-g2p` trực tiếp và bỏ SDK — cách hai gọn hơn nhưng phải tự viết lại vòng streaming. |
| **VNNI** | Không có VNNI ⇒ kẹt ở fp32 ⇒ **đúng một luồng TTS**, và trên 2–4 nhân có thể vỡ RTF. Phải đo trước khi cam kết GĐ 4. |
| **320 ms lead-in** | Chi phí cố định trước byte audio đầu tiên trên CPU. Phải nằm trong ngân sách của `configs/`, và nó **cộng vào** chứ không thay thế độ trễ quyết định lượt. |
| **Chưa nghe thử** | Toàn bộ xếp hạng này dựa trên giấy phép và số liệu tác giả. Nếu nghe thử thấy VieNeu không đạt R12, thứ tự đổi ngay — và khi đó lựa chọn tiếp theo (Piper) là một bước lùi rõ rệt về độ tự nhiên. |
| **Một điểm hỏng duy nhất** | Cả GĐ 1 lẫn GĐ 4 phụ thuộc một tác giả cá nhân. Apache-2.0 khiến repo biến mất cũng không sao *nếu đã lưu trọng số*. Lưu bản đã dùng, và ghi revision hash vào `configs/`. |

---

*Tài liệu này chỉ mang bằng chứng. Chốt engine TTS, thêm phụ thuộc `vieneu`/`onnxruntime`, và
chọn giọng preset cụ thể để nướng vào GĐ 1 — cả ba đều cần một ADR riêng, theo ADR-0001. Không
mục nào ở đây cho phép bỏ qua phép đo R12 do người nghe chấm.*
