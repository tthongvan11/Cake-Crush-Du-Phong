from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_safe

from nhan_su.models import NhanVien
from .forms import (
    CapNhatKetQuaForm,
    CapNhatNoiDungKhoaForm,
    KhoaDaoTaoForm,
    PhanCongDaoTaoForm,
)
from .models import KetQuaDaoTao, KhoaDaoTao, PhanCongDaoTao, TienDoDaoTao, TrangThaiKhoa
from .permissions import la_quan_ly, yeu_cau_quan_ly
from . import services


# ==============================================================================
# KHÔNG GIAN QUẢN LÝ (MANAGER VIEWS)
# ==============================================================================

@login_required(login_url="login")
@require_safe
def danh_sach_khoa(request):
    """Màn hình 1: Danh sách khóa đào tạo & 4 thẻ thống kê (Quản lý)."""
    yeu_cau_quan_ly(request.user)
    services.dong_bo_trang_thai_tat_ca_khoa()

    # Thống kê
    thong_ke = services.lay_thong_ke_dao_tao()

    # Lọc & Tìm kiếm
    ds = KhoaDaoTao.objects.all().order_by("-ngaybatdau", "-ngaytao")

    q = request.GET.get("q", "").strip()
    if q:
        ds = ds.filter(tenkhoa__icontains=q)

    trang_thai = request.GET.get("trang_thai", "").strip()
    if trang_thai and trang_thai in TrangThaiKhoa.values:
        ds = ds.filter(trangthai=trang_thai)

    thoi_gian = request.GET.get("thoi_gian", "").strip()
    hom_nay = timezone.localdate()
    if thoi_gian == "thang_nay":
        ds = ds.filter(ngaybatdau__year=hom_nay.year, ngaybatdau__month=hom_nay.month)
    elif thoi_gian == "nam_nay":
        ds = ds.filter(ngaybatdau__year=hom_nay.year)

    # Phân trang (mặc định 10 bản ghi/trang)
    paginator = Paginator(ds, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dao_tao/quan_ly/danh_sach_khoa.html",
        {
            "thong_ke": thong_ke,
            "page_obj": page_obj,
            "q": q,
            "trang_thai": trang_thai,
            "thoi_gian": thoi_gian,
            "TrangThaiKhoa": TrangThaiKhoa,
        },
    )


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def tao_khoa(request):
    """Màn hình 2: Tạo khóa đào tạo mới (Quản lý)."""
    yeu_cau_quan_ly(request.user)

    if request.method == "POST":
        form = KhoaDaoTaoForm(request.POST)
        if form.is_valid():
            khoa = form.save(commit=False)
            if not khoa.makhoa:
                khoa.makhoa = services.tao_ma_khoa()
            if not form.cleaned_data.get("trangthai"):
                khoa.trangthai = khoa.tinh_trang_thai_tu_dong()
            khoa.save()
            messages.success(request, f"Đã tạo thành công khóa đào tạo {khoa.makhoa} - {khoa.tenkhoa}.")
            return redirect("dao_tao:chi_tiet_khoa", makhoa=khoa.makhoa)
    else:
        form = KhoaDaoTaoForm()

    return render(
        request,
        "dao_tao/quan_ly/tao_khoa.html",
        {
            "form": form,
            "tieu_de": "Tạo khóa đào tạo",
        },
    )


@login_required(login_url="login")
@require_safe
def chi_tiet_khoa(request, makhoa):
    """Màn hình 3: Chi tiết khóa đào tạo (Quản lý)."""
    yeu_cau_quan_ly(request.user)
    services.dong_bo_trang_thai_tat_ca_khoa()
    khoa = get_object_or_404(KhoaDaoTao, pk=makhoa)

    return render(
        request,
        "dao_tao/quan_ly/chi_tiet_khoa.html",
        {
            "khoa": khoa,
        },
    )


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def cap_nhat_noi_dung_khoa(request, makhoa):
    """Màn hình 4: Cập nhật nội dung khóa đào tạo (Quản lý)."""
    yeu_cau_quan_ly(request.user)
    khoa = get_object_or_404(KhoaDaoTao, pk=makhoa)

    if request.method == "POST":
        form = CapNhatNoiDungKhoaForm(request.POST, instance=khoa)
        if form.is_valid():
            form.save()
            messages.success(request, f"Đã cập nhật nội dung khóa {khoa.makhoa}.")
            return redirect("dao_tao:chi_tiet_khoa", makhoa=khoa.makhoa)
    else:
        form = CapNhatNoiDungKhoaForm(instance=khoa)

    return render(
        request,
        "dao_tao/quan_ly/cap_nhat_noi_dung.html",
        {
            "khoa": khoa,
            "form": form,
        },
    )


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def phan_cong_dao_tao(request):
    """Màn hình 5: Phân công nhân viên vào khóa đào tạo (Quản lý)."""
    yeu_cau_quan_ly(request.user)
    services.dong_bo_trang_thai_tat_ca_khoa()

    khoa_id_param = request.GET.get("khoa", "").strip()
    nhan_vien_id_param = request.GET.get("nhanvien", "").strip()

    if request.method == "POST":
        form = PhanCongDaoTaoForm(request.POST)
        if form.is_valid():
            phan_cong = form.save()
            messages.success(
                request,
                f"Đã phân công nhân viên {phan_cong.nhanvien.tennv} vào khóa {phan_cong.khoadaotao.tenkhoa}.",
            )
            return redirect("dao_tao:theo_doi_dao_tao")
    else:
        initial = {}
        if khoa_id_param:
            initial["khoadaotao"] = khoa_id_param
        if nhan_vien_id_param:
            initial["nhanvien"] = nhan_vien_id_param
        form = PhanCongDaoTaoForm(initial=initial)

    ds_nhan_vien = NhanVien.objects.filter(trangthai=True).order_by("tennv")
    ds_khoa = KhoaDaoTao.objects.exclude(trangthai=TrangThaiKhoa.DA_KET_THUC).order_by("-ngaybatdau")

    return render(
        request,
        "dao_tao/quan_ly/phan_cong.html",
        {
            "form": form,
            "ds_nhan_vien": ds_nhan_vien,
            "ds_khoa": ds_khoa,
            "khoa_id_param": khoa_id_param,
        },
    )


