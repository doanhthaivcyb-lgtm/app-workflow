# Weavy Clone v1 — App desktop giống Figma Weave / Weavy (BẢN MOCK)

App desktop Windows, giao diện tiếng Việt, CustomTkinter, dark theme.
Canvas node kéo-thả, nối dây, chạy workflow tạo ảnh/video.

## ⚠ Đọc trước: bản này là MOCK, model thật là Pax

- **Model chạy trên app chính là Pax (Muse).** Pax sống trên cloud của Muse,
  **không phải file model cài vào máy Windows**, nên không thể nhúng Pax
  vào file `.exe` / `.py` để chạy offline.
- Bản v1 này dùng **engine MOCK chạy giả lập tại chỗ**:
  - `Tạo ảnh` → tạo ảnh **PNG thật** bằng PIL (gradient theo prompt + ghi prompt lên ảnh),
    lưu vào thư mục `outputs/`.
  - `Tạo video` → tạo **file mô tả `.txt` + thumbnail PNG**, chưa phải video thật.
  - `Xóa nền / Upscale / Ghép lớp` → xử lý thật trên file PNG mock đó bằng PIL.
- **Chạy thật bằng Pax:** trong app bấm `Lưu workflow` để xuất file JSON,
  gửi file JSON đó cho Pax trong chat Muse, Pax sẽ chạy từng node bằng
  khả năng tạo ảnh/video thật của Pax và trả kết quả về. Giới hạn của Pax:
  tối đa **4 ảnh / lần yêu cầu**, tối đa **6 clip video ~10 giây / lần yêu cầu**,
  nên workflow lớn phải chia nhiều lần chạy.

## Tính năng v1

- Canvas node kéo-thả được (kéo tiêu đề node để di chuyển).
- Nối dây: bấm nút **`Ra ●`** của node trước, rồi bấm **`● Vào`** của node sau.
  Dây sai (tự nối chính mình, tạo vòng lặp, trùng dây) sẽ bị chặn và báo lỗi.
- Các loại node: **Prompt, Tạo ảnh, Tạo video, Xóa nền, Upscale, Ghép lớp**.
  Mỗi node có tiêu đề, ô nhập prompt, cổng vào/ra, trạng thái
  (`Chưa chạy / Đang chạy / Xong / Lỗi`).
- **▶ Chạy tổng** (nút lớn ở thanh trên cùng): chạy toàn bộ workflow theo
  **thứ tự topo** dựa trên dây nối.
  - **Lựa chọn đã chốt: DỪNG NGAY khi một node lỗi.** App báo rõ node nào lỗi,
    các node sau chưa chạy. Sửa node lỗi rồi bấm `Chạy tổng` lại,
    hoặc bấm `Chạy` riêng từng node sau.
  - Bản v1 chưa có cache bỏ qua node đã xong: bấm `Chạy tổng` lại sẽ chạy lại
    từ đầu tất cả các node.
- **Nút `Chạy` riêng trên mỗi node:** chỉ chạy node đó, không chạy cả workflow.
  Node cần đầu vào (Xóa nền / Upscale / Ghép lớp) mà node trước chưa chạy xong
  thì sẽ báo lỗi rõ, yêu cầu chạy node đầu vào trước hoặc dùng `Chạy tổng`.
- Thêm node (chọn loại ở menu), xóa node (nút `✕` trên node), lưu/tải workflow JSON,
  workflow mẫu, xóa canvas, panel nhật ký chạy ở dưới.

## Cách chạy trên Windows

```bat
py -3.13 -m pip install -r requirements.txt
py weavy_app.py
```

Yêu cầu: Windows, Python 3.13, đã cài CustomTkinter + Pillow (trong `requirements.txt`).
File output nằm trong thư mục `outputs/` cạnh file `weavy_app.py`.

Thử nhanh sau khi mở app:
1. Bấm `Workflow mẫu` (mặc định đã tải sẵn: Prompt → Tạo ảnh → Upscale).
2. Bấm **`▶ Chạy tổng`** → xem nhật ký chạy ở panel dưới.
3. Kiểm tra thư mục `outputs/` có file `*_anh.png` và `*_upscale.png`.
4. Thử bấm nút `Chạy` riêng trên node `Tạo ảnh` để chạy chỉ node đó.

