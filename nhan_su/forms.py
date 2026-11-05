from django import forms  # Cung cấp Form, ModelForm và các ô nhập liệu.
from django.contrib.auth import get_user_model  # Lấy danh sách tài khoản để quản lý liên kết hồ sơ.
from django.utils import timezone  # Lấy ngày hiện tại theo múi giờ dự án.
from .models import HopDong, NhanVien  # Import hai model dùng cho biểu mẫu.


def o_chon_ngay():  # Tạo một widget chọn ngày để dùng lại.
    return forms.DateInput(  # Dùng ô nhập dành cho ngày tháng.
        format="%Y-%m-%d",  # Định dạng giá trị theo chuẩn ô ngày của trình duyệt.
        attrs={"type": "date"},  # Hiển thị bộ chọn ngày trên trình duyệt.
    )  # Trả về widget vừa tạo.


class NhanVienForm(forms.ModelForm):  # Dùng chung cho thêm mới và sửa hồ sơ.
    class Meta:  # Khai báo model, trường và cách hiển thị.
        model = NhanVien  # Biểu mẫu làm việc với model NhanVien.
        fields = [  # Chỉ cho phép người dùng sửa những trường được liệt kê.
            "tennv",  # Họ tên nhân viên.
            "ngaysinh",  # Ngày sinh.
            "gioitinh",  # Giới tính.
            "sdt",  # Số điện thoại.
            "email",  # Địa chỉ email.
            "cccd",  # Số căn cước công dân.
            "diachi",  # Địa chỉ liên hệ.
            "maphong",  # Phòng ban làm việc.
            "chucvu",  # Chức vụ của nhân viên.
            "ngayvaolam",  # Ngày bắt đầu làm việc.
            "id_taikhoan",  # Quản lý chọn tài khoản để người dùng xem đúng hồ sơ của mình.
        ]  # Mã và trạng thái nghỉ việc vẫn được xử lý riêng tại service.
        labels = {"id_taikhoan": "Tài khoản liên kết"}  # Nhãn rõ nghĩa thay tên cột ERD.
        help_texts = {"id_taikhoan": "Chọn tài khoản đăng nhập của nhân viên để mở Hồ sơ của tôi và Hợp đồng của tôi."}  # Không tự ghép bằng email.
        widgets = {  # Tùy chỉnh ô nhập của một số trường.
            "ngaysinh": o_chon_ngay(),  # Hiển thị bộ chọn ngày sinh.
            "ngayvaolam": o_chon_ngay(),  # Hiển thị bộ chọn ngày vào làm.
            "diachi": forms.Textarea(attrs={"rows": 2}),  # Địa chỉ có thể nhập nhiều dòng.
        }  # Kết thúc cấu hình widget.

    def __init__(self, *args, **kwargs):  # Giới hạn tài khoản có thể liên kết.
        super().__init__(*args, **kwargs)  # Tạo các trường của ModelForm.
        da_gan = NhanVien.objects.exclude(pk=self.instance.pk).values("id_taikhoan_id")  # Hồ sơ khác đã dùng tài khoản nào.
        self.fields["id_taikhoan"].queryset = get_user_model().objects.exclude(  # Không cho chọn tài khoản của hồ sơ khác.
            pk__in=da_gan.filter(id_taikhoan__isnull=False)
        ).filter(is_active=True).order_by("username")  # Chỉ chọn tài khoản còn hoạt động.
        if not self.instance._state.adding and not self.instance.trangthai:  # Hồ sơ đã nghỉ giữ nguyên liên kết.
            self.fields["id_taikhoan"].queryset = get_user_model().objects.filter(pk=self.instance.id_taikhoan_id)  # Bao gồm tài khoản đã khóa.
            self.fields["id_taikhoan"].disabled = True  # POST giả mạo cũng không đổi được trường này.

    def clean_email(self):  # Kiểm tra bổ sung cho trường email.
        email = self.cleaned_data["email"].strip().lower()  # Bỏ khoảng trắng và chuẩn hóa chữ thường.
        trung = NhanVien.objects.filter(email__iexact=email)  # Tìm email trùng, không phân biệt hoa thường.

        if not self.instance._state.adding:  # Nếu đang sửa một hồ sơ đã tồn tại...
            trung = trung.exclude(pk=self.instance.pk)  # ...không tính chính hồ sơ đang sửa.

        if trung.exists():  # Kiểm tra cả hồ sơ đang làm việc và đã nghỉ việc.
            raise forms.ValidationError("Email đã được sử dụng bởi hồ sơ khác.")  # Gắn lỗi vào ô email.

        return email  # Trả email đã chuẩn hóa để tiếp tục kiểm tra và lưu.


