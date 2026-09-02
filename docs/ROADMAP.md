# ROADMAP.md

> Dựa trên PROJECT_BRIEF.md + ARCHITECTURE.md + DATA_MODEL.md +
> DEVELOPMENT_RULES.md + AGENTS.md (đã approved). Chia theo **vertical
> milestone** — mỗi milestone chạm đủ backend + frontend (khi cần) để **demo
> được** một lát cắt thật của flow, không tách kiểu "toàn bộ backend trước,
> toàn bộ frontend sau".

## Tổng quan các milestone

| Milestone | Tên | Demo được gì |
|---|---|---|
| M0 | Skeleton + tooling | App chạy được (rỗng), lint/test/typecheck có sẵn |
| M1 | Case + Upload | Tạo case, upload đủ 4 giấy tờ, thấy trong DB |
| M2 | Viewer + static highlight | Xem tài liệu, highlight 1 vùng bbox hard-code |
| M3 | OCR + persist | Upload → OCR thật chạy → OCRBlock lưu vào DB |
| M4 | LLM extraction + source_ids | OCRBlock → Gemini → ExtractedField + FieldSource lưu vào DB |
| M5 | Dynamic evidence highlight | Click field thật → viewer tự mở đúng doc/trang/vùng |
| M6 | Review / edit / confirm | Sửa field, bấm Upload, lưu ReviewAction, Case → COMPLETED |
| M7 | Polish + demo | Xử lý lỗi, trạng thái loading/failed, demo mượt end-to-end |

Thứ tự này bám sát core workflow ở PROJECT_BRIEF (Upload → OCR → LLM extract →
Backend Mapping → Review UI → Sửa → Upload) và tách theo đúng ranh giới module ở
ARCHITECTURE.md — không đổi nội dung 2 file đó.

---

## M0 — Skeleton + Tooling

**Goal:** Có bộ khung project chạy được, đúng folder structure ở
ARCHITECTURE.md §5, có sẵn lint/test/typecheck để mọi milestone sau tuân theo
DEVELOPMENT_RULES.md §11 ngay từ đầu.

**User-visible result:** Chạy `backend` (FastAPI, endpoint `/health` trả OK) và
`frontend` (React, trang trắng "Hello") cùng lúc, không có tính năng nghiệp vụ.

**Tasks:**
- Tạo folder structure backend (`api/`, `domain/models.py`, `domain/services/`,
  `domain/ports/`, `infra/ocr/`, `infra/llm/`, `infra/db/`, `tests/`) và
  frontend (`pages/`, `components/`, `api/`, `types/`) đúng ARCHITECTURE.md §5.
- Cấu hình FastAPI app tối thiểu + 1 endpoint `/health`.
- Cấu hình Vite + React + TypeScript (strict mode) + PDF.js dependency (chưa dùng
  logic, chỉ cài đặt).
- Cấu hình SQLite + SQLAlchemy 2.x connection/session (chưa có bảng).
- Cấu hình lint (`ruff`/`flake8`, `eslint`), typecheck (`mypy`/Pydantic strict,
  `tsc --noEmit`), test runner (`pytest`, `vitest`).
- Tạo `.env.example` + `.gitignore` (không commit `.env` thật).

**Dependencies:** Không có (milestone đầu tiên).

**Acceptance criteria:**
- [ ] `GET /health` trả 200.
- [ ] Frontend build và chạy dev server không lỗi.
- [ ] `ruff`/`eslint`/`mypy`/`tsc --noEmit`/`vitest run` chạy được, pass trên codebase rỗng.

**Tests:** Test cho `/health` (happy path, dùng FastAPI TestClient).

**Definition of Done:** Cả backend và frontend chạy local được, toàn bộ lệnh
lint/test/typecheck ở DEVELOPMENT_RULES.md §11 chạy pass.

**Out of scope:** Bất kỳ logic nghiệp vụ nào (case, document, OCR, LLM).

---

## M1 — Case + Upload

**Goal:** Chuyên viên tạo được 1 case và upload đủ 4 loại giấy tờ bắt buộc,
dữ liệu lưu đúng theo DATA_MODEL.md (bảng `Case`, `Document`).

