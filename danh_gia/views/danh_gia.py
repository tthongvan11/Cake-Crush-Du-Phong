"""UC-1.3: đánh giá và chấm điểm (bước nhập điểm -> bước xác nhận -> lưu)."""
from urllib.parse import urlencode

from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from nhan_su.models import NhanVien

from .. import services
from ..forms import DanhGiaForm
from ..models import DanhGia, KyDanhGia
from ..permissions import QUYEN_DANH_GIA, yeu_cau_quyen


def _url_voi_query(ten_url, **tham_so):
    return f"{reverse(ten_url)}?{urlencode(tham_so)}"


def _khoa_phien(maky, manv):
    return f"dg_nhap_{maky}_{manv}"


def _lay_ky_nv(request):
    ma_ky, ma_nv = request.GET.get("ky"), request.GET.get("nv")
    ky = KyDanhGia.objects.filter(pk=ma_ky).first() if ma_ky else None
    nv = NhanVien.objects.filter(pk=ma_nv).first() if ma_nv else None
    return ky, nv


def _nguong_cho_js():
    """Ngưỡng xếp loại để trang chấm điểm hiện tổng điểm/xếp loại tạm tính."""
    nhan = dict(DanhGia.XEP_LOAI_CHOICES)
    return {
        "nguong": [[n, nhan[m]] for n, m in services.lay_nguong()],
        "cuoi": nhan["CHUADAT"],
    }


@yeu_cau_quyen(QUYEN_DANH_GIA)
def danh_gia_tao(request):
    ky, nv = _lay_ky_nv(request)
    da_danh_gia = (
        set(DanhGia.objects.filter(maky=ky).values_list("manv_id", flat=True)) if ky else set()
    )
    tieu_chi = list(ky.tieuchi_set.all()) if ky else []
    form = None

    if ky and not tieu_chi:
        messages.error(request, "Kỳ đánh giá chưa có tiêu chí, hãy thiết lập tiêu chí trước.")
    elif ky and nv and nv.pk in da_danh_gia:
        messages.error(request, "Nhân viên đã có bản đánh giá trong kỳ này.")
    elif ky and nv:
        khoa = _khoa_phien(ky.pk, nv.pk)
        initial = DanhGiaForm.initial_tu_phien(request.session.get(khoa, {}))
        form = DanhGiaForm(request.POST or None, initial=initial, tieu_chi_list=tieu_chi)
        if request.method == "POST" and form.is_valid():
            request.session[khoa] = form.du_lieu_phien()
            return redirect(_url_voi_query("danh_gia:danh_gia_xac_nhan", ky=ky.pk, nv=nv.pk))

    return render(request, "danh_gia/cham_diem.html", {
        "ds_ky": KyDanhGia.objects.all(),
        "nhan_vien": NhanVien.objects.all().order_by("pk"),
        "ky": ky, "nv": nv, "da_danh_gia": da_danh_gia, "form": form,
        "nguong": _nguong_cho_js(),
    })


@yeu_cau_quyen(QUYEN_DANH_GIA)
def danh_gia_xac_nhan(request):
    ky, nv = _lay_ky_nv(request)
    if not (ky and nv):
        return redirect("danh_gia:danh_gia_tao")
    khoa = _khoa_phien(ky.pk, nv.pk)
    nhap = request.session.get(khoa)
    tieu_chi = list(ky.tieuchi_set.all())

    if not nhap or any(tc.matieuchi not in nhap.get("diem", {}) for tc in tieu_chi):
        request.session.pop(khoa, None)
        return redirect(_url_voi_query("danh_gia:danh_gia_tao", ky=ky.pk, nv=nv.pk))

    chi_tiet = [
        {"tieuchi": tc, "diem": nhap["diem"][tc.matieuchi], "nhanxet": ""} for tc in tieu_chi
    ]
    diem_tb = services.tinh_diem_trung_binh([c["diem"] for c in chi_tiet])
    xep_loai = services.xep_loai_tu_diem(diem_tb)
    quay_lai = _url_voi_query("danh_gia:danh_gia_tao", ky=ky.pk, nv=nv.pk)

    if request.method == "POST":
        try:
            services.luu_danh_gia(nv, ky, chi_tiet, nhap.get("nhanxet", ""), timezone.localdate())
        except (services.DanhGiaDaTonTai, IntegrityError):
            request.session.pop(khoa, None)
            messages.error(request, "Nhân viên đã có bản đánh giá trong kỳ này.")
            return redirect(_url_voi_query("danh_gia:danh_gia_tao", ky=ky.pk))
        except DatabaseError:
            messages.error(request, "Không thể lưu kết quả đánh giá, vui lòng thử lại sau.")
        else:
            request.session.pop(khoa, None)
            messages.success(request, "Lưu kết quả đánh giá thành công!")
            return redirect(_url_voi_query("danh_gia:danh_gia_tao", ky=ky.pk))

    return render(request, "danh_gia/danh_gia_xac_nhan.html", {
        "ky": ky, "nv": nv, "chi_tiet": chi_tiet, "nhanxet": nhap.get("nhanxet", ""),
        "diem_tb": diem_tb, "xep_loai": dict(DanhGia.XEP_LOAI_CHOICES)[xep_loai],
        "nguoi_danh_gia": request.user.get_full_name() or request.user.get_username(),
        "quay_lai": quay_lai,
    })
