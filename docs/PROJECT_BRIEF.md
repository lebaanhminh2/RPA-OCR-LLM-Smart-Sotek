# PROJECT_BRIEF.md

## 1. Problem Statement

Chuyên viên Direct Sale hiện phải đọc thủ công từng loại giấy tờ trong hồ sơ vay từ
lương (CCCD, giấy đề nghị vay vốn, hợp đồng lao động) để nhập lại thông tin vào hệ
thống. Việc này chậm, dễ sai sót, và mỗi lần cần kiểm tra lại một trường dữ liệu thì
phải tự lật lại đúng trang giấy tờ để đối chiếu bằng mắt.

Dự án xây dựng một web app giúp chuyên viên xử lý hồ sơ nhanh và chính xác hơn bằng
cách: dùng OCR để đọc chữ trong giấy tờ, dùng LLM để trích xuất các trường dữ liệu
nghiệp vụ từ nội dung OCR, sau đó cho chuyên viên xem lại và xác nhận — với khả năng
click vào một trường dữ liệu là hệ thống tự mở đúng tài liệu, đúng trang, và tô sáng
đúng vùng chữ trên ảnh gốc mà thông tin đó được trích ra.

## 2. Users / Actors

- **Chuyên viên Direct Sale** — người dùng chính. Upload hồ sơ, xem kết quả OCR/LLM
  trích xuất, kiểm tra bằng chứng (evidence) trên tài liệu gốc, sửa các trường dữ liệu
  nếu phát hiện sai sót. Khi đã kiểm tra xong, bấm nút Upload để lưu toàn bộ dữ liệu
  hồ sơ một lần — không cần xác nhận (confirm) từng trường riêng lẻ.
- **Hệ thống (OCR + LLM pipeline)** — actor tự động, chạy nền sau khi hồ sơ được
  upload: đọc chữ từ tài liệu (OCR) và trích xuất trường dữ liệu nghiệp vụ (LLM).

Phạm vi MVP chỉ có một vai trò người dùng (chuyên viên xử lý). Không có vai trò
duyệt/quản lý riêng trong bản MVP này.

## 3. Goals

- Tự động hoá bước đọc và trích xuất dữ liệu từ 4 loại giấy tờ bắt buộc trong hồ sơ
  vay từ lương, giảm thời gian nhập liệu thủ công.
- Mỗi giá trị dữ liệu được trích xuất phải truy ngược được về đúng vị trí (document,
  trang, vùng bounding box) trên tài liệu gốc — để chuyên viên có thể kiểm chứng nhanh
  thay vì phải đọc lại toàn bộ giấy tờ.
- Cho phép chuyên viên xem lại và sửa từng trường dữ liệu ngay trên giao diện, dựa
  trên bằng chứng (evidence) được highlight trực tiếp; không cần confirm từng field riêng lẻ.
- Lưu lại kết quả cuối cùng sau khi chuyên viên đã review/sửa hồ sơ.
- Toàn bộ flow "upload → OCR → LLM extract → review/sửa → save" chạy được trọn
  vẹn, ổn định cho một hồ sơ đơn lẻ, làm nền tảng để mở rộng sau này.

## 4. Non-Goals (MVP)

Các hạng mục sau **không** thuộc phạm vi MVP, để tránh phình scope:

- Cross-document validation (đối chiếu chéo thông tin giữa các giấy tờ với nhau).
- Chấm điểm/scoring tín dụng.
- Phát hiện gian lận (fraud detection).
- Quy trình BPM (business process management) thật với nhiều bước duyệt, phân quyền
  phức tạp.
- Kiến trúc microservices.
- Hàng đợi (queue) xử lý phức tạp, xử lý bất đồng bộ nhiều tầng.
- Hỗ trợ nhiều provider OCR/LLM cùng lúc (MVP chỉ dùng đúng 1 OCR provider và 1 LLM
  provider).
- Các yêu cầu bảo mật cấp enterprise (SSO, audit log chi tiết, phân quyền nhiều cấp,
  mã hoá nâng cao, v.v.).

## 5. Core Workflow

1. **Upload** — chuyên viên upload đủ 4 loại giấy tờ của một hồ sơ.
2. **OCR** — hệ thống chạy OCR trên từng tài liệu, sinh ra các khối dữ liệu gồm: text,
   số trang (page), toạ độ vùng (bounding box), độ tin cậy (confidence), và một mã định
   danh nguồn (source_id) cho từng khối.
3. **LLM Extract** — LLM đọc nội dung OCR và trích xuất các trường dữ liệu nghiệp vụ,
   mỗi trường gồm: field_code, value, và danh sách source_ids trỏ về các khối OCR đã
   dùng làm căn cứ. LLM **không được tự tạo bounding box** — chỉ được tham chiếu tới
   source_id đã có sẵn từ bước OCR.
4. **Backend Mapping** — backend dùng source_ids do LLM trả về để tra ngược lại đúng
   bounding box tương ứng (đã có từ bước OCR).
5. **Review UI** — chuyên viên xem danh sách trường dữ liệu; khi click vào một trường,
   giao diện tự mở đúng tài liệu, đúng trang, và highlight đúng vùng bounding box liên
   quan để đối chiếu trực quan.
6. **Sửa** — chuyên viên sửa giá trị các trường nếu phát hiện sai, dựa trên bằng chứng
   được highlight. Không cần xác nhận (confirm) từng trường riêng lẻ.
