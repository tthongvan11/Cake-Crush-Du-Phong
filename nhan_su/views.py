# import các hàm dùng chung
import logging  # Ghi lỗi database vào log để kiểm tra.
from datetime import timedelta  # Tính khoảng ngày cảnh báo.
from functools import wraps  # Giữ tên và thông tin hàm khi dùng decorator.
from urllib.parse import urlsplit  # Tách đường dẫn quay lại để chỉ chấp nhận trang nội bộ phù hợp.
from django.conf import settings  # Đọc chính sách doanh nghiệp đã được cấu hình.

from django.contrib import messages  # Hiển thị thông báo thành công hoặc lỗi.
from django.contrib.auth.decorators import login_required  # Yêu cầu đăng nhập.
from django.core.exceptions import ObjectDoesNotExist, ValidationError  # Các lỗi cần xử lý.
from django.core.paginator import Paginator  # Chia danh sách thành nhiều trang.
from django.db import DatabaseError, IntegrityError  # Nhận diện lỗi database.
from django.db.models import Q  # Kết hợp điều kiện AND, OR và NOT.
from django.shortcuts import get_object_or_404, redirect, render  # Lấy dữ liệu, chuyển trang và render HTML.
from django.urls import reverse  # Tạo URL từ tên route.
from django.utils import timezone  # Lấy ngày theo múi giờ dự án.
from django.views.decorators.http import require_http_methods, require_safe  # Giới hạn phương thức HTTP.

from . import services  # Gọi các hàm nghiệp vụ đã viết ở bước 4.
from .forms import GiaHanHopDongForm, HopDongForm, NhanVienForm, VoHieuHoaNhanVienForm  # Import biểu mẫu.
from .models import HopDong, NhanVien, PhongBan  # Import các model cần truy vấn.
from .permissions import yeu_cau_quan_ly  # Kiểm tra quyền quản lý.


logger = logging.getLogger(__name__)  # Tạo logger cho file views.py.


def quan_ly_required(view):  # Decorator dùng chung cho các trang quản lý.
    @login_required(login_url="login")  # Chưa đăng nhập thì chuyển đến route login hiện có.
    @wraps(view)  # Giữ thông tin của view gốc.
    def wrapped(request, *args, **kwargs):  # Nhận request và các tham số URL.
        yeu_cau_quan_ly(request.user)  # Nhân viên thường bị từ chối truy cập.
        return view(request, *args, **kwargs)  # Người đủ quyền được chạy view.

    return wrapped  # Trả view đã được bảo vệ.


def _gan_loi(form, loi):  # Đưa lỗi nghiệp vụ từ service về biểu mẫu.
    if hasattr(loi, "error_dict"):  # Nếu lỗi được phân theo tên trường...
        for truong, danh_sach_loi in loi.error_dict.items():  # ...duyệt từng trường lỗi.
            form.add_error(  # Gắn lỗi vào ô nhập hoặc phần lỗi chung.
                truong if truong in form.fields else None, danh_sach_loi
            )  # Trường không có trên form được chuyển thành lỗi chung.
    else:  # Nếu lỗi chỉ có nội dung thông báo...
        form.add_error(None, loi)  # ...hiển thị ở phần lỗi chung.


def _phan_trang(request, danh_sach):  # Chia trang và giữ lại các bộ lọc.
    tham_so = request.GET.copy()  # Sao chép tham số để không sửa request gốc.
    tham_so.pop("page", None)  # Bỏ số trang cũ khỏi chuỗi bộ lọc.
    page = Paginator(danh_sach, 10).get_page(request.GET.get("page"))  # Mỗi trang 10 dòng, xử lý cả số trang sai.

    return {  # Trả dữ liệu dùng chung cho danh sách.
        "page_obj": page,  # Dữ liệu của trang hiện tại.
        "so_trang": page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1),  # Rút gọn số trang khi danh sách dài.
        "tham_so_loc": tham_so.urlencode(),  # Chuỗi bộ lọc dùng khi tạo liên kết chuyển trang.
    }  # Kết thúc dữ liệu phân trang.


