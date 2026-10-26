from django.contrib.auth import get_user_model  # Lấy model tài khoản đang sử dụng.
from django.core.exceptions import ValidationError  # Thông báo lỗi nghiệp vụ.
from django.db import models, transaction  # Cung cấp truy vấn và giao dịch database.
from django.db.models.functions import Cast, Substr  # Cắt phần số của mã và chuyển sang số nguyên.
from django.db.models.functions import Coalesce  # Dùng ngày hiện tại nếu hồ sơ cũ thiếu ngày nghỉ.
from django.utils import timezone  # Lấy ngày theo múi giờ dự án.
from .forms import GiaHanHopDongForm  # Nhận diện biểu mẫu gia hạn hợp đồng.
from .models import HopDong, NhanVien  # Import các model cần xử lý.
from .permissions import yeu_cau_quan_ly  # Dùng chung hàm kiểm tra quyền.


def _kiem_tra_form(form):  # Kiểm tra biểu mẫu trước khi sử dụng dữ liệu.
    if not form.is_valid():  # Nếu dữ liệu nhập không hợp lệ...
        raise ValidationError(form.errors.as_data())  # ...trả lại lỗi theo từng trường.


def _du_lieu(form):  # Lấy những trường model được biểu mẫu cho phép cập nhật.
    _kiem_tra_form(form)  # Bảo đảm biểu mẫu đã hợp lệ.
    return {  # Tạo dictionary gồm tên trường và giá trị đã kiểm tra.
        ten: form.cleaned_data[ten] for ten in form.Meta.fields
    }  # Không lấy mã, quyền tài khoản hoặc các trường ngoài danh sách cho phép.


def _tao_ma(model, tien_to):  # Sinh mã tăng dần bên trong giao dịch lưu dữ liệu.
    truong = model._meta.pk  # Lấy thông tin trường khóa chính của model.
    cung_nhom = model.objects.filter(  # Chỉ tìm các mã đúng nhóm và có phần đuôi là số.
        **{f"{truong.name}__regex": rf"^{tien_to}[0-9]+$"}
    )  # Bỏ qua các mã UUID cũ có chứa chữ trong phần đuôi.
    phan_so = Cast(  # Chuyển phần đuôi của mã thành số nguyên.
        Substr(truong.name, len(tien_to) + 1), models.IntegerField()
    )  # Ví dụ NV009 thành số 9.
    so_cu = cung_nhom.aggregate(so=models.Max(phan_so))["so"] or 0  # Chưa có mã thì bắt đầu từ 0.
    ma = f"{tien_to}{so_cu + 1:03d}"  # Tăng một đơn vị, hiển thị tối thiểu ba chữ số.

    if len(ma) > truong.max_length:  # Không cho mã vượt độ dài trường trong ERD.
        raise ValidationError("Đã đạt giới hạn mã của nhóm này.")  # Dừng cấp mã.

    return ma  # Trả mã mới để service lưu vào database.


def tinh_trang_thai(hop_dong):  # Tính trạng thái hợp đồng tại ngày hiện tại.
    if hop_dong.trangthai == HopDong.TrangThai.CHAM_DUT:  # Hợp đồng đã chấm dứt...
        return HopDong.TrangThai.CHAM_DUT  # ...không tự chuyển lại thành đang hiệu lực.

    hom_nay = timezone.localdate()  # Lấy ngày hiện tại tại Việt Nam.
    nv = hop_dong.manv  # Đọc hồ sơ đã được select_related ở view.
    ngay_nghi = nv.ngaynghiviec or hom_nay  # Xử lý cả hồ sơ cũ chưa ghi ngày nghỉ.

    if not nv.trangthai and (not hop_dong.ngayhethan or hop_dong.ngayhethan >= ngay_nghi):  # Còn hạn khi nghỉ.
        return HopDong.TrangThai.CHAM_DUT  # Không tiếp tục hiển thị hiệu lực sau khi nghỉ việc.

    if hom_nay < hop_dong.ngaybatdau:  # Chưa đến ngày bắt đầu.
        return HopDong.TrangThai.CHUA_HIEU_LUC  # Trả trạng thái chưa hiệu lực.

    if hop_dong.ngayhethan and hom_nay > hop_dong.ngayhethan:  # Đã qua ngày hết hạn.
        return HopDong.TrangThai.HET_HAN  # Trả trạng thái hết hạn.

    return HopDong.TrangThai.DANG_HIEU_LUC  # Các trường hợp còn lại đang hiệu lực.