**User-visible result:** Trên UI, tạo case mới, upload lần lượt 4 file (CCCD
mặt trước/sau, giấy đề nghị vay vốn, hợp đồng lao động), thấy case chuyển
`status = UPLOADING → PROCESSING` khi đủ 4 loại (OCR/LLM thật chưa chạy ở
milestone này — có thể để `PROCESSING` là trạng thái "chờ", chưa cần xử lý
xong).

**Tasks:**
- Backend: `case_service.py` (tạo case, đổi status khi đủ document) theo
  DEVELOPMENT_RULES.md §2 (chỉ lo vòng đời Case).
- Backend: bảng `Case`, `Document` (SQLite repository trong `infra/db/`), ràng
  buộc `unique(case_id, document_type)` theo DATA_MODEL.md §4.2.
- Backend: `api/cases.py`, `api/documents.py` — router mỏng, gọi service,
  không chứa logic (DEVELOPMENT_RULES.md §1).
- Backend: lưu file vật lý lên local disk, `file_path` lưu trong `Document`.
- Frontend: `CaseUploadPage.tsx` — form tạo case + upload 4 loại giấy tờ, gọi
  API thật (không mock).

**Dependencies:** M0 (skeleton, DB connection).

**Acceptance criteria:**
- [ ] Tạo case mới thành công, trả về `id`, `status = UPLOADING`.
- [ ] Upload đủ 4 loại document hợp lệ → status chuyển `PROCESSING`.
- [ ] Upload thiếu loại hoặc trùng loại (`document_type` đã tồn tại trong case)
      → lỗi rõ ràng, không tạo dữ liệu sai.
- [ ] Dữ liệu `Case`, `Document` đúng field bắt buộc ở DATA_MODEL.md §4.1, §4.2.

**Tests:** Unit test `case_service.py` (dùng fake repository — theo
DEVELOPMENT_RULES.md §8, không phụ thuộc DB thật cho unit test logic). API
test happy path cho `/cases`, `/documents` bằng FastAPI TestClient.

**Definition of Done:** Lint/test/typecheck pass. Có thể tạo case + upload đủ
4 giấy tờ end-to-end qua UI thật (không qua Postman/curl).

**Out of scope:** OCR, LLM, review UI, document viewer.

---

## M2 — Viewer + Static Highlight

**Goal:** Xây xong phần khó về mặt kỹ thuật frontend (PDF.js render + vẽ
overlay theo bbox chuẩn hoá 0–1) trước khi có dữ liệu OCR thật, để tách rủi ro
kỹ thuật ra khỏi rủi ro dữ liệu.

**User-visible result:** Mở 1 document đã upload ở M1, xem được trang PDF/ảnh,
và thấy 1 ô highlight xuất hiện đúng vị trí tương ứng với bbox **hard-code**
(chưa lấy từ OCR thật).

**Tasks:**
- Frontend: `DocumentViewer/` component — render PDF.js, hỗ trợ chuyển trang.
- Frontend: logic vẽ overlay highlight từ toạ độ chuẩn hoá (0–1) sang toạ độ
  pixel thực tế trên canvas, đúng như quyết định ở DATA_MODEL.md §4.3 (không
  dùng pixel tuyệt đối vì zoom thay đổi).
- Frontend: test thủ công với vài giá trị `bbox_x/y/width/height` hard-code
  để xác nhận highlight đúng vị trí ở nhiều mức zoom.
- Backend: endpoint tối thiểu trả file document để frontend load (nếu chưa có
  từ M1).

**Dependencies:** M1 (đã có document để mở).

**Acceptance criteria:**
- [ ] Mở đúng document đã upload, xem được đúng trang.
- [ ] Overlay highlight hiển thị đúng vị trí tương ứng bbox hard-code, đúng ở
      ít nhất 2 mức zoom khác nhau.

**Tests:** Test frontend cho hàm chuyển đổi toạ độ chuẩn hoá → pixel (unit
test thuần, không cần OCR thật).

**Definition of Done:** Lint/test/typecheck pass. Demo được: mở document, thấy
1 ô highlight đúng chỗ, zoom in/out overlay vẫn đúng.

**Out of scope:** Lấy bbox từ OCR thật, click field để highlight (đó là M5).

---

## M3 — OCR + Persist

