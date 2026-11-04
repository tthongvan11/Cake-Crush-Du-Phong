from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

# Import models an toàn (tránh lỗi nếu chưa migrate hoặc thiếu app)
try:
    from nhan_su.models import NhanVien, HopDong, BoPhan
except Exception:
    NhanVien = HopDong = BoPhan = None

try:
    from cham_cong.models import ChamCong
except Exception:
    ChamCong = None


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


@login_required
def trang_quan_ly(request):
    # 1. Chặn nhân viên thường cố tình gõ link /quan-ly/
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('trang_nhan_vien')

    today = timezone.localdate()

    # 2. Truy vấn số liệu thực tế (nếu rỗng hoặc lỗi sẽ mặc định là 0)
    try:
        tong_nhan_vien = NhanVien.objects.count() if NhanVien else 0
    except Exception:
        tong_nhan_vien = 0

    try:
        cham_cong_hom_nay = ChamCong.objects.filter(ngay=today).count() if ChamCong else 0
    except Exception:
        cham_cong_hom_nay = 0

    don_nghi_cho_duyet = 0
    try:
        from nhan_su.models import NghiPhep
        don_nghi_cho_duyet = NghiPhep.objects.filter(trang_thai='cho_duyet').count()
    except Exception:
        pass

    hop_dong_sap_het_han = 0
    danh_sach_hop_dong = []
    try:
        if HopDong:
            ngay_gioi_han = today + timedelta(days=30)
            qs = HopDong.objects.filter(ngay_het_han__gte=today, ngay_het_han__lte=ngay_gioi_han)
            hop_dong_sap_het_han = qs.count()
            for hd in qs[:5]:
                so_ngay = (hd.ngay_het_han - today).days
                danh_sach_hop_dong.append({
                    'ma_nv': getattr(hd.nhan_vien, 'ma_nv', f"NV{hd.nhan_vien_id}"),
                    'ho_ten': getattr(hd.nhan_vien, 'ho_ten', str(hd.nhan_vien)),
                    'loai': getattr(hd, 'loai_hop_dong', 'HĐ Lao động'),
                    'het_han': hd.ngay_het_han.strftime('%d/%m/%Y'),
                    'con_lai': f"{so_ngay} ngày",
                    'canh_bao': 'do' if so_ngay <= 15 else 'vang'
                })
    except Exception:
        pass

    # Thống kê điểm danh hôm nay
    co_mat = di_muon = vang_mat = 0
    try:
        if ChamCong:
            co_mat = ChamCong.objects.filter(ngay=today, trang_thai='co_mat').count()
            di_muon = ChamCong.objects.filter(ngay=today, trang_thai='di_muon').count()
            vang_mat = max(0, tong_nhan_vien - (co_mat + di_muon))
    except Exception:
        pass

    # Thống kê theo phòng ban
    bo_phan_list = []
    try:
        if BoPhan and NhanVien:
            for bp in BoPhan.objects.all():
                c = NhanVien.objects.filter(bo_phan=bp).count()
                pct = int((c / tong_nhan_vien) * 100) if tong_nhan_vien > 0 else 0
                bo_phan_list.append({
                    'ten': getattr(bp, 'ten_bo_phan', str(bp)),
                    'so_luong': c,
                    'phan_tram': pct
                })
    except Exception:
        pass

    context = {
        'tong_nhan_vien': tong_nhan_vien,
        'cham_cong_hom_nay': cham_cong_hom_nay,
        'don_nghi_cho_duyet': don_nghi_cho_duyet,
        'hop_dong_sap_het_han': hop_dong_sap_het_han,
        'diem_danh': {'co_mat': co_mat, 'di_muon': di_muon, 'vang_mat': vang_mat},
        'bo_phan': bo_phan_list,
        'danh_sach_hop_dong': danh_sach_hop_dong,
    }
    return render(request, 'quan_ly_home.html', context)


def trang_chao_mung(request):
    """Trang chào mừng Cake Crush HR"""
    return render(request, 'welcome.html')


def trang_chu(request):
    """Trang chủ hiển thị trang chào mừng"""
    return render(request, 'welcome.html')
