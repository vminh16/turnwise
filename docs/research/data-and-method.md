# Dữ liệu và phương pháp — hai câu hỏi chưa chốt, và bằng chứng để chốt

Tài liệu này trả lời đúng hai câu hỏi: **(1) dữ liệu đóng vai tự thu là tập huấn luyện hay tập
đánh giá, và có nguồn công khai nào thay được không?** — **(2) dự án đã chốt phương pháp nào
chưa, và Giai đoạn 2 phải đo gì để chốt cho trung thực?**

**Mọi con số tra ngày 2026-09-12.** Nguồn chỉ là nguồn gốc: bài báo, model card, dataset card,
file `LICENSE`, `config.json`, catalog LDC/ELRA, metadata Hugging Face Hub API, và mã nguồn của
chính dự án đó. Không lấy từ blog, bài tóm tắt hay bảng so sánh của bên thứ ba.

**Thứ tự ưu tiên khi đọc:** `SPEC.md` đúng hơn tài liệu này; `docs/roadmap.md` và `docs/adr/`
đúng hơn mọi thứ tra được trên mạng. Tài liệu này chỉ mang **bằng chứng**; nó không quyết định
gì. Chỗ nào bằng chứng ngoài mạng mâu thuẫn với tài liệu trong repo thì §7 nói rõ cả hai phía và
nêu tài liệu nào phải sửa — việc sửa là một ADR, không phải một lần sửa chữ.

**Cập nhật 2026-10-28:** câu 1–3 ở §10 đã được quyết bởi ADR-0007. §6 của `SPEC.md` được đọc theo
lối (a); corpus nghiên cứu hội thoại thật làm **bộ phân tích**, tách khỏi dữ liệu đóng vai; không tự
thu thêm. Nguồn và cách lấy mẫu ở `docs/research/analysis-corpus.md`. Phần còn lại của tài liệu này
giữ nguyên làm bằng chứng tại thời điểm tra.

Tài liệu này **xây tiếp** `docs/research/reuse-audit.md` (tra ngày 2026-09-10). Nó không lặp lại
bảng phán quyết kế thừa ở đó. Nó trả lời bốn câu hỏi còn treo ở §10 của tài liệu đó (câu 1, 2, 8,
9), và sửa ba chỗ trong chính tài liệu đó.

---

## 1. Tóm tắt cho người vội

| Câu hỏi | Trả lời ngắn |
|---|---|
| Dữ liệu đóng vai là train hay test? | **Chủ yếu là evaluation + calibration.** Không đủ và không thể đủ để huấn luyện một mô hình VAP từ đầu. |
| Có corpus tiếng Việt công khai thay được không? | **Không cho việc huấn luyện turn-taking.** Mọi corpus miễn phí đều đơn kênh, đã cắt thành phát ngôn, không có ranh giới lượt. Có **một** corpus hai kênh thật (LDC96S60, 25 giờ) nhưng phải mua và không phải đóng vai. |
| Cần bao nhiêu giờ? | Suy ra từ chỉ số, không từ mô hình: **cỡ 6–12 giờ hội thoại hai kênh, ≥ 24–30 người nói**. Giả định nêu rõ ở §5.3. |
| Đã chốt method chưa? | **Chưa.** Không ADR nào chọn một trong bốn hướng §7. Cái đã chốt là seam, hợp đồng, ngữ nghĩa bỏ phiếu trắng, ba baseline, và thứ tự ưu tiên "thích ứng trước, tự dựng sau". |
| Giả thuyết thanh điệu đúng không? | **Tiền đề được ủng hộ bằng nguyên văn của một nhà ngữ âm học; hệ quả mạnh thì chưa ai kiểm chứng, và có một bằng chứng đi ngược.** Chi tiết §6.3. |

Phát hiện nặng nhất: **toàn bộ 1.004 mẫu tiếng Việt trong tập benchmark của `smart-turn` v3.2 là
giọng tổng hợp TTS.** Không một mẫu nào là người Việt nói. Xem §4.3.

---

## 2. Nguồn đã tra và cách kiểm chứng

Ba loại bằng chứng, phân biệt rõ vì độ nặng khác nhau:

- **Đọc từ nguồn gốc** — PDF bài báo, catalog LDC/ELRA, dataset card, model card.
- **Truy vấn API** — Hugging Face Hub API và `datasets-server.huggingface.co` (statistics,
  filter). Đây là cách §4.3 đếm được mà không phải tải 36,8 GB parquet.
- **Không kiểm chứng được** — ghi thẳng vào §8, không đoán.

Hai thứ tra lại và **không đổi** so với `reuse-audit.md` ngày 2026-09-10, nên các con số ở tài
liệu đó vẫn dùng được:

- `pipecat-ai/smart-turn-v3`: `lastModified` = `2026-01-07T18:00:39Z`, licence `bsd-2-clause`,
  vẫn năm file benchmark, vẫn `smart-turn-v3.2-cpu.onnx` là bản mới nhất.
- `videosdk-live/Namo-Turn-Detector-v1-Vietnamese`: `lastModified` = `2025-10-15T07:39:32Z`,
  licence `apache-2.0`, `base_model` = `distilbert-base-multilingual-cased` — **xác nhận đính
  chính §3.2 của `reuse-audit.md`** (ADR-0002 ghi "mmBERT" là sai cho bản tiếng Việt). Bộ dữ liệu
  huấn luyện `videosdk-live/Namo-Turn-Detector-v1-Train` **vẫn trả HTTP 401** ngày 2026-09-12 —
  câu hỏi 2 ở §10 của `reuse-audit.md` vẫn chưa trả lời được.

---

# PHẦN A — Dữ liệu

## 3. Mỗi hướng ở `SPEC.md` §7 cần loại dữ liệu nào, và bao nhiêu

### 3.1 "Nhãn tự sinh" không có nghĩa là "cần ít dữ liệu"

`SPEC.md` §7 mô tả hướng VAP là *"nhãn tự sinh từ chính dữ liệu nên không cần gán tay"*, và tiêu
chí chọn số (4) là *"không cần gán nhãn thủ công quy mô lớn"*. Cả hai câu đều **đúng** — và cả
hai đều không nói gì về chi phí **thu** dữ liệu.

