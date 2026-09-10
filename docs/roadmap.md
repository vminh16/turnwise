# Lộ trình

Tài liệu này nói **làm theo thứ tự nào và vì sao thứ tự đó**. Nó không thay `SPEC.md`:
bài toán, quy tắc nghiệp vụ và tiêu chí nghiệm thu vẫn ở đó, và khi hai tài liệu mâu
thuẫn thì `SPEC.md` đúng.

Phân biệt nguồn, vì hai thứ này có sức nặng khác nhau:

- **Từ `SPEC.md` và `docs/adr/`** — đã chốt: bài toán, chỉ số, quy tắc báo cáo, ba
  baseline, ranh giới tầng, hợp đồng scorer.
- **Đề xuất trong tài liệu này** — cách chia giai đoạn. `SPEC.md` chỉ nhắc tên "Giai
  đoạn 0" mà không định nghĩa. Thứ tự dưới đây suy ra từ quan hệ phụ thuộc, và sửa
  được mà không đụng tới `SPEC.md`.

---

## 1. Bài toán, gọn lại

Ngưỡng im lặng cố định không thể đúng, vì *đang nghĩ* và *đã nói xong* giống hệt nhau
trên trục biên độ. Ba lỗi đối kháng — cắt lời, chờ quá lâu, không cho ngắt — và không
giá trị ngưỡng nào tránh được cả ba. Chi tiết: `SPEC.md` §1.

Chứng minh mệnh đề đó là việc của baseline B1, không phải của lời văn.

## 2. Đóng góp, đã thu hẹp sau khảo sát

Từ tháng 9/2026 đã có endpointer mã nguồn mở công bố hỗ trợ tiếng Việt, nên "chưa ai
làm cho tiếng Việt" không còn là đóng góp. Bốn khoảng trống còn thật (ADR-0002):

1. Chưa ai báo cáo tỉ lệ lỗi **tách theo thanh điệu của âm tiết cuối**.
2. Chưa có mô hình dự đoán hoạt động giọng nói (VAP) cho tiếng Việt.
3. Chưa ai tách thành phần thanh điệu khỏi ngữ điệu trong F0 để làm tín hiệu chuyển lượt.
4. Chưa ai xử lý sự nhập nhằng của "dạ" giữa tiếng đệm và một lượt hoàn chỉnh.

## 3. Chỉ số

Kết quả khoa học chính: **chênh lệch tỉ lệ lỗi giữa các thanh điệu của âm tiết cuối**.
Mọi con số khác là ngữ cảnh cho con số này. Danh sách đầy đủ ở `SPEC.md` §9.1–9.2.

Năm quy tắc báo cáo ở §9.3 là chỗ dễ mất giá trị nhất, đặc biệt hai quy tắc đầu: không
bao giờ báo tỉ lệ cắt lời mà thiếu độ trễ, và baseline quét cả dải chứ không chọn một
điểm. Chi tiết thực thi: `.claude/rules/evaluation.md`.

## 4. Method — chưa chốt, và cố ý chưa chốt

Bốn hướng ở `SPEC.md` §7, chọn sau Giai đoạn 2 dựa trên số đo, ghi vào `docs/adr/`.

Ràng buộc đã biết: **không có corpus hội thoại hai kênh tiếng Việt công khai**. VIVOS,
VLSP, BUD500 đều đơn kênh. Nếu chọn hướng VAP thì bắt buộc tự thu — đó là ràng buộc
thật, không phải một lựa chọn còn để ngỏ.

---

## 5. Các giai đoạn

| GĐ | Tên | Xong khi |
|---|---|---|
| 0 | Đường đo | `pytest -m scenario` xanh; `run_baseline.py` vẽ được đường cong B1 |
| 1 | Dữ liệu | Manifest có checksum và nhãn; IAA đạt ngưỡng; holdout khoá |
| 2 | Baseline và chọn hướng | Có số thật cho B1, B2, B3; ADR chốt phương pháp |
| 3 | Hệ đề xuất | Bảng ablation đầy đủ; đường cong hệ mới đặt cạnh ba baseline |
| 4 | Nghiệp vụ và đầu-cuối | Năm phép thử §10 chạy được với người chưa từng dùng hệ thống |
| 5 | Báo cáo | Mở holdout đúng một lần; báo cáo sinh bằng một lệnh |
| 6 | Sản phẩm | Người ngoài nhóm cài và chạy được, không cần hỏi ai |

### GĐ 0 — Đường đo

Dựng đủ hạ tầng để **đo được**, trước khi có bất kỳ mô hình nào. Thứ tự: `config.py`
đọc `configs/default.yaml` đã có → `audio/source.py` và một adapter đọc file wav →
`deciders/silence_threshold.py` (B1, đơn giản nhất) → `telemetry/collector.py` → năm
file `scenarios/*.yaml` → `evaluation/metrics.py`.

B1 đi trước mọi thứ vì nó vừa là baseline bắt buộc, vừa là bài kiểm tra rẻ nhất cho
toàn bộ seam: nếu B1 không cắm vừa `TurnDecider` thì thiết kế sai, và biết điều đó bây
giờ rẻ hơn nhiều so với biết sau khi đã viết fusion.

Chưa mô hình nào. Chưa micro. Chưa dữ liệu thật.

### GĐ 1 — Dữ liệu

