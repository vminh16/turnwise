# Hướng dẫn gán nhãn và thu dữ liệu có đồng ý

Tài liệu cho người gán nhãn và người quản trị buổi thu của Giai đoạn 1. Nó định nghĩa
**nhãn nào, gán ở đâu, quyết định ca khó ra sao, đo độ đồng thuận thế nào**, và mẫu đồng ý
người tham gia phải ký trước khi thu.

`SPEC.md` đúng hơn tài liệu này. Chỗ nào tài liệu này và `SPEC.md` mâu thuẫn, sửa tài liệu này.

**Phạm vi (từ 2026-10-28, ADR-0007):** hướng dẫn này chỉ áp dụng cho **bộ kiểm thử sản phẩm**,
tức các cuộc gọi đóng vai NetCo có track bot. **Bộ phân tích** là hội thoại tự nhiên giữa hai
người, không có bot, và cần hướng dẫn riêng (`docs/research/analysis-corpus.md` §7). Hướng dẫn đó
chưa viết; đừng dùng tài liệu này để gán nhãn bộ phân tích.

Phiên bản hướng dẫn: **1.2** (2026-09-15). Mỗi file nhãn ghi phiên bản hướng dẫn đã dùng để
gán; đổi quy tắc là tăng phiên bản (§6.4).

---

## 1. Dữ liệu này dùng để làm gì

Bộ dữ liệu vàng dùng để **đo**, không dùng để huấn luyện (`docs/progress.md` §6.1). Mọi quy
tắc dưới đây phục vụ một câu hỏi: *ở cuối mỗi đoạn khách nói, bot lẽ ra phải làm gì, và bot
đã làm gì?*

Vì vậy nhãn mô tả **hành vi đúng của bot**, không mô tả ngôn ngữ học thuần tuý. Nhãn trung
tâm (`caller_act`, §4) dùng đúng ba giá trị mà `TurnDecision` trả về — `hold`, `take`,
`backchannel` — cộng hai ca mà tầng quyết định lượt phải xử lý khác: nói đè có nội dung và lời
không nói với bot.

---

## 2. Một buổi thu sinh ra gì

| Thành phần | Nguồn | Ghi chú |
|---|---|---|
| Track **micro** | micro người tham gia | tiếng khách; ở buổi thu bằng loa có lẫn tiếng bot vọng lại |
| Track **bot** | chính tín hiệu đã phát | biết chính xác từng mẫu, không phải đoán |
| Log phát | web thu (`collector/`) | mỗi câu bot: bước, mốc người thu bấm nút, mốc bắt đầu phát, mốc hết câu; tính bằng chỉ số mẫu trong file |
| Metadata buổi | người thu điền trên web, trình duyệt tự ghi phần kỹ thuật | §3 |
| File nhãn | người gán | §4, §5 |

Hai track ghi trên cùng đồng hồ của trình duyệt. Kênh micro vẫn trễ hơn kênh bot một khoảng
bằng độ trễ thiết bị; trình duyệt báo ước lượng trong file `.json` đi kèm (`base_latency_s`,
`output_latency_s`). Buổi thử đo lại khoảng này để quyết định có cần bù trước khi gán nhãn.

---

## 3. Metadata

### 3.1 Người nói

Chỉ thu thứ phép đo cần. Luật 91/2025/QH15 Điều 3 khoản 2: *"Chỉ được thu thập, xử lý dữ liệu
cá nhân đúng phạm vi, mục đích cụ thể, rõ ràng"*.

| Trường | Giá trị | Vì sao cần |
|---|---|---|
| `speaker_id` | mã giả danh, ví dụ `S014` | chia tập theo người nói (`.claude/rules/training.md`) |
| `dialect` | `north`, `north_central`, `central`, `south` | §5.3: thanh điệu đọc từ chữ viết sai với giọng Nam và nhiều giọng Trung |
| `adult` | `true` | chỉ nhận người từ 18 tuổi |

