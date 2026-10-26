"""Trang chủ của app: hiện các chức năng theo quyền của người dùng."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..permissions import QUYEN_DANH_GIA, QUYEN_KHEN_THUONG, QUYEN_KY_LUAT


@login_required
def trang_chu(request):
    u = request.user
    return render(request, "danh_gia/trang_chu.html", {
        "co_quyen_danh_gia": u.has_perm(QUYEN_DANH_GIA),
        "co_quyen_khen_thuong": u.has_perm(QUYEN_KHEN_THUONG),
        "co_quyen_ky_luat": u.has_perm(QUYEN_KY_LUAT),
    })
