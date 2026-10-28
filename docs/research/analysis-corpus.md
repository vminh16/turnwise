# Bộ phân tích: nguồn hội thoại tiếng Việt tự nhiên cho turn-taking

Tài liệu này trả lời một câu hỏi: **lấy hội thoại tiếng Việt thật ở đâu để phân tích ngữ điệu kết
thúc lượt và để benchmark các decider, khi không tự thu thêm được?** Nó là bằng chứng cho ADR-0007,
không tự quyết định gì.

**Tra ngày 2026-10-28.** Tài liệu này xây tiếp `docs/research/data-and-method.md` §4 (tra
2026-09-12) và không lặp lại bảng loại trừ ở đó. Những gì chưa tự đọc được từ nguồn gốc ghi ở §6,
không ghi như sự kiện.

---

## 1. Tóm tắt

| Câu hỏi | Trả lời ngắn |
|---|---|
| Có benchmark turn-taking tiếng Việt công khai không | **Không tìm thấy.** Khảo sát IWSDS 2025 cũng không liệt kê bộ nào |
| Corpus hội thoại tiếng Việt thật, đã công bố, có chép lời | **Hai bộ, đều ở LDC, đều phải trả phí:** Babel Vietnamese (`LDC2017S01`, ~201 giờ, 2012, bốn vùng phương ngữ) và CALLFRIEND Vietnamese (`LDC96S60`, ~25 giờ, hai kênh, 1996) |
| Công trình ngữ âm học trước về ngữ điệu kết thúc lượt tiếng Việt | **Có**, nhóm Hạ Kiều Phương và Martine Grice (Köln). Đây là công trình phải trích và tái lập, không phải nguồn dữ liệu |
| Nguồn miễn phí dùng được ngay | Kho lịch sử truyền khẩu UCI *Viet Stories* (phỏng vấn, cho phép dùng cho nghiên cứu) và podcast/phỏng vấn dài. Không có nhãn, độ phủ vùng chưa kiểm |
| Đối chứng ngôn ngữ khác, không phải gán nhãn | Easy-Turn và MagicData-RAMC (Quan Thoại, cũng là ngôn ngữ có thanh điệu), TurnBench (hai kênh, có nhãn EOT/INT) |
| Đề xuất | Tầng 1 nếu mua được LDC; nếu không thì tầng 3. Gán nhãn **toàn bộ** điểm ngừng trong các cửa sổ chọn ngẫu nhiên, vài giờ là đủ. Chi tiết ở §4–§5 |

---

## 2. Tiêu chí chọn nguồn

Đặt trước khi xem nguồn, để không chọn theo thứ tình cờ tìm được:

1. **Hội thoại thật giữa hai người**, không đọc theo kịch bản, không cắt dựng mất khoảng lặng.
   Phân tích chỉ lấy đoạn có đúng hai người nói (`SPEC.md` §11 loại hội thoại từ ba người trở lên).
2. **Giữ được ranh giới lượt.** Tốt nhất là mỗi người một kênh. Nếu đơn kênh thì phải là bản ghi
   liền mạch để tách người nói được, không phải phát ngôn đã cắt sẵn cho ASR.
3. **Phủ ba miền** Bắc, Trung, Nam, và ghi được miền của từng người nói.
4. **Có quyền dùng cho nghiên cứu**, theo giấy phép hoặc điều khoản của kho lưu trữ, và không phải
   ghi âm cuộc gọi khách hàng của bất kỳ công ty nào (`SPEC.md` §6).
5. Ưu tiên theo thứ tự: **corpus đã có bài báo và có nhãn → corpus chưa có nhãn → audio phỏng vấn
   hoặc podcast đời thật.**

---

## 3. Nguồn ứng viên

### 3.1 Tầng 1: corpus đã công bố, có chép lời

