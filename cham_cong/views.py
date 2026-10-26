from io import BytesIO  # Bộ nhớ tạm để ghi file Excel trước khi gửi về trình duyệt.
from urllib.parse import urlencode  # Ghép bộ lọc thành chuỗi tham số URL.

from django.contrib import messages  # Hiển thị thông báo thành công hoặc lỗi.
from django.contrib.auth.decorators import login_required  # Yêu cầu đăng nhập.
from django.core.exceptions import ValidationError  # Lỗi nghiệp vụ từ services.
from django.db.models import Q  # Kết hợp điều kiện tìm kiếm.
from django.http import HttpResponse  # Trả file Excel.
from django.shortcuts import get_object_or_404, redirect, render  # Lấy dữ liệu, chuyển trang và render HTML.
from django.urls import reverse  # Tạo URL từ tên route.
from django.utils import timezone  # Ngày giờ theo máy chủ.
from django.views.decorators.http import require_http_methods, require_POST, require_safe  # Giới hạn phương thức HTTP.

from nhan_su.models import NhanVien  # Hồ sơ nhân viên.
from nhan_su.views import _gan_loi, _phan_trang, quan_ly_required  # Dùng lại hàm chung của phân hệ nhân sự.

from . import services  # Các hàm nghiệp vụ chấm công và nghỉ phép.
from .forms import DonNghiPhepForm, TuChoiForm  # Biểu mẫu tạo đơn và từ chối.
from .models import ChamCong, DonNghiPhep, LoaiPhep  # Các model cần truy vấn.

THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]  # Tên thứ trong tuần.
nhan_vien_required = login_required(login_url="login")  # Trang của nhân viên chỉ cần đăng nhập.


# ===================== HÀM DÙNG CHUNG =====================

def _chua_lien_ket(request):  # Tài khoản chưa có hồ sơ nhân viên (ví dụ admin).
    return render(request, "cham_cong/chua_lien_ket.html")  # Hiển thị hướng dẫn thay vì báo lỗi.


def _so_nguyen(gia_tri, mac_dinh, nho_nhat, lon_nhat):  # Đọc số từ URL, sai thì dùng mặc định.
    try:  # Chuỗi có thể không phải số.
        so = int(gia_tri)  # Đổi chuỗi thành số.
    except (TypeError, ValueError):  # Không đổi được.
        return mac_dinh  # Dùng giá trị mặc định.
    return so if nho_nhat <= so <= lon_nhat else mac_dinh  # Ngoài khoảng cho phép thì dùng mặc định.


def _thang_nam(request):  # Lấy tháng và năm đang xem từ bộ lọc.
    hom_nay = timezone.localdate()  # Mặc định là tháng hiện tại.
    thang = _so_nguyen(request.GET.get("thang"), hom_nay.month, 1, 12)  # Tháng 1 → 12.
    nam = _so_nguyen(request.GET.get("nam"), hom_nay.year, 2000, hom_nay.year + 1)  # Năm hợp lý.
    return thang, nam  # Trả cặp tháng, năm.


def _lua_chon_thoi_gian():  # Danh sách tháng và năm cho ô chọn.
    nam_nay = timezone.localdate().year  # Năm hiện tại.
    return {"ds_thang": range(1, 13), "ds_nam": range(nam_nay, nam_nay - 3, -1)}  # 12 tháng, 3 năm gần nhất.


# ===================== 4.1 CHẤM CÔNG (NHÂN VIÊN) =====================

