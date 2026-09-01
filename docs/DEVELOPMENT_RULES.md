# DEVELOPMENT_RULES.md

> Dựa trên ARCHITECTURE.md + DATA_MODEL.md (đã approved). Đây là bản đầy đủ, chi
> tiết — dành cho bất kỳ ai (người hoặc Codex) viết code cho dự án này. Bản tóm
> tắt ngắn cho coding agent nằm ở `AGENTS.md`.

## 1. Không business logic trong route (API layer)

Router trong `api/` (ví dụ `cases.py`, `documents.py`, `review.py`) chỉ được
làm 3 việc: nhận request → gọi đúng service ở `domain/services/` → trả response.

- **Không** viết if/else nghiệp vụ, không tính toán, không gọi trực tiếp
  `infra/` (PaddleOCR/VietOCR/Gemini/SQLAlchemy/SQLite) từ trong router.
- Nếu thấy route đang làm nhiều hơn "nhận → gọi service → trả" — đó là dấu hiệu
  logic đang bị đặt sai chỗ, phải chuyển vào `domain/services/`.

## 2. Module single responsibility

Mỗi module (file/class) chỉ nên có **một lý do để thay đổi**.

- `case_service.py` chỉ lo vòng đời Case (tạo, đổi status).
- `extraction_service.py` chỉ lo điều phối OCR → LLM → mapping source_id/bbox.
- `review_service.py` chỉ lo đọc dữ liệu cho Review UI, ghi nhận sửa field, xử
  lý hành động Upload.

Nếu một service bắt đầu làm việc của service khác (ví dụ `review_service.py`
tự gọi OCR) — dừng lại, đây là dấu hiệu vi phạm ranh giới đã định trong
ARCHITECTURE.md.

## 3. Không giant file, không "utils.py nhét mọi thứ"

- Không có file nào (ngoại trừ file cấu hình) vượt quá vài trăm dòng một cách
  vô lý — nếu 1 file đang phình to, tách theo trách nhiệm, không tách bừa theo
  kiểu "phần 1, phần 2".
- **Cấm tuyệt đối** kiểu file `utils.py` hay `helpers.py` dùng chung, chứa đủ
  loại hàm không liên quan tới nhau. Hàm dùng chung phải nằm đúng module nó
  phục vụ (ví dụ hàm chuẩn hoá bbox thuộc về OCR module, không phải "utils"
  chung chung).

## 4. Type Safety

- **Backend:** mọi input/output ở API layer phải có Pydantic schema rõ ràng
  (khớp với entity ở DATA_MODEL.md). Không dùng `dict` hay `Any` để "cho nhanh".
  Domain model (`domain/models.py`) cũng nên dùng dataclass/Pydantic có type
  rõ ràng, không dùng dict lỏng lẻo để truyền dữ liệu giữa các service.
- **Frontend:** TypeScript ở chế độ strict, có type khớp với schema backend
  (đặt trong `frontend/src/types/`). Không dùng `any` trừ khi thực sự bất khả
  kháng (và phải có comment giải thích lý do).

## 5. Provider tách khỏi domain

Đây là nguyên tắc cốt lõi đã thiết kế trong ARCHITECTURE.md (Ports & Adapters):

- `domain/` **không được import** trực tiếp: `paddleocr`, `vietocr`, SDK của
  Google Gemini, hay bất kỳ thư viện DB cụ thể nào.
- `domain/` chỉ được biết tới các interface trong `domain/ports/`
  (`OCRProvider`, `LLMProvider`, `Repository`).
- Chỉ có code trong `infra/` được phép import các thư viện/SDK bên ngoài đó.
- Vi phạm rule này (dù chỉ 1 dòng import) coi như phá vỡ kiến trúc đã approved
  — không tự sửa, phải dừng lại và báo lại.

## 6. Không thêm dependency tuỳ tiện

- Trước khi thêm bất kỳ package mới nào (Python hay npm), phải trả lời được:
  package này giải quyết vấn đề gì mà tech stack hiện có (đã chốt ở
  ARCHITECTURE.md) không giải quyết được?
- Không thêm thư viện chỉ vì "quen dùng" hoặc "tiện". Ưu tiên dùng thư viện đã
  có trong stack: FastAPI/Pydantic, Vite/React/TypeScript/PDF.js, PaddleOCR/VietOCR,
  Google Gemini SDK và SQLAlchemy 2.x cho persistence.
- Nếu thực sự cần thêm dependency mới — nêu rõ lý do và xin xác nhận trước khi
  thêm, không tự ý thêm rồi báo sau.

## 7. Không refactor code không liên quan

- Mỗi task chỉ động vào phần code liên quan trực tiếp tới task đó.
- Thấy code cũ "xấu" hoặc có thể cải thiện nhưng không liên quan tới task đang
  làm → ghi chú lại (ví dụ thêm vào FEATURE_BACKLOG.md như 1 task riêng), không
  tiện tay sửa luôn trong lúc làm việc khác. Việc này giúp mỗi lần thay đổi code
  dễ review, dễ biết "task này sửa gì, vì sao".

