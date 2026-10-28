# Hướng dẫn gán nhãn v2.0: hội thoại tự nhiên giữa hai người

Tài liệu cho người lập danh mục và người gán nhãn **bộ phân tích** (ADR-0007). Nó định nghĩa
**lấy hội thoại nào, nghe đoạn nào, gán nhãn gì, quyết định ca khó ra sao, đo độ đồng thuận thế
nào**.

`SPEC.md` đúng hơn tài liệu này. Nguồn và cỡ mẫu ở `docs/research/analysis-corpus.md`; tài liệu
này không lặp lại.

Phiên bản hướng dẫn: **2.0** (2026-10-28). Các bản 1.x (`docs/annotation-guide.md`) chỉ dành cho
bộ kiểm thử sản phẩm, tức cuộc gọi đóng vai có track bot. Mỗi file nhãn ghi phiên bản đã dùng;
đổi quy tắc là tăng phiên bản (§7.4).

---

## 1. Dữ liệu này dùng để làm gì

Bộ phân tích trả lời câu hỏi: **trong hội thoại tiếng Việt tự nhiên, ở cuối mỗi đoạn nói, người
kia nhận lượt hay người nói còn tiếp; và cuối đoạn đó nghe ra sao theo thanh điệu và theo miền?**
Mọi decider (B1, B2, B3, hệ đề xuất) được chấm trên cùng các nhãn này.

Khác bản 1.x ở ba điểm:

1. **Nhãn mô tả việc con người đã làm, không mô tả việc bot lẽ ra phải làm.** Không có bot, không
   có "đúng" hay "sai". Người gán ghi lại điều đã xảy ra.
2. **Hai người nói ngang hàng.** Cả hai đều được gán nhãn, theo cùng một bộ nhãn.
3. **Người gán không chọn đoạn để nghe.** Hội thoại và cửa sổ do máy bốc ngẫu nhiên (§3). Người
   gán gán nhãn **mọi** đoạn nói trong cửa sổ, kể cả đoạn nghe chán hoặc khó.

Điều quan trọng nhất của bộ này là **sự tự nhiên**. Không lọc theo chủ đề, không bỏ chỗ nói vấp,
không "làm sạch" chỗ nói chồng. Chỗ hai người cùng nói, chỗ ngắt lời, chỗ ậm ừ chính là dữ liệu.

---

## 2. Danh mục: lập trước khi nghe

### 2.1 Nguồn của đợt pilot

Đợt pilot dùng **UCI Libraries, *Viet Stories: Vietnamese American Oral History Project***, trên
Calisphere. Lý do chọn:

- Kho lưu trữ của một thư viện đại học. Điều khoản nói rõ tư liệu được cung cấp cho *"private
  study, scholarship, or research"*.
- Phỏng vấn kể chuyện đời không theo kịch bản, có phỏng vấn bằng tiếng Việt.
- Metadata ghi **năm sinh và nơi sinh** của người kể. Vì vậy miền được gán theo hồ sơ, trước khi
  ai nghe audio (§2.3).
- Miễn phí.

Giới hạn, ghi ngay từ đầu để không quên khi đọc kết quả:

- Đây là phỏng vấn nên lượt lời không cân xứng: người kể nói dài, người phỏng vấn hỏi ngắn.
- Người kể phần lớn là người Việt hải ngoại lớn tuổi, đã sống nhiều năm ở Mỹ.
- Nhiều khả năng nghiêng về giọng Nam.
- Audio chỉ có một kênh, nên phải tự tách người nói.

Pilot đo những giới hạn này bằng số; không đoán trước.

Repo **không** chứa audio của nguồn này và không bao giờ chứa (`AGENTS.md`, Off-Limits). Chỉ có
mã mục, mốc thời gian, nhãn và manifest.

### 2.2 Lập danh mục

File: `data/manifests/analysis-catalog.csv`. Mẫu cột ở `data/manifests/analysis-catalog.template.csv`.

Quy tắc duy nhất: **liệt kê hết, không chọn.** Lọc trên Calisphere theo bộ sưu tập Viet Stories và
ngôn ngữ Vietnamese, rồi chép **mọi** mục ra, kể cả mục trông có vẻ không hay. Danh mục là khung lấy
mẫu. Thiếu một mục vì "trông không hay" là đã thiên lệch trước khi bốc.