@nhan_vien_required  # Yêu cầu đăng nhập.
@require_safe  # Trang chỉ đọc.
def cham_cong_hom_nay(request):  # Giao diện chấm công hôm nay.
    nv = services.lay_nhan_vien(request.user)  # Hồ sơ của người đang đăng nhập.
    if not nv:  # Chưa liên kết hồ sơ.
        return _chua_lien_ket(request)  # Hiển thị hướng dẫn.
    bay_gio = timezone.localtime()  # Giờ máy chủ hiện tại.
    ban_ghi = services.cham_cong_hom_nay(nv)  # Bản ghi hôm nay nếu có.
    return render(request, "cham_cong/hom_nay.html", {  # Hiển thị trang.
        "nv": nv, "ban_ghi": ban_ghi, "bay_gio": bay_gio,  # Nhân viên, bản ghi và giờ máy chủ.
        "thu": THU[bay_gio.weekday()],  # Tên thứ của hôm nay.
        "gio_bat_dau": services.cau_hinh("GIO_BAT_DAU"), "gio_ket_thuc": services.cau_hinh("GIO_KET_THUC"),  # Giờ ca.
        "ca_lam": services.ca_lam_viec(),  # Chuỗi ca 08:00 – 17:00.
        "trang_thai_ngay": services.trang_thai_trong_ngay(ban_ghi),  # Trạng thái trong ngày.
        "vao_som": services.tinh_vao_som(ban_ghi.gio_checkin) if ban_ghi and ban_ghi.gio_checkin else 0,  # Số phút vào sớm.
        "nghi_phep": bool(ban_ghi and ban_ghi.trangthai == ChamCong.TrangThai.NGHI_PHEP),  # Hôm nay nghỉ có phép.
    })  # Kết thúc context.


def _xu_ly_cham_cong(request, ham, thong_bao):  # Dùng chung cho Check-in và Check-out.
    nv = services.lay_nhan_vien(request.user)  # Hồ sơ của người gửi yêu cầu.
    if not nv:  # Chưa liên kết hồ sơ.
        return _chua_lien_ket(request)  # Không cho chấm công.
    try:  # Gọi nghiệp vụ.
        ban_ghi = ham(nv)  # Check-in hoặc Check-out theo giờ máy chủ.
    except ValidationError as loi:  # Vi phạm quy tắc hoặc lưu thất bại.
        messages.error(request, " ".join(loi.messages))  # Hiển thị đúng câu thông báo của đặc tả.
    else:  # Thành công.
        messages.success(request, thong_bao(ban_ghi))  # Thông báo kèm thời gian vừa ghi nhận.
    return redirect("cham_cong:hom_nay")  # Quay lại trang chấm công (tránh gửi lại khi F5).


@nhan_vien_required  # Yêu cầu đăng nhập.
@require_POST  # Chỉ nhận POST vì có ghi dữ liệu.
def check_in(request):  # UC-CC-3.01.
    return _xu_ly_cham_cong(request, services.check_in, lambda bg: f"Check-in thành công lúc {bg.gio_checkin:%H:%M}.")  # Gọi hàm chung.


@nhan_vien_required  # Yêu cầu đăng nhập.
@require_POST  # Chỉ nhận POST.
def check_out(request):  # UC-CC-3.02.
    return _xu_ly_cham_cong(  # Gọi hàm chung.
        request, services.check_out,  # Nghiệp vụ Check-out.
        lambda bg: f"Check-out thành công lúc {bg.gio_checkout:%H:%M}. Dữ liệu chấm công đã được lưu.",  # Thông báo.
    )  # Kết thúc gọi hàm.


@nhan_vien_required  # Yêu cầu đăng nhập.
@require_safe  # Chỉ xem, không sửa dữ liệu.
def lich_su(request):  # UC-CC-3.03: tra cứu lịch sử chấm công theo tháng.
    nv = services.lay_nhan_vien(request.user)  # Chỉ xem dữ liệu của chính mình.
    if not nv:  # Chưa liên kết hồ sơ.
        return _chua_lien_ket(request)  # Hiển thị hướng dẫn.
    thang, nam = _thang_nam(request)  # Tháng đang xem.
    dong = services.tao_bang_cong(nam, thang, [nv])  # Dựng bảng công của một nhân viên.
    context = _phan_trang(request, dong)  # Chia trang 10 dòng.
    context.update(_lua_chon_thoi_gian())  # Thêm danh sách tháng và năm.
    context.update({"nv": nv, "thang": thang, "nam": nam, "thong_ke": services.thong_ke_bang_cong(dong)})  # Số liệu.
    return render(request, "cham_cong/lich_su.html", context)  # Hiển thị trang.


# ===================== 4.2 ĐƠN NGHỈ PHÉP (NHÂN VIÊN) =====================