**Không** thu họ tên thật, số điện thoại, giới tính, tuổi cụ thể. Bảng nối `speaker_id` với
người thật (để thực hiện quyền rút lại đồng ý) nằm **ngoài repo**, trên giấy hoặc một file do
một người giữ.

Không thu giới tính vì phép đo không cần: F0 được chuẩn hoá **theo từng người nói** trước khi
gộp (`AGENTS.md` Gotchas), không theo giới.

### 3.2 Buổi thu

`session_id`, ngày, `speaker_id`, danh sách kịch bản theo thứ tự đã chạy, `playback`
(`headset` hoặc `loudspeaker`), `noise` (`none`, `tv`, `street`, `children`, `other`), thiết bị
micro và độ trễ trình duyệt báo, phiên bản hướng dẫn.

Buổi `loudspeaker` là nguồn dữ liệu duy nhất cho R5 (bot không nhận nhầm tiếng mình). Buổi có
`noise` khác `none` là nguồn duy nhất cho hành vi §4.3 "tiếng ồn nền". Không có hai loại buổi
này thì hai yêu cầu đó không đo được.

---

## 4. Các lớp nhãn

Công cụ gán nhãn: **Praat**, file TextGrid, chốt ở pha 1.6. Bản nháp sinh bằng
`evaluation/annotation.py`, cách bấm ở `docs/runbook/annotate.md`. Nhãn `caller_act` ghi thẳng trên
khoảng của đoạn nói: người gán sửa ranh giới và nhãn trên cùng một lớp.

### 4.1 Lớp tự động — máy sinh, người chỉ sửa khi sai

| Lớp | Nội dung | Cách sinh |
|---|---|---|
| `bot` | khoảng bot nói, nhãn là mã câu | từ log phát; không gán tay |
| `caller_vad` | khoảng có tiếng / im trên track micro | dò tiếng nói tự động; người gán sửa ranh giới |
| `state` | `self`, `other`, `none`, `both` ở mỗi khung | tính từ `bot` ∩ `caller_vad`; không gán tay |

`state` và cách suy ra khoảng lặng lấy nguyên từ Heldner & Edlund (2010, §2.1 và §3.2), không
tự đặt ra:

- **pause** — khoảng lặng giữa hai đoạn nói của **cùng** một người;
- **gap** — khoảng lặng giữa đoạn nói của **hai** người khác nhau;
- **overlap_between** — nói chồng tại chỗ đổi người;
- **overlap_within** — nói chồng mà không đổi người, ví dụ khách chêm tiếng đệm khi bot đang nói.

Bài báo đó gộp các khoảng lặng ngắn hơn 180 ms vào đoạn nói (để không nhầm chỗ tắc của phụ âm
với khoảng ngừng) và bỏ các đoạn nói ngắn hơn 90 ms (để không nhầm tiếng gõ với lời nói). Hai
con số này là **mặc định tham khảo**; giá trị dùng thật đặt trong `configs/`, không đặt ở đây và
không đặt trong code.

Một **đoạn nói của khách** (IPU, inter-pausal unit) là một khoảng liền trên `caller_vad` sau
khi đã gộp và bỏ như trên. Lớp `caller_act` gán đúng một nhãn cho mỗi IPU.

### 4.2 Lớp người gán

| Lớp | Đơn vị | Nội dung |
|---|---|---|
| `caller_words` | mỗi IPU | lời khách, theo quy ước §5.1 |
| `caller_act` | mỗi IPU | một nhãn trong §4.3 |
| `nonspeech` | khoảng | tiếng không phải lời: `cough`, `laugh`, `breath`, `tv`, `street`, `children`, `bot_echo`, `other` |
| `tone_override` | mỗi IPU, tuỳ chọn | chỉ điền khi thanh đọc từ chữ viết sai (§5.3) |