@login_required(login_url="login")
@require_safe
def theo_doi_dao_tao(request):
    """Màn hình 6: Theo dõi tiến độ đào tạo của nhân viên (Quản lý)."""
    yeu_cau_quan_ly(request.user)

    nhan_vien_id = request.GET.get("nhanvien", "").strip()
    khoa_id = request.GET.get("khoa", "").strip()

    ds_nhan_vien = NhanVien.objects.filter(trangthai=True).order_by("tennv")
    ds_khoa_cua_nv = []
    phan_cong_hien_tai = None

    if nhan_vien_id:
        ds_khoa_cua_nv = KhoaDaoTao.objects.filter(
            danh_sach_phan_cong__nhanvien_id=nhan_vien_id
        ).order_by("-ngaybatdau")

        if khoa_id:
            phan_cong_hien_tai = PhanCongDaoTao.objects.filter(
                nhanvien_id=nhan_vien_id, khoadaotao_id=khoa_id
            ).first()

    return render(
        request,
        "dao_tao/quan_ly/theo_doi.html",
        {
            "ds_nhan_vien": ds_nhan_vien,
            "ds_khoa_cua_nv": ds_khoa_cua_nv,
            "nhan_vien_id": nhan_vien_id,
            "khoa_id": khoa_id,
            "phan_cong": phan_cong_hien_tai,
        },
    )


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def cap_nhat_ket_qua_dao_tao(request):
    """Màn hình 7: Cập nhật kết quả đào tạo Đạt hoặc Chưa đạt (Quản lý)."""
    yeu_cau_quan_ly(request.user)

    nhan_vien_id = request.GET.get("nhanvien", "").strip()
    khoa_id = request.GET.get("khoa", "").strip()

    ds_nhan_vien = NhanVien.objects.filter(trangthai=True).order_by("tennv")
    ds_khoa_cua_nv = []
    phan_cong_hien_tai = None

    if nhan_vien_id:
        ds_khoa_cua_nv = KhoaDaoTao.objects.filter(
            danh_sach_phan_cong__nhanvien_id=nhan_vien_id
        ).order_by("-ngaybatdau")

        if khoa_id:
            phan_cong_hien_tai = PhanCongDaoTao.objects.filter(
                nhanvien_id=nhan_vien_id, khoadaotao_id=khoa_id
            ).first()

    if request.method == "POST":
        form = CapNhatKetQuaForm(request.POST)
        if form.is_valid():
            p_nhanvien = request.POST.get("nhanvien")
            p_khoa = request.POST.get("khoa")
            pc = get_object_or_404(PhanCongDaoTao, nhanvien_id=p_nhanvien, khoadaotao_id=p_khoa)
            services.cap_nhat_ket_qua_dao_tao(
                pc,
                ket_qua=form.cleaned_data["ketqua"],
                nguoi_danh_gia=request.user,
            )
            messages.success(request, f"Đã cập nhật kết quả: {form.cleaned_data['ketqua']}.")
            return redirect(f"{reverse('dao_tao:theo_doi_dao_tao')}?nhanvien={p_nhanvien}&khoa={p_khoa}")
    else:
        initial = {}
        if phan_cong_hien_tai and phan_cong_hien_tai.ketqua in [KetQuaDaoTao.DAT, KetQuaDaoTao.CHUA_DAT]:
            initial["ketqua"] = phan_cong_hien_tai.ketqua
        form = CapNhatKetQuaForm(initial=initial)

    return render(
        request,
        "dao_tao/quan_ly/cap_nhat_ket_qua.html",
        {
            "ds_nhan_vien": ds_nhan_vien,
            "ds_khoa_cua_nv": ds_khoa_cua_nv,
            "nhan_vien_id": nhan_vien_id,
            "khoa_id": khoa_id,
            "phan_cong": phan_cong_hien_tai,
            "form": form,
        },
    )