@nhan_vien_required  # Yêu cầu đăng nhập.
@require_http_methods(["GET", "HEAD", "POST"])  # GET hiển thị form, POST gửi đơn.
def tao_don(request):  # UC-NP-3.01: tạo đơn xin nghỉ phép.
    nv = services.lay_nhan_vien(request.user)  # Người gửi đơn.
    if not nv:  # Chưa liên kết hồ sơ.
        return _chua_lien_ket(request)  # Hiển thị hướng dẫn.
    form = DonNghiPhepForm(request.POST or None)  # Biểu mẫu có hoặc không có dữ liệu gửi lên.
    if request.method == "POST" and form.is_valid():  # Dữ liệu đủ và đúng định dạng.
        du_lieu = form.cleaned_data  # Dữ liệu đã kiểm tra.
        try:  # Kiểm tra quy tắc nghiệp vụ.
            don = services.tao_don(  # Lưu đơn.
                nv, du_lieu["maloaiphep"], du_lieu["ngaybatdau"], du_lieu["ngayketthuc"], du_lieu["lydo"],  # Dữ liệu đơn.
            )  # Kết thúc gọi service.
        except ValidationError as loi:  # Vi phạm quy tắc.
            _gan_loi(form, loi)  # Đưa lỗi về đúng ô nhập.
        else:  # Lưu thành công.
            messages.success(  # Thông báo theo đặc tả.
                request, f"Gửi đơn xin nghỉ phép thành công. Đơn {don.ma_hien_thi} đã được gửi và đang chờ quản lý xét duyệt.",  # Nội dung.
            )  # Kết thúc thông báo.
            return redirect("cham_cong:don_cua_toi")  # Đơn mới hiện ngay trong danh sách.
    elif request.method == "POST":  # Thiếu thông tin bắt buộc.
        messages.error(request, "Vui lòng điền đầy đủ thông tin trước khi gửi.")  # Cảnh báo chung.
    return render(request, "cham_cong/tao_don.html", {  # Hiển thị biểu mẫu.
        "form": form, "nv": nv,  # Biểu mẫu và người gửi.
        "quy_phep": services.thong_ke_phep(nv, timezone.localdate().year),  # Khung "Phép năm của bạn".
        "nam": timezone.localdate().year,  # Năm hiện tại.
        "ds_tru_phep": list(LoaiPhep.objects.filter(tru_phepnam=True).values_list("pk", flat=True)),  # Dùng cho JavaScript.
    })  # Kết thúc context.


@nhan_vien_required  # Yêu cầu đăng nhập.
@require_safe  # Chỉ đọc.
def don_cua_toi(request):  # UC-NP-3.02: theo dõi trạng thái đơn.
    nv = services.lay_nhan_vien(request.user)  # Chỉ lấy đơn của chính mình.
    if not nv:  # Chưa liên kết hồ sơ.
        return _chua_lien_ket(request)  # Hiển thị hướng dẫn.
    nam = _so_nguyen(request.GET.get("nam"), timezone.localdate().year, 2000, 2100)  # Năm đang xem.
    ds = nv.don_nghi_phep.select_related("maloaiphep").filter(services.giao_voi_nam(nam))  # Đơn có ngày nghỉ trong năm.
    trang_thai = request.GET.get("trang_thai", "")  # Bộ lọc trạng thái.
    if trang_thai in DonNghiPhep.TrangThai.values:  # Chỉ nhận giá trị hợp lệ.
        ds = ds.filter(trangthai=trang_thai)  # Lọc theo trạng thái.
    context = _phan_trang(request, ds)  # Chia trang.
    context.update(_lua_chon_thoi_gian())  # Danh sách năm.
    context.update({"nam": nam, "trang_thai": trang_thai, "ds_trang_thai": DonNghiPhep.TrangThai.choices})  # Bộ lọc.
    context["co_don"] = nv.don_nghi_phep.exists()  # Phân biệt "chưa từng nộp đơn" với "lọc không ra".
    return render(request, "cham_cong/don_cua_toi.html", context)  # Hiển thị danh sách.


