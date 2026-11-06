from dataclasses import dataclass  # Tạo lớp dữ liệu gọn cho từng dòng bảng công.
from datetime import date, datetime, time, timedelta  # Làm việc với ngày và giờ.
from decimal import ROUND_HALF_UP, Decimal  # Làm tròn số giờ chính xác 2 chữ số thập phân.

from django.conf import settings  # Đọc cấu hình ca làm việc trong settings.py.
from django.core.exceptions import ValidationError  # Lỗi nghiệp vụ trả về cho giao diện.
from django.db import DatabaseError, IntegrityError, transaction  # Lỗi database và giao dịch an toàn.
from django.db.models import Q  # Kết hợp điều kiện truy vấn.
from django.utils import timezone  # Lấy giờ máy chủ theo múi giờ Việt Nam.

from nhan_su.models import NhanVien  # Hồ sơ nhân viên của phân hệ nhân sự.

from .models import ChamCong, DonNghiPhep  # Hai bảng nghiệp vụ của phân hệ này.


# ===================== CẤU HÌNH CA LÀM VIỆC =====================

MAC_DINH = {  # Giá trị dùng khi settings.py chưa khai báo CHAM_CONG.
    "GIO_BAT_DAU": "08:00",  # Giờ bắt đầu ca hành chính.
    "GIO_KET_THUC": "17:00",  # Giờ kết thúc ca hành chính.
    "NGHI_TRUA_BAT_DAU": "12:00",  # Bắt đầu nghỉ trưa, không tính công.
    "NGHI_TRUA_KET_THUC": "13:00",  # Kết thúc nghỉ trưa.
    "PHEP_NAM": 12,  # Số ngày phép năm của mỗi nhân viên.
}  # Kết thúc giá trị mặc định.


def cau_hinh(khoa):  # Đọc một mục cấu hình chấm công.
    gia_tri = getattr(settings, "CHAM_CONG", {}).get(khoa, MAC_DINH[khoa])  # Ưu tiên settings, thiếu thì dùng mặc định.
    if khoa == "PHEP_NAM":  # Quỹ phép là số nguyên.
        return int(gia_tri)  # Trả về số ngày.
    return time.fromisoformat(gia_tri)  # Chuỗi "08:00" thành đối tượng giờ.


def ca_lam_viec():  # Trả chuỗi ca hiển thị trên giao diện.
    return f"{cau_hinh('GIO_BAT_DAU'):%H:%M} – {cau_hinh('GIO_KET_THUC'):%H:%M}"  # Ví dụ 08:00 – 17:00.


# ===================== TÍNH TOÁN GIỜ CÔNG =====================

def _phut(gio):  # Đổi giờ trong ngày thành số phút tính từ 00:00.
    return gio.hour * 60 + gio.minute  # Bỏ qua giây để đếm phút tròn như mockup.


