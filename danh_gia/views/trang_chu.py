"""Trang chủ của app: hiện các chức năng theo quyền của người dùng."""
from django.shortcuts import render

from ..permissions import (
    QUYEN_DANH_GIA,
    QUYEN_KHEN_THUONG,
    QUYEN_KY_LUAT,
    co_quyen,
    dang_nhap_bat_buoc,
)


@dang_nhap_bat_buoc
def trang_chu(request):
    u = request.user
    return render(request, "danh_gia/trang_chu.html", {
        "co_quyen_danh_gia": co_quyen(u, QUYEN_DANH_GIA),
        "co_quyen_khen_thuong": co_quyen(u, QUYEN_KHEN_THUONG),
        "co_quyen_ky_luat": co_quyen(u, QUYEN_KY_LUAT),
    })
