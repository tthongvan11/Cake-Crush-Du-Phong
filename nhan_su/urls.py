from django.urls import path  # Khai báo đường dẫn URL.
from django.urls import reverse_lazy  # Tạo liên kết sau khi các URL đã được nạp.
from django.contrib.auth import views as auth_views  # Dùng luồng đổi mật khẩu chuẩn của Django.
from . import views  # Import các view vừa viết.


app_name = "nhan_su"  # Namespace để dùng tên như nhan_su:them_nhan_vien.


urlpatterns = [  # Danh sách URL của phân hệ.
    path("tai-khoan/doi-mat-khau/", auth_views.PasswordChangeView.as_view(  # Yêu cầu đăng nhập và mật khẩu hiện tại.
        template_name="nhan_su/form.html", success_url=reverse_lazy("nhan_su:doi_mat_khau_xong"),  # Tái dùng giao diện form.
        extra_context={"tieu_de": "Đổi mật khẩu", "url_huy": reverse_lazy("nhan_su:ho_so_cua_toi")},  # Tiêu đề và nút hủy.
    ), name="doi_mat_khau"),  # Liên kết từ thẻ bảo mật cá nhân.
    path("tai-khoan/doi-mat-khau/xong/", auth_views.PasswordChangeDoneView.as_view(  # Trang xác nhận sau khi lưu.
        template_name="nhan_su/doi_mat_khau_xong.html",  # Không thay đổi dữ liệu khi mở bằng GET.
    ), name="doi_mat_khau_xong"),  # Kết thúc luồng đổi mật khẩu.
    path("quan-ly/nhan-vien/", views.danh_sach_nhan_vien, name="danh_sach_nhan_vien"),  # Danh sách hồ sơ.
    path("quan-ly/nhan-vien/them/", views.them_nhan_vien, name="them_nhan_vien"),  # Tạo hồ sơ mới.
    path("quan-ly/nhan-vien/<str:manv>/", views.chi_tiet_nhan_vien, name="chi_tiet_nhan_vien"),  # Chi tiết hồ sơ.
    path("quan-ly/nhan-vien/<str:manv>/sua/", views.sua_nhan_vien, name="sua_nhan_vien"),  # Sửa hồ sơ.
    path("quan-ly/nhan-vien/<str:manv>/vo-hieu-hoa/", views.vo_hieu_hoa_nhan_vien, name="vo_hieu_hoa_nhan_vien"),  # Nghỉ việc.

    path("quan-ly/hop-dong/", views.danh_sach_hop_dong, name="danh_sach_hop_dong"),  # Danh sách hợp đồng.
    path("quan-ly/hop-dong/them/", views.them_hop_dong, name="them_hop_dong"),  # Tạo hợp đồng mới.
    path("quan-ly/hop-dong/<str:mahd>/", views.chi_tiet_hop_dong, name="chi_tiet_hop_dong"),  # Chi tiết hợp đồng.
    path("quan-ly/hop-dong/<str:mahd>/sua/", views.sua_hop_dong, name="sua_hop_dong"),  # Sửa hợp đồng.
    path("quan-ly/hop-dong/<str:mahd>/gia-han/", views.gia_han_hop_dong, name="gia_han_hop_dong"),  # Gia hạn.

    path("ho-so-cua-toi/", views.ho_so_cua_toi, name="ho_so_cua_toi"),  # Hồ sơ cá nhân.
    path("hop-dong-cua-toi/", views.hop_dong_cua_toi, name="hop_dong_cua_toi"),  # Hợp đồng cá nhân.
    path("hop-dong-cua-toi/<str:mahd>/", views.chi_tiet_hop_dong_cua_toi, name="chi_tiet_hop_dong_cua_toi"),  # Chi tiết hợp đồng sở hữu.
]  # Kết thúc danh sách URL.