@nhan_vien_required  # Yêu cầu đăng nhập.
@require_safe  # Chỉ đọc.
def chi_tiet_don_cua_toi(request, madon):  # Xem chi tiết một đơn của chính mình.
    nv = services.lay_nhan_vien(request.user)  # Hồ sơ người xem.
    if not nv:  # Chưa liên kết hồ sơ.
        return _chua_lien_ket(request)  # Hiển thị hướng dẫn.
    don = get_object_or_404(DonNghiPhep.objects.select_related("maloaiphep", "nguoiduyet"), pk=madon, manv=nv)  # Đơn người khác trả 404.
    return render(request, "cham_cong/don_chi_tiet.html", {"don": don, "che_do_ca_nhan": True})  # Dùng chung giao diện chi tiết.


# ===================== 4.3 BẢNG CHẤM CÔNG (QUẢN LÝ) =====================

def _loc_bang_cong(request):  # Đọc bộ lọc và dựng bảng công; dùng chung cho xem và xuất file.
    thang, nam = _thang_nam(request)  # Tháng đang xem.
    ds_nv = NhanVien.objects.select_related("maphong").order_by("tennv")  # Tất cả nhân viên.
    ma_nv = request.GET.get("nhan_vien", "")  # Lọc một nhân viên.
    vi_tri = request.GET.get("vi_tri", "")  # Lọc theo chức vụ.
    trang_thai = request.GET.get("trang_thai", "")  # Lọc theo trạng thái.
    if ma_nv:  # Có chọn nhân viên.
        ds_nv = ds_nv.filter(manv=ma_nv)  # Chỉ nhân viên đó.
    if vi_tri:  # Có chọn vị trí.
        ds_nv = ds_nv.filter(chucvu=vi_tri)  # Chỉ đúng chức vụ.
    if trang_thai not in ChamCong.TrangThai.values:  # Giá trị lạ.
        trang_thai = ""  # Bỏ qua bộ lọc trạng thái.
    dong = services.tao_bang_cong(nam, thang, ds_nv, trang_thai)  # Dựng bảng công.
    bo_loc = {"thang": thang, "nam": nam, "nhan_vien": ma_nv, "vi_tri": vi_tri, "trang_thai": trang_thai}  # Bộ lọc hiện tại.
    return bo_loc, dong  # Trả bộ lọc và dữ liệu.


def _mo_ta_pham_vi(bo_loc):  # Câu mô tả phạm vi dữ liệu trong hộp thoại xuất file.
    nv = NhanVien.objects.filter(manv=bo_loc["nhan_vien"]).first() if bo_loc["nhan_vien"] else None  # Nhân viên được lọc.
    phan = [  # Các phần của câu mô tả.
        f"Tháng {bo_loc['thang']:02d}/{bo_loc['nam']}",  # Tháng.
        nv.tennv if nv else "Tất cả nhân viên",  # Nhân viên.
        bo_loc["vi_tri"] or "Tất cả vị trí",  # Vị trí.
        ChamCong.TrangThai(bo_loc["trang_thai"]).label if bo_loc["trang_thai"] else "Tất cả trạng thái",  # Trạng thái.
    ]  # Kết thúc danh sách.
    return " · ".join(phan)  # Nối bằng dấu chấm giữa.


@quan_ly_required  # Chỉ quản lý.
@require_safe  # Chỉ đọc.
def bang_cham_cong(request):  # UC-QL-3.01: xem bảng chấm công tổng hợp.
    bo_loc, dong = _loc_bang_cong(request)  # Dữ liệu theo bộ lọc.
    context = _phan_trang(request, dong)  # Chia trang.
    context.update(_lua_chon_thoi_gian())  # Danh sách tháng, năm.
    context.update({  # Dữ liệu cho bộ lọc và thẻ thống kê.
        "bo_loc": bo_loc, "thong_ke": services.thong_ke_bang_cong(dong), "so_ban_ghi": len(dong),  # Số liệu.
        "ds_nhan_vien": NhanVien.objects.order_by("tennv"),  # Ô chọn nhân viên.
        "ds_vi_tri": NhanVien.objects.order_by("chucvu").values_list("chucvu", flat=True).distinct(),  # Ô chọn vị trí.
        "ds_trang_thai": ChamCong.TrangThai.choices,  # Ô chọn trạng thái.
        "mo_xuat_file": request.GET.get("xuat") == "1" and bool(dong),  # Mở hộp thoại xuất file.
        "pham_vi": _mo_ta_pham_vi(bo_loc),  # Mô tả phạm vi xuất.
        "tham_so_bo_loc": urlencode(bo_loc),  # Bộ lọc không kèm cờ mở hộp thoại (dùng cho nút Hủy).
    })  # Kết thúc context.
    if request.GET.get("da_xuat") == "1":  # Trình duyệt quay lại sau khi tải file.
        messages.success(request, "Xuất dữ liệu thành công")  # Thông báo theo đặc tả.
    if request.GET.get("xuat") == "1" and not dong:  # Bấm xuất khi bảng trống.
        messages.error(request, "Không có dữ liệu để xuất file")  # Thông báo theo đặc tả.
    return render(request, "cham_cong/bang_cham_cong.html", context)  # Hiển thị trang.


