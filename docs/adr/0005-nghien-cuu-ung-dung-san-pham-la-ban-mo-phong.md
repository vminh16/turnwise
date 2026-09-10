# ADR-0005 — Đề tài là nghiên cứu ứng dụng; sản phẩm cuối là bản mô phỏng

- **Trạng thái:** Đã chấp nhận
- **Ngày:** 2026-09-10
- **Liên quan:** `SPEC.md` §9, §10, §11; `docs/roadmap.md`; sửa một câu ở ADR-0002

## Bối cảnh

`SPEC.md` mô tả bài toán, chỉ số và quy tắc báo cáo rất kỹ, nhưng không nói thẳng **đích đến là
gì**. Đọc §9 và §12 một mình thì rất dễ hiểu nhầm đây là nghiên cứu thuần nhằm viết bài đăng, và
tài liệu do dự án tự sinh ra đã trôi theo hướng đó: ADR-0002 kết luận một kết cục là "kết quả
công bố được", ADR-0003 gọi chỉ số §9.1 là "chỉ số khoa học chính", `README.md` tự mô tả là
"a research project".

Cách hiểu đó dẫn tới thứ tự ưu tiên sai. Nghiên cứu thuần thưởng cho cái mới; ứng dụng thưởng cho
cái chạy được. Hai thứ đó chọn khác nhau ở đúng những ngã rẽ đắt tiền nhất của dự án này.

## Quyết định

**Đây là nghiên cứu ứng dụng. Đích đến là một ứng dụng chạy được.**

Sản phẩm cuối là **bản mô phỏng trợ lý giọng nói CSKH**: năm luồng nghiệp vụ của NetCo, ngắt lời
được, có bảng theo dõi, chạy trên laptop, demo được cho người chưa từng dùng.

Nói rõ nó **không** là gì, vì đây là chỗ dễ trượt nhất:

- Không phải ứng dụng thương mại hoàn chỉnh.
- Không lắp vào doanh nghiệp thật, không đấu nối tổng đài viễn thông.
- Không dùng dữ liệu khách hàng thật. NetCo là công ty giả định, backend là stub.
- Không nhằm vận hành 24/7: bền bỉ ở mức "một buổi demo không hỏng", không phải mức SLA.

**Phần đo đạc phục vụ sản phẩm, không phải phục vụ một bài nộp.** Ba baseline, đường cong đánh
đổi và ablation tồn tại để trả lời ba câu hỏi kỹ thuật: cách cũ có hỏng thật không; mô hình mã
nguồn mở có sẵn đã đủ tốt cho tiếng Việt chưa; nếu chưa thì hỏng ở đâu. Không có ba câu trả lời
đó thì sản phẩm chỉ là một bản demo không ai biết nó hơn cái gì và hơn bao nhiêu.

**Thứ tự ưu tiên khi chọn phương pháp: thích ứng trước, tự dựng sau.** Vá đúng chỗ mô hình có sẵn
hỏng, hoặc tinh chỉnh nó trên dữ liệu đóng vai, được ưu tiên hơn dựng một hướng mới từ đầu. Chỉ
dựng mới khi số đo ở Giai đoạn 2 cho thấy cái có sẵn không cứu được.

## Hệ quả

- Kết cục "mô hình có sẵn đã đủ tốt, ship nó và dồn công sức vào `dialog/`" là một **kết cục
  tốt**, không phải thất bại. Với nghiên cứu thuần thì đó là bài không có đóng góp; với ứng dụng
  thì đó là tiết kiệm được nửa học kỳ.
- Câu ở phần Hệ quả của ADR-0002 — *"nếu thắng trên các thanh điệu khó mà thua ở tổng, đó vẫn là
  kết quả công bố được"* — đọc theo khung mới là: đó vẫn là **kết quả kỹ thuật dùng được**, vì nó
  chỉ ra nên định tuyến theo thanh điệu nào, hoặc nên chấp nhận đánh đổi nào trong sản phẩm.
  ADR-0002 giữ nguyên nội dung theo quy ước ở ADR-0001; câu này thay thế cách diễn giải của nó.
- Chỉ số §9.1 (lỗi theo thanh điệu âm tiết cuối) vẫn là chỉ số quan trọng nhất, nhưng vì lý do
  khác: nó **chỉ đường**. Lỗi rải đều nghĩa là vấn đề ở ngưỡng và ở luồng; lỗi dồn vào vài thanh
  nghĩa là đã biết chính xác phải vá gì.
- Năm quy tắc báo cáo ở §9.3 giữ nguyên và còn thiết thực hơn: chúng tồn tại để nhóm không tự lừa
  mình rằng sản phẩm đã đủ tốt.
- `SPEC.md` §10 và §11 không đổi. Định nghĩa "xong" và bảy mục ngoài phạm vi vẫn là thứ chặn dự án
  phình ra, và khung ứng dụng không phải cái cớ để mở lại chúng — đặc biệt là mục "đấu nối tổng
  đài thật" và "sinh câu trả lời bằng LLM", hai thứ mà chữ "làm sản phẩm thật" hay kéo theo.

## Các phương án đã cân nhắc

- **Để ngỏ như cũ.** Rẻ nhất, nhưng đã chứng minh là gây trôi: ba tài liệu do dự án tự sinh đều
  đã ngả sang khung nghiên cứu thuần mà không ai quyết định điều đó.
- **Sửa `SPEC.md` §9 cho bớt vẻ học thuật.** Không chọn. §9 mô tả *đo cái gì*, và những chỉ số đó
  đúng cho cả hai khung. Vấn đề nằm ở mục đích của phép đo, và mục đích thuộc về ADR.
- **Đổi định nghĩa "xong" ở §10 để bao gồm cả phần đóng gói.** Không chọn. §10 đang là ranh giới
  bảo vệ đề tài; nới nó ra là mất chính thứ đang giữ cho dự án kết thúc được.
