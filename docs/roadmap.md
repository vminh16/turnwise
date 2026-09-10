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

## 1. Đây là loại dự án gì

**Nghiên cứu ứng dụng, đích đến là một ứng dụng chạy được.** Không phải nghiên cứu thuần
để viết bài đăng.

Sản phẩm cuối là **bản mô phỏng trợ lý giọng nói CSKH**: chạy được năm luồng nghiệp vụ
của NetCo, ngắt lời được, có bảng theo dõi, chạy trên laptop, demo được cho người chưa
từng dùng. **Không phải** một ứng dụng thương mại hoàn chỉnh, và **không** lắp vào doanh
nghiệp thật.

Điều đó quyết định vai trò của phần đo đạc. Baseline, đường cong đánh đổi và ablation ở
đây **không phải để nộp cho ai chấm**. Chúng trả lời ba câu hỏi kỹ thuật mà bất kỳ ai
nhìn sản phẩm cũng sẽ hỏi:

1. Cách cũ — ngưỡng im lặng — hỏng thật, hay chỉ là mình chưa chỉnh khéo? (B1 trả lời)
2. Mô hình mã nguồn mở có sẵn đã đủ tốt cho tiếng Việt chưa? (B2, B3 trả lời)
3. Nếu chưa đủ, nó hỏng **ở đâu**, để biết cần vá chỗ nào? (phân tích theo thanh điệu
   trả lời)

Không có ba câu trả lời đó thì sản phẩm cuối chỉ là một bản demo không ai biết nó tốt
hơn cái gì, hay tốt hơn bao nhiêu. Có chúng thì mỗi quyết định kỹ thuật đều có số đứng
sau. Đó là toàn bộ lý do đo, không hơn.

## 2. Bài toán, gọn lại

Ngưỡng im lặng cố định không thể đúng, vì *đang nghĩ* và *đã nói xong* giống hệt nhau
trên trục biên độ. Ba lỗi đối kháng — cắt lời, chờ quá lâu, không cho ngắt — và không
giá trị ngưỡng nào tránh được cả ba. Chi tiết: `SPEC.md` §1.

Chứng minh mệnh đề đó là việc của baseline B1, không phải của lời văn.

## 3. Chỗ tiếng Việt khác, và vì sao nó là việc kỹ thuật

Từ tháng 9/2026 đã có endpointer mã nguồn mở công bố hỗ trợ tiếng Việt
(`pipecat-ai/smart-turn` v3.2, `Namo-Turn-Detector-v1-Vietnamese`). Nên câu hỏi đúng
**không phải** "tiếng Việt đã ai làm chưa" mà là "cái có sẵn dùng được tới đâu".

Bốn chỗ chưa ai đo, và cả bốn đều ảnh hưởng trực tiếp tới việc sản phẩm chạy tốt hay
không (ADR-0002):

1. Không ai báo cáo tỉ lệ lỗi **tách theo thanh điệu của âm tiết cuối** — nên không biết
   mô hình có sẵn hỏng đều hay hỏng dồn vào vài thanh.
2. Không có mô hình dự đoán hoạt động giọng nói (VAP) cho tiếng Việt.
3. Không ai tách thanh điệu khỏi ngữ điệu trong F0 để làm tín hiệu chuyển lượt.
4. Không ai xử lý sự nhập nhằng của "dạ" giữa tiếng đệm và một lượt hoàn chỉnh — mà
   `SPEC.md` §4.3 bắt sản phẩm phải phân biệt đúng.

Cả hai mô hình có sẵn đều không công bố dữ liệu tiếng Việt của họ và không tách số liệu
riêng cho tiếng Việt. Nghĩa là con số duy nhất đáng tin cho quyết định của bạn là con số
bạn tự đo.

## 4. Chỉ số