**Goal:** Chạy OCR thật (PaddleOCR detect + VietOCR recognize) trên document
đã upload, lưu kết quả thành `OCRBlock` — nguồn sự thật duy nhất cho mọi bbox
(DATA_MODEL.md §1).

**User-visible result:** Sau khi upload đủ 4 giấy tờ, chạy nền OCR (qua
`BackgroundTasks` theo ARCHITECTURE.md §8), Document chuyển `ocr_status:
PENDING → DONE`, và có thể xem danh sách `OCRBlock` (text + bbox + confidence)
qua API hoặc log để kiểm tra bằng mắt.

**Tasks:**
- Backend: `infra/ocr/local_ocr_adapter.py` implement `OCRProvider` port —
  gọi PaddleOCR (detect) rồi VietOCR (recognize), convert kết quả thành
  `OCRBlock` nội bộ. Model weights load 1 lần lúc khởi động app
  (DEVELOPMENT_RULES.md §14), không hard-code đường dẫn model.
- Backend: repository lưu `OCRBlock` vào SQLite.
- Backend: `extraction_service.py` (chỉ điều phối bước OCR ở milestone này) —
  gọi OCR qua port, lưu `OCRBlock`, cập nhật `Document.ocr_status`, kích hoạt
  từ `BackgroundTasks` sau khi đủ 4 document.
- **Thử nghiệm sớm với chữ viết tay thật:** theo lưu ý rủi ro ở
  ARCHITECTURE.md §1 — chạy thử OCR trên vài mẫu giấy đề nghị vay vốn có chữ
  viết tay thật (hoặc mẫu gần giống), đánh giá độ chính xác trước khi đi tiếp
  sang M4. Nếu chưa đạt, ghi chú lại hướng fine-tune VietOCR như một task
  riêng — không tự ý đổi provider giữa milestone (theo DEVELOPMENT_RULES.md
  §12, phải dừng lại và báo nếu phát hiện provider không khả thi).
- Backend: adapter test dùng fixture ảnh mẫu cố định (DEVELOPMENT_RULES.md §8).

**Dependencies:** M1 (có document đã upload).

**Acceptance criteria:**
- [ ] Sau upload đủ 4 giấy tờ, OCR tự chạy nền, không chặn request upload.
- [ ] Mỗi `OCRBlock` có đủ text/page/bbox/confidence/source_id (chính là
      `OCRBlock.id`) theo DATA_MODEL.md §4.3.
- [ ] `Document.ocr_status` chuyển đúng `PENDING → DONE` hoặc `→ FAILED` nếu
      lỗi.
- [ ] Đã thử nghiệm OCR trên chữ viết tay thật/gần thật, có ghi nhận kết quả
      (đạt hoặc cần fine-tune thêm).

**Tests:** Unit test `extraction_service.py` (phần điều phối OCR) dùng fake
`OCRProvider`. Adapter test với fixture ảnh mẫu cố định cho
`local_ocr_adapter.py`.

**Definition of Done:** Lint/test/typecheck pass. Demo được: upload đủ giấy
tờ → sau vài giây/chục giây thấy `OCRBlock` xuất hiện trong DB với dữ liệu hợp
lý.

**Out of scope:** LLM extraction, hiển thị OCR lên UI (M2 đã xong phần
viewer, nhưng nối OCR thật vào viewer là việc của M5).

---

## M4 — LLM Extraction + source_ids

**Goal:** Gọi Gemini để trích xuất `ExtractedField` từ `OCRBlock`, map
`source_ids` sang `FieldSource`, đúng ràng buộc "LLM không được tự tạo bbox"
(PROJECT_BRIEF.md §3, §5).

**User-visible result:** Sau khi OCR xong (`ocr_status = DONE` cho cả 4
document), hệ thống tự gọi LLM, case chuyển `PROCESSING → READY_FOR_REVIEW`,
và có thể xem qua API danh sách `ExtractedField` kèm `sources` (như ví dụ JSON
ở DATA_MODEL.md §5).