Thanh của âm tiết cuối **không gán tay**: nó đọc từ `caller_words` bằng
`evaluation.roleplay.final_syllable_tone`, trừ khi có `tone_override`.

### 4.3 `caller_act` — nhãn trung tâm

Hỏi đúng một câu cho mỗi IPU: **ngay khi IPU này kết thúc, bot lẽ ra phải làm gì?**

| Nhãn | Bot lẽ ra phải | Định nghĩa |
|---|---|---|
| `hold` | im, chờ tiếp | khách **chưa xong** lượt: sau khoảng lặng, khách nói tiếp cùng một ý |
| `take` | nhận lượt, đáp lại | khách **đã xong** lượt và chờ bot |
| `backchannel` | nói tiếp nếu đang nói; nếu đang im thì im tiếp | khách chỉ báo là đang nghe, **không** giành lượt |
| `barge_in` | dừng ngay, nhường lượt | khách nói đè lên bot **có nội dung** giành lượt |
| `aside` | bỏ qua | lời không nói với bot: nói với người trong phòng, tự lẩm bẩm không thuộc lượt |

Thuộc tính đi kèm, chỉ điền khi đúng:

- `agent` — trên `take` hoặc `barge_in`: khách đòi gặp nhân viên (N5).
- `explicit` — trên `hold`: khách **nói rõ** là cần chờ ("chờ chút", "để tôi tìm"). Khoảng lặng
  sau các IPU này thường dài hơn hẳn, nên phân tích phải tách chúng khỏi ngập ngừng im lặng.
- `filled` — trên `hold`: IPU kết thúc bằng tiếng ngập ngừng ("ờ", "ừm", "à").
- `cut_in` — trên `hold`: bot đã nói trong lúc khách còn chưa xong. Đây là một lần **cắt lời
  thật**, dữ liệu quý nhất cho tỉ lệ cắt lời; không được sửa thành `take`. Web thu hiện chỉ phát
  câu bot khi người thu bấm, nên ca này chỉ xuất hiện khi người thu bấm sớm.

---

## 5. Quy tắc cho ca khó

### 5.1 Quy ước chép lời

- Chữ thường, **đủ dấu thanh**, không dấu câu. Thiếu dấu thì không đọc được thanh.
- **Số viết bằng chữ, đúng như khách đọc**: "tám hai bốn" chứ không "824"; "hai bốn chín
  nghìn" nếu khách đọc tắt như vậy. Chữ số làm thanh của âm tiết cuối thành `unknown`.
- Tiếng đệm và ngập ngừng viết theo một bộ cố định: `dạ`, `vâng`, `ừ`, `ừa`, `ờ`, `ừm`, `à`,
  `ạ`, `hả`, `ơ`. Âm nghe khác bộ này thì chọn cái gần nhất và ghi chú.
- Từ phương ngữ có cách viết thông dụng thì chép đúng từ đó ("hông", "hổng"), không đổi sang từ
  phổ thông. Cùng một từ chỉ khác cách phát âm thì viết theo chính tả ("dzậy" viết "vậy").
- Từ nước ngoài viết như thường gặp: `modem`, `wifi`, `ok`.
- Từ bị cắt dở: phần nghe được và dấu gạch, `tá-`. Không nghe rõ: `[x]`.

### 5.2 Phân biệt bằng những gì xảy ra sau đó

Nhãn gán **sau khi nghe hết đoạn phía sau**. Khách có xong lượt hay không là ý định của khách,
và bằng chứng tốt nhất của ý định là việc khách làm tiếp theo.

