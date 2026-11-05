from datetime import timedelta
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

# ------------------------------------------------------------------------------
# 1. IMPORT AN TOÀN CÁC MODEL THEO TÊN LỚP THỰC TẾ
# ------------------------------------------------------------------------------
try:
    from nhan_su.models import NhanVien, BoPhan, HopDong
except Exception:
    NhanVien = BoPhan = HopDong = None

try:
    from cham_cong.models import ChamCong, DonNghiPhep
except Exception:
    ChamCong = DonNghiPhep = None

try:
    from dao_tao.models import Nv_DaoTao
except Exception:
    try:
        from dao_tao.models import NV_DAOTAO as Nv_DaoTao
    except Exception:
        Nv_DaoTao = None


# ------------------------------------------------------------------------------
# 2. XỬ LÝ ĐĂNG NHẬP / ĐĂNG XUẤT / ĐIỀU HƯỚNG VAI TRÒ
# ------------------------------------------------------------------------------
class CakeCrushLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = False

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return reverse_lazy('trang_quan_ly')
        return reverse_lazy('trang_nhan_vien')


class CakeCrushLogoutView(LogoutView):
    next_page = reverse_lazy('login')
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')


@login_required
def dieu_huong_dashboard(request):
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

    # --- A. Thống kê Nhân viên (NhanVien) ---
    tong_nhan_vien = 0
    dang_lam = 0
    da_nghi = 0
    if NhanVien:
        try:
            fields = [f.name for f in NhanVien._meta.get_fields()]
            if 'trangthai' in fields:
                dang_lam = NhanVien.objects.filter(trangthai=True).count()
                da_nghi = NhanVien.objects.filter(trangthai=False).count()
                tong_nhan_vien = dang_lam
            elif 'is_active' in fields:
                dang_lam = NhanVien.objects.filter(is_active=True).count()
                da_nghi = NhanVien.objects.filter(is_active=False).count()
                tong_nhan_vien = dang_lam
            else:
                tong_nhan_vien = NhanVien.objects.count()
                dang_lam = tong_nhan_vien
        except Exception:
            tong_nhan_vien = dang_lam = da_nghi = 0

    # --- B. Thống kê Chấm công trong ngày (ChamCong) ---
    cham_cong_hom_nay = 0
    co_mat = di_muon = vang_mat = 0
    if ChamCong:
        try:
            cc_fields = [f.name for f in ChamCong._meta.get_fields()]
            date_col = 'ngaychamcong' if 'ngaychamcong' in cc_fields else 'ngay'

            qs_cc = ChamCong.objects.filter(**{date_col: today})
            cham_cong_hom_nay = qs_cc.count()

            if 'trangthai' in cc_fields:
                co_mat = qs_cc.filter(trangthai__in=['DILAM', 'co_mat', 'Đi làm']).count()
            elif 'gio_checkin' in cc_fields:
                co_mat = qs_cc.filter(gio_checkin__isnull=False).count()
            else:
                co_mat = cham_cong_hom_nay

            if 'thoigianditre' in cc_fields:
                di_muon = qs_cc.filter(thoigianditre__gt=0).count()
            elif 'di_muon' in cc_fields:
                di_muon = qs_cc.filter(di_muon=True).count()

            vang_mat = max(0, tong_nhan_vien - co_mat)
        except Exception:
            pass

    # --- C. Thống kê Đơn nghỉ phép (DonNghiPhep) ---
    don_nghi_cho_duyet = 0
    don_nghi_da_duyet = 0
    don_nghi_tu_choi = 0
    if DonNghiPhep:
        try:
            don_nghi_cho_duyet = DonNghiPhep.objects.filter(trangthai__in=['CHODUYET', 'cho_duyet', 'Chờ duyệt']).count()
            don_nghi_da_duyet = DonNghiPhep.objects.filter(trangthai__in=['DADUYET', 'da_duyet', 'Đã duyệt']).count()
            don_nghi_tu_choi = DonNghiPhep.objects.filter(trangthai__in=['TUCHOI', 'tu_choi', 'Từ chối']).count()
        except Exception:
            pass

    # --- D. Cảnh báo Hợp đồng sắp hết hạn trong 30 ngày (HopDong) ---
    hop_dong_sap_het_han = 0
    danh_sach_hop_dong = []
    if HopDong:
        try:
            hd_fields = [f.name for f in HopDong._meta.get_fields()]
            exp_col = 'ngayhethan' if 'ngayhethan' in hd_fields else 'ngay_het_han'
            ngay_gioi_han = today + timedelta(days=30)

            qs_hd = HopDong.objects.filter(**{
                f"{exp_col}__isnull": False,
                f"{exp_col}__gte": today,
                f"{exp_col}__lte": ngay_gioi_han
            })
            hop_dong_sap_het_han = qs_hd.count()

            dict_loai_hd = {
                'THU_VIEC': 'Thử việc',
                'XAC_DINH_1_NAM': '1 năm',
                'KHONG_XAC_DINH': 'Không thời hạn'
            }

            for hd in qs_hd[:5]:
                dt_end = getattr(hd, exp_col)
                so_ngay = (dt_end - today).days

                nv_obj = getattr(hd, 'manv', getattr(hd, 'nhan_vien', None))
                ma_nv = getattr(nv_obj, 'manv', getattr(nv_obj, 'ma_nv', f"NV{getattr(hd, 'manv_id', hd.pk)}"))
                ho_ten = getattr(nv_obj, 'tennv', getattr(nv_obj, 'ho_ten', getattr(nv_obj, 'hoten', str(nv_obj))))
                loai_hd_val = getattr(hd, 'loaihd', getattr(hd, 'loai_hop_dong', 'HĐ Lao động'))

                danh_sach_hop_dong.append({
                    'ma_nv': ma_nv,
                    'ho_ten': ho_ten,
                    'loai': dict_loai_hd.get(loai_hd_val, loai_hd_val),
                    'het_han': dt_end.strftime('%d/%m/%Y'),
                    'con_lai': f"{so_ngay} ngày",
                    'canh_bao': 'do' if so_ngay <= 15 else 'vang'
                })
        except Exception:
            pass

    # --- E. Thống kê theo Bộ phận (BoPhan & NhanVien) ---
    bo_phan_list = []
    if BoPhan and NhanVien:
        try:
            nv_fields = [f.name for f in NhanVien._meta.get_fields()]
            bp_fk = 'maphong' if 'maphong' in nv_fields else 'bo_phan'

            for bp in BoPhan.objects.all():
                query = {bp_fk: bp}
                if 'trangthai' in nv_fields:
                    query['trangthai'] = True
                elif 'is_active' in nv_fields:
                    query['is_active'] = True

                count_nv = NhanVien.objects.filter(**query).count()
                pct = int((count_nv / tong_nhan_vien) * 100) if tong_nhan_vien > 0 else 0
                ten_bp = getattr(bp, 'tenphongban', getattr(bp, 'ten_bo_phan', getattr(bp, 'ten', str(bp))))

                bo_phan_list.append({
                    'ten': ten_bp,
                    'so_luong': count_nv,
                    'phan_tram': pct
                })
        except Exception:
            pass

    # Đảm bảo luôn có đủ 5 bộ phận chuẩn của Cake Crush
    cac_bo_phan_chuan = ['Bếp bánh', 'Bán hàng', 'Thu ngân', 'Pha chế', 'Kho vận']
    ten_hien_co = [b['ten'] for b in bo_phan_list]
    for ten in cac_bo_phan_chuan:
        if ten not in ten_hien_co:
            c = 0
            if NhanVien:
                try:
                    c = NhanVien.objects.filter(chucvu__icontains=ten).count()
                except Exception:
                    c = 0
            pct = int((c / tong_nhan_vien) * 100) if tong_nhan_vien > 0 else 0
            bo_phan_list.append({
                'ten': ten,
                'so_luong': c,
                'phan_tram': pct
            })

    # --- F. Tình trạng Đào tạo (Nv_DaoTao) ---
    dao_tao = {
        'chua_hoc': 0,
        'dang_hoc': 0,
        'da_hoc': 0,
        'dat': 0,
        'chua_dat': 0
    }
    if Nv_DaoTao:
        try:
            dao_tao['chua_hoc'] = Nv_DaoTao.objects.filter(trangthai__in=['CHUA_HOC', 'chua_hoc']).count()
            dao_tao['dang_hoc'] = Nv_DaoTao.objects.filter(trangthai__in=['DANG_HOC', 'dang_hoc']).count()
            dao_tao['da_hoc'] = Nv_DaoTao.objects.filter(trangthai__in=['DA_HOC', 'da_hoc']).count()
            dao_tao['dat'] = Nv_DaoTao.objects.filter(ketqua__in=['DAT', 'dat']).count()
            dao_tao['chua_dat'] = Nv_DaoTao.objects.filter(ketqua__in=['CHUA_DAT', 'chua_dat']).count()
        except Exception:
            pass

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
        'danh_sach_hop_dong': danh_sach_hop_dong,
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