**Tasks:**
- Trước khi code M4, phải có `docs/EXTRACTION_SCHEMA.md` chốt danh sách field MVP, field type và document source dự kiến. Đây là input cho prompt/schema LLM; không để Codex tự invent field_code trong lúc code.
- Mở rộng local OCR adapter bằng template-assisted OMR cho checkbox của
  `LOAN_APPLICATION`: hỗ trợ V1 không marker và V2 có marker; căn chỉnh trang,
  tinh chỉnh ROI cục bộ, tạo `CHECKBOX_SELECTION` block khi đủ chắc chắn và
  fail closed khi uncertain/conflict. Dùng OpenCV/NumPy đã có, không thêm
  dependency.
- Mở rộng `OCRProvider.extract` để orchestration truyền `document_type`; không
  đoán loại tài liệu từ filename và không bật OMR cho ba loại tài liệu khác.
- Mở rộng `OCRBlock` bằng `block_kind` để phân biệt text và checkbox evidence;
  không tạo hệ thống bbox/evidence song song.
- `LLMProvider` nhận document-aware input (`document_id`, `document_type`,
  `blocks`) thay vì danh sách block bị mất ngữ cảnh nguồn.
- Backend: `infra/llm/gemini_extractor.py` implement `LLMProvider` port — gọi
  model `gemini-3.7-flash` qua `google-genai==2.21.0` với structured output
  schema (`field_code`, `value`, `source_ids`), validate bằng Pydantic. Có
  retry/backoff giới hạn số lần khi gặp 429 (DEVELOPMENT_RULES.md §14).