Đọc từ bài gốc (Ekstedt & Skantze, *Voice Activity Projection: Self-supervised Learning of
Turn-taking Events*, arXiv 2205.09812, §2 và §4 — <https://arxiv.org/pdf/2205.09812>):

- Nhãn VAP sinh ra bằng cách rời rạc hoá **hoạt động giọng nói của từng kênh** trong cửa sổ
  tương lai 2 giây thành 8 bin (4 bin mỗi người, độ dài 200/400/600/800ms), cho 2⁸ = 256 trạng
  thái.
- Nghĩa là nhãn tự sinh **với điều kiện tiên quyết**: mỗi người nói phải nằm trên **kênh riêng**.
  Bài viết nguyên văn: *"The dialog waveforms are volume normalized, resampled to 16kHz and,
  unlike prior work, we use the separate channel."*
- Thứ được miễn là **công gán nhãn**. Thứ không được miễn là **công thu hai kênh sạch, có tách
  kênh, giữ nguyên chồng lấn**.

Đó chính là chỗ chi phí chuyển từ "người gán nhãn" sang "buổi thu". Tiêu chí (4) của §7 được thoả
mãn; ràng buộc thật nằm ở chỗ khác.

### 3.2 Số giờ có nguồn, cho từng hướng

Hai bài VAP công bố số cụ thể. Đây là những con số duy nhất trong tài liệu này về "bao nhiêu giờ
để huấn luyện VAP", và chúng đến từ chính tác giả.

**Ekstedt & Skantze 2022 (arXiv 2205.09812, §4):** huấn luyện trên Switchboard, 2.438 hội thoại,
loại 98 hội thoại có hơn hai người nói, giữ 135 hội thoại làm test, còn 2.205 hội thoại chia
k-fold 11 lần thành cặp train/val 2000/205. Âm thanh cắt thành đoạn 10 giây chồng lấn 2 giây.
Switchboard-1 Release 2 (LDC97S62) tổng khoảng 259,1 giờ (số này lấy từ bài LREC-COLING 2024 bên
dưới), nên 2.205/2.438 hội thoại ≈ **234 giờ**.

**Inoue, Jiang, Ekstedt, Kawahara & Skantze, *Multilingual Turn-taking Prediction Using Voice
Activity Projection*, LREC-COLING 2024, trang 11873–11883** —
<https://aclanthology.org/2024.lrec-main.1036.pdf>. §3 ghi rõ từng bộ:

| Ngôn ngữ | Corpus | Tổng | Sau khi cân bằng để so sánh công bằng |
|---|---|---|---|
| English | Switchboard | 2.438 hội thoại, ~259,1 giờ (train 1.950 = 218,7 giờ) | **train 92,5 giờ / val 11,5 giờ** |
| Mandarin | HKUST Mandarin Telephone Speech | 867 hội thoại, ~148,6 giờ (train 758 = 130,1 giờ) | **train 92,5 giờ / val 11,5 giờ** |
| Japanese | Travel Agency Task Dialogues | 329 hội thoại, 115,5 giờ | **train 263 hội thoại = 92,5 giờ / val 33 = 11,5 giờ** |

**Tiếng Việt không có trong bài.** Ba ngôn ngữ, hết. Bài chọn ba họ ngôn ngữ khác nhau (Germanic,
Sino-Tibetan, Japonic) *"since they represent three different language families ... and therefore
should exhibit a certain level of diversity"*.

Kiến trúc, để biết chi phí: đầu vào **stereo**, mỗi kênh một người, tối đa 20 giây, 16 kHz, tốc
độ khung **50 Hz**. Encoder CPC (5 lớp CNN + 1 GRU, tiền huấn luyện trên LibriSpeech) **đóng
băng**; phần huấn luyện là 1 lớp self-attention Transformer dim 256 mỗi kênh + 3 lớp
cross-attention dim 256, 4 đầu, dropout 0,1; 20 epoch, batch 8, lr 3,63e-4, AdamW.

Một chi tiết đáng giá cho dự án: bài nói thẳng rằng khi **bỏ đóng băng** encoder thì cả CPC lẫn
MMS đều **giảm** độ chính xác, và *"Given the current size of the training dataset, there is a
possibility that the model is overfitting."* Tức 92,5 giờ **không** phải ngưỡng tối thiểu đã đo
được — nó là con số chọn để ba bộ bằng nhau, và ở mức đó mô hình đã có dấu hiệu quá khớp khi mở
thêm tham số. Ngưỡng tối thiểu thật: **chưa ai công bố** (§8).

### 3.3 Bảng vai trò dữ liệu

| Hướng `SPEC.md` §7 | Vai trò của dữ liệu đóng vai | Số giờ có nguồn | Nguồn |
|---|---|---|---|
| Ngưỡng im lặng có tinh chỉnh (B1) | **Evaluation + sweep.** Không có tham số học; `configs/baseline/` quét 11 giá trị | vài giờ đủ vẽ đường cong hai trục | `SPEC.md` §9.3 quy tắc 2; `docs/progress.md` §2.1 |
| Dự đoán liên tục từ âm thanh — **VAP từ đầu** | **Training** (bắt buộc hai kênh) | **92,5 giờ/ngôn ngữ** (Inoue 2024) hoặc ~234 giờ (Ekstedt 2022) | hai bài trên |
| VAP — **tinh chỉnh từ checkpoint có sẵn** | Fine-tuning | **không có số công bố** — chưa ai công bố thí nghiệm thêm ngôn ngữ thứ tư vào mô hình VAP đa ngữ | §8, câu U6 |
| B2 `smart-turn` — **nguyên trọng số** | **Evaluation-only.** 0 giờ huấn luyện | 0 | `SPEC.md` R8 |
| B2 — tinh chỉnh trên dữ liệu đóng vai (GĐ 3 bước 2) | Fine-tuning | không công bố mức tối thiểu; tập train của họ 270.429 mẫu / 36,8 GB | dataset card HF |
| B3 `Namo` — **nguyên trọng số** | **Evaluation-only.** 0 giờ huấn luyện | 0 | `SPEC.md` R8 |
| Kết hợp nhiều tín hiệu, cho bỏ phiếu trắng | **Calibration / chọn ngưỡng.** Đặc trưng thiết kế tay, tham số học ít | vài giờ, nhưng phải đủ **số người nói** để chia theo người nói | `.claude/rules/training.md` |

Đọc thẳng bảng này: **ba trong bốn hướng của §7 không cần dữ liệu huấn luyện nào cả.** Chỉ hướng
VAP-từ-đầu cần, và nó cần gấp khoảng mười lần những gì một giai đoạn thu đóng vai làm nổi.

Phép tính minh hoạ, giả định nêu rõ: 92,5 giờ = 5.550 phút. Với buổi đóng vai 10 phút một hội
thoại, đó là **555 hội thoại**. Ba con số đầu vào (thời lượng buổi, tỉ lệ dùng được, số người
tham gia) đều là giả định để minh hoạ bậc độ lớn.

---

## 4. Corpus tiếng Việt công khai — tra từ nguồn gốc

Tiêu chí quyết định, nói trước để đọc bảng cho nhanh: **chỉ corpus hội thoại có kênh tách riêng
cho từng người nói mới sinh được nhãn turn-taking.** Corpus đọc câu (read speech) không sinh được
nhãn nào cả — không phải "kém hơn", mà là **không có**. Corpus hội thoại đơn kênh đã cắt thành
phát ngôn cũng vậy: ranh giới lượt và chồng lấn đã bị bước cắt cho ASR xoá mất.

### 4.1 Bảng ứng viên

| Corpus | Host / URL | Giờ | Người nói | Giấy phép (nguyên văn) | Hai kênh? | Chồng lấn / tiếng đệm / ngừng tự nhiên | Điện thoại? | Dùng cho `turn` được không |
|---|---|---|---|---|---|---|---|---|
| **VIVOS** | `AILAB-VNUHCM/vivos` <https://huggingface.co/datasets/AILAB-VNUHCM/vivos> | 15 | 65 (46 train / 19 test) | "Public Domain, Creative Commons Attribution NonCommercial ShareAlike v4.0 (CC BY-NC-SA 4.0)" | Không | Không có gì cả | Không | **Không.** "speakers were asked to read one sentence at a time" — đọc câu rời trong phòng yên tĩnh |
| **Common Voice `vi`** (cv-corpus-26.0, 2026-06-12) | `common-voice/cv-dataset` <https://raw.githubusercontent.com/common-voice/cv-dataset/main/datasets/scripted-speech/cv-corpus-26.0-2026-06-12.json> | **22,96 tổng / 7,80 đã thẩm định** | 417 `users` | CC0 | Không | Không | Không | **Không.** 20.599 clip, trung bình 4,013 giây/clip, câu đọc rời |
| **Common Voice Spontaneous Speech** v4.0 (2026-06-12) | cùng repo, thư mục `spontaneous-speech` | 515 tổng / 273 thẩm định, 78 ngôn ngữ | 2.105 người | CC0 | Không | Không | Không | **Không — và không có `vi`.** Đã kiểm bằng cách nạp `sps-corpus-4.0-2026-06-12.json`: khoá `vi` không tồn tại trong 78 locale. Ngoài ra modality này là trả lời câu hỏi mở một mình, không phải đối thoại |
| **FPT Open Speech (FOSD)** | Mendeley Data, DOI `10.17632/k9sxg2twv4.4` <https://data.mendeley.com/datasets/k9sxg2twv4/4> | **~30** (bản ghi Mendeley), 25.921 mẫu | không nêu | CC BY 4.0 | Không | Không | Không | **Không.** mp3 phát ngôn rời. *Con số "100 giờ" lưu truyền rộng rãi không khớp bản ghi Mendeley — xem §8* |
| **VLSP / VinBigdata-VLSP2020-100h** | <https://vlsp.org.vn/resources> | ~100 công khai (≈20 đọc + ≈80 tự phát) | không công bố | **Không công bố trên trang.** Truy cập bằng cách tải mẫu đơn, ký, gửi email `vlsp.resources@gmail.com` | Không | Không giữ ranh giới lượt | Không | **Không.** Phát ngôn ASR đơn kênh |
| **BUD500** | `linhtran92/viet_bud500` | ~500 | — | CC-BY-NC-SA-4.0 | Không | Không | Không | **Không** (dẫn lại `reuse-audit.md` §4, chưa tra lại ngày 2026-09-12) |
| **VietMed** | `leduckhai/VietMed` <https://huggingface.co/datasets/leduckhai/VietMed> | 16 có nhãn + 1.000 không nhãn y tế + 1.200 không nhãn phổ thông | "13 values" cho tên người nói ở subset train | `mit` (trường licence của card) | Không nêu | Nội dung *là* hội thoại y tế, nhưng đã cắt thành phát ngôn 1–13 giây | Không | **Không.** Không có kênh riêng, không có nhãn lượt. Nguồn âm thanh và tình trạng đồng ý **không nêu** ở card, README GitHub hay abstract — cờ đỏ với `SPEC.md` §6, xem §8 |
| **VietSuperSpeech** | `thanhnew2001/VietSuperSpeech` | **~103,18 / 67.405 mẫu** (card HF) — abstract arXiv 2603.01894 nói 267,39 giờ / 52.023 cặp | — | `mit` (card HF) | Không | Không có nhãn turn-taking, chồng lấn hay diarization | Không (YouTube độc thoại/vlog) | **Không.** *Trả lời câu hỏi 9 ở §10 của `reuse-audit.md`: giấy phép là MIT. Kèm một mâu thuẫn số liệu, xem §8* |
| **GigaSpeech 2** | `speechcolab/gigaspeech2` | Vietnamese **6.000** (bản refined) | — | "Researcher shall use the Database only for **non-commercial research and educational purposes**" | Không — "Channels: 1", 16 kHz | Không | Không (YouTube) | **Không.** Đoạn phát ngôn đơn kênh, phiên âm tự động |
| **YODAS / YODAS2** | `espnet/yodas` | `vi000` 779,854 · `vi100` 4.963,77 · `vi101` 4.239,37 | — | `cc-by-3.0` | Không nêu | Không có nhãn người nói / lượt | Không (YouTube) | **Không.** Phát ngôn + phụ đề, không diarization |
| **MLS** | `facebook/multilingual_librispeech` | — | — | CC-BY-4.0 | — | — | — | **Không có tiếng Việt.** 8 ngôn ngữ, đều là sách nói đọc |
| **VoxPopuli** | `facebook/voxpopuli` | — | — | CC0 | — | — | — | **Không có tiếng Việt.** 18 ngôn ngữ EU, họp Nghị viện châu Âu |
| **Emilia / Emilia-YODAS** | `amphion/Emilia-Dataset` | — | — | CC-BY-NC (Emilia) / CC-BY (Emilia-YODAS) | — | — | — | **Không có tiếng Việt.** en, zh, de, fr, ja, ko |
| **CALLFRIEND Vietnamese** | LDC **LDC96S60**, DOI `10.35111/0m20-qn97` <https://catalog.ldc.upenn.edu/LDC96S60> | **~25** (60 hội thoại, mỗi cuộc 5–30 phút) | 60 cuộc, 100 người gọi được tuyển | "LDC User Agreement for Non-Members" — phí ẩn sau đăng nhập | **CÓ.** Trường `Sample Type` nguyên văn: **"2-channel ulaw"**, `Sample Rate: 8000`, `Data Source(s): telephone conversations` | **Có** — hội thoại điện thoại tự do, không kịch bản | **Có** | **Về mặt kỹ thuật: CÓ.** Về mặt `SPEC.md` §6: xem §4.2 |
| **IARPA Babel Vietnamese** | LDC **LDC2017S01**, DOI `10.35111/yrqp-r555` <https://catalog.ldc.upenn.edu/LDC2017S01> | **~201** (hội thoại + có kịch bản), thu 2012 tại Việt Nam, 4 vùng phương ngữ, tuổi 16–64 | không nêu trên trang | Ba bản thoả thuận: For-Profit / Not-For-Profit / Non-Member — phí ẩn sau đăng nhập | **Chưa xác định.** Trường `Sample Type` chỉ ghi `a-law`, không ghi "2-channel" — nhưng trường này không tin được (xem §8, U1) | Có (điện thoại thật, nhiều môi trường) | **Có** | **Chưa kết luận được** — phụ thuộc câu hỏi kênh |
| **ELRA-S0432** "Vietnamese Speech Data by Mobile Phone" | <https://catalog.elra.info/en-us/repository/browse/ELRA-S0432/> | 760 | 1.751 (778 nam / 973 nữ) | "Commercial Use - ELRA VAR"; **giá nghiên cứu €122.740,00** | Không — "16kHz, 16bit, wav, **mono channel**" | Không — nội dung do nhà ngôn ngữ học soạn sẵn | Điện thoại di động nhưng đọc theo prompt | **Không** |
| **ELRA-U-S 0090** "Vietnamese Telephone Speech Corpus" | `universal.elra.info` | không rõ | không rõ | không rõ | không rõ | không rõ | Có | **Chưa kiểm chứng được** — máy chủ từ chối kết nối ngày 2026-09-12 (§8, U9) |
| **Nexdata 500h VN Conversational · DataoceanAI 213h** | thương mại | 500 / 213 | — | phải mua | không công bố | — | — | **Không dùng được** (dẫn lại `reuse-audit.md` §4) |

Mốc so sánh, không phải ứng viên: **SpokenWOZ** (<https://spokenwoz.github.io/>) — 5,7 nghìn hội
thoại, **249 giờ**, người-với-người, CC BY-NC 4.0, tiếng Anh. Đây là corpus mà bài endpoint
anticipation 2026 dùng (§6.2), và nó là mốc để thấy một corpus hội thoại *có kịch bản nghiệp vụ,
có âm thanh* trông như thế nào ở quy mô thật.

### 4.2 Khẳng định "không có corpus hai kênh tiếng Việt công khai" cần sửa một chữ

`docs/roadmap.md` §5 viết: *"không có corpus hội thoại hai kênh tiếng Việt công khai. VIVOS, VLSP,
BUD500 đều đơn kênh. Nếu chọn hướng VAP thì bắt buộc tự thu — đó là ràng buộc thật, không phải một
lựa chọn còn để ngỏ."* `reuse-audit.md` §5 xác nhận lại, và §10 câu 8 tự ghi: *"Chưa tra: ...
catalog LDC ở mức chi tiết từng mục."*

**Đã tra. Có một corpus.** `LDC96S60` — CALLFRIEND Vietnamese, Canavan & Zipperlen, 1996 — là 60
cuộc gọi điện thoại không kịch bản giữa người nói tiếng Việt bản ngữ, ~25 giờ, **ghi 2 kênh ulaw
8 kHz**. Tài liệu `CF_VIE.TXT` của chính LDC ghi: *"All speakers were aware that they were being
recorded. They were given no guidelines concerning what they should talk about."* và *"The call
was allowed only if both parties agreed to being recorded."* Người tham gia được tuyển qua
internet, quảng cáo, quan hệ cá nhân, và nhận 20 USD.

Bốn điều phải nói ngay, để không ai đọc phát hiện này rộng hơn nó thật sự là:

1. **Nó không miễn phí và không "công khai" theo nghĩa tải về được.** Giấy phép là "LDC User
   Agreement for Non-Members", phí không hiển thị nếu chưa đăng nhập. Câu ở roadmap nên đọc là
   *"không có corpus hội thoại hai kênh tiếng Việt **tải công khai miễn phí**"* — chứ không phải
   *"không tồn tại"*.
2. **25 giờ < 92,5 giờ.** Kể cả mua được, nó vẫn thiếu so với mức mà bài VAP đa ngữ dùng. Kết
   luận vận hành của roadmap — *hướng VAP đòi phải tự thu* — **vẫn đứng**, nhưng vì lý do khác:
   không phải "không tồn tại" mà là "tồn tại, không đủ, sai miền, và vướng §6".
3. **Sai miền.** 1996, người Việt ở Mỹ và Canada, nói chuyện phiếm với bạn bè, không kịch bản,
   không nghiệp vụ, không có nhãn sự kiện lượt nói. Năm luồng nghiệp vụ NetCo không có ở đó.
4. **Vướng `SPEC.md` §6, và đây là quyết định của bạn, không phải của tài liệu này.** §6 viết:
   *"Chỉ dùng hội thoại đóng vai theo kịch bản, có đồng ý. Không dùng ghi âm cuộc gọi thật của
   khách hàng bất kỳ công ty nào."* CALLFRIEND và Babel **không** vi phạm câu thứ hai — chúng
   không phải cuộc gọi khách hàng của công ty nào. Nhưng chúng **cũng không** là "đóng vai theo
   kịch bản", nên chúng vi phạm câu thứ nhất theo đúng câu chữ. Hai lối đọc, cả hai đều hợp lý,
   và chọn lối nào là một ADR:
   - (a) §6 là quy tắc về **dữ liệu của sản phẩm**, và corpus nghiên cứu công khai có đồng ý nằm
     ngoài phạm vi câu đó;
   - (b) §6 là quy tắc tuyệt đối về **mọi** âm thanh dự án chạm tới, và LDC bị loại.

### 4.3 Toàn bộ dữ liệu tiếng Việt của `smart-turn` là giọng tổng hợp

`reuse-audit.md` §10 câu 1 gọi đây là *"câu hỏi đáng đầu tư nhất còn lại"*: bao nhiêu phần trong
1.004 mẫu tiếng Việt của benchmark là TTS? Và ghi rằng *"Phải tải 38,5 GB parquet mới đếm được."*

Không phải. Đếm được bằng API, và câu trả lời là **100%**.

Cách đếm, để tái lập được:

```
https://datasets-server.huggingface.co/statistics
    ?dataset=pipecat-ai/smart-turn-data-v3.2-test&config=default&split=train
https://datasets-server.huggingface.co/filter
    ?dataset=pipecat-ai/smart-turn-data-v3.2-test&config=default&split=train
    &where="language"='vie' AND "synthetic"=true
```

Kết quả, ngày 2026-09-12:

| Đại lượng | Giá trị |
|---|---|
| `num_examples` của `smart-turn-data-v3.2-test` | **31.527**, `partial: false` (tức đếm trên **toàn bộ** tập, không phải mẫu) |
| `language == 'vie'` | **1.004** |
| `language == 'vie' AND synthetic == true` | **1.004** |
| `language == 'vie' AND synthetic == false` | **0** |
| Trường `dataset` của mọi hàng `vie` xem được | `chirp3_2` |
| Toàn tập: `synthetic == false` | 5.863 / 31.527 = **18,6%** |

Con số 31.527 và 1.004 khớp **chính xác** với bảng benchmark
`benchmarks/smart-turn-v3.2-cpu.md` mà `reuse-audit.md` §3.1 đã trích. Nên đây đúng là tập test
sinh ra con số 79,38% cho tiếng Việt.

Kiểm chéo trường `synthetic` bằng trường `dataset`, để chắc `synthetic` nghĩa là "TTS" chứ không
phải thứ khác: trên tập train v3.1, tổng các nguồn `chirp3_1 + chirp3_2 + orpheus_grammar_1 +
orpheus_midfiller_1 + orpheus_endfiller_1 + rime_2` = 31.947, **bằng đúng** số hàng
`synthetic == true`; tổng `liva_1 + midcentury_1 + human_5 + mundo_1 + human_convcollector_1` =
6.690, **bằng đúng** số hàng `synthetic == false`. Chirp3, Orpheus và Rime đều là hệ TTS. Vậy
`synthetic == true` ⇔ giọng máy.

Trên **tập train** `smart-turn-data-v3.1-train`, chỉ số của datasets-server chỉ phủ 38.637 trong
270.429 hàng (phần parquet đầu ~5 GB). Trong phần phủ được: `vie` = 1.152, và `vie AND
synthetic=true` = **1.152**, `vie AND synthetic=false` = **0**. Không kết luận được cho 86% còn
lại (§8, U5) — nhưng trong toàn bộ phần đo được, mô hình B2 **chưa từng nghe một người Việt nào
nói**.

**Hệ quả, và nó đi ngược cách `reuse-audit.md` §3.1 đọc con số 79,38%:**

- Điểm 1 của `reuse-audit.md` §3.1 viết: *"Củng cố tiền đề. Giả thuyết 'ngôn ngữ thanh điệu khác'
  ở `SPEC.md` §7 giờ có một quan sát độc lập đứng sau, do chính tác giả mô hình công bố."*
  **Câu này phải rút lại.** 79,38% là điểm số trên giọng Chirp3 đọc tiếng Việt. Nó nói về ngữ
  điệu của một hệ TTS, không nói về ngữ điệu của người Việt. Nó **không** là quan sát độc lập về
  thanh điệu.
- Điểm 2 và 3 của §3.1 **không bị chạm tới**, và còn mạnh lên: số baseline vẫn phải do nhóm tự
  đo, và chỗ trống vẫn trống.
- Thêm một khoảng trống **mới, cụ thể hơn, và đo được**: endpointer đa ngữ phổ biến nhất hiện nay
  công bố hỗ trợ tiếng Việt mà tập huấn luyện lẫn tập đánh giá tiếng Việt của nó đều là giọng
  máy. Đó là một phát biểu kiểm chứng được, và §6.4 đề nghị một phép đo rẻ để khai thác nó.

---

## 5. Phán quyết về dữ liệu

### 5.1 Trả lời trực tiếp

**Dữ liệu đóng vai tự thu phải là (i) đánh giá + (ii) hiệu chỉnh/tinh chỉnh nhỏ trên trọng số có
sẵn — chứ không phải tập huấn luyện.** Và **không có dữ liệu công khai nào đứng ra huấn luyện
thay được**, vì:

- Mọi corpus tiếng Việt miễn phí đều đơn kênh, đã cắt thành phát ngôn cho ASR: không sinh được
  nhãn VAP, không có ranh giới lượt, không giữ chồng lấn. Không phải "ít nhãn" mà là **không có
  nhãn nào để sinh**.
- Corpus hai kênh duy nhất tra được (LDC96S60, 25 giờ) nhỏ hơn mức tham chiếu 92,5 giờ, sai miền
  hai mươi năm, và vướng cách đọc chặt của `SPEC.md` §6.
- Ba trong bốn hướng ở §7 **không cần** dữ liệu huấn luyện nào (§3.3). Hướng thứ tư cần nhiều hơn
  khả năng thu của một giai đoạn đóng vai khoảng một bậc độ lớn.

Điều đó **khớp** với `docs/roadmap.md` §6 GĐ 1, vốn đã viết: *"Mục tiêu **không phải** xây một
corpus để phát hành. Mục tiêu là đủ dữ liệu để (a) đo được ba baseline một cách trung thực, (b) vá
được chỗ hỏng tìm thấy ở GĐ 2, và (c) chạy được năm phép thử ở GĐ 4."* Ba mục đích đó đều là
**đánh giá và hiệu chỉnh**, không phải huấn luyện. Tài liệu này chỉ bổ sung số liệu để câu đó có
cơ sở định lượng thay vì là một lựa chọn phong cách.

### 5.2 Chỗ duy nhất dữ liệu tự thu đóng vai trò huấn luyện

Có hai chỗ, cả hai đều nhỏ và cả hai đều nằm ở GĐ 3 theo đúng thứ tự rẻ-trước của `roadmap` §6:

1. **Scorer đặc trưng thủ công** (scorer thanh điệu, scorer phân biệt "dạ") — đặc trưng do người
   thiết kế, tham số ít, học được từ vài giờ. Đây là *calibration*, không phải *training* theo
   nghĩa cần GPU.
2. **Tinh chỉnh B2 trên dữ liệu đóng vai** — hợp pháp với `smart-turn` (BSD-2-Clause) và
   `Namo` (Apache-2.0). **Không hợp pháp với trọng số MaAI** — xem §7, mâu thuẫn C3.

Cả hai đều phải tuân `.claude/rules/training.md`: chia **theo người nói**, không theo phát ngôn;
chuẩn hoá F0 **theo từng người** trước khi gộp; seed ghi vào output của lần chạy chứ không chỉ vào
config; không đọc `data/holdout/` kể cả để "nhìn một file".

### 5.3 Cần bao nhiêu giờ — suy từ chỉ số, không từ mô hình

Cách đúng để ra con số này là hỏi **chỉ số chính cần bao nhiêu sự kiện**, không phải hỏi mô hình
cần bao nhiêu dữ liệu — vì theo §5.1 dự án không huấn luyện mô hình lớn nào.

Giả định nêu rõ, cả bốn đều là giả định:

- **G1.** Chỉ số chính (`.claude/rules/evaluation.md`, "The headline metric") là tỉ lệ lỗi tách
  theo thanh điệu âm tiết cuối: **6 thanh + UNKNOWN**.
- **G2.** Để một ô có khoảng tin cậy đọc được chứ không phải nhiễu, cần cỡ **100 sự kiện kết
  thúc lượt mỗi thanh** → 6 × 100 = **600 sự kiện** cho tập đánh giá.
- **G3.** Mật độ lượt: SpokenWOZ có 203.000 lượt trên 249 giờ ≈ **815 lượt/giờ** hội thoại hai
  bên có nghiệp vụ. Lấy nửa làm số ranh giới đổi người → cỡ **400 sự kiện/giờ**. Đây là số của
  tiếng Anh, miền khác; dùng làm bậc độ lớn, không phải hằng số.
- **G4.** Bốn hành vi ở `SPEC.md` §4.3 (ngập ngừng, tiếng đệm, nói đè, trả lời ngắn) **hiếm nếu
  để tự nhiên**, nên kịch bản phải ép chúng xuất hiện. Điều đó làm mật độ sự kiện *hữu ích* cao
  hơn G3, nhưng cũng làm mỗi buổi thu dài hơn.

Ra số:

| Tập | Mục đích | Sự kiện cần | Giờ (ở 400 sự kiện/giờ) |
|---|---|---|---|
| **validation** | quét B1, chốt ngưỡng, chọn hướng ở GĐ 2, ablation ở GĐ 3 | ~600 | ~1,5 |
| **train (nhỏ)** | hiệu chỉnh scorer, tinh chỉnh B2 nếu chọn | ~1.200 | ~3 |
| **holdout** | mở **đúng một lần** ở GĐ 5 | ~600 | ~1,5 |
| dự phòng: hỏng băng, nhiễu, người nói rút lui, thu lại | | | ~×1,5 |
| **Tổng** | | | **~9 giờ, khoảng 6–12** |

Ràng buộc thứ hai, và nó **chặt hơn số giờ**: `.claude/rules/training.md` bắt chia theo **người
nói**. Ba tập rời nhau về người nói, mỗi tập cần đủ người để con số không phải là mô tả của hai
giọng. Lấy tối thiểu 8 người mỗi tập → **≥ 24 người nói**, và nên nhắm 30 để còn chỗ loại. Với
hội thoại hai bên, đó là ≥ 12–15 cặp.

**So sánh để thấy khoảng cách:** 9 giờ so với 92,5 giờ của một mô hình VAP đơn ngữ. Tỉ số ~10
lần. Đó là toàn bộ lý do §5.1 kết luận như vậy, phát biểu bằng một con số thay vì bằng lời.

### 5.4 Ba điều phải làm đúng ngay từ buổi thu đầu tiên

Không phải khuyến nghị phong cách — cả ba đều là thứ sửa sau thì phải thu lại từ đầu.

1. **Thu hai kênh, tách kênh vật lý, không trộn.** Kể cả khi phương pháp cuối không phải VAP.
   Nhãn VAP, nhãn chồng lấn, nhãn tiếng đệm, và cả phép đo R5 ("bot không nhận nhầm tiếng của
   chính nó") đều cần biết mẫu nào của ai. `docs/progress.md` §4 đã ghi rằng `WavFrameSource` hiện
   **từ chối file nhiều kênh** và rằng `FeatureFrame` mang đúng một mảng mẫu — tức seam phải đổi
   trước khi dữ liệu về, không phải sau.
2. **Chép sẵn định dạng nhãn của VAP**, như `reuse-audit.md` §5 đã đề nghị: `waveform (B, 2, n)`
   + `vad (B, n_frames + horizon, 2)` ở 50 Hz, chân trời 2 giây. Miễn phí ở GĐ 1, đắt ở GĐ 3.
3. **Ghi metadata người nói ngay lúc thu**: id người nói, giới, vùng phương ngữ (bốn vùng, theo
   đúng cách tài liệu Babel `LSP_107_final.pdf` phân: Northern / North-central / Central /
   Southern). Không có id người nói thì không chia theo người nói được, và lỗi đó **không để lại
   dấu vết nào trong chỉ số** — đúng cảnh báo của `roadmap` §6 GĐ 1.

---

# PHẦN B — Phương pháp

## 6. Đã chốt method chưa?

### 6.1 Trả lời trực tiếp: **chưa** — và đây là danh sách cái *đã* chốt

Đọc cả năm file trong `docs/adr/` ngày 2026-09-12. **Không ADR nào chọn một trong bốn hướng của
`SPEC.md` §7.** Cả năm đều chốt *seam, hợp đồng, quy trình, và khung diễn giải* — không chốt
phương pháp.

| ADR | Chốt cái gì | Có phải chọn method không |
|---|---|---|
| 0001 | Định dạng và quy trình ADR | Không |
| 0002 | R8 nâng lên **ba** baseline; đặt tên cụ thể B2 = `smart-turn` v3.2, B3 = `Namo-...-Vietnamese`; thu hẹp phát biểu đóng góp còn **bốn** chỗ trống; **phát biểu lại** giả thuyết §7 | Không — nó chốt *cái để so*, không chốt *cái để làm* |
| 0003 | Seam ngoài của tầng `turn` là **quyết định lượt nói**, không phải thành phần chấm điểm; bốn adapter sau một interface; quyết định là **giá trị trả về**; telemetry ghi ở **đúng một chỗ** | Không |
| 0004 | `Prediction` hai giá trị `END_OF_TURN` / `BACKCHANNEL`; `score() -> float \| None` với `None` = **bỏ phiếu trắng**; `decide()` trả ở **mọi** khung; `reset()` trên cả hai protocol; khởi tạo tốn kém được phép, `decide()` thì không | Không |
| 0005 | Đây là **nghiên cứu ứng dụng**; sản phẩm là bản mô phỏng; **thích ứng trước, tự dựng sau** | Không — nhưng nó ràng buộc *thứ tự* xét |

Thêm bảy quyết định kỹ thuật ở `docs/progress.md` §3 (cổng năng lượng cho B1, kích thích tổng hợp
ở GĐ 0, ngân sách khung suy từ hệ số thời gian thực, registry theo config, mốc nhận lượt là cuối
khung, khung cuối mang `padded_samples`, telemetry một chỗ) — cũng không cái nào chọn method.

`docs/roadmap.md` §5 nói thẳng: *"Bốn hướng ở `SPEC.md` §7, chọn sau Giai đoạn 2 dựa trên số đo,
ghi vào `docs/adr/`."* Đó vẫn là trạng thái hiện tại.

**Một cam kết mềm cần gọi tên, vì nó không có trong ADR nào nhưng đã có trong code.** ADR-0003
liệt kê `fused.py` là *"Hệ đề xuất — dùng `scorers/` và `fusion.py`"*, và ADR-0004 dựng ngữ nghĩa
bỏ phiếu trắng cùng hai ngưỡng riêng (`take_threshold`, `backchannel_threshold`) — tức toàn bộ bộ
máy của **hướng thứ tư (kết hợp nhiều tín hiệu)** đã được xây sẵn. Điều đó không *chọn* hướng thứ
tư, nhưng nó làm hướng thứ tư rẻ nhất để làm và ba hướng kia đắt hơn để thay vào. Nếu GĐ 2 kết
luận "ship B2 nguyên trọng số" (một trong ba kết cục hợp lệ ở `roadmap` §6 GĐ 2), thì `fusion.py`
là công sức bỏ đi — và đó là một đánh đổi có thật, đáng ghi vào ADR chốt hướng chứ không nên để
lộ ra sau.

### 6.2 Hiện trạng nguồn gốc của bốn hướng

**(1) Ngưỡng im lặng có tinh chỉnh (B1).** Đã đo xong ở GĐ 0. `docs/progress.md` §2.1: quét 11
ngưỡng 200–1200ms trên 5 kịch bản; hẹp thì cắt lời 25%, rộng thì hết cắt lời nhưng đáp chậm thêm
nửa giây, quá 900ms thì có kịch bản bot không đáp; cột tiếng đệm nhận nhầm **100% ở mọi ngưỡng**.
Chi phí: trung vị 0,0072 ms/khung, ~1/1000 ngân sách. Đánh giá theo bốn tiêu chí §7: (1) đạt tuyệt
đối, (2) giải thích được tuyệt đối, (3) không có gì để ablation, (4) không cần nhãn. **Và đã được
đo là không thắng được** — đó là luận điểm trung tâm của `SPEC.md` §1, giờ có số đứng sau.

**(2) Dự đoán liên tục từ âm thanh.** Ba nhánh, khác nhau rất xa, và `SPEC.md` §7 gộp cả ba vào
một dòng:

| Nhánh | Trạng thái ngày 2026-09-12 | Chặn ở đâu |
|---|---|---|
| VAP gốc `ErikEkstedt/VoiceActivityProjection` | MIT. Có checkpoint mẫu `VAP_3mmz3t0u_50Hz_ad20s_134-epoch9-val_2.56.pt`. Đầu vào **stereo**; nếu đưa mono thì *"we automatically add a silent channel as speaker 2"*. Huấn luyện trên Switchboard / Fisher / Candor — README tự nói là không mở. Hướng dẫn cài vẫn `cudatoolkit=11.6`, **không có phát biểu nào về CPU** | Không có trọng số tiếng Việt; chưa biết chạy CPU nổi không |
| `MaAI-Kyoto/MaAI` | Mã MIT. **Trọng số thì không**: mọi model `vap_*` là **CC-BY-NC-ND-4.0**, trừ `vap_tri` (CC-BY-NC-SA-4.0) và `vap_bc_*` (MIT). Ngôn ngữ nay gồm `vap_en`, `vap_jp`, `vap_ch`, `vap_fr`, `vap_ca`, `vap_tri` — **vẫn không có tiếng Việt**. Có bản **đơn kênh** (`vap_mc_*`). `vap_en` sửa lần cuối 2026-09-11 | **ND cấm tạo bản phái sinh** → không tinh chỉnh sang tiếng Việt được. Xem §7 C3 |
| `smart-turn` v3.2 (B2) | BSD-2-Clause, 8M tham số, ONNX int8 8 MB. **Không phải VAP**: nó là bộ phân loại **một đoạn** ≤ 8 giây, 16 kHz **mono**, kích hoạt bởi một VAD bên ngoài (`reuse-audit.md` §4.1). Tác giả nói *"Runs in as little as 10ms on some CPUs, and under 100ms on most cloud instances"* | Dữ liệu tiếng Việt 100% là TTS (§4.3) |

Bài endpoint anticipation 2026 mà `SPEC.md` §12 dẫn — Udupa, Watanabe, Schwarz, Černocký,
<https://arxiv.org/html/2606.13450> — huấn luyện và đánh giá trên **SpokenWOZ** và **Switchboard**,
cả hai 8 kHz, cả hai tiếng Anh. Dự đoán trước tới 2,56 giây; hệ Unmute từ 1.195ms xuống 690ms,
giảm 505ms. Bài không nhắc tới ngôn ngữ thanh điệu hay tiếng Việt, và không phát biểu gì về CPU.

**(3) Dựa vào tính trọn vẹn của câu (B3).** Tra Hugging Face Hub API ngày 2026-09-12 với hai truy
vấn (`search=turn-detector` giới hạn 50 kết quả, và `search=Vietnamese turn`):
**`videosdk-live/Namo-Turn-Detector-v1-Vietnamese` là model duy nhất trả về có tiếng Việt.** 38
lượt tải. Apache-2.0. `distilbert-base-multilingual-cased`, `model.onnx` +
`model_quant.onnx`, kèm `tokenizer.json` và `vocab.txt` — tức **cần thêm một phụ thuộc tokenizer**,
đúng như `reuse-audit.md` §9.1 đã cảnh báo. Độ trễ của nó bị **độ trễ ASR chi phối**, và
`.claude/rules/evaluation.md` bắt: *"B3's numbers are meaningless without the ASR latency that fed
it — report them together."*

**(4) Kết hợp nhiều tín hiệu, cho bỏ phiếu trắng.** Không có mô hình ngoài nào để so; đây là chỗ
dự án tự dựng. Seam đã có (ADR-0003), hợp đồng đã có (ADR-0004), ngữ nghĩa bỏ phiếu trắng đã có.
Chi phí dữ liệu: **hiệu chỉnh, không huấn luyện**.

### 6.3 Chấm bốn hướng theo bốn tiêu chí xếp hạng của `SPEC.md` §7

Thang: ✓✓ đạt chắc chắn có bằng chứng · ✓ nhiều khả năng đạt · ? chưa biết · ✗ không đạt.

| Hướng | (1) Thời gian thực trên laptop | (2) Giải thích được khi báo sai | (3) Ablation từng phần | (4) Không cần gán nhãn tay quy mô lớn | Cái chưa biết thật sự |
|---|---|---|---|---|---|
| Ngưỡng im lặng | ✓✓ đo rồi: 0,0072 ms/khung | ✓✓ một biến | ✗ không có phần nào để tắt | ✓✓ | Không còn gì — đã đo |
| VAP tự dựng | ? — chưa nguồn nào công bố hệ số thời gian thực trên CPU cho VAP | ✓ có đường xác suất theo thời gian | ✓ tắt được nhánh kênh, tắt được encoder | ✓✓ nhãn tự sinh — **nhưng đòi 92,5 giờ hai kênh** | Ngưỡng dữ liệu tối thiểu; CPU; chưa có trọng số tiếng Việt nào |
| B2 `smart-turn` nguyên trọng số | ✓ tác giả nói 10–100ms, nhưng **dồn cục**: chạy một lần trên đoạn ≤8s, không phải mỗi khung → `budget_per_frame_ms: 5.0` phải đọc là **trung bình** | ? hộp đen, không có điểm thành phần | ✗ một khối | ✓✓ 0 giờ | Chi phí đỉnh thật; chất lượng trên người Việt thật (dữ liệu của họ là TTS) |
| B3 `Namo` trên văn bản ASR | ✓ tác giả nói <13ms — **cộng độ trễ ASR**, là phần lớn | ✓✓ đọc được văn bản mà nó quyết định | ✗ một khối | ✓✓ 0 giờ | Tổng độ trễ thật; ASR sai chữ thì sai thanh |
| Kết hợp nhiều tín hiệu | ✓ tuỳ scorer; ngân sách còn dư ~1000 lần sau B1 | ✓✓ `TurnDecision.scores` mang điểm từng nguồn + ai bỏ phiếu trắng | ✓✓ đúng thứ `configs/ablation/` và §9.3 quy tắc 3 sinh ra để làm | ✓ hiệu chỉnh vài giờ | Các scorer thành phần có tín hiệu thật không — đó là câu hỏi của §6.3 |

Đọc thẳng bảng: **theo đúng thứ tự ưu tiên mà §7 tự đặt, hướng (4) thắng trên tiêu chí (2) và
(3), và không thua ở (1) hay (4).** Hướng (2) tự dựng thua nặng ở tiêu chí (4) — không phải vì
nhãn, mà vì giờ thu. Điều đó **không chốt gì cả**: §7 nói tiêu chí dùng để chọn *sau khi có số*,
và GĐ 2 chưa chạy. Bảng này là dự báo, không phải kết quả.

### 6.4 Giả thuyết thanh điệu: ủng hộ ở phần nào, đi ngược ở phần nào

`SPEC.md` §7 phát biểu: *"Vì F0 tiếng Việt mang thanh điệu từ vựng, dấu hiệu ngữ điệu báo hiệu
kết thúc lượt hoạt động khác so với ngôn ngữ không thanh điệu; và tách phần thanh điệu ra khỏi F0
sẽ cho tín hiệu tốt hơn F0 thô."* ADR-0002 quyết định 3 đã phát biểu lại chặt hơn: F0 quan sát
được là chồng chập của thanh điệu từ vựng và ngữ điệu phát ngôn.

Tách giả thuyết làm ba mệnh đề, vì chúng có mức bằng chứng rất khác nhau.

**Mệnh đề 1 — "F0 tiếng Việt đã bị thanh điệu chiếm chỗ". ỦNG HỘ, gần như nguyên văn.**

Marc Brunelle, *Intonational phrase marking in Southern Vietnamese*, TAL 2016, trang 60–64,
doi `10.21437/TAL.2016-13` — <https://www.isca-archive.org/tal_2016/brunelle16_tal.pdf>. Nguyên
văn phần Introduction:

> "This suggests that intonational targets may not be phonologized, perhaps because lexical tones
> monopolize pitch and leave little room for intonation."

Đó đúng là câu mà `SPEC.md` §7 đang giả thuyết, do một nhà ngữ âm học viết mười năm trước, dựa
trên corpus. Corpus của bài: tiếng Việt Nam Bộ, 8 bản ghi mỗi bản ~1 giờ, tổng **472 phút**,
**86.232 âm tiết**, **26.160 intonational phrase**, gồm 2 phỏng vấn truyền hình (3 người), 2 tiểu
phẩm hài (8 người), và **4 hội thoại tự nhiên giữa bạn bè cùng tuổi cùng giới** (8 người). Gán
nhãn bởi nhóm người Việt bản ngữ. F0 đo bằng script Praat tại 5 điểm cách đều trong phần hữu
thanh của âm tiết, và **z-normalise để so sánh được giữa các người nói** — đúng cạm bẫy mà
`AGENTS.md` và `.claude/rules/training.md` đều cảnh báo.

**Mệnh đề 2 — "tách thanh điệu khỏi F0 sẽ cho tín hiệu tốt hơn F0 thô". CHƯA AI KIỂM CHỨNG, và
bằng chứng ngữ âm nói phần dư rất yếu.**

Cùng bài Brunelle, phần Results và Conclusions:

> "We see that overall, intonational types have a very limited effect on tone contour or height,
> suggesting that there is no single conventionalized strategy to realize intonation on the last
> syllable of intonational phrases."

> "...there is little evidence that the language uses discrete and categorical intonational
> targets at the end of intonational phrases. The two systematic intonational patterns uncovered
> in this study, a higher f0 in the final syllable of exclamatives and emphatics, and a lower f0
> in backchannel utterances, could both be attributed to a weak effect of a universal effort
> code ... Furthermore, these intonational effects are of an order of magnitude that seems too
> weak to be attributed to conventionalized intonational targets (such as boundary tones)."

Đọc thẳng: nếu tách được thanh điệu ra, cái còn lại **có** cấu trúc, nhưng yếu. Đó là rủi ro
chính của hướng này, và nó phải được nói trong ADR chốt hướng chứ không được lờ đi.

**Mệnh đề 3 — "ngôn ngữ thanh điệu thì F0 kém hữu ích hơn cho turn-taking". CÓ BẰNG CHỨNG ĐI
NGƯỢC.**

Inoue et al. 2024 §4.3 làm đúng phép thử đó: **làm phẳng pitch** bằng Praat rồi đo lại độ chính
xác shift/hold (bảng 5, balanced accuracy %, số trong ngoặc là chênh lệch so với không làm phẳng):

| Tập test | Mô hình đơn ngữ | Mô hình đa ngữ |
|---|---|---|
| English | 79,68 (**+0,09**) | 76,28 (**+0,12**) |
| Mandarin | 82,47 (**−2,02**) | 82,30 (**−2,30**) |
| Japanese | 72,83 (**−1,37**) | 74,73 (**−1,81**) |

Diễn giải của chính tác giả:

> "For Mandarin, together with the high accuracy in the shift/hold prediction experiment, our
> results suggest that pitch plays an important role for indicating turn-final position ...
> Mandarin, being a tonal language with lexical tones for individual words, may be able to provide
> richer pitch information for the model."

Và bài dẫn hai nguồn nữa cho tiếng Quan Thoại: *"Mandarin shows turn-final pitch lowering for all
words in both task-oriented and daily conversations, **regardless of the original lexical tone**
(Jian and Wu, 2011; Levow, 2005)."*

Tức: ở một ngôn ngữ thanh điệu khác, F0 **quan trọng hơn** cho turn-taking chứ không kém, và ngữ
điệu vẫn hạ cuối lượt **bất kể** thanh điệu từ vựng. Câu ở `SPEC.md` §2 — *"Tiếng Việt không có
quyền đó — đổi đường F0 là đổi luôn từ"* — phát biểu quá mạnh theo hướng này. ADR-0002 phần Hệ
quả đã ghi *"`SPEC.md` §2 và §7 cần sửa lời cho khớp"* và chưa làm; bằng chứng ở đây chỉ hướng
việc sửa đó đi cụ thể hơn.

**Chỗ giả thuyết có khả năng đúng nhất — và nó không phải chỗ §7 đang nhắm.**

Brunelle §1, dẫn Hà & Grice và luận án của Hà:

> "...in Northern Vietnamese telephone conversations, intonation on discourse markers (such as the
> backchannels *ờ* and *ừ* and the repair utterances *dạ* and *vâng*, which are all forms of
> acknowledgement) can obscure lexical tone targets, and that some tones are more affected than
> others."

> "One could interpret this as evidence for covert intonational targets: when the lexical identity
> of a word matters, as in regular sentences, the lexical tone wins out. However, when a word is
> just a semantically bleached discourse marker, **its lexical tone loses its importance and the
> effect of intonation is allowed to surface**."

Và Brunelle §3.2 đo được chính điều đó trên `ờ`, `ừ`, `dạ` (246, 182, 152 lần xuất hiện):

> "...most monosyllabic utterances used as backchannels (empty blue circles) are produced with a
> low endpoint" — trong khi "a high proportion of monosyllabic utterances that convey emphatic
> agreement (full green diamonds) are realized with a high endpoint."

Đây **đúng** bài toán "dạ" ở `SPEC.md` §4.3 và R4, đúng điểm 4 trong bốn chỗ trống của ADR-0002,
và nó có một **dự đoán định lượng** để kiểm: cùng chuỗi âm `dạ`, nếu là tiếng đệm thì F0 điểm
cuối thấp, nếu là một lượt hoàn chỉnh (đồng ý nhấn mạnh) thì cao.

Nguồn còn lại đáng đọc trước khi thiết kế thí nghiệm: Hà, K.P. & Grice, M., *Modelling the
interaction of intonation and lexical tone in Vietnamese*, Speech Prosody 2010 —
<https://www.isca-archive.org/speechprosody_2010/ha10_speechprosody.html>. Tóm tắt nguyên văn:
*"Analysis of telephone conversations within the framework of Conversation Analysis reveals that
Vietnamese makes pragmatic use of intonational tones."* Hai thanh được xét là **thanh ngang** và
**thanh huyền**, trên các phát ngôn một từ ở bốn chức năng: **backchannel, yêu cầu thông tin, ra
khỏi lượt, khởi tạo sửa chữa**. Đây là tiếng Việt Bắc Bộ, hội thoại điện thoại — gần bối cảnh
NetCo hơn corpus Nam Bộ của Brunelle.

**Phép thử rẻ nhất và dứt khoát nhất.** Hai thí nghiệm, cả hai chỉ cần dữ liệu GĐ 1 và không cần
huấn luyện mô hình nào, không cần GPU:

- **Thí nghiệm D (làm trước — kỳ vọng cao nhất, chi phí thấp nhất).** Trên mọi phát ngôn đơn âm
  tiết `dạ / vâng / ờ / ừ / à` trong dữ liệu đóng vai: lấy đúng **một** đặc trưng — F0 tại điểm
  cuối phần hữu thanh, z-normalise **theo từng người nói** — và đo AUC phân biệt *tiếng đệm* với
  *một lượt hoàn chỉnh*. Brunelle dự đoán AUC rõ rệt hơn ngẫu nhiên. Nếu đúng: có ngay một scorer
  `BACKCHANNEL` một chiều, giải thích được, gần như miễn phí về độ trễ, và nó vá đúng chỗ mà GĐ 0
  đã đo là hỏng 100% ở mọi ngưỡng.
- **Thí nghiệm T (kiểm đúng mệnh đề 2).** Trên mọi âm tiết cuối của mọi lượt: so AUC của
  (a) F0 thô đã z-normalise theo người nói, với (b) **F0 đã trừ thanh điệu** — lấy z-F0 trừ đường
  trung bình của chính thanh điệu đó, ước lượng từ các âm tiết **không** ở cuối lượt của **cùng
  người nói** (6 mẫu thanh × mỗi người). Nhiệm vụ phân biệt: *kết thúc lượt* với *ngừng giữa
  lượt*. Một con số, hai cột. Nếu (b) không thắng (a) thì giả thuyết chết rẻ, và `SPEC.md` §9.3
  quy tắc 3 được thoả mãn ngay từ cấu trúc thí nghiệm.

Cả hai đòi đúng hai thứ mà `.claude/rules/training.md` đã bắt: **chuẩn hoá F0 theo từng người
nói** và **chia theo người nói**. Cả hai chạy trên `data/processed/`, không đụng `data/holdout/`.

Một lưu ý về công cụ: trích F0 hiện đi qua `praat-parselmouth` (GPLv3, nằm ở `[project]
dependencies`, tức đường chạy chính) — `docs/progress.md` §5 đã treo quyết định này và
`reuse-audit.md` §9.2 đã cắm cờ ⛔. Hai thí nghiệm trên là **offline**, nên chúng chạy được ở
extra `research` mà không cần mở lại câu hỏi giấy phép. Câu hỏi đó chỉ phải chốt khi một scorer
thanh điệu vào **runtime**.

### 6.5 Giai đoạn 2 phải đo gì để chốt hướng cho trung thực

Đây là **thủ tục quyết định**, không phải quyết định. Mười một mục, thứ tự là thứ tự thực hiện.

**Trước khi chạy bất cứ thứ gì:**

1. **Sửa đơn vị đánh giá trước, không phải sau.** `docs/progress.md` §4 ghi: *"Chốt TAKE hiện là
   một lượt một clip. Ghi âm thật có nhiều lượt, nên cả decider lẫn mẫu số của `metrics.py` ...
   phải làm lại, và mọi con số Giai đoạn 0 sẽ không so sánh trực tiếp được qua mốc đó."* Nếu chạy
   B2 và B3 trước khi sửa, ba đường cong sẽ nằm trên ba mẫu số khác nhau và không đặt cạnh nhau
   được. Sửa trước.
2. **Viết trước quy tắc quyết định, trước khi nhìn số.** `roadmap` §6 GĐ 2 liệt kê ba kết cục hợp
   lệ. Ghi vào bản nháp ADR — trước khi chạy — **kết quả nào chọn kết cục nào**: ngưỡng cụ thể
   trên trục nào, ở mức nào. Không có bước này thì ADR chốt hướng sẽ được viết để biện minh cho
   thứ đã lỡ xây, và không ai phát hiện được điều đó sáu tuần sau.

**Chạy:**

3. **B1 quét cả dải trên dữ liệu thật** — 11 điểm, hai trục cùng lúc (`SPEC.md` §9.3 quy tắc 1 và
   2). Không chọn một ngưỡng. Đây cũng là phép kiểm tra xem đường ống GĐ 0 có sống sót qua dữ liệu
   thật không.
4. **B2 nguyên trọng số**, `smart-turn-v3.2-cpu.onnx`, ngưỡng 0,5, 16 kHz mono, đoạn ≤ 8 giây.
   **Ghi riêng chi phí khung chạy ONNX**, không trộn vào trung bình: `reuse-audit.md` §4.1 chỉ ra
   `budget_per_frame_ms: 5.0` phải đọc là ngân sách **trung bình**, và khung nào chạy ONNX sẽ vượt
   xa. Nếu không tách, phép đo độ trễ sẽ nói dối theo hướng lạc quan.
5. **B3 nguyên trọng số**, `Namo-Turn-Detector-v1-Vietnamese`, **kèm độ trễ ASR trong cùng một
   hàng**, không phải ở một bảng khác (ADR-0002 Hệ quả; `.claude/rules/evaluation.md`).
6. **Phép đối chứng TTS-với-người — đề nghị mới, và nó rẻ.** Vì §4.3 chứng minh dữ liệu tiếng
   Việt của B2 là 100% giọng Chirp3, hãy chạy B2 **hai lần**: một lần trên bản đóng vai người
   thật, một lần trên bản TTS đọc **cùng kịch bản đó** (dự án đã có TTS trong vòng lặp). Nếu B2
   tốt hơn hẳn trên bản TTS, chỗ hỏng là **khoảng cách miền tổng-hợp-với-người**, không phải
   "tiếng Việt khó". Hai chẩn đoán đó dẫn tới hai việc hoàn toàn khác nhau ở GĐ 3, và không có
   phép đối chứng này thì không phân biệt được. Chưa ai công bố phép đo này.

**Cắt số:**

7. **Cắt ba chiều, bắt buộc cả ba.** (a) theo **thanh điệu âm tiết cuối** — 6 thanh + `UNKNOWN`,
   chỉ số chính; (b) theo **bốn hành vi** `SPEC.md` §4.3; (c) theo **năm luồng** N1–N5. Cắt (a) là
   thứ `.claude/rules/evaluation.md` gọi là *"the headline metric ... Every other number is context
   for this one."*
8. **Ghi mẫu số bên cạnh mọi tỉ lệ.** `docs/progress.md` §4 đã sửa lỗi này một lần ở GĐ 0
   (`backchannel_error_rate` có mẫu số 1). Cắt ba chiều sẽ làm mẫu số nhỏ đi rất nhanh — 600 sự
   kiện chia cho 6 thanh × 4 hành vi là 25 sự kiện một ô. Ô nào dưới ngưỡng thì ghi "không đủ
   mẫu", không ghi một tỉ lệ.
9. **Một hàng trần (oracle)** — *đề nghị của tài liệu này, không có trong repo*: chạy cùng bộ chỉ
   số với một endpointer hoàn hảo (dùng chính nhãn). Nó cho biết khoảng cách còn lại là bao nhiêu,
   và nó ngăn việc dồn công sức vào một chỗ chỉ còn 3 điểm để lấy.

**Kỷ luật:**

10. **Số độ trễ chỉ lấy từ đường chạy sống** (`SPEC.md` §9.3 quy tắc 4). Cột `latency_source`
    trong CSV đã có từ GĐ 0; giữ nó và giữ nhãn `file-based` ở đâu còn là file.
11. **`data/holdout/` đóng suốt GĐ 2.** Mọi quyết định — kể cả ADR chốt hướng — viết từ tập
    validation. Holdout mở **đúng một lần** ở GĐ 5, và `.github/workflows/holdout-guard.yml` là
    cổng chứ không phải gợi ý.

---

## 7. Chỗ bằng chứng mâu thuẫn với tài liệu trong repo

Bốn chỗ. Cả bốn đều nêu cả hai phía, và **không chỗ nào được sửa bởi tài liệu này** — mỗi chỗ là
một ADR.

### C1 — "Không có corpus hội thoại hai kênh tiếng Việt công khai"

- **Repo nói:** `docs/roadmap.md` §5 — *"không có corpus hội thoại hai kênh tiếng Việt công khai
  ... đó là ràng buộc thật, không phải một lựa chọn còn để ngỏ."* `reuse-audit.md` §3.4 và §5 xác
  nhận lại.
- **Bằng chứng nói:** `LDC96S60` CALLFRIEND Vietnamese tồn tại: 60 hội thoại điện thoại không
  kịch bản, ~25 giờ, `Sample Type: 2-channel ulaw`, `Sample Rate: 8000`, `Data Source(s):
  telephone conversations`, `License(s): LDC User Agreement for Non-Members`, DOI
  `10.35111/0m20-qn97`. Có văn bản đồng ý ghi âm từ cả hai phía.
- **Chữ cần sửa:** "công khai" → "tải công khai miễn phí". Kết luận vận hành **không đổi** (25
  giờ < 92,5 giờ; sai miền; vướng §6).
- **Tài liệu phải sửa:** `docs/roadmap.md` §5; `docs/research/reuse-audit.md` §5 và §10 câu 8.

### C2 — Cách đọc con số 79,38% của `smart-turn`

- **Repo nói:** `reuse-audit.md` §3.1 điểm 1 — *"Củng cố tiền đề. Giả thuyết 'ngôn ngữ thanh điệu
  khác' ở `SPEC.md` §7 giờ có một quan sát độc lập đứng sau, do chính tác giả mô hình công bố."*
- **Bằng chứng nói:** cả **1.004/1.004** mẫu `vie` trong `smart-turn-data-v3.2-test` có
  `synthetic == true`, nguồn `chirp3_2`. Tập đó không phải mẫu — `partial: false`, 31.527 hàng,
  khớp chính xác tổng của bảng benchmark. 79,38% là điểm trên giọng TTS.
- **Hệ quả:** điểm 1 phải rút lại. Điểm 2 và 3 của §3.1 không bị chạm. Đổi lại, xuất hiện một
  khoảng trống mới và cụ thể hơn (§4.3).
- **Tài liệu phải sửa:** `docs/research/reuse-audit.md` §3.1 điểm 1, và §10 câu 1 (đã trả lời).

### C3 — Giấy phép trọng số MaAI

- **Repo nói:** `reuse-audit.md` §4 — *"`MaAI-Kyoto/MaAI` | MIT (mã); trọng số theo từng model,
  encoder Mimi là CC BY 4.0"*, phán quyết *"Kế thừa hình dạng ⚠ — ứng viên cho hướng §7 ở GĐ 3"*.
  ADR-0002 bảng công trình liên quan ghi MaAI/VAP là "MIT". `reuse-audit.md` §9.2 xếp MIT vào
  nhóm ✅ "không có xung đột".
- **Bằng chứng nói** (Hub API, `cardData.license`, ngày 2026-09-12): `vap_en`, `vap_jp`, `vap_ch`,
  `vap_fr`, `vap_ca`, `vap_mc_en`, `vap_mc_jp` → **`cc-by-nc-nd-4.0`**; `vap_tri` →
  `cc-by-nc-sa-4.0`; `vap_bc_en` → `mit`; `continuous-mimi-onnx` → `cc-by-4.0`.
- **Hệ quả, và nó nặng:** **ND = NoDerivatives.** Bước 2 của `roadmap` §6 GĐ 3 — *"Tinh chỉnh mô
  hình có sẵn trên dữ liệu đóng vai đã thu"* — **không áp dụng được cho trọng số MaAI**. NC cũng
  loại mọi đường thương mại hoá. Hai model duy nhất ở MaAI không vướng ND là `vap_tri`
  (NC-SA, có lây lan) và `vap_bc_*` (MIT).
  Thêm: MaAI nay có `vap_fr` và `vap_ca`, nên câu *"chỉ Anh, Trung, Nhật"* ở `reuse-audit.md` §4
  và ADR-0002 đã cũ. **Vẫn không có tiếng Việt** — điểm 2 trong bốn chỗ trống của ADR-0002 đứng
  vững.
- **Tài liệu phải sửa:** `docs/research/reuse-audit.md` §4 và §9.2; bảng công trình liên quan của
  ADR-0002.

### C4 — Phát biểu "F0 tiếng Việt không có quyền báo hiệu kết thúc lượt"

- **Repo nói:** `SPEC.md` §2 — *"Tiếng Anh báo hiệu hết lượt bằng đường cao độ đi xuống cuối câu.
  Tiếng Việt không có quyền đó."* ADR-0002 quyết định 3 đã phát biểu lại chặt hơn, và phần Hệ quả
  tự ghi: *"`SPEC.md` §2 và §7 cần sửa lời cho khớp mục 2 và 3 ở trên. Chưa làm trong ADR này."*
- **Bằng chứng nói:** làm phẳng pitch làm **giảm** độ chính xác turn-taking ở Quan Thoại 2,02–2,30
  điểm và ở Nhật 1,37–1,81 điểm, trong khi ở Anh **không giảm** (Inoue et al. 2024, bảng 5). Và
  Quan Thoại hạ F0 cuối lượt *"regardless of the original lexical tone"*.
- **Hệ quả:** việc sửa lời mà ADR-0002 đã hẹn giờ có hướng cụ thể: không phải "F0 mất quyền", mà
  "F0 mang đồng thời hai thứ, và chưa ai tách chúng ra cho tiếng Việt".
- **Tài liệu phải sửa:** `SPEC.md` §2 và §7 — đúng việc ADR-0002 đã ghi là còn nợ.

---

## 8. Chưa kiểm chứng được

Ghi ra để không ai tưởng chúng đã xong. Xếp theo giá trị nếu trả lời được.

**U1. Babel Vietnamese (`LDC2017S01`) là mấy kênh? — câu hỏi đáng đầu tư nhất còn lại.**
201 giờ hội thoại điện thoại tiếng Việt thu **tại Việt Nam** năm 2012, bốn vùng phương ngữ, tuổi
16–64. Nếu nó là hai kênh thì toàn bộ bức tranh dữ liệu ở Phần A đổi. Trang catalog chỉ ghi
`Sample Type: a-law`, không ghi số kênh; tài liệu trực tuyến duy nhất (`LSP_107_final.pdf`) là tài
liệu đặc thù ngôn ngữ, không nói gì về âm thanh. Thử suy từ quy ước trường `Sample Type`: `LDC97S62`
(Switchboard-1 R2) ghi `2-channel ulaw`, nhưng `LDC2004S13` (Fisher English Part 1) chỉ ghi `ulaw`
— **nên trường này không tin được** và không suy ra được gì. Trả lời bằng cách hỏi thẳng LDC hoặc
đọc file `*.sph` mẫu.

**U2. Phí của `LDC96S60` và `LDC2017S01`.** Ẩn sau đăng nhập LDC ("Login for the applicable fee").

**U3. `SPEC.md` §6 có cho dùng corpus nghiên cứu công khai có đồng ý nhưng không đóng vai không?**
Đây là **quyết định**, không phải sự kiện. Xem §9.

**U4. CALLFRIEND Vietnamese dùng được tới đâu.** 1996, cộng đồng ở Mỹ/Canada, chuyện phiếm, không
nhãn sự kiện lượt nói, không nghiệp vụ. Chưa ai đo khoảng cách giữa nó và tiếng Việt tổng đài hôm
nay.

**U5. Tỉ lệ TTS trong phần còn lại của tập train `smart-turn`.** Chỉ số của
`datasets-server` chỉ phủ 38.637/270.429 hàng (~14%, phần parquet đầu ~5 GB). Trong phần đó:
`vie` = 1.152, `vie AND synthetic=true` = 1.152. Kết luận cho **tập test** thì chắc chắn
(`partial: false`); cho tập train thì chỉ chắc trên 14%.

**U6. Cần bao nhiêu giờ để tinh chỉnh một VAP đã tiền huấn luyện sang ngôn ngữ thứ tư?**
Không bài nào công bố. Inoue et al. 2024 chỉ trả lời "mô hình đơn ngữ không chuyển được" (RQ1) và
"mô hình đa ngữ ngang mô hình đơn ngữ" (RQ2); không có thí nghiệm thêm ngôn ngữ mới với ít dữ
liệu. Cộng thêm C3: kể cả biết số, trọng số MaAI cũng không cho phép tạo bản phái sinh.

**U7. `MaAI` chạy CPU ở mức nào.** README vẫn chỉ nói *"operates efficiently, even exclusively on
CPU"*, không có hệ số thời gian thực, không có cấu hình máy. Câu 6 ở §10 của `reuse-audit.md` vẫn
mở.

**U8. VAP gốc của Ekstedt có chạy CPU không.** README vẫn chỉ có hướng dẫn cài `cudatoolkit=11.6`,
không phát biểu gì về CPU. Câu 7 ở §10 của `reuse-audit.md` vẫn mở.

**U9. `ELRA-U-S 0090` "Vietnamese Telephone Speech Corpus".** `universal.elra.info` từ chối kết
nối ngày 2026-09-12 (`ECONNREFUSED 51.178.59.122:443`). Mô tả gián tiếp gọi nó là "telephone speech
database ... labeled at syllable level", nghe giống đọc theo prompt hơn là hội thoại, nhưng
**chưa xác nhận được**.

**U10. Nguồn âm thanh và tình trạng đồng ý của VietMed.** Không nêu ở dataset card HF, ở README
GitHub `leduckhai/MultiMed/VietMed`, hay ở abstract arXiv 2404.05659 — trong khi chính abstract
viện dẫn *"privacy restrictions"* làm lý do khan hiếm dữ liệu loại này. Đây là **cờ đỏ `SPEC.md`
§6**, không phải giấy thông hành. Đằng nào nó cũng không dùng được cho tầng `turn`.

**U11. Điều khoản giấy phép của VLSP.** Trang `vlsp.org.vn/resources` không công bố; truy cập
bằng mẫu đơn ký tay gửi email. Không biết có cho dùng lại, phát hành lại, hay chỉ cho dự thi.

**U12. Hai mâu thuẫn số liệu chưa giải quyết, ghi lại chứ không giải:**
- **VietSuperSpeech:** abstract arXiv 2603.01894 nói 267,39 giờ / 52.023 cặp; card HF
  `thanhnew2001/VietSuperSpeech` cho ~103,18 giờ / 67.405 mẫu. Một trong hai sai.
- **FOSD:** bản ghi Mendeley (DOI `10.17632/k9sxg2twv4.4`) nói ~30 giờ / 25.921 mẫu; con số "100
  giờ" được lặp lại rộng rãi ở nơi khác. Bản ghi Mendeley là nguồn gốc, nên tài liệu này dùng ~30
  giờ.

---

## 9. Bảng phán quyết

### 9.1 Dữ liệu

| Câu hỏi | Phán quyết | Độ chắc |
|---|---|---|
| Dữ liệu đóng vai tự thu là gì | **Evaluation + calibration.** Huấn luyện chỉ ở mức scorer đặc trưng thủ công và tinh chỉnh nhỏ trên trọng số BSD-2/Apache-2.0 | Chắc — suy từ §3.2 và §4.1 |
| Có nguồn công khai thay được không | **Không, cho tầng `turn`.** Mọi corpus miễn phí đều đơn kênh hoặc đã cắt phát ngôn | Chắc — tra từng cái ở §4.1 |
| Corpus hai kênh tiếng Việt có tồn tại không | **Có đúng một**: `LDC96S60`, 25 giờ, phải mua, không đóng vai, sai miền | Chắc — đọc trực tiếp trường `Sample Type` của LDC |
| `LDC2017S01` (201 giờ) có dùng được không | **Chưa kết luận được** — phụ thuộc số kênh (U1) | Chưa chắc |
| Số giờ cần thu | **~6–12 giờ, ≥ 24–30 người nói**, chia theo người nói | Suy luận, giả định nêu rõ ở §5.3 |
| VAP tự dựng có khả thi về dữ liệu không | **Không**, ở quy mô một giai đoạn thu đóng vai. 92,5 giờ so với ~9 giờ | Chắc |

### 9.2 Phương pháp

| Câu hỏi | Phán quyết | Độ chắc |
|---|---|---|
| Đã chốt method chưa | **Chưa.** Không ADR nào chọn một trong bốn hướng §7 | Chắc — đọc cả năm ADR |
| Cái gì đã chốt | Seam ở `turn/deciders/` (0003); `Prediction`/`score() -> float\|None`/`decide()` mọi khung/`reset()` (0004); ba baseline và tên model (0002); khung ứng dụng và "thích ứng trước" (0005) | Chắc |
| Có cam kết mềm nào không | **Có.** `fused.py` + ngữ nghĩa bỏ phiếu trắng làm hướng (4) rẻ nhất để làm. Không phải quyết định, nhưng là đòn bẩy | Quan sát |
| Tiền đề giả thuyết thanh điệu | **Được ủng hộ**, gần như nguyên văn (Brunelle 2016) | Chắc |
| Hệ quả mạnh ("tách ra thì tốt hơn F0 thô") | **Chưa ai kiểm chứng**, và phần dư được mô tả là yếu | Chắc rằng chưa ai kiểm; rủi ro cao |
| "Ngôn ngữ thanh điệu ⇒ F0 kém hữu ích" | **Có bằng chứng đi ngược** (Inoue et al. 2024, bảng 5) | Chắc |
| Chỗ giả thuyết dễ đúng nhất | **Phân biệt "dạ" tiếng đệm với "Dạ." trọn lượt bằng F0 điểm cuối** — có dự đoán định lượng từ Brunelle §3.2 | Chắc rằng có dự đoán; chưa ai đo trên tiếng Việt tổng đài |
| Phép thử rẻ nhất | **Thí nghiệm D rồi T** ở §6.4 — một đặc trưng, một con số AUC, không huấn luyện, không GPU | — |

---

## 10. Những quyết định thuộc về bạn, không thuộc tài liệu này

Bảy cái. Không cái nào tài liệu này được phép quyết, và bốn cái đầu chặn GĐ 1.

1. **`SPEC.md` §6 có mở cho corpus nghiên cứu công khai có đồng ý nhưng không theo kịch bản
   không?** (CALLFRIEND `LDC96S60`, Babel `LDC2017S01`.) Hai lối đọc đều hợp lý, hệ quả rất khác
   nhau, và cần một ADR dù chọn lối nào. **Chặn GĐ 1.**
2. **Có ngân sách và tư cách để mua dữ liệu LDC không?** Nếu không, câu 1 thành lý thuyết và Phần
   A gọn lại thành "tự thu, dùng để đánh giá". **Chặn GĐ 1.**
3. **Số giờ và số người nói mục tiêu cho GĐ 1.** §5.3 đề nghị ~9 giờ và ≥ 24–30 người, kèm đủ giả
   định để bạn bác. Con số cuối là của bạn. **Chặn GĐ 1.**
4. **Đổi seam `FeatureFrame`/`WavFrameSource` sang hai kênh trước hay sau buổi thu đầu?**
   `docs/progress.md` §4 đã ghi đây là việc còn nợ. Thu trước rồi sửa sau là rẻ hơn về code nhưng
   rủi ro hơn: nếu định dạng thu không khớp, phải thu lại. **Chặn GĐ 1.**
5. **`LICENSE` gốc (đang 0 byte) và `praat-parselmouth` GPLv3 trên đường chạy chính.**
   `docs/progress.md` §5 đã treo. Nay cộng thêm hai họ giấy phép nữa nếu có lúc chạm tới: NC-SA
   (VIVOS, BUD500) và **NC-ND (trọng số MaAI)**. Phải chốt **trước GĐ 3**.
6. **Có thêm phép đối chứng TTS-với-người vào GĐ 2 không** (§6.5 mục 6). Nó là một lần chạy thêm
   và một bộ kịch bản đọc bằng TTS. Rẻ, chưa ai làm, và nó phân biệt hai chẩn đoán dẫn tới hai GĐ
   3 khác nhau — nhưng nó vẫn là công thêm.
7. **Có ghi trước quy tắc quyết định của GĐ 2 không** (§6.5 mục 2), và có chấp nhận rằng
   `fusion.py` có thể thành công sức bỏ đi nếu kết cục là "ship B2" không (§6.1).

---

*Tài liệu này chỉ mang bằng chứng. Mọi lựa chọn suy ra từ nó — chốt hướng ở `SPEC.md` §7, sửa
`docs/roadmap.md` §5, sửa `reuse-audit.md` §3.1/§4/§9.2, sửa `SPEC.md` §2, mua hay không mua dữ
liệu LDC, thêm phụ thuộc — đều cần một ADR riêng, theo ADR-0001.*