Đường găng của cả dự án, và tốn thời gian thật chứ không tốn code: viết kịch bản đóng
vai cho năm luồng nghiệp vụ, thu **hai kênh** có đồng ý, viết `docs/annotation-guide.md`,
gán nhãn, đo độ đồng thuận giữa người gán, sinh manifest kèm sha256, chia tập **theo
người nói** chứ không theo phát ngôn, khoá holdout.

Chia theo phát ngôn làm mọi con số về sau lạc quan hơn thực tế, và sai lầm đó không để
lại dấu vết nào trong chỉ số.

### GĐ 2 — Baseline và chọn hướng

**Điểm quyết định lớn nhất của đề tài.** Chạy B1 quét cả dải, B2 và B3 giữ nguyên trọng
số, trên tập validation. Phân tích lỗi tách theo thanh điệu. Đặt ba đường cong cạnh
nhau, rồi chốt hướng §7 bằng một ADR.

Bỏ qua giai đoạn này để nhảy thẳng vào GĐ 3 là mất cả baseline lẫn lý do chọn phương
pháp — đúng thứ mà 72% bài được rà soát trong khảo sát IWSDS 2025 không có.

### GĐ 3 — Hệ đề xuất

Viết scorer và fusion theo hướng đã chốt. Kiểm chứng giả thuyết tách thanh điệu khỏi
ngữ điệu. Ablation từng thành phần qua `configs/ablation/`.

Kết quả có thể là hệ đề xuất **thua** B2 ở chỉ số tổng. Nếu nó thắng trên các thanh điệu
khó, đó vẫn là kết quả công bố được và cụ thể hơn — đừng sửa mục tiêu để tránh khả năng
này.

### GĐ 4 — Nghiệp vụ và đầu-cuối

`dialog/` với năm luồng, N5 ưu tiên tuyệt đối ở mọi trạng thái, chuyển máy kèm ngữ cảnh,
bảng theo dõi thời gian thực. Kết thúc bằng đúng năm phép thử ở `SPEC.md` §10, chạy bởi
một người chưa từng dùng hệ thống, trên hai cấu hình đặt cạnh nhau.

Hết giai đoạn này là **đề tài đã hoàn thành theo định nghĩa của `SPEC.md` §10.**

### GĐ 5 — Báo cáo

Mở holdout đúng một lần. Sinh báo cáo bằng một lệnh: bảng ablation, đường cong đánh đổi,
chênh lệch tỉ lệ lỗi theo thanh điệu.

### GĐ 6 — Sản phẩm

Biến hệ đã kiểm chứng thành thứ người khác cài và chạy được. Giai đoạn này **nằm ngoài
định nghĩa "xong" ở §10** và cố ý như vậy: nó không được phép làm trượt bất cứ điều gì ở
GĐ 0–5, và không mở lại holdout — GĐ 6 không sinh ra con số khoa học nào.

Chạy được sau GĐ 4; không cần chờ GĐ 5, vì nó không phụ thuộc holdout.

**Trong phạm vi:**

- Đóng gói: `Dockerfile` và `.dockerignore` đang rỗng; ảnh container chạy được, mô hình
  tham chiếu bằng checksum trong manifest.
- Bền bỉ: mất thiết bị audio, mất kết nối, phục hồi khi đứt, health check, suy giảm có
  kiểm soát khi một scorer hỏng thay vì sập cả phiên.
- Vận hành: hồ sơ cấu hình cho từng môi trường, telemetry xoay vòng, cảnh báo khi độ trễ
  vượt ngân sách, một runbook người trực đọc được.
- Phát hành: đánh phiên bản, ghi `CHANGELOG.md`, hướng dẫn cài đặt mà người ngoài nhóm
  làm theo được mà không hỏi ai.
- Bàn giao: hoàn tất R9 — điện thoại viên nhận đủ ngữ cảnh đã thu.

**Ngoài phạm vi, và không được lặng lẽ mở lại** — cả ba đều nằm trong `SPEC.md` §11:

- **Đấu nối tổng đài viễn thông thật.** Ranh giới dừng ở WebRTC. Nếu cần SIP thì để nó
  là một adapter *chưa cài đặt* sau seam của `transport/`, có tài liệu, không có code.
- **Sinh câu trả lời tự do bằng LLM.** Đề tài trả lời câu hỏi *khi nào* nói. Thay máy
  trạng thái bằng LLM là đổi sang một đề tài khác, và làm hỏng phép so sánh với ba
  baseline vì độ trễ sinh câu trộn vào độ trễ chuyển lượt.
- **Giao diện đẹp.** Bảng theo dõi chỉ cần đọc được.

Nghiệp vụ thứ sáu vẫn là scope creep ở giai đoạn này, y như ở mọi giai đoạn trước.

---

## 6. Hai chỗ dễ chết

**GĐ 1 chặn GĐ 2 và GĐ 3.** Không có dữ liệu hai kênh thì cả hai đứng im. Bắt đầu viết
kịch bản đóng vai sớm, song song với GĐ 0.

**GĐ 6 hấp dẫn hơn GĐ 2.** Làm sản phẩm cho cảm giác tiến triển rõ ràng hơn nhiều so với
đo baseline. Nhưng đảo thứ tự thì đề tài mất phần khoa học và còn lại một bản demo — và
`SPEC.md` §11 mở đầu bằng đúng cảnh báo đó: mỗi mục hợp lý một cách riêng lẻ, cộng lại
thì hết học kỳ.