- Backend: validate nghiêm ở tầng domain — chặn nếu LLM trả về `source_id`
  không tồn tại trong `OCRBlock` đã lưu (đúng nguyên tắc "LLM không tự tạo
  bbox").
- Backend: mở rộng `extraction_service.py` — sau khi có đủ `OCRBlock` của cả
  4 document, gọi LLM, tạo `ExtractedField` + `FieldSource`, chuyển
  `Case.status → READY_FOR_REVIEW`.
- Backend: repository lưu `ExtractedField`, `FieldSource`.
- Backend: adapter test cho `gemini_extractor.py` dùng dữ liệu mẫu cố định,
  không bắt buộc gọi Gemini thật trong test tự động (DEVELOPMENT_RULES.md §8).

**Dependencies:** M3 (cần `OCRBlock` làm input cho LLM), catalog Core 40 và
template checkbox V1 đã được đăng ký.

**Acceptance criteria:**
- [ ] Sau khi OCR xong cả 4 document, LLM tự chạy, tạo được `ExtractedField`
      cho các field nghiệp vụ chính (ví dụ `ho_ten`, `so_cccd`, `ngay_sinh`).
- [ ] Checkbox của synthetic loan-application PDF được đọc thành evidence có
      source ID/bbox; input uncertain/conflict không bị tự chọn sai.
- [ ] Gemini nhận biết được source document của từng block mà không query
      repository từ adapter.
- [ ] Field có value phải có ít nhất 1 `FieldSource` hợp lệ; field không tìm thấy được lưu với `value = null`, không có source. Không có `source_id` bịa.
- [ ] `Case.status` chuyển đúng `PROCESSING → READY_FOR_REVIEW`, hoặc `→
      FAILED` nếu Gemini lỗi sau khi hết số lần retry.
- [ ] Retry/backoff hoạt động đúng khi giả lập lỗi 429 (test bằng mock).

**Tests:** Giữ bộ test rủi ro cao, tránh ma trận biến thể trùng lặp: unit test
OMR cho checked/unchecked/uncertain + conflict; một fixture synthetic PDF kiểm
tra căn chỉnh/checkbox/bbox; unit test điều phối dùng fake `LLMProvider` cho
case missing và source ID không hợp lệ; adapter test Gemini fixture cố định +
mock retry/backoff. Không gọi Gemini thật trong test tự động.

**Definition of Done:** Lint/test/typecheck pass. Demo được: từ lúc upload
xong tới lúc `READY_FOR_REVIEW`, dữ liệu `ExtractedField`/`FieldSource` đúng
và truy ngược được `OCRBlock` gốc.

**Out of scope:** Hiển thị lên Review UI, sửa field (đó là M6).

---

## M5 — Dynamic Evidence Highlight

**Goal:** Nối Review data thật (từ M4) với Document Viewer (từ M2) — đúng
tính năng lõi ở PROJECT_BRIEF: click 1 field → tự mở đúng document/trang/vùng.

**User-visible result:** Trang Review hiển thị danh sách field thật (từ
`ExtractedField`), click vào 1 field → Document Viewer tự chuyển sang đúng
document, đúng trang, và highlight đúng vùng bbox (lấy từ `FieldSource` →
`OCRBlock` thật, không còn hard-code như M2).

**Tasks:**
- Backend: `review_service.py` (khởi tạo, chỉ phần đọc dữ liệu ở milestone
  này) — trả danh sách field kèm `sources` (document_id, page_number, bbox)
  cho 1 case.
- Backend: `api/review.py` — endpoint lấy dữ liệu review cho 1 case.
- Frontend: `FieldList/`, `FieldItem/` components — hiển thị field thật.
- Frontend: nối sự kiện click field → điều khiển `DocumentViewer` (đã xây ở
  M2) mở đúng document/trang, vẽ overlay từ bbox thật lấy qua API.
- Frontend: xử lý field có nhiều `sources` (nhiều OCRBlock) — highlight tất cả
  vùng liên quan theo DATA_MODEL.md §2 (field có thể có nhiều bằng chứng).

**Dependencies:** M2 (viewer), M4 (dữ liệu field + source thật).

**Acceptance criteria:**
- [ ] Trang Review hiển thị đúng danh sách field của case (chỉ khi
      `status = READY_FOR_REVIEW`).
- [ ] Click 1 field → viewer mở đúng document, đúng trang, highlight đúng
      vùng bbox thật.
- [ ] Field có nhiều nguồn OCR (nhiều `FieldSource`) → tất cả vùng liên quan
      được highlight.

**Tests:** Unit test `review_service.py` (phần đọc dữ liệu) dùng fake
repository. API test cho `/review` endpoint. Frontend: test tích hợp
click-field-to-highlight nếu framework test hỗ trợ, hoặc test thủ công có ghi
lại kịch bản kiểm tra.

**Definition of Done:** Lint/test/typecheck pass. Demo được: mở case đã
`READY_FOR_REVIEW`, click qua vài field khác nhau, xác nhận highlight đúng vị
trí trên tài liệu gốc.

**Out of scope:** Sửa giá trị field, nút Upload (đó là M6).

---

## M6 — Review / Edit / Confirm

**Goal:** Hoàn thiện toàn bộ vòng đời chính: chuyên viên sửa field, bấm
Upload để lưu toàn bộ hồ sơ một lần, đúng PROJECT_BRIEF §5 bước 6–7 và
DATA_MODEL.md §3 (`ReviewAction`, `Case.status → COMPLETED`).

**User-visible result:** Trên Review UI, sửa giá trị 1 hoặc nhiều field, bấm
nút "Upload" — toàn bộ hồ sơ được lưu trong 1 thao tác (không cần confirm
từng field riêng lẻ), case chuyển `COMPLETED`, có thể xem lại giá trị cuối +
lịch sử sửa.

**Tasks:**
- Backend: mở rộng `review_service.py` — nhận sửa field
  (`current_value` mới), ghi 1 `ReviewAction` (`EDIT_FIELD`,
  `previous_value`/`new_value`) mỗi lần sửa, **không** tạo `ExtractedField`
  mới (DATA_MODEL.md §3).
- Backend: xử lý hành động Upload — chuyển `Case.status → COMPLETED`, ghi 1
  `ReviewAction` loại `UPLOAD_CASE` (`extracted_field_id = null`).
- Backend: `api/review.py` — endpoint sửa field (PATCH) và endpoint Upload
  (POST), giữ đúng API compatibility nếu đụng tới field đã có từ M5
  (DEVELOPMENT_RULES.md §9).
- Frontend: `FieldItem/` cho phép sửa giá trị, lưu qua API ngay khi sửa (theo
  đúng PROJECT_BRIEF: không cần confirm từng field).
- Frontend: nút "Upload" toàn hồ sơ, disable sau khi case đã `COMPLETED`.
- Frontend: hiển thị lại được giá trị cuối (`current_value`) sau khi
  `COMPLETED`, đúng như DATA_MODEL.md §3 mô tả (query theo `case_id`).

**Dependencies:** M5 (đã có Review UI + dữ liệu field thật để sửa).

**Acceptance criteria:**
- [ ] Sửa 1 field → `current_value` cập nhật, `ReviewAction` (`EDIT_FIELD`)
      được ghi đúng `previous_value`/`new_value`.
- [ ] Sửa nhiều lần cùng 1 field → mỗi lần sửa tạo 1 `ReviewAction` mới, không
      tạo `ExtractedField` mới.
- [ ] Bấm Upload → `Case.status → COMPLETED`, 1 `ReviewAction`
      (`UPLOAD_CASE`) được ghi, không cần xác nhận từng field.
- [ ] Xem lại được giá trị cuối cùng của mọi field thuộc case sau khi
      `COMPLETED`.

**Tests:** Unit test `review_service.py` cho cả 2 luồng (edit field, upload
case) dùng fake repository. API test cho endpoint sửa field và endpoint
Upload, bao gồm case sửa nhiều lần liên tiếp.

**Definition of Done:** Lint/test/typecheck pass. Demo được: chạy trọn vẹn
"upload → OCR → LLM extract → review/sửa → Upload (lưu)" cho 1 hồ sơ, đúng
MVP Acceptance Criteria cuối cùng ở PROJECT_BRIEF.md §8.

**Out of scope:** Xử lý lỗi tinh tế (loading state đẹp, thông báo lỗi rõ ràng
cho người dùng cuối) — đó là M7.

---

## M7 — Polish + Demo

**Goal:** Làm mượt trải nghiệm demo end-to-end, xử lý các trạng thái lỗi
(`FAILED`) và loading một cách rõ ràng, không thêm tính năng mới.

**User-visible result:** Toàn bộ flow chạy mượt từ đầu đến cuối cho 1 hồ sơ
demo, có phản hồi rõ ràng ở mọi bước chờ (OCR đang chạy, LLM đang chạy), và
báo lỗi dễ hiểu nếu OCR/LLM thất bại.

**Tasks:**
- Frontend: hiển thị trạng thái `Case.status` rõ ràng (loading spinner khi
  `PROCESSING`, thông báo lỗi khi `FAILED`), polling đơn giản theo
  ARCHITECTURE.md §8.
- Backend: đảm bảo mọi lỗi ở OCR/LLM đều được bắt và chuyển `Case.status →
  FAILED` thay vì để case "treo" (DATA_MODEL.md §3).
- Rà lại toàn bộ acceptance criteria ở PROJECT_BRIEF.md §8 — checklist từng
  mục.
- Dọn lại code theo DEVELOPMENT_RULES.md (không giant file, không dependency
  thừa, không business logic lạc trong router) — chỉ trong phạm vi code đã
  viết ở M0–M6, không refactor lan man.
- Chuẩn bị 1 bộ dữ liệu demo (4 giấy tờ mẫu) chạy trọn vẹn được từ đầu.

**Dependencies:** M6 (toàn bộ flow chính đã hoàn thiện).

**Acceptance criteria:**
- [ ] Toàn bộ 9 mục ở PROJECT_BRIEF.md §8 (MVP Acceptance Criteria) đều pass.
- [ ] Case chuyển `FAILED` đúng cách khi giả lập lỗi OCR hoặc lỗi Gemini, UI
      hiển thị thông báo lỗi thay vì treo im lặng.
- [ ] Chạy trọn vẹn 1 hồ sơ demo từ Upload tới Upload (lưu) không cần can
      thiệp thủ công vào DB.

**Tests:** Test lại toàn bộ regression suite từ M0–M6 vẫn pass. Thêm test cho
đường lỗi (`FAILED` path) nếu chưa có ở M3/M4.

**Definition of Done:** Lint/test/typecheck pass. Demo trực tiếp được toàn bộ
flow cho ít nhất 1 hồ sơ, không lỗi, không cần dev can thiệp giữa chừng.

**Out of scope:** Mọi hạng mục ở PROJECT_BRIEF.md §9 (Future Scope) —
cross-document validation, scoring, fraud detection, BPM thật, microservices,
đa provider, enterprise security.

---

- Last updated: <để tôi tự điền ngày>
- Downstream docs cần rà lại nếu file này đổi: FEATURE_BACKLOG.md
