"""UC-2.3 (tra cứu kết quả) và UC-2.4 (gửi phản hồi) dành cho nhân viên."""
from django.contrib import messages
from django.db import DatabaseError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from ..forms import PhanHoiForm
from ..models import DanhGia, KyDanhGia
from ..permissions import yeu_cau_nhan_vien


# ======================= UC-2.3: TRA CỨU KẾT QUẢ =======================
@yeu_cau_nhan_vien
def ket_qua_cua_toi(request):
    ds = list(
        DanhGia.objects.filter(manv=request.nhan_vien)
        .select_related("maky")
        .order_by("-maky__thoigianbatdau")
    )
    ma_ky = request.GET.get("ky")
    if ma_ky:
        dg = next((d for d in ds if d.maky_id == ma_ky), None)  # kỳ chưa có kết quả -> None
    else:
        dg = ds[0] if ds else None
    da_co = {d.maky_id for d in ds}
    return render(request, "danh_gia/ket_qua.html", {
        "nhan_vien": request.nhan_vien,
        "ds": ds,
        "dg": dg,
        "ky_dang_xem": KyDanhGia.objects.filter(pk=ma_ky).first() if ma_ky else None,
        "chi_tiet": dg.chitietdanhgia_set.select_related("matieuchi") if dg else [],
        "phan_hoi": dg.phanhoi_set.all() if dg else [],
        "cac_ky": [
            (k, k.pk in da_co)
            for k in KyDanhGia.objects.all()
            if not dg or k.pk != dg.maky_id
        ],
    })


# ======================= UC-2.4: GỬI PHẢN HỒI =======================
@yeu_cau_nhan_vien
def gui_phan_hoi(request, madanhgia):
    dg = DanhGia.objects.select_related("maky").filter(pk=madanhgia).first()
    if dg is None or dg.manv_id != request.nhan_vien.pk:
        messages.error(request, "Bạn chỉ được gửi phản hồi đối với kết quả đánh giá của chính mình.")
        return redirect("danh_gia:ket_qua")

    form = PhanHoiForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ph = form.save(commit=False)
        ph.manv = request.nhan_vien
        ph.madanhgia = dg
        ph.ngayphanhoi = timezone.localdate()
        try:
            with transaction.atomic():
                ph.save()
        except DatabaseError:
            messages.error(request, "Không thể gửi phản hồi, vui lòng thử lại sau")
        else:
            messages.success(request, "Gửi phản hồi thành công!")
            return redirect("danh_gia:ket_qua")
    return render(request, "danh_gia/phan_hoi_form.html", {
        "dg": dg, "form": form, "nhan_vien": request.nhan_vien,
    })
