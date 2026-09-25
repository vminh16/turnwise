# Phương pháp chuyển lượt: bài báo của thầy, các ứng viên, và cái rẻ nhất còn công bố được

Tài liệu này là **bằng chứng, không phải quyết định**. Nó trả lời bốn câu hỏi: (1) bài báo Map Task
mà thầy đề xuất thật sự làm gì và chuyển được gì sang Turnwise; (2) những phương pháp nào dùng
được, xếp hạng, với ràng buộc **gần như không có dữ liệu huấn luyện** và **CPU laptop thời gian
thực**; (3) đặc trưng ngôn điệu nào chạy được mà không cần huấn luyện; (4) tầng nào thật sự là đóng
góp. Việc chốt hướng thuộc về `docs/adr/`, theo ADR-0001 và `roadmap.md` §6 GĐ 2.

Nền đã có, không lặp lại ở đây: `docs/research/data-and-method.md` (chi phí dữ liệu của bốn hướng
`SPEC.md` §7, corpus tiếng Việt, giả thuyết thanh điệu) và `docs/research/reuse-audit.md` (số liệu
tiếng Việt của `smart-turn` và NAMO). Tài liệu này bắt đầu từ chỗ hai tài liệu đó dừng lại.

---

## 1. Nguồn và ngày tra cứu

**Mọi thứ dưới đây tra ngày 2026-09-25.** Nguồn là nguồn gốc: file PDF của chính hội nghị/tạp chí,
metadata Hugging Face Hub API, README trong chính repo của tác giả, trang catalog chính thức. Ba
mức, luôn ghi rõ:

- **Đã kiểm chứng từ nguồn gốc** — tôi đã đọc file đó.
- **Do dự án hoặc tác giả tự nhận** — có phát biểu, chưa có kiểm chứng độc lập.
- **Không kiểm chứng được** — gom ở §8, không đoán.

Số đo độ trễ F0 ở §5.4 do **tài liệu này tự đo** trên chính laptop của dự án
(11th Gen Intel Core i5-11400H, 6 nhân — cùng máy đã đo TTS ở `docs/progress.md` §6.8), bằng
`praat-parselmouth` 0.4.7 đã có trong `[project] dependencies`. Không cài thêm gì, không tải mô
hình nào.

**Ngân sách độ trễ, đọc từ `configs/default.yaml`:** `latency.budget_per_frame_ms: 5.0` cho một
khung capture 10 ms, tức **hệ số thời gian thực 0,5**. `docs/progress.md` §2.2 phát biểu cùng ngân
sách đó ở đơn vị khung đặc trưng: **10,00 ms cho mỗi khung 20 ms**. Mọi con số chi phí dưới đây so
với mốc 10 ms/khung-20ms. B1 hiện tiêu 0,0072 ms — khoảng 1/1400 ngân sách.

---

## 2. Trả lời ngắn

| Hạng | Hướng | Dữ liệu cần | CPU/khung 20ms | Giấy phép | Vào seam ở đâu |
|---|---|---|---|---|---|
| **1** | **Scorer ngôn điệu thủ công + fusion** (5–10 đặc trưng kiểu Sharon 2026 / Paierl 2025, cộng scorer thanh điệu cuối câu) | 0 giờ huấn luyện; vài giờ để hiệu chỉnh ngưỡng | **đo được: 0,7–2,3 ms** cho F0 cửa sổ 0,5–3 s | mọi thứ tự viết; `parselmouth` GPLv3 (cờ §6.3) | `scorers/` sau `fused.py` |
| **2** | **B2 `smart-turn` v3.2 nguyên trọng số**, rồi **tinh chỉnh linear head** nếu GĐ 2 chỉ ra chỗ hỏng | 0 giờ (nguyên); ~2–4 giờ nếu tinh chỉnh, theo tiền lệ TamilEOT | tác giả nói 10–100 ms **dồn cục** mỗi đoạn ≤8 s | BSD-2 | `deciders/acoustic_onnx.py`; bản tinh chỉnh là adapter khác |
| **3** | **B3 `Namo-Turn-Detector-v1-Vietnamese` nguyên trọng số** | 0 giờ | <29 ms **+ toàn bộ độ trễ ASR** | Apache-2.0 | `deciders/semantic_onnx.py` |
| 4 | VAP tinh chỉnh từ checkpoint có sẵn | không có số công bố; trọng số dùng được thì NC hoặc "academic only" | tác giả nói chạy CPU thời gian thực, **không có số** | ⛔ xem §4.3 | `deciders/` (adapter thứ năm) |
| ✗ | VAP tự dựng từ đầu | 92,5 giờ hai kênh | — | — | không khả thi |
| ✗ | Prompt-Guided VAP, TurnGPT, Endpoint Anticipation, Easy Turn | 100–950 giờ, hoặc LLM trong vòng lặp | — | — | §4.4 |

**Ba phát hiện nặng nhất của tài liệu này:**

1. **Bài báo Map Task không phải là phương pháp đề xuất được, nhưng nó là nguồn đặc trưng tốt nhất
   đang có** — và nó là **tiền lệ trực tiếp** cho đúng cấu trúc Turnwise đã xây: nó tách đặc trưng
   thành ba nhóm (ngôn điệu / cú pháp / ngữ cảnh), báo cáo đóng góp riêng của từng nhóm, rồi mới
   hợp nhất. Đó chính là `SPEC.md` §9.3 quy tắc 3, viết ra từ năm 2013. Nó cũng có một điểm
   **không** chuyển được: bài dự đoán *khi nào bot nên chêm tiếng đệm*, còn Turnwise phải *nhận ra
   tiếng đệm của khách*. Hai bài toán ngược chiều nhau. Chi tiết §3.
2. **Có hai bài 2025–2026 làm đúng phép đo mà Turnwise sắp làm, và kết quả nghiêng về ngôn điệu chứ
   không nghiêng về ngữ nghĩa.** Sharon et al. 2026 (Uniphore) cho thấy trên 5.000 phát ngôn, thêm
   kênh văn bản vào một endpointer **làm tăng cắt lời** mà không tăng F1; tổ hợp acoustic+prosodic
   thắng. Paierl et al. 2025 dự đoán được *thời điểm* tiếng đệm bằng **LightGBM trên 266 cặp lượt**
   với 45 đặc trưng `parselmouth`, chạy 1,48 ms trên CPU. Cả hai đều ở đúng quy mô dữ liệu mà
   Turnwise có. Chi tiết §4.2.
3. **Hà & Grice 2010 có một quy tắc định lượng cho tiếng Việt, và nó ngược với trực giác tiếng
   Anh:** tiếng đệm mang **boundary tone thấp L%** ở cả hai đầu, còn **kỹ thuật ra khỏi lượt
   (turn exit) mang đường lên, kết thúc bằng H%** — *không bị thanh điệu từ vựng chi phối*. Một
   scorer viết từ hai câu đó không cần huấn luyện gì cả. Chi tiết §5.1.

---

## 3. Bài báo của thầy — Map Task

### 3.1 Trước hết: danh sách tác giả trong đề bài sai một tên

`SPEC.md` §12 chỉ ghi tiêu đề và DOI, nên repo không sai. Nhưng lời đề nghị nói "Meena, Skantze &
Al Moubayed". **Tác giả thứ ba là Joakim Gustafson, không phải Samer Al Moubayed.**

