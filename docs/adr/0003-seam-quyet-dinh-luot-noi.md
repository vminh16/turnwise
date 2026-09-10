# ADR-0003 — Đặt seam ở quyết định lượt nói, và trả quyết định về bằng giá trị

- **Trạng thái:** Đã chấp nhận
- **Ngày:** 2026-09-10
- **Liên quan:** `SPEC.md` R7, R8, §8, §9.3; ADR-0002; `.claude/rules/turn.md`

## Bối cảnh

ADR-0002 nâng R8 lên ba baseline. Bố cục lúc đó đặt việc chạy baseline ở
`evaluation/run_baseline.py`, tách khỏi `src/turnwise/turn/`. Làm đúng như vậy sẽ có hai đường
chạy khác nhau: hệ đề xuất đi qua `turn/fusion`, ba baseline đi qua code trong `evaluation/`.

R8 lại yêu cầu cả bốn chạy trên **cùng** ASR, TTS và kịch bản, bật tắt bằng cấu hình. Với hai
đường chạy, yêu cầu đó chỉ được bảo đảm bằng kỷ luật của người viết. Đường cong đánh đổi ở §9.3
quy tắc 1 khi đó vẽ từ hai nguồn số khác nhau — loại lỗi không bao giờ làm chương trình dừng, và
làm hỏng toàn bộ kết luận.

Vấn đề thứ hai, cùng gốc: `AGENTS.md` yêu cầu mọi quyết định được ghi qua `telemetry.collector`
kèm điểm của từng scorer. Cách đọc tự nhiên nhất là mỗi scorer tự gọi collector. Khi đó ghi log
là hiệu ứng lề rải khắp tầng `turn`; mỗi test scorer phải dựng collector giả; và một scorer quên
gọi thì bảng ablation thiếu một cột mà không có gì báo lỗi.

## Quyết định

**1. Seam ngoài của tầng `turn` là quyết định lượt nói, không phải thành phần chấm điểm.**

`src/turnwise/turn/deciders/` chứa bốn adapter sau cùng một interface:

| File | Vai |
|---|---|
| `fused.py` | Hệ đề xuất — dùng `scorers/` và `fusion.py` |
| `silence_threshold.py` | B1, quét giá trị theo `configs/baseline/` |
| `acoustic_onnx.py` | B2, mô hình âm thanh có sẵn, giữ nguyên trọng số |
| `semantic_onnx.py` | B3, mô hình ngữ nghĩa trên văn bản ASR, giữ nguyên trọng số |

`scorers/` và `fusion.py` trở thành seam **nội bộ**: chỉ adapter `fused.py` và test của chính
tầng `turn` dùng chúng. Không gì ngoài `turn/` import chúng.

`evaluation/` không còn chứa đường ra quyết định nào. Nó chọn adapter theo cấu hình, chạy, chấm
điểm.

**2. Quyết định là giá trị trả về, không phải hiệu ứng lề.**

Decider trả về `TurnDecision` (định nghĩa ở `types.py`) mang: kết quả, điểm của từng scorer,
scorer nào bỏ phiếu trắng, và thanh điệu của âm tiết cuối. Tầng `turn` không gọi telemetry.
Đúng một chỗ — phần nối dây ở `transport/` — ghi giá trị đó xuống `telemetry.collector` kèm
timestamp.

## Hệ quả

- "Cùng ASR, TTS, kịch bản" thành sự thật cấu trúc thay vì lời hứa.
- Năm kịch bản ở §10 chạy được với **mọi** adapter, nên bộ test kịch bản vừa là phép kiểm tra vừa
  là phép so sánh.
- Chỉ số khoa học chính ở §9.1 (lỗi theo thanh điệu âm tiết cuối) được kiểu dữ liệu bảo đảm, thay
  vì phụ thuộc việc ai đó nhớ ghi thanh điệu.
- Test scorer thành so sánh giá trị thuần, không cần dựng phụ thuộc.
- Giữ đúng ràng buộc §8: `telemetry` chỉ đọc, không tác động ngược — vì tầng `turn` không biết nó
  tồn tại.
- Chi phí: thêm một tầng gián tiếp giữa `evaluation/` và `fusion`. Chấp nhận, vì đó chính là chỗ
  R8 cần có công tắc.
- B2 và B3 nạp mô hình ONNX, nên interface của decider phải cho phép khởi tạo tốn kém một lần rồi
  gọi nhiều lần. Chi tiết interface chưa chốt ở ADR này.

## Các phương án đã cân nhắc

- **Giữ baseline trong `evaluation/`.** Ít file hơn, nhưng đúng là vấn đề mô tả ở phần Bối cảnh.
- **Coi baseline là một scorer trong `scorers/`.** Sai tầng: B1, B2, B3 là **hệ quyết định hoàn
  chỉnh**, không phải một nguồn tín hiệu để hợp nhất với nguồn khác. Nhét chúng vào `scorers/` sẽ
  khiến fusion phải biết khi nào cần bỏ qua chính mình.
- **Mỗi scorer tự ghi telemetry.** Đơn giản khi viết dòng đầu tiên, đắt ở mọi dòng sau: test cần
  fake, và cột thiếu thì im lặng.
- **Đợi tới khi có code rồi mới tách.** Không chọn vì lúc đó cái phải gỡ là hai đường ống đã có số
  đo, và những số đó phải đo lại.

## Chưa quyết

Hình dạng cụ thể của `Scorer` — trong đó có nguy cơ scorer trở thành module nông vì §9.3 quy tắc 3
ép mở cấu hình bật tắt — để lại tới khi scorer đầu tiên tồn tại. Ràng buộc "bỏ phiếu trắng là giá
trị trả về hạng nhất" ở §8 giữ nguyên trong mọi phương án.
