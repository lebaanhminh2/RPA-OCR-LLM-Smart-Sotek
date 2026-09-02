# FEATURE_BACKLOG.md

> Dựa trên ROADMAP.md + phần liên quan của ARCHITECTURE.md/DATA_MODEL.md/
> DEVELOPMENT_RULES.md (đã approved). Mỗi task nhỏ, độc lập, có thể dán thẳng
> prompt cho Codex mà không cần giải thích thêm. Không viết code ứng dụng ở
> file này — chỉ mô tả yêu cầu.
>
> **Quy ước ID:** `M{số milestone}-T{số thứ tự}`, khớp với milestone tương ứng
> ở ROADMAP.md.
>
> **Cách dùng "Ready-to-paste Codex prompt":** copy nguyên đoạn trong khối
> code, dán trực tiếp cho Codex, không cần sửa (trừ khi bạn muốn thêm chi tiết
> riêng). Mỗi prompt đã tự nhắc Codex đọc AGENTS.md/ARCHITECTURE.md/
> DATA_MODEL.md trước khi code, đúng DEVELOPMENT_RULES.md §10.

---

## M0 — Skeleton + Tooling

### M0-T1 — Backend skeleton (FastAPI app + folder structure)

**Goal:** Có backend chạy được, đúng folder structure ARCHITECTURE.md §5, chưa
có logic nghiệp vụ.

**Files/modules:** `backend/app/main.py`, `backend/app/api/`,
`backend/app/domain/`, `backend/app/infra/`, `backend/tests/`.

**Requirements:**
- Tạo đúng cây thư mục ở ARCHITECTURE.md §5 (kể cả thư mục rỗng có `.gitkeep`
  nếu cần).
- FastAPI app khởi tạo ở `main.py`, có 1 endpoint `GET /health` trả
  `{"status": "ok"}`.

**Acceptance criteria:**
- [ ] `uvicorn app.main:app` chạy được, `/health` trả 200.
- [ ] Cây thư mục khớp đúng ARCHITECTURE.md §5.

**Tests required:** Test `/health` bằng FastAPI TestClient (happy path).

**Do not do:** Không thêm route/service nghiệp vụ nào; không cài OCR/LLM SDK.

**Dependencies:** Không có.

**Ready-to-paste Codex prompt:**
```
Đọc AGENTS.md và ARCHITECTURE.md (mục 5 - Folder Structure) trước khi làm.
Tạo skeleton backend FastAPI theo đúng cây thư mục ở ARCHITECTURE.md mục 5:
app/api/, app/domain/models.py, app/domain/services/, app/domain/ports/,
app/infra/ocr/, app/infra/llm/, app/infra/db/, app/main.py, và thư mục tests/.
main.py chỉ cần khởi tạo FastAPI app và 1 endpoint GET /health trả về
{"status": "ok"}. Chưa viết bất kỳ logic nghiệp vụ nào (case, document, OCR,
LLM) - milestone này chỉ là skeleton. Viết 1 test cho /health dùng FastAPI
TestClient. Chạy lint/test/typecheck (theo DEVELOPMENT_RULES.md mục 11) và
báo kết quả.
```

---

### M0-T2 — Backend tooling (lint/test/typecheck)

**Goal:** Có sẵn công cụ kiểm tra chất lượng code cho mọi task backend sau
này, đúng DEVELOPMENT_RULES.md §11.

**Files/modules:** cấu hình `ruff`/`flake8`, `pytest`, `mypy` (hoặc Pydantic
strict) ở root `backend/`.

**Requirements:**
- Cấu hình linter, test runner, type checker chạy được bằng 1 lệnh mỗi loại.
- Thêm script/README ngắn ghi rõ 3 lệnh này là gì.

**Acceptance criteria:**
- [ ] `ruff check .` (hoặc tương đương) chạy pass trên codebase hiện tại.
- [ ] `pytest` chạy pass (kể cả khi chỉ có 1 test từ M0-T1).
- [ ] `mypy .` (hoặc type check tương đương) chạy pass.

**Tests required:** Không có test mới — task này là cấu hình tooling.

**Do not do:** Không tắt rule linter/type checker chỉ để "cho pass nhanh".

**Dependencies:** M0-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 11 trước khi làm. Cấu hình tooling cho backend
Python: ruff (hoặc flake8) cho lint, pytest cho test, mypy cho type check
(hoặc bật chế độ strict của Pydantic nếu phù hợp hơn). Đảm bảo cả 3 lệnh chạy
được và pass trên codebase hiện tại (chỉ có main.py + test /health từ task
trước). Không tắt rule nào chỉ để pass nhanh - nếu có lỗi thật, sửa code, không
sửa cấu hình để né lỗi. Ghi lại 3 lệnh này vào README ngắn.
```

---

### M0-T3 — Frontend skeleton (Vite + React + TypeScript + PDF.js)

**Goal:** Có frontend chạy được, đúng folder structure ARCHITECTURE.md §5,
cài sẵn PDF.js (chưa dùng logic).

**Files/modules:** `frontend/src/pages/`, `frontend/src/components/`,
`frontend/src/api/`, `frontend/src/types/`.

**Requirements:**
- Vite + React + TypeScript project, cài dependency PDF.js.
- 1 trang mặc định hiển thị chữ "Hello" hoặc tương tự, chưa có logic nghiệp
  vụ.

**Acceptance criteria:**
- [ ] `npm run dev` (hoặc tương đương) chạy được, mở trình duyệt thấy trang.
- [ ] Cây thư mục khớp ARCHITECTURE.md §5.

**Tests required:** Không bắt buộc test cho trang rỗng.

**Do not do:** Không viết component nghiệp vụ (Viewer, FieldList...) ở task
này.

**Dependencies:** Không có (chạy song song M0-T1/T2).

**Ready-to-paste Codex prompt:**
```
Đọc AGENTS.md và ARCHITECTURE.md (mục 5 - Folder Structure) trước khi làm.
Tạo skeleton frontend bằng Vite + React + TypeScript (strict mode) theo đúng cây thư mục
ở ARCHITECTURE.md mục 5: src/pages/, src/components/, src/api/, src/types/.
Cài dependency PDF.js nhưng chưa dùng tới (chỉ cài đặt, kiểm tra import
được). Tạo 1 trang mặc định hiển thị "Hello" để xác nhận app chạy được. Chưa
viết component nghiệp vụ nào (Document Viewer, Field List...) - đó là các
milestone sau.
```

---

### M0-T4 — Frontend tooling (eslint/tsc/test runner)

**Goal:** Có sẵn công cụ kiểm tra chất lượng code frontend, đúng
DEVELOPMENT_RULES.md §11.

**Files/modules:** cấu hình `eslint`, `tsconfig.json` (strict), test runner
(Vitest).

**Requirements:**
- ESLint cấu hình cho React + TypeScript.
- `tsconfig.json` bật chế độ `strict`.
- Vitest cài đặt và cấu hình sẵn (chưa cần test nghiệp vụ thật).

**Acceptance criteria:**
- [ ] `eslint .` chạy pass.
- [ ] `tsc --noEmit` chạy pass, `strict: true` trong `tsconfig.json`.
- [ ] `vitest run` chạy được và pass (có thể chỉ là smoke test tối thiểu ở M0).

**Tests required:** Không có test mới bắt buộc.

**Do not do:** Không bật `any` tràn lan để né lỗi type.

**Dependencies:** M0-T3.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 4 và mục 11 trước khi làm. Cấu hình ESLint cho
React + TypeScript, bật strict mode trong tsconfig.json. Cài đặt và cấu hình Vitest làm test runner frontend dù chưa có
test thật. Đảm bảo `eslint .`, `tsc --noEmit` và `vitest run` chạy pass trên codebase hiện
tại (chỉ có trang "Hello" từ task trước).
```

---

### M0-T5 — SQLite connection setup (chưa có schema)

**Goal:** Backend kết nối được SQLite, sẵn sàng cho các task sau tạo bảng.

**Files/modules:** `backend/app/infra/db/` (connection/session setup).

**Requirements:**
- Kết nối SQLite bằng **SQLAlchemy 2.x** theo stack đã chốt; không dùng `sqlite3` thuần song song.
- File DB tạo tự động khi app khởi động (dev environment).

**Acceptance criteria:**
- [ ] App khởi động không lỗi, file SQLite được tạo/kết nối thành công.
- [ ] Có 1 hàm/test đơn giản xác nhận kết nối DB hoạt động (ví dụ query
      `SELECT 1`).

**Tests required:** Test kết nối DB cơ bản.

**Do not do:** Không tạo bảng nghiệp vụ (Case, Document...) ở task này — đó
là việc của M1-T3.

**Dependencies:** M0-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 1 và mục 5 trước khi làm. Thiết lập kết nối SQLite
trong app/infra/db/ bằng SQLAlchemy 2.x + SQLite theo stack đã chốt. Không dùng sqlite3 thuần song song. File DB tự tạo khi app khởi động ở môi trường dev. Chưa
tạo bảng nghiệp vụ nào (Case, Document, OCRBlock...) - đó là task sau. Viết 1
test xác nhận kết nối DB hoạt động được.
```

---

### M0-T6 — Env & secrets scaffolding

**Goal:** Có sẵn cơ chế đọc API key/cấu hình từ biến môi trường, không
hard-code, không commit secrets, đúng DEVELOPMENT_RULES.md §14.

**Files/modules:** `.env.example`, `.gitignore`.

**Requirements:**
- `.env.example` liệt kê các biến sẽ cần (ví dụ `GEMINI_API_KEY`,
  `OCR_MODEL_PATH`) dù chưa dùng tới ở milestone này.
- `.gitignore` loại trừ `.env` thật, file model weights lớn, thư mục
  build/cache.

**Acceptance criteria:**
- [ ] `.env.example` tồn tại, không chứa giá trị thật.
- [ ] `.gitignore` loại trừ đúng `.env`.

**Tests required:** Không cần test.

**Do not do:** Không commit bất kỳ file `.env` thật hay API key thật nào.

**Dependencies:** M0-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 14 (phần Secrets) trước khi làm. Tạo file
.env.example liệt kê các biến môi trường sẽ cần cho dự án (ví dụ
GEMINI_API_KEY, đường dẫn model OCR nếu cần) - chỉ liệt kê tên biến, không
điền giá trị thật. Cập nhật .gitignore để loại trừ file .env thật, thư mục
build/cache, và bất kỳ file model weights lớn nào nếu có. Không tạo hay commit
file .env thật.
```

---

## M1 — Case + Upload

### M1-T1 — Domain models: Case, Document + enums

**Goal:** Định nghĩa model nội bộ cho `Case` và `Document`, đúng field/enum ở
DATA_MODEL.md §4.1, §4.2.

**Files/modules:** `backend/app/domain/models.py`.