class VoHieuHoaNhanVienForm(forms.Form):  # Chỉ nhận dữ liệu, chưa tự cập nhật database.
    ngaynghiviec = forms.DateField(  # Khai báo ngày nghỉ việc bắt buộc.
        label="Ngày nghỉ việc",  # Nhãn hiển thị trên biểu mẫu.
        widget=o_chon_ngay(),  # Dùng bộ chọn ngày.
        initial=timezone.localdate,  # Khi mở biểu mẫu, mặc định là ngày hiện tại.
    )  # Kết thúc khai báo ngày nghỉ việc.

    lydonghiviec = forms.CharField(  # Khai báo lý do nghỉ việc bắt buộc.
        label="Lý do nghỉ việc",  # Nhãn hiển thị.
        strip=True,  # Loại bỏ khoảng trắng đầu và cuối nội dung.
        widget=forms.Textarea(attrs={"rows": 3}),  # Dùng ô nhập nhiều dòng.
    )  # Kết thúc khai báo lý do nghỉ việc.

    def __init__(self, *args, nhan_vien, **kwargs):  # Bắt buộc truyền nhân viên cần vô hiệu hóa.
        super().__init__(*args, **kwargs)  # Khởi tạo biểu mẫu theo cơ chế Django.
        self.nhan_vien = nhan_vien  # Giữ hồ sơ để kiểm tra ngày và trạng thái.

    def clean_ngaynghiviec(self):  # Kiểm tra ngày nghỉ sau khi Django chuyển thành kiểu date.
        ngay_nghi = self.cleaned_data["ngaynghiviec"]  # Lấy ngày nghỉ đã nhập.

        if ngay_nghi < self.nhan_vien.ngayvaolam:  # Ngày nghỉ không được trước ngày vào làm.
            raise forms.ValidationError("Ngày nghỉ việc không được trước ngày vào làm.")  # Báo lỗi ngày.

        if ngay_nghi > timezone.localdate():  # Luồng này khóa tài khoản ngay, chưa lập lịch nghỉ tương lai.
            raise forms.ValidationError("Ngày nghỉ việc không được ở tương lai.")  # Yêu cầu ngày phù hợp.

        return ngay_nghi  # Trả ngày nghỉ hợp lệ.

    def clean(self):  # Kiểm tra điều kiện chung của thao tác vô hiệu hóa.
        data = super().clean()  # Chạy kiểm tra mặc định và lấy dữ liệu hợp lệ.

        if not self.nhan_vien.trangthai:  # Hồ sơ đã nghỉ việc không được vô hiệu hóa lần nữa.
            raise forms.ValidationError("Hồ sơ này đã được vô hiệu hóa.")  # Hiển thị lỗi chung.

        return data  # Trả dữ liệu để bước xử lý nghiệp vụ sử dụng.


class HopDongForm(forms.ModelForm):  # Dùng cho tạo mới hoặc chỉnh sửa thông tin hợp đồng.
    nhom_ma = forms.ChoiceField(  # Trường bổ sung trên biểu mẫu, không tạo cột database.
        label="Nhóm mã hợp đồng",  # Nhãn hiển thị.
        choices=[  # Các lựa chọn nhóm mã.
            ("", "Tự xác định từ tài khoản"),  # Hồ sơ có tài khoản được xác định nhóm tự động.
            ("QL", "Quản lý"),  # Dùng tiền tố HD-QL-.
            ("NV", "Nhân viên"),  # Dùng tiền tố HD-NV-.
        ],  # Kết thúc danh sách lựa chọn.
        required=False,  # Chỉ bắt buộc chọn khi hồ sơ chưa có tài khoản.
        help_text="Chỉ cần chọn nếu hồ sơ chưa có tài khoản.",  # Hướng dẫn dưới ô nhập.
    )  # Kết thúc khai báo nhóm mã.

    class Meta:  # Cấu hình các trường lấy từ model.
        model = HopDong  # Biểu mẫu làm việc với model HopDong.
        fields = [  # Chỉ đưa các trường nghiệp vụ được phép nhập lên biểu mẫu.
            "manv",  # Nhân viên ký hợp đồng.
            "loaihd",  # Loại hợp đồng theo đặc tả.
            "ngayky",  # Ngày ký kết.
            "ngaybatdau",  # Ngày bắt đầu hiệu lực.
            "ngayhethan",  # Ngày hết hạn nếu có.
            "luongcoban",  # Lương cơ bản thỏa thuận.
        ]  # Mã và trạng thái hợp đồng được xử lý phía server.
        widgets = {  # Cấu hình bộ chọn ngày cho ba trường.
            "ngayky": o_chon_ngay(),  # Ô chọn ngày ký.
            "ngaybatdau": o_chon_ngay(),  # Ô chọn ngày bắt đầu.
            "ngayhethan": o_chon_ngay(),  # Ô chọn ngày hết hạn.
        }  # Kết thúc cấu hình widget.

    def __init__(self, *args, **kwargs):  # Tùy chỉnh biểu mẫu khi được khởi tạo.
        super().__init__(*args, **kwargs)  # Khởi tạo các trường của ModelForm.

        if self.instance._state.adding:  # Trường hợp tạo hợp đồng mới.
            self.fields["manv"].queryset = NhanVien.objects.filter(  # Giới hạn nhân viên được lựa chọn.
                trangthai=True  # Chỉ cho tạo mới với nhân viên đang làm việc.
            ).order_by("tennv", "manv")  # Sắp xếp ổn định theo tên rồi mã.
        else:  # Trường hợp sửa hợp đồng đã tồn tại.
            self.fields["manv"].queryset = NhanVien.objects.filter(  # Giữ nhân viên hiện tại trong ô chọn.
                pk=self.instance.manv_id  # Vẫn hiển thị được nếu nhân viên đã nghỉ việc.
            )  # Kết thúc truy vấn nhân viên hiện tại.
            self.fields["manv"].disabled = True  # Không cho đổi người sở hữu hợp đồng, kể cả sửa POST.
            self.fields.pop("nhom_ma")  # Hợp đồng đã có mã nên không chọn lại nhóm.

    def clean(self):  # Kiểm tra thêm điều kiện chọn nhóm mã.
        data = super().clean()  # Giữ kiểm tra model và tính duy nhất của ModelForm.
        nhan_vien = data.get("manv")  # Lấy nhân viên nếu trường này đã hợp lệ.

        if self.instance._state.adding and nhan_vien:  # Chỉ kiểm tra nhóm khi tạo hợp đồng mới.
            if not nhan_vien.id_taikhoan_id and not data.get("nhom_ma"):  # Chưa có tài khoản và chưa chọn nhóm.
                self.add_error(  # Gắn lỗi vào trường nhóm mã.
                    "nhom_ma", "Hồ sơ chưa có tài khoản. Vui lòng chọn QL hoặc NV."
                )  # Người dùng cần chọn nhóm trước khi tiếp tục.

        return data  # Trả dữ liệu đã kiểm tra.