@login_required(login_url="login")
@require_safe
def api_khoa_theo_nhan_vien(request):
    """API JSON trả về danh sách khóa học chưa tham gia hoặc đã tham gia của nhân viên."""
    manv = request.GET.get("manv", "").strip()
    loai = request.GET.get("loai", "chua_tham_gia").strip()

    if not manv:
        return JsonResponse({"khoa": []})

    nv = NhanVien.objects.filter(pk=manv).first()
    if not nv:
        return JsonResponse({"khoa": []})

    if loai == "da_tham_gia":
        ds = KhoaDaoTao.objects.filter(
            danh_sach_phan_cong__nhanvien=nv
        ).values("makhoa", "tenkhoa")
    else:
        ds = services.lay_khoa_chua_phan_cong_cho_nhan_vien(nv).values("makhoa", "tenkhoa")

    return JsonResponse({"khoa": list(ds)})


# ==============================================================================
# KHÔNG GIAN NHÂN VIÊN (EMPLOYEE VIEWS)
# ==============================================================================

def _lay_nhan_vien_hien_tai(user):
    """Lấy hồ sơ nhân viên của người dùng đang đăng nhập."""
    return NhanVien.objects.filter(id_taikhoan=user).first()


@login_required(login_url="login")
@require_safe
def chuong_trinh_cua_toi(request):
    """Màn hình 8: Chương trình đào tạo của tôi (Nhân viên)."""
    services.dong_bo_trang_thai_tat_ca_khoa()
    nv = _lay_nhan_vien_hien_tai(request.user)

    ds_phan_cong = []
    if nv:
        ds_phan_cong = PhanCongDaoTao.objects.filter(nhanvien=nv).select_related("khoadaotao").order_by("-khoadaotao__ngaybatdau")

    return render(
        request,
        "dao_tao/nhan_vien/chuong_trinh_cua_toi.html",
        {
            "nhan_vien": nv,
            "ds_phan_cong": ds_phan_cong,
        },
    )


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def xem_noi_dung_dao_tao(request):
    """Màn hình 9: Xem nội dung đào tạo & Xác nhận hoàn thành (Nhân viên)."""
    services.dong_bo_trang_thai_tat_ca_khoa()
    nv = _lay_nhan_vien_hien_tai(request.user)

    ds_phan_cong = []
    if nv:
        ds_phan_cong = PhanCongDaoTao.objects.filter(nhanvien=nv).select_related("khoadaotao").order_by("-khoadaotao__ngaybatdau")

    khoa_id = request.GET.get("khoa", "").strip() or request.POST.get("khoa", "").strip()
    phan_cong_hien_tai = None

    if ds_phan_cong:
        if khoa_id:
            phan_cong_hien_tai = ds_phan_cong.filter(khoadaotao_id=khoa_id).first()
        if not phan_cong_hien_tai:
            phan_cong_hien_tai = ds_phan_cong.first()

    if request.method == "POST":
        if phan_cong_hien_tai and phan_cong_hien_tai.tiendo != TienDoDaoTao.DA_HOAN_THANH:
            services.xac_nhan_hoan_thanh(phan_cong_hien_tai)
            messages.success(request, f"Đã xác nhận hoàn thành khóa {phan_cong_hien_tai.khoadaotao.tenkhoa}!")
            return redirect(f"{reverse('dao_tao:xem_noi_dung_dao_tao')}?khoa={phan_cong_hien_tai.khoadaotao_id}")

    return render(
        request,
        "dao_tao/nhan_vien/xem_noi_dung.html",
        {
            "nhan_vien": nv,
            "ds_phan_cong": ds_phan_cong,
            "phan_cong": phan_cong_hien_tai,
        },
    )


@login_required(login_url="login")
@require_safe
def ket_qua_dao_tao_cua_toi(request):
    """Màn hình 10: Kết quả đào tạo của tôi (Nhân viên)."""
    nv = _lay_nhan_vien_hien_tai(request.user)

    ds_phan_cong = []
    if nv:
        ds_phan_cong = PhanCongDaoTao.objects.filter(nhanvien=nv).select_related("khoadaotao").order_by("-khoadaotao__ngaybatdau")

    khoa_id = request.GET.get("khoa", "").strip()
    phan_cong_hien_tai = None

    if ds_phan_cong:
        if khoa_id:
            phan_cong_hien_tai = ds_phan_cong.filter(khoadaotao_id=khoa_id).first()
        if not phan_cong_hien_tai:
            phan_cong_hien_tai = ds_phan_cong.first()

    return render(
        request,
        "dao_tao/nhan_vien/ket_qua_cua_toi.html",
        {
            "nhan_vien": nv,
            "ds_phan_cong": ds_phan_cong,
            "phan_cong": phan_cong_hien_tai,
            "KetQuaDaoTao": KetQuaDaoTao,
        },
    )