**Requirements:**
- Dùng dataclass hoặc Pydantic model có type rõ ràng (DEVELOPMENT_RULES.md
  §4) — không dùng dict lỏng lẻo.
- Enum `CaseStatus` (`UPLOADING`, `PROCESSING`, `READY_FOR_REVIEW`,
  `COMPLETED`, `FAILED`), enum `DocumentType` (`CCCD_FRONT`, `CCCD_BACK`,
  `LOAN_APPLICATION`, `LABOR_CONTRACT`), enum `DocumentOcrStatus` (`PENDING`,
  `DONE`, `FAILED`).
- Field đúng bảng DATA_MODEL.md §4.1 (Case) và §4.2 (Document).

**Acceptance criteria:**
- [ ] Model `Case`, `Document` có đủ field bắt buộc, đúng type.
- [ ] Enum khớp đúng danh sách giá trị ở DATA_MODEL.md.

**Tests required:** Unit test đơn giản khởi tạo model với dữ liệu hợp lệ, xác
nhận type/field đúng.

**Do not do:** Không thêm field ngoài DATA_MODEL.md; không tự đổi enum.

**Dependencies:** M0-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 4.1 và 4.2, và DEVELOPMENT_RULES.md mục 4 trước khi
làm. Định nghĩa trong app/domain/models.py: enum CaseStatus (UPLOADING,
PROCESSING, READY_FOR_REVIEW, COMPLETED, FAILED), enum DocumentType
(CCCD_FRONT, CCCD_BACK, LOAN_APPLICATION, LABOR_CONTRACT), enum
DocumentOcrStatus (PENDING, DONE, FAILED), và model Case, Document đúng field
ở DATA_MODEL.md mục 4.1/4.2 (dùng dataclass hoặc Pydantic, có type rõ ràng,
không dùng dict). Không thêm field nào ngoài bảng đã liệt kê. Viết test khởi
tạo model với dữ liệu hợp lệ.
```

---

### M1-T2 — Repository port interface (Case, Document)

**Goal:** Định nghĩa interface `Repository` cho Case/Document ở tầng
`domain/ports/`, chưa có implementation cụ thể.

**Files/modules:** `backend/app/domain/ports/repository.py`.

**Requirements:**
- Interface trừu tượng (Protocol/ABC) định nghĩa các thao tác cần cho Case
  (tạo, lấy theo id, cập nhật status) và Document (tạo, lấy theo case_id,
  kiểm tra `unique(case_id, document_type)`).
- Không import bất kỳ thư viện DB cụ thể nào (đúng DEVELOPMENT_RULES.md §5).

**Acceptance criteria:**
- [ ] Interface đủ method cho các thao tác cần ở M1-T3/T4.
- [ ] File này không import SQLAlchemy/sqlite3/thư viện DB nào.

**Tests required:** Không cần test riêng (interface không có logic).

**Do not do:** Không viết implementation trong file này.

**Dependencies:** M1-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 3-4 và DEVELOPMENT_RULES.md mục 5 trước khi làm.
Trong app/domain/ports/repository.py, định nghĩa interface trừu tượng (dùng
Protocol hoặc ABC) cho các thao tác cần với Case và Document: tạo case, lấy
case theo id, cập nhật case.status; tạo document, lấy danh sách document theo
case_id, kiểm tra document_type đã tồn tại trong case chưa (unique
constraint). File này tuyệt đối không được import SQLAlchemy, sqlite3, hay
bất kỳ thư viện DB cụ thể nào - chỉ định nghĩa "hợp đồng", không có logic cụ
thể.
```

---

### M1-T3 — SQLite repository implementation: Case, Document

**Goal:** Implement interface ở M1-T2 bằng SQLite thật.

**Files/modules:** `backend/app/infra/db/sqlite_repository.py`,
`backend/app/infra/db/orm_models.py`.

**Requirements:**
- Tạo bảng `Case`, `Document` đúng field DATA_MODEL.md §4.1/§4.2, ràng buộc
  `unique(case_id, document_type)`.
- Implement đầy đủ method của interface ở M1-T2.

**Acceptance criteria:**
- [ ] Tạo/đọc/cập nhật Case, Document hoạt động đúng qua SQLite thật.
- [ ] Vi phạm `unique(case_id, document_type)` bị chặn ở tầng DB hoặc
      repository.

**Tests required:** Test repository dùng SQLite thật (in-memory hoặc file
tạm) — test tạo, đọc, cập nhật, và test vi phạm unique constraint.

**Do not do:** Không đặt business logic (ví dụ quyết định khi nào đổi status)
trong repository — đó là việc của `case_service.py` ở M1-T4.

**Dependencies:** M1-T2, M0-T5.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 4.1, 4.2 và DEVELOPMENT_RULES.md mục 5 trước khi làm.
Trong app/infra/db/, implement interface Repository (đã định nghĩa ở
domain/ports/repository.py) bằng SQLite thật: tạo bảng Case và Document đúng
field ở DATA_MODEL.md mục 4.1/4.2, có ràng buộc unique(case_id,
document_type). Repository chỉ làm nhiệm vụ đọc/ghi dữ liệu, không chứa
business logic (ví dụ không tự quyết định khi nào đổi Case.status - đó là
việc của case_service.py). Viết test cho repository dùng SQLite thật (in-
memory hoặc file tạm), bao gồm test vi phạm unique constraint.
```

---

### M1-T4 — case_service.py: tạo case, đổi status khi đủ document

**Goal:** Business logic vòng đời Case — tạo case, tự chuyển `UPLOADING →
PROCESSING` khi đủ 4 loại document.

**Files/modules:** `backend/app/domain/services/case_service.py`.

**Requirements:**
- Service chỉ phụ thuộc interface `Repository` ở `domain/ports/`, không import
  trực tiếp SQLite.
- Logic: tạo case mới (`status = UPLOADING`); sau khi thêm document, kiểm tra
  đã đủ 4 loại document bắt buộc chưa → nếu đủ, chuyển `status = PROCESSING`.

**Acceptance criteria:**
- [ ] Tạo case mới trả về `status = UPLOADING`.
- [ ] Thêm đủ 4 loại document hợp lệ → `status` tự chuyển `PROCESSING`.
- [ ] Thêm document trùng loại hoặc chưa đủ 4 loại → không đổi status, báo
      lỗi/giữ nguyên tương ứng.

**Tests required:** Unit test dùng fake `Repository` (không phụ thuộc SQLite
thật) — theo DEVELOPMENT_RULES.md §8.

**Do not do:** Không gọi OCR/LLM ở service này (đó là `extraction_service.py`
ở M3/M4); không tự thêm business rule ngoài PROJECT_BRIEF/DATA_MODEL.

**Dependencies:** M1-T2.

**Ready-to-paste Codex prompt:**
```
Đọc docs/PROJECT_BRIEF.md mục 6-7, DATA_MODEL.md mục 3, và DEVELOPMENT_RULES.md
mục 2 và mục 8 trước khi làm. Trong app/domain/services/case_service.py, viết
logic: tạo case mới (status = UPLOADING, dùng interface Repository ở
domain/ports/, không import SQLite trực tiếp); khi thêm 1 document vào case,
kiểm tra case đã có đủ 4 loại document bắt buộc chưa (CCCD_FRONT, CCCD_BACK,
LOAN_APPLICATION, LABOR_CONTRACT) - nếu đủ thì chuyển case.status sang
PROCESSING. Service này chỉ lo vòng đời Case, không gọi OCR/LLM. Viết unit
test dùng fake Repository (implement interface bằng in-memory dict, không
dùng SQLite thật) cho các case: tạo case, đủ 4 document, thiếu document,
document trùng loại.
```

---

### M1-T5 — api/cases.py: POST /cases

**Goal:** Endpoint tạo case mới, router mỏng đúng DEVELOPMENT_RULES.md §1.

**Files/modules:** `backend/app/api/cases.py`.

**Requirements:**
- `POST /cases` gọi `case_service.py`, trả `Case` (Pydantic schema).
- Router không chứa if/else nghiệp vụ, không gọi trực tiếp `infra/`.

**Acceptance criteria:**
- [ ] Gọi `POST /cases` trả về case mới với `status = UPLOADING`.

**Tests required:** API test happy path bằng FastAPI TestClient.

**Do not do:** Không viết business logic trong router.

**Dependencies:** M1-T4.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 1 trước khi làm. Trong app/api/cases.py, viết
endpoint POST /cases: nhận request, gọi case_service.py để tạo case mới, trả
response là Case (dùng Pydantic schema khớp DATA_MODEL.md mục 4.1). Router
chỉ được làm 3 việc: nhận request -> gọi service -> trả response, không chứa
if/else nghiệp vụ, không gọi trực tiếp infra/. Viết API test happy path bằng
FastAPI TestClient.
```

---

### M1-T6 — api/documents.py: upload document

**Goal:** Endpoint upload 1 document cho case, lưu file vật lý + record DB,
kích hoạt chuyển status khi đủ 4 loại.

**Files/modules:** `backend/app/api/documents.py`,
`backend/app/domain/services/case_service.py` (gọi từ đây).

**Requirements:**
- `POST /cases/{case_id}/documents` nhận file + `document_type`, lưu file lên
  local disk (đường dẫn lưu vào `Document.file_path`), gọi
  `case_service.py` để tạo `Document` record và kiểm tra đủ 4 loại.
- Trả lỗi rõ ràng khi `document_type` đã tồn tại trong case (vi phạm unique)
  hoặc `case_id` không tồn tại.

**Acceptance criteria:**
- [ ] Upload hợp lệ → file lưu trên disk, `Document` record đúng, response
      thành công.
- [ ] Upload trùng `document_type` → lỗi rõ ràng, không tạo record mới.
- [ ] Upload đủ 4 loại → `Case.status` chuyển `PROCESSING` (kiểm tra qua
      response hoặc GET case).

**Tests required:** API test: upload hợp lệ, upload trùng loại, upload đủ 4
loại để xác nhận status đổi.

**Do not do:** Không chạy OCR/LLM ở task này (đó là M3/M4) — chỉ cần lưu file
và record.

**Dependencies:** M1-T5, M1-T4.

**Ready-to-paste Codex prompt:**
```
Đọc docs/PROJECT_BRIEF.md mục 6, DATA_MODEL.md mục 4.2, ARCHITECTURE.md mục 9
(không dùng cloud storage), và DEVELOPMENT_RULES.md mục 1 trước khi làm.
Trong app/api/documents.py, viết endpoint POST /cases/{case_id}/documents:
nhận file upload + document_type, lưu file lên local disk (đường dẫn ghi vào
Document.file_path), gọi case_service.py để tạo Document record và kiểm tra
đủ 4 loại document (nếu đủ, case_service tự chuyển status). Trả lỗi rõ ràng
nếu document_type đã tồn tại trong case (vi phạm unique constraint) hoặc
case_id không tồn tại. Router chỉ nhận request -> gọi service -> trả response,
không chứa logic nghiệp vụ. Chưa gọi OCR/LLM ở task này. Viết API test cho:
upload hợp lệ, upload trùng loại, upload đủ 4 loại (xác nhận case chuyển
PROCESSING).
```