def dieu_kien_trang_thai():  # Dùng chung điều kiện lọc với quy tắc hiển thị trạng thái.
    hom_nay = timezone.localdate()  # Mốc tính trạng thái động theo ngày.
    ngay_nghi = Coalesce("manv__ngaynghiviec", models.Value(hom_nay))  # Dữ liệu cũ có thể thiếu ngày nghỉ.
    cham_dut = models.Q(trangthai=HopDong.TrangThai.CHAM_DUT) | (  # Ưu tiên hợp đồng đã chấm dứt.
        models.Q(manv__trangthai=False)  # Hồ sơ đã nghỉ việc...
        & (models.Q(ngayhethan__isnull=True) | models.Q(ngayhethan__gte=ngay_nghi))  # ...và còn hạn lúc nghỉ.
    )  # Hợp đồng hết hạn trước ngày nghỉ vẫn giữ lịch sử hết hạn.
    bat_dau = models.Q(ngaybatdau__lte=hom_nay)  # Đã đến ngày bắt đầu.
    return {  # Mã trạng thái khớp ERD và bộ lọc giao diện.
        "CHAMDUT": cham_dut,  # Bao gồm cả dữ liệu cũ chưa đồng bộ.
        "CHUHIEULUC": ~cham_dut & models.Q(ngaybatdau__gt=hom_nay),  # Chưa đến ngày bắt đầu.
        "HETHAN": ~cham_dut & bat_dau & models.Q(ngayhethan__lt=hom_nay),  # Hết hạn tự nhiên.
        "DANGHIEULUC": ~cham_dut & bat_dau & (  # Đã bắt đầu và vẫn còn hạn.
            models.Q(ngayhethan__isnull=True) | models.Q(ngayhethan__gte=hom_nay)
        ),  # Hợp đồng không thời hạn cũng thuộc nhóm này.
    }  # View bổ sung khoảng ngày khi lọc sắp hết hạn.


@transaction.atomic  # Toàn bộ thao tác thành công hoặc được hoàn tác.
def luu_nhan_vien(*, form, nguoi_thuc_hien):  # Thêm hoặc sửa hồ sơ từ NhanVienForm.
    yeu_cau_quan_ly(nguoi_thuc_hien)  # Chỉ quản lý được thực hiện.
    data = _du_lieu(form)  # Lấy dữ liệu đã được kiểm tra.
    la_moi = form.instance._state.adding  # Xác định đang tạo mới hay chỉnh sửa.
    nv = NhanVien() if la_moi else NhanVien.objects.get(  # Khi sửa, đọc lại dữ liệu mới nhất.
        pk=form.instance.pk  # Giữ đúng hồ sơ đang được chỉnh sửa.
    )  # Không dùng trạng thái hồ sơ cũ đã nạp từ trước.
    tai_khoan_cu = nv.id_taikhoan_id  # Giữ liên kết gốc trước khi gán dữ liệu biểu mẫu.

    for ten, gia_tri in data.items():  # Duyệt các trường biểu mẫu cho phép sửa.
        setattr(nv, ten, gia_tri)  # Gán giá trị vào trường tương ứng của nhân viên.

    if not nv.trangthai and nv.id_taikhoan_id != tai_khoan_cu:  # Không gắn tài khoản mới cho hồ sơ đã nghỉ.
        raise ValidationError({"id_taikhoan": "Không thể đổi tài khoản của hồ sơ đã nghỉ việc."})  # Tránh bỏ qua khóa tài khoản.

    if la_moi:  # Chỉ cấp mã khi tạo hồ sơ mới.
        nv.manv = _tao_ma(NhanVien, "NV")  # Sinh NV001, NV002...

    if nv.ngaynghiviec and nv.ngaynghiviec < nv.ngayvaolam:  # Kiểm tra khi sửa hồ sơ đã nghỉ việc.
        raise ValidationError({  # Gắn lỗi vào trường ngày vào làm.
            "ngayvaolam": "Ngày vào làm không được sau ngày nghỉ việc."
        })  # Dừng lưu dữ liệu không hợp lệ.

    nv.full_clean()  # Kiểm tra lại model, tính duy nhất và các ràng buộc.
    nv.save(force_insert=la_moi, force_update=not la_moi)  # Tạo mới hoặc cập nhật, không ghi đè nhầm mã.
    return nv  # Trả hồ sơ đã lưu cho view sử dụng.


