# SPEC.md — Nhịp Nói Chuyện

**Trợ lý giọng nói có xử lý ngắt lời (barge-in) và turn-taking cho tổng đài chăm sóc khách hàng tiếng Việt**
*A Vietnamese Voice Assistant with Barge-in and Turn-Taking for Customer Service Call Centers*


> Đây là tài liệu định hướng. Nó nói **bài toán là gì**, **vì sao đáng giải**, **nghiệp vụ phải đúng thế nào**, và **thế nào là xong**.
> Nó cố tình **không** chốt phương pháp. Phương pháp được chọn sau Giai đoạn 0 dựa trên bằng chứng, và ghi vào `docs/adr/`.
> Quy ước code, lệnh chạy và cạm bẫy kỹ thuật nằm ở `CLAUDE.md`.

---

## 1. Bài toán

Tổng đài tự động quyết định "khách nói xong chưa" bằng **một ngưỡng im lặng cố định** — thường 500–800ms. Cách này hỏng vì một lý do cơ bản: *đang nghĩ* và *đã nói xong* nghe giống hệt nhau trên trục biên độ. Cả hai đều là im lặng. Chúng chỉ khác nhau ở nội dung câu đã nói và ở ngữ điệu dẫn tới khoảng lặng — thông tin không nằm trong đại lượng mà hệ thống đang đo.

Hệ quả là ba lỗi **đối kháng nhau**, sửa cái này thì hỏng cái kia:

| Lỗi | Xảy ra khi | Trải nghiệm của khách |
|---|---|---|
| **Cắt lời** | Hạ ngưỡng để phản hồi nhanh | Khách đọc dở số thuê bao, dừng nhìn hoá đơn, bot đã chen vào |
| **Chờ quá lâu** | Nâng ngưỡng để tránh cắt lời | Trả lời "Đúng rồi." xong vẫn phải chờ máy im 700ms |
| **Không cho ngắt** | Bot không nghe khi đang nói | Biết bot hiểu sai từ giây thứ hai, vẫn phải nghe hết mười giây |

Không tồn tại giá trị ngưỡng nào tránh được cả ba. **Đó là phát biểu bài toán.**

## 2. Bằng chứng

**Khoảng cách với con người.** Người trả lời nhau trong khoảng **250ms** — nhanh hơn thời gian cần để soạn một câu, nghĩa là người nghe đã dự đoán điểm kết thúc từ trước. Hệ thống nối tầng hiện tại mất **1.195ms**; nghiên cứu endpoint anticipation 2026 rút xuống **690ms** bằng cách dự đoán trước tới 2,56 giây. Khoảng cách còn lại vẫn gần nửa giây.

**Ngành đã kết luận cách cũ hỏng.** Các nguồn kỹ thuật 2026 nói thẳng *"rule-based VAD is broken"*. Mô hình dò lượt mã nguồn mở phổ biến nhất đã ra tới bản v3.2, và bản đó tồn tại để xử lý đúng hai thứ: môi trường ồn và **câu trả lời ngắn**.

**Khoảng trống tiếng Việt, do một khảo sát tự nêu.** Khảo sát turn-taking IWSDS 2025 ghi nhận: nghiên cứu đa ngôn ngữ **chỉ tập trung ở tiếng Anh và tiếng Nhật**; *"backchannels use varies from one culture to another"*; và **ngôn ngữ thanh điệu không được nhắc tới ở bất kỳ đâu**. Không có bộ dữ liệu tiếng Việt nào trong danh sách của khảo sát.

Cùng khảo sát đó ghi: **chỉ 28% bài được rà soát có so sánh với công trình trước.** Vì vậy dự án này coi việc dựng baseline nghiêm túc là một phần kết quả, không phải việc vặt.

**Hai đặc điểm tiếng Việt chưa ai xử lý:**