---

### M1-T7 — Frontend: CaseUploadPage.tsx

**Goal:** UI tạo case mới và upload 4 loại giấy tờ, gọi API thật.

**Files/modules:** `frontend/src/pages/CaseUploadPage.tsx`,
`frontend/src/api/`, `frontend/src/types/`.

**Requirements:**
- Form tạo case (nút "Tạo hồ sơ mới").
- 4 ô upload tương ứng 4 loại document, gọi API thật ở M1-T5/T6 (không mock).
- Type TypeScript khớp schema backend (`frontend/src/types/`).

**Acceptance criteria:**
- [ ] Tạo case mới qua UI thành công.
- [ ] Upload đủ 4 file qua UI, thấy phản hồi thành công/thất bại rõ ràng.

**Tests required:** Không bắt buộc test tự động ở task này (có thể thêm nếu
Codex thấy hợp lý); tối thiểu kiểm tra thủ công theo Acceptance criteria.

**Do not do:** Không code sẵn Document Viewer/Review Panel ở task này.

**Dependencies:** M1-T5, M1-T6, M0-T3/T4.

**Ready-to-paste Codex prompt:**
```
Đọc docs/PROJECT_BRIEF.md mục 5, mục 7, và DEVELOPMENT_RULES.md mục 4 (phần
frontend type safety) trước khi làm. Trong frontend/src/pages/
CaseUploadPage.tsx, viết UI: nút tạo case mới (gọi POST /cases thật), và 4 ô
upload file tương ứng 4 loại document (CCCD mặt trước, CCCD mặt sau, giấy đề
nghị vay vốn, hợp đồng lao động), mỗi ô gọi API upload thật (POST
/cases/{case_id}/documents) - không mock dữ liệu. Định nghĩa type TypeScript
trong frontend/src/types/ khớp với schema backend (Case, Document). Hiển thị
rõ trạng thái thành công/lỗi cho mỗi lần upload. Chưa code Document Viewer
hay Review Panel ở task này.
```

---

## M2 — Viewer + Static Highlight

### M2-T1 — Frontend: DocumentViewer (PDF.js render + điều hướng trang)

**Goal:** Component xem tài liệu, render PDF.js, chuyển trang.

**Files/modules:** `frontend/src/components/DocumentViewer/`.

**Requirements:**
- Render 1 file PDF/ảnh qua PDF.js.
- Hỗ trợ điều hướng trang (next/prev hoặc chọn số trang) nếu file nhiều trang.

**Acceptance criteria:**
- [ ] Mở đúng file, xem được nội dung trang.
- [ ] Chuyển trang hoạt động đúng với file nhiều trang.

**Tests required:** Test thủ công (ghi lại kịch bản kiểm tra) — component
render PDF.js khó unit test tự động; nếu Codex có cách test hợp lý thì thêm.

**Do not do:** Không vẽ overlay highlight ở task này (đó là M2-T2).

**Dependencies:** M0-T3, M1-T6 (cần có file thật để test).

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 1 (lý do chọn PDF.js) và mục 3 (Document Viewer)
trước khi làm. Trong frontend/src/components/DocumentViewer/, viết component
render 1 file PDF/ảnh bằng PDF.js, hỗ trợ điều hướng trang (next/prev hoặc
input số trang) khi file có nhiều trang. Chưa vẽ overlay highlight ở task
này - chỉ cần render đúng và chuyển trang đúng. Ghi lại kịch bản test thủ công
đã kiểm tra (mở file, chuyển trang) trong PR/commit message.
```

---

### M2-T2 — Frontend: bbox→pixel overlay utility + highlight hard-code

**Goal:** Chuyển toạ độ chuẩn hoá (0–1) sang pixel thực tế, vẽ overlay
highlight, test với bbox hard-code.

**Files/modules:** `frontend/src/components/DocumentViewer/` (mở rộng), hàm
tiện ích chuyển đổi toạ độ.

**Requirements:**
- Hàm thuần (pure function) chuyển `bbox_x/y/width/height` (0–1) + kích thước
  trang hiện tại → toạ độ pixel để vẽ overlay.
- Vẽ được overlay đúng vị trí với ít nhất 1 giá trị bbox hard-code, đúng ở
  nhiều mức zoom.

**Acceptance criteria:**
- [ ] Overlay hiển thị đúng vị trí ở ít nhất 2 mức zoom khác nhau, dùng cùng
      1 bbox hard-code.

**Tests required:** Unit test thuần cho hàm chuyển đổi toạ độ (input bbox +
kích thước trang → output pixel đúng).

**Do not do:** Không lấy bbox từ OCR thật ở task này (đó là M5).

**Dependencies:** M2-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 4.3 (phần Quyết định về bbox chuẩn hoá) trước khi làm.
Trong frontend/src/components/DocumentViewer/, viết 1 hàm thuần chuyển đổi
toạ độ bbox chuẩn hoá (bbox_x, bbox_y, bbox_width, bbox_height, giá trị
0.0-1.0) cộng với kích thước hiển thị hiện tại của trang, ra toạ độ pixel để
vẽ overlay. Vẽ overlay highlight (ví dụ khung màu) đúng vị trí, test bằng 1
giá trị bbox hard-code (ví dụ bbox_x=0.12, bbox_y=0.34, bbox_width=0.30,
bbox_height=0.04), xác nhận đúng vị trí ở ít nhất 2 mức zoom khác nhau. Viết
unit test thuần cho hàm chuyển đổi toạ độ. Chưa nối với dữ liệu OCR thật ở
task này.
```

---

### M2-T3 — Backend: endpoint trả file document cho viewer

**Goal:** Frontend load được file document đã upload để hiển thị trong
viewer.

**Files/modules:** `backend/app/api/documents.py` (mở rộng).

**Requirements:**
- `GET /documents/{document_id}/file` trả file vật lý (PDF/ảnh) đã upload ở
  M1.

**Acceptance criteria:**
- [ ] Gọi endpoint với `document_id` hợp lệ → trả đúng file đã upload.
- [ ] `document_id` không tồn tại → lỗi 404 rõ ràng.

**Tests required:** API test happy path + test document_id không tồn tại.

**Do not do:** Không thêm logic OCR/LLM vào endpoint này.

**Dependencies:** M1-T6.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 1 trước khi làm. Trong app/api/documents.py,
thêm endpoint GET /documents/{document_id}/file trả về file vật lý (PDF/ảnh)
đã upload, dựa trên Document.file_path lưu trong DB. Trả lỗi 404 rõ ràng nếu
document_id không tồn tại. Router chỉ nhận request -> đọc file_path qua
service/repository -> trả file, không chứa logic nghiệp vụ khác. Viết API
test cho document_id hợp lệ và không hợp lệ.
```

---

## M3 — OCR + Persist

### M3-T1 — OCRProvider port interface

**Goal:** Định nghĩa interface `OCRProvider` ở tầng `domain/ports/`.

**Files/modules:** `backend/app/domain/ports/ocr_provider.py`.

**Requirements:**
- Interface nhận input là 1 document (file path hoặc nội dung file) và trả
  về danh sách `OCRBlock` nội bộ (chưa lưu DB).
- Không import PaddleOCR/VietOCR trong file này.

**Acceptance criteria:**
- [ ] Interface đủ để `local_ocr_adapter.py` (M3-T3) implement.
- [ ] File không import PaddleOCR/VietOCR.

**Tests required:** Không cần test riêng.

**Do not do:** Không viết implementation trong file này.

**Dependencies:** M1-T1 (cần model `OCRBlock` — xem M3-T2, có thể làm song
song).

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 3-4, mục 6 (OCR Module) và DEVELOPMENT_RULES.md mục 5
trước khi làm. Trong app/domain/ports/ocr_provider.py, định nghĩa interface
trừu tượng OCRProvider: nhận input là thông tin 1 document (ví dụ file_path,
document_id), trả về danh sách OCRBlock nội bộ (text, page_number, bbox,
confidence - chưa lưu DB, chỉ trả về object). File này tuyệt đối không được
import paddleocr, vietocr hay bất kỳ thư viện OCR cụ thể nào - chỉ định nghĩa
hợp đồng.
```

---

### M3-T2 — Domain model: OCRBlock

**Goal:** Định nghĩa model `OCRBlock`, đúng field DATA_MODEL.md §4.3.

**Files/modules:** `backend/app/domain/models.py` (mở rộng).

**Requirements:**
- Field đúng bảng DATA_MODEL.md §4.3, bbox dùng kiểu float (0.0–1.0).

**Acceptance criteria:**
- [ ] Model `OCRBlock` có đủ field, đúng type.

**Tests required:** Unit test khởi tạo model với dữ liệu hợp lệ.

**Do not do:** Không thêm field ngoài DATA_MODEL.md.

**Dependencies:** M1-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 4.3 trước khi làm. Mở rộng app/domain/models.py, thêm
model OCRBlock đúng field: id, document_id, page_number, text, bbox_x,
bbox_y, bbox_width, bbox_height (float 0.0-1.0), confidence (float 0.0-1.0),
created_at. Dùng dataclass hoặc Pydantic có type rõ ràng, không dùng dict.
Viết test khởi tạo model với dữ liệu hợp lệ.
```

---

### M3-T3 — infra/ocr/local_ocr_adapter.py (PaddleOCR + VietOCR)

**Goal:** Implement `OCRProvider` bằng PaddleOCR (detect) + VietOCR
(recognize), chạy local.

**Files/modules:** `backend/app/infra/ocr/local_ocr_adapter.py`.

**Requirements:**
- PaddleOCR detect vùng chữ → cắt vùng → VietOCR recognize nội dung.
- Model weights load 1 lần lúc khởi động app, không load lại mỗi request
  (DEVELOPMENT_RULES.md §14).
- Đường dẫn model đọc từ biến môi trường/file cấu hình, không hard-code.
- Convert kết quả thành `OCRBlock` (sinh `id` nội bộ làm `source_id`, không
  dùng ID nội bộ của PaddleOCR).

**Acceptance criteria:**
- [ ] Chạy OCR trên 1 file mẫu, trả về danh sách `OCRBlock` hợp lý (text,
      bbox chuẩn hoá 0–1, confidence).
- [ ] Model load 1 lần, không load lại mỗi lần gọi adapter trong cùng
      process.

**Tests required:** Adapter test dùng fixture ảnh mẫu cố định
(DEVELOPMENT_RULES.md §8).

**Do not do:** Không đổi provider OCR khác PaddleOCR/VietOCR; không thêm
dependency ngoài stack đã chốt mà chưa xin xác nhận.

**Dependencies:** M3-T1, M3-T2.

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 1 và mục 6 (OCR Module), DATA_MODEL.md mục 4.3, và
DEVELOPMENT_RULES.md mục 14 trước khi làm. Trong
app/infra/ocr/local_ocr_adapter.py, implement interface OCRProvider: dùng
PaddleOCR để detect vùng chữ (bounding box + confidence), cắt từng vùng và
đưa qua VietOCR để nhận dạng nội dung chữ tiếng Việt (kể cả chữ viết tay).
Convert kết quả thành danh sách OCRBlock nội bộ - tự sinh id làm source_id
(không dùng ID nội bộ của PaddleOCR), bbox chuẩn hoá theo tỉ lệ trang
(0.0-1.0), không dùng pixel tuyệt đối. Model weights của PaddleOCR/VietOCR
phải load 1 lần khi khởi động app, không load lại mỗi request. Đường dẫn model
đọc từ biến môi trường/file cấu hình, không hard-code trong source code. Viết
adapter test dùng 1-2 file ảnh mẫu cố định (fixture) để xác nhận output hợp lý
(không cần gọi model thật nếu tốn thời gian - có thể dùng ảnh nhỏ, đơn giản
làm fixture).
```

