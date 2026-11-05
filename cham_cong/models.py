from django.core.validators import MinValueValidator  # Kiểm tra giá trị không được nhỏ hơn mức tối thiểu.
from django.db import models  # Cung cấp lớp Model và các kiểu trường dữ liệu.

from nhan_su.models import NhanVien  # Dùng lại bảng NHANVIEN của phân hệ nhân sự, không tạo bảng mới.


class LoaiPhep(models.Model):  # Bảng LOAIPHEP: danh mục loại nghỉ phép.
    maloaiphep = models.AutoField(primary_key=True)  # Khóa chính tự sinh định danh loại phép.
    tenloaiphep = models.CharField("Tên loại phép", max_length=100, unique=True)  # Tên loại phép, không được trùng.
    huongluong = models.BooleanField("Hưởng lương", default=False)  # True: nghỉ có hưởng lương.
    tru_phepnam = models.BooleanField("Trừ phép năm", default=False)  # True: trừ vào quỹ phép năm khi đơn được duyệt.

    class Meta:  # Cấu hình bổ sung cho model.
        db_table = "LOAIPHEP"  # Tên bảng đúng ERD.
        ordering = ["maloaiphep"]  # Sắp xếp danh mục theo thứ tự tạo.

    def __str__(self):  # Cách hiển thị loại phép trong ô chọn và admin.
        return self.tenloaiphep  # Hiển thị tên loại phép.


class ChamCong(models.Model):  # Bảng CHAMCONG: mỗi nhân viên một bản ghi cho mỗi ngày.
    class TrangThai(models.TextChoices):  # Các trạng thái làm việc trong ngày.
        DI_LAM = "DILAM", "Đi làm"  # Có dữ liệu Check-in/Check-out.
        NGHI_PHEP = "NGHIPHEP", "Nghỉ có phép"  # Đồng bộ từ đơn nghỉ đã duyệt.
        VANG_KHONG_PHEP = "VANGKHONGPHEP", "Vắng không phép"  # Ngày làm việc không chấm công, không có đơn.

    machamcong = models.AutoField(primary_key=True)  # Khóa chính tự sinh, không cho sửa.
    manv = models.ForeignKey(  # Nhân viên thực hiện chấm công.
        NhanVien,  # Liên kết tới bảng NHANVIEN.
        on_delete=models.PROTECT,  # Không cho xóa nhân viên khi còn dữ liệu chấm công.
        related_name="cham_cong",  # Lấy dữ liệu bằng nhan_vien.cham_cong.all().
        verbose_name="Nhân viên",  # Nhãn hiển thị.
    )  # Kết thúc khai báo khóa ngoại nhân viên.
    ngaychamcong = models.DateField("Ngày chấm công")  # Ngày ghi nhận chấm công.
    gio_checkin = models.TimeField("Giờ Check-in", null=True, blank=True)  # Hệ thống tự ghi theo giờ máy chủ.
    gio_checkout = models.TimeField("Giờ Check-out", null=True, blank=True)  # Chỉ có sau khi đã Check-in.
    sogiolamviec = models.DecimalField(  # Tổng số giờ làm việc thực tế trong ngày.
        "Số giờ làm việc", max_digits=4, decimal_places=2, null=True, blank=True,  # Tối đa 99,99 giờ, 2 số lẻ.
    )  # Hệ thống tự tính khi đủ Check-in và Check-out.
    thoigianditre = models.PositiveIntegerField("Đi trễ (phút)", null=True, blank=True)  # Số phút sau giờ bắt đầu ca.
    thoigianvesom = models.PositiveIntegerField("Về sớm (phút)", null=True, blank=True)  # Số phút trước giờ kết thúc ca.
    sogiolamthem = models.DecimalField(  # Số giờ làm thêm phát sinh, chỉ để đối soát.
        "Số giờ làm thêm", max_digits=4, decimal_places=2, null=True, blank=True,  # Cùng định dạng với số giờ làm việc.
        validators=[MinValueValidator(0)],  # Giá trị không được âm.
    )  # Không tự động được công nhận là tăng ca tính lương.
    trangthai = models.CharField(  # Trạng thái làm việc trong ngày.
        "Trạng thái", max_length=30, choices=TrangThai.choices,  # Chỉ nhận 3 giá trị theo ERD.
    )  # Bắt buộc có giá trị.
    ghichu = models.TextField("Ghi chú", null=True, blank=True)  # Ghi chú hoặc giải trình, không bắt buộc.

    class Meta:  # Cấu hình bảng và ràng buộc.
        db_table = "CHAMCONG"  # Tên bảng đúng ERD.
        constraints = [  # Ràng buộc kiểm tra tại database.
            models.UniqueConstraint(fields=["manv", "ngaychamcong"], name="unique_nv_ngay"),  # Mỗi nhân viên một bản ghi mỗi ngày.
        ]  # Kết thúc danh sách ràng buộc.
        ordering = ["-ngaychamcong"]  # Ngày mới nhất hiển thị trước.

    def __str__(self):  # Cách hiển thị bản ghi chấm công.
        return f"{self.manv_id} - {self.ngaychamcong:%d/%m/%Y}"  # Mã nhân viên kèm ngày.


