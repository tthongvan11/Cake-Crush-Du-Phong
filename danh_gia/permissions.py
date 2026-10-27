from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

QUYEN_DANH_GIA = "danh_gia.quan_ly_danh_gia"
QUYEN_KHEN_THUONG = "danh_gia.ghi_nhan_khen_thuong"
QUYEN_KY_LUAT = "danh_gia.quan_ly_ky_luat"

# settings chưa có LOGIN_URL nên chỉ rõ tên url đăng nhập của app tai_khoan.
dang_nhap_bat_buoc = login_required(login_url="login")


def la_quan_ly(user):
    """Quy ước của tai_khoan: staff hoặc superuser là Quản lý, còn lại là Nhân viên."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def co_quyen(user, perm):
    """Quản lý có toàn quyền; tài khoản khác cần được cấp quyền `perm` (qua Admin > Groups)."""
    return la_quan_ly(user) or (user.is_authenticated and user.has_perm(perm))


def lay_nhan_vien(user):
    """Trả về hồ sơ NhanVien của tài khoản đang đăng nhập, hoặc None.

    !!! ĐIỀU CHỈNH hàm này cho khớp cách app nhan_vien liên kết với User
    (repo main chưa có app nhan_vien). Ví dụ:
      - NhanVien có OneToOneField(User) tên mặc định  -> getattr(user, "nhanvien", None)
      - NhanVien có khóa ngoại/1-1 tới User tên taikhoan -> NhanVien.objects.filter(taikhoan=user).first()
    """
    return getattr(user, "ho_so", None)


def yeu_cau_quyen(perm):
    """Đăng nhập + có quyền `perm` (hoặc là Quản lý) mới được vào view."""

    def decorator(view):
        @dang_nhap_bat_buoc
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if not co_quyen(request.user, perm):
                messages.error(request, "Bạn không có quyền thực hiện chức năng này.")
                return redirect("danh_gia:trang_chu")
            return view(request, *args, **kwargs)

        return _wrapped

    return decorator


def yeu_cau_nhan_vien(view):
    """Đăng nhập + tài khoản gắn với hồ sơ nhân viên; gán request.nhan_vien."""

    @dang_nhap_bat_buoc
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        nhan_vien = lay_nhan_vien(request.user)
        if nhan_vien is None:
            messages.error(request, "Tài khoản của bạn chưa liên kết với hồ sơ nhân viên.")
            return redirect("danh_gia:trang_chu")
        request.nhan_vien = nhan_vien
        return view(request, *args, **kwargs)

    return _wrapped