---

### M3-T4 — SQLite repository: OCRBlock

**Goal:** Lưu/đọc `OCRBlock` vào SQLite.

**Files/modules:** `backend/app/infra/db/` (mở rộng), cập nhật
`domain/ports/repository.py` nếu cần thêm method.

**Requirements:**
- Bảng `OCRBlock` đúng field DATA_MODEL.md §4.3.
- `OCRBlock` bất biến sau khi tạo (DATA_MODEL.md §3) — repository không cung
  cấp method update cho bảng này.

**Acceptance criteria:**
- [ ] Lưu và đọc lại `OCRBlock` theo `document_id` đúng dữ liệu.
- [ ] Không có method update/delete cho `OCRBlock` trong repository.

**Tests required:** Test repository tạo + đọc `OCRBlock`.

**Do not do:** Không thêm method sửa `OCRBlock`.

**Dependencies:** M3-T2, M1-T3.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 3 (lifecycle - OCRBlock bất biến) và mục 4.3 trước khi
làm. Mở rộng app/infra/db/ để lưu và đọc OCRBlock: tạo bảng đúng field ở
DATA_MODEL.md mục 4.3, thêm method vào repository (và interface ở
domain/ports/repository.py nếu cần) để tạo OCRBlock (theo batch, vì 1 lần OCR
sinh nhiều block) và đọc danh sách OCRBlock theo document_id. KHÔNG thêm
method update hay delete cho OCRBlock - theo DATA_MODEL.md, OCRBlock bất biến
sau khi tạo. Viết test cho tạo + đọc OCRBlock.
```

---

### M3-T5 — extraction_service.py (phần OCR) + BackgroundTasks wiring

**Goal:** Điều phối chạy OCR nền sau khi case đủ 4 document, lưu `OCRBlock`,
cập nhật `Document.ocr_status`.

**Files/modules:** `backend/app/domain/services/extraction_service.py`,
`backend/app/api/documents.py` (kích hoạt BackgroundTasks).

**Requirements:**
- Sau khi `case_service.py` xác nhận đủ 4 document (từ M1-T4), kích hoạt
  `extraction_service.py` qua `BackgroundTasks` (ARCHITECTURE.md §8).
- Với mỗi document: gọi `OCRProvider`, lưu `OCRBlock`, cập nhật
  `Document.ocr_status: PENDING → DONE` (hoặc `FAILED` nếu lỗi).
- Service chỉ phụ thuộc `domain/ports/`, không import PaddleOCR/VietOCR trực
  tiếp.

**Acceptance criteria:**
- [ ] Sau upload đủ 4 giấy tờ, OCR tự chạy nền, không chặn response upload.
- [ ] `Document.ocr_status` chuyển đúng `PENDING → DONE`/`FAILED`.
- [ ] `OCRBlock` được lưu đúng, đủ field.

**Tests required:** Unit test phần điều phối OCR dùng fake `OCRProvider`
(không dùng PaddleOCR/VietOCR thật) — theo DEVELOPMENT_RULES.md §8.

**Do not do:** Không gọi LLM ở task này (đó là M4); không để lỗi OCR làm
"treo" document ở trạng thái `PENDING` mãi.

**Dependencies:** M3-T3, M3-T4, M1-T4, M1-T6.

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 2-3, mục 8 (BackgroundTasks), DEVELOPMENT_RULES.md
mục 2 và mục 5 trước khi làm. Trong app/domain/services/extraction_service.py
(tạo mới nếu chưa có), viết phần điều phối OCR: khi case đủ 4 document (đã
xác nhận từ case_service.py), kích hoạt xử lý nền qua FastAPI BackgroundTasks
- với mỗi document, gọi OCRProvider (qua interface ở domain/ports/, không
import PaddleOCR/VietOCR trực tiếp), lưu kết quả OCRBlock, cập nhật
Document.ocr_status từ PENDING sang DONE (hoặc FAILED nếu OCR lỗi - không để
document treo ở PENDING mãi). Nối wiring BackgroundTasks vào endpoint upload
document ở app/api/documents.py. Chưa gọi LLM ở task này. Viết unit test cho
phần điều phối OCR dùng fake OCRProvider (implement interface, trả dữ liệu
giả), test cả trường hợp OCR thành công và lỗi.
```

---

### M3-T6 — Adapter test với fixture ảnh mẫu

**Goal:** Đảm bảo `local_ocr_adapter.py` được test với dữ liệu mẫu cố định
để phát hiện khi PaddleOCR/VietOCR đổi hành vi.

**Files/modules:** `backend/tests/infra/ocr/` (fixture + test).

**Requirements:**
- Chuẩn bị 1–2 file ảnh mẫu cố định (đơn giản, không phải giấy tờ thật) làm
  fixture.
- Test chạy adapter thật (không mock) với fixture, xác nhận output hợp lý
  (không cần chính xác 100%, chỉ cần không lỗi và có bbox/text hợp lệ).

**Acceptance criteria:**
- [ ] Test chạy được, không phụ thuộc mạng, không phụ thuộc dữ liệu thay đổi.

**Tests required:** Đây chính là task viết test — không có test khác.

**Do not do:** Không dùng giấy tờ thật (CCCD/hợp đồng thật) làm fixture.

**Dependencies:** M3-T3.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 8 trước khi làm. Chuẩn bị 1-2 ảnh mẫu đơn giản,
không phải giấy tờ thật (ví dụ ảnh chụp 1 đoạn chữ in tiếng Việt tự tạo) làm
fixture cố định trong backend/tests/infra/ocr/. Viết test chạy
local_ocr_adapter.py thật (không mock PaddleOCR/VietOCR) với fixture này, xác
nhận: không lỗi, trả về ít nhất 1 OCRBlock, bbox nằm trong khoảng 0.0-1.0,
text không rỗng. Không dùng giấy tờ thật (CCCD, hợp đồng thật) làm fixture.
```

---

### M3-T7 — Thử nghiệm OCR trên chữ viết tay thật (task đánh giá, không phải code)

**Goal:** Đánh giá sớm rủi ro độ chính xác OCR trên chữ viết tay, theo cảnh
báo ở ARCHITECTURE.md §1, trước khi đi tiếp sang M4.

**Files/modules:** Không có file code cố định — đây là task thử nghiệm/đánh
giá, kết quả ghi lại thành note (ví dụ 1 file `docs/ocr-handwriting-eval.md`
hoặc mục trong FEATURE_BACKLOG này nếu cần task fine-tune tiếp theo).

**Requirements:**
- Chạy `local_ocr_adapter.py` (từ M3-T3) trên vài mẫu giấy đề nghị vay vốn có
  chữ viết tay thật hoặc gần giống thật (không dùng giấy tờ CCCD/hợp đồng
  thật của người thật, chỉ cần mẫu viết tay tương tự).
- Ghi nhận kết quả: đạt yêu cầu hay cần fine-tune thêm.

**Acceptance criteria:**
- [ ] Có ít nhất 1 lần chạy thử thật với vài mẫu viết tay, có ghi nhận kết
      quả rõ ràng (đạt/chưa đạt, ví dụ nào đọc sai).
- [ ] Nếu chưa đạt: có note đề xuất fine-tune VietOCR như 1 task riêng, KHÔNG
      tự ý đổi OCR provider (DEVELOPMENT_RULES.md §12).

**Tests required:** Không phải test tự động — đây là đánh giá thủ công.

**Do not do:** Không tự quyết định đổi OCR provider nếu kết quả chưa tốt —
phải dừng lại, báo lại, chờ xác nhận hướng xử lý.

**Dependencies:** M3-T3.

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 1 (phần "Rủi ro cần thử nghiệm sớm" ở dòng OCR
provider) và DEVELOPMENT_RULES.md mục 12 trước khi làm. Dùng
local_ocr_adapter.py (đã có từ task trước) chạy thử trên vài mẫu giấy đề nghị
vay vốn có chữ viết tay (dùng mẫu tự tạo/mẫu công khai gần giống, KHÔNG dùng
giấy tờ thật của người thật). Ghi lại kết quả vào 1 file note (ví dụ
docs/ocr-handwriting-eval.md): mẫu nào đọc đúng, mẫu nào đọc sai, đánh giá
tổng thể đạt hay chưa đạt yêu cầu. Nếu chưa đạt, đề xuất hướng fine-tune
VietOCR như 1 task riêng trong note - KHÔNG tự ý đổi sang OCR provider khác,
phải dừng lại và chờ xác nhận hướng xử lý.
```

---

## M4 — LLM Extraction + source_ids

### M4-T1 — Chốt `docs/EXTRACTION_SCHEMA.md`

**Goal:** Chốt chính xác các field mà LLM phải extract trong MVP trước khi viết prompt/schema Gemini.

**Files/modules:** `docs/EXTRACTION_SCHEMA.md`.

**Requirements:**
- Liệt kê từng `field_code`, label, data type và document source dự kiến (`CCCD_FRONT`, `CCCD_BACK`, `LOAN_APPLICATION`, `LABOR_CONTRACT`).
- Chốt Core 40 field, tất cả dùng raw `string | null`; không tự mở rộng sang
  toàn bộ BPM form.
- Chốt checkbox semantics: nhóm single-choice, `muc_dich_vay` multi-choice,
  `UNCERTAIN`/conflict không được tự chọn.