COT_EXCEL = ["Mã NV", "Nhân viên", "Vị trí", "Ngày", "Check-in", "Check-out", "Giờ làm", "Đi trễ (phút)",  # Tiêu đề cột.
             "Về sớm (phút)", "Làm thêm (giờ)", "Trạng thái"]  # Giống các cột trên màn hình.


def _dong_excel(d):  # Đổi một dòng bảng công thành một hàng Excel.
    bg = d.ban_ghi  # Bản ghi thật (None nếu là ngày vắng).
    return [  # Các ô theo đúng thứ tự cột.
        d.nv.manv, d.nv.tennv, d.nv.chucvu, d.ngay,  # Thông tin nhân viên và ngày.
        bg.gio_checkin if bg and bg.gio_checkin else None,  # Giờ Check-in.
        bg.gio_checkout if bg and bg.gio_checkout else None,  # Giờ Check-out.
        float(bg.sogiolamviec) if bg and bg.sogiolamviec is not None else None,  # Giờ làm.
        bg.thoigianditre if bg else None, bg.thoigianvesom if bg else None,  # Đi trễ, về sớm.
        float(bg.sogiolamthem) if bg and bg.sogiolamthem is not None else None,  # Làm thêm.
        d.nhan_trang_thai,  # Nhãn trạng thái.
    ]  # Kết thúc hàng.


def tao_file_excel(bo_loc, dong):  # Tạo nội dung file .xlsx từ dữ liệu đang lọc.
    from openpyxl import Workbook  # Thư viện ghi Excel (đã thêm vào requirements.txt).
    from openpyxl.styles import Font, PatternFill  # Định dạng chữ đậm và màu nền.

    wb = Workbook()  # Tạo sổ tính mới.
    ws = wb.active  # Trang tính đầu tiên.
    ws.title = f"T{bo_loc['thang']:02d}-{bo_loc['nam']}"  # Tên trang tính, ví dụ T09-2026.
    ws.append([f"BẢNG CHẤM CÔNG THÁNG {bo_loc['thang']:02d}/{bo_loc['nam']}"])  # Dòng tiêu đề.
    ws.append([_mo_ta_pham_vi(bo_loc)])  # Dòng mô tả phạm vi lọc.
    ws.append([])  # Dòng trống ngăn cách.
    ws.append(COT_EXCEL)  # Hàng tiêu đề cột.
    ws["A1"].font = Font(bold=True, size=14)  # Tiêu đề chữ lớn.
    for o in ws[4]:  # Định dạng hàng tiêu đề cột.
        o.font = Font(bold=True)  # Chữ đậm.
        o.fill = PatternFill("solid", fgColor="FDE7F0")  # Nền hồng nhạt như giao diện.
    for d in dong:  # Ghi từng dòng dữ liệu.
        ws.append(_dong_excel(d))  # Thêm một hàng.
    for hang in ws.iter_rows(min_row=5):  # Định dạng các ô dữ liệu.
        hang[3].number_format = "DD/MM/YYYY"  # Cột ngày.
        hang[4].number_format = hang[5].number_format = "HH:MM"  # Cột giờ.
        hang[6].number_format = hang[9].number_format = "0.00"  # Cột số giờ.
    for cot, rong in zip("ABCDEFGHIJK", [9, 24, 22, 12, 10, 10, 9, 13, 13, 14, 17]):  # Độ rộng từng cột.
        ws.column_dimensions[cot].width = rong  # Gán độ rộng.
    bo_dem = BytesIO()  # Bộ nhớ tạm.
    wb.save(bo_dem)  # Ghi sổ tính vào bộ nhớ.
    return bo_dem.getvalue()  # Trả nội dung nhị phân.