def _bo_sung_trang_thai(hd):  # Bổ sung thông tin hiển thị cho một hợp đồng.
    hd.ma_trang_thai = services.tinh_trang_thai(hd)  # Tính trạng thái theo ngày hiện tại.
    hd.nhan_trang_thai = hd.ma_trang_thai.label  # Lấy nhãn tiếng Việt của trạng thái.
    hd.so_ngay_con_lai = (  # Tính số ngày còn lại nếu hợp đồng có ngày hết hạn.
        (hd.ngayhethan - timezone.localdate()).days if hd.ngayhethan else None
    )  # Hợp đồng không thời hạn nhận giá trị None.
    hd.sap_het_han = (  # Đánh dấu hợp đồng thuộc nhóm cảnh báo.
        hd.ma_trang_thai == HopDong.TrangThai.DANG_HIEU_LUC  # Phải đang có hiệu lực.
        and hd.so_ngay_con_lai is not None  # Phải có ngày hết hạn.
        and 1 <= hd.so_ngay_con_lai <= 30  # Còn từ 1 đến 30 ngày.
    )  # Các thuộc tính bổ sung chỉ phục vụ hiển thị, không lưu vào database.

    return hd  # Trả hợp đồng đã bổ sung thông tin.


def _url_quay_lai(request, danh_sach, chi_tiet):  # Ghi nhớ trang mở form, gồm cả bộ lọc và số trang.
    try:  # URL truyền sai định dạng không được làm lỗi trang chỉnh sửa.
        url = urlsplit(request.GET.get("next", ""))  # Chỉ lấy địa chỉ được truyền từ liên kết Chỉnh sửa.
    except ValueError:  # Ví dụ URL có phần tên máy chủ không hợp lệ.
        return danh_sach  # Quay về tab danh sách thay vì trả lỗi server.
    if not url.scheme and not url.netloc and url.path in (danh_sach, chi_tiet):  # Không chuyển tới website khác hoặc trang ngoài phạm vi.
        return url.path + (f"?{url.query}" if url.query else "")  # Giữ các bộ lọc và trang danh sách ban đầu.
    return danh_sach  # Mở trực tiếp form thì quay về tab danh sách tương ứng.


def _xu_ly_form(request, lop_form, ham_luu, tieu_de, url_huy, *, url_thanh_cong=None, **kwargs):  # Xử lý chung các trang biểu mẫu.
    form = lop_form(  # Khởi tạo đúng loại biểu mẫu.
        request.POST if request.method == "POST" else None, **kwargs
    )  # POST rỗng vẫn được nhận là biểu mẫu đã gửi để hiển thị lỗi bắt buộc.

    if request.method == "POST" and form.is_valid():  # Chỉ ghi dữ liệu sau POST hợp lệ.
        try:  # Gọi service và xử lý những lỗi có thể trả về.
            obj = ham_luu(form=form, nguoi_thuc_hien=request.user)  # Service kiểm tra quyền và lưu dữ liệu.
        except ValidationError as loi:  # Lỗi nghiệp vụ hoặc dữ liệu vừa thay đổi.
            _gan_loi(form, loi)  # Hiển thị lỗi ngay trên biểu mẫu.
        except ObjectDoesNotExist:  # Bản ghi đã bị thay đổi hoặc không còn tồn tại.
            form.add_error(None, "Dữ liệu không còn tồn tại. Vui lòng tải lại trang.")  # Báo lỗi chung.
        except IntegrityError:  # Database phát hiện trùng hoặc vi phạm ràng buộc.
            form.add_error(None, "Dữ liệu bị trùng hoặc không hợp lệ. Vui lòng kiểm tra lại.")  # Báo lỗi chung.
        except DatabaseError:  # Các lỗi database còn lại.
            logger.exception("Không thể lưu dữ liệu nhân sự")  # Ghi chi tiết lỗi vào log.
            form.add_error(None, "Không thể lưu dữ liệu. Vui lòng thử lại sau.")  # Thông báo cho người dùng.
        else:  # Chỉ chạy khi service lưu thành công.
            messages.success(request, f"{tieu_de} thành công.")  # Gửi thông báo thành công.

            if url_thanh_cong:  # Form chỉnh sửa trở về đúng trang đã mở nó.
                return redirect(url_thanh_cong)  # Dùng địa chỉ nội bộ đã kiểm tra trước khi xử lý form.

            if isinstance(obj, NhanVien):  # Nếu vừa lưu hồ sơ nhân viên...
                return redirect("nhan_su:chi_tiet_nhan_vien", manv=obj.pk)  # ...mở chi tiết hồ sơ.

            return redirect("nhan_su:chi_tiet_hop_dong", mahd=obj.pk)  # Hợp đồng được chuyển đến trang chi tiết.

    nhom_truong = []  # Chia biểu mẫu hồ sơ thành hai phần như mockup.
    if isinstance(form, NhanVienForm):  # Các form hợp đồng vẫn dùng lưới chung.
        nhom_truong = [  # Tên nhóm và các BoundField giữ nguyên dữ liệu, lỗi và widget.
            ("Thông tin cá nhân", [form[ten] for ten in ("tennv", "ngaysinh", "gioitinh", "cccd", "sdt", "email", "diachi")]),
            ("Thông tin công việc", [form[ten] for ten in ("maphong", "chucvu", "ngayvaolam", "id_taikhoan")]),
        ]  # Trường tài khoản được quản lý chọn rõ ràng, không tự suy đoán chủ sở hữu.

    return render(  # GET hoặc POST có lỗi đều hiển thị biểu mẫu.
        request, "nhan_su/form.html",  # Dùng chung một template cho các biểu mẫu.
        {"form": form, "tieu_de": tieu_de, "url_huy": url_huy, "nhom_truong": nhom_truong},  # Dữ liệu và bố cục form.
    )  # Biểu mẫu có lỗi vẫn giữ nội dung người dùng đã nhập.