Kiểm chứng từ Semantic Scholar Graph API trên chính DOI
(`https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.csl.2014.02.002`, tra 2026-09-25):
`"authors": [{"name": "R. Meena"}, {"name": "Gabriel Skantze"}, {"name": "Joakim Gustafson"}]`.
Trang công bố của chính Skantze ghi cùng thế: *"R. Meena, G. Skantze och J. Gustafsson,
'Data-driven models for timing feedback responses in a Map Task dialogue system,' Computer speech &
language (Print), vol. 28, no. 4, s. 903-922, 2014"*
(<https://www.kth.se/profile/skantze/publications/>). Al Moubayed có làm việc với Skantze ở KTH
nhưng trên công trình khác (ví dụ Furhat).

**Trích dẫn đúng:** Meena, R., Skantze, G., & Gustafson, J. (2014). *Data-driven models for timing
feedback responses in a Map Task dialogue system*. **Computer Speech & Language, 28(4), 903–922**.
<https://doi.org/10.1016/j.csl.2014.02.002>

### 3.2 Đọc được tới đâu — nói thẳng

- **Bản tạp chí CSL 2014: không đọc được.** `openAccessPdf.status` = `"CLOSED"` ở Semantic Scholar;
  ScienceDirect trả **HTTP 403**; CORE trả **HTTP 403**; DiVA (`kth.diva-portal.org` và
  `www.diva-portal.org`) **từ chối kết nối** (`ECONNREFUSED`) ở cả hai lần thử ngày 2026-09-25. Kể
  cả abstract cũng bị nhà xuất bản gỡ khỏi API (`"Notice: The following paper fields have been
  elided by the publisher: {'abstract'}"`).
- **Bản hội nghị tiền thân: đọc được toàn văn, và tôi đã đọc hết 9 trang.** Meena, Skantze &
  Gustafson, *A Data-driven Model for Timing Feedback in a Map Task Dialogue System*, **SIGDIAL
  2013, Metz, trang 375–383** — <https://aclanthology.org/W13-4062.pdf>. Mọi con số ở §3.3–§3.7
  dưới đây **lấy từ bản SIGDIAL 2013**, không phải bản CSL 2014.
- Phần bản tạp chí mở rộng thêm cái gì so với bản hội nghị: **không kiểm chứng được** (§8, V1).
  Mô tả gián tiếp duy nhất đọc được là cụm *"prosodic, contextual and lexico-syntactic features for
  online detection of feedback response locations"* — cùng ba nhóm đặc trưng với bản 2013.

### 3.3 Bài toán nó giải

**Response Location Detection (RLD).** Không phải endpointing. Hệ thống chạy Map Task với vai
*information follower*; người dùng mô tả đường đi trên bản đồ, hệ thống chỉ chêm phản hồi. Mỗi khi
dò thấy **một khoảng im rất ngắn 200 ms**, mô hình quyết định nhị phân: **Respond** hay **Hold**.
Đơn vị quyết định là **IPU** (inter-pausal unit) — đúng định nghĩa mà `docs/annotation-guide.md`
§4.1 đang dùng.

Nguyên văn phạm vi: *"we do not discriminate between locations for backchannels and turn-changes.
Instead, we propose a general model for response location detection."* Tức bài **cố ý không** tách
tiếng đệm khỏi giành lượt — đúng thứ `SPEC.md` R4 và ADR-0004 bắt buộc phải tách.

### 3.4 Dữ liệu và cách gán nhãn

| Hạng mục | Giá trị |
|---|---|
| Loại dữ liệu | **người–máy** (không phải người–người), Map Task, KTH |
| Ngôn ngữ | **tiếng Anh**, và nguyên văn: *"All the users who participated in the corpus collection were non-native speakers of English"* |
| Cách thu | hệ thống phiên bản ngây thơ: chờ **ngẫu nhiên 0–800 ms** sau mỗi IPU; nếu không có IPU mới thì coi là một Response Location |
| Quy mô thu | **10 người**, mỗi người 5 lượt trên 5 bản đồ → **50 hội thoại** |
| Nhãn | mỗi IPU gán tay ba lớp: **Hold / Respond / Optional**, **hai người gán độc lập** |
| Độ đồng thuận | **kappa 0,68**; **trùng nhau 87,20%** — và bài dùng chính 87,20% làm **trần hiệu năng** |
| Tập dùng được | `Optional` chỉ chiếm 2,1% → bỏ; còn **2.272 IPU**, `Respond` chiếm **50,79%** (baseline lớp đa số) |

Đáng ghi cho GĐ 1 của Turnwise: **đây là một corpus người–máy nhỏ, thu bằng chính hệ thống ngây thơ
mà nghiên cứu muốn thay thế.** Đó đúng là hình dạng của `collector/`. 2.272 IPU từ 50 hội thoại là
bậc độ lớn mà một giai đoạn đóng vai làm nổi.

### 3.5 Đặc trưng — phần chuyển được nhiều nhất

**Ngôn điệu (§4.1 của bài).** Pitch và cường độ lấy mẫu mỗi **10 ms** bằng ESPS trong
WaveSurfer/Snack, đổi sang **thang log** và **z-normalise theo từng người dùng**:

- **mean pitch** trên **200 ms hữu thanh cuối** của IPU;
- **slope of the pitch** trên cùng vùng đó, bằng hồi quy tuyến tính, **kèm hệ số tương quan r** làm
  đặc trưng riêng (tức: vừa lấy độ dốc, vừa lấy *mức tin cậy* của độ dốc);
- **duration** của vùng hữu thanh cuối;
- **mean intensity** trên **500 ms cuối**, cũng z-normalise.

Chuẩn hoá theo người nói lấy từ **phiên làm quen** của chính người đó — một chi tiết vận hành rất
đáng bắt chước: Turnwise đã có câu chào bot ở đầu mỗi buổi thu.

**Cú pháp (§4.2).** Word form và POS tag của **hai từ cuối** IPU; thêm một **word-class
dictionary** tự đặt (gom từ thành lớp theo miền, kiểu class-based n-gram); thêm **word confidence
score** của ASR. POS bằng LBJ.

**Ngữ cảnh (§4.3).** Ba thứ: **độ dài lượt** và **độ dài IPU** (tính cả theo từ và theo giây), và
**dialogue act của câu hệ thống nói gần nhất**.

Một luật cây quyết định (J48, accuracy 65,7%) đáng chép nguyên vào `dialog/` của Turnwise:
*"if the last system dialogue act is Clarification or Guess, and the turn word count is less than
equal to 1, then Respond"* và *"if the last system dialogue act was a Restart or Repetition Request,
and if the turn word count is more than 4 then Respond otherwise Hold."*

### 3.6 Mô hình và số liệu

Naïve Bayes (NB) và SVM trong WEKA, **10-fold cross-validation**. Baseline lớp đa số **50,79%**;
trần do người gán **87,20%**. WER của ASR đưa vào mô hình online: **17,22% (SD 3,8%)**.

Đóng góp từng nhóm, accuracy %:

| Nhóm đặc trưng | NB (transcript tay) | SVM (transcript tay) | NB (ASR) | SVM (ASR) |
|---|---|---|---|---|
| Prosody | 63,3 | **64,5** | 63,3 | 64,5 |
| Context | 59,9 | 64,5 | 60,4 | **64,8** |
| Syntax | **82,3** | 81,5 | **81,1** | 80,5 |
| Prosody + Context | 67,7 | 70,2 | 67,5 | 69,1 |
| **Prosody + Context + Syntax** | **84,6** | 77,2 | **82,0** | 77,1 |

Precision/Recall của mô hình NB tổ hợp: Respond P 81,0 / R 87,0; Hold P 85,0 / R 78,0.

Ba con số cần nhớ, vì chúng định khung cả §4 dưới đây:

- Ngôn điệu **một mình** chỉ đạt 64,5% so với baseline 50,79%. Tức **+13,7 điểm**, không nhiều.
- Cú pháp **một mình** đạt 82,3% — **mạnh hơn ngôn điệu rất nhiều** trên bài toán này.
- **Không có ASR thì cả hệ chỉ còn 70,2%** (nguyên văn: *"they are clearly useful when no ASR is
  available (70.2% as compared to the baseline of 50.79%)"*).

### 3.7 Nghiên cứu người dùng

Đây là phần mạnh nhất của bài và là thứ ít bài turn-taking nào có.

- 8 người thử (2 nữ, 6 nam) làm Map Task với **hai phiên bản** hệ thống: **Random model** (chọn
  ngẫu nhiên Respond/Hold, xấp xỉ baseline 50,79%) và **Trained model**. Hold thì chờ 1,5 giây rồi
  vẫn đáp.
- 32 hội thoại, trung bình **1,7 phút (SD 0,5)**. Random phân loại 557 IPU, Trained 544 IPU.
- **Người thử không phân biệt được hai phiên bản khi đang vừa làm nhiệm vụ vừa đánh giá** — bài nói
  thẳng điều này và phải đổi thiết kế đánh giá.
- Thiết kế thay thế: **8 người nghe lại** và bấm phím mỗi khi thấy phản hồi bị thiếu hoặc không phù
  hợp. Kết quả: **26,75%** quyết định của Random bị chấm là không phù hợp, so với **11,39%** của
  Trained. t = 4,66, dF = 30, **p < 0,001**.

Bài học vận hành cho `SPEC.md` §10 và §9.2: **người đang bận làm nhiệm vụ không chấm được nhịp hội
thoại.** Nếu Turnwise định để người thử chấm "bot nghe có giống người không" ngay sau cuộc gọi, hãy
đọc lại đoạn này — nhóm KTH đã thử đúng cách đó và nó hỏng.

### 3.8 Chuyển được gì, không chuyển được gì

**Chuyển được:**

| Thứ | Vì sao chuyển được |
|---|---|
| **Cấu trúc thí nghiệm ba nhóm đặc trưng + bảng đóng góp riêng** | Là bản mẫu có sẵn cho `SPEC.md` §9.3 quy tắc 3 và `configs/ablation/`. Chép bảng, đổi nhóm. |
| **Bốn đặc trưng ngôn điệu cụ thể** (mean pitch, pitch slope + r, duration vùng hữu thanh, mean intensity), cửa sổ 200/500 ms cuối, z-norm theo người nói | Rẻ, không cần huấn luyện, đúng thứ `.claude/rules/turn.md` đòi ("Normalise F0 per speaker before pooling"). Cửa sổ 200/500 ms nằm gọn trong `ring_buffer_ms: 3000`. |
| **Đơn vị quyết định là IPU, không phải clip** | `docs/progress.md` §4 đã ghi "một lượt một clip" phải sửa. Bài này là tiền lệ cho cách sửa. |
| **Trần hiệu năng = độ đồng thuận người gán** | `docs/annotation-guide.md` §6.3 đã đo đồng thuận nhưng chưa dùng nó làm trần. Dùng đi — nó ngăn việc đuổi theo điểm số vô nghĩa. |
| **Ngữ cảnh: dialogue act của câu bot gần nhất + độ dài lượt** | Turnwise có sẵn cả hai, miễn phí, từ `dialog/`. Nhưng xem cảnh báo tầng ở §3.9. |
| **Thiết kế đánh giá chủ quan bằng người nghe lại, không phải người tham gia** | Đã nói ở §3.7. |

**Không chuyển được:**

| Thứ | Vì sao không |
|---|---|
| **Bản thân bài toán** | Bài quyết định *khi nào bot nên chêm feedback*. Turnwise R4 hỏi *cái khách vừa nói có phải tiếng đệm không*. Nhãn `backchannel` ở `docs/annotation-guide.md` §4.3 nói rõ: "khách chỉ báo là đang nghe". Hai chiều ngược nhau, và chỉ số chính của Turnwise là **tỉ lệ tiếng đệm của *khách* bị nhận nhầm** — bài này không có chỉ số đó và không thể có. |
| **Việc gộp backchannel với turn-change làm một** | ADR-0004 quyết định 1 bác bỏ đúng cách gộp này, có lý do viết sẵn. |
| **Trọng số của cú pháp** | 82,3% từ hai từ cuối + POS là **tiếng Anh, người nói không bản ngữ, miền bản đồ đóng**. Không có POS tagger cho tiếng Việt trên đường chạy runtime mà không kéo theo ASR + tokenizer + độ trễ (§6). Và Sharon et al. 2026 (§4.2) đo lại chính điểm này trên dữ liệu hiện đại và ra kết quả ngược. |
| **Map Task** | Người–máy, nhưng là nhiệm vụ mô tả đường đi. Không có ngắt lời, không có đọc dãy số, không có "dạ". Năm luồng NetCo ở `SPEC.md` §4.1 không có gì chung với nó ngoài hình dạng IPU. |
| **Mức hiệu năng** | 84,6% trên bài toán nhị phân với baseline 50,79%, trong một miền đóng, bằng WEKA năm 2013. Không phải mốc để Turnwise so. |

### 3.9 Phán quyết: dùng nó làm gì

Đề bài cho bốn lựa chọn. Phán quyết: **(b) nguồn đặc trưng cho scorer, cộng (c) trích dẫn công
trình liên quan. Không phải (a), và dứt khoát không phải (d).**

- **Không (a) — phương pháp đề xuất.** Ba lý do, mỗi lý do đủ để loại: bài giải bài toán khác
  (§3.8); phần mạnh nhất của nó là cú pháp tiếng Anh; và nếu chọn nó làm phương pháp thì đóng góp
  của Turnwise trở thành "chạy lại một bài 2013 bằng tiếng Việt" — trong khi bốn chỗ trống ở
  ADR-0002 vẫn còn nguyên.
- **Có (b) — nguồn đặc trưng.** Bốn đặc trưng ngôn điệu ở §3.5 vào thẳng một scorer `END_OF_TURN`,
  không huấn luyện, chi phí đo được ở §5.4. Đây là cách dùng đúng và rẻ nhất.
- **Có (c) — trích dẫn.** Nó là **tiền lệ phương pháp luận** cho cấu trúc đánh giá của Turnwise, và
  nó là chỗ duy nhất trong danh mục tham khảo có **user study** đúng nghĩa. Giữ nó ở phần Related
  Work với vai trò đó, không với vai trò "chúng tôi làm theo".
- **Không (d) — cơ sở cho hành vi chêm tiếng đệm của bot.** Về kỹ thuật thì đúng vai, nhưng
  `SPEC.md` §11 không cấm và §5 cũng không yêu cầu bot chêm tiếng đệm; thêm nó là **thêm một
  nghiệp vụ**, tức scope creep, và nó cần một vòng đánh giá chủ quan riêng (§3.7 cho thấy vòng đó
  đắt). Nếu sau GĐ 4 còn thời gian thì đây là phần mở rộng tự nhiên nhất — ghi vào ADR, đừng làm
  bây giờ.

Một cảnh báo tầng, vì nó dễ sai: nhóm đặc trưng **ngữ cảnh** (dialogue act của câu bot gần nhất)
**không được đặt trong `turn/`**. `SPEC.md` §8 và `.claude/rules/turn.md` nói tầng `turn` "knows
nothing about business flows". Nếu muốn tín hiệu đó, nó phải đi vào qua `FeatureFrame` như một
trường trung tính (ví dụ `bot_speaking` đã có, hoặc một mã hành vi bot trừu tượng), **không** phải
bằng cách cho scorer import `dialog/`. Chưa quyết định điều này là một rủi ro kiến trúc thật.

### 3.10 Chi phí trung thực để tái lập ở quy mô Turnwise

Nếu ai đó vẫn muốn tái lập bài này trên tiếng Việt, đây là hoá đơn:

| Hạng mục | Bài gốc | Turnwise hiện có | Thiếu bao nhiêu |
|---|---|---|---|
| Hội thoại người–máy | 50 | **9** (`docs/progress.md` §6, một người nói, ~9,7 phút) | thiếu ~41 hội thoại |
| IPU gán tay | 2.272 | 0 | 2.272 IPU × 2 người gán |
| Người gán | **2 độc lập**, toàn bộ corpus | **1** | không đo được kappa ⇒ **không có trần hiệu năng** |
| Người nói | 10 | 1 | thiếu 9 |
| POS tagger | LBJ (tiếng Anh) | không có | phải chọn, và nó kéo theo ASR |
| ASR trong vòng lặp | Nuance 9, WER 17,22% | chưa chọn cho runtime (§6.2) | một quyết định chặn |

Ước lượng thời gian gán nhãn, **giả định nêu rõ**: `docs/annotation-guide.md` §6.1 quy định ba
lượt gán. Với 2.272 IPU và một người gán làm được ~150–250 IPU/giờ ở lượt đầu (giả định, chưa đo),
riêng lượt đầu là **9–15 giờ công**, chưa kể lượt soát và lượt gán kép. Với **một** người gán, phần
gán kép — tức chính thứ sinh ra kappa 0,68 và trần 87,20% — **không tồn tại**. Đó không phải chi
tiết nhỏ: bỏ nó đi thì con số duy nhất khiến bài báo gốc đáng tin cũng biến mất.

Kết luận chi phí: **tái lập đầy đủ nằm ngoài tầm.** Lấy đặc trưng thì miễn phí. Đó là toàn bộ lý do
phán quyết là (b)+(c).

---

## 4. Ứng viên, xếp hạng

### 4.0 Tiêu chí

Theo đúng bốn tiêu chí `SPEC.md` §7 đặt ra, cộng ba ràng buộc cứng của lời đề nghị: **gần như không
có dữ liệu huấn luyện** (1 người nói, ~9,7 phút; thực tế 6–16 người, 1,5–3,5 giờ), **CPU laptop
thời gian thực**, **không sinh câu tự do bằng LLM** (`SPEC.md` §11).

### 4.1 Nhóm A — dùng nguyên trọng số, 0 giờ huấn luyện (đã là B2 và B3)

Hai cái này đã chốt ở ADR-0002; ở đây chỉ bổ sung những gì mới so với `reuse-audit.md`.

**`pipecat-ai/smart-turn` v3.2.** Kiểm chứng lại ngày 2026-09-25 qua Hub API
(`https://huggingface.co/api/models/pipecat-ai/smart-turn-v3?full=true`): licence `bsd-2-clause`,
`lastModified` **2026-01-07**, và danh sách file dừng ở `smart-turn-v3.2-cpu.onnx` /
`smart-turn-v3.2-gpu.onnx`. **Không có v3.3 hay v4.** v3.2 vẫn là bản mới nhất.
Tiếng Việt **79,38%** trên 1.004 mẫu, xếp **bét trong 23 ngôn ngữ** — số này `reuse-audit.md` §3.1
đã trích từ `benchmarks/smart-turn-v3.2-cpu.md`, và `data-and-method.md` §4.3 đã chứng minh 1.004
mẫu đó **100% là giọng TTS**. Không có gì mới làm thay đổi hai kết luận đó.

**`videosdk-live/Namo-Turn-Detector-v1-Vietnamese`.** Hub API ngày 2026-09-25: `license:
apache-2.0`, `language: vi`, `lastModified` **2025-10-15**, **47 lượt tải** (tăng 9 lượt so với 38
mà `data-and-method.md` ghi ngày 2026-09-12 — tức gần như không ai dùng). File gồm `model.onnx`,
`model_quant.onnx`, `tokenizer.json`, `vocab.txt`. Kiến trúc là `distilbert-base-multilingual-cased`
(`reuse-audit.md` §3.2 đã sửa ADR-0002 ở điểm này). Model card tự nhận Accuracy 82,37% / F1 83,44%
trên "1000+ Vietnamese utterances" — **tập test không công khai**, không kiểm chứng được.

### 4.2 Nhóm B — scorer đặc trưng thủ công + fusion ← **hạng 1**

Đây là hướng (4) của `SPEC.md` §7, và hai bài mới nhất đều đẩy về phía nó.

**Sharon, Manickavela, Hacioglu & Stolcke (Uniphore), *Less can be More: What Aspects of Speech
Drive End-of-Turn Detection*, arXiv 2609.11066, 10-09-2026** —
<https://arxiv.org/abs/2609.11066>. Tôi đã đọc toàn văn.

- Kiến trúc **APT**: ba nhánh Acoustic / Prosodic / Text, mỗi nhánh chiếu về một không gian rồi hợp
  nhất; **chỉ phần đầu phân loại ~261K tham số được huấn luyện**, hai encoder tiền huấn luyện
  (Zipformer2 70M, MiniLM) **đóng băng**. Khung 25 Hz (40 ms), ngữ cảnh nhân quả 7 khung (**280
  ms**).
- **Nhánh ngôn điệu chỉ có 5 đặc trưng thủ công**, lấy ở 100 Hz bằng pitch tracking của `librosa`
  rồi gộp xuống 25 Hz: `f0` z-normalise (gộp bằng median), `Δf0` (last − first), cờ `voiced` (max),
  cờ `speech` (RMS > 0,02, max), và **`d_sil`** — một bộ đếm im lặng log-scaled, lấy giá trị cuối.
  Năm đặc trưng, 16 chiều sau khi chiếu.
- Dữ liệu: corpus điện thoại tiếng Anh **thật, người–người, 8 kHz stereo**, đa miền (ngân hàng, bán
  lẻ, viễn thông). **10K mẫu huấn luyện ≈ 33 giờ**, 2K val, 5K test, **chia theo bản ghi để không
  rò rỉ người nói**.
- Kết quả (Bảng 2, 5.000 phát ngôn):

  | Cấu hình | F1 | FA% | Miss% | FA/utt | Med Lat (ms) |
  |---|---|---|---|---|---|
  | A (acoustic) | 0,927 | 9,2 | **4,4** | 0,196 | 440 |
  | P (prosodic) | 0,828 | 25,6 | 3,7 | 0,327 | 960 |
  | T (text) | 0,292 | 74,8 | 8,1 | 5,416 | 640 |
  | **A+P** | **0,930** | **7,8** | 5,2 | **0,148** | **400** |
  | APT (cả ba) | 0,909 | 10,7 | 6,0 | 0,206 | 360 |

- Kết luận nguyên văn: *"Adding text increases premature detections without improving performance."*
  Và: *"Only acoustic–prosodic and trimodal systems meet real-time deployment latency and false
  alarm constraints at any operating point."*
- Phân tích không gian đặc trưng: silhouette EOT/non-EOT của **prosodic thô 35 chiều là 0,301**,
  của **text 800 chiều chỉ 0,108**. Tức 35 con số thủ công tách lớp tốt hơn một embedding BERT.
- **Giới hạn tác giả tự nêu, và nó chính là chỗ Turnwise đứng:** *"Results are limited to in-domain
  two-speaker English telephony and text may contribute more in domains with weaker acoustic EOT
  cues (low-resource languages or noisy conditions)."*
- **Độ trễ đo trên NVIDIA A10G** (chú thích Hình 2), **không có số CPU**. Đây là giới hạn thật của
  bài với Turnwise.

**Paierl, Hagmüller & Schuppler (TU Graz), *Continuous prediction of backchannel timing for
human-robot interaction*, Interspeech 2025, trang 3020–3024**,
doi `10.21437/Interspeech.2025-770` —
<https://www.isca-archive.org/interspeech_2025/paierl25_interspeech.pdf>. Đã đọc toàn văn. Bài này
là bài **quan trọng nhất về mặt quy mô dữ liệu** trong cả danh sách.

- Corpus **GRASS**, tiếng Đức Áo, **19 hội thoại đôi mỗi cuộc 1 giờ**, có nhãn turn-taking gán tay
  với độ đồng thuận cao.
- Sau khi lọc còn **266 cặp `hold`–HRT** (HRT = Hearer Response Token, tức tiếng đệm). Cắt cửa sổ
  500 ms bước nhảy 25 ms trên 1,025 giây cuối → **5.123 đoạn**. **266 sự kiện.** Đó là bậc độ lớn
  mà một giai đoạn thu đóng vai làm được.
- **45 đặc trưng, toàn bộ qua `parselmouth`** — đúng thư viện đã có trong `[project] dependencies`
  của Turnwise: 34 đặc trưng F0 + RMS (mean, SD, max/min và **vị trí** của chúng, slope, cộng đặc
  trưng vi phân giữa hai cửa sổ liên tiếp); 3 đặc trưng thời lượng gồm **VU-AR** (voiced-unvoiced
  articulation rate, tính bằng zero-crossing rate của F0sign — **không cần phân đoạn âm vị, không
  cần đếm từ**); 8 đặc trưng chất giọng (HNR qua `to_harmonicity`, H1-H2 qua `to_spectrum`, jitter,
  shimmer).
- F0 trích bằng autocorrelation của `parselmouth`, **dải theo giới tính: 60–300 Hz nam, 80–400 Hz
  nữ**, lấy mỗi 10 ms, làm trơn bằng moving average N=5. F0 và cường độ **chuẩn hoá theo người nói,
  tương đối với chính lượt đó** — nguyên văn: *"speaker-normalized relative to the corresponding
  entire turn of each segment, as global normalization would not effectively capture natural
  variations within a conversation."*
- Mô hình: **LightGBM** (so với Extra Trees và Random Forest), 100 estimators, 10-fold stratified
  CV, 70/30.
- Kết quả: MAE **0,1335** (≈ **130 ms**), RMSE 0,1955, R² **0,6391**; **Prediction Time 1,48 ms**
  cho N=1000 dự đoán, đo trên **Intel Xeon E3-1230 v5, 4 nhân, 3,40 GHz, Windows 10** — tức
  **CPU, và nhanh hơn ET/RF khoảng 15 lần** (27,08 / 26,76 ms).
- Đặc trưng quan trọng nhất (permutation + SHAP): **thời lượng nói của lượt trước**, **intensity
  max**, rồi F0 min / intensity mean / F0 max, jitter, F0 mean, HNR, VU-AR.
- Cửa sổ dự đoán tốt nhất: đoạn tiếng nói **275–875 ms trước** tiếng đệm.

**Vì sao hai bài này đưa nhóm B lên hạng 1:**

1. Cả hai chứng minh **đặc trưng ngôn điệu thủ công vẫn mang tín hiệu thật** ở 2025–2026, không
   phải di sản 2013.
2. Paierl chạy ở **266 sự kiện** — dưới cả quy mô GĐ 1 của Turnwise. Sharon chỉ huấn luyện **261K
   tham số** trên 33 giờ, phần còn lại đóng băng. Cả hai đều khả thi.
3. Cả hai đều dùng **đúng thư viện Turnwise đã có** (`parselmouth`, `numpy`) hoặc tương đương. Không
   thêm phụ thuộc — thoả `AGENTS.md`.
4. Cả hai **giải thích được**: SHAP cho LightGBM, ablation modality cho APT. Đúng tiêu chí (2) và
   (3) của `SPEC.md` §7, và đúng thứ `TurnDecision.scores` sinh ra để chứa.
5. Sharon cho Turnwise một **phát biểu đóng góp sắc hơn**: bài kết luận text không giúp **trên
   tiếng Anh, miền trong, âm học sạch**, và tự nêu giả thuyết rằng text có thể giúp hơn ở
   *low-resource languages*. Turnwise ở đúng ô đó và có B3 để đo. **Đó là một câu hỏi nghiên cứu
   chưa ai trả lời, và Turnwise trả lời được bằng đúng bộ baseline đã chốt.**

**Vào seam thế nào.** `scorers/` + `fusion.py` sau `deciders/fused.py`. Mỗi đặc trưng cụm thành một
scorer khai báo `predicts` (`END_OF_TURN` hay `BACKCHANNEL`, ADR-0004 quyết định 1), trả
`float | None`, `None` khi khung không có vùng hữu thanh nào để đo — **đó là trường hợp bỏ phiếu
trắng tự nhiên nhất mà repo chưa có ví dụ cụ thể**. Ngưỡng ra `configs/`. Tắt từng scorer bằng cách
bỏ tên khỏi `turn.scorers` — `configs/default.yaml` đã chuẩn bị sẵn chỗ đó.

### 4.3 Nhóm C — Voice Activity Projection

**Có dùng zero-shot cho tiếng Việt được không? Bằng chứng nói: không, và có bằng chứng đo được.**

Khảo sát IWSDS 2025 §4.1 viết, nguyên văn: *"Inoue et al. (2024a) investigated multilingual VAP
models to predict turns-shifts in English, Mandarin, and Japanese. **While their results indicate
that models evaluated in cross-lingual settings do not perform well**, Sato et al. (2024b)
demonstrated that aligning the criteria for speech segmentation labels across datasets is crucial to
provide proper evaluation and to effectively use VAP models in cross-lingual scenarios."*
(<https://aclanthology.org/2025.iwsds-1.27.pdf>, trang 258).

Và bài LREC-COLING 2024 **không** có thí nghiệm trên ngôn ngữ thứ tư chưa thấy —
<https://aclanthology.org/2024.lrec-main.1036/>: ba ngôn ngữ, huấn luyện trên cả ba, đánh giá trên
cả ba. Không có zero-shot sang ngôn ngữ mới. Điều này xác nhận lại `data-and-method.md` §8 U6.

**Chi phí thích ứng tối thiểu — repo ghi là "không ai công bố", và điều đó giờ cần sửa một nửa.**
Cùng khảo sát IWSDS 2025, trang 258, nguyên văn: *"VAP models have been observed to perform better
in Japanese when trained in English and fine-tuned with Japanese data than models directly trained
in Japanese (Sato et al., 2024a)."*

Đó là **đúng câu trả lời định tính** mà U6 hỏi: tiền huấn luyện ở ngôn ngữ khác rồi tinh chỉnh
**thắng** huấn luyện trực tiếp. Bài gốc là Sato, Chiba & Higashinaka, *Effects of Multiple Japanese
Datasets for Training Voice Activity Projection Models*, **O-COCOSDA 2024**, IEEE Xplore
<https://ieeexplore.ieee.org/document/10800197/> — **paywall, không đọc được số giờ tinh chỉnh**
(§8, V2). Nên: định tính đã có, **định lượng vẫn chưa**.

**Bằng chứng mới nghiêng về phía "VAP chạy bằng ngôn điệu, không bằng từ ngữ".** O'Connor Russell,
Charuau & Harte, *The Role of Prosodic and Lexical Cues in Turn-Taking with Self-Supervised Speech
Representations*, arXiv 2601.13835, 20-01-2026 — <https://arxiv.org/abs/2601.13835>. Họ dùng
vocoder để tách riêng ngôn điệu khỏi nội dung từ vựng, rồi chạy VAP: *"prediction on
prosody-matched, unintelligible noise is similar to accuracy on clean speech"*, và hai loại tín hiệu
có *"limited interdependence"*. Nếu đúng, VAP chuyển ngôn ngữ **có thể** dễ hơn người ta tưởng — vì
nó ít phụ thuộc từ vựng. Đây là **giả thuyết đáng đo**, không phải kết luận: bài không thử tiếng
Việt và không thử ngôn ngữ thanh điệu.

**Giấy phép — chỗ chặn thật sự, và nó chưa được gỡ.** Tra Hub API ngày 2026-09-25, tổ chức
`maai-kyoto` có **36 model**, vẫn **không có tiếng Việt** (có en, jp, ch, fr, ca, tri):

| Model | Licence | Ý nghĩa với Turnwise |
|---|---|---|
| `maai-kyoto/vap_en`, `vap_mc_en` | **cc-by-nc-nd-4.0** | **ND cấm tạo bản phái sinh** ⇒ không tinh chỉnh sang tiếng Việt được, chấm hết |
| `maai-kyoto/vap_tri` | cc-by-nc-sa-4.0 | NC + share-alike |
| `maai-kyoto/vap_bc_en`, `vap_bc_jp`, `vap_prompt_jp` | **mit** | Tinh chỉnh được — nhưng đây là model **dự đoán tiếng đệm**, không phải VAP chuyển lượt |
| `maai-kyoto/continuous-mimi-onnx` | cc-by-4.0 | encoder, dùng lại được |

`inokoj/VAP-Realtime` (<https://github.com/inokoj/VAP-Realtime>) — mã **MIT**, nhưng README ghi
trọng số *"used for only academic purposes"*. Đầu vào **16 kHz, 2 kênh**, tốc độ 5/10/20 Hz, ngữ
cảnh 2,5–10 giây. Và một câu quan trọng, nguyên văn: ***"In this repository, the VAP model can
operate in real-time in a CPU environment."*** Đây là **lần đầu có phát biểu CPU trực tiếp từ nguồn
gốc** — `data-and-method.md` §8 U7/U8 ghi là chưa có. Nhưng **vẫn không có hệ số thời gian thực và
không có cấu hình máy**, nên U7/U8 chỉ đóng được một nửa.

**Phán quyết nhóm C:** giữ làm ứng viên hạng 4, **không** làm hướng chính. Lý do không phải kỹ
thuật mà là giấy phép + dữ liệu: trọng số VAP chuyển lượt duy nhất chất lượng tốt đều NC-ND hoặc
"academic only", và `SPEC.md` §6 cộng `roadmap.md` §1 định vị đây là dự án ứng dụng. Nếu GĐ 2 cho
thấy phải đi hướng này thì cái phải mở trước là **một ADR về giấy phép**, không phải một dòng code.

### 4.4 Nhóm D — đã loại, kèm lý do để khỏi mở lại

| Ứng viên | Nguồn | Vì sao loại |
|---|---|---|
| **Prompt-Guided Turn-Taking Prediction** (Inoue, Elmers, Fu, Pang, Lala, Ochi, Kawahara, SIGDIAL 2025, tr. 146–151) | <https://aclanthology.org/2025.sigdial-1.9.pdf> | **953,5 giờ hội thoại tiếng Nhật**; prompt do **GPT-4.1** sinh cho cả tập huấn luyện. Cải thiện: balanced accuracy 77,17 → **79,80**, VAP loss 2,431 → 2,346. Vi phạm ràng buộc dữ liệu và §11 (LLM trong vòng lặp). Giữ làm trích dẫn: nó chứng minh VAP **điều khiển được bằng chỉ dẫn**, một hướng mở rất xa. |
| **TurnGPT** (Ekstedt & Skantze 2020) | khảo sát IWSDS 2025 §4.1 | GPT-2 trên văn bản ⇒ thừa hưởng toàn bộ độ trễ ASR, và cần một LM hội thoại tiếng Việt. Hub API ngày 2026-09-25: **không có trọng số chính thức**, chỉ có bản cộng đồng tiếng Nhật (`ouktlab/turngpt-jp-rinna-gpt1b-cejc`, 24–26 lượt tải). Không có bản tiếng Việt. |
| **Endpoint Anticipation for Low-Latency Spoken Dialogue** (arXiv 2606.13450) | `data-and-method.md` §6.2 đã tra | SpokenWOZ (249 giờ) + Switchboard, tiếng Anh, 8 kHz. Không nhắc ngôn ngữ thanh điệu, không phát biểu gì về CPU. Số 1.195 → 690 ms ở `SPEC.md` §2 lấy từ bài này và là **số của họ**, không phải mốc cho Turnwise. |
| **Easy Turn** (Li et al., arXiv 2509.23938, 28-09-2025) | <https://arxiv.org/abs/2509.23938> | Tập huấn luyện **1.145 giờ**. Bốn trạng thái complete / incomplete / backchannel / wait — gần `caller_act` của Turnwise một cách thú vị. Data + model hứa phát hành CC BY 4.0. **Không khai tiếng Việt.** Giữ làm trích dẫn cho phần phân lớp bốn trạng thái. |
| **`FireRedTeam/FireRedChat-turn-detector`** | Hub API 2026-09-25 | apache-2.0, `language: ['zh','en']`, có `multilingual_best_model_q8.onnx`. Dựa trên văn bản (có tokenizer/vocab). **Không khai tiếng Việt**, 0 lượt tải. |
| **`anyreach-ai/dualturn-endpointing`** | Hub API 2026-09-25 | apache-2.0, **`language: ['en']`**, nhưng có `stream_tick.onnx` + `onnx_streaming.py` — tức một **endpointer ONNX streaming hai kênh** thật sự. Không dùng được cho tiếng Việt, **nhưng đáng đọc code** làm mẫu cho adapter streaming của Turnwise. |
| **LiveKit turn-detector** | ADR-0002 đã loại | Không hỗ trợ tiếng Việt, plugin deprecated. Không có gì mới. |
| **Vilex / DuplexGen** | xem §4.5 | Sinh dữ liệu tổng hợp, không phải phương pháp chuyển lượt. |

### 4.5 Tiền lệ ngôn ngữ ít tài nguyên — hai bài, và bài thứ hai là bản thiết kế sẵn

**`TamilEOT` (Santhoshkumar V, arXiv 2609.05631, 04-09-2026)** — <https://arxiv.org/abs/2609.05631>,
CC BY 4.0. Đây là **bài giống Turnwise nhất trong toàn bộ tài liệu này**, và nó ra cách đây ba tuần.

- 18.485 ranh giới lượt gán nhãn, cắt từ **116 cuộc gọi điện thoại tiếng Tamil thật**; test 4.168
  clip từ **30 cuộc chưa thấy**.
- **Hai detector âm thanh tinh chỉnh từ Smart Turn v3.** Accuracy: **70,30% zero-shot → 83,71%**
  (bản 8,7 MB) và **86,13%** (bản 21 MB). ROC-AUC 0,751 → **0,921**.
- **"Both models run in under 150 ms single-threaded on a laptop CPU."**
- Và phần đắt giá nhất, nguyên văn: *"Rule-derived labels, checked against a blind human listening
  pass, were right 95.9% of the time on the positive class and **44.4% on the negative class, which
  is below chance**, because the rule answered a different question than the model is asked."* →
  Thay bằng audio-LLM labeller đạt 97,5% đồng thuận với người, **chi phí 5,69 USD**.
- Ba bài học vận hành, tất cả áp thẳng vào Turnwise: (a) **nhãn sinh bằng luật có thể dưới mức ngẫu
  nhiên ở lớp âm** — `docs/annotation-guide.md` §4.1 đang sinh `caller_vad` và `state` tự động, phải
  kiểm chéo bằng tai đúng như bài này làm; (b) *"three runs at identical config and seed span 0.87
  accuracy points"* — **sàn nhiễu 0,87 điểm**, dưới đó mọi cải thiện là ảo; (c) chạy lại qua VAD
  sản phẩm + adapter streaming **mất thêm 2,60 điểm**, và **7,8% ranh giới không bao giờ tới được
  mô hình** — đúng thứ `SPEC.md` §9.3 quy tắc 4 nói về độ trễ đo trên file.

**Thai Semantic End-of-Turn Detection (arXiv 2510.04016, 05-10-2025)** —
<https://arxiv.org/abs/2510.04016>. ADR-0002 đã ghi. Bổ sung: **chỉ dùng văn bản**, dựng dữ liệu từ
phụ đề YODAS, khai thác **sentence-final particles** của tiếng Thái. Không chạm F0, không chạm
tương tác thanh điệu–ngữ điệu. Tiếng Việt cũng có tiểu từ cuối câu ("ạ", "nhé", "đấy", "thôi") —
đó là một scorer văn bản rẻ mà bài Thái đã chứng minh có tín hiệu, nhưng nó đi qua ASR (§6).

**Vilex (<https://github.com/thaiphu05/Vilex>) — có người đã đụng vào turn-taking tiếng Việt.**
Nguyên văn README: *"Vilex is a Vietnamese adaptation of DuplexGen: Adaptive Synthesis of Human–AI
Turn-Taking Dialogues (EMNLP 2026) — a 5-stage pipeline that synthesizes duplex (two-way) dialogues
where the turn-taking behavior (floor-taking / backchannel / silence) is decided word-by-word within
each utterance."* Apache-2.0, **0 sao**, **không phát hành dữ liệu hay trọng số nào**, và âm thanh
là **TTS hoàn toàn** (OmniVoice tiếng Việt). Bài gốc: Kim, Kim, Woo, Hirschberg, Kim &
Hakkani-Tür, *DuplexGen*, EMNLP 2026, arXiv 2607.26178 — <https://arxiv.org/abs/2607.26178>.

Hai hệ quả, ngược chiều nhau, và cả hai đều thật:

- Phát biểu "chưa ai đụng turn-taking tiếng Việt" **đang yếu đi**. Không đủ để phá đóng góp ở
  ADR-0002 (Vilex không có dữ liệu, không có mô hình, không có phép đo, không có thanh điệu), nhưng
  phải nhắc tới nó trong Related Work, nếu không người phản biện sẽ nhắc hộ.
- Nó rơi vào **đúng cái bẫy** mà `data-and-method.md` §4.3 đã phát hiện ở `smart-turn`: toàn bộ âm
  thanh tiếng Việt là giọng máy. Đó là một luận cứ **ủng hộ** bộ dữ liệu vàng người thật của
  Turnwise, không phải chống lại.

### 4.6 Có benchmark rồi — và kết luận của nó trùng luận điểm trung tâm của SPEC

**TurnBench** (Sesame AI Labs, cùng Mundo AI, Oto, CMU, National Taiwan University, Academia Sinica,
Brno University of Technology) — <https://turnbench.sesame.com/>. Đo end-of-turn và ngắt lời bằng ba
chỉ số **recall, FPR, latency**; 104 giờ train / 7,3 giờ dev / 22,9 giờ test trên Hugging Face; 20
hệ thống trên leaderboard. Tiếng Anh, thu trong studio, **không có tiếng Việt**.

Kết luận của chính họ: ***"No system is simultaneously fast, high-recall, and low on false
positives."***

Đó là `SPEC.md` §1 và §9.3 quy tắc 1, do một bên thứ ba đo trên 20 hệ thống thương mại. Dùng nó làm
chỗ dựa cho luận điểm đánh đổi — và nó cũng lấp một phần khoảng trống mà khảo sát IWSDS 2025 §7.1
than phiền (*"the lack of well-established benchmarks to monitor progress"*).

---

## 5. Đặc trưng ngôn điệu và thanh điệu — cái gì chạy được mà không cần huấn luyện

### 5.1 Hà & Grice 2010: một quy tắc định lượng, và nó ngược chiều tiếng Anh

Đã đọc **toàn văn** bản PDF ISCA: Kieu-Phuong Ha & Martine Grice, *Modelling the Interaction of
Intonation and Lexical Tone in Vietnamese*, **Speech Prosody 2010, Chicago**, doi
`10.21437/SpeechProsody.2010-27`, IfL Phonetik, University of Cologne —
<https://www.isca-archive.org/speechprosody_2010/ha10_speechprosody.pdf>.

**Corpus:** 18 cuộc gọi điện thoại, **28 người nói tiếng Việt Bắc Bộ** (15 nữ, 13 nam), tuổi 11–63,
thu ở **Hà Nội và Berlin**, tổng khoảng **57 phút**. Từ khảo sát: *ờ/ừ* và *gì* (thanh **huyền**,
low-level), *vâng* và *ai* (thanh **ngang**, high-level).

**Bốn chức năng, và đường F0 của từng chức năng** (Bảng 2 và §4 của bài):

| Chức năng | Đường F0 cuối | Phân tích autosegmental | Thanh điệu từ vựng |
|---|---|---|---|
| **Tiếng đệm (BC)** | **thấp hoặc đi xuống** | **L%** ở cả đầu và cuối IP | **bị ghi đè** |
| **Hỏi thông tin (Req)** | **đi lên** | L% … **H%** | không bị ảnh hưởng |
| **Ra khỏi lượt (T-Ex)** | **đi lên** | L% … **H%** | không bị ảnh hưởng |
| **Khởi tạo sửa chữa (RI)** | **đi lên cao** | **H%** | có thể mất trong lời nhanh |

Ba câu nguyên văn đáng chép vào ADR:

> "In backchannels, low boundary tones (L%) are used at the beginning and at the end of the phrase,
> whereas lexical tones appear to be lost."

> "In requests for information during telephone openings and in turn exits, a rising contour
> (initial L% and final H%) is produced, **again not affected by the lexical tones**."

> "…lexical tones can be masked or even overridden by edge tones."

**Ba hệ quả trực tiếp cho Turnwise:**

1. **Có một scorer `BACKCHANNEL` viết được ngay, không huấn luyện.** Với mỗi IPU đơn âm tiết trong
   tập {dạ, vâng, ừ, ờ, à}: đo F0 ở điểm cuối vùng hữu thanh, z-normalise theo người nói, và hỏi
   nó thấp hay cao. Thấp ⇒ tiếng đệm. Điều này **trùng khớp độc lập** với Brunelle 2016 mà
   `data-and-method.md` §6.4 đã trích (*"most monosyllabic utterances used as backchannels … are
   produced with a low endpoint"*). **Hai corpus khác nhau, hai phương ngữ khác nhau, cùng một dự
   đoán.** Đó là mức bằng chứng tốt nhất mà dự án này có cho bất kỳ giả thuyết nào.
2. **Dấu hiệu ra khỏi lượt trong tiếng Việt là một đường LÊN, không phải đường xuống.**
   `SPEC.md` §2 viết "Tiếng Anh báo hiệu hết lượt bằng đường cao độ đi xuống cuối câu" rồi ngụ ý
   tiếng Việt mất dấu hiệu đó. Hà & Grice nói mạnh hơn và cụ thể hơn: tiếng Việt **có** một dấu
   hiệu ra khỏi lượt, nó là **H% cuối**, và nó **không bị thanh điệu từ vựng chi phối**.
   `.claude/rules/turn.md` đã cảnh báo đúng chiều này ("A scorer that assumes a falling contour
   means end-of-turn is importing an English assumption") — giờ có nguồn gốc đứng sau.
3. **Giả thuyết ở ADR-0002 quyết định 3 vẫn đứng, nhưng cái cần "tách" không phải là phần dư.** Nếu
   ngữ điệu **ghi đè** thanh điệu ở đúng vị trí quan trọng, thì thứ cần đo là **độ lệch của âm tiết
   cuối so với mẫu thanh điệu của chính nó**, chứ không phải F0 thô và cũng không phải một phần dư
   tinh vi. Xem §5.3.

**Giới hạn phải nói:** 57 phút, 28 người, **chỉ hai thanh** (huyền và ngang), **chỉ từ chức năng
đơn âm tiết**. Tác giả tự ghi: *"Future work needs to include the other lexical tones on function
words as well as content words, and also needs to consider longer phrases and different speech
rates."* Bốn thanh còn lại (sắc, hỏi, ngã, nặng) **chưa ai đo ở vị trí cuối lượt**. Đó vừa là giới
hạn vừa là **chỗ trống mà chỉ số chính của Turnwise nhắm vào**.

### 5.2 Nguồn mới hơn

**Tjuka, Nguyen, van de Vijver & Spalek, *Investigating the variation of intonation contours in
Northern Vietnamese tones*, Frontiers in Education, 2024**, doi `10.3389/feduc.2024.1411660`,
**CC BY** — <https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2024.1411660/full>.

- **70 người nói Bắc Bộ** (45 nữ, 25 nam, 19–39 tuổi), **21.332 điểm dữ liệu**, mô hình hoá bằng
  **Generalized Additive Models**. Đây là corpus tiếng Việt lớn nhất trong toàn bộ tài liệu này.
- Kết quả: khác biệt về cao độ giữa hai điều kiện tiêu điểm **chủ yếu ở đầu từ**, và *"significant
  differences in pitch … restricted to parts of the words"*. Mỗi thanh phản ứng **khác nhau**: sắc
  lên cuối từ để đánh dấu tiêu điểm; ngã và nặng **xuống**; huyền **lên**.
- Hai điều rút ra cho Turnwise: (a) **mỗi thanh cần một mẫu riêng** — một quy tắc chung cho cả sáu
  thanh sẽ sai; (b) tác giả cảnh báo **F0 một mình không đủ** cho tiếng Việt, phải tính tới **kiểu
  phát âm (phonation)** — điều này trùng với việc Paierl et al. 2025 thấy **jitter và HNR** lọt vào
  top-10 đặc trưng.
- Cảnh báo về ngoại suy: đây là **tiêu điểm trong câu đọc**, không phải kết thúc lượt trong hội
  thoại. Không dùng nó để suy ra hành vi cuối lượt.

**Hà & Grice, *Tone and intonation in discourse management — How do speakers of Standard Vietnamese
initiate a repair?*, Journal of Pragmatics** —
<https://www.sciencedirect.com/science/article/abs/pii/S0378216616306336>. Phần mở rộng của mục
"khởi tạo sửa chữa" ở §5.1. **Paywall, chưa đọc** (§8, V3). Đáng đọc vì `SPEC.md` §4.2 có quy tắc
"ba lần hiểu sai thì chuyển người" — sửa chữa là một hành vi nghiệp vụ thật của Turnwise.

### 5.3 Tách thanh điệu khỏi ngữ điệu — bốn cách, xếp theo giá

| Cách | Cần gì | Làm được ở Turnwise? |
|---|---|---|
| **A. z-normalise F0 theo người nói** | vài chục giây tiếng nói của chính người đó | **Có, ngay.** Bắt buộc bởi `AGENTS.md` và `.claude/rules/turn.md`. Đây là điều kiện cần cho mọi cách sau. |
| **B. Trừ mẫu thanh điệu của chính người nói** ("per-tone template subtraction") | 6 mẫu thanh × mỗi người, ước lượng từ các âm tiết **không ở cuối lượt** của chính người đó | **Có.** Đây chính là "Thí nghiệm T" mà `data-and-method.md` §6.4 đã thiết kế. Không huấn luyện, chỉ lấy trung bình. Vài phút tiếng nói mỗi người là đủ cho 6 mẫu nếu kịch bản phủ đủ thanh. |
| **C. Stylise đường F0** (Prosogram, MOMEL/INTSINT) | thuật toán có sẵn, không cần dữ liệu | **Có, nhưng chưa rõ ích lợi.** Stylisation làm trơn F0 thành các đoạn tuyến tính; nó *giảm nhiễu*, không *tách* thanh điệu khỏi ngữ điệu. Rẻ, nhưng đừng nhầm nó với cách B. |
| **D. Phân rã kiểu Fujisaki** (phrase command + accent/tone command) | ước lượng tham số, cần chuyên gia và hậu xử lý | **Không, ở giai đoạn này.** Mô hình Fujisaki **đúng về khái niệm** — nó chính là phát biểu "F0 là chồng chập" của ADR-0002 quyết định 3, dưới dạng hai bộ lọc bậc hai cộng lại (<https://en.wikipedia.org/wiki/Fujisaki_model>). Đã có bản cho tiếng Việt trong TTS (*Fujisaki model based F0 contours in Vietnamese TTS*, <https://www.researchgate.net/publication/221478949_Fujisaki_model_based_F0_contours_in_vietnamese_TTS>) và bản khảo sát đa ngôn ngữ của Mixdorff (<https://sprosig.org/tal2004/tal2004-Beijing/Mixdorff.pdf>). Nhưng trích tham số tự động *"require a high degree of expert knowledge and post-processing"*, và chưa nguồn nào công bố nó chạy **online, nhân quả, trong ngân sách 10 ms/khung**. Đây là một luận án, không phải một scorer. |

**Khuyến nghị:** A rồi B. C chỉ khi B nhiễu quá. D **không**, và nếu ai đề xuất D thì đòi một ADR
riêng kèm số đo độ trễ trước khi viết dòng code nào.

Một điểm mà cách B giải quyết mà không cách nào khác giải quyết: `TurnDecision` theo ADR-0003 **bắt
buộc mang thanh điệu của âm tiết cuối**, và `evaluation.roleplay.final_syllable_tone` đã đọc được
thanh từ chữ viết. Tức Turnwise **đã có nhãn thanh miễn phí** — thứ mà mọi bài ở §4 đều không có.
Cách B chỉ là: dùng nhãn đó để chọn đúng mẫu trừ đi. Đó là lý do chỉ số chính ở `SPEC.md` §9.1 vừa
là chỉ số vừa là **cơ chế**.

### 5.4 Chi phí F0 trên CPU — tự đo, không lấy từ bài báo

Đo trên laptop của dự án (**i5-11400H, 6 nhân**), `praat-parselmouth` 0.4.7, tín hiệu tổng hợp có
F0 biến thiên 100–140 Hz, `time_step=0.01`, dải 60–400 Hz, 40 lần lặp mỗi cấu hình. Script ở thư
mục scratchpad, không commit.

```
to_pitch_ac  cửa sổ 0,2 s   median 0,46 ms   p95 0,54   max 3,72
to_pitch_ac  cửa sổ 0,5 s   median 0,71 ms   p95 0,89   max 1,62
to_pitch_ac  cửa sổ 1,0 s   median 1,01 ms   p95 1,18   max 1,32
to_pitch_ac  cửa sổ 3,0 s   median 2,30 ms   p95 2,69   max 2,72
to_pitch_cc  cửa sổ 0,5 s   median 1,39 ms   p95 1,43   max 1,47
numpy FFT-ACF, khung 50 ms  median 0,0370 ms p95 0,0403 max 58,05
```

**Đọc thẳng:**

- Ngân sách là **10 ms cho mỗi khung đặc trưng 20 ms**. Trích F0 bằng `parselmouth` trên cửa sổ
  **0,5 giây** tiêu **0,71 ms — khoảng 7% ngân sách**. Trên cả `ring_buffer_ms: 3000` cũng chỉ
  2,30 ms, **23%**. Cửa sổ 200 ms mà bài Map Task dùng: **0,46 ms, 4,6%**.
- ⇒ **Toàn bộ nhóm đặc trưng ngôn điệu ở §3.5 và §4.2 nằm gọn trong ngân sách, với biên rất rộng.**
  Đây là câu trả lời cho câu hỏi "chạy nổi không", và nó là số đo chứ không phải suy đoán.
- `to_pitch_ac` (autocorrelation) **nhanh gấp đôi** `to_pitch_cc` (cross-correlation) ở cùng cửa sổ.
  Dùng `ac` — đây cũng là thuật toán Paierl et al. 2025 dùng.
- Đường ACF thuần `numpy` rẻ hơn **20 lần** (0,037 ms) nhưng `max` chạm **58 ms** vì cấp phát của
  `np.fft` ở lần chạy đầu. Trên đường chạy thời gian thực, **đuôi chậm mới giết**, không phải trung
  vị. Nếu dùng đường này thì phải cấp phát trước bộ đệm FFT, đúng kỷ luật ring buffer ở
  `.claude/rules/audio.md`.
- **Ba cảnh báo về chính phép đo này:** (a) tín hiệu tổng hợp, không phải tiếng Việt thật — tiếng
  thật có vùng vô thanh và nhiễu, chi phí có thể khác; (b) đo tách rời, **không** đo trong đường
  chạy sống, nên theo `SPEC.md` §9.3 quy tắc 4 nó **không phải số báo cáo được**, chỉ là số để
  quyết định có đáng thử không; (c) `parselmouth` là **GPLv3 trên đường chạy chính** —
  `reuse-audit.md` §9.2 đã cắm cờ ⛔ và `docs/progress.md` §5 đã treo. Nếu một scorer F0 vào runtime
  thì **câu hỏi giấy phép đó phải chốt trước**, không phải sau.

### 5.5 Bảng: scorer nào cần gì

| Scorer đề xuất | Dự đoán | Cần huấn luyện? | Nguồn gốc |
|---|---|---|---|
| `silence_accumulator` — thời lượng im lặng log-scaled | `END_OF_TURN` | **Không**, thuần quy tắc | Sharon 2026 `d_sil`, đặc trưng mạnh nhất của nhánh ngôn điệu |
| `final_f0_endpoint` — F0 điểm cuối vùng hữu thanh, z-norm theo người nói | `BACKCHANNEL` | **Không** | Hà & Grice 2010 (L% cho tiếng đệm); Brunelle 2016 |
| `final_contour_direction` — độ dốc F0 200 ms hữu thanh cuối **kèm hệ số r** | `END_OF_TURN` | **Không** | Map Task §3.5; Hà & Grice (H% cho turn exit) |
| `tone_residual` — z-F0 âm tiết cuối **trừ mẫu thanh của chính người nói** | `END_OF_TURN` | **Không huấn luyện**, chỉ ước lượng 6 trung bình/người | ADR-0002 quyết định 3; "Thí nghiệm T" ở `data-and-method.md` §6.4 |
| `intensity_tail` — cường độ trung bình 500 ms cuối, z-norm | `END_OF_TURN` | **Không** | Map Task §3.5; Paierl 2025 (intensity max hạng 2) |
| `turn_duration` — thời lượng IPU/lượt | cả hai | **Không** | Paierl 2025 (đặc trưng hạng 1); Map Task nhóm ngữ cảnh |
| `voice_quality` — jitter, shimmer, HNR | `BACKCHANNEL` | **Không**, `parselmouth` có sẵn | Paierl 2025; Tjuka 2024 (phonation) |
| *(tuỳ chọn)* `final_particle` — tiểu từ cuối câu từ văn bản ASR | `END_OF_TURN` | **Không** | tiền lệ tiếng Thái arXiv 2510.04016 — **nhưng đi qua ASR**, xem §6 |

Tám scorer, **không cái nào cần một mô hình huấn luyện**, tất cả đều bật tắt được bằng
`turn.scorers` trong `configs/`, tất cả đều bỏ phiếu trắng được khi không có vùng hữu thanh. Đó là
hình dạng mà ADR-0003 và ADR-0004 dựng sẵn chỗ cho.

---

## 6. Tầng nào là đóng góp

### 6.1 Phát biểu thẳng

**Đóng góp của Turnwise nằm ở `src/turnwise/turn/`. Không ở ASR, không ở TTS.**

Căn cứ, từ chính repo:

- `SPEC.md` **§11** liệt kê "Huấn luyện mô hình nhận dạng giọng nói hoặc tổng hợp giọng nói mới" là
  mục **ngoài phạm vi** thứ nhất.
- `SPEC.md` **§8** giao cho `turn`: "nhận đặc trưng, trả về đánh giá về trạng thái lượt nói".
- `SPEC.md` **R8** đòi ba baseline chạy trên **cùng** ASR và TTS — tức ASR và TTS là **hằng số của
  thí nghiệm**, không phải biến. Nếu chúng thay đổi giữa các lần chạy, cả bảng so sánh vô nghĩa.
- **ADR-0003** đặt seam ở `turn/deciders/` và nói rõ điều này thành **sự thật cấu trúc** thay vì
  lời hứa.
- `SPEC.md` **§9.1** đặt chỉ số khoa học chính là "chênh lệch tỉ lệ lỗi giữa các thanh điệu của âm
  tiết cuối" — một chỉ số của tầng `turn`.

### 6.2 ASR dùng để làm gì, và ở đâu nó trở thành chịu lực

**Bốn vai, đừng lẫn:**

| Vai | Hiện trạng | Có chịu lực không |
|---|---|---|
| **Nghe ngược dữ liệu thu** (GĐ 1) | Đã chốt: `asr-check/`, `Systran/faster-whisper-small`, MIT, khoá revision `536b0662` (`docs/progress.md` §6.7) | **Không.** Môi trường riêng, chỉ gợi ý cho người gán |
| **Gán nhãn hỗ trợ** (pha 1.6) | Chưa chốt | Không — người gán vẫn nghe lại |
| **Nuôi B3** (`SPEC.md` R8) | **Chưa chốt — và đây là chỗ chặn** | **CÓ.** Xem dưới |
| **Runtime của sản phẩm** (GĐ 4) | Chưa chốt | **CÓ**, nếu có bất kỳ scorer văn bản nào |

**Chỗ ASR trở thành chịu lực, nói cho rõ:**

1. **B3 không có số nếu chưa chốt ASR.** `.claude/rules/evaluation.md`: *"B3's numbers are
   meaningless without the ASR latency that fed it — report them together."* Và độ trễ ASR **chi
   phối** độ trễ của B3: Namo tự nhận <29 ms, nhưng `faster-whisper-small` trên một đoạn tiếng nói
   mất **hàng trăm ms**. Tức con số của B3 gần như **hoàn toàn là con số của ASR**. Nếu chọn ASR
   khác, B3 thành một baseline khác. **Chốt ASR trước khi chạy GĐ 2, và ghi tên + phiên bản + độ
   trễ đo được vào cùng hàng CSV.**
2. **ASR sai chữ ⇒ sai thanh.** `evaluation.roleplay.final_syllable_tone` đọc thanh **từ chữ viết**.
   Nếu đường chạy nào lấy văn bản từ ASR rồi suy thanh, thì lỗi ASR biến thành lỗi thanh, và **chỉ
   số chính của dự án bị nhiễm** bởi một thành phần không phải đóng góp. `docs/progress.md` §6.7 đã
   thấy Whisper small dao động trên câu ngắn ("ồ ồ" / "à lâu quá" / "alô alô") — đúng loại câu mà
   R4 quan tâm. **Kết luận: thanh điệu cho chỉ số chính phải lấy từ nhãn người gán
   (`caller_words` + `tone_override`), tuyệt đối không từ ASR.**
3. **Bất kỳ scorer văn bản nào (ví dụ `final_particle` ở §5.5) đều thừa hưởng độ trễ ASR.** Một
   scorer chạy 0,5 ms mà phải chờ 300 ms để có chữ thì độ trễ thật là 300,5 ms. Nếu thêm scorer
   loại này, `TurnDecision` phải ghi lại **tuổi của văn bản** ở khung đó, nếu không bảng ablation
   sẽ nói dối.

**Ứng viên ASR tiếng Việt, giấy phép tra từ Hub API ngày 2026-09-25:**

| Model | Licence (trường `cardData.license`) | Streaming | Ghi chú |
|---|---|---|---|
| `vinai/PhoWhisper-{tiny,base,small,medium,large}` | **`bsd-3-clause`** ✅ | Không có streaming gốc; Whisper là kiến trúc **đoạn 30 giây**, phải tự cắt cửa sổ | Fine-tune Whisper trên **844 giờ** tiếng Việt nhiều giọng (tác giả tự nhận). `PhoWhisper-small` 6.263 lượt tải, `lastModified` 2024-11-12 |
| `Systran/faster-whisper-small` (+ các bản khác) | **`mit`** ✅ | Không streaming thật; CTranslate2, **không cần torch** | 3,1 triệu lượt tải. **Đã dùng trong `asr-check/`** |
| `nguyenvulebinh/wav2vec2-base-vietnamese-250h` | **`cc-by-nc-4.0`** ⛔ **phi thương mại** | CTC ⇒ **streaming được thật sự** (khung-theo-khung, không cần đoạn 30 s) | 61.075 lượt tải — phổ biến nhất, và **vướng giấy phép** |
| `khanhld/wav2vec2-base-vietnamese-160h` | **`cc-by-nc-4.0`** ⛔ | CTC, streaming được | Cùng vấn đề |

**Nghịch lý phải nói ra:** các checkpoint tiếng Việt **streaming được thật sự** (wav2vec2 + CTC)
đều là **CC BY-NC**; các checkpoint **giấy phép sạch** (PhoWhisper BSD-3, faster-whisper MIT) đều là
kiến trúc **encoder-decoder theo đoạn**, phải giả lập streaming bằng cách cắt cửa sổ chồng lấn — và
cách đó **thêm độ trễ và thêm ảo giác** (`docs/progress.md` §6.7 đã chứng kiến ảo giác trên đoạn
im). Đây là cùng họ bệnh mà `tts-voice.md` §4.2 và `data-and-method.md` §7 C3 đã ghi: **thứ tốt nhất
trong hệ sinh thái tiếng Việt thường là NC.** Một ADR về giấy phép sẽ giải quyết cả ASR, TTS,
`parselmouth` và trọng số VAP cùng lúc — rẻ hơn là chốt bốn lần.

Nếu muốn một bản PhoWhisper chạy qua CTranslate2 (tức giữ BSD-3 và bỏ torch), phải **tự chuyển đổi**
bằng `ct2-transformers-converter`; **chưa kiểm chứng** có bản chuyển đổi sẵn trên Hub (§8, V4).

### 6.3 TTS dùng để làm gì

**Đã chốt, không mở lại: `VieNeu-TTS v3 Turbo`, preset "Minh Quân Pro", int8** —
`docs/progress.md` §6.8, bằng chứng ở `docs/research/tts-voice.md` (Apache-2.0, audio sinh ra không
bị ràng buộc thêm).

Ba ràng buộc TTS áp lên tầng `turn`, tất cả đều đã đo:

- **Giọng bot nằm trong kênh 1 của mọi bản ghi GĐ 1.** Đổi TTS sau GĐ 1 = thu lại. Nên TTS là hằng
  số, đúng như R8 cần.
- **TTFA 168–334 ms (int8, đo trên chính laptop này).** Con số này cộng vào **mọi** độ trễ đáp của
  **mọi** decider, kể cả B1. Nó là nền chung, không phải biến so sánh — nhưng phải xuất hiện trong
  báo cáo, nếu không người đọc sẽ tưởng 400 ms là toàn bộ độ trễ.
- **`dialog/` tự viết slot thành chữ trước khi đưa cho TTS** (số thuê bao, tiền, ngày). Đã quyết ở
  §6.8. Đây là lý do `turn` không bao giờ được thấy văn bản có slot chưa mở.

**TTS không phải chỗ nào trong bài báo cần đóng góp.** Nó xuất hiện ở đúng một chỗ trong phần đánh
giá: `SPEC.md` §9.2 mục 4, điểm tự nhiên do người nghe chấm (R12), với mốc trần là người thật đọc
cùng lời thoại. Đó là một phép đo, không phải một phương pháp.

---

## 7. Chỗ bằng chứng mâu thuẫn hoặc bổ sung cho giả định trong repo

Năm chỗ. Không chỗ nào được sửa bởi tài liệu này — mỗi chỗ cần một ADR hoặc một lần sửa văn bản có
chủ ý.

**M1. Tác giả bài Map Task.** Đề bài (và có thể lời thầy) nói "Al Moubayed"; tác giả thứ ba là
**Gustafson**. `SPEC.md` §12 không ghi tác giả nên repo không sai, nhưng nếu bài báo của nhóm trích
dẫn thì phải trích đúng. Bằng chứng §3.1.

**M2. "Ngôn ngữ thanh điệu không được nhắc tới ở bất kỳ đâu" trong khảo sát IWSDS 2025 — phát biểu
quá mạnh.** `SPEC.md` §2 viết vậy. Đọc chính bài (<https://aclanthology.org/2025.iwsds-1.27.pdf>):
**Bảng 1 có HKUST Mandarin Telephone Speech Corpus** (zh, 200 giờ, 1,2K hội thoại), và §4.1 bàn
thẳng về VAP tiếng Quan Thoại. Tiếng Quan Thoại **là** ngôn ngữ thanh điệu. Phát biểu đúng phải là:
*khảo sát có bao một ngôn ngữ thanh điệu ở mức "ngôn ngữ", nhưng **không chỗ nào coi thanh điệu từ
vựng là một biến** ảnh hưởng tới chuyển lượt, và không có tiếng Việt*. Ba khẳng định khác của
`SPEC.md` §2 lấy từ cùng khảo sát thì **đúng nguyên văn**: *"only 28% of the reviewed papers in this
survey compare their methods with systems presented in prior works"*; *"backchannels use varies from
one culture to another"*; và kết luận *"the majority of works have been conducted on English and
Japanese corpora, with almost no efforts in other languages"*. Thêm hai con số hữu ích chưa ai trích:
**một phần ba** công trình end-of-turn **không chạy trên corpus công khai nào**, và Switchboard được
dùng trong **69% / 41%** số bài backchannel / end-of-turn.

**M3. "Chưa có công trình turn-taking tiếng Việt" — đang yếu đi.** `Vilex` tồn tại (§4.5): Apache-2.0,
0 sao, không dữ liệu, không trọng số, âm thanh TTS hoàn toàn. Không phá được bốn chỗ trống của
ADR-0002, nhưng phải nhắc trong Related Work.

**M4. `data-and-method.md` §8 U6 — "không ai công bố chi phí thêm ngôn ngữ thứ tư vào VAP" — cần sửa
một nửa.** Khảo sát IWSDS 2025 ghi (dẫn Sato et al. 2024a): VAP **tiền huấn luyện tiếng Anh rồi tinh
chỉnh tiếng Nhật thắng VAP huấn luyện trực tiếp bằng tiếng Nhật**. Định tính đã có; **số giờ vẫn
chưa** (bài gốc paywall, §8 V2). Nhưng kết luận vận hành đổi: **thích ứng từ checkpoint có sẵn không
còn là vùng hoàn toàn mù** — nó bị chặn bởi **giấy phép** (NC-ND), không bởi việc thiếu tiền lệ.

**M5. `data-and-method.md` §8 U7/U8 — "chưa ai phát biểu VAP chạy CPU" — đóng được một nửa.**
`inokoj/VAP-Realtime` README, nguyên văn: *"In this repository, the VAP model can operate in
real-time in a CPU environment."* Vẫn **không có hệ số thời gian thực và không có cấu hình máy**,
nên phần định lượng của U7/U8 còn mở. Đồng thời một cờ mới: README ghi trọng số *"used for only
academic purposes"* — chặt hơn MIT của phần mã.

**Bổ sung, không mâu thuẫn:** khẳng định *"không có corpus hội thoại hai kênh tiếng Việt tải công
khai miễn phí"* (`roadmap.md` §5, đã được `data-and-method.md` §4.2 sửa chính xác) **vẫn đứng** sau
lần tra 2026-09-25. Không có bộ nào mới xuất hiện; thứ gần nhất là một pool diarization tiếng Việt
gom từ YouTube/TikTok/phát thanh, vốn **vi phạm `SPEC.md` §6** ngay ở nguồn gốc và không có nhãn
lượt.

---

## 8. Không kiểm chứng được

Ghi ra để không ai tưởng đã xong. Xếp theo giá trị nếu trả lời được.

**V1. Bản CSL 2014 mở rộng thêm gì so với SIGDIAL 2013.** ScienceDirect và CORE trả **HTTP 403**;
DiVA `ECONNREFUSED` ở cả hai host; abstract bị nhà xuất bản gỡ khỏi API. Cách trả lời: thư viện
trường, hoặc luận án của Meena
(<https://kth.diva-portal.org/smash/get/diva2:906334/ATTACHMENT01.pdf>, `curl` **timeout** ngày
2026-09-25) vốn là luận án tổng hợp nên **gần như chắc chắn đính kèm nguyên bài CSL**. Đây là cách
rẻ nhất để đọc bản tạp chí một cách hợp pháp.

**V2. Sato et al. 2024a cần bao nhiêu giờ tiếng Nhật để tinh chỉnh.** IEEE Xplore
<https://ieeexplore.ieee.org/document/10800197/>, paywall. Đây là **con số quan trọng nhất còn
thiếu** cho bất kỳ quyết định nào về hướng VAP.

**V3. Hà & Grice, Journal of Pragmatics (repair initiation).** Paywall ScienceDirect. Liên quan tới
`SPEC.md` §4.2 quy tắc "ba lần hiểu sai thì chuyển người".

**V4. Có bản PhoWhisper chuyển sẵn sang CTranslate2 không.** Chưa tra. Nếu không có thì phải tự
chuyển, và phải kiểm lại WER sau chuyển đổi.

**V5. Chi phí CPU thật của `smart-turn` v3.2 trên chính laptop này.** Tác giả nói 10–100 ms; chưa ai
trong dự án đo. `reuse-audit.md` §4.1 đã cảnh báo nó là **chi phí dồn cục**, không phải mỗi khung.
Phải đo ở GĐ 2 và ghi riêng, không trộn vào trung bình.

**V6. Sharon et al. 2026 trên CPU.** Bài đo trên **NVIDIA A10G**. Nhánh ngôn điệu 5 đặc trưng gần
như chắc chắn rẻ (§5.4 đã đo phần F0), nhưng **encoder Zipformer2 70M thì không**. Nếu mượn kiến
trúc, chỉ mượn **nhánh ngôn điệu**, không mượn encoder.

**V7. Bốn thanh còn lại ở vị trí cuối lượt.** Hà & Grice chỉ đo huyền và ngang; Brunelle đo tiếng
Nam Bộ. **Không nguồn nào đo sắc, hỏi, ngã, nặng ở cuối lượt trong hội thoại điện thoại Bắc Bộ.**
Đây không phải thiếu sót của tài liệu này — đây là **chỗ trống mà chỉ số chính của Turnwise sinh ra
để lấp**.

**V8. TamilEOT: 116 cuộc gọi là bao nhiêu giờ.** Abstract không nói. Quan trọng vì nó là mốc "cần
bao nhiêu để tinh chỉnh smart-turn cho một ngôn ngữ mới". Đọc được từ chính bài (arXiv, mở) nếu ai
đó có 20 phút.

**V9. Giấy phép tập dữ liệu TurnBench và điều khoản dùng lại.** Chỉ đọc trang giới thiệu; chưa mở
repo GitHub và dataset card.

---

## 9. Khuyến nghị

### 9.1 Con đường rẻ nhất vẫn ra được kết quả công bố được, trong ~25 ngày với một người gán nhãn

Giả định nêu rõ: một người gán, ~25 ngày làm việc, laptop i5-11400H không GPU, dữ liệu dừng ở mức
6–16 người nói / 1,5–3,5 giờ. Nếu một trong các giả định đó sai, thứ tự dưới đây đổi.

**Ngày 1–3 — chốt hai thứ đang chặn, bằng ADR, trước khi chạy gì.**
(a) **ADR giấy phép**: `parselmouth` GPLv3 trên runtime, ASR nào cho B3, và lập trường với trọng số
NC. Một ADR, bốn câu hỏi, vì chúng là cùng một câu hỏi. (b) **ADR quy tắc quyết định GĐ 2**: viết
trước kết quả nào dẫn tới kết cục nào, theo `data-and-method.md` §6.5 mục 2. Không làm bước này thì
ADR chốt hướng sẽ được viết để biện minh cho thứ đã lỡ xây.

**Ngày 3–5 — sửa đơn vị đánh giá sang IPU.** `docs/progress.md` §4 đã ghi "một lượt một clip" phải
làm lại. Map Task §3.3 là tiền lệ cho cách làm. Sửa trước khi có bất kỳ con số B2/B3 nào, nếu không
ba đường cong nằm trên ba mẫu số khác nhau.

**Ngày 5–12 — thu và gán nhãn, đủ dùng chứ không đủ oai.** Mục tiêu tối thiểu để mọi thứ sau đó có
nghĩa: **≥ 12 người nói, ≥ 1,5 giờ, chia theo người nói, `S001` không vào holdout**. Trên đường đi,
gán kép **một phần** (10–15%) để có kappa — Map Task §3.4 cho thấy **kappa là thứ sinh ra trần hiệu
năng**, và không có trần thì không biết 82% là tốt hay tệ. Với một người gán, cách rẻ nhất để có
"người thứ hai" là **tự gán lại một mẫu sau hai tuần** (intra-annotator agreement) và nói rõ nó là
loại nào. Kém hơn hai người, nhưng khác hẳn không có gì.

**Ngày 12–16 — GĐ 2: chạy B1 quét dải, B2, B3 trên tập validation.** Theo đúng 11 bước của
`data-and-method.md` §6.5. Thêm hai việc mà tài liệu này bổ sung:
- **Chạy B2 zero-shot rồi ghi con số ấy xuống trước tiên.** TamilEOT cho mốc so sánh trực tiếp:
  zero-shot smart-turn v3 trên tiếng Tamil = **70,30%**. Nếu tiếng Việt ra một con số cùng bậc, đó
  là một hàng trong bảng so sánh chéo ngôn ngữ mà chưa ai có.
- **Đo sàn nhiễu trước khi tin bất kỳ delta nào.** TamilEOT đo được **0,87 điểm** giữa ba lần chạy
  cùng config cùng seed. Chạy lại ba lần, lấy khoảng đó làm sàn, và **không báo cáo cải thiện nào
  nhỏ hơn sàn**.

**Ngày 16–22 — GĐ 3, chỉ làm nhóm B ở §4.2.** Thêm **tối đa bốn** scorer trong bảng §5.5, theo thứ
tự: `silence_accumulator` → `final_f0_endpoint` → `final_contour_direction` → `tone_residual`. Mỗi
scorer thêm vào phải đi kèm **một hàng ablation** và **một bảng cắt theo sáu thanh**. Chạy trước
"Thí nghiệm D" của `data-and-method.md` §6.4 (một đặc trưng, một số AUC) để biết có đáng viết scorer
không — nó mất một buổi chứ không mất một tuần.

**Ngày 22–25 — GĐ 4 rút gọn và viết.** Năm phép thử `SPEC.md` §10 trên **hai** cấu hình, số độ trễ
lấy từ đường chạy sống. Bài viết ra có bốn thứ mà §4 cho thấy **chưa ai có**: (1) bảng lỗi cắt theo
**thanh điệu của âm tiết cuối**; (2) so sánh **cùng một kịch bản, giọng người thật với giọng TTS**,
tức phép đối chứng trả lời được câu "dữ liệu tiếng Việt của smart-turn 100% là TTS thì có sao
không"; (3) một hàng **zero-shot smart-turn trên tiếng Việt thật**, đặt cạnh con số Tamil; (4) kiểm
chứng quy tắc L%/H% của Hà & Grice trên **dữ liệu tổng đài**, không phải trên chuyện phiếm điện
thoại năm 2010.

**Bốn thứ đó là đóng góp. Không cái nào cần GPU, không cái nào cần 90 giờ dữ liệu.**

### 9.2 Đừng làm — danh sách dứt khoát

- **Đừng lấy bài Map Task làm phương pháp đề xuất.** §3.9. Lấy đặc trưng, trích dẫn, đi tiếp.
- **Đừng dựng VAP từ đầu.** 92,5 giờ hai kênh, và dự án có 9,7 phút. `data-and-method.md` §9.1 đã
  kết luận, §4.3 ở đây chỉ củng cố.
- **Đừng tinh chỉnh trọng số MaAI.** `cc-by-nc-nd-4.0`: **ND cấm bản phái sinh.** Đây là vấn đề
  pháp lý, không phải vấn đề kỹ thuật, và không có cách lách nào an toàn.
- **Đừng thêm mô hình ngôn ngữ vào đường chạy.** `SPEC.md` §11, và Sharon et al. 2026 vừa đo rằng
  thêm văn bản **làm tăng cắt lời** mà không tăng F1 (F1 0,930 → 0,909; FA% 7,8 → 10,7).
- **Đừng làm phân rã kiểu Fujisaki.** §5.3 cách D. Nó là một luận án riêng.
- **Đừng để bot chêm tiếng đệm ở học kỳ này.** §3.9 (d). Nghiệp vụ mới, vòng đánh giá mới.
- **Đừng sinh dữ liệu tiếng Việt bằng TTS để huấn luyện** (Vilex / DuplexGen). Đó chính xác là chỗ
  hỏng mà dự án đã phát hiện ở `smart-turn` (`data-and-method.md` §4.3). Dùng TTS làm **nhóm đối
  chứng** thì có; làm **dữ liệu huấn luyện** thì không.
- **Đừng báo cáo độ trễ đo trên file.** `SPEC.md` §9.3 quy tắc 4. Kể cả các con số F0 ở §5.4 của
  chính tài liệu này — chúng dùng để quyết định, không để báo cáo.
- **Đừng lấy thanh điệu cho chỉ số chính từ ASR.** §6.2 mục 2. Lấy từ nhãn người gán.
- **Đừng mở `data/holdout/`** cho tới báo cáo cuối. `.github/workflows/holdout-guard.yml` là cổng,
  không phải gợi ý.

---

*Tài liệu này chỉ mang bằng chứng. Mọi lựa chọn suy ra từ nó — chốt hướng ở `SPEC.md` §7, sửa
`SPEC.md` §2 theo M2, thêm Vilex vào Related Work theo M3, cập nhật `data-and-method.md` §8 U6/U7/U8
theo M4/M5, chốt ASR cho B3, chốt lập trường giấy phép — đều cần một ADR riêng, theo ADR-0001.*
