"""Logic CHUNG cho khen thưởng (UC-2.1) và kỷ luật (UC-2.2).

Hai chức năng dùng chung bảng KhenThuongKyLuat nên dùng chung luồng xử lý:
chọn nhân viên -> chọn kết quả đánh giá -> nhập thông tin -> lưu.
Phần riêng của từng loại (tiêu đề, quyền, câu thông báo...) nằm ở khen_thuong.py
và ky_luat.py, truyền vào đây qua tham số `cfg`.
"""
from django.contrib import messages
from django.db import DatabaseError, transaction
from django.shortcuts import redirect, render

from nhan_su.models import NhanVien

from ..forms import GhiNhanForm
from ..models import DanhGia, KhenThuongKyLuat
from ..permissions import co_quyen


def xu_ly_ghi_nhan(request, loai, cfg):
    if not co_quyen(request.user, cfg["quyen"]):
        messages.error(request, "Bạn không có quyền thực hiện chức năng này.")
        return redirect("danh_gia:trang_chu")

    nhan_vien = NhanVien.objects.all().order_by("pk")
    ma_nv, ma_dg = request.GET.get("nv"), request.GET.get("dg")
    nv = nhan_vien.filter(pk=ma_nv).first() if ma_nv else None
    ds_dg = DanhGia.objects.none()
    dg = None
    if nv:
        ds_dg = (
            DanhGia.objects.filter(manv=nv)
            .select_related("maky")
            .order_by("-maky__thoigianbatdau")
        )
        dg = ds_dg.filter(pk=ma_dg).first() if ma_dg else ds_dg.first()
        if dg is None:
            messages.error(request, "Không tìm thấy kết quả đánh giá tương ứng.")

    form = GhiNhanForm(request.POST or None, loai=loai) if dg else None
    if form is not None and request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.madanhgia = dg
        obj.loaiphieu = loai
        try:
            with transaction.atomic():
                obj.save()
        except DatabaseError:
            messages.error(request, cfg["loi_csdl"])
        else:
            messages.success(request, cfg["thanh_cong"])
            return redirect(cfg["url"])

    return render(request, "danh_gia/ghi_nhan.html", {
        "cfg": cfg, "nhan_vien": nhan_vien, "nv": nv, "ds_dg": ds_dg, "dg": dg, "form": form,
        "da_ghi_nhan": (
            KhenThuongKyLuat.objects.filter(madanhgia=dg, loaiphieu=loai) if dg else []
        ),
    })