def _hien_thi_ho_so(request, nv, co_quyen_sua):  # Dùng chung cho hồ sơ quản lý và hồ sơ cá nhân.
    hop_dong = (  # Lấy lịch sử hợp đồng nếu đã có hồ sơ.
        list(nv.hop_dong.select_related("manv").order_by("-ngaybatdau", "mahd")) if nv else []
    )  # Người chưa liên kết hồ sơ nhận danh sách rỗng.

    for hd in hop_dong:  # Duyệt các hợp đồng của hồ sơ.
        _bo_sung_trang_thai(hd)  # Bổ sung trạng thái chính xác tại ngày đang xem.

    return render(  # Hiển thị trang chi tiết hồ sơ.
        request, "nhan_su/nhan_vien_detail.html" if co_quyen_sua else "nhan_su/ho_so_cua_toi.html",  # Trang cá nhân có bố cục riêng.
        {"nhan_vien": nv, "hop_dong": hop_dong, "co_quyen_sua": co_quyen_sua},  # Dữ liệu và quyền hiển thị nút.
    )  # Kết thúc xử lý hiển thị hồ sơ.


#view quản lý hsnv
@quan_ly_required  # Yêu cầu tài khoản quản lý.
@require_safe  # Chỉ nhận GET hoặc HEAD, không ghi dữ liệu.
def danh_sach_nhan_vien(request):  # Hiển thị danh sách và bộ lọc nhân viên.
    ds = NhanVien.objects.select_related("maphong")  # Lấy nhân viên cùng phòng ban trong một truy vấn.
    q = request.GET.get("q", "").strip()  # Lấy từ khóa tìm kiếm.

    if q:  # Chỉ tìm kiếm khi có từ khóa.
        ds = ds.filter(Q(manv__icontains=q) | Q(tennv__icontains=q))  # Tìm theo mã hoặc tên.

    for tham_so, truong in (("phong_ban", "maphong_id"), ("chuc_vu", "chucvu")):  # Ánh xạ bộ lọc sang trường model.
        gia_tri = request.GET.get(tham_so, "").strip()  # Lấy giá trị được chọn.
        if gia_tri:  # Nếu người dùng đã chọn tiêu chí...
            ds = ds.filter(**{truong: gia_tri})  # ...áp dụng điều kiện bằng nhau.

    trang_thai = request.GET.get("trang_thai", "")  # Nhận 1: đang làm; 0: đã nghỉ.

    if trang_thai in ("1", "0"):  # Kiểm tra giá trị trạng thái hợp lệ.
        ds = ds.filter(trangthai=trang_thai == "1")  # Chuyển chuỗi thành Boolean để lọc.
    elif trang_thai:  # Có trạng thái nhưng giá trị không được hỗ trợ.
        messages.error(request, "Trạng thái nhân viên không hợp lệ.")  # Thông báo lỗi bộ lọc.
        ds = ds.none()  # Trả danh sách rỗng.

    context = _phan_trang(request, ds.order_by("tennv", "manv"))  # Sắp xếp ổn định trước khi chia trang.
    context["phong_ban"] = PhongBan.objects.order_by("tenphongban")  # Danh mục cho ô lọc phòng ban.
    context["chuc_vu"] = (  # Danh mục chức vụ không trùng nhau.
        NhanVien.objects.order_by("chucvu").values_list("chucvu", flat=True).distinct()
    )  # Chỉ lấy cột chức vụ để giảm dữ liệu truy vấn.

    return render(request, "nhan_su/nhan_vien_list.html", context)  # Hiển thị danh sách.


