# ADR-0007 — Ngữ điệu kết thúc lượt được đo trên hội thoại tự nhiên, tách khỏi dữ liệu kiểm thử sản phẩm

- **Trạng thái:** Đã chấp nhận
- **Ngày:** 2026-10-28
- **Liên quan:** `SPEC.md` §6, §7, §9.1, §11; ADR-0002, ADR-0005, ADR-0006; `docs/roadmap.md` §6 GĐ 1–3;
  `docs/research/analysis-corpus.md`; `docs/research/data-and-method.md` §4.2, §10 câu 1–3;
  `docs/annotation-guide.md`

## Bối cảnh

Giai đoạn 1 dồn mọi phép đo vào **một** bộ dữ liệu: cuộc gọi đóng vai tổng đài NetCo, tự thu, có
đồng ý. Sau hơn một tháng, bộ đó có khoảng hai cuộc hội thoại dùng được, với hai người nói đều là
tác giả kịch bản (`evaluation/dataset.py`, `AUTHORS`). Tìm người thu đã khó, tìm người nói giọng
Trung và giọng Nam còn khó hơn.

Bộ dữ liệu đó đang phải trả lời hai câu hỏi khác nhau về bản chất:

1. **Câu hỏi về tiếng Việt:** ở cuối một lượt nói tự nhiên, ngữ điệu và thanh điệu của âm tiết cuối
   báo hiệu điều gì, có khác nhau giữa các miền không, và các endpointer có sẵn hỏng ở thanh nào.
   Đây là chỉ số chính của `SPEC.md` §9.1. Nó cần **nhiều người nói, đủ ba miền, hội thoại thật**.
2. **Câu hỏi về sản phẩm:** bot NetCo có làm đúng năm hành vi §4.3 và năm phép thử §10 không.
   Câu này cần **đúng bối cảnh nghiệp vụ** nhưng không cần nhiều người nói.

Dữ liệu đóng vai tối ưu cho câu 2 và làm hỏng câu 1. Kịch bản ép hành vi xuất hiện
(`data-and-method.md` §5.3, G4), nên tần suất ngắt lời và tiếng đệm phản ánh kịch bản chứ không
phản ánh người nói. Người gọi nói với bot cũng khác người nói với người (`SPEC.md` §3). Với hai
người nói thì không có phân tích theo thanh điệu nào có ý nghĩa thống kê.

`data-and-method.md` §10 câu 1 đã để treo đúng quyết định này: `SPEC.md` §6 có cho dùng corpus
nghiên cứu hội thoại thật, có đồng ý, nhưng không theo kịch bản không. Lối đọc (a): §6 là quy tắc
về dữ liệu của sản phẩm. Lối đọc (b): §6 là tuyệt đối cho mọi âm thanh dự án chạm tới.

## Quyết định

**Chọn lối đọc (a), và tách dữ liệu thành hai bộ có vai trò khác nhau.**

| | **Bộ phân tích** | **Bộ kiểm thử sản phẩm** |
|---|---|---|
| Trả lời | Câu 1: ngữ điệu và thanh điệu ở cuối lượt; benchmark B1, B2, B3 và hệ đề xuất tách theo thanh, theo miền | Câu 2: hành vi §4.3, phép thử §10, R3, R5 |
| Nguồn | Hội thoại tiếng Việt tự nhiên giữa hai người, đủ ba miền, theo thứ tự ưu tiên: corpus đã công bố có chép lời → corpus chưa có nhãn → audio phỏng vấn, podcast đời thật (`analysis-corpus.md` §3) | Các cuộc gọi đóng vai đã thu, `scenarios/*.yaml`, phép thử sống với người chưa từng dùng hệ thống |
| Quy mô | Vài giờ gán nhãn, khoảng 30 người nói trở lên, ước lượng ở `analysis-corpus.md` §6 | Nhỏ, như hiện có |
| Holdout | Riêng, chia theo người nói và theo hội thoại, mở một lần | Giữ như pha 1.5 |

Năm điều đi kèm:

1. **Không tự thu thêm cho bộ phân tích.** Web thu `collector/` và chín kịch bản `roleplay/` ở lại
   để phục vụ bộ kiểm thử sản phẩm.
2. **Thứ tự nguồn**: Babel Vietnamese (`LDC2017S01`) nếu mỗi phía cuộc gọi có kênh riêng và mua
   được, rồi CALLFRIEND Vietnamese (`LDC96S60`). Nếu không mua được thì dùng nguồn tầng 3 miễn phí
   (`analysis-corpus.md` §4, phương án B). Đối chứng liên ngôn ngữ dùng nhãn có sẵn: Easy-Turn và
   MagicData-RAMC (Quan Thoại), TurnBench.