Chỉ số quan trọng nhất: **chênh lệch tỉ lệ lỗi giữa các thanh điệu của âm tiết cuối**.
Không phải vì nó nghe học thuật, mà vì nó là thứ **chỉ đường**: nếu lỗi rải đều thì vấn
đề nằm ở ngưỡng và ở luồng; nếu lỗi dồn vào vài thanh thì đã biết chính xác phải vá gì ở
GĐ 3. Danh sách đầy đủ ở `SPEC.md` §9.1–9.2.

Năm quy tắc báo cáo ở §9.3 vẫn giữ nguyên, và với dự án ứng dụng chúng còn thiết thực
hơn: hai quy tắc đầu — không báo tỉ lệ cắt lời mà thiếu độ trễ, và baseline quét cả dải
chứ không chọn một điểm — tồn tại để bạn không tự lừa mình rằng sản phẩm đã đủ tốt. Chi
tiết thực thi: `.claude/rules/evaluation.md`.

## 5. Method — chưa chốt, và cố ý chưa chốt

Bốn hướng ở `SPEC.md` §7, chọn sau Giai đoạn 2 dựa trên số đo, ghi vào `docs/adr/`.

Với khung ứng dụng, thứ tự ưu tiên khi chọn nghiêng hẳn về phía rẻ và chắc: **thích ứng
cái đã có** trước, **tự dựng từ đầu** sau, và chỉ khi số đo cho thấy cái đã có không cứu
được.

Ràng buộc đã biết: **không có corpus hội thoại hai kênh tiếng Việt công khai**. VIVOS,
VLSP, BUD500 đều đơn kênh. Nếu chọn hướng VAP thì bắt buộc tự thu — đó là ràng buộc
thật, không phải một lựa chọn còn để ngỏ.

---

## 6. Các giai đoạn

| GĐ | Tên | Xong khi |
|---|---|---|
| 0 | Đường đo | `pytest -m scenario` xanh; `run_baseline.py` vẽ được đường cong B1 |
| 1 | Dữ liệu đóng vai | Manifest có checksum và nhãn; chia theo người nói; holdout khoá |
| 2 | Đo cái có sẵn, chốt hướng | Có số thật cho B1, B2, B3; biết mô hình có sẵn hỏng ở đâu; ADR chốt hướng |
| 3 | Thích ứng cho tiếng Việt | Ablation cho thấy phần thêm vào đóng góp bao nhiêu, ở thanh điệu nào |
| 4 | **Trợ lý CSKH chạy được** | Năm phép thử §10 chạy với người chưa từng dùng hệ thống |
| 5 | Bản demo đóng gói + hồ sơ bằng chứng | Người khác cài trên máy họ và demo lại được, không cần hỏi ai |

**GĐ 4 là mục tiêu chính của repo.** GĐ 0–3 tồn tại để GĐ 4 hoạt động và để biết nó tốt
tới đâu. GĐ 5 làm cho nó rời khỏi được máy của bạn.

### GĐ 0 — Đường đo

Dựng đủ hạ tầng để **đo được**, trước khi có bất kỳ mô hình nào. Thứ tự: `config.py`
đọc `configs/default.yaml` đã có → `audio/source.py` và một adapter đọc file wav →
`deciders/silence_threshold.py` (B1, đơn giản nhất) → `telemetry/collector.py` → năm
file `scenarios/*.yaml` → `evaluation/metrics.py`.

B1 đi trước mọi thứ vì nó vừa là baseline bắt buộc, vừa là bài kiểm tra rẻ nhất cho toàn
bộ seam: nếu B1 không cắm vừa `TurnDecider` thì thiết kế sai, và biết điều đó bây giờ rẻ
hơn nhiều so với biết sau khi đã viết fusion.

Chưa mô hình nào. Chưa micro. Chưa dữ liệu thật.

### GĐ 1 — Dữ liệu đóng vai

Đường găng của cả dự án, và tốn thời gian thật chứ không tốn code.

Mục tiêu **không phải** xây một corpus để phát hành. Mục tiêu là đủ dữ liệu để (a) đo
được ba baseline một cách trung thực, (b) vá được chỗ hỏng tìm thấy ở GĐ 2, và (c) chạy
được năm phép thử ở GĐ 4. Thu vừa đủ, đừng thu để cho oai.