- **F0 đã bị thanh điệu chiếm chỗ.** Tiếng Anh báo hiệu hết lượt bằng đường cao độ đi xuống cuối câu. Tiếng Việt không có quyền đó — đổi đường F0 là đổi luôn từ. Câu kết thúc bằng *"rồi"* (F0 xuống) và *"đấy"* (F0 lên) có hướng ngược nhau dù cả hai đều là kết thúc lượt.
- **"Dạ" vừa là tiếng đệm vừa là câu trả lời.** Khách chêm "dạ, vâng, ừ" liên tục trong lúc bot đọc thông tin — đó không phải giành lượt. Nhưng "Dạ." đứng một mình sau câu hỏi *là* một lượt hoàn chỉnh. Cùng chuỗi âm, hai chức năng ngược nhau.

**Vì sao chọn bối cảnh tổng đài.** Ngắt lời ở tổng đài không phải chuyện hiếm mà là hành vi mặc định: khách đã biết mình muốn gì, đang mất kiên nhẫn, và hay ngập ngừng vì phải tra thông tin. Ngoài ra tổng đài có chỉ số đo được bằng tiền — thời gian xử lý trung bình mỗi cuộc gọi, tỉ lệ bot tự xử lý xong, tỉ lệ khách bỏ cuộc — mà độ trễ chuyển lượt cộng thẳng vào cả ba.

*Phép tính minh hoạ, giả định nêu rõ:* nếu một cuộc gọi có 12 lượt nói và mỗi lượt tiết kiệm 800ms, đó là 9,6 giây mỗi cuộc; với 10.000 cuộc/ngày là khoảng 26,7 giờ thời lượng cuộc gọi mỗi ngày. Ba con số đầu vào đều là giả định để minh hoạ bậc độ lớn, **không phải số đo của một tổng đài thật**.

## 3. Người dùng

Bối cảnh sản phẩm: tổng đài CSKH của **NetCo**, nhà cung cấp Internet gia đình. *Công ty giả định, dùng làm ngữ cảnh nghiệp vụ.*

| Vai | Bối cảnh | Lỗi đau nhất | Cần gì |
|---|---|---|---|
| **Khách hàng** | Mạng hỏng, đang bực, vừa nói vừa lật hoá đơn | Bị cắt lời khi đọc dở dãy số | Được ngừng giữa câu mà không mất lượt; ngắt lời được bất cứ lúc nào |
| **Điện thoại viên** | Nhận cuộc gọi bot chuyển sang | Khách đã bực sẵn vì vật lộn với bot | Bot chuyển sớm, kèm thông tin đã thu, không bắt khách kể lại |
| **Quản lý vận hành** | Chịu trách nhiệm thời gian xử lý và tỉ lệ tự động hoá. **Người "mua" giải pháp.** | Chỉnh ngưỡng mãi không xong | Module thay được chỗ cũ, có chỉ số theo dõi |

**Bằng chứng hành vi cần ghi nhớ:** người gọi tổng đài hiện nay đã tự thích nghi — nói thành khối cụt lủn, tránh ngập ngừng, nói xong im bặt và chờ. Đó là hành vi bù trừ cho một sản phẩm hỏng, và nó mạnh hơn mọi khảo sát.

## 4. Nghiệp vụ

### 4.1 Năm luồng nghiệp vụ

Miền đóng, cố tình nhỏ. **Nghiệp vụ thứ sáu là scope creep.**

| # | Nghiệp vụ | Thông tin cần thu | Vì sao có trong danh sách |
|---|---|---|---|
| N1 | Báo sự cố mất mạng | Số thuê bao, mô tả lỗi, khung giờ hẹn kỹ thuật viên | Phổ biến nhất; khách bực nhất nên ngắt lời nhiều nhất |
| N2 | Tra cứu cước | Số thuê bao, kỳ cước | Bot phải đọc lại dãy số dài → tình huống ngắt lời kinh điển |
| N3 | Đổi lịch hẹn kỹ thuật viên | Mã lịch hẹn, ngày, khung giờ | Nhiều trường, nhiều xác nhận, nhiều chỗ khách chen vào sửa |
| N4 | Đăng ký hoặc huỷ gói | Số thuê bao, tên gói, xác nhận | Bắt buộc đọc điều khoản → khách hay ngắt giữa chừng |
| N5 | Gặp điện thoại viên | — | Phép thử ngắt lời quan trọng nhất; phải chạy được ở **bất kỳ** điểm nào |

