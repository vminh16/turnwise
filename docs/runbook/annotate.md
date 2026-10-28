# Gán nhãn một bản thu

Quy tắc gán nằm ở `docs/annotation-guide.md` (§4.3 nhãn, §5 ca khó). Tài liệu này chỉ nói bấm
vào đâu.

## Một lần

1. Cài Praat, miễn phí: <https://www.fon.hum.uva.nl/praat/>. Bản Windows là một file `.exe`, không
   cần cài đặt.
2. Sinh bản nháp cho mọi bản thu chưa có:

   ```bash
   uv run python -m evaluation.annotation prepare
   ```

   Mỗi bản thu trong `data/raw/<người nói>/` có thêm một file `.TextGrid` cạnh file `.wav`. Lệnh
   này **không bao giờ ghi đè** một TextGrid đã có.

## Mỗi bản thu

1. Praat → **Open → Read from file…**, mở file `.wav` (bản 48 kHz, không phải `.16k.wav`), rồi mở
   file `.TextGrid` cùng tên.
2. Chọn cả hai trong danh sách (giữ Ctrl), bấm **View & Edit**.
3. Kênh trên là **khách**, kênh dưới là **bot**. Năm lớp bên dưới:

   | Lớp | Việc của bạn |
   |---|---|
   | `bot` | không sửa |
   | `caller_act` | sửa ranh giới cho khớp tiếng khách; thay `?` bằng nhãn |
   | `caller_words` | chép lời vào khoảng tương ứng |
   | `asr_draft` | chỉ để nhìn, gõ nhanh hơn; không sửa |
   | `nonspeech` | tuỳ chọn: `cough`, `laugh`, `breath`, `bot_echo`… |

4. Thao tác:
   - **Gán nhãn:** bấm vào một khoảng, gõ vào ô chữ trên cùng. Ví dụ `take`, `hold filled`,
     `barge_in agent`.
   - **Dời ranh giới:** kéo đường ranh giới.
   - **Thêm ranh giới:** bấm vào lớp tại thời điểm cần, nhấn Enter.
   - **Xoá ranh giới:** bấm chọn ranh giới, nhấn Alt+Backspace.
   - **Nghe một đoạn:** bấm vào khoảng rồi nhấn Tab.
5. Lưu: trong cửa sổ danh sách của Praat, chọn TextGrid → **Save → Save as text file…**, ghi đè
   đúng file cũ.

## Kiểm tra

```bash
uv run python -m evaluation.annotation status
```

In số đoạn theo từng nhãn. Còn `?` là còn đoạn chưa gán. Gõ sai tên nhãn thì lệnh báo lỗi kèm mốc
thời gian, sửa rồi chạy lại.

Nhãn **không nằm trong git** (`data/` bị gitignore). Sao lưu thư mục `data/raw/` sau mỗi buổi gán.

## Bộ phân tích: hội thoại hai người

Quy tắc ở `docs/annotation-guide-conversation.md` (v2.0). Các bước bấm:

1. **Lập danh mục** (§2): chép `data/manifests/analysis-catalog.template.csv` thành
   `analysis-catalog.csv`. Trên Calisphere, lọc bộ *Viet Stories*, ngôn ngữ Vietnamese, rồi chép
   **mọi** mục ra, mỗi mục một dòng.
2. **Bốc**:

   ```bash
   uv run python -m evaluation.analysis_sample rank
   ```

   Mở `data/manifests/analysis-sample.csv`. Với mỗi vùng, tải audio của các mục hạng 1 đến
   `windows_per_region` về `data/raw/analysis/viet-stories/<item_id>.mp3`. Nếu kho chia một cuộc
   thành nhiều file, đặt tên `<item_id>_1.mp3`, `<item_id>_2.mp3`.
3. **Sinh TextGrid**:

   ```bash
   uv run python -m evaluation.analysis_sample prepare
   ```

   Mục nào không dùng được thì ghi lý do vào cột `excluded` (§3.1), tải mục hạng kế tiếp của
   cùng vùng, rồi chạy lại `prepare`.
4. **Gán** trong Praat, như phần trên, nhưng với các lớp `window`, `draft`, `A`, `B`, `nonspeech`.
   Chỉ gán trong khoảng `label` của lớp `window`. Mỗi khoảng viết `<nhãn> [thuộc tính] | <lời>`,
   ví dụ `S | hồi đó tôi ở huế`.
5. **Ghi** `dialect_heard`, `annotator`, `guide_version`, `minutes_spent` vào
   `analysis-sample.csv`.
6. **Kiểm tra**:

   ```bash
   uv run python -m evaluation.analysis_sample status
   ```

   Lệnh in số cửa sổ đã xong theo vùng, số nhãn, và số kết thúc `shift`/`hold` theo thanh. Gõ sai
   nhãn thì lệnh báo lỗi kèm mốc thời gian.

`analysis-catalog.csv` và `analysis-sample.csv` **nằm trong git**: đó là bằng chứng việc bốc mẫu
không có chọn tay. Audio và TextGrid thì không.