@quan_ly_required  # Chỉ quản lý được xuất dữ liệu.
@require_safe  # Tải file bằng GET.
def xuat_bang_cham_cong(request):  # UC-QL-3.02: xuất bảng chấm công ra Excel.
    bo_loc, dong = _loc_bang_cong(request)  # Đúng dữ liệu đang lọc trên màn hình.
    quay_lai = reverse("cham_cong:bang_cham_cong") + "?" + request.GET.urlencode()  # Trang bảng công kèm bộ lọc.
    if not dong:  # Bảng trống.
        messages.error(request, "Không có dữ liệu để xuất file")  # Thông báo theo đặc tả.
        return redirect(quay_lai)  # Quay lại bảng công.
    try:  # Bắt lỗi khi tạo file.
        noi_dung = tao_file_excel(bo_loc, dong)  # Tạo file Excel.
    except Exception:  # Bất kỳ lỗi nào khi tạo tệp.
        messages.error(request, "Xuất file thất bại, vui lòng thử lại")  # Thông báo theo đặc tả.
        return redirect(quay_lai)  # Quay lại bảng công.
    phan_hoi = HttpResponse(  # Phản hồi chứa file.
        noi_dung, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Kiểu file .xlsx.
    )  # Kết thúc tạo phản hồi.
    phan_hoi["Content-Disposition"] = f'attachment; filename="bang_cham_cong_{bo_loc["nam"]}_{bo_loc["thang"]:02d}.xlsx"'  # Tên file tải về.
    return phan_hoi  # Trình duyệt tự tải file về máy.


# ===================== 4.4 DUYỆT ĐƠN VÀ QUỸ PHÉP (QUẢN LÝ) =====================

def _canh_bao_quy(don):  # Các năm mà đơn phép năm chờ duyệt vượt quỹ (danh sách rỗng nếu không vượt).
    if don.trangthai != DonNghiPhep.TrangThai.CHO_DUYET or not don.maloaiphep.tru_phepnam:  # Chỉ xét đơn phép năm chờ duyệt.
        return []  # Không cần cảnh báo.
    return services.nam_thieu_phep(don.manv, don.ngaybatdau, don.ngayketthuc)  # Kiểm tra quỹ của từng năm.


@quan_ly_required  # Chỉ quản lý.
@require_safe  # Chỉ đọc.
def duyet_don_list(request):  # Danh sách đơn cần duyệt.
    ds = DonNghiPhep.objects.select_related("manv", "maloaiphep")  # Đơn kèm nhân viên và loại phép.
    q = request.GET.get("q", "").strip()  # Từ khóa tên hoặc mã nhân viên.
    if q:  # Có từ khóa.
        ds = ds.filter(Q(manv__manv__icontains=q) | Q(manv__tennv__icontains=q))  # Tìm theo mã hoặc tên.
    trang_thai = request.GET.get("trang_thai", DonNghiPhep.TrangThai.CHO_DUYET)  # Mặc định xem đơn Chờ duyệt.
    if trang_thai in DonNghiPhep.TrangThai.values:  # Giá trị hợp lệ.
        ds = ds.filter(trangthai=trang_thai)  # Lọc theo trạng thái.
    thang_gui = request.GET.get("thang_gui", "")  # Tháng gửi dạng YYYY-MM.
    if thang_gui:  # Có chọn tháng gửi.
        nam, _, thang = thang_gui.partition("-")  # Tách năm và tháng.
        ds = ds.filter(thoigianguidon__year=_so_nguyen(nam, 0, 2000, 2100), thoigianguidon__month=_so_nguyen(thang, 0, 1, 12))  # Lọc.
    context = _phan_trang(request, ds)  # Chia trang.
    canh_bao = []  # Danh sách đơn vượt quỹ trên trang hiện tại.
    for don in context["page_obj"]:  # Duyệt đơn trên trang.
        don.thieu_phep = _canh_bao_quy(don)  # Gắn thông tin cảnh báo vào từng đơn.
        if don.thieu_phep:  # Đơn vượt quỹ ít nhất một năm.
            canh_bao.append(don)  # Hiển thị khung cảnh báo dưới bảng.
    context.update({  # Dữ liệu bộ lọc.
        "q": q, "trang_thai": trang_thai, "thang_gui": thang_gui, "ds_trang_thai": DonNghiPhep.TrangThai.choices,  # Bộ lọc.
        "canh_bao": canh_bao, "so_cho_duyet": DonNghiPhep.objects.filter(trangthai="CHODUYET").count(),  # Cảnh báo, số chờ duyệt.
    })  # Kết thúc context.
    return render(request, "cham_cong/duyet_don_list.html", context)  # Hiển thị danh sách.