### 4.2 Quy tắc nghiệp vụ

Những quy tắc này quyết định hành vi đúng, độc lập với cách cài đặt:

- **N5 ưu tiên tuyệt đối.** Yêu cầu gặp người thật cắt ngang mọi luồng đang chạy, ở mọi trạng thái, kể cả giữa lúc bot đang đọc.
- **Chuyển máy phải kèm ngữ cảnh.** Điện thoại viên nhận được những trường bot đã thu và luồng đang dở. Khách không phải kể lại.
- **Xác nhận trước khi thay đổi.** Mọi thao tác làm thay đổi dữ liệu (N3, N4) phải được khách xác nhận rõ ràng trước khi ghi nhận. Im lặng không phải đồng ý.
- **Ba lần hiểu sai thì chuyển người.** Cùng một trường mà hỏi lại quá ba lần thì chuyển sang N5, không hỏi tiếp.
- **Đọc lại thông tin nhạy cảm phải ngắt được.** Khi bot đọc số tiền, địa chỉ hoặc điều khoản, khách phải ngắt được giữa chừng và bot phải biết đã đọc tới đâu.
- **Không tự suy đoán trường còn thiếu.** Thiếu thông tin thì hỏi, không đoán.
- **Số thuê bao được xác thực theo định dạng trước khi tra cứu**, và đọc lại cho khách nghe để xác nhận.

### 4.3 Hành vi hội thoại phải đúng

Đây là phần đặc thù của đề tài, và là nơi hệ thống dễ sai nhất:

- Khách **ngừng giữa câu** để nghĩ hoặc tra thông tin → bot **giữ im**, không chen vào.
- Khách **chêm tiếng đệm** ("dạ", "vâng", "ừ", "à") trong lúc bot nói → bot **nói tiếp**, không dừng.
- Khách **nói đè có nội dung** → bot **dừng ngay** và nhường lượt.
- Khách **trả lời ngắn** ("Hai người.", "Đúng rồi.") → bot đáp lại **không chậm hơn câu dài**.
- **Tiếng ồn nền** (TV, trẻ con, xe cộ) → bot **bỏ qua hoàn toàn**, không coi là ngắt lời.
- Bot **không bao giờ được coi tiếng của chính mình là ngắt lời**.

## 5. Yêu cầu

Phát biểu theo điều **phải đúng**, không theo cách cài đặt.

### Bắt buộc

- **R1** — Hệ thống ước lượng liên tục khả năng khách sắp kết thúc lượt, thay vì chờ hết một ngưỡng im lặng cố định.
- **R2** — Khách ngừng giữa câu không bị mất lượt.
- **R3** — Khách ngắt lời được ở bất kỳ thời điểm nào bot đang nói, và bot dừng đủ nhanh để nghe tự nhiên.
- **R4** — Hệ thống phân biệt được tiếng đệm với hành vi giành lượt.
- **R5** — Hệ thống không bao giờ nhận nhầm tiếng của chính nó là ngắt lời.
- **R6** — Hoàn tất được năm luồng nghiệp vụ ở §4.1, tuân thủ quy tắc ở §4.2.
- **R7** — Mọi quyết định chuyển lượt được ghi log đủ để tái dựng và phân tích sau.
- **R8** — **Ba** baseline được cài song song, chạy trên **cùng** ASR, TTS và kịch bản, bật tắt bằng cấu hình:
  - **B1 — ngưỡng im lặng.** Cách làm hiện hành ở §1. Quét nhiều giá trị, không chọn một (§9.3).
  - **B2 — endpointer âm thanh mã nguồn mở có sẵn.** Mô hình đã công bố hỗ trợ tiếng Việt, chạy CPU, dùng nguyên trọng số, không tinh chỉnh.
  - **B3 — endpointer ngữ nghĩa trên văn bản ASR.** Mô hình mã nguồn mở có bản tiếng Việt riêng, chạy CPU, dùng nguyên trọng số, không tinh chỉnh.

  B1 chứng minh luận điểm ở §1: không ngưỡng nào thắng được. B2 và B3 trả lời câu hỏi “tại sao không dùng mô hình có sẵn” — câu hỏi này đã hợp lệ từ 2025, khi các endpointer đa ngôn ngữ bắt đầu liệt kê tiếng Việt. Tên và phiên bản mô hình cụ thể ghi ở `docs/adr/`, không chốt trong tài liệu này.