## 8. Feature mới phải có test

- Mọi service mới ở `domain/services/` cần có unit test tương ứng (không phụ
  thuộc OCR/LLM thật — dùng fake/mock implement `OCRProvider`/`LLMProvider` để
  test logic điều phối của `extraction_service.py`).
- Adapter ở `infra/` (gọi PaddleOCR/VietOCR/Gemini) nên có ít nhất 1 test dùng
  dữ liệu mẫu cố định (fixture) để phát hiện khi thư viện/API bên ngoài đổi
  hành vi — không bắt buộc gọi Gemini thật trong test tự động (tốn quota free
  tier), có thể mock ở mức adapter.
- API layer nên có test gọi thử endpoint (dùng FastAPI TestClient) cho ít nhất
  luồng chính (happy path) của mỗi route.

## 9. Giữ API compatibility

- Khi sửa 1 endpoint đã có người dùng (frontend đang gọi), không đổi shape của
  response hoặc field bắt buộc của request theo kiểu breaking change nếu không
  thực sự cần thiết.
- Nếu bắt buộc phải đổi (ví dụ đổi cấu trúc ExtractedField trả về), phải cập
  nhật đồng thời phần frontend đang dùng field đó trong cùng 1 task — không để
  backend và frontend lệch nhau.

## 10. Đọc docs trước khi code

Trước khi bắt đầu 1 task, đọc lại:

- ARCHITECTURE.md — để biết task này thuộc module nào, ranh giới ra sao.
- DATA_MODEL.md — để biết field, kiểu dữ liệu, quan hệ liên quan tới task.
- FEATURE_BACKLOG.md (khi có) — để lấy đúng yêu cầu/acceptance criteria của
  task, không tự đoán.

## 11. Chạy lint/test/typecheck sau mỗi task

Trước khi báo 1 task hoàn thành, phải chạy và đảm bảo pass:

- Backend: linter (ví dụ `ruff`/`flake8`), test (`pytest`), type check
  (`mypy` hoặc dùng chế độ strict của Pydantic).
- Frontend: linter (`eslint`), type check (`tsc --noEmit`), tests (`vitest run`).

Không báo "xong" khi các bước trên còn lỗi, kể cả khi tính năng "chạy được" trên
máy lúc demo nhanh.

## 12. Không tự đổi architecture đã approved

- Không tự ý đổi: kiến trúc Modular Monolith, ranh giới module, OCR/LLM
  provider đã chọn (PaddleOCR+VietOCR / Google Gemini), cấu trúc bảng trong
  DATA_MODEL.md.
- Nếu trong lúc code phát hiện kiến trúc/data model hiện tại **thực sự không
  khả thi** (ví dụ PaddleOCR không cài được, Gemini free tier không đáp ứng
  được) — **DỪNG LẠI, KHÔNG TỰ SỬA**, nêu rõ vấn đề và chờ xác nhận hướng xử lý.

## 13. Khi requirement mâu thuẫn — DỪNG và báo lại

Nếu 1 yêu cầu mới (từ `docs/ROADMAP.md` hoặc `docs/FEATURE_BACKLOG.md`) mâu thuẫn với
`docs/ARCHITECTURE.md`/`docs/DATA_MODEL.md` đã approved, hoặc mâu thuẫn với chính nó — không
tự chọn cách hiểu và code đại. Dừng lại, nêu rõ mâu thuẫn là gì, đề xuất hướng
xử lý, chờ xác nhận.

## 14. Quy tắc riêng cho OCR/LLM adapter (bổ sung theo tech stack đã chốt)

- **PaddleOCR/VietOCR:** model weights load 1 lần khi khởi động app (không load
  lại mỗi request — rất tốn thời gian). API key/đường dẫn model không hard-code
  trong source code, đọc từ biến môi trường/file cấu hình.
- **Gemini API:** vì dùng free tier có giới hạn request/phút, adapter gọi
  Gemini phải có retry/backoff đơn giản khi gặp lỗi rate-limit (429), và không
  được gọi lặp vô hạn — giới hạn số lần retry rõ ràng.
- **Secrets:** API key của Gemini không commit vào git (dùng file `.env`, thêm
  vào `.gitignore`).

## 15. Tooling/persistence đã chốt cho MVP

- Frontend scaffold/build: **Vite + React + TypeScript**.
- Frontend test runner: **Vitest**.
- Persistence: **SQLite + SQLAlchemy 2.x**. Không dùng `sqlite3` thuần song song với SQLAlchemy.
- Backend quality checks: **Ruff + Pytest + mypy**.
- Nếu một task thật sự cần thay một lựa chọn trên, dừng và báo; không tự đổi giữa chừng.

---

- Last updated: <để tôi tự điền ngày>
- Downstream docs cần rà lại nếu file này đổi: AGENTS.md, ROADMAP.md,
  FEATURE_BACKLOG.md
