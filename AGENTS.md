# AGENTS.md

Bạn (Codex) đang code cho: web app hỗ trợ chuyên viên Direct Sale xử lý hồ sơ
vay từ lương bằng OCR + LLM. Flow: Upload → OCR → LLM extract → mapping bbox →
Review UI → sửa → Upload (lưu 1 lần).

**Tech stack:** Frontend Vite + React + TypeScript + PDF.js (Vitest). Backend Python + FastAPI
+ Pydantic. Persistence SQLite + SQLAlchemy 2.x. OCR = PaddleOCR (detect) + VietOCR
(recognize), chạy local. LLM = Google Gemini API (free tier).

**Kiến trúc:** Modular Monolith, theo Ports & Adapters. `domain/` chứa business
logic, không import trực tiếp SDK OCR/LLM/DB — chỉ gọi qua `domain/ports/`.
Code cụ thể gọi PaddleOCR/VietOCR/Gemini/SQLAlchemy/SQLite nằm ở `infra/`. Router ở `api/`
không chứa business logic.

**Luôn làm:**
- Đọc `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, và task cụ thể trong `docs/FEATURE_BACKLOG.md`
  trước khi code.
- Viết test cho mọi service/logic mới.
- Chạy lint + test + typecheck trước khi báo hoàn thành task.
- Chỉ sửa code liên quan trực tiếp tới task đang làm.

**Không bao giờ làm:**
- Không viết business logic trong router (`api/`).
- Không để `domain/` import trực tiếp thư viện/SDK bên ngoài.
- Không thêm dependency mới nếu chưa thật sự cần và chưa được xác nhận.
- Không tự đổi kiến trúc, data model, hay provider đã chốt.
- Không refactor code không liên quan tới task.

**Khi gặp mâu thuẫn** giữa yêu cầu task và tài liệu đã approved (`docs/ARCHITECTURE.md`
/ `docs/DATA_MODEL.md`) — DỪNG LẠI, nêu rõ mâu thuẫn, KHÔNG tự chọn cách hiểu và code
đại.

Chi tiết đầy đủ xem `docs/DEVELOPMENT_RULES.md`.

---

- Last updated: <để tôi tự điền ngày>
- Downstream docs cần rà lại nếu file này đổi: `docs/ROADMAP.md`, `docs/FEATURE_BACKLOG.md`