Việc phải làm: kịch bản đóng vai cho năm luồng nghiệp vụ, thu **hai kênh** có đồng ý,
viết `docs/annotation-guide.md`, gán nhãn, sinh manifest kèm sha256, chia tập **theo
người nói** chứ không theo phát ngôn, khoá holdout.

Chia theo phát ngôn làm mọi con số về sau lạc quan hơn thực tế, và sai lầm đó không để
lại dấu vết nào trong chỉ số — bạn sẽ tưởng sản phẩm tốt hơn thực tế đúng vào lúc đem đi
demo.

### GĐ 2 — Đo cái có sẵn, chốt hướng

Giai đoạn quyết định phần lớn công sức của GĐ 3.

Chạy B1 quét cả dải, B2 và B3 giữ nguyên trọng số, trên tập validation. Phân tích lỗi
tách theo thanh điệu và theo bốn hành vi ở §4.3 (ngập ngừng, tiếng đệm, nói đè, trả lời
ngắn). Đặt ba đường cong cạnh nhau, rồi chốt hướng §7 bằng một ADR.

Ba kết cục, và cả ba đều là kết quả hợp lệ:

- **Cái có sẵn đủ tốt.** Ship B2, dồn công sức còn lại vào `dialog/` và trải nghiệm. Ghi
  ADR nói rõ vì sao không tự làm. Đây là kết cục **tốt** cho một dự án ứng dụng, không
  phải kết cục thất bại.
- **Cái có sẵn hỏng dồn vào vài thanh điệu hoặc vài hành vi.** Đây là kết cục dễ xảy ra
  nhất và cũng hữu ích nhất: GĐ 3 biết chính xác phải vá gì.
- **Cái có sẵn hỏng đều và nặng.** Lúc đó mới cân nhắc dựng hướng VAP từ đầu, với con mắt
  tỉnh táo về thời gian còn lại.

Bỏ qua giai đoạn này để nhảy thẳng vào GĐ 3 nghĩa là tự làm một thứ mà không biết cái có
sẵn đã giải quyết được bao nhiêu — cách chắc chắn nhất để tiêu hết học kỳ vào việc phát
minh lại thứ đã có.

### GĐ 3 — Thích ứng cho tiếng Việt

Vá đúng chỗ GĐ 2 chỉ ra. Theo thứ tự rẻ trước:

1. Thêm scorer nhắm đúng chỗ hỏng, hợp nhất với điểm của mô hình có sẵn — ví dụ một
   scorer thanh điệu, hoặc một scorer phân biệt "dạ" tiếng đệm với "Dạ." trọn lượt.
2. Tinh chỉnh mô hình có sẵn trên dữ liệu đóng vai đã thu.
3. Dựng hướng mới từ đầu — chỉ khi hai cách trên không cứu được.

Cả ba đều không phá `SPEC.md` R8: baseline vẫn là **trọng số nguyên bản**, còn bản đã
tinh chỉnh là hệ đề xuất. Đó là hai adapter khác nhau ở cùng một seam (ADR-0003).

Đây cũng là chỗ kiểm chứng giả thuyết tách thanh điệu khỏi ngữ điệu. Ablation qua
`configs/ablation/` phải cho thấy phần thêm vào đóng góp **bao nhiêu** và **ở thanh điệu
nào** — nếu không đo được đóng góp riêng thì không biết có nên giữ nó trong sản phẩm hay
không.

Kết quả có thể là phần thêm vào chỉ cải thiện chút ít. Ghi lại trung thực và giữ sản
phẩm đơn giản còn tốt hơn là nhét vào một thành phần không chứng minh được giá trị.

### GĐ 4 — Trợ lý CSKH chạy được ← mục tiêu chính

`dialog/` với năm luồng, N5 ưu tiên tuyệt đối ở mọi trạng thái, chuyển máy kèm ngữ cảnh,
bảng theo dõi thời gian thực.

