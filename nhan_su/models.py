from decimal import Decimal  # Biểu diễn số thập phân chính xác, phù hợp lưu tiền.
from uuid import uuid4  # Tạo UUID ngẫu nhiên để cấp mã trong phiên bản này.

from django.conf import settings  # Đọc cấu hình Django, gồm model tài khoản đang dùng.
from django.core.exceptions import ValidationError  # Tạo thông báo lỗi kiểm tra dữ liệu.
from django.core.validators import MinValueValidator, RegexValidator  # Kiểm tra giá trị nhỏ nhất và định dạng.
from django.db import models  # Cung cấp lớp Model và các kiểu trường dữ liệu.


def tao_ma_nhan_vien():  # Hàm tạo mã nhân viên trong phiên bản UUID.
    return f"NV{uuid4().hex[:8].upper()}"  # Ghép NV với 8 ký tự đầu của UUID viết hoa.


def tao_ma_hop_dong():  # Hàm tạo mã hợp đồng trong phiên bản UUID.
    return f"HD{uuid4().hex[:8].upper()}"  # Ghép HD với 8 ký tự đầu của UUID viết hoa.


class PhongBan(models.Model):  # Khai báo model lưu danh mục phòng ban.
    maphongban = models.CharField(  # Mã phòng ban được lưu dưới dạng chuỗi.
        "Mã phòng ban",  # Nhãn hiển thị trên biểu mẫu.
        max_length=10,  # Chuỗi dài tối đa 10 ký tự.
        primary_key=True,  # Dùng trường này làm khóa chính; không tạo thêm cột id.
    )  # Kết thúc khai báo mã phòng ban.

    tenphongban = models.CharField(  # Khai báo tên phòng ban.
        "Tên phòng ban",  # Nhãn hiển thị của trường.
        max_length=100,  # Tên dài tối đa 100 ký tự.
        unique=True,  # Không cho hai phòng ban có cùng tên.
    )  # Kết thúc khai báo tên phòng ban.

    mota = models.TextField("Mô tả", null=True, blank=True)  # Cho phép không nhập mô tả và lưu NULL.
    ngaytao = models.DateTimeField(auto_now_add=True)  # Tự ghi thời điểm tạo bản ghi lần đầu.

    class Meta:  # Chứa cấu hình bổ sung cho model.
        db_table = "PHONGBAN"  # Đặt tên bảng trong database là PHONGBAN.

    def __str__(self):  # Xác định cách hiển thị một đối tượng phòng ban.
        return self.tenphongban  # Hiển thị tên phòng ban trong admin và ô lựa chọn.