| Tình huống | Nhãn |
|---|---|
| Khách im 3 giây giữa dãy số rồi đọc tiếp, bot không nói gì | IPU trước: `hold` |
| Khách im giữa dãy số, bot nói chen vào, khách **đọc tiếp dãy số** | IPU trước: `hold` + `cut_in` |
| Khách im giữa dãy số, bot nói chen vào, khách **bỏ dở** và đáp bot | IPU trước: `hold` + `cut_in` (khách bị buộc bỏ dở, không phải đã xong) |
| "Dạ." sau câu hỏi của bot, khách im và chờ | `take` |
| "dạ" trong lúc bot đang đọc, bot đọc tiếp, khách không phản đối | `backchannel` |
| "dạ" ở chỗ bot ngắt hơi giữa đoạn đọc, bot đọc tiếp | `backchannel` |
| "dạ, nhưng mà..." đè lên bot rồi nói tiếp nội dung | `barge_in` |
| "hả?" hoặc "gì cơ?" đè lên bot | `barge_in` — khách đòi bot nhắc lại, tức giành lượt |
| "ừ ừ ừ" liền nhau trong lúc bot nói | một IPU `backchannel` |
| Khách nói đè có nội dung, bot không dừng (web thu không dừng bot), khách im hoặc nói tiếp | vẫn `barge_in` |
| "alo? alo?" khi bot im quá lâu | `take` — khách đang giục bot; đồng thời là dấu hiệu bot chậm |
| "để xem nào, ờ..." rồi đọc tiếp | `hold` + `filled` |
| Khách quay sang nói với người khác trong phòng | `aside` |
| Khách cười hoặc ho, không có lời | không phải IPU của `caller_act`; gán vào `nonspeech` |

**Nói đè khi bot không dừng.** Web thu phát câu bot tới hết, kể cả khi bị nói đè; nhãn
`barge_in` ghi điều bot *lẽ ra* phải làm. Nhãn và mốc tính ở **đầu IPU nói đè** — đó là chỗ
phép đo "thời gian từ lúc khách nói đè tới lúc bot im" bắt đầu đếm. Phần còn lại của lượt đó,
khi hai bên cứ nói chồng lên nhau, không đại diện cho sản phẩm (bot thật đã dừng, khách sẽ nói
khác): vẫn gán nhãn cho đủ, nhưng các chỉ số §9.1 **không chấm** quyết định nào nằm sau mốc nói
đè cho tới khi câu bot kết thúc.

Ca "Dạ." và "dạ" là ca khó nhất của R4 (`SPEC.md` §2) và là lý do nhãn **không bao giờ** gán
theo từ. Cùng một chuỗi âm, hai nhãn khác nhau; chỉ ngữ cảnh phân biệt được.

### 5.3 Thanh điệu và phương ngữ