- Ghi rõ V1 không marker và V2 có marker cùng được hỗ trợ; runtime input vẫn là
  PDF/ảnh, không thêm DOCX upload.
- Chỉ gồm field thật sự cần demo trong MVP; không thêm cross-document validation.
- Quy định output khi không tìm thấy field: `value = null`, `source_ids = []`.
- Quy định field có value thì mọi `source_id` phải tồn tại trong OCRBlock input.

**Acceptance criteria:**
- [ ] Không còn field_code mơ hồ trước khi implement Gemini extractor.
- [ ] M4-T2 trở đi có thể dùng tài liệu này làm source of truth cho structured output.

**Tests required:** Không có — đây là specification task.

**Do not do:** Không viết code LLM; không tự thêm field ngoài scope MVP.

**Dependencies:** M3 hoàn thành hoặc ít nhất đã có OCR output mẫu để kiểm tra schema.

**Ready-to-paste Codex prompt:**
```
Không code ứng dụng. Đọc docs/PROJECT_BRIEF.md và docs/DATA_MODEL.md, sau đó tạo docs/EXTRACTION_SCHEMA.md chốt danh sách field MVP cho 4 document types. Với mỗi field ghi field_code, label, type và document source dự kiến. Quy định rõ: không tìm thấy -> value=null, source_ids=[]; có value -> source_ids phải là OCRBlock id có trong input. Giữ scope nhỏ, không thêm cross-document validation.
```



### M4-T1A — Local template OMR cho checkbox

**Goal:** Biến checkbox đã chọn trên `LOAN_APPLICATION` thành evidence block có
source ID/bbox trước khi gọi Gemini.

**Files/modules:** `backend/app/infra/ocr/` (module template/alignment/detector),
`backend/app/infra/ocr/local_ocr_adapter.py`, template config/assets và tests
liên quan.

**Requirements:**
- Chỉ chạy cho `LOAN_APPLICATION` có template/version đã đăng ký.
- `OCRProvider.extract` nhận thêm `document_type` từ orchestration; adapter
  không đoán loại tài liệu từ filename. Cập nhật các fake/call site liên quan.
- V1 không marker: feature matching + RANSAC/homography với blank template.
- V2 có bốn marker ID khác nhau: ưu tiên marker để nhận diện version/căn chỉnh;
  fallback V1 chỉ khi template config cho phép.
- Sau căn chỉnh vẫn tìm lại checkbox quanh ROI chuẩn hoá và so sánh phần ruột
  với blank template; không dùng một pixel/toạ độ tuyệt đối.
- Phân loại `CHECKED`, `UNCHECKED`, `UNCERTAIN`; chỉ `CHECKED` tạo
  `OCRBlockKind.CHECKBOX_SELECTION` có canonical field/option, bbox thật và
  confidence.
- Nhiều lựa chọn trong single-choice, sai template, thiếu vùng cần thiết hoặc
  alignment score thấp phải fail closed; không tự chọn option gần nhất.
- Dùng OpenCV và NumPy trong OCR environment đã approved; không thêm dependency.

**Acceptance criteria:**
- [ ] Synthetic PDF trên đúng production template đọc đúng tick/X/tô kín ở
      các nhóm checkbox đã đăng ký.
- [ ] Blur/xoay/phối cảnh ở mức acceptance fixture vẫn căn chỉnh và đọc đúng;
      mẫu dưới ngưỡng chất lượng trả uncertain/failure thay vì chọn sai.
- [ ] Selection block có source ID và bbox chuẩn hoá để Review UI highlight.
- [ ] V1 không marker chạy được; config V2 có marker được hỗ trợ mà không đổi
      contract phía người upload.

**Tests required:** Unit test classifier checked/unchecked/uncertain và
single-choice conflict; một synthetic PDF fixture bao phủ alignment + local
ROI + bbox. Không cần tạo ma trận lớn các biến thể gần giống nhau ở task này.

**Do not do:** Không dùng OCR text/Gemini để đoán tick; không thêm provider,
subprocess/microservice hoặc dependency; không dùng tài liệu khách hàng thật.

**Dependencies:** M3-T3, M3-T6, `docs/EXTRACTION_SCHEMA.md`.

---

### M4-T2 — LLMProvider port interface

**Goal:** Định nghĩa interface `LLMProvider` ở tầng `domain/ports/`.

**Files/modules:** `backend/app/domain/ports/llm_provider.py`.

**Requirements:**
- Định nghĩa `LLMDocumentInput` gồm `document_id`, `document_type` và danh sách
  `OCRBlock` của document đó. Interface nhận danh sách document input của 1
  case, trả về danh sách field trích xuất (`field_code`, `value`,
  `source_ids`), trong đó `value` có thể null khi không tìm thấy.
- Giữ nguyên page/bbox/source ID và document grouping; adapter không query
  repository để tự tìm document type.
- Không import Google Gemini SDK trong file này.

**Acceptance criteria:**
- [ ] Interface đủ để `gemini_extractor.py` (M4-T4) implement.
- [ ] File không import Gemini SDK.

**Tests required:** Không cần test riêng.

**Do not do:** Không viết implementation trong file này.

**Dependencies:** M3-T2 (cần khái niệm OCRBlock/source_id).

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 3-4, mục 6 (LLM Extraction Module) và
DEVELOPMENT_RULES.md mục 5 trước khi làm. Trong
app/domain/ports/llm_provider.py, định nghĩa interface trừu tượng
LLMProvider: nhận input là danh sách LLMDocumentInput của 1 case; mỗi input có
document_id, document_type và danh sách OCRBlock (text/checkbox selection + source_id),
trả về danh sách field trích xuất gồm field_code, value (nullable), source_ids (danh
sách source_id tham chiếu tới OCRBlock đã có). Quy ước: value=null thì source_ids=[]; value có dữ liệu thì source_ids phải có ít nhất 1 phần tử hợp lệ. File này tuyệt đối không được
import SDK Google Gemini - chỉ định nghĩa hợp đồng.
```

---

### M4-T3 — Domain models: ExtractedField, FieldSource

**Goal:** Định nghĩa model, đúng field DATA_MODEL.md §4.4, §4.5.

**Files/modules:** `backend/app/domain/models.py` (mở rộng).

**Requirements:**
- Field đúng bảng DATA_MODEL.md §4.4 (`ExtractedField`) và §4.5
  (`FieldSource`).

**Acceptance criteria:**
- [ ] Model có đủ field, đúng type.

**Tests required:** Unit test khởi tạo model với dữ liệu hợp lệ.

**Do not do:** Không thêm field ngoài DATA_MODEL.md.

**Dependencies:** M1-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 4.4 và 4.5 trước khi làm. Mở rộng app/domain/models.py,
thêm model ExtractedField (id, case_id, field_code, original_value,
current_value, created_at, updated_at) và FieldSource (id,
extracted_field_id, ocr_block_id). Dùng dataclass hoặc Pydantic có type rõ
ràng. Viết test khởi tạo model với dữ liệu hợp lệ.
```

---

### M4-T4 — infra/llm/gemini_extractor.py (structured output + retry/backoff)

**Goal:** Implement `LLMProvider` bằng Gemini API, ép structured output, có
retry/backoff.

**Files/modules:** `backend/app/infra/llm/gemini_extractor.py`.

**Requirements:**
- Dùng đúng SDK `google-genai==2.21.0` (không dùng legacy
  `google-generativeai`) và model `gemini-3.7-flash`.
- Gọi Gemini API (free tier) với document-aware input và schema JSON định sẵn
  (`field_code`, `value`, `source_ids`), validate cấu trúc/catalog response bằng
  Pydantic. Validation nghiệp vụ từng field (value/source tồn tại) nằm ở
  Extraction Service để hỗ trợ partial extraction theo
  `docs/EXTRACTION_SCHEMA.md`.
- Retry/backoff giới hạn số lần khi gặp lỗi 429 (DEVELOPMENT_RULES.md §14) —
  không retry vô hạn.
- API key đọc từ biến môi trường, không hard-code.

**Acceptance criteria:**
- [ ] Gọi Gemini thành công, parse được response đúng schema.
- [ ] Giả lập lỗi 429 → retry đúng số lần giới hạn, sau đó raise lỗi rõ ràng
      thay vì lặp vô hạn.

**Tests required:** Adapter test dùng fixture cố định (mock response Gemini)
+ test riêng cho retry/backoff (mock lỗi 429), không bắt buộc gọi Gemini thật
trong test tự động (DEVELOPMENT_RULES.md §8).

**Do not do:** Không đổi LLM provider khác Gemini; không retry vô hạn; không
thêm retry dependency như tenacity nếu SDK/thư viện chuẩn đã đủ; không gửi tài
liệu khách hàng thật trong smoke/demo.

**Dependencies:** M4-T2, M4-T3.

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 1 và mục 6 (LLM Extraction Module), PROJECT_BRIEF.md
mục 5 bước 3 (LLM không được tự tạo bbox), và DEVELOPMENT_RULES.md mục 14
trước khi làm. Trong app/infra/llm/gemini_extractor.py, implement interface
LLMProvider: dùng google-genai==2.21.0 gọi model gemini-3.7-flash (Google AI
Studio free tier) với document-aware input và structured
output schema JSON định sẵn (field_code, value, source_ids), validate response
bằng Pydantic ở mức cấu trúc/catalog. Giữ nguyên value/source_ids để
Extraction Service validate nghiệp vụ từng field và áp dụng partial extraction
theo docs/EXTRACTION_SCHEMA.md. API key đọc từ biến môi trường (GEMINI_API_KEY), không
hard-code. Có cơ chế retry/backoff đơn giản khi gặp lỗi rate-limit (429), giới
hạn số lần retry rõ ràng (ví dụ tối đa 3 lần), không được retry vô hạn - sau
khi hết số lần retry, raise lỗi rõ ràng để tầng gọi xử lý (chuyển Case.status
sang FAILED). Viết adapter test dùng fixture cố định (mock response Gemini,
không gọi API thật trong test tự động) và test riêng cho retry/backoff (mock
lỗi 429 liên tiếp, xác nhận dừng đúng sau số lần giới hạn).
```

---

### M4-T5 — SQLite repository: ExtractedField, FieldSource

**Goal:** Lưu/đọc `ExtractedField`, `FieldSource` vào SQLite.

**Files/modules:** `backend/app/infra/db/` (mở rộng).

**Requirements:**
- Bảng đúng field DATA_MODEL.md §4.4, §4.5.
- `FieldSource` bất biến sau khi tạo (DATA_MODEL.md §3).
- Method đọc `ExtractedField` kèm `sources` (join `FieldSource` → `OCRBlock`)
  cho 1 case — cần cho M5.

**Acceptance criteria:**
- [ ] Lưu và đọc lại `ExtractedField` + `FieldSource` đúng dữ liệu.
- [ ] Đọc theo `case_id` trả đúng danh sách field kèm sources.

**Tests required:** Test repository tạo + đọc.

**Do not do:** Không thêm method update cho `FieldSource`.

**Dependencies:** M4-T3, M3-T4.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 3, mục 4.4, mục 4.5, và mục 5 (ví dụ JSON ExtractedField
kèm sources) trước khi làm. Mở rộng app/infra/db/ để lưu và đọc
ExtractedField, FieldSource: tạo bảng đúng field ở DATA_MODEL.md mục 4.4/4.5,
thêm method tạo (batch), và method đọc danh sách ExtractedField kèm sources
(join qua FieldSource -> OCRBlock, trả về cấu trúc giống ví dụ JSON ở
DATA_MODEL.md mục 5) theo case_id. KHÔNG thêm method update cho FieldSource -
bất biến sau khi tạo. Viết test cho tạo + đọc, bao gồm test đọc kèm sources.
```