class DonNghiPhep(models.Model):  # Bảng DONNGHIPHEP: đơn xin nghỉ của nhân viên.
    class TrangThai(models.TextChoices):  # Các trạng thái xét duyệt.
        CHO_DUYET = "CHODUYET", "Chờ duyệt"  # Đơn vừa gửi.
        DA_DUYET = "DADUYET", "Đã duyệt"  # Quản lý đã phê duyệt.
        TU_CHOI = "TUCHOI", "Từ chối"  # Quản lý từ chối kèm phản hồi.

    madon = models.AutoField(primary_key=True)  # Khóa chính tự sinh, không cho sửa.
    manv = models.ForeignKey(  # Nhân viên gửi đơn.
        NhanVien,  # Liên kết tới bảng NHANVIEN.
        on_delete=models.PROTECT,  # Không cho xóa nhân viên khi còn đơn.
        related_name="don_nghi_phep",  # Lấy đơn bằng nhan_vien.don_nghi_phep.all().
        verbose_name="Nhân viên",  # Nhãn hiển thị.
    )  # Kết thúc khai báo khóa ngoại nhân viên.
    maloaiphep = models.ForeignKey(  # Loại phép nhân viên xin nghỉ.
        LoaiPhep,  # Liên kết tới bảng LOAIPHEP.
        on_delete=models.PROTECT,  # Không cho xóa loại phép đang được sử dụng.
        related_name="don_nghi_phep",  # Lấy đơn theo loại phép.
        verbose_name="Loại phép",  # Nhãn hiển thị.
    )  # Kết thúc khai báo khóa ngoại loại phép.
    ngaybatdau = models.DateField("Ngày bắt đầu")  # Ngày bắt đầu nghỉ, phải từ hôm nay trở đi.
    ngayketthuc = models.DateField("Ngày kết thúc")  # Ngày kết thúc nghỉ, không trước ngày bắt đầu.
    songaynghi = models.PositiveIntegerField("Số ngày nghỉ")  # Hệ thống tự tính từ khoảng ngày nghỉ.
    lydo = models.TextField("Lý do xin nghỉ")  # Bắt buộc nhân viên giải trình.
    thoigianguidon = models.DateTimeField("Thời gian gửi đơn", auto_now_add=True)  # Tự lưu lúc gửi đơn.
    trangthai = models.CharField(  # Trạng thái xét duyệt.
        "Trạng thái", max_length=20, choices=TrangThai.choices, default=TrangThai.CHO_DUYET,  # Mặc định Chờ duyệt.
    )  # Kết thúc khai báo trạng thái.
    nguoiduyet = models.ForeignKey(  # Quản lý trực tiếp duyệt hoặc từ chối.
        NhanVien,  # Người duyệt cũng là một hồ sơ nhân viên.
        on_delete=models.SET_NULL,  # Xóa người duyệt thì chỉ để trống trường này.
        null=True, blank=True,  # Để trống khi đơn chưa được xử lý.
        related_name="don_da_duyet",  # Phân biệt với đơn do chính nhân viên gửi.
        verbose_name="Người duyệt",  # Nhãn hiển thị.
    )  # Kết thúc khai báo người duyệt.
    ngayduyet = models.DateTimeField("Thời gian xét duyệt", null=True, blank=True)  # Ghi nhận khi duyệt hoặc từ chối.
    phanhoi = models.TextField("Phản hồi của quản lý", null=True, blank=True)  # Bắt buộc khi từ chối.

    class Meta:  # Cấu hình bảng.
        db_table = "DONNGHIPHEP"  # Tên bảng đúng ERD.
        ordering = ["-thoigianguidon", "-madon"]  # Đơn mới nhất hiển thị trước.

    @property  # Dùng như một thuộc tính khi hiển thị.
    def ma_hien_thi(self):  # Mã đơn dạng NP001 giống mockup.
        return f"NP{self.madon:03d}"  # Ghép tiền tố NP với số thứ tự 3 chữ số.

    def __str__(self):  # Cách hiển thị đơn.
        return f"{self.ma_hien_thi} - {self.manv_id}"  # Mã đơn kèm mã nhân viên.
