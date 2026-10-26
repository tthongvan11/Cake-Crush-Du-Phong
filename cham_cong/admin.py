from django.contrib import admin  # Trang quản trị của Django.

from .models import ChamCong, DonNghiPhep, LoaiPhep  # Ba bảng của phân hệ.


@admin.register(LoaiPhep)  # Hiển thị danh mục loại phép trong admin.
class LoaiPhepAdmin(admin.ModelAdmin):  # Cấu hình trang loại phép.
    list_display = ("maloaiphep", "tenloaiphep", "huongluong", "tru_phepnam")  # Các cột hiển thị.


@admin.register(ChamCong)  # Hiển thị dữ liệu chấm công trong admin.
class ChamCongAdmin(admin.ModelAdmin):  # Cấu hình trang chấm công.
    list_display = ("manv", "ngaychamcong", "gio_checkin", "gio_checkout", "sogiolamviec", "trangthai")  # Các cột.
    list_filter = ("trangthai", "ngaychamcong")  # Bộ lọc bên phải.
    search_fields = ("manv__manv", "manv__tennv")  # Tìm theo mã hoặc tên nhân viên.


@admin.register(DonNghiPhep)  # Hiển thị đơn nghỉ phép trong admin.
class DonNghiPhepAdmin(admin.ModelAdmin):  # Cấu hình trang đơn nghỉ phép.
    list_display = ("madon", "manv", "maloaiphep", "ngaybatdau", "ngayketthuc", "songaynghi", "trangthai")  # Các cột.
    list_filter = ("trangthai", "maloaiphep")  # Bộ lọc bên phải.
    search_fields = ("manv__manv", "manv__tennv")  # Tìm theo nhân viên.