- **R12** — **Bot nói chuyện giống người, không vô cảm.** Giọng tự nhiên, lời thoại có đồng cảm và không lặp lại máy móc, nhịp đáp tự nhiên. Không ai muốn nói chuyện với một cái máy đọc; một bot chuyển lượt đúng từng mili giây mà nghe vô cảm vẫn là sản phẩm hỏng. Đạt được bằng: chọn giọng TTS có sẵn theo độ tự nhiên, viết lời thoại, và chính tầng `turn`. **Không** bằng huấn luyện TTS mới, sinh câu trả lời tự do bằng LLM, hay nhận dạng cảm xúc (§11).

### Nên có

- **R9** — Chuyển điện thoại viên kèm tóm tắt thông tin đã thu.
- **R10** — Bảng theo dõi hiển thị chỉ số theo thời gian thực trong lúc hệ thống chạy.
- **R11** — Bot nhớ được vị trí bị ngắt khi đang đọc đoạn dài.

## 6. Ràng buộc

- **Thời gian thực.** Suy luận phải theo kịp luồng audio trên máy tính xách tay thông thường, không phải máy có GPU. Ngân sách cụ thể ghi trong `configs/`, kiểm tra bằng `uv run pytest -m latency`.
- **Ngắt lời phải nhanh hơn ngưỡng cảm nhận của con người**, nếu không tính năng mất ý nghĩa.
- **Không phụ thuộc dịch vụ đám mây trong đường chạy chính.** Phụ thuộc mạng làm hỏng phép đo độ trễ và làm demo mong manh.
- **Dữ liệu.** Chỉ dùng hội thoại đóng vai theo kịch bản, có đồng ý. Không dùng ghi âm cuộc gọi thật của khách hàng bất kỳ công ty nào. NetCo là công ty giả định.
- **Không ghi audio ra đĩa trong runtime.**
- **Tập kiểm thử khoá.** Không dùng để huấn luyện hay chọn siêu tham số. Mở đúng một lần khi báo cáo cuối.

## 7. Hướng tiếp cận — đang cân nhắc, chưa chốt

**Không hardcode phương pháp vào tài liệu này.** Dưới đây là các hướng đã khảo sát, kèm tiêu chí để chọn. Quyết định ghi vào `docs/adr/` sau Giai đoạn 0.

| Hướng | Ý tưởng | Đánh đổi |
|---|---|---|
| Ngưỡng im lặng có tinh chỉnh | Giữ cách cũ, chỉnh ngưỡng theo ngữ cảnh | Rẻ nhất; nhưng §1 đã lập luận là không thắng được |
| Dự đoán liên tục từ âm thanh | Ước lượng hoạt động giọng nói tương lai; nhãn tự sinh từ chính dữ liệu nên không cần gán tay | Hứa hẹn nhất; cần dữ liệu hội thoại hai kênh |
| Dựa vào tính trọn vẹn của câu | Dùng văn bản từ ASR để xét câu đã đủ ý chưa | Bổ trợ tốt; phụ thuộc độ trễ và độ chính xác ASR |
| Kết hợp nhiều tín hiệu | Chấm điểm song song rồi hợp nhất, cho phép từng nguồn bỏ phiếu trắng | Giải thích được và ablation được; phức tạp hơn |

