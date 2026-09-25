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
