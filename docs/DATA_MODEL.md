# DATA_MODEL.md

> Dựa trên PROJECT_BRIEF.md + ARCHITECTURE.md (đã approved). Tài liệu này mô tả
> cấu trúc dữ liệu ở mức khái niệm (bảng, quan hệ, vòng đời), không viết code ORM.

## 1. Tổng quan các entity

| Entity | Vai trò (responsibility) |
|---|---|
| **Case** | Đại diện cho 1 hồ sơ vay từ lương. Là "gốc" gắn kết mọi thứ khác lại: document, field, action. |
| **Document** | 1 file giấy tờ đã upload, thuộc 1 trong 4 loại bắt buộc, gắn với 1 Case. |
| **OCRBlock** | 1 khối chữ được OCR phát hiện + đọc ra từ 1 Document. Là **nguồn sự thật duy nhất** cho mọi bounding box. |
| **ExtractedField** | 1 trường dữ liệu nghiệp vụ (ví dụ: họ tên, số CCCD...) mà LLM trích xuất được cho 1 Case. |
| **FieldSource** | Liên kết 1 ExtractedField với 1 (hoặc nhiều) OCRBlock — chính là kết quả của bước "backend map source_ids → bounding box". |
| **ReviewAction** | Nhật ký (audit log) các hành động chuyên viên thực hiện: sửa field, bấm Upload. |

## 2. Quan hệ (relationships)

```
Case (1) ───< (4, đúng loại) Document
Document (1) ───< (N) OCRBlock
Case (1) ───< (N) ExtractedField
ExtractedField (1) ───< (N) FieldSource >─── (1) OCRBlock
Case (1) ───< (N) ReviewAction >─── (0..1) ExtractedField
```

Giải thích các điểm dễ nhầm:

- **ExtractedField thuộc về Case, không thuộc về 1 Document cụ thể** — vì một
  trường dữ liệu (ví dụ họ tên) có thể được LLM tổng hợp từ nhiều tài liệu khác
  nhau trong cùng hồ sơ (CCCD + hợp đồng lao động).
- **FieldSource là bảng nối nhiều-nhiều** giữa ExtractedField và OCRBlock, vì
  `source_ids` mà LLM trả về là một **danh sách**, không phải 1 giá trị — một
  field có thể có nhiều bằng chứng (nhiều vùng OCR) hỗ trợ.
- **ReviewAction có thể không gắn với field cụ thể nào** — vì hành động "bấm
  Upload" là hành động ở cấp độ Case, không phải ở cấp độ 1 field.

## 3. Vòng đời (lifecycle)

**Case.status** (enum):

| Giá trị | Ý nghĩa |
|---|---|
| `UPLOADING` | Đã tạo case, đang chờ đủ 4 loại giấy tờ. |
| `PROCESSING` | Đã đủ 4 giấy tờ, đang chạy OCR + LLM ở nền (BackgroundTasks). |
| `READY_FOR_REVIEW` | OCR + LLM xong, ExtractedField/FieldSource đã có dữ liệu, chờ chuyên viên xem/sửa. |
| `COMPLETED` | Chuyên viên đã bấm Upload — dữ liệu cuối đã được lưu. |
| `FAILED` | OCR hoặc LLM lỗi giữa chừng (để tránh case bị "treo" không rõ trạng thái). |

Chuyển trạng thái: `UPLOADING → PROCESSING → READY_FOR_REVIEW → COMPLETED`, hoặc
rẽ sang `FAILED` nếu bước OCR/LLM gặp lỗi ở `PROCESSING`.

**Document.ocr_status** (enum): `PENDING → DONE` hoặc `PENDING → FAILED`.

**OCRBlock**: được tạo 1 lần duy nhất khi OCR chạy xong cho 1 Document, sau đó
**bất biến (immutable)** — không entity nào khác được sửa bbox của nó.

**ExtractedField**: được tạo 1 lần khi LLM extraction chạy xong (giá trị ban đầu
= `original_value`). Sau đó `current_value` có thể được chuyên viên sửa nhiều
lần trong lúc review — mỗi lần sửa tạo thêm 1 dòng `ReviewAction` để lưu vết,
không tạo `ExtractedField` mới.

**FieldSource**: được tạo cùng lúc với `ExtractedField` (kết quả bước mapping),
sau đó bất biến.

**"Lưu kết quả cuối"**: theo đúng lưu ý của bạn, MVP **không có bảng kết quả cuối
riêng** — khi chuyên viên bấm Upload, hệ thống chỉ cần chuyển `Case.status` thành
`COMPLETED` và ghi 1 `ReviewAction` loại `UPLOAD_CASE`. Giá trị cuối cùng của hồ
sơ chính là `current_value` mới nhất của từng `ExtractedField` thuộc case đó —
xem lại được bất cứ lúc nào bằng cách query theo `case_id`.

## 4. Chi tiết từng bảng

### 4.1 Case

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| id | string (UUID) | ✔ | Khoá chính |
| status | enum `CaseStatus` | ✔ | Xem mục 3 |
| created_at | datetime | ✔ | |
| updated_at | datetime | ✔ | Cập nhật mỗi khi status đổi |

### 4.2 Document

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| id | string (UUID) | ✔ | Khoá chính |
| case_id | FK → Case.id | ✔ | |
| document_type | enum `DocumentType` | ✔ | `CCCD_FRONT`, `CCCD_BACK`, `LOAN_APPLICATION`, `LABOR_CONTRACT` |
| file_path | string | ✔ | Đường dẫn file trên local disk (theo ARCHITECTURE.md — chưa dùng cloud storage) |
| page_count | integer | ✔ | Số trang (ảnh = 1, PDF nhiều trang có thể > 1) |
| ocr_status | enum `DocumentOcrStatus` | ✔ | `PENDING`, `DONE`, `FAILED` |
| uploaded_at | datetime | ✔ | |