def _hien_thi_chi_tiet_duyet(request, don, form=None, mo_tu_choi=False):  # Dùng chung cho xem, duyệt, từ chối.
    tru_phep = don.maloaiphep.tru_phepnam  # Loại phép có trừ quỹ hay không.
    nguoi_xem = services.lay_nhan_vien(request.user)  # Hồ sơ của quản lý đang xem.
    return render(request, "cham_cong/don_chi_tiet.html", {  # Dùng chung giao diện chi tiết với nhân viên.
        "don": don, "tru_phep": tru_phep,  # Đơn và loại phép.
        "quy_theo_nam": services.quy_theo_tung_nam(don.manv, don.ngaybatdau, don.ngayketthuc),  # Quỹ từng năm đơn đi qua.
        "thieu_phep": _canh_bao_quy(don),  # Cảnh báo vượt quỹ theo từng năm.
        "la_don_cua_minh": bool(nguoi_xem and nguoi_xem.pk == don.manv_id),  # Không cho tự duyệt.
        "form": form or TuChoiForm(), "mo_tu_choi": mo_tu_choi,  # Hộp thoại từ chối.
    })  # Kết thúc context.


def _lay_don(madon):  # Lấy đơn kèm dữ liệu liên quan.
    return get_object_or_404(DonNghiPhep.objects.select_related("manv", "maloaiphep", "nguoiduyet"), pk=madon)  # Không có thì 404.


@quan_ly_required  # Chỉ quản lý.
@require_safe  # Chỉ đọc.
def chi_tiet_duyet(request, madon):  # Xem chi tiết đơn cần xử lý.
    return _hien_thi_chi_tiet_duyet(request, _lay_don(madon), mo_tu_choi=request.GET.get("tu_choi") == "1")  # Có thể mở hộp thoại từ chối.


@quan_ly_required  # Chỉ quản lý.
@require_POST  # Ghi dữ liệu.
def phe_duyet(request, madon):  # UC-QLP-3.01: phê duyệt đơn.
    don = _lay_don(madon)  # Đơn cần duyệt.
    try:  # Gọi nghiệp vụ.
        services.duyet_don(don, services.lay_nhan_vien(request.user))  # Duyệt, trừ phép, đồng bộ bảng công.
    except ValidationError as loi:  # Vi phạm quy tắc.
        messages.error(request, " ".join(loi.messages))  # Báo lỗi.
    else:  # Thành công.
        messages.success(request, f"Đã phê duyệt đơn {don.ma_hien_thi}. Ngày nghỉ đã được đồng bộ vào bảng chấm công.")  # Thông báo.
    return redirect("cham_cong:chi_tiet_duyet", madon=don.pk)  # Quay lại chi tiết đơn.


