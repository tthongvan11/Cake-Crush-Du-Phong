"""UC-2.2: ghi nhận kỷ luật (phần riêng của kỷ luật)."""
from ..permissions import QUYEN_KY_LUAT, dang_nhap_bat_buoc
from .ghi_nhan import xu_ly_ghi_nhan

LOAI = "KYLUAT"

CAU_HINH = {
    "tieu_de": "Ghi nhận kỷ luật",
    "mo_ta": "Ghi nhận vi phạm theo từng nhân viên và kết quả đánh giá đã lưu.",
    "the_tieu_de": "Thông tin vi phạm và kỷ luật",
    "nhan_vien_label": "Nhân viên từ danh sách kỷ luật",
    "chip": "Quyền ghi nhận kỷ luật",
    "nut_luu": "Lưu kỷ luật",
    "quyen": QUYEN_KY_LUAT,
    "url": "danh_gia:ky_luat",
    "thanh_cong": "Ghi nhận kỷ luật thành công",
    "loi_csdl": "Không thể lưu thông tin kỷ luật, vui lòng thử lại sau",
}


@dang_nhap_bat_buoc
def ky_luat(request):
    return xu_ly_ghi_nhan(request, LOAI, CAU_HINH)
