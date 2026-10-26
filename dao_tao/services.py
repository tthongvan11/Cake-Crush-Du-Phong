import re
from django.db import transaction
from django.utils import timezone
from .models import KhoaDaoTao, PhanCongDaoTao, TrangThaiKhoa, TienDoDaoTao, KetQuaDaoTao


def tao_ma_khoa():
    """Sinh mã khóa đào tạo tự động tăng: DT001, DT002, DT003..."""
    ds_ma = KhoaDaoTao.objects.filter(makhoa__startswith="DT").values_list("makhoa", flat=True)
    so_lon_nhat = 0
    for ma in ds_ma:
        match = re.match(r"^DT(\d+)$", ma)
        if match:
            so = int(match.group(1))
            if so > so_lon_nhat:
                so_lon_nhat = so
    return f"DT{str(so_lon_nhat + 1).zfill(3)}"


def dong_bo_trang_thai_tat_ca_khoa():
    """Cập nhật lại trạng thái các khóa học dựa trên ngày hiện tại nếu khóa không bị gán cứng."""
    hom_nay = timezone.localdate()
    for khoa in KhoaDaoTao.objects.all():
        tt_moi = khoa.tinh_trang_thai_tu_dong(hom_nay)
        if khoa.trangthai != tt_moi:
            khoa.trangthai = tt_moi
            khoa.save(update_fields=["trangthai"])


def lay_thong_ke_dao_tao():
    """Tính toán 4 thẻ thống kê ở đầu trang danh sách khóa đào tạo."""
    dong_bo_trang_thai_tat_ca_khoa()
    tong = KhoaDaoTao.objects.count()
    dang_dien_ra = KhoaDaoTao.objects.filter(trangthai=TrangThaiKhoa.DANG_DIEN_RA).count()
    chua_bat_dau = KhoaDaoTao.objects.filter(trangthai=TrangThaiKhoa.CHUA_BAT_DAU).count()
    da_ket_thuc = KhoaDaoTao.objects.filter(trangthai=TrangThaiKhoa.DA_KET_THUC).count()

    pt_dang_dien_ra = round((dang_dien_ra / tong * 100)) if tong > 0 else 0
    pt_da_ket_thuc = round((da_ket_thuc / tong * 100)) if tong > 0 else 0

    return {
        "tong_khoa": tong,
        "dang_dien_ra": dang_dien_ra,
        "pt_dang_dien_ra": pt_dang_dien_ra,
        "chua_bat_dau": chua_bat_dau,
        "da_ket_thuc": da_ket_thuc,
        "pt_da_ket_thuc": pt_da_ket_thuc,
    }


def lay_khoa_chua_phan_cong_cho_nhan_vien(nhan_vien):
    """Lấy danh sách các khóa học mà nhân viên này chưa tham gia và chưa kết thúc."""
    dong_bo_trang_thai_tat_ca_khoa()
    khoa_da_tham_gia = PhanCongDaoTao.objects.filter(nhanvien=nhan_vien).values_list("khoadaotao_id", flat=True)
    return KhoaDaoTao.objects.exclude(makhoa__in=khoa_da_tham_gia).exclude(trangthai=TrangThaiKhoa.DA_KET_THUC)


@transaction.atomic
def phan_cong_nhan_vien(nhan_vien, khoa_dao_tao):
    """Phân công nhân viên vào khóa đào tạo."""
    phan_cong, created = PhanCongDaoTao.objects.get_or_create(
        nhanvien=nhan_vien,
        khoadaotao=khoa_dao_tao,
        defaults={
            "tiendo": TienDoDaoTao.CHUA_HOAN_THANH,
            "ketqua": KetQuaDaoTao.CHO_DANH_GIA,
        },
    )
    return phan_cong, created


@transaction.atomic
def xac_nhan_hoan_thanh(phan_cong):
    """Nhân viên tự xác nhận hoàn thành nội dung đào tạo."""
    phan_cong.tiendo = TienDoDaoTao.DA_HOAN_THANH
    phan_cong.ngayhoanthanh = timezone.localdate()
    phan_cong.save(update_fields=["tiendo", "ngayhoanthanh", "ngaycapnhat"])
    return phan_cong


@transaction.atomic
def cap_nhat_ket_qua_dao_tao(phan_cong, ket_qua, nguoi_danh_gia=None):
    """Quản lý chấm điểm kết quả đào tạo: Đạt hoặc Chưa đạt."""
    phan_cong.ketqua = ket_qua
    phan_cong.ngaydanhgia = timezone.localdate()
    if nguoi_danh_gia:
        phan_cong.nguoidanhgia = nguoi_danh_gia
    phan_cong.save(update_fields=["ketqua", "ngaydanhgia", "nguoidanhgia", "ngaycapnhat"])
    return phan_cong