class NhanVien(models.Model):  # Khai báo model lưu hồ sơ nhân viên.
    manv = models.CharField(  # Mã nhân viên được lưu dưới dạng chuỗi.
        max_length=10,  # Mã dài tối đa 10 ký tự.
        primary_key=True,  # Dùng mã nhân viên làm khóa chính.
        default=tao_ma_nhan_vien,  # Gọi hàm cấp mã khi khởi tạo đối tượng không truyền mã.
        editable=False,  # Không đưa trường mã vào các biểu mẫu chỉnh sửa tự động.
    )  # Kết thúc khai báo mã nhân viên.

    id_taikhoan = models.OneToOneField(  # Liên kết một hồ sơ với tối đa một tài khoản.
        settings.AUTH_USER_MODEL,  # Tham chiếu model tài khoản được cấu hình trong Django.
        on_delete=models.PROTECT,  # Chặn xóa tài khoản đang được hồ sơ này tham chiếu.
        related_name="ho_so",  # Cho phép lấy hồ sơ từ tài khoản bằng user.ho_so.
        null=True,  # Cho phép database lưu NULL khi hồ sơ chưa có tài khoản.
        blank=True,  # Cho phép để trống trường tài khoản trên biểu mẫu.
    )  # Kết thúc khai báo liên kết tài khoản.

    maphong = models.ForeignKey(  # Liên kết nhiều nhân viên với một phòng ban.
        PhongBan,  # Model được tham chiếu là PhongBan.
        on_delete=models.PROTECT,  # Chặn xóa phòng ban đang có nhân viên tham chiếu.
        related_name="nhan_vien",  # Lấy nhân viên bằng phong_ban.nhan_vien.all().
        verbose_name="Phòng ban",  # Nhãn hiển thị trên biểu mẫu.
    )  # Kết thúc khai báo liên kết phòng ban.

    tennv = models.CharField("Họ tên", max_length=100)  # Họ tên bắt buộc, tối đa 100 ký tự.
    ngaysinh = models.DateField("Ngày sinh", null=True, blank=True)  # Ngày sinh được phép bỏ trống.

    gioitinh = models.CharField(  # Lưu giới tính dưới dạng chuỗi.
        "Giới tính",  # Nhãn hiển thị.
        max_length=3,  # Chuỗi dài tối đa 3 ký tự.
        choices=[("Nam", "Nam"), ("Nữ", "Nữ")],  # Mỗi cặp gồm giá trị lưu và nhãn hiển thị.
    )  # Kết thúc khai báo giới tính.

    sdt = models.CharField(  # Dùng chuỗi để giữ được số 0 ở đầu số điện thoại.
        "Số điện thoại",  # Nhãn hiển thị.
        max_length=10,  # Tối đa 10 ký tự.
        unique=True,  # Không được trùng số điện thoại giữa các hồ sơ.
        validators=[  # Danh sách các hàm kiểm tra giá trị của trường.
            RegexValidator(  # Kiểm tra chuỗi bằng biểu thức chính quy.
                r"\A[0-9]{10}\Z",  # Toàn bộ chuỗi phải gồm đúng 10 chữ số từ 0 đến 9.
                "Số điện thoại phải gồm đúng 10 chữ số.",  # Thông báo khi sai định dạng.
            )  # Kết thúc bộ kiểm tra số điện thoại.
        ],  # Kết thúc danh sách bộ kiểm tra.
    )  # Kết thúc khai báo số điện thoại.

    email = models.EmailField("Email", max_length=254, unique=True)  # Kiểm tra định dạng email và yêu cầu duy nhất.

    cccd = models.CharField(  # Lưu CCCD dưới dạng chuỗi để giữ số 0 ở đầu.
        "CCCD",  # Nhãn hiển thị.
        max_length=12,  # Tối đa 12 ký tự.
        unique=True,  # Không được trùng CCCD giữa các hồ sơ.
        validators=[  # Danh sách bộ kiểm tra CCCD.
            RegexValidator(  # Kiểm tra định dạng bằng biểu thức chính quy.
                r"\A[0-9]{12}\Z",  # Toàn bộ chuỗi phải gồm đúng 12 chữ số.
                "CCCD phải gồm đúng 12 chữ số.",  # Thông báo khi nhập sai.
            )  # Kết thúc bộ kiểm tra CCCD.
        ],  # Kết thúc danh sách bộ kiểm tra.
    )  # Kết thúc khai báo CCCD.

    diachi = models.CharField("Địa chỉ", max_length=255, blank=True)  # Địa chỉ tối đa 255 ký tự, được bỏ trống.
    chucvu = models.CharField("Chức vụ", max_length=100)  # Chức vụ bắt buộc, tối đa 100 ký tự.
    ngayvaolam = models.DateField("Ngày vào làm")  # Lưu ngày bắt đầu làm việc, không chứa giờ.

    trangthai = models.BooleanField("Đang làm việc", default=True)  # True: đang làm việc; False: đã nghỉ.

    ngaynghiviec = models.DateField(  # Khai báo ngày nghỉ việc.
        "Ngày nghỉ việc",  # Nhãn hiển thị.
        null=True,  # Cho phép lưu NULL khi chưa nghỉ việc.
        blank=True,  # Cho phép để trống trên biểu mẫu.
    )  # Kết thúc khai báo ngày nghỉ việc.

    lydonghiviec = models.TextField("Lý do nghỉ việc", blank=True)  # Nội dung lý do, được bỏ trống khi chưa nghỉ.

    class Meta:  # Cấu hình bổ sung cho model nhân viên.
        db_table = "NHANVIEN"  # Tên bảng trong database.

    def __str__(self):  # Xác định cách hiển thị đối tượng nhân viên.
        return f"{self.manv} - {self.tennv}"  # Hiển thị mã kèm họ tên.