3. **Lấy mẫu để giữ tính tự nhiên**: chọn hội thoại và cửa sổ ngẫu nhiên, gán nhãn **mọi** điểm
   ngừng trong cửa sổ, không lọc theo chủ đề, giới hạn đóng góp của từng người nói, ghi trước kế
   hoạch phân tích (`analysis-corpus.md` §5). Ngắt lời được đo đúng như nó tự xảy ra, không ép bằng
   kịch bản.
4. **Quyền dùng**: chỉ dùng nguồn có giấy phép hoặc điều khoản cho phép nghiên cứu. Không phát hành
   lại âm thanh. Chỉ công bố mã nguồn gốc (ID), mốc thời gian, nhãn và số đo. Không bao giờ dùng ghi
   âm cuộc gọi khách hàng của bất kỳ công ty nào. Phạm vi phi thương mại theo ADR-0006.
5. **Mục đích sản phẩm không đổi** (ADR-0005). Bộ phân tích là cách để trả lời câu hỏi số 3 của
   ADR-0005, *"nếu chưa đủ thì hỏng ở đâu"*, bằng dữ liệu tổng quát hơn cuộc gọi NetCo. Kết quả của
   nó báo cáo được độc lập với app, nhưng nó không mở lại mục nào ở `SPEC.md` §11.

## Hệ quả

- Chỉ số chính §9.1 được đo trên bộ phân tích. Các chỉ số còn lại của §9.1 và toàn bộ §9.2 vẫn đo
  trên hệ sống và bộ kiểm thử sản phẩm. Độ trễ vẫn chỉ lấy từ `uv run pytest -m latency` (§9.3,
  quy tắc 4).
- **Có hai chỗ bộ phân tích không đo được, và phải nói rõ khi báo cáo:**
  - R5 (bot nhận nhầm tiếng của chính nó) không tồn tại trong hội thoại người với người.
  - R3 (dừng khi bị ngắt lời) chỉ có phần mô tả ngữ điệu của người ngắt lời, không có phản ứng của
    bot. Với nguồn đơn kênh, phần này còn yếu hơn nữa.
- Bộ phân tích mang theo một độ lệch miền: hội thoại người với người, phần lớn không phải nghiệp vụ.
  Báo cáo phải đặt kết quả của hai bộ cạnh nhau, không suy kết quả của bộ này sang bộ kia.
- Việc phải làm trước khi gán nhãn bộ vàng (`analysis-corpus.md` §7):
  - xác định quyền truy cập LDC;
  - viết hướng dẫn gán nhãn cho hội thoại người với người;
  - thêm chế độ người với người cho `evaluation/golden.py`, vốn đang chia lượt theo `bot_speaking`;
  - chạy một pilot khoảng 1 giờ.
- Tài liệu phải sửa theo quyết định này: `SPEC.md` §6 và §9.1, `AGENTS.md` (Off-Limits), `README.md`,
  `docs/roadmap.md` GĐ 1–3, `docs/annotation-guide.md` (phạm vi), `.claude/rules/evaluation.md`.
- Câu *"tinh chỉnh nó trên dữ liệu đóng vai"* ở ADR-0005 đọc thành: tinh chỉnh trên dữ liệu thuộc
  phần train của bộ phân tích, nếu GĐ 2 cho thấy có lý do. Bộ kiểm thử sản phẩm và mọi holdout
  không bao giờ được dùng để huấn luyện. ADR-0005 giữ nguyên nội dung theo quy ước ở ADR-0001.

## Các phương án đã cân nhắc

- **Tiếp tục tự thu đóng vai cho đủ khoảng 9 giờ và 24–30 người** (`data-and-method.md` §5.3).
  Loại. Sau một tháng mới có hai người nói, và kể cả thu đủ thì kịch bản vẫn ép hành vi, nên phân
  tích ngữ điệu tự nhiên vẫn không đứng được.
- **Đổi sang hội thoại tự do hai người, vẫn tự thu.** Loại ở thời điểm này. Nó tự nhiên hơn nhưng
  vẫn vướng đúng nút thắt tuyển người, nhất là người giọng Trung và giọng Nam.
- **Chỉ dùng tập test tiếng Việt của `smart-turn`.** Loại: 100% giọng tổng hợp
  (`data-and-method.md` §4.3), và nó cùng phân phối với dữ liệu huấn luyện của B2.
- **Chỉ dùng corpus Quan Thoại hoặc tiếng Anh.** Loại làm nguồn chính vì không trả lời được câu hỏi
  về tiếng Việt. Giữ lại làm đối chứng.
- **Lối đọc (b), §6 tuyệt đối.** Loại vì nó đòi hỏi chính điều đã không làm được: tự thu đủ người
  nói ba miền.
- **Đổi đề tài sang app khác.** Loại. Vấn đề nằm ở cách lấy dữ liệu, không nằm ở bài toán; bài toán
  turn-taking tiếng Việt vẫn còn nguyên khoảng trống (ADR-0002).