| Corpus | Quy mô | Vùng | Kênh | Quyền dùng | Phù hợp |
|---|---|---|---|---|---|
| **IARPA Babel Vietnamese** [`LDC2017S01`](https://catalog.ldc.upenn.edu/LDC2017S01) | ~201 giờ điện thoại, gồm cả hội thoại lẫn phần đọc theo kịch bản; thu tại Việt Nam năm 2012; tuổi 16–64, cân bằng giới | **Bắc, Bắc Trung Bộ, Trung, Nam**, theo catalog | **Chưa xác định** (`data-and-method.md` §8, U1). 8 kHz a-law SPHERE | Ba loại thoả thuận LDC (For-Profit / Not-For-Profit / Non-Member); phí phải đăng nhập mới xem được | **Cao nhất về độ phủ**: hội thoại thật, ở Việt Nam, đủ ba miền, có chép lời. Đã dùng trong nhiều bài thuộc chương trình Babel, và trong [một bài phân đoạn hành vi hội thoại tiếng Việt](https://arxiv.org/pdf/1708.04765) chọn 22 cuộc |
| **CALLFRIEND Vietnamese** [`LDC96S60`](https://catalog.ldc.upenn.edu/LDC96S60) | ~25 giờ, 60 cuộc gọi 5–30 phút | Người Việt ở Mỹ và Canada; **chưa rõ** có ghi phương ngữ không | **Hai kênh** ulaw 8 kHz (đã đọc trường `Sample Type`, `data-and-method.md` §4.1) | LDC Non-Member Agreement; mọi người nói đều đồng ý ghi âm và tự chọn chủ đề | **Cao về tính tự nhiên**: nói chuyện phiếm với người quen, không kịch bản. Hạn chế: năm 1996, cộng đồng hải ngoại, độ phủ vùng chưa rõ |

**Công trình trước, phải trích và tái lập:**

- Hạ Kiều Phương (2012), [*Prosody in Vietnamese: Intonational form and function of short
  utterances in conversation*](https://openresearch-repository.anu.edu.au/items/7e338c44-971d-4005-9226-efa530964976),
  Asia-Pacific Linguistics, CC BY 4.0. Phân tích hội thoại điện thoại theo khung Phân tích hội thoại
  (Conversation Analysis).
- Hạ & Grice, [Speech Prosody 2010](https://mail.sprosig.org/sp2010/papers/100042.pdf): so sánh
  đường F0 của các phát ngôn một từ trong tiếng đệm, câu hỏi thông tin, **lượt kết thúc (turn
  exit)** và câu sửa chữa. Theo phần tóm tắt, ở lượt kết thúc và câu hỏi thông tin có một đường lên
  **không phụ thuộc thanh điệu từ vựng**. Đây là phát biểu gần nhất với giả thuyết `SPEC.md` §7 mà
  dự án tìm được.
- Hạ, Ebner & Grice (2016), Speech Prosody 8: hành vi người nghe trong hội thoại tiếng Việt và tiếng
  Đức. Danh sách đầy đủ ở [trang dự án Tone and Intonation in Vietnamese](https://ifl.phil-fak.uni-koeln.de/en/phonetik/forschung/projekte/tiv).

Dữ liệu của nhóm này là tiếng Bắc / Hà Nội, gồm hội thoại điện thoại, đối thoại theo nhiệm vụ và
tiếng nói trong phòng thí nghiệm. Trang dự án **không nói** dữ liệu có công khai hay không. Nếu hỏi
được tác giả, đó là nguồn tiếng Bắc đã được phân tích chuyên sâu. Dù có hỏi được hay không, kết quả
của họ vẫn là giả thuyết mà bộ phân tích phải kiểm lại, trên nhiều người nói và nhiều miền hơn.

### 3.2 Tầng 2: corpus có hội thoại nhưng không có nhãn lượt

| Nguồn | Có gì | Dùng thế nào |
|---|---|---|
| **VoxVietnam** ([arXiv 2501.00328](https://arxiv.org/pdf/2501.00328), [HF](https://huggingface.co/datasets/hustep-lab/VoxVietnam-Dataset)) | 187.980 phát ngôn, 1.406 người nói, 261 giờ; hơn 80% là tiếng nói tự phát; nguồn gồm phỏng vấn, gameshow, podcast | Phát ngôn đã cắt, nên **không** dùng trực tiếp được. Có thể dùng làm danh mục để tìm video phỏng vấn gốc. Chưa rõ có nhãn vùng hay ID video không |
| **SpeechData.ai Vietnamese conversational** ([HF](https://huggingface.co/datasets/SpeechDataAI/vietnamese-conversational-speech)) | Theo trang: 2.000 giờ hội thoại tự phát hai người, **hai kênh**, metadata vùng, 200 người nói, chép lời có mốc thời gian | **Thương mại.** Có mẫu miễn phí nếu xin. Chỉ đáng dùng cho pilot, và chỉ khi điều khoản của mẫu cho phép dùng nghiên cứu |
| ViMD / LSVSC (đa phương ngữ, ~100 giờ) | Phát ngôn đơn lẻ, có nhãn tỉnh hoặc vùng | Không phải hội thoại. Chỉ dùng làm mốc tham chiếu F0 của từng thanh theo vùng, nếu cần |

Nguồn đã loại vì đơn kênh và đã cắt thành phát ngôn: VIVOS, VLSP, BUD500, VietSuperSpeech,
GigaSpeech 2, YODAS (`data-and-method.md` §4.1). Bộ test tiếng Việt của `smart-turn` có 1.004 mẫu,
**100% là giọng tổng hợp** (`data-and-method.md` §4.3). Chỉ báo số trên bộ này làm tham khảo.

### 3.3 Tầng 3: audio phỏng vấn và podcast đời thật

| Nguồn | Có gì | Rủi ro |
|---|---|---|
| **UCI Libraries — *Viet Stories: Vietnamese American Oral History Project*** ([Calisphere](https://news.lib.uci.edu/libraries-news/viet-stories-oral-history-project-now-calisphere)) | Hơn 220 cuộc phỏng vấn lịch sử truyền khẩu, có audio hoặc video; một số có bản chép tiếng Việt. Điều khoản: dùng cho *"private study, scholarship, or research"*; muốn dùng ngoài phạm vi đó phải xin phép `spcoll@uci.edu` | Thể loại phỏng vấn nên lượt lời không cân xứng. Chủ yếu người Việt hải ngoại, nhiều khả năng nghiêng về giọng Nam. Phải kiểm từng mục |
| **Podcast trò chuyện dài**, ví dụ *Have A Sip* (Vietcetera, tập 60–90 phút), podcast của đài địa phương như NTV Nghệ An cho miền Trung | Hội thoại ngang hàng hơn phỏng vấn | Chưa kiểm: mức cắt dựng, nhạc nền, vùng của khách mời, điều khoản sử dụng. **Chỉ là ứng viên cho pilot**, chưa phải nguồn đã chọn |

Mọi nguồn ở tầng 3 là đơn kênh, phải tách người nói tự động rồi sửa tay. Đoạn nói đè trộn hai
giọng, nên phần phân tích ngắt lời ở tầng này yếu hơn so với dữ liệu hai kênh.

### 3.4 Đối chứng liên ngôn ngữ, dùng nguyên nhãn có sẵn

| Bộ | Ngôn ngữ | Có gì | Quyền dùng |
|---|---|---|---|
| [Easy-Turn](https://github.com/aslp-lab/easy-turn) ([arXiv 2509.23938](https://arxiv.org/abs/2509.23938v1)) | Quan Thoại | Tập train 1.145 giờ (cả thật lẫn tổng hợp), bốn trạng thái complete / incomplete / backchannel / wait, testset công khai | Chưa đọc giấy phép |
| [MagicData-RAMC](https://openslr.org/123/) ([arXiv 2203.16844](https://arxiv.org/pdf/2203.16844)) | Quan Thoại | 180 giờ hội thoại hai người qua điện thoại di động, 16 kHz, có mốc hoạt động giọng nói của từng người | CC BY-NC-ND 4.0: được đánh giá, **không** được phát hành nhãn dựng trên nó |
| [TurnBench](https://github.com/SesameAILabs/turnbench) | Chưa xác định | 154 cuộc hai người, ~30 giờ, 106 người nói, hai kênh, nhãn EOT và INT do ba người gán | Mã nguồn MIT; dữ liệu phi thương mại, cấm nhân bản giọng; nhãn tập test được giữ kín |

Quan Thoại là ngôn ngữ có thanh điệu và có dữ liệu tốt, nên đây là phép kiểm rẻ nhất cho câu hỏi:
hiện tượng ở tiếng Việt là đặc thù tiếng Việt, hay chung cho ngôn ngữ có thanh điệu.

---

## 4. Đề xuất thành phần bộ phân tích

**Phương án A, nếu mua được dữ liệu LDC:**

1. Babel Vietnamese là nguồn chính, **nếu** mỗi phía cuộc gọi nằm ở kênh riêng (U1). Lấy mẫu phân
   tầng theo bốn vùng của Babel, gộp thành ba miền khi báo cáo: Bắc Trung Bộ tính vào Trung.
2. CALLFRIEND Vietnamese là nguồn phụ: hai kênh chắc chắn, tự nhiên nhất.
3. Đối chứng: Easy-Turn testset và RAMC.

**Phương án B, nếu không mua được:**

1. Tầng 3: Viet Stories cộng hai hoặc ba podcast, chọn sao cho có đủ ba miền.
2. Tách người nói tự động rồi sửa tay. Báo rõ phần ngắt lời có độ tin cậy thấp hơn.
3. Đối chứng giữ nguyên như phương án A.

Hai phương án dùng **cùng** hướng dẫn gán nhãn và cùng quy tắc lấy mẫu (§5), để chuyển từ B sang A
không phải gán lại.

---

## 5. Lấy mẫu sao cho không thiên lệch

Mục tiêu là đo hội thoại **như nó tự nhiên diễn ra**. Mọi quy tắc dưới đây chặn một cách mà người
gán vô tình làm lệch kết quả.

1. **Chọn hội thoại trước khi nghe.** Bốc ngẫu nhiên từ danh mục, phân tầng theo miền và giới; ghi
   hạt giống ngẫu nhiên vào manifest.
2. **Chọn cửa sổ ngẫu nhiên trong hội thoại**, ví dụ một đoạn liên tục vài phút, bỏ qua phần chào
   hỏi ở đầu. Độ dài cửa sổ đặt trong config, không cố định trong tài liệu.
3. **Gán nhãn toàn bộ điểm ngừng trong cửa sổ.** Không chọn khoảnh khắc "đáng chú ý", không bỏ đoạn
   "chán". Chọn lọc là cách nhanh nhất để thổi phồng tỉ lệ ngắt lời hoặc tiếng đệm.
4. **Không lọc theo chủ đề.** Chủ đề và thể loại ghi thành metadata để phân tích sau, không dùng làm
   tiêu chí chọn. Chỉ loại theo **chất lượng âm thanh** (nhạc nền, cắt dựng, quá ồn), và ghi lý do
   cho từng lần loại.
   Riêng tiêu chí chọn **nguồn** thì có một ngoại lệ, vì lý do quyền riêng tư chứ không vì chủ đề:
   không dùng các chương trình mà một cá nhân riêng tư kể chuyện sức khoẻ hay tâm lý của chính họ.
5. **Giới hạn đóng góp của từng người nói**, để vài người nói nhiều không quyết định kết quả. Mức
   trần đặt trong config.
6. **Ghi trước kế hoạch phân tích**: phép thử nào, ngưỡng ý nghĩa nào, trước khi mở tập dev
   (`data-and-method.md` §6.5 mục 2).
7. **Chia tập theo người nói và theo hội thoại**, khoá holdout một lần (`.claude/rules/training.md`).
8. **Chuẩn hoá F0 theo từng người nói** trước khi gộp (`AGENTS.md`, Gotchas).

---

## 6. Cần bao nhiêu để có ý nghĩa thống kê

Suy từ chỉ số chính chứ không từ mô hình, theo đúng cách `data-and-method.md` §5.3 đã làm. Bốn
giả định dưới đây đều là giả định:

- **G1.** Đơn vị là **điểm ngừng**: mỗi khoảng lặng giữa hai đoạn nói của cùng một người, hoặc mỗi
  chỗ đổi người nói. Nhãn: giữ lượt / chuyển lượt / tiếng đệm / ngắt lời / khác.
- **G2.** Phân tích chính là tỉ lệ chuyển lượt và tỉ lệ lỗi của decider, tách theo **6 thanh** của
  âm tiết cuối. Mỗi thanh cần cỡ **100 điểm chuyển lượt và 100 điểm giữ lượt**. Với 100 trên 100,
  phép so hai tỉ lệ ở α = 0,05 phát hiện được chênh lệch 20 điểm phần trăm với power khoảng 0,9,
  và chênh lệch 15 điểm với power khoảng 0,67 (tính quanh mức 20–40%).
- **G3.** Phân tích theo miền × thanh có 18 ô, ít sự kiện hơn mỗi ô. Báo cáo bằng mô hình hồi quy
  logistic có hiệu ứng ngẫu nhiên theo người nói, kèm khoảng tin cậy bootstrap lấy mẫu theo người
  nói. Không so từng ô riêng lẻ.
- **G4.** **Thanh hiếm quyết định số giờ, không phải tổng số sự kiện.** Thanh ngã ở cuối lượt nhiều
  khả năng hiếm nhất. Pilot sẽ đo tần suất thật.

Ở mật độ khoảng 400 sự kiện mỗi giờ (`data-and-method.md` §5.3, G3; con số lấy từ tiếng Anh) thì
cần **khoảng 4–6 giờ đã gán nhãn** cho dev cộng holdout, và **ít nhất khoảng 30 người nói, mỗi miền
khoảng 10 người**. Đây là ước lượng. Pilot ở §7 thay nó bằng số đo thật.

---

## 7. Bắt đầu gán nhãn được chưa

**Chưa, với bộ vàng. Pilot thì bắt đầu được.** Còn bốn việc chặn, xếp theo thứ tự:

1. **Quyền truy cập LDC**: trường có tư cách thành viên LDC không; phí của `LDC2017S01` và
   `LDC96S60`; Babel có mấy kênh (U1). Câu trả lời quyết định chọn phương án A hay B.
2. **Hướng dẫn gán nhãn cho hội thoại người với người.** `docs/annotation-guide.md` v1.2 viết cho
   cuộc gọi đóng vai với bot; nó cần định nghĩa lại điểm ngừng và bỏ khái niệm "track bot".
3. **Adapter đánh giá**: `evaluation/golden.py` chia lượt theo `bot_speaking`. Hội thoại người với
   người cần một chế độ mà lần lượt mỗi người đóng vai "khách", người kia là bên nghe.
4. **Pilot khoảng 1 giờ** trên một nguồn tầng 3 (miễn phí), để đo: số giờ gán nhãn cho mỗi giờ
   audio, tỉ lệ lỗi tách người nói, tần suất từng thanh ở cuối lượt.

---

## 8. Chưa kiểm chứng

- **U1** (kế thừa): Babel Vietnamese có tách mỗi phía cuộc gọi ra kênh riêng không, và bản chép có
  mốc thời gian không.
- **U2** (kế thừa): phí của hai corpus LDC.
- **U13.** CALLFRIEND Vietnamese có ghi vùng phương ngữ của người nói không.
- **U14.** Dữ liệu của nhóm Hạ & Grice có chia sẻ được không.
- **U15.** Giấy phép của Easy-Turn testset, và ngôn ngữ của TurnBench.
- **U16.** VoxVietnam có công bố ID video gốc và nhãn vùng không.
- **U17.** Điều khoản của mẫu miễn phí SpeechData.ai.
- **U18.** Mức cắt dựng và độ phủ vùng thật của từng podcast ở tầng 3.
