from django.core.exceptions import PermissionDenied  # Tạo lỗi từ chối truy cập.


def la_quan_ly(user):  # Kiểm tra quyền quản lý theo quy ước hiện tại của dự án.
    return bool(  # Trả về True hoặc False.
        user.is_authenticated  # Người dùng phải đăng nhập.
        and user.is_active  # Tài khoản phải đang hoạt động.
        and (user.is_staff or user.is_superuser)  # Có quyền quản lý hoặc superuser.
    )  # Kết thúc điều kiện kiểm tra.


def yeu_cau_quan_ly(user):  # Chặn thao tác nghiệp vụ nếu người dùng không đủ quyền.
    if not la_quan_ly(user):  # Nếu không đáp ứng điều kiện quản lý...
        raise PermissionDenied("Bạn không có quyền quản lý nhân sự.")  # ...trả lỗi truy cập.