7. **Upload** — khi đã kiểm tra/sửa xong, chuyên viên bấm nút Upload để lưu toàn bộ dữ
   liệu của hồ sơ trong một lần thao tác. Ở giai đoạn MVP hiện tại (chưa demo phần
   upload lên hệ thống ngoài), "Upload" chỉ cần lưu dữ liệu vào một nơi có thể xem lại
   được — chưa cần tích hợp với hệ thống bên ngoài.

## 6. Required Documents

Mỗi hồ sơ vay từ lương bắt buộc phải có đủ 4 loại giấy tờ sau:

1. CCCD (Căn cước công dân) — mặt trước
2. CCCD (Căn cước công dân) — mặt sau
3. Giấy đề nghị vay vốn theo lương
4. Hợp đồng lao động

> **Lưu ý:** một số giấy tờ (ví dụ phần điền tay trong giấy đề nghị vay vốn) có thể
> chứa chữ viết tay tiếng Việt, không chỉ chữ in. OCR cần xử lý được cả hai dạng này.
> Đây là ràng buộc cần cân nhắc khi chọn OCR provider ở ARCHITECTURE.md.

## 7. Core Features (MVP)

- Tạo hồ sơ (case) và upload đủ 4 loại giấy tờ cho hồ sơ đó.
- Chạy OCR tự động trên từng tài liệu sau khi upload, lưu lại text/page/bbox/
  confidence/source_id cho từng khối.
- Chạy LLM để trích xuất các trường dữ liệu nghiệp vụ bắt buộc, mỗi trường có
  field_code, value, và source_ids tham chiếu tới khối OCR gốc.
- Mapping source_ids → bounding box ở tầng backend.
- Giao diện xem tài liệu (document viewer) hỗ trợ điều hướng trang và highlight vùng.
- Giao diện review: danh sách trường dữ liệu, click vào trường để nhảy tới đúng
  document/trang/vùng bằng chứng tương ứng.
- Cho phép sửa giá trị từng trường dữ liệu.
- Nút Upload để lưu toàn bộ dữ liệu hồ sơ trong một lần thao tác (không cần confirm
  từng trường riêng lẻ). Ở MVP hiện tại, Upload = lưu vào nơi có thể xem lại được,
  chưa cần tích hợp hệ thống ngoài.

## 8. MVP Acceptance Criteria

- [ ] Có thể tạo một hồ sơ (case) và upload đủ 4 loại giấy tờ bắt buộc cho hồ sơ đó.
- [ ] Sau khi upload, hệ thống tự động chạy OCR và sinh ra được các khối dữ liệu OCR
      với đầy đủ: text, page, bounding box, confidence, source_id.
- [ ] LLM trích xuất được các trường dữ liệu bắt buộc từ nội dung OCR, mỗi trường có
      field_code, value, và danh sách source_ids hợp lệ (không có bounding box do LLM
      tự tạo ra).
- [ ] Backend map đúng từng source_id về đúng bounding box gốc tương ứng.
- [ ] Trong Review UI, click vào một trường dữ liệu sẽ mở đúng tài liệu, đúng trang,
      và highlight đúng vùng bounding box liên quan tới trường đó.
- [ ] Chuyên viên sửa được giá trị của các trường dữ liệu nếu phát hiện sai.
- [ ] Sau khi kiểm tra/sửa xong, chuyên viên bấm nút Upload và toàn bộ dữ liệu hồ sơ
      được lưu lại trong một lần thao tác (không phải xác nhận từng trường riêng lẻ).
- [ ] Ở MVP hiện tại, nút Upload chỉ cần lưu dữ liệu vào một nơi có thể xem lại được;
      chưa cần tích hợp gửi dữ liệu ra hệ thống ngoài.
- [ ] Toàn bộ flow upload → OCR → LLM extract → review/sửa → Upload (lưu) chạy được
      end-to-end cho ít nhất một hồ sơ demo, dùng đúng 1 OCR provider, 1 LLM provider,
      và lưu dữ liệu trong SQLite.

## 9. Future Scope (Post-MVP)

Các hướng mở rộng có thể cân nhắc sau khi MVP hoàn thành và ổn định:

- Cross-document validation — đối chiếu chéo thông tin giữa các giấy tờ (ví dụ: tên
  trên CCCD phải khớp tên trên hợp đồng lao động).
- Chấm điểm/scoring tín dụng tự động.
- Phát hiện gian lận (fraud detection) trên hồ sơ hoặc giấy tờ.
- Quy trình BPM thật với nhiều bước duyệt và phân quyền theo vai trò.
- Tách kiến trúc theo hướng microservices nếu quy mô tăng.
- Hàng đợi xử lý phức tạp cho khối lượng hồ sơ lớn, xử lý song song/bất đồng bộ nhiều
  tầng.
- Hỗ trợ nhiều provider OCR/LLM, có thể chọn hoặc so sánh giữa các provider.
- Nâng cấp bảo mật lên chuẩn enterprise (SSO, audit log, phân quyền nhiều cấp, mã hoá
  nâng cao).

---

- Last updated: <để tôi tự điền ngày>
- Downstream docs cần rà lại nếu file này đổi: ARCHITECTURE.md, DATA_MODEL.md,
  DEVELOPMENT_RULES.md, AGENTS.md, ROADMAP.md, FEATURE_BACKLOG.md
