from dataclasses import dataclass
from typing import Protocol

from app.domain.models import DocumentType, OCRBlock

MVP_FIELD_CODES = (
    "ho_ten",
    "gioi_tinh",
    "ngay_sinh",
    "so_cccd",
    "ngay_cap_cccd",
    "co_quan_cap_cccd",
    "so_dien_thoai_di_dong",
    "email",
    "tinh_trang_hon_nhan",
    "trinh_do_hoc_van",
    "hinh_thuc_so_huu_nha",
    "dia_chi_thuong_tru",
    "dia_chi_hien_tai",
    "thoi_gian_cu_tru_hien_tai",
    "so_tien_vay_de_nghi",
    "so_tien_vay_de_nghi_bang_chu",
    "ngay_lam_don",
    "ky_han_vay",
    "muc_dich_vay",
    "chi_tiet_muc_dich_vay_khac",
    "phuong_thuc_giai_ngan",
    "loai_tai_khoan_nhan_giai_ngan",
    "ngan_hang_nhan_giai_ngan",
    "chi_nhanh_nhan_giai_ngan",
    "so_tai_khoan_nhan_giai_ngan",
    "ten_chu_tai_khoan_nhan_giai_ngan",
    "nghe_nghiep_chuyen_mon",
    "ten_don_vi_cong_tac",
    "ma_so_thue_cong_ty",
    "dia_chi_cong_ty",
    "dien_thoai_cong_ty",
    "chuc_vu",
    "loai_hop_dong_lao_dong",
    "ngay_bat_dau_lam_viec",
    "ngay_nhan_luong_hang_thang",
    "muc_luong_gross",
    "thu_nhap_thuc_lanh_hang_thang",
    "chi_phi_sinh_hoat_hang_thang",
    "hinh_thuc_nhan_luong",
    "so_nguoi_phu_thuoc",
)


@dataclass(frozen=True)
class LLMDocumentInput:
    document_id: str
    document_type: DocumentType
    blocks: list[OCRBlock]


@dataclass(frozen=True)
class LLMExtractedField:
    field_code: str
    value: str | None
    source_ids: list[str]


class LLMProvider(Protocol):
    def extract(
        self,
        documents: list[LLMDocumentInput],
    ) -> list[LLMExtractedField]: ...
