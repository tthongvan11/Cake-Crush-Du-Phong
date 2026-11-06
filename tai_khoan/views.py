from datetime import timedelta
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from cham_cong.models import ChamCong, DonNghiPhep
from dao_tao.models import KhoaDaoTao, PhanCongDaoTao
from nhan_su.models import HopDong, NhanVien, PhongBan


# ------------------------------------------------------------------------------
# 2. XỬ LÝ ĐĂNG NHẬP / ĐĂNG XUẤT / ĐIỀU HƯỚNG VAI TRÒ
# ------------------------------------------------------------------------------
class CakeCrushLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = False

    def get_success_url(self):
        user = self.request.user
        # Cả Admin (superuser) và Quản lý (staff) đều vào Dashboard Quản lý
        if user.is_superuser or user.is_staff:
            return reverse_lazy('trang_quan_ly')
        return reverse_lazy('trang_nhan_vien')


class CakeCrushLogoutView(LogoutView):
    next_page = reverse_lazy('login')
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')


def dieu_huong_dashboard(request):
    """Điều hướng người dùng đã đăng nhập tới dashboard tương ứng"""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_superuser or request.user.is_staff:
        return redirect('trang_quan_ly')
    return redirect('trang_nhan_vien')


@login_required
def trang_nhan_vien(request):
    return render(request, 'nhan_vien_home.html')


# ------------------------------------------------------------------------------
# 3. DASHBOARD QUẢN LÝ: TRUY VẤN VÀ TỰ ĐỘNG CẬP NHẬT THEO CSDL
# ------------------------------------------------------------------------------
@login_required
def trang_quan_ly(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('trang_nhan_vien')

    today = timezone.localdate()

    nhan_vien_dang_lam = NhanVien.objects.filter(trangthai=True)
    tong_nhan_vien = nhan_vien_dang_lam.count()
    dang_lam = tong_nhan_vien
    da_nghi = NhanVien.objects.filter(trangthai=False).count()

    cham_cong_hom_nay_qs = ChamCong.objects.filter(ngaychamcong=today)
    cham_cong_hom_nay = cham_cong_hom_nay_qs.count()
    co_mat = cham_cong_hom_nay_qs.filter(trangthai=ChamCong.TrangThai.DI_LAM).count()
    di_muon = cham_cong_hom_nay_qs.filter(
        trangthai=ChamCong.TrangThai.DI_LAM, thoigianditre__gt=0
    ).count()
    nhan_vien_nghi_phep = DonNghiPhep.objects.filter(
        trangthai=DonNghiPhep.TrangThai.DA_DUYET,
        ngaybatdau__lte=today,
        ngayketthuc__gte=today,
        manv__trangthai=True,
    ).values("manv_id").distinct().count()
    vang_mat = max(0, tong_nhan_vien - co_mat - nhan_vien_nghi_phep)

    don_nghi_cho_duyet = DonNghiPhep.objects.filter(
        trangthai=DonNghiPhep.TrangThai.CHO_DUYET
    ).count()
    don_nghi_da_duyet = DonNghiPhep.objects.filter(
        trangthai=DonNghiPhep.TrangThai.DA_DUYET
    ).count()
    don_nghi_tu_choi = DonNghiPhep.objects.filter(
        trangthai=DonNghiPhep.TrangThai.TU_CHOI
    ).count()

    ngay_gioi_han = today + timedelta(days=30)
    qs_hd = HopDong.objects.filter(
        manv__trangthai=True,
        ngayhethan__gte=today,
        ngayhethan__lte=ngay_gioi_han,
    ).exclude(trangthai=HopDong.TrangThai.CHAM_DUT).select_related("manv").order_by(
        "ngayhethan", "manv__tennv"
    )
    hop_dong_sap_het_han = qs_hd.count()
    danh_sach_hop_dong = []
    for hd in qs_hd:
        so_ngay = (hd.ngayhethan - today).days
        danh_sach_hop_dong.append({
            "ma_nv": hd.manv.manv,
            "ho_ten": hd.manv.tennv,
            "loai": hd.get_loaihd_display(),
            "het_han": hd.ngayhethan.strftime("%d/%m/%Y"),
            "con_lai": f"{so_ngay} ngày",
            "canh_bao": "do" if so_ngay <= 15 else "vang",
        })
    hop_dong_hien_thi = danh_sach_hop_dong[:3]
    hop_dong_xem_them = danh_sach_hop_dong[3:]

    bo_phan_list = []
    for phong in PhongBan.objects.annotate(
        so_nhan_vien=Count("nhan_vien", filter=Q(nhan_vien__trangthai=True))
    ).order_by("tenphongban"):
        bo_phan_list.append({
            "ten": phong.tenphongban,
            "so_luong": phong.so_nhan_vien,
            "phan_tram": round(phong.so_nhan_vien * 100 / tong_nhan_vien) if tong_nhan_vien else 0,
        })

    dao_tao = {
        "chua_hoc": KhoaDaoTao.objects.filter(ngaybatdau__gt=today).count(),
        "dang_hoc": KhoaDaoTao.objects.filter(ngaybatdau__lte=today, ngayketthuc__gte=today).count(),
        "da_hoc": KhoaDaoTao.objects.filter(ngayketthuc__lt=today).count(),
        "dat": PhanCongDaoTao.objects.filter(ketqua="Đạt").count(),
        "chua_dat": PhanCongDaoTao.objects.filter(ketqua="Chưa đạt").count(),
    }

    context = {
        'tong_nhan_vien': tong_nhan_vien,
        'dang_lam': dang_lam,
        'da_nghi': da_nghi,
        'cham_cong_hom_nay': cham_cong_hom_nay,
        'don_nghi_cho_duyet': don_nghi_cho_duyet,
        'don_nghi_da_duyet': don_nghi_da_duyet,
        'don_nghi_tu_choi': don_nghi_tu_choi,
        'hop_dong_sap_het_han': hop_dong_sap_het_han,
        'diem_danh': {'co_mat': co_mat, 'di_muon': di_muon, 'vang_mat': vang_mat},
        'bo_phan': bo_phan_list,
        'danh_sach_hop_dong': hop_dong_hien_thi,
        'hop_dong_xem_them': hop_dong_xem_them,
        'dao_tao': dao_tao,
    }
    return render(request, 'quan_ly_home.html', context)


# ------------------------------------------------------------------------------
# 4. TRANG CHÀO MỪNG VÀ TRANG CHỦ (LUÔN HIỂN THỊ WELCOME.HTML)
# ------------------------------------------------------------------------------
def trang_chao_mung(request):
    try:
        return render(request, 'welcome.html')
    except Exception:
        return redirect('login')


def trang_chu(request):
    try:
        return render(request, 'welcome.html')
    except Exception:
        return redirect('login')