| Cột | Ghi gì |
|---|---|
| `source` | `viet-stories` |
| `item_id` | mã của kho, ví dụ `VAOHP0087` |
| `url` | link của mục trên Calisphere |
| `language` | `vi`, `en` hay `mixed`, theo metadata. Chỉ `vi` được bốc |
| `birth_year` | theo metadata; để trống nếu không có |
| `birthplace` | chép nguyên văn metadata, ví dụ `Huế` |
| `province` | tỉnh hiện nay tương ứng; để trống nếu không xác định được |
| `region` | `north`, `central`, `south` hay `unknown`, theo §2.3 |
| `restricted` | `yes` nếu kho ghi hạn chế truy cập. Mục `yes` không được bốc |
| `notes` | bất cứ điều gì từ metadata, ví dụ có hai người kể |

### 2.3 Miền: từ hồ sơ, không từ tai

`region` gán theo **nơi sinh trong metadata**, chia ba vùng phương ngữ:

| Vùng | Tỉnh |
|---|---|
| Bắc | Bắc Bộ, đến Thanh Hoá |
| Trung | từ Nghệ An đến Thừa Thiên Huế |
| Nam | từ Quảng Nam trở vào |

Cách chia này là cách chia ba vùng phổ biến trong phương ngữ học tiếng Việt (Hoàng Thị Châu,
*Phương ngữ học tiếng Việt*, 2004). **Chưa đối chiếu bản gốc trong dự án này.** Ranh giới ở Thanh
Hoá và ở Quảng Nam, Quảng Ngãi còn tranh luận. Vì vậy cột `province` luôn được giữ, để sau này đổi
cách chia mà không phải mở lại metadata.

Tại sao không gán theo tai: nếu nghe trước rồi mới quyết định ai thuộc miền nào, người gán sẽ vô
tình chọn những người "nghe rõ giọng", tức chọn theo đúng biến đang đo. Sau khi gán xong, người gán
**được** ghi giọng nghe thấy vào `dialect_heard` (§5.4). Hai cột này lệch nhau thì đó là thông tin,
không phải lỗi. Ví dụ một người sinh ở Huế nhưng lớn lên ở Sài Gòn.

`unknown` không được đoán. Mục `unknown` vẫn ở trong danh mục và được bốc vào một nhóm riêng.

---

## 3. Lấy mẫu: máy bốc, người không chọn

```bash
uv run python -m evaluation.analysis_sample rank      # xếp hạng ngẫu nhiên mọi mục đủ điều kiện
uv run python -m evaluation.analysis_sample prepare   # cửa sổ + TextGrid cho các mục đã có audio
uv run python -m evaluation.analysis_sample status    # đã gán bao nhiêu, theo vùng và theo nhãn
```

### 3.1 Bốc hội thoại

`rank` gán mỗi mục một khoá ngẫu nhiên bằng `sha256(seed:source:item_id)`, rồi xếp theo khoá
trong từng vùng. Kết quả nằm ở `data/manifests/analysis-sample.csv`. Hạt giống đặt trong
`configs/default.yaml` (`analysis_sample.seed`) và được commit.

Khoá chỉ phụ thuộc mã mục, nên bổ sung danh mục sau **không** làm đổi thứ hạng của các mục đã có.

Người gán **làm theo thứ hạng**, mỗi vùng từ hạng 1 trở xuống, cho tới khi đủ số cửa sổ mỗi vùng
(`analysis_sample.windows_per_region`). Không nhảy hạng.

Một mục chỉ được **bỏ qua** vì một trong các lý do sau, và lý do được ghi vào cột `excluded` của
`analysis-sample.csv`:

| `excluded` | Khi nào |
|---|---|
| `no_audio` | kho không có audio, hoặc audio không tải được |
| `not_two_party` | cửa sổ có từ ba người nói trở lên, không có ai nói, hoặc chỉ một người nói suốt (`SPEC.md` §11) |
| `music` | nhạc nền hoặc thuyết minh đè lên lời |
| `edited` | có dấu hiệu cắt dựng làm mất khoảng lặng |
| `unintelligible` | quá ồn, quá rè, không chép nổi lời |
| `not_vietnamese` | cửa sổ chủ yếu không phải tiếng Việt |
| `private_sensitive` | người kể nói về sức khoẻ hay tâm lý của chính họ ở mức riêng tư (`analysis-corpus.md` §5 mục 4) |
| `too_short` | máy ghi: hội thoại không đủ dài cho cửa sổ sau khi bỏ đầu và cuối (§3.2) |