**Giả thuyết riêng cần kiểm chứng, không được coi là đã đúng:**
> Vì F0 tiếng Việt mang thanh điệu từ vựng, dấu hiệu ngữ điệu báo hiệu kết thúc lượt hoạt động khác so với ngôn ngữ không thanh điệu; và tách phần thanh điệu ra khỏi F0 sẽ cho tín hiệu tốt hơn F0 thô.

**Tiêu chí chọn hướng, xếp theo thứ tự ưu tiên:** (1) đáp ứng được ràng buộc thời gian thực ở §6; (2) giải thích được khi báo sai; (3) bật tắt từng thành phần được để làm ablation; (4) không cần gán nhãn thủ công quy mô lớn.

## 8. Ranh giới giữa các thành phần

Mô tả trách nhiệm, không mô tả cách cài đặt. Tên module khớp `AGENTS.md`.

- **`audio`** — nhận âm thanh vào, tách tiếng bot khỏi tiếng khách, cung cấp đặc trưng theo khung đều đặn. Không biết gì về hội thoại.
- **`turn`** — nhận đặc trưng, trả về đánh giá về trạng thái lượt nói: *giữ lượt*, *nhận lượt*, hay *đây chỉ là tiếng đệm*. **Mỗi nguồn tín hiệu phải trả về được "không kết luận" thay vì đoán bừa.** Không biết gì về nghiệp vụ.
- **`dialog`** — nhận quyết định lượt nói và văn bản, chạy máy trạng thái nghiệp vụ §4, sinh câu trả lời. Không biết gì về xử lý tín hiệu.
- **`telemetry`** — nhận sự kiện từ mọi tầng, ghi log có timestamp, dựng bảng theo dõi. Chỉ đọc, không tác động ngược.

Ranh giới này giữ để thay một tầng mà không đụng tầng khác — điều kiện cần để chạy A/B ở R8.

## 9. Nghiệm thu

### 9.1 Chỉ số kỹ thuật

Ngưỡng cụ thể đặt ở `configs/`. Baseline đo ở Giai đoạn 0, không được điền bằng số đoán.

- Tỉ lệ bot cắt lời khách khi họ chưa nói xong
- Độ trễ từ lúc khách dứt lời đến lúc bot lên tiếng (trung vị và đuôi chậm)
- Tỉ lệ tiếng đệm bị nhận nhầm thành giành lượt
- Thời gian từ lúc khách nói đè đến lúc bot im
- Tỉ lệ bot tự nhận nhầm tiếng của mình là ngắt lời
- Chênh lệch tỉ lệ lỗi giữa các thanh điệu của âm tiết cuối — *kết quả khoa học chính*

### 9.2 Chỉ số nghiệp vụ

- Thời gian trung bình hoàn tất một luồng nghiệp vụ
- Tỉ lệ phiên bot thu đủ thông tin mà không phải chuyển người
- Số lần trung bình khách phải lặp lại một thông tin
- Điểm tự nhiên của bot do người nghe chấm (R12), đặt cạnh cùng lời thoại do người thật đọc ở Giai đoạn 1 làm mốc trần

### 9.3 Quy tắc báo cáo

1. **Không bao giờ báo tỉ lệ cắt lời mà thiếu độ trễ, và ngược lại.** Hai chỉ số đối kháng; trình bày đúng là một đường cong đánh đổi.
2. **Baseline quét nhiều ngưỡng, không chọn một.** Một ngưỡng đơn lẻ mời gọi câu hỏi "sao không chỉnh tốt hơn?". Quét nhiều mức chứng minh *không ngưỡng nào tốt cả* — đó là luận điểm trung tâm.
3. **Ablation bắt buộc:** bật tắt từng thành phần và báo cáo đóng góp riêng của mỗi cái.
4. **Số liệu độ trễ đo trên hệ chạy trực tiếp**, không phải trên file đã thu.
5. **Tập kiểm thử mở đúng một lần.**

## 10. Kiểm chứng đầu-cuối

