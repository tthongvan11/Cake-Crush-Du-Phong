"""UC-1.1 (thiết lập kỳ đánh giá) và UC-1.2 (thiết lập tiêu chí)."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import KyDanhGiaForm, TieuChiFormSet
from ..models import DanhGia, KyDanhGia
from ..permissions import QUYEN_DANH_GIA, yeu_cau_quyen


# ======================= UC-1.1: THIẾT LẬP KỲ ĐÁNH GIÁ =======================
@yeu_cau_quyen(QUYEN_DANH_GIA)
def ky_danh_sach(request):
    q = request.GET.get("q", "").strip()
    trang_thai = request.GET.get("trang_thai", "")
    nam = request.GET.get("nam", "")

    ds = KyDanhGia.objects.annotate(
        so_tieu_chi=Count("tieuchi", distinct=True),
        so_danh_gia=Count("danhgia", distinct=True),
    )
    if q:
        ds = ds.filter(tenky__icontains=q)
    if nam.isdigit():
        ds = ds.filter(thoigianbatdau__year=int(nam))
    if trang_thai == "chua":
        ds = ds.filter(so_tieu_chi=0)
    elif trang_thai == "du":
        ds = ds.filter(so_tieu_chi__gt=0, so_danh_gia=0)
    elif trang_thai == "co_ket_qua":
        ds = ds.filter(so_danh_gia__gt=0)

    paginator = Paginator(ds, 5)
    trang = paginator.get_page(request.GET.get("trang"))
    giu_loc = request.GET.copy()
    giu_loc.pop("trang", None)
    return render(request, "danh_gia/ky_list.html", {
        "trang": trang,
        "paginator": paginator,
        "q": q, "trang_thai": trang_thai, "nam": nam,
        "ds_nam": KyDanhGia.objects.dates("thoigianbatdau", "year"),
        "giu_loc": giu_loc.urlencode(),
    })


@yeu_cau_quyen(QUYEN_DANH_GIA)
def ky_tao(request):
    form = KyDanhGiaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except DatabaseError:
            messages.error(request, "Không thể lưu kỳ đánh giá, vui lòng thử lại sau.")
        else:
            messages.success(request, "Tạo kỳ đánh giá thành công!")
            return redirect("danh_gia:ky_ds")
    return render(request, "danh_gia/ky_form.html", {"form": form})


@yeu_cau_quyen(QUYEN_DANH_GIA)
def ky_ket_qua(request, maky):
    """Xem kết quả các bản đánh giá đã lưu của một kỳ (nút 'Xem kết quả')."""
    ky = get_object_or_404(KyDanhGia, pk=maky)
    ds = (
        DanhGia.objects.filter(maky=ky)
        .select_related("manv")
        .annotate(tb=Avg("chitietdanhgia__diem"))
        .order_by("manv_id")
    )
    return render(request, "danh_gia/ky_ket_qua.html", {"ky": ky, "ds": ds})


# ======================= UC-1.2: THIẾT LẬP TIÊU CHÍ =======================
@yeu_cau_quyen(QUYEN_DANH_GIA)
def tieu_chi_thiet_lap(request, maky):
    ky = get_object_or_404(KyDanhGia, pk=maky)
    if DanhGia.objects.filter(maky=ky).exists():
        messages.error(request, "Kỳ đánh giá đã có nhân viên được đánh giá, không thể sửa tiêu chí.")
        return redirect("danh_gia:ky_ds")

    formset = TieuChiFormSet(request.POST or None, instance=ky)
    if request.method == "POST":
        if formset.is_valid():
            try:
                with transaction.atomic():
                    formset.save()
            except DatabaseError:
                messages.error(request, "Không thể lưu tiêu chí, vui lòng thử lại sau.")
            else:
                messages.success(request, "Thiết lập tiêu chí đánh giá thành công")
                return redirect("danh_gia:ky_ds")
        else:
            messages.error(request, "Dữ liệu tiêu chí không hợp lệ, vui lòng kiểm tra và nhập lại.")
    return render(request, "danh_gia/tieu_chi_form.html", {
        "ky": ky, "formset": formset, "ds_ky": KyDanhGia.objects.all(),
    })