`final_syllable_tone` đọc thanh từ **chữ viết**, tức thanh theo chuẩn chính tả. Với giọng Nam
và nhiều giọng Trung, thanh hỏi và thanh ngã **đã nhập làm một**, còn năm thanh (*Journal of the
International Phonetic Association*, "Stress and phrasal prominence in tone languages: The case of
Southern Vietnamese").
Thanh nặng ở giọng Nam cũng khác giọng Bắc về đường nét.

Hệ quả cho người gán: **không** sửa `tone_override` chỉ vì người Nam đọc "ngã" giống "hỏi".
Chữ viết vẫn là nhãn đúng cho câu hỏi "âm tiết này thuộc thanh nào". Việc tách kết quả theo
`dialect` là của `evaluation/`, và đó là lý do `dialect` là trường bắt buộc (§3.1).

Chỉ điền `tone_override: unknown` khi âm tiết cuối không phải tiếng Việt (`modem`, `ok`) hoặc
không nghe rõ.

### 5.4 Ranh giới thời gian

- Đầu IPU: âm thanh lời nói đầu tiên nghe được. Cuối IPU: âm thanh lời nói cuối cùng.
- Không tính hơi thở, tiếng chép miệng, tiếng lật giấy vào IPU.
- Không cắt ranh giới giữa một âm tiết.
- Nhìn phổ, không chỉ nghe: phụ âm tắc cuối ("mất", "đẹp") có đoạn im ngắn trước tiếng nổ;
  ranh giới cuối nằm sau tiếng nổ nếu có.

---

## 6. Quy trình và độ đồng thuận

### 6.1 Ba lượt

1. **Máy**: sinh `bot`, `caller_vad`, `state`.
2. **Người gán A**: sửa `caller_vad`, chép `caller_words`, gán `caller_act`, `nonspeech`.
3. **Người gán B** trên một phần các buổi, **độc lập**, không xem nhãn của A.

Người gán **không** được biết buổi thu thuộc tập nào (`dev` hay `holdout`), và **không** được
xem kết quả của bất kỳ decider nào trên buổi đó trước khi gán xong. Biết một hệ đoán gì là đủ để
nghiêng nhãn về phía đó.

### 6.2 Phần gán kép

Đề xuất: **20% số buổi**, chọn ngẫu nhiên có hạt giống cố định, rải đều theo `dialect`. Tỉ lệ
này là giả định, người phụ trách dự án chốt ở pha 1.6.

### 6.3 Đo gì

| Đại lượng | Trên | Cách đo |
|---|---|---|
| Cohen's κ | `caller_act` | trên các IPU mà hai người gán có ranh giới khớp nhau |
| Tỉ lệ ranh giới khớp | điểm cuối các IPU `take` | hai ranh giới khớp nếu lệch nhau không quá một dung sai đặt trong `configs/` |
| Ma trận nhầm lẫn | `caller_act` | để biết **cặp nhãn nào** hay bị lẫn, không chỉ một con số |

Đọc κ theo thang của Landis & Koch (1977, *Biometrics* 33(1):159–174): 0,61–0,80 là "substantial".
Đề xuất ngưỡng chấp nhận **κ ≥ 0,7** cho `caller_act`; cũng là giả định để chốt ở pha 1.6.

Dưới ngưỡng thì **không** gán tiếp. Xem ma trận nhầm lẫn, viết thêm quy tắc vào §5, tăng phiên
bản hướng dẫn, gán lại phần kép.

Riêng cặp `backchannel`/`take` trên "dạ": báo κ **tách riêng** cho các IPU chỉ gồm một tiếng đệm.
Một κ tổng cao có thể che một cặp nhãn gần như gán ngẫu nhiên, và đây đúng là cặp quan trọng nhất.

### 6.4 Giải quyết bất đồng

Bất đồng trên phần gán kép do một người thứ ba quyết, hoặc hai người gán thảo luận tới khi thống
nhất. Mỗi quyết định sinh ra một quy tắc mới thì ghi vào §5 và tăng phiên bản. File nhãn đã gán
theo phiên bản cũ được rà lại theo quy tắc mới.

Sau khi holdout đã khoá (pha 1.5), nhãn holdout **không** sửa nữa, kể cả khi phát hiện lỗi. Lỗi
ghi vào một danh sách errata đi kèm báo cáo cuối. Sửa nhãn holdout sau khi đã thấy kết quả là
một cách chọn tham số trên holdout.

---

## 7. Ghi chú cho người quản trị buổi thu

Người thu tự làm trên web (`docs/runbook/collect-data.md`). Người quản trị:

- Thu thử một buổi với chính mình trước mỗi đợt, nghe lại cả hai kênh.
- Gửi mỗi người một link riêng. Không gửi kèm kịch bản; web chỉ cho người thu thấy tình huống,
  thẻ giả và chỉ dẫn, không cho thấy trước lời bot.
- Không nhắc người thu "nhớ chêm dạ". Chỉ dẫn trong kịch bản là đủ; ép thêm thì tiếng đệm mất
  nhịp tự nhiên.
- Khi nghe lại, nếu người thu lỡ nói thông tin thật của mình, ghi mốc thời gian để xoá đoạn đó
  trước khi gán nhãn.

---

## Phụ lục A — Mẫu đồng ý tham gia thu âm

> **Đây không phải tư vấn pháp lý.** Mẫu này bám các điều khoản về sự đồng ý của Luật Bảo vệ
> dữ liệu cá nhân số 91/2025/QH15 (hiệu lực từ 01/01/2026): Điều 9 (sự đồng ý), Điều 10 (rút lại
> đồng ý), Điều 11 khoản 1 (đồng ý trước khi thu thập), Điều 14 (xoá dữ liệu). Luật không liệt kê
> giọng nói trong định nghĩa dữ liệu nhạy cảm mà để Chính phủ ban hành danh mục (Điều 2 khoản 3);
> danh mục đó **chưa được kiểm chứng** trong tài liệu này. Mẫu xử lý giọng nói **như dữ liệu nhạy
> cảm** để an toàn. Nếu dự án thuộc một trường đại học có hội đồng đạo đức nghiên cứu, hỏi hội
> đồng trước khi dùng.

Luật đòi sự đồng ý phải *"tự nguyện và biết rõ"* loại dữ liệu, mục đích, bên kiểm soát dữ liệu,
quyền và nghĩa vụ của người tham gia (Điều 9 khoản 2); *"thể hiện sự đồng ý đối với từng mục
đích"* (Điều 9 khoản 4 điểm a); và *"sự im lặng hoặc không phản hồi không được coi là sự đồng ý"*
(Điều 9 khoản 4 điểm d). Mẫu dưới đây vì vậy có **ô đánh dấu riêng cho từng mục đích**.

---

**PHIẾU ĐỒNG Ý THAM GIA THU ÂM — DỰ ÁN TURNWISE**

**Dự án là gì.** Turnwise nghiên cứu cách một tổng đài tự động biết khi nào người gọi đã nói
xong, và dừng lại khi người gọi nói chen vào. Công ty NetCo trong buổi thu là công ty giả định.

**Bạn sẽ làm gì.** Bạn đóng vai một khách hàng gọi tổng đài, trong khoảng [__] phút, theo một số
tình huống có sẵn. Mọi số thuê bao, mã và địa chỉ bạn cần đọc đều in trên thẻ giả. **Không đọc
số điện thoại, địa chỉ hay tên thật của bạn.**

**Về "tổng đài".** Giọng tổng đài là các câu một người đã đọc và thu sẵn. Trang web phát từng
câu khi bạn bấm nút. Bạn không nói chuyện với một hệ thống tự động thật, và tổng đài không dừng
lại khi bạn nói chen vào.

**Dữ liệu được thu.** Bản ghi âm giọng nói của bạn; bản chép lời; một mã người nói không chứa
tên bạn; vùng giọng nói của bạn (Bắc, Bắc Trung Bộ, Trung, Nam). Không thu họ tên, tuổi, giới
tính, số điện thoại trong bộ dữ liệu.

**Bên kiểm soát dữ liệu.** [Tên người hoặc nhóm chịu trách nhiệm], liên hệ: [cách liên hệ].

**Lưu trữ.** Bản ghi lưu trên [thiết bị/nơi lưu], chỉ [những ai] truy cập được, **không** đưa lên
kho mã nguồn và **không** công bố công khai. Lưu đến [thời hạn], sau đó xoá.

**Quyền của bạn.**
- Tham gia là tự nguyện. Bạn dừng buổi thu bất cứ lúc nào mà không cần nêu lý do.
- Bạn có quyền rút lại đồng ý và yêu cầu xoá bản ghi của mình bằng cách liên hệ bên kiểm soát dữ
  liệu. Việc rút lại **không** ảnh hưởng tới những xử lý đã thực hiện trước thời điểm rút lại
  (Luật 91/2025/QH15 Điều 10 khoản 4) — ví dụ một con số đã nằm trong báo cáo đã nộp.
- Bạn có quyền được biết dữ liệu của mình đang được xử lý thế nào.

**Đồng ý theo từng mục đích.** Đánh dấu vào ô bạn đồng ý. Ô không đánh dấu nghĩa là **không**
đồng ý.

- [ ] **Mục đích 1 (bắt buộc để tham gia):** Ghi âm buổi đóng vai, chép lời, gán nhãn, và dùng để
  **đo và đánh giá** hệ thống của dự án. Kết quả chỉ công bố dưới dạng số liệu tổng hợp.
- [ ] **Mục đích 2 (không bắt buộc):** Dùng **trích đoạn âm thanh** giọng nói của tôi trong báo
  cáo, bài trình bày hoặc buổi demo của dự án.

Dữ liệu này **không** được dùng để huấn luyện mô hình. Nếu sau này dự án muốn dùng cho mục đích
khác với hai mục đích trên, dự án phải xin đồng ý lại.

Tôi xác nhận đã đủ 18 tuổi, đã đọc và hiểu phiếu này.

Mã người nói (nhóm dự án điền): ________ Ngày: ________ Chữ ký: ________

---

## Phụ lục B — Đồng ý của người thu giọng bot

Giọng bot cũng là giọng một người thật, phát lại trong mọi buổi thu và nằm trong mọi bản ghi.
Cùng căn cứ và cùng lưu ý pháp lý như phụ lục A.

---

**PHIẾU ĐỒNG Ý THU GIỌNG TỔNG ĐÀI — DỰ ÁN TURNWISE**

**Bạn sẽ làm gì.** Đọc toàn bộ lời tổng đài trong các kịch bản của dự án, một lần, theo đúng
chữ viết. Bản thu được phát lại cho người tham gia trong các buổi đóng vai.

**Dữ liệu được thu.** Bản ghi giọng đọc của bạn. Không gắn với tên bạn trong bộ dữ liệu.

**Bên kiểm soát dữ liệu, lưu trữ, quyền của bạn.** Như phụ lục A. Nếu bạn rút lại đồng ý, các
buổi thu **đã** diễn ra không bị ảnh hưởng (Luật 91/2025/QH15 Điều 10 khoản 4); các buổi sau
dùng giọng khác.

- [ ] **Mục đích 1 (bắt buộc):** Phát lại giọng tôi trong các buổi đóng vai, và giọng tôi có mặt
  trong bản ghi của các buổi đó, dùng để **đo và đánh giá** hệ thống.
- [ ] **Mục đích 2 (không bắt buộc):** Dùng trích đoạn giọng tôi trong báo cáo, bài trình bày
  hoặc demo.

Giọng tôi **không** được dùng để huấn luyện mô hình tổng hợp giọng nói.

Tôi xác nhận đã đủ 18 tuổi, đã đọc và hiểu phiếu này.

Ngày: ________ Chữ ký: ________

---

## Nguồn

- Heldner, M. & Edlund, J. (2010). Pauses, gaps and overlaps in conversations. *Journal of
  Phonetics* 38(4), 555–568. §2.1 định nghĩa pause, gap, overlap; §3.2 ngưỡng 180 ms và 90 ms, bốn
  trạng thái `self/other/none/both`. Đọc từ bản PDF ngày 2026-09-14.
- Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15, ký 26/06/2025, hiệu lực 01/01/2026. Bản có chữ ký
  số tại cổng văn bản Chính phủ, `datafiles.chinhphu.vn/cpp/files/vbpq/2025/7/91qh.signed.pdf`.
  Đọc Điều 2, 3, 9, 10, 11, 14 ngày 2026-09-14.
- Landis, J. R. & Koch, G. G. (1977). The measurement of observer agreement for categorical data.
  *Biometrics* 33(1), 159–174. PubMed 843571.
- Stress and phrasal prominence in tone languages: The case of Southern Vietnamese. *Journal of
  the International Phonetic Association*, Cambridge Core. Nguồn cho việc thanh hỏi và ngã nhập
  làm một ở giọng Nam; tra ngày 2026-09-14 qua kết quả tìm kiếm trích từ bài, **chưa đọc toàn văn
  và chưa kiểm tác giả**.