@quan_ly_required  # Chỉ quản lý.
@require_POST  # Ghi dữ liệu.
def tu_choi(request, madon):  # UC-QLP-3.01 luồng thay thế: từ chối đơn.
    don = _lay_don(madon)  # Đơn cần từ chối.
    form = TuChoiForm(request.POST)  # Biểu mẫu lý do từ chối.
    form.is_valid()  # Làm sạch dữ liệu (trường không bắt buộc ở form).
    try:  # Gọi nghiệp vụ.
        services.tu_choi_don(don, services.lay_nhan_vien(request.user), form.cleaned_data.get("phanhoi", ""))  # Từ chối.
    except ValidationError as loi:  # Thiếu lý do hoặc vi phạm quy tắc.
        _gan_loi(form, loi)  # Gắn lỗi vào ô lý do.
        return _hien_thi_chi_tiet_duyet(request, don, form, mo_tu_choi=True)  # Giữ hộp thoại mở, không lưu.
    messages.success(request, f"Đã từ chối đơn {don.ma_hien_thi}. Quỹ phép của nhân viên giữ nguyên.")  # Thông báo.
    return redirect("cham_cong:chi_tiet_duyet", madon=don.pk)  # Quay lại chi tiết đơn.


@quan_ly_required  # Chỉ quản lý.
@require_safe  # Chỉ đọc.
def quy_phep(request):  # UC-QLP-3.02: theo dõi quỹ phép năm.
    nam = _so_nguyen(request.GET.get("nam"), timezone.localdate().year, 2000, 2100)  # Năm đang xem.
    ds_nv = NhanVien.objects.filter(trangthai=True).order_by("manv")  # Nhân viên đang làm việc.
    q = request.GET.get("q", "").strip()  # Từ khóa tên hoặc mã.
    if q:  # Có từ khóa.
        ds_nv = ds_nv.filter(Q(manv__icontains=q) | Q(tennv__icontains=q))  # Tìm theo mã hoặc tên.
    dong = services.danh_sach_quy_phep(ds_nv, nam)  # Quỹ phép từng nhân viên.
    context = _phan_trang(request, dong)  # Chia trang.
    context.update(_lua_chon_thoi_gian())  # Danh sách năm.
    context.update({  # Số liệu tổng hợp cho 4 thẻ.
        "nam": nam, "q": q, "so_nv": len(dong), "phep_chuan": services.cau_hinh("PHEP_NAM"),  # Bộ lọc và hạn ngạch.
        "tong": sum(d["tong"] for d in dong), "da_dung": sum(d["da_dung"] for d in dong),  # Tổng phép, đã dùng.
        "con_lai": sum(d["con_lai"] for d in dong),  # Tổng còn lại.
    })  # Kết thúc context.
    return render(request, "cham_cong/quy_phep.html", context)  # Hiển thị trang.


@quan_ly_required  # Chỉ quản lý.
@require_safe  # Chỉ đọc.
def chi_tiet_quy_phep(request, manv):  # Chi tiết quỹ phép của một nhân viên.
    nv = get_object_or_404(NhanVien, pk=manv)  # Nhân viên cần xem.
    nam = _so_nguyen(request.GET.get("nam"), timezone.localdate().year, 2000, 2100)  # Năm đang xem.
    don_tru_phep = nv.don_nghi_phep.select_related("maloaiphep").filter(services.don_tru_phep_trong_nam(nam))  # Đơn phép năm giao với năm.
    quy = services.thong_ke_phep(nv, nam)  # Bốn con số quỹ phép.
    context = _phan_trang(request, don_tru_phep.filter(trangthai="DADUYET"))  # Bảng các đơn đã trừ phép.
    don_cho_duyet = list(don_tru_phep.filter(trangthai="CHODUYET"))  # Đơn đang chờ duyệt.
    for don in [*context["page_obj"], *don_cho_duyet]:  # Gắn số ngày tính vào năm đang xem.
        don.so_ngay_nam = services.so_ngay_trong_nam(don.ngaybatdau, don.ngayketthuc, nam)  # Đơn qua 2 năm chỉ tính phần của năm này.
    context.update({  # Dữ liệu còn lại.
        "nv": nv, "nam": nam, "quy": quy,  # Nhân viên, năm, quỹ.
        "don_cho_duyet": don_cho_duyet,  # Đơn đang chờ duyệt.
        "con_lai_neu_duyet": quy["con_lai"] - quy["cho_duyet"],  # Số phép còn lại nếu duyệt hết đơn chờ.
    })  # Kết thúc context.
    return render(request, "cham_cong/quy_phep_chi_tiet.html", context)  # Hiển thị trang.