Kết thúc bằng đúng năm phép thử ở `SPEC.md` §10, chạy bởi một người chưa từng dùng hệ
thống, trên hai cấu hình đặt cạnh nhau. Đây là lúc dự án trở thành thứ demo được, và là
định nghĩa "xong" của `SPEC.md`.

Nói rõ ranh giới, vì đây là chỗ dễ trượt nhất: bản này là **mô phỏng tổng đài NetCo**.
Backend là stub. NetCo là công ty giả định. Không có khách hàng thật, không có dữ liệu
thật, không đấu nối tổng đài thật.

### GĐ 5 — Bản demo đóng gói + hồ sơ bằng chứng

Làm cho sản phẩm rời được khỏi máy của bạn, và kèm theo bằng chứng nó tốt tới đâu.

- Đóng gói: `Dockerfile` và `.dockerignore` đang rỗng; ảnh container chạy được, mô hình
  tham chiếu bằng checksum trong manifest, hướng dẫn cài mà người ngoài nhóm làm theo
  được không cần hỏi.
- Bền bỉ ở mức demo: mất thiết bị audio, mất kết nối, một scorer hỏng thì suy giảm có
  kiểm soát thay vì sập cả phiên. Đủ để một buổi demo không hỏng, không phải đủ cho
  vận hành 24/7.
- Hồ sơ bằng chứng: mở holdout **đúng một lần**, sinh báo cáo bằng một lệnh — bảng
  ablation, đường cong đánh đổi, chênh lệch tỉ lệ lỗi theo thanh điệu. Đây là thứ trả lời
  câu "sao biết nó tốt", không phải một bài nộp.
- Bàn giao: hoàn tất R9 — điện thoại viên nhận đủ ngữ cảnh đã thu.

**Ngoài phạm vi, và không được lặng lẽ mở lại** — cả bốn đều nằm trong `SPEC.md` §11:

- **Lắp vào doanh nghiệp thật, đấu nối tổng đài viễn thông.** Ranh giới dừng ở WebRTC.
  Cần SIP thì để nó là một adapter *chưa cài đặt* sau seam của `transport/`, có tài liệu,
  không có code.
- **Dữ liệu khách hàng thật.** Chỉ hội thoại đóng vai có đồng ý, mãi mãi.
- **Sinh câu trả lời tự do bằng LLM.** Đề tài trả lời câu hỏi *khi nào* nói. Thay máy
  trạng thái bằng LLM là đổi sang một sản phẩm khác, và làm hỏng phép so sánh với ba
  baseline vì độ trễ sinh câu trộn vào độ trễ chuyển lượt.
- **Giao diện đẹp, và vận hành mức sản xuất.** Bảng theo dõi chỉ cần đọc được. SLA, cảnh
  báo, trực hệ thống đều thuộc về một dự án khác.

Nghiệp vụ thứ sáu vẫn là scope creep ở giai đoạn này, y như ở mọi giai đoạn trước.

---

## 7. Ba chỗ dễ chết

**GĐ 1 chặn GĐ 2, 3 và 4.** Không có dữ liệu hai kênh thì cả ba đứng im. Bắt đầu viết
kịch bản đóng vai sớm, song song với GĐ 0.

**Nhảy sang GĐ 4 quá sớm.** Làm `dialog/` cho cảm giác tiến triển rõ ràng hơn nhiều so
với đo baseline, và năm luồng nghiệp vụ là phần dễ hình dung nhất. Nhưng nếu tầng `turn`
chưa đúng thì trợ lý sẽ cắt lời khách ở mọi luồng, và bạn sẽ đi sửa `dialog/` cho một lỗi
nằm ở `audio/`.

**Làm GĐ 3 mà chưa có GĐ 2.** Tự dựng một hệ mà không biết cái có sẵn giải quyết được bao
nhiêu là cách chắc nhất để tiêu hết thời gian vào việc phát minh lại thứ đã có — và với
dự án ứng dụng thì đó là lỗi tốn kém hơn hẳn so với dự án nghiên cứu thuần.