@quan_ly_required  # Chỉ quản lý được xem hồ sơ bất kỳ.
@require_safe  # Trang chỉ đọc dữ liệu.
def chi_tiet_nhan_vien(request, manv):  # Nhận mã nhân viên từ URL.
    nv = get_object_or_404(  # Trả lỗi 404 nếu mã không tồn tại.
        NhanVien.objects.select_related("maphong", "id_taikhoan"), pk=manv
    )  # Lấy hồ sơ kèm thông tin phòng ban.

    return _hien_thi_ho_so(request, nv, True)  # Hiển thị hồ sơ với quyền quản lý.


@quan_ly_required  # Chỉ quản lý được thêm nhân viên.
@require_http_methods(["GET", "POST"])  # GET mở biểu mẫu; POST gửi dữ liệu.
def them_nhan_vien(request):  # Trang tạo hồ sơ mới.
    return _xu_ly_form(  # Dùng luồng xử lý biểu mẫu chung.
        request, NhanVienForm, services.luu_nhan_vien,  # Chọn form và service.
        "Thêm nhân viên", reverse("nhan_su:danh_sach_nhan_vien"),  # Tiêu đề và URL nút Hủy.
    )  # Không truyền instance nên tạo hồ sơ mới.


@quan_ly_required  # Chỉ quản lý được chỉnh sửa hồ sơ.
@require_http_methods(["GET", "POST"])  # Giới hạn phương thức được nhận.
def sua_nhan_vien(request, manv):  # Trang sửa hồ sơ theo mã.
    nv = get_object_or_404(NhanVien, pk=manv)  # Lấy hồ sơ hoặc trả 404.
    quay_lai = _url_quay_lai(request, reverse("nhan_su:danh_sach_nhan_vien"), reverse("nhan_su:chi_tiet_nhan_vien", args=[manv]))  # Phân biệt mở từ danh sách hay chi tiết.

    return _xu_ly_form(  # Xử lý biểu mẫu chỉnh sửa.
        request, NhanVienForm, services.luu_nhan_vien,  # Dùng lại form và service hồ sơ.
        "Sửa hồ sơ", quay_lai, url_thanh_cong=quay_lai,  # Quay lại, Hủy và Lưu đều về đúng trang ban đầu.
        instance=nv,  # Truyền hồ sơ hiện tại để cập nhật thay vì tạo mới.
    )  # Kết thúc xử lý sửa hồ sơ.


