# EXTRACTION_SCHEMA.md

> Source of truth cho danh mục trường M4. Tài liệu này chỉ mô tả dữ liệu trích
> xuất thô từ 4 loại tài liệu MVP; không mô tả BPM mapping, chuẩn hoá nghiệp vụ,
> suy diễn hay đối chiếu chéo tài liệu.

## 1. Phạm vi

- Runtime input là PDF/ảnh của 4 `DocumentType`: `CCCD_FRONT`, `CCCD_BACK`,
  `LOAN_APPLICATION`, `LABOR_CONTRACT`.
- Các file DOCX mẫu chỉ là bằng chứng để thiết kế biểu mẫu; ứng dụng không cần
  hỗ trợ upload DOCX.
- M4 tạo đúng một `ExtractedField` cho mỗi `field_code` dưới đây trong một
  `Case`, kể cả khi không tìm thấy giá trị.
- Tất cả giá trị M4 dùng kiểu `string | null`. Chuẩn hoá tiền tệ, ngày tháng,
  địa chỉ hoặc enum BPM nằm ngoài M4.
- Không dùng tài liệu khách hàng thật trong test Gemini, smoke test hoặc dữ
  liệu demo. Chỉ dùng dữ liệu synthetic.

## 2. Quy ước output

- Không tìm thấy bằng chứng: `value = null`, `source_ids = []`.
- Có giá trị: `value` là chuỗi khác rỗng và `source_ids` có ít nhất một ID của
  `OCRBlock` đã có trong input của đúng case.
- LLM không được tạo `source_id` hoặc bounding box.
- Partial extraction là hành vi mặc định của MVP: nếu một field có value rỗng,
  thiếu source hoặc source không tồn tại, backend không lưu value đó mà tạo
  `ExtractedField` tương ứng với `original_value = current_value = null` và
  không có `FieldSource`. Các field hợp lệ khác vẫn được giữ để chuyên viên
  review; luôn có đủ đúng 40 `ExtractedField`.
- Case vẫn có thể `READY_FOR_REVIEW` khi nhiều hoặc toàn bộ field null để chuyên
  viên nhập tay. Chỉ lỗi cấp pipeline (OCR, Gemini hết retry/response không
  parse được, persistence) mới chuyển case sang `FAILED`.
- Mọi `field_code` ngoài catalog này đều bị từ chối.
- Các giá trị từ checkbox được local OMR chuẩn hoá thành evidence block trước
  khi gửi LLM; Gemini không tự suy đoán dấu tick từ text OCR.

## 3. Core 40 field catalog

### 3.1 Cá nhân và cư trú (14)