@transaction.atomic  # Cập nhật hồ sơ và khóa tài khoản trong cùng một giao dịch.
def vo_hieu_hoa_nhan_vien(*, form, nguoi_thuc_hien):  # Nhận VoHieuHoaNhanVienForm.
    yeu_cau_quan_ly(nguoi_thuc_hien)  # Chỉ quản lý được vô hiệu hóa hồ sơ.
    _kiem_tra_form(form)  # Kiểm tra ngày và lý do nghỉ việc.
    nv = NhanVien.objects.get(pk=form.nhan_vien.pk)  # Đọc lại hồ sơ mới nhất.
    ngay_nghi = form.cleaned_data["ngaynghiviec"]  # Lấy ngày nghỉ đã được chuyển thành kiểu date.

    if not nv.trangthai:  # Kiểm tra lại trạng thái tại thời điểm lưu.
        raise ValidationError("Hồ sơ này đã được vô hiệu hóa.")  # Không xử lý nghỉ việc lần nữa.

    if nv.id_taikhoan_id == nguoi_thuc_hien.pk:  # Nếu hồ sơ thuộc chính quản lý đang thao tác...
        raise ValidationError("Bạn không thể tự vô hiệu hóa hồ sơ của mình.")  # ...chặn tự khóa tài khoản.

    if not nv.ngayvaolam <= ngay_nghi <= timezone.localdate():  # So sánh với ngày vào làm mới nhất.
        raise ValidationError({  # Gắn lỗi vào trường ngày nghỉ.
            "ngaynghiviec": "Ngày nghỉ việc không hợp lệ."
        })  # Ngày nghỉ phải từ ngày vào làm đến hôm nay.

    nv.trangthai = False  # Chuyển hồ sơ sang đã nghỉ việc.
    nv.ngaynghiviec = ngay_nghi  # Ghi ngày nghỉ.
    nv.lydonghiviec = form.cleaned_data["lydonghiviec"]  # Ghi lý do đã kiểm tra.
    nv.full_clean()  # Kiểm tra hồ sơ trước khi lưu.
    nv.save(  # Chỉ cập nhật ba trường phục vụ nghỉ việc.
        update_fields=["trangthai", "ngaynghiviec", "lydonghiviec"]
    )  # Các thông tin khác được giữ nguyên.

    nv.hop_dong.exclude(trangthai=HopDong.TrangThai.CHAM_DUT).update(  # Đồng bộ hợp đồng trong cùng giao dịch.
        trangthai=models.Case(  # Phân biệt hợp đồng lịch sử với hợp đồng còn hạn khi nghỉ.
            models.When(ngayhethan__lt=ngay_nghi, then=models.Value(HopDong.TrangThai.HET_HAN)),  # Giữ hết hạn tự nhiên.
            default=models.Value(HopDong.TrangThai.CHAM_DUT),  # Chấm dứt cả hợp đồng còn hạn và chưa bắt đầu.
            output_field=models.CharField(),  # Kết quả được lưu vào trường chuỗi trạng thái.
        )  # Giữ nguyên mã, thời hạn đã ký và lương của hợp đồng.
    )  # Nếu bước khóa tài khoản lỗi, tất cả thay đổi đều được hoàn tác.

    if nv.id_taikhoan_id:  # Hồ sơ có tài khoản liên kết thì thực hiện khóa.
        get_user_model().objects.filter(  # Tìm đúng tài khoản của nhân viên.
            pk=nv.id_taikhoan_id
        ).update(is_active=False)  # Khóa tài khoản, không xóa tài khoản.

    return nv  # Trả hồ sơ; lịch sử hợp đồng được giữ và đã đồng bộ trạng thái.