class HopDong(models.Model):  # Khai báo model lưu hợp đồng lao động.
    class Loai(models.TextChoices):  # Tập các loại hợp đồng được phép lựa chọn.
        THU_VIEC = "THU_VIEC", "Thử việc"  # Giá trị lưu THU_VIEC, nhãn hiển thị Thử việc.
        XAC_DINH_1_NAM = "XAC_DINH_1_NAM", "Xác định thời hạn 1 năm"  # Hợp đồng có thời hạn một năm.
        KHONG_XAC_DINH = "KHONG_XAC_DINH", "Không xác định thời hạn"  # Hợp đồng không có ngày hết hạn.

    class TrangThai(models.TextChoices):  # Tập các trạng thái của hợp đồng.
        CHUA_HIEU_LUC = "CHUHIEULUC", "Chưa hiệu lực"  # Hợp đồng chưa đến thời điểm hiệu lực.
        DANG_HIEU_LUC = "DANGHIEULUC", "Đang hiệu lực"  # Hợp đồng đang có hiệu lực.
        HET_HAN = "HETHAN", "Hết hạn"  # Hợp đồng đã hết thời hạn.
        CHAM_DUT = "CHAMDUT", "Hết hiệu lực"  # Giữ mã ERD; hiển thị khi hợp đồng chấm dứt.

    mahd = models.CharField(  # Khai báo mã hợp đồng.
        max_length=10,  # Mã dài tối đa 10 ký tự.
        primary_key=True,  # Dùng mã hợp đồng làm khóa chính.
        default=tao_ma_hop_dong,  # Gọi hàm sinh mã khi khởi tạo đối tượng không truyền mã.
        editable=False,  # Không cho nhập hoặc sửa mã qua biểu mẫu tự động.
    )  # Kết thúc khai báo mã hợp đồng.

    manv = models.ForeignKey(  # Mỗi hợp đồng thuộc một nhân viên.
        NhanVien,  # Model được tham chiếu.
        on_delete=models.PROTECT,  # Chặn xóa nhân viên khi vẫn còn hợp đồng tham chiếu.
        related_name="hop_dong",  # Lấy hợp đồng bằng nhan_vien.hop_dong.all().
        verbose_name="Nhân viên",  # Nhãn hiển thị trên biểu mẫu.
    )  # Kết thúc khai báo liên kết nhân viên.

    loaihd = models.CharField(  # Lưu loại hợp đồng.
        "Loại hợp đồng",  # Nhãn hiển thị.
        max_length=30,  # Giá trị lưu dài tối đa 30 ký tự.
        choices=Loai.choices,  # Dùng các lựa chọn đã khai báo trong lớp Loai.
    )  # Kết thúc khai báo loại hợp đồng.

    ngayky = models.DateField("Ngày ký")  # Ngày ký kết hợp đồng.
    ngaybatdau = models.DateField("Ngày bắt đầu")  # Ngày hợp đồng bắt đầu có hiệu lực.

    ngayhethan = models.DateField(  # Khai báo ngày kết thúc hiệu lực.
        "Ngày hết hạn",  # Nhãn hiển thị.
        null=True,  # Cho phép lưu NULL với hợp đồng không thời hạn.
        blank=True,  # Cho phép biểu mẫu nhận giá trị trống; clean() sẽ kiểm tra theo loại.
    )  # Kết thúc khai báo ngày hết hạn.

    luongcoban = models.DecimalField(  # Lưu tiền dưới dạng số thập phân chính xác.
        "Lương cơ bản",  # Nhãn hiển thị.
        max_digits=18,  # Tối đa 18 chữ số, tính cả trước và sau dấu thập phân.
        decimal_places=2,  # Có tối đa 2 chữ số sau dấu thập phân.
        validators=[MinValueValidator(Decimal("0.01"))],  # Giá trị nhỏ nhất là 0,01.
    )  # Kết thúc khai báo lương cơ bản.

    ngaygiahan = models.DateField(  # Khai báo ngày gia hạn gần nhất.
        "Ngày gia hạn",  # Nhãn hiển thị.
        null=True,  # Cho phép lưu NULL nếu chưa gia hạn.
        blank=True,  # Cho phép bỏ trống trên biểu mẫu.
    )  # Kết thúc khai báo ngày gia hạn.

    trangthai = models.CharField(  # Lưu trạng thái hợp đồng.
        "Trạng thái",  # Nhãn hiển thị.
        max_length=20,  # Giá trị lưu dài tối đa 20 ký tự.
        choices=TrangThai.choices,  # Chỉ sử dụng các trạng thái đã khai báo.
        default=TrangThai.CHUA_HIEU_LUC,  # Mặc định là Chưa hiệu lực khi tạo đối tượng.
    )  # Kết thúc khai báo trạng thái.

    class Meta:  # Cấu hình bảng và các ràng buộc database.
        db_table = "HOPDONG"  # Tên bảng trong database.
        constraints = [  # Danh sách điều kiện được kiểm tra tại database.
            models.CheckConstraint(  # Ràng buộc thứ nhất: kiểm tra mức lương.
                condition=models.Q(luongcoban__gt=0),  # __gt nghĩa là lớn hơn: lương phải lớn hơn 0.
                name="hd_luong_duong",  # Tên duy nhất để nhận diện ràng buộc.
            ),  # Kết thúc ràng buộc lương.
            models.CheckConstraint(  # Ràng buộc thứ hai: kiểm tra loại và thời hạn hợp đồng.
                condition=(  # Bắt đầu biểu thức điều kiện.
                    models.Q(  # Nhánh dành cho hợp đồng không xác định thời hạn.
                        loaihd="KHONG_XAC_DINH",  # Loại hợp đồng phải là không thời hạn.
                        ngayhethan__isnull=True,  # Ngày hết hạn phải là NULL.
                    )  # Kết thúc nhánh không thời hạn.
                    | models.Q(  # Dấu | nghĩa là HOẶC: chấp nhận nhánh có thời hạn bên dưới.
                        loaihd__in=["THU_VIEC", "XAC_DINH_1_NAM"],  # Loại thuộc một trong hai giá trị này.
                        ngayhethan__gt=models.F("ngaybatdau"),  # So sánh ngày hết hạn với cột ngày bắt đầu.
                    )  # Kết thúc nhánh có thời hạn.
                ),  # Kết thúc biểu thức điều kiện.
                name="hd_thoi_han_hop_le",  # Tên nhận diện ràng buộc thời hạn.
            ),  # Kết thúc ràng buộc thời hạn.
        ]  # Kết thúc danh sách ràng buộc.

    def clean(self):  # Kiểm tra các quy tắc liên quan giữa nhiều trường.
        super().clean()  # Gọi xử lý kiểm tra của lớp cha.

        if self.loaihd == self.Loai.KHONG_XAC_DINH:  # Xử lý hợp đồng không thời hạn.
            if self.ngayhethan:  # Nếu người dùng vẫn nhập ngày hết hạn...
                raise ValidationError({  # ...tạo lỗi gắn với trường ngày hết hạn.
                    "ngayhethan":  # Tên trường sẽ hiển thị lỗi.
                        "Hợp đồng không xác định thời hạn phải để trống ngày hết hạn."  # Nội dung lỗi.
                })  # Dừng kiểm tra và trả lỗi.

        elif self.loaihd:  # Xử lý những loại hợp đồng còn lại đã được chọn.
            if not self.ngayhethan:  # Kiểm tra người dùng có bỏ trống ngày hết hạn không.
                raise ValidationError({  # Tạo lỗi cho trường ngày hết hạn.
                    "ngayhethan": "Vui lòng nhập ngày hết hạn."  # Yêu cầu bổ sung ngày.
                })  # Dừng kiểm tra và trả lỗi.

            if self.ngaybatdau and self.ngayhethan <= self.ngaybatdau:  # Kiểm tra thứ tự hai ngày.
                raise ValidationError({  # Tạo lỗi nếu ngày kết thúc không sau ngày bắt đầu.
                    "ngayhethan": "Ngày hết hạn phải sau ngày bắt đầu."  # Nội dung lỗi.
                })  # Dừng kiểm tra và trả lỗi.

    def __str__(self):  # Xác định cách hiển thị một đối tượng hợp đồng.
        return f"{self.mahd} - {self.manv.tennv}"  # Hiển thị mã hợp đồng kèm tên nhân viên.