**Không có** lý do "chủ đề không hợp", "nói chán", "ít ngắt lời". Bỏ một mục thì lấy mục hạng kế
tiếp của **cùng vùng**.

### 3.2 Bốc cửa sổ trong hội thoại

Mỗi hội thoại chỉ có **một** cửa sổ. Như vậy mỗi người kể đóng góp đúng một cửa sổ: đó là mức trần
đóng góp theo người nói (`analysis-corpus.md` §5 mục 5).

`prepare` chọn vị trí cửa sổ bằng một bộ sinh số ngẫu nhiên gieo từ cùng khoá, nên vị trí tái lập
được. Cửa sổ dài `window_s` giây. Vị trí của nó nằm trong khoảng từ sau `skip_head_s` giây đầu
(phần chào hỏi, giới thiệu, xin đồng ý) đến trước `skip_tail_s` giây cuối.

Trước cửa sổ có `context_s` giây **ngữ cảnh**: được nghe, không được gán nhãn. Ngữ cảnh cần cho
đoạn nói đầu tiên trong cửa sổ, vì nhãn của một đoạn phụ thuộc vào cái xảy ra trước nó.

Mọi con số ở đây đặt trong `configs/default.yaml`, không đặt trong tài liệu.

---

## 4. TextGrid

Mở bằng Praat, như `docs/runbook/annotate.md`. `prepare` sinh một file `.TextGrid` cạnh file audio
(`data/raw/analysis/<source>/<item_id>.<đuôi>`). Lệnh **không bao giờ ghi đè** một TextGrid đã có.

| Lớp | Nội dung | Ai làm |
|---|---|---|
| `window` | `context`, rồi `label` | máy; không sửa |
| `draft` | các khoảng có tiếng, tính theo năng lượng trên audio đơn kênh | máy; chỉ để nhìn |
| `A` | đoạn nói của **người kể** (người có nơi sinh trong danh mục) | người gán |
| `B` | đoạn nói của người kia, thường là người phỏng vấn | người gán |
| `nonspeech` | tiếng không phải lời: `laugh`, `cough`, `breath`, `music`, `noise`, `other` | người gán, tuỳ chọn |

Lớp `A` và `B` được sinh sẵn **cùng ranh giới với `draft`, để trống chữ**. Với mỗi khoảng, người
gán gõ nhãn vào **đúng lớp của người đang nói** và để trống lớp kia. Một khoảng trống là im lặng.
Khi hai người nói chồng nhau, cả hai lớp đều có chữ ở cùng thời điểm. Đó là lý do có hai lớp chứ
không phải một.

Ranh giới của `draft` sai thì sửa trên `A` hoặc `B`, không sửa `draft`.

### 4.1 Cách viết một khoảng

```
<nhãn> [thuộc tính ...] | <lời>
```

Ví dụ: `S | hồi đó tôi ở huế`, `H filled | thì ờ`, `BC | dạ`, `I | nhưng mà chị`.

Một **đoạn nói** (IPU) là một khoảng liền tiếng của **một** người. Khoảng lặng dưới
`annotation.ipu_merge_ms` thì gộp vào đoạn nói, theo Heldner & Edlund (2010), như bản 1.x.

---

## 5. Nhãn

### 5.1 Nhãn mở đầu: đoạn nói này **bắt đầu** thế nào

Mỗi IPU mang đúng một nhãn. Nhãn trả lời câu hỏi: **so với người kia, đoạn nói này bắt đầu như
thế nào?**

Bộ nhãn lấy theo sơ đồ chuyển lượt của Gravano & Hirschberg (2011), mà các tác giả phát triển từ
Beattie (1982). Đó là sơ đồ được dùng nhiều nhất cho dữ liệu hội thoại có gán nhãn ngữ điệu. Dự án
**dùng lại, không tự đặt ra**, để kết quả so được với các bài trước. Định nghĩa dưới đây là bản
dịch của dự án và **phải được đối chiếu lại với bài gốc** trước khi chốt κ ở §7.