---

### M4-T6 — extraction_service.py (phần LLM) — validate source_ids, cập nhật status

**Goal:** Mở rộng `extraction_service.py`: sau khi đủ `OCRBlock` của cả 4
document, gọi LLM, validate, lưu `ExtractedField`/`FieldSource`, chuyển
`Case.status → READY_FOR_REVIEW`.

**Files/modules:** `backend/app/domain/services/extraction_service.py` (mở
rộng).

**Requirements:**
- Sau khi tất cả document có `ocr_status = DONE`, gọi `LLMProvider` với toàn
  bộ `OCRBlock` của case được nhóm thành `LLMDocumentInput` kèm đúng
  `document_id`/`document_type`.
- **Validate nghiêm theo từng field:** nếu field có value thì value phải khác
  rỗng, có ít nhất 1 `source_id`, và mọi `source_id` phải tồn tại trong
  `OCRBlock` đã lưu của case đó. Field không đạt bị hạ thành null/không source,
  không lưu value không đáng tin; LLM không được tự tạo bbox/source id.
- Luôn tạo đủ đúng 40 `ExtractedField`, kể cả field missing/invalid. Partial
  extraction vẫn chuyển `READY_FOR_REVIEW` để chuyên viên điền ô trống.
- Lưu `ExtractedField` + `FieldSource`, chuyển `Case.status → READY_FOR_REVIEW`
  (hoặc `FAILED` nếu lỗi cấp pipeline như OCR lỗi, LLM hết retry/response không
  parse được, hoặc persistence lỗi).

**Acceptance criteria:**
- [ ] Sau OCR xong cả 4 document, LLM tự chạy, tạo đúng `ExtractedField`.
- [ ] Field missing hoặc có value nhưng thiếu/sai source_id được lưu thành ô
      trống; field hợp lệ vẫn được giữ và tổng cộng luôn đủ 40 field.
- [ ] `Case.status` chuyển đúng `PROCESSING → READY_FOR_REVIEW` hoặc
      `→ FAILED`.

**Tests required:** Unit test dùng fake `LLMProvider`, bao gồm case LLM trả
`source_id` không hợp lệ (phải bị chặn) — DEVELOPMENT_RULES.md §8.

**Do not do:** Không tự nới lỏng validate "source_id phải tồn tại" dù LLM
free tier đôi khi trả sai — đây là rule cứng từ PROJECT_BRIEF.

**Dependencies:** M4-T4, M4-T5, M3-T5.

**Ready-to-paste Codex prompt:**
```
Đọc docs/PROJECT_BRIEF.md mục 3 và mục 5 bước 3-4 (LLM không được tự tạo bbox),
DATA_MODEL.md mục 3, và ARCHITECTURE.md mục 6 (Mapping) trước khi làm. Mở
rộng app/domain/services/extraction_service.py: sau khi tất cả document của 1
case có ocr_status = DONE, nhóm toàn bộ OCRBlock theo document và gọi
LLMProvider (qua interface, không import Gemini SDK trực tiếp) bằng danh sách
LLMDocumentInput có document_id/document_type. Validate nghiêm theo từng field
theo docs/EXTRACTION_SCHEMA.md: value có dữ liệu phải khác rỗng, có ít nhất 1
source_id và mọi source_id phải khớp OCRBlock đã có trong case. Nếu sai, không
lưu value không đáng tin mà tạo field null/không source để chuyên viên nhập tay.
Luôn lưu đủ đúng 40 ExtractedField và chuyển sang READY_FOR_REVIEW, kể cả partial
extraction hoặc toàn bộ field null. Chỉ chuyển FAILED khi lỗi cấp pipeline như
OCR lỗi, Gemini hết retry/response không parse được hoặc persistence lỗi. Viết unit test dùng fake
LLMProvider, bao gồm test case: field hợp lệ được lưu đúng, field có
source_id sai bị chặn, LLM lỗi -> case FAILED.
```

---

### M4-T7 — Adapter test cho gemini_extractor.py (mock)

**Goal:** Bổ sung test còn thiếu cho adapter Gemini nếu M4-T4 chưa đủ coverage
(đặc biệt phần parse structured output với dữ liệu tiếng Việt thật).

**Files/modules:** `backend/tests/infra/llm/`.

**Requirements:**
- Test parse response Gemini mẫu (mock, dữ liệu tiếng Việt) thành
  `ExtractedField`/`source_ids` đúng.
- Test response Gemini sai schema (ví dụ thiếu field bắt buộc) → bị Pydantic
  chặn, không crash toàn service.

**Acceptance criteria:**
- [ ] Test pass với response mẫu hợp lệ và không hợp lệ.

**Tests required:** Đây là task viết test.

**Do not do:** Không gọi Gemini thật trong test tự động.

**Dependencies:** M4-T4.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 8 trước khi làm. Bổ sung test cho
app/infra/llm/gemini_extractor.py trong backend/tests/infra/llm/: dùng mock
response Gemini (dữ liệu tiếng Việt mẫu, ví dụ field ho_ten/so_cccd) để test
parse thành field + source_ids đúng; test thêm 1 trường hợp response sai
schema (ví dụ thiếu field bắt buộc trong JSON) để xác nhận Pydantic validation
chặn đúng, không làm crash toàn bộ service. Không gọi Gemini API thật trong
test tự động.
```

---

## M5 — Dynamic Evidence Highlight

### M5-T1 — review_service.py (phần đọc dữ liệu cho Review UI)

**Goal:** Đọc danh sách field kèm sources cho 1 case, phục vụ Review UI.

**Files/modules:** `backend/app/domain/services/review_service.py` (tạo
mới).

**Requirements:**
- Method lấy danh sách `ExtractedField` kèm `sources` (document_id,
  page_number, bbox) cho 1 `case_id`, dùng repository method từ M4-T4.
- Chỉ trả dữ liệu khi `Case.status = READY_FOR_REVIEW` (hoặc `COMPLETED` để
  xem lại) — case chưa xử lý xong thì báo trạng thái tương ứng.

**Acceptance criteria:**
- [ ] Trả đúng danh sách field kèm sources cho case đã `READY_FOR_REVIEW`.
- [ ] Case chưa `READY_FOR_REVIEW` → trả thông tin trạng thái phù hợp, không
      trả field rỗng gây hiểu nhầm.

**Tests required:** Unit test dùng fake repository.

**Do not do:** Không xử lý sửa field ở task này (đó là M6).

**Dependencies:** M4-T4.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 3 và mục 5 (ví dụ JSON ExtractedField kèm sources), và
DEVELOPMENT_RULES.md mục 2 trước khi làm. Trong
app/domain/services/review_service.py (tạo mới), viết method lấy danh sách
ExtractedField kèm sources (document_id, page_number, bbox) cho 1 case_id,
dùng method repository đã có từ task trước. Nếu Case.status chưa
READY_FOR_REVIEW (ví dụ còn PROCESSING hoặc FAILED), trả về thông tin trạng
thái rõ ràng thay vì danh sách field rỗng gây hiểu nhầm là "không có field
nào". Service này chỉ lo đọc dữ liệu cho Review UI ở task này, chưa xử lý sửa
field. Viết unit test dùng fake repository cho các case: case READY_FOR_REVIEW
có field, case còn PROCESSING.
```

---

### M5-T2 — api/review.py: GET endpoint

**Goal:** Endpoint lấy dữ liệu review cho 1 case.

**Files/modules:** `backend/app/api/review.py` (tạo mới).

**Requirements:**
- `GET /cases/{case_id}/review` gọi `review_service.py`, trả danh sách field
  kèm sources.

**Acceptance criteria:**
- [ ] Gọi endpoint với case đã `READY_FOR_REVIEW` → trả đúng dữ liệu.

**Tests required:** API test happy path + case chưa sẵn sàng.

**Do not do:** Không viết business logic trong router.

**Dependencies:** M5-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 1 trước khi làm. Trong app/api/review.py (tạo
mới), viết endpoint GET /cases/{case_id}/review: nhận request, gọi
review_service.py, trả response là danh sách field kèm sources (Pydantic
schema khớp ví dụ JSON ở DATA_MODEL.md mục 5). Router chỉ nhận request -> gọi
service -> trả response. Viết API test cho case đã READY_FOR_REVIEW và case
chưa sẵn sàng.
```

---

### M5-T3 — Frontend: FieldList/FieldItem components

**Goal:** Hiển thị danh sách field thật lên Review UI.

**Files/modules:** `frontend/src/components/FieldList/`,
`frontend/src/components/FieldItem/`.

**Requirements:**
- `FieldList` gọi API M5-T2, hiển thị danh sách field (`field_code`,
  `current_value`).
- `FieldItem` hiển thị 1 field, có thể click (sự kiện click nối ở M5-T4).

**Acceptance criteria:**
- [ ] Trang Review hiển thị đúng danh sách field thật của case.

**Tests required:** Không bắt buộc test tự động; kiểm tra thủ công.

**Do not do:** Không code sẵn logic sửa field ở task này (đó là M6).

**Dependencies:** M5-T2.

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 3 (Review Panel) trước khi làm. Trong
frontend/src/components/FieldList/ và frontend/src/components/FieldItem/,
viết component hiển thị danh sách field thật của 1 case: FieldList gọi API
GET /cases/{case_id}/review và hiển thị danh sách, FieldItem hiển thị 1 field
(field_code, current_value), có thể nhận sự kiện click (xử lý click thật sẽ
nối ở task sau). Chưa code logic sửa giá trị field ở task này.
```

---

### M5-T4 — Frontend: nối click field → DocumentViewer (dữ liệu thật)

**Goal:** Click 1 field → viewer mở đúng document/trang, highlight đúng vùng
bbox thật.

**Files/modules:** trang Review (`frontend/src/pages/ReviewPage.tsx`), nối
`FieldList`/`FieldItem` (M5-T3) với `DocumentViewer` (M2-T1/T2).