Dự án được coi là hoàn thành khi **một người chưa từng dùng hệ thống** gọi vào và làm được trọn năm phép thử sau, trên hai cấu hình đặt cạnh nhau — baseline và hệ mới — với mọi thành phần khác giữ nguyên:

1. **Ngập ngừng giữa câu.** Đọc số thuê bao, dừng giữa chừng để nhìn hoá đơn, rồi đọc tiếp. Hệ mới không chen vào.
2. **Tiếng đệm.** Chêm "dạ" trong lúc bot đọc thông tin cước. Hệ mới đọc tiếp liền mạch.
3. **Ngắt lời thật.** Nói đè "Không, không phải địa chỉ đó." Bot dừng ngay.
4. **Yêu cầu gặp người.** Nói "Cho tôi gặp nhân viên" giữa lúc bot đang nói. Bot dừng và chuyển máy kèm thông tin đã thu.
5. **Câu trả lời ngắn.** Trả lời "Hai người." Bot đáp không chậm hơn khi trả lời câu dài.

Trong suốt năm phép thử, bảng theo dõi hiển thị chỉ số theo thời gian thực, và bot **không lần nào tự nhận nhầm tiếng của chính mình là ngắt lời**. Sau cuộc gọi, người thử chấm bot nghe có giống người không (R12).

Ngoài ra: bộ chỉ số ở §9 chạy được bằng một lệnh, sinh ra báo cáo đầy đủ gồm cả bảng ablation và đường cong đánh đổi.

## 11. Ngoài phạm vi

Bảy mục dưới đây là nơi các đồ án tương tự chết. Mỗi cái đều hợp lý một cách riêng lẻ; cộng lại thì hết học kỳ.

- Huấn luyện mô hình nhận dạng giọng nói hoặc tổng hợp giọng nói mới
- Sinh câu trả lời tự do bằng mô hình ngôn ngữ lớn — đề tài về *khi nào* nói, không phải *nói gì*
- Đấu nối tổng đài viễn thông thật
- Hội thoại từ ba người trở lên
- Nhận dạng cảm xúc, hoặc nhận dạng danh tính người nói
- Giao diện đẹp — bảng theo dõi chỉ cần đọc được
- Nghiệp vụ thứ sáu ngoài danh sách §4.1

## 12. Tài liệu tham khảo

**Chính**
- A Survey of Recent Advances on Turn-taking Modeling in Spoken Dialogue Systems — IWSDS 2025. https://aclanthology.org/2025.iwsds-1.27.pdf
- Data-driven models for timing feedback responses in a Map Task dialogue system — *Computer Speech & Language*, 2014 (Q2). https://doi.org/10.1016/j.csl.2014.02.002

**Phương pháp**
- Voice Activity Projection: Self-supervised Learning of Turn-taking Events. https://arxiv.org/abs/2205.09812
- Multilingual Turn-taking Prediction Using Voice Activity Projection — LREC-COLING 2024. https://aclanthology.org/2024.lrec-main.1036/
- Prompt-Guided Turn-Taking Prediction — SIGDIAL 2025. https://aclanthology.org/2025.sigdial-1.9.pdf
- Endpoint Anticipation for Low-Latency Spoken Dialogue — 2026. https://arxiv.org/html/2606.13450
- Continuous prediction of backchannel timing for human-robot interaction — Interspeech 2025. https://www.isca-archive.org/interspeech_2025/paierl25_interspeech.pdf

**Bối cảnh**
- From Turn-Taking to Synchronous Dialogue: A Survey of Full-Duplex Spoken Language Models. https://arxiv.org/html/2509.14515v1
- Modelling the Interaction of Intonation and Lexical Tone in Vietnamese — cơ sở cho giả thuyết §7
- Vietnamese ASR: A Revisit. https://arxiv.org/html/2603.14779

---

*Mọi mốc thời gian và phép tính minh hoạ trong tài liệu này đều nêu rõ giả định. Số baseline chưa có và phải do nhóm tự đo — không điền bằng số tham khảo từ nguồn khác.*