| Nhãn | Tên | Định nghĩa |
|---|---|---|
| `H` | giữ lượt (hold) | cùng người nói tiếp sau một khoảng lặng; người kia không nhận lượt trong khoảng lặng đó |
| `S` | chuyển lượt êm (smooth switch) | người này bắt đầu **sau khi** người kia đã dứt, và lượt của người kia **đã trọn** |
| `O` | chuyển lượt chồng (overlapping switch) | người này bắt đầu **khi người kia còn đang nói**, nhưng lượt của người kia đã trọn hoặc gần trọn; người kia dứt mà không bị cắt dở |
| `PI` | ngắt trong lúc ngừng (pause interruption) | người này bắt đầu **trong khoảng lặng** của người kia, khi lượt người kia **chưa trọn** |
| `I` | ngắt lời (interruption) | người này bắt đầu **khi người kia đang nói** và lượt người kia chưa trọn; người kia **dừng lại**, bỏ dở |
| `BI` | chen vào không thành (butting-in) | như `I`, nhưng người kia **không dừng**, nói tiếp; người này bỏ cuộc |
| `BC` | tiếng đệm (backchannel) | người nghe báo đang nghe ("dạ", "ừ", "vâng", "thế à"), **không** giành lượt; bắt đầu trong khoảng lặng của người kia |
| `BC_O` | tiếng đệm chồng | như `BC`, nhưng chồng lên lúc người kia đang nói |
| `X` | không xếp loại được | dùng khi không nghe rõ, hoặc khi thật sự không thuộc nhãn nào; ghi lý do vào `notes` của `status` |

IPU **đầu tiên** của mỗi người trong cửa sổ cũng được gán nhãn, dựa vào ngữ cảnh. Đó là lý do có
lớp `context`.

### 5.2 Kết thúc lượt được suy ra, không gán tay

Câu hỏi của chỉ số chính, "ở cuối đoạn nói này, có chuyển lượt không", **không** được gán thẳng. Nó
được suy từ nhãn mở đầu của đoạn kế tiếp (`evaluation.analysis_sample.endings`):

| Sau IPU *k* của người X, việc kế tiếp là | Kết thúc của IPU *k* |
|---|---|
| IPU tiếp theo của chính X, nhãn `H` | `hold` |
| IPU của người kia, nhãn `S` hoặc `O` | `shift` |
| IPU của người kia, nhãn `PI` | `interrupted`: X chưa xong mà bị lấy lượt |
| IPU của người kia, nhãn `I`, chồng lên IPU *k* | `interrupted` |
| hết cửa sổ | `censored`: không biết, không chấm |

`BC`, `BC_O` và `BI` của người kia **không** quyết định kết thúc của IPU *k*. Chúng được ghi thành
cờ đi kèm, vì một tiếng "dạ" xen vào không lấy lượt của X.

Gán nhãn mở đầu thay vì gán thẳng kết thúc có hai lợi ích. Người gán chỉ phải quyết định một lần
cho mỗi IPU. Và cùng bộ nhãn cho ra cả chỉ số chuyển lượt lẫn phân tích ngắt lời (`I`, `PI`, `BI`).

### 5.3 Thuộc tính

Chỉ điền khi đúng.

- `filled`: IPU **kết thúc** bằng tiếng ngập ngừng (`ờ`, `ừm`, `à`). Cần để tách ngập ngừng có
  tiếng khỏi khoảng lặng thuần.
- `laugh`: IPU có tiếng cười đè lên lời.
- `question`: IPU là một câu hỏi, xét theo nội dung. Câu hỏi ở cuối lượt có ngữ điệu riêng
  (Hạ & Grice 2010), nên phân tích phải tách được nó.

### 5.4 Ghi chép sau khi gán xong cửa sổ

Ghi vào `analysis-sample.csv`:

- `dialect_heard`: giọng nghe được của người A (`north`, `central`, `south`, `mixed`, `unsure`).
  Chỉ điền **sau** khi gán xong (§2.3).
- `annotator`: mã người gán.
- `guide_version`: `2.0`.
- `minutes_spent`: số phút đã gán. Đây là con số pilot cần nhất.

---

## 6. Ca khó

### 6.1 Chép lời

Chép như bản 1.x §5.1:

- chữ thường, đủ dấu thanh, không dấu câu;
- số viết bằng chữ, như người nói đọc;
- tiếng đệm dùng bộ cố định `dạ`, `vâng`, `ừ`, `ừa`, `ờ`, `ừm`, `à`, `ạ`, `hả`, `ơ`;
- từ bị cắt dở viết `tá-`, chỗ không nghe rõ viết `[x]`.

Thanh của âm tiết cuối **không gán tay**: nó được đọc từ lời bằng
`evaluation.roleplay.final_syllable_tone`. Vì vậy âm tiết cuối của mỗi IPU phải chép đủ dấu. Ở một
IPU kết thúc bằng `[x]` thì thanh là `unknown`, và nhãn mở đầu vẫn gán bình thường.