@quan_ly_required  # Chỉ quản lý được vô hiệu hóa hồ sơ.
@require_http_methods(["GET", "POST"])  # GET chỉ mở xác nhận, POST mới thực hiện.
def vo_hieu_hoa_nhan_vien(request, manv):  # Trang nhập ngày và lý do nghỉ việc.
    nv = get_object_or_404(NhanVien, pk=manv)  # Xác định hồ sơ cần xử lý.

    return _xu_ly_form(  # Dùng luồng xử lý biểu mẫu chung.
        request, VoHieuHoaNhanVienForm, services.vo_hieu_hoa_nhan_vien,  # Form và service nghỉ việc.
        "Vô hiệu hóa hồ sơ", reverse("nhan_su:chi_tiet_nhan_vien", args=[manv]),  # Tiêu đề và URL Hủy.
        nhan_vien=nv,  # Đúng tham số mà VoHieuHoaNhanVienForm yêu cầu.
    )  # Service sẽ cập nhật hồ sơ và khóa tài khoản cùng nhau.


#view hợp đồng
def _hien_thi_hop_dong(request, ds, co_quyen_sua):  # Hiển thị danh sách hợp đồng quản lý hoặc cá nhân.
    hom_nay = timezone.localdate()  # Ngày dùng để tính trạng thái.
    dieu_kien = services.dieu_kien_trang_thai()  # Bộ lọc và nhãn cùng dùng quy tắc nghỉ việc.
    dieu_kien["SAP_HET_HAN"] = dieu_kien["DANGHIEULUC"] & Q(  # Cảnh báo chỉ dành cho hợp đồng còn hiệu lực.
        ngayhethan__range=(hom_nay + timedelta(days=1), hom_nay + timedelta(days=30))
    )  # Giữ đúng khoảng 1–30 ngày theo đặc tả.

    q = request.GET.get("q", "").strip()  # Lấy từ khóa tìm kiếm.

    if q:  # Nếu có từ khóa...
        ds = ds.filter(  # ...tìm trong mã hợp đồng, mã nhân viên hoặc họ tên.
            Q(mahd__icontains=q) | Q(manv__manv__icontains=q) | Q(manv__tennv__icontains=q)
        )  # Tiếp tục giữ phạm vi dữ liệu được truyền vào hàm.

    loai = request.GET.get("loai_hd", "")  # Lấy loại hợp đồng được chọn.

    if loai:  # Có chọn loại thì áp dụng bộ lọc.
        ds = ds.filter(loaihd=loai)  # Chỉ lấy hợp đồng đúng loại.

    so_sap_het_han = ds.filter(dieu_kien["SAP_HET_HAN"]).count()  # Banner khớp từ khóa và loại đang lọc.

    trang_thai = request.GET.get("trang_thai", "")  # Lấy trạng thái được chọn.

    if trang_thai in dieu_kien:  # Nếu trạng thái hợp lệ...
        ds = ds.filter(dieu_kien[trang_thai])  # ...áp dụng điều kiện ngày tương ứng.
    elif trang_thai:  # Có giá trị nhưng không nằm trong danh sách hỗ trợ.
        messages.error(request, "Trạng thái hợp đồng không hợp lệ.")  # Thông báo lỗi bộ lọc.
        ds = ds.none()  # Trả danh sách rỗng.

    context = _phan_trang(request, ds.order_by("-ngaybatdau", "mahd"))  # Hợp đồng mới đứng trước.

    for hd in context["page_obj"]:  # Chỉ xử lý các hợp đồng của trang hiện tại.
        _bo_sung_trang_thai(hd)  # Bổ sung nhãn trạng thái và thông tin cảnh báo.

    context.update({  # Bổ sung dữ liệu cho giao diện.
        "co_quyen_sua": co_quyen_sua,  # Quyết định hiển thị các nút quản lý.
        "so_sap_het_han": so_sap_het_han,  # Banner cảnh báo trên danh sách như mockup.
        "loai_hop_dong": HopDong.Loai.choices,  # Danh mục cho ô lọc loại.
        "trang_thai_hop_dong": [  # Danh mục cho ô lọc trạng thái.
            *HopDong.TrangThai.choices,  # Bốn trạng thái đã khai báo trong model.
            ("SAP_HET_HAN", "Sắp hết hạn"),  # Thêm lựa chọn lọc cảnh báo.
        ],  # Kết thúc danh mục trạng thái.
    })  # Kết thúc bổ sung context.

    return render(request, "nhan_su/hop_dong_list.html", context)  # Hiển thị danh sách hợp đồng.