def _doi_gio(so_phut):  # Đổi số phút thành số giờ thập phân 2 chữ số.
    return (Decimal(so_phut) / Decimal(60)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # 453 phút → 7,55 giờ.


def tinh_di_tre(gio_checkin):  # Số phút đi trễ so với giờ bắt đầu ca.
    return max(0, _phut(gio_checkin) - _phut(cau_hinh("GIO_BAT_DAU")))  # Không đi trễ thì bằng 0.


def tinh_vao_som(gio_checkin):  # Số phút Check-in trước giờ bắt đầu ca (chỉ để hiển thị).
    return max(0, _phut(cau_hinh("GIO_BAT_DAU")) - _phut(gio_checkin))  # Vào đúng giờ hoặc trễ thì bằng 0.


def tinh_ket_qua_checkout(gio_checkin, gio_checkout):  # Tính các chỉ số khi Check-out.
    vao, ra = _phut(gio_checkin), _phut(gio_checkout)  # Đổi giờ vào, giờ ra sang phút.
    trua_bd, trua_kt = _phut(cau_hinh("NGHI_TRUA_BAT_DAU")), _phut(cau_hinh("NGHI_TRUA_KET_THUC"))  # Khung nghỉ trưa.
    trung_gio_trua = max(0, min(ra, trua_kt) - max(vao, trua_bd))  # Phần thời gian làm việc trùng nghỉ trưa.
    ket_thuc_ca = _phut(cau_hinh("GIO_KET_THUC"))  # Giờ kết thúc ca tính bằng phút.
    return {  # Trả các giá trị để lưu vào bản ghi.
        "sogiolamviec": _doi_gio(max(0, ra - vao - trung_gio_trua)),  # Giờ ra − giờ vào − nghỉ trưa.
        "thoigianvesom": max(0, ket_thuc_ca - ra),  # Ra trước 17:00 là về sớm.
        "sogiolamthem": _doi_gio(max(0, ra - max(vao, ket_thuc_ca))),  # Chỉ tính phần làm sau 17:00.
    }  # Kết thúc kết quả tính.


def _gio_may_chu(bay_gio=None):  # Lấy giờ máy chủ theo múi giờ của dự án.
    bay_gio = timezone.localtime(bay_gio) if bay_gio else timezone.localtime()  # Chuyển về giờ Việt Nam.
    return bay_gio.date(), bay_gio.time().replace(microsecond=0)  # Tách ngày và giờ, bỏ phần micro giây.


# ===================== CHECK-IN / CHECK-OUT =====================

def lay_nhan_vien(user):  # Tìm hồ sơ nhân viên của tài khoản đang đăng nhập.
    return NhanVien.objects.select_related("maphong").filter(id_taikhoan=user).first()  # Không có hồ sơ thì trả None.


def cham_cong_hom_nay(nv, bay_gio=None):  # Lấy bản ghi chấm công hôm nay của nhân viên.
    ngay, _ = _gio_may_chu(bay_gio)  # Ngày hiện tại theo giờ máy chủ.
    return ChamCong.objects.filter(manv=nv, ngaychamcong=ngay).first()  # Chưa có thì trả None.


def check_in(nv, bay_gio=None):  # UC-CC-3.01: ghi nhận giờ bắt đầu làm việc.
    ngay, gio = _gio_may_chu(bay_gio)  # Thời gian lấy theo máy chủ, nhân viên không tự nhập.
    ban_ghi = ChamCong.objects.filter(manv=nv, ngaychamcong=ngay).first()  # Kiểm tra dữ liệu trong ngày.
    if ban_ghi and ban_ghi.trangthai == ChamCong.TrangThai.NGHI_PHEP:  # Hôm nay đã có đơn nghỉ được duyệt.
        raise ValidationError("Hôm nay bạn đang nghỉ có phép, không cần Check-in.")  # Không ghi đè ngày nghỉ.
    if ban_ghi and ban_ghi.gio_checkin:  # Đã Check-in trước đó.
        raise ValidationError("Bạn đã Check-in trong ngày hôm nay")  # Không ghi đè, không tạo bản ghi trùng.
    try:  # Bắt lỗi khi lưu dữ liệu.
        return ChamCong.objects.create(  # Tạo bản ghi chấm công của ngày.
            manv=nv, ngaychamcong=ngay, gio_checkin=gio,  # Nhân viên, ngày và giờ Check-in.
            thoigianditre=tinh_di_tre(gio),  # Lưu số phút đi trễ (0 nếu đúng giờ).
            trangthai=ChamCong.TrangThai.DI_LAM,  # Trạng thái Đi làm.
        )  # Kết thúc tạo bản ghi.
    except (IntegrityError, DatabaseError):  # Lưu thất bại hoặc bấm 2 lần cùng lúc.
        raise ValidationError("Check-in thất bại, vui lòng thử lại")  # Giữ nguyên dữ liệu trước đó.


def check_out(nv, bay_gio=None):  # UC-CC-3.02: ghi nhận giờ kết thúc làm việc.
    ngay, gio = _gio_may_chu(bay_gio)  # Thời gian lấy theo máy chủ.
    ban_ghi = ChamCong.objects.filter(manv=nv, ngaychamcong=ngay).first()  # Bản ghi đã tạo khi Check-in.
    if not ban_ghi or not ban_ghi.gio_checkin:  # Chưa Check-in.
        raise ValidationError("Bạn chưa Check-in trong ngày hôm nay")  # Không ghi nhận Check-out.
    if ban_ghi.gio_checkout:  # Đã Check-out trước đó.
        raise ValidationError("Bạn đã Check-out trong ngày hôm nay")  # Không thay đổi dữ liệu đã lưu.
    if gio < ban_ghi.gio_checkin:  # Giờ ra nhỏ hơn giờ vào.
        raise ValidationError("Thời gian Check-out không hợp lệ, vui lòng thử lại")  # Không lưu thay đổi.
    ban_ghi.gio_checkout = gio  # Gán giờ Check-out.
    for truong, gia_tri in tinh_ket_qua_checkout(ban_ghi.gio_checkin, gio).items():  # Gán giờ làm, về sớm, làm thêm.
        setattr(ban_ghi, truong, gia_tri)  # Gán từng trường vào bản ghi.
    try:  # Bắt lỗi khi lưu dữ liệu.
        ban_ghi.save()  # Cập nhật cùng bản ghi đã Check-in.
    except DatabaseError:  # Lưu thất bại.
        raise ValidationError("Check-out thất bại, vui lòng thử lại")  # Giữ nguyên dữ liệu đã có.
    return ban_ghi  # Trả bản ghi đã cập nhật.


def trang_thai_trong_ngay(ban_ghi):  # Chuỗi trạng thái hiển thị ở khung "Thông tin làm việc".
    if not ban_ghi:  # Chưa có bản ghi.
        return "Chưa chấm công"  # Trạng thái ban đầu.
    if ban_ghi.trangthai == ChamCong.TrangThai.NGHI_PHEP:  # Ngày nghỉ có phép.
        return "Nghỉ có phép"  # Trạng thái nghỉ.
    loi = []  # Danh sách vi phạm trong ngày.
    if ban_ghi.thoigianditre:  # Có phút đi trễ.
        loi.append("Đi trễ")  # Thêm vi phạm đi trễ.
    if ban_ghi.thoigianvesom:  # Có phút về sớm.
        loi.append("về sớm" if loi else "Về sớm")  # Viết thường khi đứng sau "Đi trễ".
    if loi:  # Có ít nhất một vi phạm.
        return ", ".join(loi)  # Ví dụ "Đi trễ, về sớm".
    return "Đã hoàn tất chấm công" if ban_ghi.gio_checkout else "Đang làm việc"  # Đúng giờ.


# ===================== BẢNG CÔNG (LỊCH SỬ + TỔNG HỢP) =====================

@dataclass  # Lớp chỉ chứa dữ liệu một dòng hiển thị.
class DongCong:  # Một dòng = 1 nhân viên × 1 ngày.
    nv: NhanVien  # Hồ sơ nhân viên.
    ngay: date  # Ngày chấm công.
    trangthai: str  # Mã trạng thái DILAM / NGHIPHEP / VANGKHONGPHEP.
    ban_ghi: ChamCong | None = None  # Bản ghi thật; None nếu là ngày vắng do hệ thống suy ra.

    @property  # Dùng như thuộc tính trong template.
    def nhan_trang_thai(self):  # Nhãn tiếng Việt của trạng thái.
        return ChamCong.TrangThai(self.trangthai).label  # Ví dụ "Đi làm".


def _cac_ngay_trong_thang(nam, thang):  # Danh sách ngày của một tháng.
    ngay = date(nam, thang, 1)  # Ngày đầu tháng.
    while ngay.month == thang:  # Lặp đến hết tháng.
        yield ngay  # Trả từng ngày.
        ngay += timedelta(days=1)  # Sang ngày kế tiếp.


def tao_bang_cong(nam, thang, ds_nhan_vien, trang_thai="", hom_nay=None):  # Dựng bảng công cho nhiều nhân viên.
    hom_nay = hom_nay or timezone.localdate()  # Ngày hiện tại theo máy chủ.
    ds_nhan_vien = list(ds_nhan_vien)  # Đọc danh sách nhân viên một lần.
    ban_ghi = {  # Tra cứu nhanh theo cặp (mã NV, ngày).
        (bg.manv_id, bg.ngaychamcong): bg  # Khóa là mã nhân viên và ngày.
        for bg in ChamCong.objects.filter(  # Chỉ lấy dữ liệu trong tháng đang xem.
            manv__in=ds_nhan_vien, ngaychamcong__year=nam, ngaychamcong__month=thang,  # Lọc theo nhân viên và tháng.
        )  # Kết thúc truy vấn.
    }  # Kết thúc từ điển tra cứu.
    dong = []  # Danh sách dòng kết quả.
    for nv in ds_nhan_vien:  # Duyệt từng nhân viên.
        for ngay in _cac_ngay_trong_thang(nam, thang):  # Duyệt từng ngày trong tháng.
            bg = ban_ghi.get((nv.manv, ngay))  # Bản ghi thật nếu có.
            if bg:  # Có dữ liệu chấm công hoặc ngày nghỉ phép.
                dong.append(DongCong(nv, ngay, bg.trangthai, bg))  # Thêm dòng từ dữ liệu thật.
            elif (  # Không có dữ liệu: xét có phải vắng không phép.
                ngay < hom_nay  # Ngày đã qua (tiệm bánh làm cả tuần nên xét cả Chủ nhật).
                and nv.ngayvaolam <= ngay  # Đã vào làm.
                and (nv.ngaynghiviec is None or ngay <= nv.ngaynghiviec)  # Chưa nghỉ việc.
            ):  # Đủ điều kiện tính vắng.
                dong.append(DongCong(nv, ngay, ChamCong.TrangThai.VANG_KHONG_PHEP))  # Hiển thị Vắng không phép.
    if trang_thai:  # Có lọc theo trạng thái.
        dong = [d for d in dong if d.trangthai == trang_thai]  # Giữ dòng đúng trạng thái.
    dong.sort(key=lambda d: (-d.ngay.toordinal(), d.nv.tennv, d.nv.manv))  # Ngày mới trước, rồi theo tên.
    return dong  # Trả danh sách dòng.


def thong_ke_bang_cong(dong):  # Số liệu 4 thẻ tổng hợp phía trên bảng.
    return {  # Đếm theo từng trạng thái.
        "so_nhan_vien": len({d.nv.manv for d in dong}),  # Số nhân viên khác nhau đang xem.
        "di_lam": sum(d.trangthai == ChamCong.TrangThai.DI_LAM for d in dong),  # Lượt đi làm.
        "nghi_phep": sum(d.trangthai == ChamCong.TrangThai.NGHI_PHEP for d in dong),  # Lượt nghỉ có phép.
        "vang": sum(d.trangthai == ChamCong.TrangThai.VANG_KHONG_PHEP for d in dong),  # Lượt vắng không phép.
        "tong_gio": sum((d.ban_ghi.sogiolamviec or 0 for d in dong if d.ban_ghi), Decimal("0")),  # Tổng giờ làm.
        "di_tre": sum(d.ban_ghi.thoigianditre or 0 for d in dong if d.ban_ghi),  # Tổng phút đi trễ.
        "ve_som": sum(d.ban_ghi.thoigianvesom or 0 for d in dong if d.ban_ghi),  # Tổng phút về sớm.
    }  # Kết thúc thống kê.


# ===================== QUỸ PHÉP NĂM =====================

def so_ngay_nghi(ngay_bat_dau, ngay_ket_thuc):  # Đếm mọi ngày, tính cả hai đầu.
    return (ngay_ket_thuc - ngay_bat_dau).days + 1  # Ví dụ 08/10 → 09/10 là 2 ngày.


def so_ngay_trong_nam(ngay_bat_dau, ngay_ket_thuc, nam):  # Số ngày của đơn rơi vào một năm.
    dau = max(ngay_bat_dau, date(nam, 1, 1))  # Ngày đầu tiên của đơn trong năm đó.
    cuoi = min(ngay_ket_thuc, date(nam, 12, 31))  # Ngày cuối cùng của đơn trong năm đó.
    return max(0, (cuoi - dau).days + 1)  # Ví dụ 30/12 → 02/01: năm cũ 2 ngày, năm mới 2 ngày.


def giao_voi_nam(nam):  # Điều kiện lọc đơn có ít nhất một ngày nằm trong năm (kể cả đơn kéo dài qua 2 năm).
    return Q(ngaybatdau__lte=date(nam, 12, 31), ngayketthuc__gte=date(nam, 1, 1))  # Khoảng ngày giao với năm.


def don_tru_phep_trong_nam(nam):  # Điều kiện lọc đơn phép năm có ít nhất một ngày trong năm.
    return giao_voi_nam(nam) & Q(maloaiphep__tru_phepnam=True)  # Chỉ loại có trừ phép năm.


def _tong_phep(nv, nam, trang_thai):  # Cộng số ngày (thuộc năm đang xét) của đơn trừ phép theo trạng thái.
    ds = DonNghiPhep.objects.filter(don_tru_phep_trong_nam(nam), manv=nv, trangthai=trang_thai)  # Đơn giao với năm.
    return sum(so_ngay_trong_nam(d.ngaybatdau, d.ngayketthuc, nam) for d in ds)  # Chỉ cộng phần ngày của năm đó.


def thong_ke_phep(nv, nam):  # Quỹ phép của một nhân viên trong năm.
    tong = cau_hinh("PHEP_NAM")  # Hạn ngạch chung 12 ngày.
    da_dung = _tong_phep(nv, nam, DonNghiPhep.TrangThai.DA_DUYET)  # Chỉ đơn đã duyệt mới trừ phép.
    cho_duyet = _tong_phep(nv, nam, DonNghiPhep.TrangThai.CHO_DUYET)  # Đơn chờ duyệt chưa trừ phép.
    con_lai = tong - da_dung  # Còn lại = Tổng hạn ngạch − Số ngày đã duyệt.
    return {  # Trả số liệu cho giao diện.
        "tong": tong, "da_dung": da_dung, "con_lai": con_lai, "cho_duyet": cho_duyet,  # Bốn con số chính.
        "vuot_quy": max(0, cho_duyet - con_lai),  # Số ngày chờ duyệt vượt quá phép còn lại.
    }  # Kết thúc thống kê.


def danh_sach_quy_phep(ds_nhan_vien, nam):  # Quỹ phép của nhiều nhân viên (trang Quản lý quỹ phép).
    tong = cau_hinh("PHEP_NAM")  # Hạn ngạch chung.
    ds_nhan_vien = list(ds_nhan_vien)  # Đọc danh sách nhân viên một lần.
    cong = {nv.manv: {"DADUYET": 0, "CHODUYET": 0} for nv in ds_nhan_vien}  # Bộ đếm theo nhân viên và trạng thái.
    for d in DonNghiPhep.objects.filter(  # Một truy vấn cho tất cả nhân viên.
        don_tru_phep_trong_nam(nam), manv__in=ds_nhan_vien, trangthai__in=["DADUYET", "CHODUYET"],  # Đơn liên quan.
    ):  # Duyệt từng đơn.
        cong[d.manv_id][d.trangthai] += so_ngay_trong_nam(d.ngaybatdau, d.ngayketthuc, nam)  # Chỉ phần ngày của năm.
    ket_qua = []  # Danh sách dòng hiển thị.
    for nv in ds_nhan_vien:  # Duyệt từng nhân viên.
        da_dung, cho_duyet = cong[nv.manv]["DADUYET"], cong[nv.manv]["CHODUYET"]  # Số ngày đã dùng, chờ duyệt.
        ket_qua.append({  # Thêm một dòng.
            "nv": nv, "tong": tong, "da_dung": da_dung, "con_lai": tong - da_dung, "cho_duyet": cho_duyet,  # Số liệu.
            "vuot_quy": max(0, cho_duyet - (tong - da_dung)),  # Cảnh báo đỏ khi > 0.
        })  # Kết thúc một dòng.
    return ket_qua  # Trả danh sách.


def quy_theo_tung_nam(nv, ngay_bat_dau, ngay_ket_thuc):  # Quỹ phép của từng năm mà đơn đi qua.
    ket_qua = []  # Một phần tử cho mỗi năm.
    for nam in range(ngay_bat_dau.year, ngay_ket_thuc.year + 1):  # Thường 1 năm; đơn qua năm mới thì 2 năm.
        quy = thong_ke_phep(nv, nam)  # Quỹ phép của năm đó.
        so_ngay = so_ngay_trong_nam(ngay_bat_dau, ngay_ket_thuc, nam)  # Số ngày của đơn thuộc năm đó.
        ket_qua.append({"nam": nam, "quy": quy, "so_ngay": so_ngay, "con_lai_sau": quy["con_lai"] - so_ngay})  # Dòng kết quả.
    return ket_qua  # Trả danh sách theo năm.


def nam_thieu_phep(nv, ngay_bat_dau, ngay_ket_thuc):  # Những năm mà quỹ phép không đủ cho đơn.
    return [n for n in quy_theo_tung_nam(nv, ngay_bat_dau, ngay_ket_thuc) if n["con_lai_sau"] < 0]  # Còn lại sau duyệt < 0.


# ===================== ĐƠN NGHỈ PHÉP =====================

def tao_don(nv, loai_phep, ngay_bat_dau, ngay_ket_thuc, ly_do, hom_nay=None):  # UC-NP-3.01: tạo đơn xin nghỉ.
    hom_nay = hom_nay or timezone.localdate()  # Ngày hiện tại theo máy chủ.
    if ngay_bat_dau < hom_nay:  # BR2: không chọn ngày trong quá khứ.
        raise ValidationError({"ngaybatdau": "Ngày bắt đầu nghỉ phải từ hôm nay trở về sau."})  # Lỗi tại ô ngày bắt đầu.
    if ngay_ket_thuc < ngay_bat_dau:  # Ngày kết thúc phải sau hoặc bằng ngày bắt đầu.
        raise ValidationError({"ngayketthuc": "Ngày kết thúc không được trước ngày bắt đầu."})  # Lỗi tại ô ngày kết thúc.
    trung = DonNghiPhep.objects.filter(  # BR3: tìm đơn chờ duyệt/đã duyệt có ngày giao nhau.
        manv=nv, trangthai__in=[DonNghiPhep.TrangThai.CHO_DUYET, DonNghiPhep.TrangThai.DA_DUYET],  # Bỏ qua đơn bị từ chối.
        ngaybatdau__lte=ngay_ket_thuc, ngayketthuc__gte=ngay_bat_dau,  # Hai khoảng ngày giao nhau.
    ).first()  # Lấy một đơn trùng để báo lỗi.
    if trung:  # Có đơn trùng ngày.
        raise ValidationError(f"Ngày nghỉ bị trùng với đơn {trung.ma_hien_thi} ({trung.get_trangthai_display().lower()}).")  # Báo đơn bị trùng.
    so_ngay = so_ngay_nghi(ngay_bat_dau, ngay_ket_thuc)  # Hệ thống tự tính số ngày nghỉ.
    thieu = nam_thieu_phep(nv, ngay_bat_dau, ngay_ket_thuc) if loai_phep.tru_phepnam else []  # BR1: kiểm tra từng năm.
    if thieu:  # Có năm không đủ phép.
        chi_tiet = "; ".join(  # Ví dụ: năm 2026 còn 1 ngày, đơn cần 2 ngày.
            f"năm {n['nam']} còn {max(n['quy']['con_lai'], 0)} ngày, đơn cần {n['so_ngay']} ngày" for n in thieu  # Từng năm.
        )  # Kết thúc chuỗi.
        raise ValidationError({"maloaiphep": (  # Lỗi tại ô loại phép.
            f"Quỹ phép năm không đủ ({chi_tiet}). Vui lòng chọn “Nghỉ việc riêng không hưởng lương”."  # Hướng dẫn theo đặc tả.
        )})  # Kết thúc lỗi.
    return DonNghiPhep.objects.create(  # Lưu đơn với trạng thái Chờ duyệt.
        manv=nv, maloaiphep=loai_phep, ngaybatdau=ngay_bat_dau, ngayketthuc=ngay_ket_thuc,  # Thông tin ngày nghỉ.
        songaynghi=so_ngay, lydo=ly_do.strip(),  # Số ngày tự tính và lý do.
    )  # Kết thúc tạo đơn.


def _kiem_tra_xu_ly(don, nguoi_xu_ly):  # Điều kiện chung cho duyệt và từ chối.
    if don.trangthai != DonNghiPhep.TrangThai.CHO_DUYET:  # BR3 UC-QLP: đơn đã xử lý không được sửa.
        raise ValidationError("Đơn đã được xử lý trước đó, không thể thay đổi.")  # Bảo toàn dữ liệu.
    if nguoi_xu_ly is None:  # Tài khoản quản lý chưa liên kết hồ sơ.
        raise ValidationError("Tài khoản của bạn chưa liên kết hồ sơ nhân viên nên chưa thể xét duyệt.")  # Cần hồ sơ để lưu người duyệt.
    if nguoi_xu_ly.pk == don.manv_id:  # Quản lý tự xử lý đơn của mình.
        raise ValidationError("Bạn không thể tự xét duyệt đơn của chính mình.")  # Quy tắc đã chốt.


def dong_bo_bang_cong(don):  # Ghi ngày nghỉ đã duyệt vào bảng chấm công.
    ngay = don.ngaybatdau  # Bắt đầu từ ngày đầu tiên của đơn.
    while ngay <= don.ngayketthuc:  # Lặp từng ngày nghỉ.
        ban_ghi, moi_tao = ChamCong.objects.get_or_create(  # Mỗi ngày một bản ghi, không tạo trùng.
            manv=don.manv, ngaychamcong=ngay,  # Nhân viên và ngày nghỉ.
            defaults={"trangthai": ChamCong.TrangThai.NGHI_PHEP, "ghichu": f"Theo đơn {don.ma_hien_thi}"},  # Ghi Nghỉ có phép.
        )  # Kết thúc tạo bản ghi.
        if not moi_tao and ban_ghi.trangthai != ChamCong.TrangThai.NGHI_PHEP:
            raise ValidationError(
                f"Ngày {ngay:%d/%m/%Y} đã có dữ liệu chấm công; không thể duyệt đơn nghỉ."
            )
        ngay += timedelta(days=1)  # Sang ngày tiếp theo.


@transaction.atomic  # Cập nhật đơn và bảng công cùng thành công hoặc cùng hoàn tác.
def duyet_don(don, nguoi_duyet, bay_gio=None):  # UC-QLP-3.01: phê duyệt đơn.
    don = DonNghiPhep.objects.select_for_update().select_related("manv").get(pk=don.pk)
    _kiem_tra_xu_ly(don, nguoi_duyet)  # Kiểm tra điều kiện chung.
    don.trangthai = DonNghiPhep.TrangThai.DA_DUYET  # Đổi trạng thái thành Đã duyệt.
    don.nguoiduyet = nguoi_duyet  # Lưu quản lý trực tiếp duyệt.
    don.ngayduyet = bay_gio or timezone.now()  # Lưu thời gian duyệt.
    don.save(update_fields=["trangthai", "nguoiduyet", "ngayduyet"])  # Chỉ cập nhật các trường thay đổi.
    dong_bo_bang_cong(don)  # Tự động ghi "Nghỉ có phép" vào bảng công.
    return don  # Quỹ phép tự giảm vì được tính từ các đơn đã duyệt.


def tu_choi_don(don, nguoi_duyet, phan_hoi, bay_gio=None):  # UC-QLP-3.01 luồng thay thế: từ chối đơn.
    if not (phan_hoi or "").strip():  # BR1: bắt buộc nhập lý do khi từ chối.
        raise ValidationError({"phanhoi": "Vui lòng nhập lý do từ chối"})  # Không lưu thao tác.
    _kiem_tra_xu_ly(don, nguoi_duyet)  # Kiểm tra điều kiện chung.
    don.trangthai = DonNghiPhep.TrangThai.TU_CHOI  # Đổi trạng thái thành Từ chối.
    don.nguoiduyet = nguoi_duyet  # Lưu người từ chối.
    don.ngayduyet = bay_gio or timezone.now()  # Lưu thời gian xử lý.
    don.phanhoi = phan_hoi.strip()  # Lưu lý do phản hồi cho nhân viên.
    don.save(update_fields=["trangthai", "nguoiduyet", "ngayduyet", "phanhoi"])  # Quỹ phép giữ nguyên.
    return don  # Trả đơn đã cập nhật.


def thoi_diem(ngay, gio):  # Ghép ngày và giờ thành thời điểm có múi giờ (dùng cho dữ liệu mẫu và kiểm thử).
    return timezone.make_aware(datetime.combine(ngay, gio))  # Gắn múi giờ Việt Nam.
