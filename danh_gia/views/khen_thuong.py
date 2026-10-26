"""UC-2.1: ghi nhận khen thưởng (phần riêng của khen thưởng)."""
from django.contrib.auth.decorators import login_required

from ..permissions import QUYEN_KHEN_THUONG
from .ghi_nhan import xu_ly_ghi_nhan

LOAI = "KHENTHUONG"

CAU_HINH = {
    "tieu_de": "Ghi nhận khen thưởng",
    "mo_ta": "Ghi nhận thành tích và liên kết với kết quả đánh giá đã lưu.",
    "the_tieu_de": "Thông tin khen thưởng",
    "nhan_vien_label": "Nhân viên",
    "chip": "",
    "nut_luu": "Lưu khen thưởng",
    "quyen": QUYEN_KHEN_THUONG,
    "url": "danh_gia:khen_thuong",
    "thanh_cong": "Ghi nhận khen thưởng thành công!",
    "loi_csdl": "Không thể lưu thông tin khen thưởng, vui lòng thử lại sau.",
}


@login_required
def khen_thuong(request):
    return xu_ly_ghi_nhan(request, LOAI, CAU_HINH)
