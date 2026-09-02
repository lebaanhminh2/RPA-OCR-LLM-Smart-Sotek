from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Protocol

from app.domain.models import DocumentType, OCRBlock, OCRBlockKind

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

FieldSourceConstraint = tuple[DocumentType, OCRBlockKind]


def _text_sources(
    *document_types: DocumentType,
) -> frozenset[FieldSourceConstraint]:
    return frozenset(
        (document_type, OCRBlockKind.TEXT)
        for document_type in document_types
    )


def _loan_checkbox_source() -> frozenset[FieldSourceConstraint]:
    return frozenset(
        {
            (
                DocumentType.LOAN_APPLICATION,
                OCRBlockKind.CHECKBOX_SELECTION,
            )
        }
    )


MVP_FIELD_SOURCE_RULES: Final[
    Mapping[str, frozenset[FieldSourceConstraint]]
] = MappingProxyType(
    {
        "ho_ten": _text_sources(
            DocumentType.CCCD_FRONT,
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "gioi_tinh": _text_sources(
            DocumentType.CCCD_FRONT,
            DocumentType.LABOR_CONTRACT,
        )
        | _loan_checkbox_source(),
        "ngay_sinh": _text_sources(
            DocumentType.CCCD_FRONT,
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "so_cccd": _text_sources(
            DocumentType.CCCD_FRONT,
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "ngay_cap_cccd": _text_sources(
            DocumentType.CCCD_BACK,
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "co_quan_cap_cccd": _text_sources(
            DocumentType.CCCD_BACK,
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "so_dien_thoai_di_dong": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "email": _text_sources(DocumentType.LOAN_APPLICATION),
        "tinh_trang_hon_nhan": _loan_checkbox_source(),
        "trinh_do_hoc_van": _loan_checkbox_source(),
        "hinh_thuc_so_huu_nha": _loan_checkbox_source(),
        "dia_chi_thuong_tru": _text_sources(
            DocumentType.CCCD_FRONT,
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "dia_chi_hien_tai": _text_sources(DocumentType.LOAN_APPLICATION),
        "thoi_gian_cu_tru_hien_tai": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "so_tien_vay_de_nghi": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "so_tien_vay_de_nghi_bang_chu": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "ngay_lam_don": _text_sources(DocumentType.LOAN_APPLICATION),
        "ky_han_vay": _loan_checkbox_source(),
        "muc_dich_vay": _loan_checkbox_source(),
        "chi_tiet_muc_dich_vay_khac": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "phuong_thuc_giai_ngan": _loan_checkbox_source(),
        "loai_tai_khoan_nhan_giai_ngan": _loan_checkbox_source(),
        "ngan_hang_nhan_giai_ngan": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "chi_nhanh_nhan_giai_ngan": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "so_tai_khoan_nhan_giai_ngan": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "ten_chu_tai_khoan_nhan_giai_ngan": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "nghe_nghiep_chuyen_mon": _text_sources(
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "ten_don_vi_cong_tac": _text_sources(
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "ma_so_thue_cong_ty": _text_sources(
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "dia_chi_cong_ty": _text_sources(
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "dien_thoai_cong_ty": _text_sources(
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "chuc_vu": _text_sources(DocumentType.LABOR_CONTRACT)
        | _loan_checkbox_source(),
        "loai_hop_dong_lao_dong": _text_sources(
            DocumentType.LABOR_CONTRACT
        )
        | _loan_checkbox_source(),
        "ngay_bat_dau_lam_viec": _text_sources(
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "ngay_nhan_luong_hang_thang": _text_sources(
            DocumentType.LOAN_APPLICATION,
            DocumentType.LABOR_CONTRACT,
        ),
        "muc_luong_gross": _text_sources(DocumentType.LABOR_CONTRACT),
        "thu_nhap_thuc_lanh_hang_thang": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "chi_phi_sinh_hoat_hang_thang": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
        "hinh_thuc_nhan_luong": _text_sources(
            DocumentType.LABOR_CONTRACT
        )
        | _loan_checkbox_source(),
        "so_nguoi_phu_thuoc": _text_sources(
            DocumentType.LOAN_APPLICATION
        ),
    }
)

if set(MVP_FIELD_SOURCE_RULES) != set(MVP_FIELD_CODES):
    raise RuntimeError("MVP field source rules must cover the Core 40 catalog")


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