| field_code | Nhãn tiếng Việt | Type | Nguồn dự kiến | Cách lấy |
|---|---|---|---|---|
| `ho_ten` | Họ và tên | `string \| null` | `CCCD_FRONT`, `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `gioi_tinh` | Giới tính | `string \| null` | `CCCD_FRONT`, `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text hoặc single-choice checkbox |
| `ngay_sinh` | Ngày sinh | `string \| null` | `CCCD_FRONT`, `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `so_cccd` | Số CCCD/CMND hiện tại | `string \| null` | `CCCD_FRONT`, `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `ngay_cap_cccd` | Ngày cấp CCCD/CMND | `string \| null` | `CCCD_BACK`, `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `co_quan_cap_cccd` | Cơ quan/nơi cấp CCCD/CMND | `string \| null` | `CCCD_BACK`, `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `so_dien_thoai_di_dong` | Số điện thoại di động | `string \| null` | `LOAN_APPLICATION` | Text |
| `email` | Địa chỉ email | `string \| null` | `LOAN_APPLICATION` | Text |
| `tinh_trang_hon_nhan` | Tình trạng hôn nhân | `string \| null` | `LOAN_APPLICATION` | Single-choice checkbox |
| `trinh_do_hoc_van` | Trình độ học vấn | `string \| null` | `LOAN_APPLICATION` | Single-choice checkbox |
| `hinh_thuc_so_huu_nha` | Hình thức sở hữu nhà đang ở | `string \| null` | `LOAN_APPLICATION` | Single-choice checkbox |
| `dia_chi_thuong_tru` | Địa chỉ thường trú | `string \| null` | `CCCD_FRONT`, `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text; giữ nguyên chuỗi thô |
| `dia_chi_hien_tai` | Địa chỉ nơi ở hiện tại | `string \| null` | `LOAN_APPLICATION` | Text; giữ nguyên chuỗi thô |
| `thoi_gian_cu_tru_hien_tai` | Thời gian cư trú tại địa chỉ hiện tại | `string \| null` | `LOAN_APPLICATION` | Text; không tự tính |

### 3.2 Khoản vay và giải ngân (12)

| field_code | Nhãn tiếng Việt | Type | Nguồn dự kiến | Cách lấy |
|---|---|---|---|---|
| `so_tien_vay_de_nghi` | Số tiền vay đề nghị bằng số | `string \| null` | `LOAN_APPLICATION` | Text |
| `so_tien_vay_de_nghi_bang_chu` | Số tiền vay đề nghị bằng chữ | `string \| null` | `LOAN_APPLICATION` | Text |
| `ngay_lam_don` | Ngày làm đơn | `string \| null` | `LOAN_APPLICATION` | Text |
| `ky_han_vay` | Kỳ hạn vay đề nghị | `string \| null` | `LOAN_APPLICATION` | Single-choice checkbox |
| `muc_dich_vay` | Mục đích vay | `string \| null` | `LOAN_APPLICATION` | Multi-choice checkbox; nhiều lựa chọn dùng chuỗi JSON array |
| `chi_tiet_muc_dich_vay_khac` | Chi tiết mục đích vay khác | `string \| null` | `LOAN_APPLICATION` | Text, chỉ có ý nghĩa khi chọn Khác |
| `phuong_thuc_giai_ngan` | Phương thức giải ngân | `string \| null` | `LOAN_APPLICATION` | Single-choice checkbox |
| `loai_tai_khoan_nhan_giai_ngan` | Loại tài khoản nhận giải ngân | `string \| null` | `LOAN_APPLICATION` | Single-choice checkbox |
| `ngan_hang_nhan_giai_ngan` | Ngân hàng nhận giải ngân | `string \| null` | `LOAN_APPLICATION` | Text |
| `chi_nhanh_nhan_giai_ngan` | Chi nhánh/PGD nhận giải ngân | `string \| null` | `LOAN_APPLICATION` | Text |
| `so_tai_khoan_nhan_giai_ngan` | Số tài khoản nhận giải ngân | `string \| null` | `LOAN_APPLICATION` | Text |
| `ten_chu_tai_khoan_nhan_giai_ngan` | Tên chủ tài khoản nhận giải ngân | `string \| null` | `LOAN_APPLICATION` | Text |

### 3.3 Nghề nghiệp (10)

| field_code | Nhãn tiếng Việt | Type | Nguồn dự kiến | Cách lấy |
|---|---|---|---|---|
| `nghe_nghiep_chuyen_mon` | Nghề nghiệp/chức danh chuyên môn | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `ten_don_vi_cong_tac` | Tên công ty/đơn vị công tác | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `ma_so_thue_cong_ty` | Mã số thuế công ty | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `dia_chi_cong_ty` | Địa chỉ công ty | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `dien_thoai_cong_ty` | Điện thoại công ty | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `chuc_vu` | Chức vụ | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text hoặc single-choice checkbox |
| `loai_hop_dong_lao_dong` | Loại hợp đồng lao động | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text hoặc single-choice checkbox |
| `ngay_bat_dau_lam_viec` | Ngày bắt đầu làm việc | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `ngay_nhan_luong_hang_thang` | Ngày nhận lương hàng tháng | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text |
| `muc_luong_gross` | Mức lương gross | `string \| null` | `LABOR_CONTRACT` | Text |

### 3.4 Tài chính (4)

| field_code | Nhãn tiếng Việt | Type | Nguồn dự kiến | Cách lấy |
|---|---|---|---|---|
| `thu_nhap_thuc_lanh_hang_thang` | Thu nhập thực lãnh hàng tháng | `string \| null` | `LOAN_APPLICATION` | Text |
| `chi_phi_sinh_hoat_hang_thang` | Chi phí sinh hoạt hàng tháng | `string \| null` | `LOAN_APPLICATION` | Text |
| `hinh_thuc_nhan_luong` | Hình thức nhận lương | `string \| null` | `LOAN_APPLICATION`, `LABOR_CONTRACT` | Text hoặc single-choice checkbox |
| `so_nguoi_phu_thuoc` | Số người phụ thuộc tài chính | `string \| null` | `LOAN_APPLICATION` | Text |

## 4. Checkbox semantics

### 4.1 Trạng thái OMR

Local OMR chỉ phát ra ba trạng thái:

- `CHECKED`: đủ bằng chứng để tạo selection evidence.
- `UNCHECKED`: không tạo selection evidence.
- `UNCERTAIN`: không được coi là checked; phải để field `null` hoặc chuyển
  người dùng review khi orchestration/UI hỗ trợ cảnh báo.

Single-choice gồm: giới tính, tình trạng hôn nhân, trình độ học vấn, hình thức
sở hữu nhà, kỳ hạn vay, phương thức giải ngân, loại tài khoản nhận giải ngân,
chức vụ, loại hợp đồng lao động và hình thức nhận lương. Nhiều lựa chọn checked
trong một nhóm single-choice là conflict, không tự chọn một giá trị.

`muc_dich_vay` là multi-choice. Giá trị canonical ở M4 là một JSON array được
serialize thành string, ví dụ `["Sửa nhà","Học tập"]`; thứ tự theo biểu mẫu.

### 4.2 Template strategy

- `V1`: biểu mẫu hiện tại không marker; căn chỉnh bằng template feature
  matching + RANSAC/homography, sau đó tinh chỉnh checkbox trong ROI cục bộ.
- `V2`: biểu mẫu mới có bốn marker ID khác nhau gần bốn góc; ưu tiên marker để
  nhận diện phiên bản và căn chỉnh, sau đó vẫn tinh chỉnh ROI cục bộ.
- Không dùng toạ độ pixel tuyệt đối. Template config dùng toạ độ chuẩn hoá và
  version rõ ràng.
- Không đủ điểm căn chỉnh, sai version, crop mất ROI hoặc confidence thấp thì
  fail closed; không đoán lựa chọn gần nhất.
- Khi V2 được phát hành, người dùng vẫn upload PDF như bình thường. V1 tiếp tục
  được hỗ trợ làm fallback.

## 5. Document/source mapping

| DocumentType | Vai trò chính |
|---|---|
| `CCCD_FRONT` | Định danh, họ tên, giới tính, ngày sinh, số CCCD, địa chỉ thường trú |
| `CCCD_BACK` | Ngày cấp và cơ quan cấp CCCD |
| `LOAN_APPLICATION` | Khoản vay, giải ngân, cá nhân bổ sung, cư trú, việc làm, tài chính và checkbox |
| `LABOR_CONTRACT` | Người lao động, người sử dụng lao động, hợp đồng, chức danh, ngày bắt đầu và lương gross |

`LLMProvider` phải nhận các block được nhóm kèm `document_id` và
`document_type`; chỉ một danh sách block không có loại tài liệu là không đủ để
trích xuất đúng theo nguồn.

## 6. Deferred — không thuộc Core 40

Các nhóm có trên form nhưng hoãn khỏi M4 để giữ scope sản phẩm đầu tiên nhỏ:

- CMND/hộ chiếu trước đây.
- Loại hình doanh nghiệp, lĩnh vực hoạt động, số máy lẻ.
- Thời gian công tác, tổng kinh nghiệm và phân loại khách hàng.
- Khoản nợ/vay hiện tại dạng repeatable.
- Người tham chiếu dạng repeatable.
- Thông tin vợ/chồng dạng conditional.
- Tách địa chỉ thành tỉnh/huyện/xã/đường.

Các field do hệ thống/rule/BPM cung cấp cũng không được LLM extract: sản phẩm,
mã sản phẩm, lãi suất, nhân viên bán hàng, dữ liệu tính toán, cross-document
validation và BPM upload bên ngoài.

---

- Last updated: <để tôi tự điền ngày>
- Downstream docs cần rà lại nếu file này đổi: `docs/ROADMAP.md`,
  `docs/FEATURE_BACKLOG.md`, prompt/schema Gemini và frontend field catalog.