**Requirements:**
- Click field → `DocumentViewer` chuyển đúng document, đúng trang, vẽ overlay
  từ bbox thật (không còn hard-code).
- Field có nhiều `sources` (nhiều `OCRBlock`) → highlight tất cả vùng liên
  quan (DATA_MODEL.md §2).

**Acceptance criteria:**
- [ ] Click qua vài field khác nhau, viewer mở đúng document/trang/vùng mỗi
      lần.
- [ ] Field có nhiều nguồn OCR → tất cả vùng liên quan được highlight cùng
      lúc.

**Tests required:** Test tích hợp nếu framework hỗ trợ, hoặc ghi lại kịch bản
test thủ công.

**Do not do:** Không cho sửa giá trị field ở task này (đó là M6).

**Dependencies:** M5-T3, M2-T1, M2-T2.

**Ready-to-paste Codex prompt:**
```
Đọc docs/PROJECT_BRIEF.md mục 5 bước 5 và DATA_MODEL.md mục 2 (1 field có thể có
nhiều nguồn OCR) trước khi làm. Trong frontend/src/pages/ReviewPage.tsx, nối
FieldList/FieldItem (đã có) với DocumentViewer (đã có): khi click 1 field,
DocumentViewer tự chuyển sang đúng document và trang tương ứng, vẽ overlay
highlight từ bbox thật lấy từ sources của field đó (dùng hàm chuyển đổi toạ
độ đã viết ở milestone trước, không còn dùng bbox hard-code). Nếu field có
nhiều sources (nhiều OCRBlock), highlight tất cả vùng liên quan cùng lúc (có
thể ở nhiều trang/document khác nhau nếu dữ liệu như vậy). Ghi lại kịch bản
test thủ công: click qua ít nhất 3 field khác nhau, xác nhận viewer mở đúng
chỗ mỗi lần.
```

---

## M6 — Review / Edit / Confirm

### M6-T1 — Domain model: ReviewAction

**Goal:** Định nghĩa model, đúng field DATA_MODEL.md §4.6.

**Files/modules:** `backend/app/domain/models.py` (mở rộng).

**Requirements:**
- Field đúng bảng DATA_MODEL.md §4.6, enum `ReviewActionType` (`EDIT_FIELD`,
  `UPLOAD_CASE`).

**Acceptance criteria:**
- [ ] Model có đủ field, `extracted_field_id`/`previous_value`/`new_value`
      nullable đúng như DATA_MODEL.md.

**Tests required:** Unit test khởi tạo model cho cả 2 loại action.

**Do not do:** Không thêm field ngoài DATA_MODEL.md.

**Dependencies:** M1-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 4.6 và mục 5 (ví dụ JSON ReviewAction) trước khi làm.
Mở rộng app/domain/models.py, thêm enum ReviewActionType (EDIT_FIELD,
UPLOAD_CASE) và model ReviewAction: id, case_id, extracted_field_id
(nullable), action_type, previous_value (nullable), new_value (nullable),
created_at. Viết test khởi tạo model cho cả 2 loại action (EDIT_FIELD có đủ
previous/new value, UPLOAD_CASE có extracted_field_id = null).
```

---

### M6-T2 — SQLite repository: ReviewAction

**Goal:** Lưu `ReviewAction` vào SQLite.

**Files/modules:** `backend/app/infra/db/` (mở rộng).

**Requirements:**
- Bảng đúng field DATA_MODEL.md §4.6.
- Method tạo `ReviewAction` (không cần update/delete — đây là audit log).

**Acceptance criteria:**
- [ ] Lưu `ReviewAction` cho cả 2 loại action đúng dữ liệu.

**Tests required:** Test repository tạo + đọc `ReviewAction` theo `case_id`.

**Do not do:** Không thêm method update/delete cho `ReviewAction` (audit log
không được sửa).

**Dependencies:** M6-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 4.6 trước khi làm. Mở rộng app/infra/db/ để lưu
ReviewAction: tạo bảng đúng field ở DATA_MODEL.md mục 4.6, thêm method tạo
ReviewAction và đọc danh sách ReviewAction theo case_id (dùng để xem lịch sử
sửa nếu cần). KHÔNG thêm method update/delete - đây là audit log, không được
sửa sau khi ghi. Viết test cho tạo + đọc.
```

---

### M6-T3 — review_service.py: sửa field (EDIT_FIELD)

**Goal:** Nhận sửa giá trị field từ chuyên viên, ghi `ReviewAction`.

**Files/modules:** `backend/app/domain/services/review_service.py` (mở
rộng).

**Requirements:**
- Method nhận `extracted_field_id` + giá trị mới, cập nhật
  `ExtractedField.current_value`, ghi 1 `ReviewAction`
  (`EDIT_FIELD`, `previous_value` = giá trị cũ, `new_value` = giá trị mới).
- **Không** tạo `ExtractedField` mới — chỉ update `current_value` (DATA_MODEL.md
  §3).

**Acceptance criteria:**
- [ ] Sửa field → `current_value` cập nhật đúng, `ReviewAction` ghi đúng
      `previous_value`/`new_value`.
- [ ] Sửa nhiều lần cùng field → mỗi lần tạo 1 `ReviewAction` mới, không tạo
      `ExtractedField` mới.

**Tests required:** Unit test dùng fake repository, bao gồm sửa nhiều lần
liên tiếp.

**Do not do:** Không tạo `ExtractedField` mới khi sửa; không yêu cầu confirm
riêng cho từng field (PROJECT_BRIEF.md §5 bước 6 — sửa không cần confirm
riêng).

**Dependencies:** M6-T2, M5-T1.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 3 (lifecycle ExtractedField) và mục 5 (ví dụ JSON
ReviewAction EDIT_FIELD), PROJECT_BRIEF.md mục 5 bước 6, trước khi làm. Mở
rộng app/domain/services/review_service.py: viết method nhận
extracted_field_id + giá trị mới, cập nhật ExtractedField.current_value (giữ
nguyên original_value), ghi 1 ReviewAction (action_type=EDIT_FIELD,
previous_value = giá trị cũ, new_value = giá trị mới). KHÔNG tạo
ExtractedField mới - chỉ update current_value của field đã có. Không yêu cầu
bước confirm riêng cho từng field. Viết unit test dùng fake repository, bao
gồm test sửa cùng 1 field nhiều lần liên tiếp (mỗi lần phải tạo 1 ReviewAction
mới, không tạo ExtractedField mới).
```

---

### M6-T4 — review_service.py: Upload case (UPLOAD_CASE, status COMPLETED)

**Goal:** Xử lý hành động Upload — lưu toàn bộ hồ sơ 1 lần, chuyển
`Case.status → COMPLETED`.

**Files/modules:** `backend/app/domain/services/review_service.py` (mở
rộng).

**Requirements:**
- Method nhận `case_id`, chuyển `Case.status → COMPLETED`, ghi 1
  `ReviewAction` (`UPLOAD_CASE`, `extracted_field_id = null`).
- Không yêu cầu confirm từng field trước đó (PROJECT_BRIEF.md §5 bước 7).

**Acceptance criteria:**
- [ ] Bấm Upload → `Case.status → COMPLETED`, đúng 1 `ReviewAction`
      (`UPLOAD_CASE`) được ghi.
- [ ] Upload khi case chưa `READY_FOR_REVIEW` → báo lỗi rõ ràng, không đổi
      status sai trạng thái.

**Tests required:** Unit test dùng fake repository cho cả 2 trường hợp.

**Do not do:** Không tạo bảng "kết quả cuối" riêng — theo DATA_MODEL.md §3,
giá trị cuối chính là `current_value` mới nhất của từng field.

**Dependencies:** M6-T2, M6-T3.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 3 (phần "Lưu kết quả cuối") và mục 5 (ví dụ JSON
ReviewAction UPLOAD_CASE), PROJECT_BRIEF.md mục 5 bước 7 trước khi làm. Mở
rộng app/domain/services/review_service.py: viết method nhận case_id, kiểm
tra case đang ở status READY_FOR_REVIEW (nếu không, báo lỗi rõ ràng, không đổi
status), chuyển Case.status sang COMPLETED, ghi 1 ReviewAction
(action_type=UPLOAD_CASE, extracted_field_id=null, previous_value=null,
new_value=null). KHÔNG tạo bảng hay entity "kết quả cuối" riêng - theo
DATA_MODEL.md, giá trị cuối chính là current_value mới nhất của từng
ExtractedField, xem lại được qua query case_id. Viết unit test dùng fake
repository: upload thành công khi case READY_FOR_REVIEW, upload thất bại khi
case chưa sẵn sàng.
```

---

### M6-T5 — api/review.py: PATCH field, POST upload

**Goal:** Endpoint sửa field và endpoint Upload.

**Files/modules:** `backend/app/api/review.py` (mở rộng).

**Requirements:**
- `PATCH /cases/{case_id}/fields/{field_id}` — sửa giá trị field, gọi
  `review_service.py` (M6-T3).
- `POST /cases/{case_id}/upload` — thực hiện Upload, gọi `review_service.py`
  (M6-T4).
- Giữ đúng shape response đã có từ M5-T2 nếu có phần trùng
  (DEVELOPMENT_RULES.md §9).

**Acceptance criteria:**
- [ ] Gọi PATCH sửa field thành công, trả `current_value` mới.
- [ ] Gọi POST upload thành công, trả `Case.status = COMPLETED`.

**Tests required:** API test cho cả 2 endpoint, bao gồm case lỗi (field
không tồn tại, case chưa sẵn sàng).

**Do not do:** Không viết business logic trong router.