Người kể hải ngoại hay chêm tiếng Anh. Từ tiếng Anh chép như thường gặp (`ok`, `school`). Thanh
của âm tiết đó là `unknown`, đúng như ý muốn.

### 6.2 Thanh điệu theo chữ viết

Như bản 1.x §5.3: thanh lấy theo **chính tả**, kể cả khi người Nam đọc hỏi và ngã như nhau. Việc
tách kết quả theo miền là của `evaluation/`, không phải của người gán.

### 6.3 Trọn hay chưa trọn

Phân biệt `S` và `PI`, hay `O` và `I`, đều phụ thuộc một phán đoán: lượt của người kia **đã trọn**
chưa. Quy tắc:

- **Nghe hết phần sau rồi mới quyết.** Người kia quay lại nói tiếp đúng ý đang dở ("…thì ở Huế,
  à mà không, ở…") là chưa trọn. Người kia im và để người này dẫn là đã trọn.
- **Xét theo nội dung và cú pháp, không theo độ cao giọng.** Không được dùng "nghe giọng đi xuống"
  để quyết định "đã trọn". Ngữ điệu cuối lượt chính là biến đang đo. Gán nhãn theo ngữ điệu là đo
  một thứ bằng chính nó.
- Câu hỏi đã hỏi xong thì trọn, kể cả khi người kia trả lời rất nhanh.
- Cụm từ bị bỏ lửng ("…mà ông ấy thì…") là chưa trọn.

### 6.4 Bảng ca khó

| Tình huống | Nhãn |
|---|---|
| Người kể dừng 2 giây giữa câu chuyện rồi kể tiếp, người phỏng vấn im | IPU sau của người kể: `H` |
| Người kể dừng giữa câu, người phỏng vấn hỏi chen vào, người kể bỏ dở và trả lời | IPU của người phỏng vấn: `PI` |
| Người kể đang nói, người phỏng vấn nói đè, người kể dừng lại | `I` |
| Người kể đang nói, người phỏng vấn nói đè, người kể vẫn nói tiếp, người phỏng vấn im | `BI` |
| "dạ" của người phỏng vấn trong lúc người kể ngừng hơi, người kể kể tiếp | `BC`; IPU sau của người kể: `H` |
| "dạ" đè lên lúc người kể đang nói | `BC_O` |
| Người kể hỏi xong, người phỏng vấn đáp sau một khoảng lặng | `S` |
| Người kể chưa nói hết từ cuối, người phỏng vấn đã bắt đầu hỏi câu tiếp, người kể dứt tự nhiên | `O` |
| "dạ, thế còn…" sau khi người kể xong: tiếng đệm rồi hỏi luôn | một IPU, `S`, không phải `BC` |
| "ừ ừ ừ" liền nhau | một IPU |
| Hai người cùng bắt đầu nói sau một khoảng lặng, một người nhường | người nhường: `BI`; người tiếp tục: `S` |
| Tiếng cười, không có lời | không phải IPU; gán vào `nonspeech` |

Ca "dạ" vẫn là ca khó nhất, như ở bản 1.x. **Không bao giờ gán nhãn theo từ.** Cùng một chữ "dạ"
có thể là `BC` hoặc mở đầu của một `S`. Chỉ có cái xảy ra sau đó mới phân biệt được hai trường hợp.

### 6.5 Ranh giới thời gian

Như bản 1.x §5.4:

- Ranh giới đặt ở âm thanh lời nói đầu tiên và cuối cùng.
- Không tính hơi thở vào IPU.
- Không cắt giữa một âm tiết.
- Nhìn phổ, không chỉ nghe.

Với audio đơn kênh, ở đoạn nói chồng **không** cố tách chính xác chỗ một người dừng. Ghi ranh giới
theo chỗ nghe được giọng thứ hai biến mất. Đây là giới hạn của nguồn đơn kênh, đã nêu ở
`analysis-corpus.md` §3.3.

---

## 7. Quy trình và độ đồng thuận

### 7.1 Ba lượt

1. **Máy**: `rank`, rồi `prepare`.
2. **Người gán A**:
   - chia các khoảng sang lớp `A` hoặc `B`;
   - sửa ranh giới;
   - gõ nhãn và lời;
   - điền §5.4.
3. **Người gán B**, trên một phần các cửa sổ, **độc lập**, không xem nhãn của A.

Người gán không được biết cửa sổ thuộc tập nào (`dev` hay `holdout`). Người gán không được xem kết
quả của bất kỳ decider nào trên cửa sổ đó trước khi gán xong.

### 7.2 Phần gán kép

Đề xuất **20% số cửa sổ**, chọn ngẫu nhiên có hạt giống, rải đều theo vùng, như bản 1.x §6.2. Riêng
pilot: gán kép **2 cửa sổ** để ước lượng κ sớm, trước khi đầu tư thêm giờ gán.

### 7.3 Đo gì

| Đại lượng | Trên | Ghi chú |
|---|---|---|
| Cohen's κ | nhãn mở đầu §5.1 | trên các IPU mà hai người có ranh giới khớp |
| κ riêng | cặp `S`/`PI` và cặp `O`/`I` | hai cặp phụ thuộc phán đoán "trọn hay chưa", dễ lẫn nhất |
| κ riêng | cặp `BC`/`S` trên IPU chỉ gồm một tiếng đệm | như bản 1.x |
| Tỉ lệ ranh giới khớp | điểm cuối IPU | dung sai đặt trong `configs/` |

Ngưỡng đề xuất **κ ≥ 0,7** (Landis & Koch 1977: "substantial"). Dưới ngưỡng thì không gán tiếp:
đọc ma trận nhầm lẫn, viết thêm quy tắc vào §6, tăng phiên bản.

### 7.4 Phiên bản và holdout

Quy tắc như bản 1.x §6.4. Mỗi quyết định sinh ra một quy tắc mới thì tăng phiên bản (2.1, 2.2,
…). Sau khi holdout của bộ phân tích đã khoá, nhãn holdout không sửa nữa.

---

## 8. Pilot: đo cái gì

Pilot gồm `windows_per_region` cửa sổ mỗi vùng, khoảng 1 giờ audio. Nó trả lời bốn câu, bằng số:

1. **Công gán**: số phút gán cho mỗi phút audio (`minutes_spent`).
2. **Tỉ lệ bỏ** theo từng lý do của §3.1. Tỉ lệ `not_two_party` hay `edited` cao là dấu hiệu nguồn
   không dùng được.
3. **Tần suất từng thanh** ở cuối các IPU có kết thúc `shift` và `hold`. Thanh hiếm nhất quyết
   định cần bao nhiêu giờ (`analysis-corpus.md` §6, G4).
4. **κ** trên 2 cửa sổ gán kép, và **độ phủ vùng thật**: mỗi vùng có đủ mục `vi` không bị hạn
   chế không.

Nếu vùng Trung hay Bắc không đủ mục, pilot cũng là bằng chứng để chọn thêm nguồn thứ hai, thay vì
đoán trước.

---

## Nguồn

- Gravano, A. & Hirschberg, J. (2011). Turn-taking cues in task-oriented dialogue. *Computer Speech
  & Language* 25(3), 601–634. Nguồn của bộ nhãn §5.1. **Viết từ trí nhớ, chưa đối chiếu toàn văn
  trong phiên này.**
- Beattie, G. W. (1982). Turn-taking and interruption in political interviews. *Semiotica* 39.
  Sơ đồ gốc mà Gravano & Hirschberg phát triển.
- Heldner, M. & Edlund, J. (2010). Pauses, gaps and overlaps in conversations. *Journal of
  Phonetics* 38(4), 555–568. Như bản 1.x.
- Hạ, K. P. & Grice, M. (2010). Speech Prosody 2010. `analysis-corpus.md` §3.1.
- Hoàng Thị Châu (2004). *Phương ngữ học tiếng Việt*. NXB Đại học Quốc gia Hà Nội. Cách chia ba
  vùng ở §2.3. **Chưa đối chiếu bản gốc.**
- Landis, J. R. & Koch, G. G. (1977). *Biometrics* 33(1), 159–174.
- UCI Libraries, *Viet Stories*: [tin công bố](https://news.lib.uci.edu/libraries-news/viet-stories-oral-history-project-now-calisphere),
  [trang dự án](https://sites.uci.edu/vaohp/about),
  [hồ sơ lưu trữ MS-SEA-069](https://oac.cdlib.org/findaid/ark:/13030/c8s1890r/). Điều khoản
  đọc ngày 2026-10-28 qua kết quả tìm kiếm và trang dự án; trang mục Calisphere chặn truy cập tự
  động nên chưa đọc trực tiếp được.
