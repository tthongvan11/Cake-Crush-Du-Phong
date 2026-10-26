from decimal import ROUND_HALF_UP, Decimal  # Làm tròn số giờ sang phút.

from django import template  # Đăng ký bộ lọc dùng trong template.

register = template.Library()  # Thư viện bộ lọc của phân hệ chấm công.


@register.filter  # Dùng trong template: {{ so_phut|phut_gio }}
def phut_gio(so_phut):  # Hiển thị số phút; đủ 60 phút thì đổi sang giờ.
    if so_phut is None or so_phut == "":  # Không có dữ liệu.
        return ""  # Để trống.
    so_phut = int(so_phut)  # Bảo đảm là số nguyên.
    gio, phut = divmod(so_phut, 60)  # Tách số giờ và số phút lẻ.
    if not gio:  # Dưới 60 phút.
        return f"{phut} phút"  # Ví dụ 45 phút.
    return f"{gio} giờ" if not phut else f"{gio} giờ {phut} phút"  # Ví dụ 1 giờ hoặc 7 giờ 33 phút.


@register.filter  # Dùng trong template: {{ so_gio|gio_phut }}
def gio_phut(so_gio):  # Số giờ thập phân trong database (7,55) → "7 giờ 33 phút".
    if so_gio is None or so_gio == "":  # Không có dữ liệu.
        return ""  # Để trống.
    phut = (Decimal(str(so_gio)) * 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP)  # Đổi giờ sang phút, làm tròn.
    return phut_gio(phut)  # Dùng chung cách hiển thị với số phút.
