from django.contrib import admin  # Cung cấp chức năng quản trị Django.
from .models import HopDong, NhanVien, PhongBan  # Import các model cần đăng ký.


class GiuLichSuAdmin(admin.ModelAdmin):  # Lớp cấu hình dùng chung để chặn xóa.
    def has_delete_permission(self, request, obj=None):  # Kiểm tra quyền xóa từng bản ghi và hàng loạt.
        return False  # Không cho phép xóa qua trang admin.


@admin.register(PhongBan)  # Đăng ký model PhongBan vào admin.
class PhongBanAdmin(admin.ModelAdmin):  # Cấu hình màn hình quản trị phòng ban.
    list_display = ("maphongban", "tenphongban")  # Hiển thị hai cột mã và tên.
    search_fields = ("maphongban", "tenphongban")  # Cho tìm kiếm theo mã hoặc tên.


@admin.register(NhanVien)  # Đăng ký model NhanVien vào admin.
class NhanVienAdmin(GiuLichSuAdmin):  # Kế thừa cấu hình chặn xóa.
    list_display = ("manv", "tennv", "maphong", "chucvu", "trangthai")  # Các cột trên danh sách.
    search_fields = ("manv", "tennv", "email")  # Cho tìm theo mã, tên hoặc email.
    list_filter = ("maphong", "trangthai")  # Tạo bộ lọc phòng ban và trạng thái.
    list_select_related = ("maphong",)  # Lấy phòng ban cùng truy vấn để tránh truy vấn lặp từng dòng.

    def has_add_permission(self, request):  # Kiểm tra quyền thêm hồ sơ qua admin.
        return False  # Tạm không cho thêm; hồ sơ sẽ được tạo qua luồng nghiệp vụ.

    def has_change_permission(self, request, obj=None):  # Kiểm tra quyền sửa hồ sơ qua admin.
        return False  # Tạm không cho sửa để tránh bỏ qua xử lý khóa tài khoản khi nghỉ việc.


@admin.register(HopDong)  # Đăng ký model HopDong vào admin.
class HopDongAdmin(GiuLichSuAdmin):  # Kế thừa cấu hình chặn xóa hợp đồng.
    list_display = (  # Khai báo các cột trên danh sách hợp đồng.
        "mahd", "manv", "loaihd", "ngayhethan", "trangthai"  # Mã, người ký, loại, hạn và trạng thái.
    )  # Kết thúc danh sách cột.
    list_filter = ("loaihd", "trangthai")  # Tạo bộ lọc loại và trạng thái hợp đồng.
    search_fields = ("mahd", "manv__tennv")  # Tìm theo mã hợp đồng hoặc tên nhân viên liên kết.
    list_select_related = ("manv",)  # Lấy nhân viên cùng truy vấn danh sách hợp đồng.

    def has_add_permission(self, request):  # Kiểm tra quyền thêm hợp đồng qua admin.
        return False  # Tạm không cho thêm; sử dụng luồng nghiệp vụ tạo hợp đồng.

    def has_change_permission(self, request, obj=None):  # Kiểm tra quyền sửa hợp đồng qua admin.
        return False  # Tạm không cho sửa; sử dụng luồng kiểm tra và cập nhật hợp đồng.