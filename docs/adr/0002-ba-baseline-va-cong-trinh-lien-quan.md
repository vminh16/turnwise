# ADR-0002 — Ba baseline, và điều chỉnh phát biểu đóng góp

- **Trạng thái:** Đã chấp nhận
- **Ngày:** 2026-09-10
- **Liên quan:** `SPEC.md` §2, §5 (R8), §7, §9.3; ADR-0001

## Bối cảnh

`SPEC.md` §5 ban đầu chỉ yêu cầu một baseline: ngưỡng im lặng. Khảo sát công trình liên quan (tra ngày 2026-09-10) cho thấy yêu cầu đó không còn đủ.

**Đã tồn tại endpointer mã nguồn mở công bố hỗ trợ tiếng Việt:**

| Công trình | Giấy phép | Dạng | Tiếng Việt |
|---|---|---|---|
| `pipecat-ai/smart-turn` v3.2 | BSD-2 | Whisper Tiny + linear head, ~8M tham số, ONNX int8 8MB, 16kHz mono, ≤8s, 10–100ms trên CPU | Có, trong danh sách 23 ngôn ngữ |
| `videosdk-live/NAMO-Turn-Detector-v1` | Apache-2.0 | mmBERT + classifier trên văn bản ASR, ONNX lượng tử hoá, <29ms | Có, kèm model riêng `Namo-Turn-Detector-v1-Vietnamese` |
| LiveKit turn-detector | Apache-2.0 | Qwen2.5-0.5B fine-tune trên văn bản | Không |
| `MaAI-Kyoto/MaAI`, `inokoj/VAP-Realtime`, `ErikEkstedt/VoiceActivityProjection` | MIT | Voice Activity Projection, stereo, chạy CPU | Không — chỉ Anh, Trung, Nhật |

Cả hai model có tiếng Việt đều **không công bố nguồn dữ liệu tiếng Việt** (thật hay tổng hợp) và **không báo cáo số liệu tách riêng cho tiếng Việt**. `RESEARCH.md` của NAMO liệt kê độ chính xác cho Turkish, Korean, Japanese, German, Hindi, không có Vietnamese; chỉ có con số trung bình 90,25% trên 23 ngôn ngữ.

**Một tiền lệ gần:** *Thai Semantic End-of-Turn Detection for Real-Time Voice Agents* (arXiv 2510.04016, 2025) tự nhận là nghiên cứu hệ thống đầu tiên về EOT tiếng Thái. Tiếng Thái cũng là ngôn ngữ thanh điệu. Nhưng công trình đó **chỉ dùng văn bản**, dựng dữ liệu từ phụ đề YODAS, và không đụng tới F0 hay tương tác thanh điệu–ngữ điệu.

**Một bằng chứng làm giả thuyết §7 phải phát biểu lại:** Hà & Grice, *Modelling the interaction of intonation and lexical tone in Vietnamese*, Speech Prosody 2010 — chính tài liệu đã có trong §12. Kết quả của họ: ở backchannel và ở ngữ cảnh nhường lượt, **ngữ điệu ghi đè lên thanh điệu từ vựng**, và có một boundary tone cao xuất hiện đều đặn ở rìa phải phát ngôn.

## Quyết định

**1. R8 nâng từ một baseline lên ba,** chạy trên cùng ASR, TTS và kịch bản, bật tắt bằng cấu hình:

- **B1 — ngưỡng im lặng.** Quét dải giá trị, không chọn một, theo §9.3 quy tắc 2.
- **B2 — endpointer âm thanh có sẵn.** `pipecat-ai/smart-turn` v3.2, ONNX, dùng nguyên trọng số, không tinh chỉnh.
- **B3 — endpointer ngữ nghĩa trên văn bản ASR.** `Namo-Turn-Detector-v1-Vietnamese`, ONNX, dùng nguyên trọng số, không tinh chỉnh.

Hai model chạy qua `onnxruntime` trên CPU. Không thêm phụ thuộc mới ngoài `onnxruntime` đã có trong nhóm runtime.

**2. Phát biểu đóng góp thu hẹp lại thành bốn điểm còn trống**, thay cho phát biểu "chưa ai xử lý tiếng Việt" ở §2 — phát biểu đó đúng tới 2025 và không còn đúng:

- Chưa công trình nào báo cáo **tỉ lệ lỗi tách theo thanh điệu của âm tiết cuối** — đúng chỉ số chính ở §9.1.
- Chưa có mô hình dự đoán hoạt động giọng nói (VAP) cho tiếng Việt.
- Chưa ai tách thành phần thanh điệu khỏi thành phần ngữ điệu trong F0 để làm tín hiệu chuyển lượt.
- Chưa ai xử lý sự nhập nhằng của "dạ" giữa vai trò tiếng đệm và vai trò một lượt hoàn chỉnh.

**3. Giả thuyết §7 phát biểu lại.** Không phải "F0 mất quyền báo hiệu kết thúc lượt", mà: F0 quan sát được là chồng chập của thanh điệu từ vựng và ngữ điệu phát ngôn; tách hai thành phần cho tín hiệu chuyển lượt tốt hơn F0 thô. Bằng chứng của Hà & Grice cho thấy ngữ điệu vẫn thắng ở đúng vị trí quan trọng, nên giả thuyết vẫn kiểm chứng được và không tự bác bỏ.

## Hệ quả

- Phần đánh giá tốn thêm hai đường chạy. Chi phí thấp: cả hai đều là ONNX chạy CPU, không huấn luyện.
- Câu phản biện "sao không dùng model có sẵn" được trả lời bằng số đo, không bằng lập luận.
- Rủi ro đã biết và chấp nhận: hệ mới có thể **không** thắng B2 trên chỉ số tổng. Nếu thắng trên các thanh điệu khó mà thua ở tổng, đó vẫn là kết quả công bố được, và là kết quả cụ thể hơn.
- §9.3 quy tắc 1 áp dụng cho cả ba baseline: mọi con số đặt trên cùng mặt phẳng cắt lời × độ trễ.
- B3 phụ thuộc độ trễ ASR, nên số đo của nó không so trực tiếp được với B2 nếu không ghi kèm độ trễ ASR. Phải ghi.
- `SPEC.md` §2 và §7 cần sửa lời cho khớp mục 2 và 3 ở trên. Chưa làm trong ADR này.

## Các phương án đã cân nhắc

- **Giữ nguyên một baseline ngưỡng im lặng.** Rẻ nhất, nhưng để hở đúng câu hỏi mà người phản biện sẽ hỏi đầu tiên, và §2 của SPEC sẽ chứa một khẳng định sai.
- **Tinh chỉnh smart-turn trên dữ liệu tiếng Việt rồi coi đó là hệ đề xuất.** Nhanh hơn, nhưng biến đề tài thành bài tập fine-tune và bỏ mất phần phân tích thanh điệu — tức bỏ mất chính đóng góp còn trống.
- **Thêm cả LiveKit turn-detector làm baseline thứ tư.** Loại: không hỗ trợ tiếng Việt, và plugin đã bị đánh dấu deprecated.
- **Dùng MaAI/VAP làm baseline.** Loại ở vai trò baseline vì không có trọng số tiếng Việt nên so sánh sẽ không công bằng. Vẫn giữ làm ứng viên cho *hệ đề xuất* ở §7 hướng 2.
