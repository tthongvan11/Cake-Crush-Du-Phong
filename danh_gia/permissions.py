from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

QUYEN_DANH_GIA = "danh_gia.quan_ly_danh_gia"
QUYEN_KHEN_THUONG = "danh_gia.ghi_nhan_khen_thuong"
QUYEN_KY_LUAT = "danh_gia.quan_ly_ky_luat"


def lay_nhan_vien(user):
    """Trả về hồ sơ NhanVien của tài khoản đang đăng nhập, hoặc None.

    !!! ĐIỀU CHỈNH hàm này cho khớp cách app tai_khoan/nhan_vien liên kết
    User <-> NhanVien (đây là điểm duy nhất cần sửa). Ví dụ:
      - NhanVien có OneToOneField(User) tên mặc định  -> getattr(user, "nhanvien", None)
      - Có model TaiKhoan có khóa ngoại manv          -> user.taikhoan.manv
    """
    return getattr(user, "ho_so", None)


def yeu_cau_quyen(perm):
    """Đăng nhập + có quyền `perm` mới được vào view."""

    def decorator(view):
        @login_required
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                messages.error(request, "Bạn không có quyền thực hiện chức năng này.")
                return redirect("danh_gia:trang_chu")
            return view(request, *args, **kwargs)

        return _wrapped

    return decorator


def yeu_cau_nhan_vien(view):
    """Đăng nhập + tài khoản gắn với hồ sơ nhân viên; gán request.nhan_vien."""

    @login_required
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        nhan_vien = lay_nhan_vien(request.user)
        if nhan_vien is None:
            messages.error(request, "Tài khoản của bạn chưa liên kết với hồ sơ nhân viên.")
            return redirect("danh_gia:trang_chu")
        request.nhan_vien = nhan_vien
        return view(request, *args, **kwargs)

    return _wrapped
