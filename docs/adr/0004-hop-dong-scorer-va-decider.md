# ADR-0004 — Hình dạng của `Scorer` và `TurnDecider`

- **Trạng thái:** Đã chấp nhận
- **Ngày:** 2026-09-10
- **Liên quan:** ADR-0003 (mục "Chưa quyết"); `SPEC.md` R1, R4, §8, §9.3; `src/turnwise/turn/base.py`

## Bối cảnh

ADR-0003 đặt seam ở `turn/deciders/` nhưng cố ý để ngỏ hình dạng interface. Giờ phải chốt,
vì không có nó thì không viết được adapter nào.

Một câu hỏi lộ ra khi viết: **một scorer trả về một số, nhưng SPEC có hai câu hỏi khác trục.**
R1 hỏi *khách nói xong chưa*. R4 hỏi *cái vừa nghe có phải chỉ là tiếng đệm không*. Gộp chung
vào một thang điểm thì "sắp xong" và "đây là tiếng đệm" triệt tiêu lẫn nhau ở khâu hợp nhất mà
không ai nhìn thấy — trong khi đúng hai thứ đó là hai hành vi mà §4.3 đòi phải phân biệt.

## Quyết định

**1. Scorer khai báo câu hỏi nó trả lời.** Một enum `Prediction` với hai giá trị,
`END_OF_TURN` và `BACKCHANNEL`. Fusion gộp riêng từng nhóm, và mỗi nhóm có ngưỡng riêng
(`turn.decision.take_threshold`, `turn.decision.backchannel_threshold` trong `configs/`).

**2. `score()` trả về `float | None`**, xác suất trong [0, 1] rằng điều `predicts` mô tả là
đúng ở khung này; `None` là bỏ phiếu trắng. Dùng `None` thay vì một sentinel riêng vì nó vừa
là cách diễn đạt ngắn nhất, vừa được kiểu tĩnh kiểm tra, và không thể nhầm với 0.5.

**3. `decide()` trả về `TurnDecision` ở mọi khung**, không chỉ khi trạng thái đổi. R1 yêu cầu
ước lượng liên tục; một chuỗi `HOLD` liền mạch là bằng chứng hệ thống đang theo dõi chứ không
phải đang đếm ngược. `HOLD` là mặc định khi thiếu cơ sở: nhận lượt sai thì cắt lời khách, giữ
im thừa một khung chỉ tốn 20ms.

**4. Cả hai protocol có `reset()`.** Trạng thái rò rỉ giữa hai lượt làm sai điểm mà không
crash. Mỗi scorer phải có test khẳng định: cùng đầu vào, cách nhau một `reset()`, cho ra cùng
đầu ra.

**5. Khởi tạo tốn kém được phép, `decide()` thì không.** B2 và B3 nạp mô hình ONNX. Nạp trong
`decide()` là làm hỏng phép đo độ trễ.

## Hệ quả

- Thêm một scorer cho câu hỏi thứ ba sau này sẽ cần thêm một giá trị `Prediction` và một ngưỡng
  — chi phí có thật, nhưng lộ ra ở đúng chỗ thay vì ẩn trong một thang điểm gộp.
- Ba baseline không có scorer nào; `TurnDecision.scores` của chúng rỗng. Đó là dữ liệu đúng,
  không phải thiếu dữ liệu: chúng không chấm điểm thành phần nào cả.
- `Scorer` là `Protocol`, không phải lớp cơ sở. Adapter không cần kế thừa gì, nên một scorer
  giả trong test chỉ là một lớp bốn dòng.

## Các phương án đã cân nhắc

- **Một thang điểm duy nhất, backchannel suy ra sau.** Ít máy móc hơn, nhưng đúng là lỗi mô tả
  ở phần Bối cảnh.
- **Hai protocol riêng, `EndOfTurnScorer` và `BackchannelScorer`.** Cùng hiệu quả, nhưng hai
  kiểu giống hệt nhau về hình dạng chỉ để mang một nhãn — một trường enum rẻ hơn.
- **Bỏ phiếu trắng bằng một sentinel `ABSTAIN` riêng.** Rõ nghĩa hơn khi đọc, nhưng thêm một
  kiểu vào mọi chữ ký và mọi phép so sánh, đổi lại không có gì mà `None` chưa làm được.
- **`decide()` chỉ trả về khi trạng thái đổi.** Ít bản ghi hơn, nhưng mất chính thứ cần đo:
  đường xác suất theo thời gian, và độ trễ từ lúc khách dứt lời tới lúc quyết định lật.