class GiaHanHopDongForm(forms.ModelForm):  # Chỉ cập nhật các thông tin phục vụ gia hạn.
    class Meta:  # Cấu hình model và các trường được sửa.
        model = HopDong  # Gia hạn trên hợp đồng hiện tại, không tạo hợp đồng mới.
        fields = [  # Giới hạn đúng các trường cần cập nhật.
            "ngaygiahan",  # Ngày thực hiện gia hạn.
            "ngayhethan",  # Ngày hết hạn mới.
            "luongcoban",  # Mức lương sau điều chỉnh.
        ]  # Không cho sửa mã, nhân viên hoặc loại hợp đồng tại đây.
        widgets = {  # Cấu hình ô nhập ngày.
            "ngaygiahan": o_chon_ngay(),  # Bộ chọn ngày gia hạn.
            "ngayhethan": o_chon_ngay(),  # Bộ chọn ngày hết hạn mới.
        }  # Kết thúc cấu hình widget.

    def __init__(self, *args, instance, **kwargs):  # Bắt buộc truyền hợp đồng cần gia hạn.
        if instance._state.adding:  # Không nhận đối tượng chưa được lưu vào database.
            raise ValueError("Cần truyền hợp đồng đã tồn tại để gia hạn.")  # Báo lỗi cách gọi trong code.

        super().__init__(*args, instance=instance, **kwargs)  # Nạp dữ liệu hợp đồng vào biểu mẫu.
        self.fields["ngaygiahan"].required = True  # Ngày gia hạn bắt buộc nhập.
        self.initial["ngaygiahan"] = timezone.localdate()  # Mặc định ngày gia hạn là hôm nay.
        self.fields["ngayhethan"].required = (  # Bắt buộc ngày hết hạn cho hợp đồng có thời hạn.
            instance.loaihd != HopDong.Loai.KHONG_XAC_DINH  # Xác định theo loại hợp đồng hiện tại.
        )  # Kết thúc cấu hình yêu cầu ngày hết hạn.

    def clean_ngayhethan(self):  # Kiểm tra ngày hết hạn mới trước khi cập nhật instance.
        ngay_moi = self.cleaned_data.get("ngayhethan")  # Lấy ngày người dùng vừa nhập.
        ngay_cu = self.instance.ngayhethan  # Lấy ngày hết hạn trước lần gia hạn này.

        if ngay_moi and ngay_cu and ngay_moi <= ngay_cu:  # Gia hạn phải làm tăng thời hạn.
            raise forms.ValidationError("Ngày hết hạn mới phải sau ngày hết hạn cũ.")  # Báo lỗi ngày mới.

        return ngay_moi  # Trả ngày hết hạn để model kiểm tra tiếp.

    def clean(self):  # Kiểm tra loại hợp đồng có phù hợp thao tác gia hạn không.
        data = super().clean()  # Chạy kiểm tra mặc định của ModelForm.

        if self.instance.loaihd == HopDong.Loai.KHONG_XAC_DINH:  # Hợp đồng không thời hạn không cần kéo dài hạn.
            raise forms.ValidationError(  # Hiển thị thông báo ở đầu biểu mẫu.
                "Hợp đồng không xác định thời hạn không cần gia hạn. Hãy dùng chức năng chỉnh sửa."
            )  # Kết thúc thông báo lỗi.

        return data  # Trả dữ liệu hợp lệ.


