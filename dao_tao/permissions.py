from django.core.exceptions import PermissionDenied


def la_quan_ly(user):
    """Kiểm tra người dùng có quyền quản lý hay không."""
    return bool(
        user.is_authenticated
        and user.is_active
        and (user.is_staff or user.is_superuser)
    )


def yeu_cau_quan_ly(user):
    """Ném ngoại lệ PermissionDenied nếu người dùng không phải Quản lý/Admin."""
    if not la_quan_ly(user):
        raise PermissionDenied("Bạn không có quyền quản lý đào tạo.")