@quan_ly_required  # Chỉ quản lý được xem danh sách toàn bộ hợp đồng.
@require_safe  # Chỉ đọc dữ liệu.
def danh_sach_hop_dong(request):  # Trang quản lý hợp đồng.
    return _hien_thi_hop_dong(  # Dùng hàm danh sách chung.
        request, HopDong.objects.select_related("manv"), True
    )  # Lấy người ký cùng hợp đồng và cho hiển thị nút quản lý.


@quan_ly_required  # Chỉ quản lý được xem hợp đồng bất kỳ.
@require_safe  # Trang chỉ đọc.
def chi_tiet_hop_dong(request, mahd):  # Nhận mã hợp đồng từ URL.
    hd = get_object_or_404(  # Trả 404 nếu hợp đồng không tồn tại.
        HopDong.objects.select_related("manv__maphong"), pk=mahd
    )  # Lấy hợp đồng và người ký trong cùng truy vấn.

    return render(  # Hiển thị trang chi tiết hợp đồng.
        request, "nhan_su/hop_dong_detail.html",  # Template dùng chung cho quản lý và cá nhân.
        {"hop_dong": _bo_sung_trang_thai(hd), "co_quyen_sua": True, "chinh_sach": getattr(settings, "NHAN_SU_CHINH_SACH", {})},  # Chính sách cố định dùng chung theo mockup.
    )  # Kết thúc xử lý chi tiết hợp đồng.


@quan_ly_required  # Chỉ quản lý được tạo hợp đồng.
@require_http_methods(["GET", "POST"])  # GET mở biểu mẫu, POST gửi dữ liệu.
def them_hop_dong(request):  # Trang tạo hợp đồng mới.
    return _xu_ly_form(  # Gọi xử lý biểu mẫu chung.
        request, HopDongForm, services.luu_hop_dong,  # Chọn form và service hợp đồng.
        "Tạo hợp đồng", reverse("nhan_su:danh_sach_hop_dong"),  # Tiêu đề và URL Hủy.
    )  # Service tự cấp mã theo nhóm quản lý hoặc nhân viên.


@quan_ly_required  # Chỉ quản lý được sửa hợp đồng.
@require_http_methods(["GET", "POST"])  # Giới hạn phương thức được hỗ trợ.
def sua_hop_dong(request, mahd):  # Trang chỉnh sửa hợp đồng.
    hd = get_object_or_404(HopDong, pk=mahd)  # Lấy hợp đồng hoặc trả 404.
    quay_lai = _url_quay_lai(request, reverse("nhan_su:danh_sach_hop_dong"), reverse("nhan_su:chi_tiet_hop_dong", args=[mahd]))  # Giữ nguồn mở form hợp đồng.

    return _xu_ly_form(  # Dùng biểu mẫu sửa thông tin.
        request, HopDongForm, services.luu_hop_dong,  # Chọn form và service.
        "Sửa hợp đồng", quay_lai, url_thanh_cong=quay_lai,  # Quay lại, Hủy và Lưu đều giữ phạm vi danh sách hoặc chi tiết.
        instance=hd,  # Cập nhật đúng hợp đồng hiện tại.
    )  # Không tạo mã hợp đồng mới.


@quan_ly_required  # Chỉ quản lý được gia hạn.
@require_http_methods(["GET", "POST"])  # GET mở biểu mẫu, POST thực hiện.
def gia_han_hop_dong(request, mahd):  # Trang gia hạn hợp đồng.
    hd = get_object_or_404(HopDong, pk=mahd)  # Xác định hợp đồng cần gia hạn.
    quay_lai = _url_quay_lai(request, reverse("nhan_su:danh_sach_hop_dong"), reverse("nhan_su:chi_tiet_hop_dong", args=[mahd]))  # Gia hạn dùng cùng quy tắc quay lại.

    return _xu_ly_form(  # Dùng riêng biểu mẫu gia hạn nhưng dùng chung service hợp đồng.
        request, GiaHanHopDongForm, services.luu_hop_dong,  # Truyền đúng loại form.
        "Gia hạn hợp đồng", quay_lai, url_thanh_cong=quay_lai,  # Lưu gia hạn xong trở về đúng trang đã mở.
        instance=hd,  # Gia hạn bản ghi hiện tại để giữ nguyên mã hợp đồng.
    )  # Kết thúc xử lý gia hạn.