@transaction.atomic  # Gộp kiểm tra, cấp mã và lưu hợp đồng trong một giao dịch.
def luu_hop_dong(*, form, nguoi_thuc_hien):  # Dùng cho cả HopDongForm và GiaHanHopDongForm.
    yeu_cau_quan_ly(nguoi_thuc_hien)  # Chỉ quản lý được ghi thông tin hợp đồng.
    data = _du_lieu(form)  # Lấy các trường được phép cập nhật.
    la_moi = form.instance._state.adding  # Xác định hợp đồng mới hay đã tồn tại.
    hd = HopDong() if la_moi else HopDong.objects.get(  # Khi sửa, đọc lại bản ghi mới nhất.
        pk=form.instance.pk  # Giữ đúng hợp đồng đang được xử lý.
    )  # Giúp kiểm tra gia hạn với dữ liệu hiện tại trong database.

    if not la_moi and (not hd.manv.trangthai or hd.trangthai == HopDong.TrangThai.CHAM_DUT):  # Kiểm tra lại khi lưu.
        raise ValidationError("Không thể sửa hoặc gia hạn hợp đồng đã chấm dứt hoặc nhân viên đã nghỉ việc.")  # Chặn cả POST trực tiếp.

    if isinstance(form, GiaHanHopDongForm):  # Nếu đang thực hiện gia hạn...
        if hd.loaihd == HopDong.Loai.KHONG_XAC_DINH:  # ...kiểm tra lại loại hợp đồng.
            raise ValidationError("Hợp đồng không thời hạn không cần gia hạn.")  # Chặn thao tác không phù hợp.

        if hd.ngayhethan and data["ngayhethan"] <= hd.ngayhethan:  # So sánh với ngày hết hạn mới nhất.
            raise ValidationError({  # Gắn lỗi vào ngày hết hạn mới.
                "ngayhethan": "Ngày mới phải sau ngày hết hạn hiện tại."
            })  # Ngăn ghi đè một lần gia hạn khác bằng dữ liệu cũ.

    if not la_moi and "manv" in data and data["manv"].pk != hd.manv_id:  # Kiểm tra người sở hữu khi sửa.
        raise ValidationError("Không được thay đổi người sở hữu hợp đồng.")  # Giữ hợp đồng đúng nhân viên.

    for ten, gia_tri in data.items():  # Duyệt các trường được biểu mẫu cho phép sửa.
        setattr(hd, ten, gia_tri)  # Gán dữ liệu vào hợp đồng.

    if la_moi:  # Chỉ chọn nhóm và cấp mã khi tạo hợp đồng mới.
        nv = NhanVien.objects.select_related("id_taikhoan").get(  # Lấy hồ sơ và tài khoản trong cùng truy vấn.
            pk=hd.manv_id  # Đọc lại nhân viên được chọn.
        )  # Dùng trạng thái và quyền tài khoản mới nhất.

        if not nv.trangthai:  # Nhân viên có thể đã nghỉ sau khi biểu mẫu được mở.
            raise ValidationError("Không thể tạo hợp đồng cho nhân viên đã nghỉ việc.")  # Dừng tạo hợp đồng.

        hd.manv = nv  # Gắn hồ sơ mới đọc vào hợp đồng.
        tk = nv.id_taikhoan  # Lấy tài khoản liên kết, có thể là None.

        if tk:  # Hồ sơ đã có tài khoản thì xác định nhóm từ quyền.
            nhom = "QL" if tk.is_staff or tk.is_superuser else "NV"  # Chọn nhóm quản lý hoặc nhân viên.
        else:  # Hồ sơ chưa có tài khoản...
            nhom = form.cleaned_data.get("nhom_ma")  # ...dùng nhóm người quản lý đã chọn.

        if nhom not in ("QL", "NV"):  # Kiểm tra lại nhóm mã hợp lệ.
            raise ValidationError({"nhom_ma": "Vui lòng chọn QL hoặc NV."})  # Báo lỗi nếu thiếu nhóm.

        hd.mahd = _tao_ma(HopDong, f"HD-{nhom}-")  # Cấp mã riêng theo nhóm QL hoặc NV.

    hom_nay = timezone.localdate()  # Ngày dùng để kiểm tra hợp đồng còn hiệu lực.
    cung_loai = HopDong.objects.filter(  # Tìm hợp đồng cùng nhân viên và cùng loại.
        manv_id=hd.manv_id,  # Cùng người ký.
        loaihd=hd.loaihd,  # Cùng loại hợp đồng.
        ngaybatdau__lte=hom_nay,  # Đã đến ngày bắt đầu hiệu lực.
    ).exclude(  # Loại trừ bản ghi đang chỉnh sửa.
        pk=hd.pk
    ).exclude(  # Không tính hợp đồng đã chấm dứt.
        trangthai=HopDong.TrangThai.CHAM_DUT
    ).filter(  # Chỉ giữ hợp đồng chưa hết hạn hoặc không có ngày hết hạn.
        models.Q(ngayhethan__isnull=True) | models.Q(ngayhethan__gte=hom_nay)
    )  # Kết thúc truy vấn hợp đồng cùng loại còn hiệu lực.

    if hd.trangthai != HopDong.TrangThai.CHAM_DUT and cung_loai.exists():  # Phát hiện hợp đồng cùng loại còn hiệu lực.
        raise ValidationError(  # Trả cảnh báo và chưa lưu để quản lý kiểm tra lại.
            "Nhân viên đang có hợp đồng cùng loại còn hiệu lực. Vui lòng kiểm tra lại."
        )  # Áp dụng kiểm tra trên dữ liệu ngày thực tế, không dựa vào trạng thái có thể đã cũ.

    hd.trangthai = tinh_trang_thai(hd)  # Cập nhật trạng thái theo các ngày vừa nhập.
    hd.full_clean()  # Kiểm tra loại, ngày, lương và các ràng buộc của model.
    hd.save(force_insert=la_moi, force_update=not la_moi)  # Lưu mới hoặc cập nhật hợp đồng hiện tại.
    return hd  # Trả hợp đồng đã lưu, giữ nguyên mã khi chỉnh sửa hoặc gia hạn.