**Dependencies:** M6-T3, M6-T4.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DEVELOPMENT_RULES.md mục 1 và mục 9 (giữ API compatibility) trước khi
làm. Mở rộng app/api/review.py: thêm endpoint PATCH
/cases/{case_id}/fields/{field_id} nhận giá trị mới, gọi review_service.py để
sửa field, trả về field đã cập nhật; thêm endpoint POST
/cases/{case_id}/upload gọi review_service.py để thực hiện Upload, trả về case
đã COMPLETED. Router chỉ nhận request -> gọi service -> trả response. Không
đổi shape response của endpoint GET /cases/{case_id}/review đã có từ trước.
Viết API test cho 2 endpoint mới, bao gồm trường hợp lỗi (field_id không tồn
tại, upload khi case chưa READY_FOR_REVIEW).
```

---

### M6-T6 — Frontend: sửa field UI

**Goal:** Cho phép chuyên viên sửa giá trị field ngay trên Review UI, lưu
ngay khi sửa.

**Files/modules:** `frontend/src/components/FieldItem/` (mở rộng).

**Requirements:**
- `FieldItem` cho phép nhập giá trị mới, gọi API PATCH (M6-T5) ngay khi sửa
  (không cần nút confirm riêng, theo PROJECT_BRIEF.md §5 bước 6).
- Hiển thị phản hồi thành công/lỗi khi sửa.

**Acceptance criteria:**
- [ ] Sửa giá trị field qua UI → lưu thành công, hiển thị giá trị mới.

**Tests required:** Không bắt buộc test tự động; kiểm tra thủ công.

**Do not do:** Không thêm bước confirm riêng cho từng field.

**Dependencies:** M6-T5, M5-T3.

**Ready-to-paste Codex prompt:**
```
Đọc docs/PROJECT_BRIEF.md mục 5 bước 6 trước khi làm. Mở rộng
frontend/src/components/FieldItem/: cho phép chuyên viên sửa giá trị field
(ví dụ input text hoặc inline edit), gọi API PATCH
/cases/{case_id}/fields/{field_id} thật ngay khi sửa xong (không cần nút
confirm riêng cho từng field - theo đúng PROJECT_BRIEF). Hiển thị rõ trạng
thái thành công/lỗi sau mỗi lần sửa.
```

---

### M6-T7 — Frontend: nút Upload + hiển thị trạng thái COMPLETED

**Goal:** Nút Upload toàn hồ sơ, hiển thị lại giá trị cuối sau khi hoàn tất.

**Files/modules:** `frontend/src/pages/ReviewPage.tsx` (mở rộng).

**Requirements:**
- Nút "Upload" gọi API POST upload (M6-T5), disable sau khi case đã
  `COMPLETED`.
- Sau khi `COMPLETED`, vẫn xem lại được danh sách field + giá trị cuối
  (`current_value`).

**Acceptance criteria:**
- [ ] Bấm Upload → case chuyển `COMPLETED`, nút Upload disable.
- [ ] Xem lại danh sách field sau khi `COMPLETED`, giá trị đúng
      `current_value` mới nhất.

**Tests required:** Không bắt buộc test tự động; kiểm tra thủ công theo
Acceptance criteria.

**Do not do:** Không xoá dữ liệu field sau khi Upload.

**Dependencies:** M6-T5, M5-T3.

**Ready-to-paste Codex prompt:**
```
Đọc docs/PROJECT_BRIEF.md mục 5 bước 7 và DATA_MODEL.md mục 3 (phần "Lưu kết quả
cuối") trước khi làm. Mở rộng frontend/src/pages/ReviewPage.tsx: thêm nút
"Upload" gọi API POST /cases/{case_id}/upload thật, disable nút này sau khi
case đã COMPLETED (tránh bấm lại). Sau khi COMPLETED, vẫn cho xem lại danh
sách field và giá trị current_value mới nhất (dùng lại API GET review đã có).
Không xoá hay ẩn dữ liệu field sau khi Upload.
```

---

## M7 — Polish + Demo

### M7-T1 — Frontend: loading/error state theo Case.status

**Goal:** Phản hồi rõ ràng cho người dùng ở mọi trạng thái chờ/lỗi.

**Files/modules:** trang liên quan (`CaseUploadPage.tsx`, `ReviewPage.tsx`).

**Requirements:**
- Hiển thị loading khi `status = PROCESSING` (polling đơn giản theo
  ARCHITECTURE.md §8).
- Hiển thị thông báo lỗi rõ ràng khi `status = FAILED`.

**Acceptance criteria:**
- [ ] Case đang `PROCESSING` → UI hiển thị trạng thái đang xử lý, không trắng
      trang hay treo im lặng.
- [ ] Case `FAILED` → UI hiển thị lỗi rõ ràng.

**Tests required:** Kiểm tra thủ công theo Acceptance criteria (có thể giả
lập `FAILED` bằng dữ liệu test).

**Do not do:** Không thêm WebSocket/real-time — vẫn dùng polling đơn giản
theo ARCHITECTURE.md §9.

**Dependencies:** M6-T7, M3-T5, M4-T5.

**Ready-to-paste Codex prompt:**
```
Đọc docs/ARCHITECTURE.md mục 8 (polling, không dùng WebSocket) và mục 9 trước khi
làm. Trong CaseUploadPage.tsx và ReviewPage.tsx, thêm xử lý hiển thị trạng
thái Case.status rõ ràng cho người dùng: khi PROCESSING, hiển thị loading/
trạng thái "đang xử lý", dùng polling đơn giản (gọi lại API định kỳ, không
dùng WebSocket) để biết khi nào chuyển sang READY_FOR_REVIEW; khi FAILED,
hiển thị thông báo lỗi rõ ràng thay vì trang trắng hoặc treo im lặng. Kiểm tra
thủ công cả 2 trạng thái.
```

---

### M7-T2 — Backend: xử lý lỗi → FAILED status (OCR & LLM)

**Goal:** Đảm bảo mọi lỗi OCR/LLM đều được bắt và chuyển case sang `FAILED`,
không để "treo".

**Files/modules:** `backend/app/domain/services/extraction_service.py` (rà
soát lại).

**Requirements:**
- Rà soát toàn bộ đường lỗi có thể xảy ra ở bước OCR (M3-T5) và LLM (M4-T5) —
  đảm bảo mọi exception đều dẫn tới `Case.status = FAILED` thay vì crash âm
  thầm hoặc để case treo ở `PROCESSING`.

**Acceptance criteria:**
- [ ] Giả lập lỗi OCR (ví dụ file hỏng) → case chuyển `FAILED`, không crash
      toàn app.
- [ ] Giả lập lỗi Gemini (hết retry) → case chuyển `FAILED`.

**Tests required:** Test bổ sung cho các đường lỗi chưa có test ở M3-T5/M4-T5.

**Do not do:** Không refactor lan man ngoài phạm vi xử lý lỗi
(DEVELOPMENT_RULES.md §7).

**Dependencies:** M3-T5, M4-T5.

**Ready-to-paste Codex prompt:**
```
Đọc docs/DATA_MODEL.md mục 3 (Case.status FAILED) và DEVELOPMENT_RULES.md mục 7
trước khi làm. Rà soát lại app/domain/services/extraction_service.py: đảm bảo
mọi exception có thể xảy ra ở bước gọi OCRProvider hoặc LLMProvider đều được
bắt (try/except) và dẫn tới Case.status chuyển sang FAILED, thay vì để
exception làm crash BackgroundTask âm thầm hoặc để case treo mãi ở
PROCESSING. Chỉ sửa phần xử lý lỗi liên quan, không refactor các phần khác
không liên quan tới task này. Bổ sung test cho các đường lỗi chưa có test:
OCR lỗi (ví dụ file không đọc được), LLM lỗi sau khi hết retry.
```

---

### M7-T3 — Rà soát checklist MVP Acceptance Criteria (task kiểm tra)

**Goal:** Xác nhận toàn bộ 9 mục ở PROJECT_BRIEF.md §8 đã đạt trước khi coi
MVP hoàn thành.

**Files/modules:** Không có file code cố định — task kiểm tra + có thể sửa
nhỏ nếu phát hiện thiếu sót.

**Requirements:**
- Chạy thử toàn bộ flow "upload → OCR → LLM extract → review/sửa → Upload"
  cho 1 hồ sơ, đối chiếu từng mục ở PROJECT_BRIEF.md §8.
- Nếu phát hiện mục nào chưa đạt, ghi rõ thiếu gì, đề xuất task bổ sung
  (không tự ý mở rộng scope).

**Acceptance criteria:**
- [ ] Toàn bộ 9 mục ở PROJECT_BRIEF.md §8 được đối chiếu, có kết quả rõ ràng
      (đạt/chưa đạt).

**Tests required:** Không phải test tự động — đây là kiểm tra checklist thủ
công/end-to-end.

**Do not do:** Không tự thêm tính năng mới nếu phát hiện "thiếu" — chỉ báo
lại và đề xuất, chờ xác nhận nếu cần mở rộng ngoài checklist đã có.

**Dependencies:** M6-T7, M7-T1, M7-T2.

**Ready-to-paste Codex prompt:**
```
Đọc docs/PROJECT_BRIEF.md mục 8 (MVP Acceptance Criteria) trước khi làm. Chạy thử
toàn bộ flow end-to-end cho 1 hồ sơ demo: tạo case, upload đủ 4 giấy tờ, chờ
OCR + LLM chạy xong, vào Review UI kiểm tra/sửa vài field, bấm Upload. Đối
chiếu kết quả với từng mục trong checklist ở PROJECT_BRIEF.md mục 8, ghi rõ
mục nào đạt, mục nào chưa đạt và vì sao. Nếu phát hiện thiếu sót, KHÔNG tự ý
thêm tính năng mới để "vá" - chỉ ghi lại rõ ràng và đề xuất hướng xử lý, chờ
xác nhận.
```

---

### M7-T4 — Chuẩn bị bộ dữ liệu demo

**Goal:** Có sẵn 1 bộ 4 giấy tờ mẫu chạy trọn vẹn được từ đầu, dùng cho demo.

**Files/modules:** thư mục dữ liệu mẫu (ví dụ `backend/tests/fixtures/demo/`
hoặc tương đương — không commit giấy tờ thật).

**Requirements:**
- Chuẩn bị 4 file mẫu (CCCD mặt trước/sau, giấy đề nghị vay vốn, hợp đồng lao
  động) — dùng dữ liệu giả/demo, không phải giấy tờ thật của người thật.
- Chạy thử trọn vẹn flow với bộ dữ liệu này, xác nhận không cần can thiệp thủ
  công vào DB.

**Acceptance criteria:**
- [ ] Chạy trọn vẹn flow với bộ dữ liệu demo, từ Upload tới Upload (lưu),
      không lỗi.

**Tests required:** Không phải test tự động — đây là chuẩn bị dữ liệu +
chạy thử thủ công.

**Do not do:** Không dùng giấy tờ thật của người thật làm dữ liệu demo.

**Dependencies:** M7-T3.

**Ready-to-paste Codex prompt:**
```
Chuẩn bị 1 bộ 4 file mẫu (CCCD mặt trước, CCCD mặt sau, giấy đề nghị vay vốn,
hợp đồng lao động) dùng dữ liệu giả/demo tự tạo, KHÔNG dùng giấy tờ thật của
người thật. Chạy thử trọn vẹn flow end-to-end với bộ dữ liệu này (upload toàn
bộ 4 giấy tờ -> chờ OCR + LLM -> review/sửa vài field -> Upload), xác nhận
chạy được từ đầu đến cuối mà không cần can thiệp thủ công vào database. Ghi
lại vị trí lưu bộ dữ liệu demo này để dùng lại cho các lần demo sau.
```

---

- Last updated: <để tôi tự điền ngày>
- Downstream docs cần rà lại nếu file này đổi: (không có — đây là file cuối
  cùng trong chuỗi 6 tài liệu)
