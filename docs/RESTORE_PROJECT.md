# Khôi phục Smart Sotek IDP từ máy trắng

Tài liệu này là checklist để một người hoặc một Codex session mới dựng lại dự
án sau khi máy local cũ đã bị xóa. Không cần database hay uploads cũ.

## 1. Yêu cầu

- Windows 10/11.
- Git và Git LFS.
- CPython 3.12 x64. Đây là runtime Windows duy nhất đã được dự án xác nhận.
- Node.js và npm.
- Một Gemini API key mới nếu chạy pipeline thật.

## 2. Clone source và phục hồi model

```powershell
git clone https://github.com/lebaanhminh2/RPA-OCR-LLM-Smart-Sotek.git
cd RPA-OCR-LLM-Smart-Sotek
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\restore_model_assets.ps1
```

Script tải model đã kiểm chứng từ nhánh Git LFS `model-assets` và tạo thư mục
`model_weights/`. Nhánh này tách khỏi `main` nên Vercel không tải 204 MB model
khi build frontend.

## 3. Chạy portfolio demo, không cần backend

```powershell
cd frontend
npm ci
$env:VITE_DEMO_MODE="true"
npm run dev
```

Demo có luồng Upload mô phỏng, bốn PDF mẫu, 40 field, 44 nguồn bằng chứng,
click-to-highlight và chỉnh sửa trong bộ nhớ.

## 4. Cài backend thật

Tạo virtual environment Python 3.12 bên ngoài repository, rồi chạy từ root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\backend\scripts\install_ocr_dependencies.ps1 `
  -PythonExecutable "C:\path\to\venv\Scripts\python.exe" `
  -CpuOnly
```

Bỏ `-CpuOnly` nếu máy có NVIDIA GPU tương thích CUDA 11.8 và muốn dùng runtime
hybrid đã mô tả trong `backend/README.md`.

## 5. Cấu hình phiên chạy

Không commit API key. Trong terminal dùng để chạy backend:

```powershell
$env:GEMINI_API_KEY="<new Google AI Studio key>"
$env:OCR_MODEL_PATH=(Resolve-Path .\model_weights).Path
$env:OCR_RECOGNITION_DEVICE="auto"
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mở terminal thứ hai:

```powershell
cd frontend
npm ci
npm run dev
```

Backend tự tạo `backend/smart_sotek.db` và `backend/uploads/`. Không cần phục hồi
hai thư mục dữ liệu runtime này.

## 6. Quality gates

```powershell
cd backend
ruff check .
python -m pytest
mypy .
```

```powershell
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

## 7. Những gì không thể lưu trong Git

- `GEMINI_API_KEY`: phải tạo/cung cấp lại vì đây là secret.
- Database và hồ sơ upload local: không cần cho clean run và không được đưa lên
  Git vì có thể chứa dữ liệu cá nhân.

Source, lockfiles, script cài dependency, model weights và portfolio demo đều
được lưu trên GitHub.
