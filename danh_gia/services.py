"""Nghiệp vụ tính điểm, xếp loại và lưu bản đánh giá (UC-1.3)."""
from django.conf import settings
from django.db import transaction

from .models import ChiTietDanhGia, DanhGia

# Ngưỡng mặc định (điểm trung bình, thang 10). Mockup ghi "cần cấu hình" nên có thể
# ghi đè trong settings.py: DANH_GIA_NGUONG_XEP_LOAI = [(9, "XUATSAC"), (8, "TOT"), ...]
# (xếp theo ngưỡng giảm dần; dưới ngưỡng cuối là "CHUADAT").
NGUONG_MAC_DINH = [
    (9.0, "XUATSAC"),
    (8.0, "TOT"),
    (6.5, "KHA"),
    (5.0, "DAT"),
]


def lay_nguong():
    return getattr(settings, "DANH_GIA_NGUONG_XEP_LOAI", NGUONG_MAC_DINH)


class DanhGiaDaTonTai(Exception):
    """Nhân viên đã có bản đánh giá trong kỳ này."""


def tinh_diem_trung_binh(ds_diem):
    return round(sum(ds_diem) / len(ds_diem), 2)


def xep_loai_tu_diem(diem_tb):
    for nguong, ma in lay_nguong():
        if diem_tb >= nguong:
            return ma
    return "CHUADAT"


@transaction.atomic
def luu_danh_gia(nhan_vien, ky, chi_tiet, nhanxet, ngay):
    """chi_tiet: list dict {"tieuchi": TieuChi, "diem": int, "nhanxet": str}."""
    if DanhGia.objects.filter(manv=nhan_vien, maky=ky).exists():
        raise DanhGiaDaTonTai()

    diem_tb = tinh_diem_trung_binh([c["diem"] for c in chi_tiet])
    danh_gia = DanhGia.objects.create(
        manv=nhan_vien,
        maky=ky,
        ngaydanhgia=ngay,
        xeploai=xep_loai_tu_diem(diem_tb),
        nhanxet=nhanxet or None,
    )
    for c in chi_tiet:
        ChiTietDanhGia.objects.create(
            madanhgia=danh_gia,
            matieuchi=c["tieuchi"],
            diem=c["diem"],
            nhanxet=c.get("nhanxet") or None,
        )
    return danh_gia