Ràng buộc: **unique(case_id, document_type)** — 1 case không thể có 2 document
cùng loại (nếu chuyên viên upload lại, xử lý thay thế thuộc về logic ứng dụng,
không phải phạm vi DATA_MODEL).

### 4.3 OCRBlock

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| id | string (UUID) | ✔ | Khoá chính — **đây chính là `source_id`** nhắc tới xuyên suốt PROJECT_BRIEF/ARCHITECTURE. Hệ thống tự sinh, không dùng ID nội bộ của PaddleOCR. |
| document_id | FK → Document.id | ✔ | |
| page_number | integer | ✔ | Đánh số từ 1 |
| text | string | ✔ | Nội dung chữ do VietOCR nhận dạng |
| bbox_x, bbox_y, bbox_width, bbox_height | float (0.0–1.0) | ✔ | Toạ độ **chuẩn hoá** theo tỉ lệ trang (không dùng pixel tuyệt đối) — để hiển thị đúng dù PDF.js render ở độ phóng to/thu nhỏ nào. |
| confidence | float (0.0–1.0) | ✔ | Độ tin cậy do OCR trả về |
| created_at | datetime | ✔ | |

> **Quyết định:** dùng bbox chuẩn hoá theo tỉ lệ (0–1) thay vì toạ độ pixel tuyệt
> đối, vì frontend (PDF.js) có thể render trang ở nhiều mức zoom khác nhau — toạ
> độ tỉ lệ giúp tính lại vị trí highlight chính xác ở bất kỳ kích thước hiển thị
> nào mà không cần lưu thêm thông tin về độ phân giải gốc.

### 4.4 ExtractedField

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| id | string (UUID) | ✔ | Khoá chính |
| case_id | FK → Case.id | ✔ | |
| field_code | string | ✔ | Mã trường nghiệp vụ. Danh mục field MVP được chốt trong `EXTRACTION_SCHEMA.md`, không invent field_code trong code. |
| original_value | string (nullable) | ✗ | Giá trị LLM trích xuất ban đầu — **bất biến**. Null khi field không tìm thấy trong tài liệu. |
| current_value | string (nullable) | ✗ | Giá trị hiện tại — mặc định = original_value; chuyên viên có thể nhập/sửa trong Review UI. |
| created_at | datetime | ✔ | |
| updated_at | datetime | ✔ | Cập nhật mỗi khi current_value đổi |

### 4.5 FieldSource

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| id | string (UUID) | ✔ | Khoá chính |
| extracted_field_id | FK → ExtractedField.id | ✔ | |
| ocr_block_id | FK → OCRBlock.id | ✔ | |

Không có thêm field nào khác — đây thuần tuý là bảng nối, thể hiện "field này
được LLM lấy căn cứ từ (những) OCRBlock nào". Field có `original_value = null` có thể
không có `FieldSource`; field có value do LLM trả về phải có ít nhất một `FieldSource` hợp lệ.

### 4.6 ReviewAction

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| id | string (UUID) | ✔ | Khoá chính |
| case_id | FK → Case.id | ✔ | Luôn có, kể cả hành động không gắn field cụ thể |
| extracted_field_id | FK → ExtractedField.id | ✗ (nullable) | Null khi action_type = `UPLOAD_CASE` |
| action_type | enum `ReviewActionType` | ✔ | `EDIT_FIELD`, `UPLOAD_CASE` |
| previous_value | string | ✗ (nullable) | Chỉ có khi action_type = `EDIT_FIELD` |
| new_value | string | ✗ (nullable) | Chỉ có khi action_type = `EDIT_FIELD` |
| created_at | datetime | ✔ | |

## 5. Ví dụ JSON

**OCRBlock** (1 khối chữ được OCR):

```json
{
  "id": "ocr_9f1a",
  "document_id": "doc_cccd_front",
  "page_number": 1,
  "text": "NGUYEN VAN A",
  "bbox_x": 0.12,
  "bbox_y": 0.34,
  "bbox_width": 0.30,
  "bbox_height": 0.04,
  "confidence": 0.97
}
```

**ExtractedField kèm nguồn** (dữ liệu trả cho Review UI khi hiển thị 1 field):

```json
{
  "id": "field_ho_ten",
  "case_id": "case_001",
  "field_code": "ho_ten",
  "original_value": "NGUYEN VAN A",
  "current_value": "NGUYEN VAN A",
  "sources": [
    { "ocr_block_id": "ocr_9f1a", "document_id": "doc_cccd_front", "page_number": 1 }
  ]
}
```

**ReviewAction** (chuyên viên sửa 1 field):

```json
{
  "id": "action_001",
  "case_id": "case_001",
  "extracted_field_id": "field_ho_ten",
  "action_type": "EDIT_FIELD",
  "previous_value": "NGUYEN VAN A",
  "new_value": "Nguyễn Văn A",
  "created_at": "2026-09-01T10:15:00Z"
}
```

**ReviewAction** (chuyên viên bấm Upload để lưu toàn bộ hồ sơ):

```json
{
  "id": "action_002",
  "case_id": "case_001",
  "extracted_field_id": null,
  "action_type": "UPLOAD_CASE",
  "previous_value": null,
  "new_value": null,
  "created_at": "2026-09-01T10:20:00Z"
}
```

---

- Last updated: <để tôi tự điền ngày>
- Downstream docs cần rà lại nếu file này đổi: DEVELOPMENT_RULES.md, AGENTS.md,
  ROADMAP.md, FEATURE_BACKLOG.md
