# ADR-0006 — Chấp nhận giấy phép phi thương mại, trừ trọng số cấm phái sinh

- **Trạng thái:** Đã chấp nhận
- **Ngày:** 2026-09-25
- **Liên quan:** `SPEC.md` §5 (R8), §11; ADR-0002; `docs/progress.md` §5; `docs/research/turn-taking-methods.md` §4, §6.2; `pyproject.toml`

## Bối cảnh

`docs/progress.md` §5 để treo hai quyết định giấy phép: `praat-parselmouth` là GPLv3+ nhưng nằm
trong `[project] dependencies`, và `LICENSE` của repo rỗng 0 byte.

Khảo sát ở `docs/research/turn-taking-methods.md` cho thấy vấn đề rộng hơn một thư viện: thứ tốt
nhất trong hệ sinh thái tiếng Việt thường mang giấy phép hạn chế.

| Thành phần | Giấy phép | Tra ngày |
|---|---|---|
| `praat-parselmouth` (F0) | **GPL-3.0-or-later** | metadata gói đã cài, 2026-09-25 |
| `nguyenvulebinh/wav2vec2-base-vietnamese-250h` (ASR, CTC, streaming thật) | **CC BY-NC 4.0** | Hub API, 2026-09-25 |
| `khanhld/wav2vec2-base-vietnamese-160h` | **CC BY-NC 4.0** | Hub API, 2026-09-25 |
| `vinai/PhoWhisper-*` | BSD-3-Clause | Hub API, 2026-09-25 |
| `Systran/faster-whisper-*` | MIT | Hub API, 2026-09-25 |
| Trọng số turn-shift của `MaAI-Kyoto/MaAI` (VAP) | **CC BY-NC-ND 4.0** | Hub API, 2026-09-25 |
| Trọng số `inokoj/VAP-Realtime` | mã MIT, trọng số "academic purposes only" | README, 2026-09-25 |
| `pipecat-ai/smart-turn` v3.2 | BSD-2-Clause | ADR-0002 |
| `Namo-Turn-Detector-v1-Vietnamese` | Apache-2.0 | ADR-0002 |
| VieNeu-TTS v3 Turbo | Apache-2.0 | `docs/research/tts-voice.md` |
| `piper-tts` trên PyPI | GPL-3.0-or-later | `docs/progress.md` §5 |

Nhưng ràng buộc thật của dự án đã đổi: đây là **đồ án cá nhân, không thương mại hoá**. `SPEC.md`
§11 và `docs/roadmap.md` GĐ 4 đã ghi bản này là mô phỏng tổng đài NetCo — công ty giả định,
backend stub, không khách hàng thật. Giấy phép phi thương mại không chặn gì trong phạm vi đó.

Chỉ còn một hạn chế cắn thật: **ND (NoDerivatives)** cấm phát hành bản phái sinh, tức cấm công bố
một mô hình đã tinh chỉnh từ trọng số đó.

## Quyết định

1. **Cho phép dùng giấy phép phi thương mại (NC) và copyleft (GPL)** ở mọi vị trí trong dự án, kể
   cả đường chạy chính. `praat-parselmouth` ở lại `[project] dependencies`.
2. **Không tinh chỉnh rồi công bố trọng số có điều khoản ND**, cụ thể là các checkpoint turn-shift
   của MaAI. Chạy chúng nguyên bản để đo thì được; phát hành bản đã tinh chỉnh thì không. Đây là
   lý do hướng "VAP tinh chỉnh" bị loại khỏi danh sách ứng viên, chứ không phải vì kỹ thuật.
3. **Trọng số `VAP-Realtime` chỉ dùng cho mục đích học thuật**, khớp phạm vi đồ án. Ghi rõ điều
   này ở chỗ nào báo cáo số của nó.
4. **`LICENSE` giữ rỗng, tức repo không cấp phép cho ai.** Không phát hành công khai trong học kỳ
   này. Khi nào muốn công khai thì mở ADR mới; lúc đó GPLv3 của `parselmouth` sẽ ép giấy phép của
   repo, và đó là lúc phải cân nhắc thay thư viện F0.
5. **ASR cho B3 và cho sản phẩm chọn theo số đo, không theo giấy phép.** Vì mục 1, các checkpoint
   CTC streaming được (`wav2vec2-base-vietnamese-250h`) đã trở thành ứng viên hợp lệ, cạnh
   PhoWhisper và faster-whisper. Chốt ở GĐ 2, kèm độ trễ đo được.
6. **Thanh điệu cho chỉ số chính vẫn lấy từ nhãn người gán**, không từ ASR, bất kể chọn ASR nào.
   Ràng buộc này là về tính đúng của phép đo, không liên quan giấy phép.

## Hệ quả

- Hai quyết định treo ở `docs/progress.md` §5 đóng lại. Mục TTS đã đóng trước đó ở §6.8 bằng
  VieNeu-TTS (Apache-2.0), nên `piper-tts` trong nhóm `[project.optional-dependencies] tts` là
  thừa và nên gỡ ở một commit riêng.
- Không còn lý do giấy phép nào chặn GĐ 2. Chỗ chặn còn lại là dữ liệu và nhãn.
- Trả giá: repo không công khai được trong học kỳ này mà không mở lại quyết định. Chấp nhận, vì
  bản demo đóng gói ở GĐ 5 là ảnh container chạy trên máy người chấm, không phải bản phát hành.
- Nếu sau này muốn công bố mã nguồn: hoặc repo theo GPLv3, hoặc thay `parselmouth` bằng một cách
  trích F0 giấy phép dễ chịu hơn. Phần ước lượng F0 vì vậy nên nằm sau một hàm riêng, để thay được
  mà không đụng scorer.

## Các phương án đã cân nhắc

- **Chỉ dùng giấy phép dễ dãi ở mọi nơi.** Sạch nhất, nhưng loại mất chính các checkpoint ASR
  tiếng Việt streaming được, và bắt viết lại phần trích F0 ngay bây giờ. Trả giá kỹ thuật thật để
  đổi lấy một quyền — quyền thương mại hoá — mà dự án không dùng tới.
- **Bỏ `parselmouth`, tự viết ước lượng F0 bằng numpy và scipy.** Vẫn là phương án dự phòng tốt và
  không thêm phụ thuộc nào, nhưng phải tự kiểm chứng độ chính xác trên giọng có thanh điệu. Để
  dành cho lúc muốn công khai repo.
- **Coi ND là chặn tuyệt đối, không chạy cả bản nguyên gốc.** Đọc sai điều khoản: ND cấm phát hành
  bản phái sinh, không cấm chạy.
