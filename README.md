# Smart Sotek IDP

Ứng dụng web hỗ trợ chuyên viên Direct Sale xử lý hồ sơ vay theo lương. Hệ
thống tự động đọc tài liệu bằng OCR, trích xuất dữ liệu có cấu trúc bằng
Gemini, liên kết mỗi giá trị với vùng bằng chứng trên tài liệu và cho phép
chuyên viên kiểm tra, sửa trước khi lưu hồ sơ.

## Luồng nghiệp vụ

1. Tạo hồ sơ và tải lên đủ bốn loại giấy tờ.
2. PaddleOCR phát hiện vùng chữ; VietOCR nhận dạng tiếng Việt.
3. Template OMR cục bộ nhận diện checkbox trên giấy đề nghị vay.
4. Gemini trích xuất các trường nghiệp vụ từ kết quả OCR.
5. Backend ánh xạ `source_id` về đúng tài liệu, trang và bounding box.
6. Chuyên viên đối chiếu vùng highlight, sửa dữ liệu nếu cần và lưu hồ sơ.

Bốn tài liệu bắt buộc gồm CCCD mặt trước, CCCD mặt sau, giấy đề nghị vay vốn
theo lương và hợp đồng lao động.

## Kiến trúc

Repository sử dụng Modular Monolith theo Ports & Adapters:

```text
frontend/                 Vite + React + TypeScript + PDF.js
backend/app/api/          FastAPI routers
backend/app/domain/       Models, ports và business services
backend/app/infra/        OCR, Gemini và SQLite adapters
backend/tests/            Backend automated tests
docs/                     Tài liệu kiến trúc và source of truth
```

`domain/` không phụ thuộc trực tiếp vào SDK OCR, Gemini hoặc SQLAlchemy. Các
provider cụ thể chỉ được khởi tạo trong `infra/` và nối với domain tại
`backend/app/main.py`.

## Công nghệ chính

- Frontend: Vite, React, TypeScript, PDF.js, Vitest.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2.x, SQLite.
- OCR local: PaddleOCR detection, VietOCR recognition, OpenCV template OMR.
- LLM: Google Gemini API với structured output.

## Thiết lập backend

Hướng dẫn cài OCR trên Windows, cấu trúc model weights và cấu hình CPU/GPU nằm
tại [backend/README.md](backend/README.md).

Các biến môi trường runtime:

```text
GEMINI_API_KEY=<Google AI Studio API key>
OCR_MODEL_PATH=<absolute path tới thư mục model_weights>
OCR_RECOGNITION_DEVICE=auto
```

Không commit API key hoặc dữ liệu hồ sơ vào Git. Sau khi đã cài dependency và
đặt biến môi trường, khởi động backend từ thư mục `backend/`:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend tạo database phát triển tại `backend/smart_sotek.db` và lưu tài liệu
tải lên trong `backend/uploads/`. Cả hai đều là dữ liệu local và đã được loại
khỏi Git.

## Thiết lập frontend

```powershell
cd frontend
npm ci
npm run dev
```

Mặc định frontend gọi `http://127.0.0.1:8000`. Có thể cấu hình một backend
khác tại thời điểm build bằng biến `VITE_API_BASE_URL`.

Frontend production hiện được phát hành tại:

https://smart-sotek-ocr-frontend.vercel.app

Deployment này chỉ phục vụ giao diện cho tới khi có backend công khai phù hợp
với workload OCR local/GPU.

## Kiểm tra chất lượng

Backend, chạy từ `backend/`:

```powershell
ruff check .
python -m pytest
mypy .
```

Frontend, chạy từ `frontend/`:

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
```

## Phạm vi MVP

MVP xử lý một hồ sơ đơn lẻ từ Upload đến Review và lưu kết quả trong SQLite.
Tích hợp BPM thật, xác thực người dùng, phân quyền, cloud storage, xử lý hàng
đợi quy mô lớn và triển khai OCR cloud nằm ngoài phạm vi hiện tại. Chi tiết
quyết định kỹ thuật và tiêu chí nghiệm thu xem trong [docs/](docs/).
