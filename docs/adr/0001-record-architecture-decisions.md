# ADR-0001 — Ghi lại các quyết định kiến trúc

- **Trạng thái:** Đã chấp nhận
- **Ngày:** 2026-09-10
- **Liên quan:** `AGENTS.md` (mục "Before Marking Done"), `SPEC.md` §7

## Bối cảnh

`SPEC.md` cố tình không chốt phương pháp. Phương pháp được chọn sau Giai đoạn 0, dựa trên số đo. Nghĩa là dự án sẽ tạo ra một chuỗi quyết định có đánh đổi thật: chọn hướng chấm điểm lượt nói, chọn cách chuẩn hoá F0, chọn baseline nào để so, chọn bỏ hướng nào.

Sáu tuần sau, không ai nhớ vì sao một hướng bị loại. Không có bản ghi thì quyết định bị mở lại, và lần thứ hai người ta thường quyết ngược với lần đầu mà không có thêm bằng chứng nào.

## Quyết định

Mỗi lựa chọn phương pháp hoặc kiến trúc được ghi thành một Architecture Decision Record trong `docs/adr/`, đánh số tăng dần, một trang.

Định dạng cố định, gồm đúng các mục dưới đây:

```markdown
# ADR-NNNN — Tiêu đề ở thể khẳng định

- **Trạng thái:** Đề xuất | Đã chấp nhận | Đã thay thế bởi ADR-NNNN | Đã bỏ
- **Ngày:** YYYY-MM-DD
- **Liên quan:** các mục SPEC, ADR khác, hoặc file cấu hình chịu ảnh hưởng

## Bối cảnh
Sức ép nào dẫn tới quyết định này. Nêu số đo nếu có.

## Quyết định
Chọn cái gì, ở thể chủ động.

## Hệ quả
Được gì, mất gì, và cái gì trở nên khó hơn vì quyết định này.

## Các phương án đã cân nhắc
Từng phương án kèm lý do loại. Đây là phần có giá trị nhất khi đọc lại.
```

Quy ước:

- Tên file: `NNNN-tieu-de-viet-thuong-co-gach-noi.md`.
- ADR không bị xoá hay sửa nội dung sau khi đã chấp nhận. Khi quyết định thay đổi, viết ADR mới và đổi trạng thái ADR cũ thành *Đã thay thế bởi ADR-NNNN*.
- ADR ghi **lý do**, không ghi hướng dẫn sử dụng. Hướng dẫn thuộc về `docs/runbook/`.
- Ngưỡng và siêu tham số cụ thể thuộc về `configs/`, không nằm trong ADR. ADR chỉ nói vì sao chọn cách đặt ngưỡng đó.

## Hệ quả

- Thêm một bước trước khi hợp nhất một phương pháp mới. Đây là chi phí có chủ ý.
- Phần "Các phương án đã cân nhắc" trở thành nguồn viết chương phương pháp của báo cáo cuối, không phải viết lại từ đầu.
- Ablation ở `SPEC.md` §9.3 tham chiếu thẳng tới ADR đã dựng ra thành phần bị tắt.

## Các phương án đã cân nhắc

- **Không ghi gì, dựa vào lịch sử commit.** Commit nói *đã đổi gì*, không nói *vì sao chọn cái này thay vì cái kia*, và không bao giờ ghi lại phương án bị loại.
- **Một file `DECISIONS.md` duy nhất.** Xung đột merge liên tục, và không có cách biểu diễn trạng thái *đã thay thế*.
- **Ghi trong wiki hoặc issue tracker.** Tách rời khỏi nhánh code tạo ra quyết định; không đi cùng khi checkout một commit cũ.
