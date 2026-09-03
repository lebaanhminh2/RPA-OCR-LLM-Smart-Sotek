# Smart Sotek IDP Frontend

Frontend cho luồng Upload → OCR/LLM processing → Review → lưu hồ sơ của Smart
Sotek IDP. Ứng dụng được xây dựng bằng Vite, React, TypeScript và PDF.js.

## Chức năng

- Tạo hồ sơ và tải lên bốn loại tài liệu bắt buộc.
- Theo dõi trạng thái xử lý nền và hiển thị lỗi rõ ràng.
- Hiển thị danh sách trường dữ liệu do OCR/LLM trích xuất.
- Mở đúng tài liệu, trang và vùng bằng chứng khi chọn một trường.
- Cho phép chuyên viên sửa giá trị và lưu hồ sơ sau khi kiểm tra.

## Phát triển local

```powershell
npm ci
npm run dev
```

## Portfolio demo không cần backend

```powershell
$env:VITE_DEMO_MODE="true"
npm run dev
```

Demo mô phỏng Upload và processing, rồi mở hồ sơ review tĩnh có đầy đủ PDF và
bbox. Field sửa được trong bộ nhớ và được khôi phục khi refresh.

Frontend mặc định kết nối tới `http://127.0.0.1:8000`. Để dùng backend khác,
đặt biến môi trường trước khi chạy hoặc build:

```powershell
$env:VITE_API_BASE_URL="https://api.example.com"
npm run dev
```

## Kiểm tra

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
```

## Cấu trúc

```text
src/api/          REST API client
src/components/   Viewer, field list và field editor
src/pages/        Upload và Review workflows
src/types/        Kiểu dữ liệu dùng chung với backend API
```

Production frontend: https://smart-sotek-ocr-frontend.vercel.app

Production URL hiện chạy portfolio demo tĩnh nên không cần backend. Chế độ local
thật vẫn mặc định gọi `http://127.0.0.1:8000`; có thể dùng
`VITE_API_BASE_URL` để trỏ tới backend công khai. Xem
[README của repository](../README.md) để biết kiến trúc và hướng dẫn backend.