## Cấu trúc file

| File | Mô tả |
|---|---|
| `weavy_app.py` | App chính (GUI CustomTkinter). Chạy file này. |
| `workflow.py` | Logic thuần, không có GUI: node, dây nối, topo sort, engine mock, lưu/tải JSON. |
| `test_workflow.py` | Test logic: `python test_workflow.py` |
| `requirements.txt` | `customtkinter`, `pillow` |
| `README.md` | File này |
| `sample_workflow.json` | Workflow mẫu: Prompt → Tạo ảnh → Upscale |
| `outputs/` | File ảnh/video mock được tạo ra khi chạy |

## Kết quả test (Linux, 2026-11-18)

- `python -m py_compile` cho mọi file `.py`: **pass**.
- `python test_workflow.py`: **18 PASS, 0 FAIL** (topo sort, chạy tổng, chạy riêng,
  dừng khi lỗi, video mock, lưu/tải JSON, ghép lớp).
- `import weavy_app` headless (không mở GUI): **pass** (chỉ import module, chưa tạo cửa sổ).
- Chạy thử workflow mẫu bằng engine mock: **pass**, đã tạo file PNG trong `outputs/`.

## Chưa test / chưa làm

- **Chưa test mở GUI thật trên Windows** (máy test là Linux, không có display Windows).
  Cần Thái mở app trên Windows thật và báo lại nếu nút kéo-thả / nối dây / chạy lỗi.
- Chưa có file `.exe` đóng gói (cần PyInstaller, chưa làm ở v1).
- Chưa nối API thật nào (Veo/Kling/Flux/OpenAI/Gemini) — theo thiết kế đã chốt,
  model thật là Pax, không nối model hãng khác ở v1.
- Chưa có cache bỏ qua node đã xong khi chạy tổng lại, chưa có hoàn tác (undo),
  chưa lưu vị trí dây nối theo từng cổng riêng (mỗi node hiện có 1 cổng vào / 1 cổng ra).

## Đẩy lên GitHub — ĐÃ SẴN SÀNG ĐẨY (chưa đẩy)

- **Repo đích: https://github.com/doanhthaivcyb-lgtm/app-workflow , nhánh `main`.**
  KHÔNG phải repo `Test` nữa.
- Đã kiểm tra ngày 2026-11-18: repo `app-workflow` đã tồn tại, nhánh `main`,
  hiện chỉ có 1 file `README.md` với nội dung `# app-workflow`.
  Đẩy bản này lên sẽ thêm toàn bộ file dưới đây và **ghi đè README.md đó**
  bằng README của app (nội dung repo README hiện tại không có gì khác để giữ).
- Code trong `~/workspace/weavy_app/` đã sẵn sàng để đẩy, **chưa tự đẩy**
  (chờ bước đẩy do main agent xử lý sau khi Thái xác nhận).
- Lệnh đẩy tham khảo (chạy từ máy có quyền git đã xác thực):
  ```bash
  git clone https://github.com/doanhthaivcyb-lgtm/app-workflow
  cd app-workflow
  cp -r ~/workspace/weavy_app/* .
  git add .
  git commit -m "Weavy Clone v1 (mock): node canvas, Chay tong + Chay rieng tung node"
  git push origin main
  ```
  Lưu ý: thư mục `outputs/` và `__pycache__/` đã có trong `.gitignore`
  nên không bị đẩy lên (file PNG mock sẽ tự tạo lại khi chạy app).

## Cần Thái quyết trước khi đẩy lên GitHub

1. Đã đúng ý về nút `Chạy tổng` dừng ngay khi lỗi chưa, hay muốn đổi sang
   "bỏ qua node lỗi và chạy tiếp các node còn lại"?
2. Đồng ý đẩy bản v1 này lên repo `doanhthaivcyb-lgtm/app-workflow` nhánh `main`
   (ghi đè README `# app-workflow` hiện tại) không?
3. Khi chuyển sang chạy thật bằng Pax: workflow gửi cho Pax qua chat Muse
   (file JSON) có chấp nhận được không, hay muốn app tự gửi thẳng cho Pax?