#view trang cá nhân
@login_required(login_url="login")  # Quản lý hoặc nhân viên đã đăng nhập đều được truy cập.
@require_safe  # Trang cá nhân chỉ đọc dữ liệu.
def ho_so_cua_toi(request):  # Trang hồ sơ của người đang đăng nhập.
    nv = (  # Tìm hồ sơ bằng tài khoản, không nhận mã nhân viên từ trình duyệt.
        NhanVien.objects.select_related("maphong")
        .filter(id_taikhoan=request.user).first()
    )  # Trả None nếu tài khoản chưa được liên kết hồ sơ.

    return _hien_thi_ho_so(request, nv, False)  # Hiển thị ở chế độ chỉ đọc.


@login_required(login_url="login")  # Yêu cầu người dùng đăng nhập.
@require_safe  # Không nhận POST tại trang xem hợp đồng cá nhân.
def hop_dong_cua_toi(request):  # Danh sách hợp đồng của chính người dùng.
    ds = HopDong.objects.select_related("manv__maphong").filter(  # Lấy hợp đồng kèm người ký và phòng ban.
        manv__id_taikhoan=request.user  # Giới hạn quyền sở hữu ngay trong truy vấn.
    )  # Tài khoản chưa có hồ sơ hoặc hợp đồng nhận danh sách rỗng.

    ds = ds.order_by("-ngaybatdau", "mahd")  # Ưu tiên bản ký gần nhất khi có nhiều hợp đồng.
    hd = ds.filter(services.dieu_kien_trang_thai()["DANGHIEULUC"]).first() or ds.first()  # Hiện hợp đồng đang hiệu lực trước.
    return render(request, "nhan_su/hop_dong_cua_toi.html", {  # Trang riêng theo mockup, vẫn giữ lịch sử.
        "hop_dong": _bo_sung_trang_thai(hd) if hd else None,  # Không lỗi khi chưa có hợp đồng.
        "lich_su": [_bo_sung_trang_thai(cu) for cu in ds.exclude(pk=hd.pk)] if hd else [],  # Các hợp đồng còn lại.
        "co_quyen_sua": False,  # Cá nhân chỉ được đọc.
        "chinh_sach": getattr(settings, "NHAN_SU_CHINH_SACH", {}),  # Chính sách cố định theo mockup, dùng chung với trang quản lý.
    })  # Quyền sở hữu đã được giới hạn trong truy vấn ds.


@login_required(login_url="login")  # Yêu cầu đăng nhập trước khi xem.
@require_safe  # Chỉ cho phép đọc dữ liệu.
def chi_tiet_hop_dong_cua_toi(request, mahd):  # Xem một hợp đồng cá nhân.
    hd = get_object_or_404(  # Trả 404 nếu không tồn tại hoặc không thuộc người dùng.
        HopDong.objects.select_related("manv__maphong"),  # Lấy hợp đồng và thông tin công việc.
        pk=mahd,  # Đúng mã hợp đồng được yêu cầu.
        manv__id_taikhoan=request.user,  # Đồng thời phải thuộc tài khoản đang đăng nhập.
    )  # Không cho xem hợp đồng người khác bằng cách đổi mã trên URL.

    return render(  # Dùng cùng template chi tiết hợp đồng.
        request, "nhan_su/hop_dong_detail.html",  # Template sẽ tạo ở bước 6.
        {"hop_dong": _bo_sung_trang_thai(hd), "co_quyen_sua": False, "chinh_sach": getattr(settings, "NHAN_SU_CHINH_SACH", {})},  # Ẩn nút quản lý.
    )  # Quyền ghi vẫn được kiểm tra riêng tại view quản lý và service.


