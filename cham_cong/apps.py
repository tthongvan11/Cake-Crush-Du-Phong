from django.apps import AppConfig  # Lớp cấu hình ứng dụng của Django.


class ChamCongConfig(AppConfig):  # Khai báo phân hệ Chấm công và Quản lý phép.
    default_auto_field = "django.db.models.BigAutoField"  # Kiểu khóa chính mặc định cho model không tự khai báo.
    name = "cham_cong"  # Tên thư mục ứng dụng.
    verbose_name = "Chấm công và quản lý phép"  # Tên hiển thị trong trang admin.
