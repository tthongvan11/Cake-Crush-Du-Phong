from django.urls import path
from . import views

app_name = "dao_tao"

urlpatterns = [
    # Không gian Quản lý
    path("quan-ly/dao-tao/", views.danh_sach_khoa, name="danh_sach_khoa"),
    path("quan-ly/dao-tao/them/", views.tao_khoa, name="tao_khoa"),
    path("quan-ly/dao-tao/phan-cong/", views.phan_cong_dao_tao, name="phan_cong_dao_tao"),
    path("quan-ly/dao-tao/theo-doi/", views.theo_doi_dao_tao, name="theo_doi_dao_tao"),
    path("quan-ly/dao-tao/cap-nhat-ket-qua/", views.cap_nhat_ket_qua_dao_tao, name="cap_nhat_ket_qua_dao_tao"),
    path("quan-ly/dao-tao/<str:makhoa>/", views.chi_tiet_khoa, name="chi_tiet_khoa"),
    path("quan-ly/dao-tao/<str:makhoa>/sua-noi-dung/", views.cap_nhat_noi_dung_khoa, name="cap_nhat_noi_dung_khoa"),

    # API hỗ trợ dropdown động
    path("api/khoa-theo-nhan-vien/", views.api_khoa_theo_nhan_vien, name="api_khoa_theo_nhan_vien"),

    # Không gian Nhân viên
    path("dao-tao-cua-toi/", views.chuong_trinh_cua_toi, name="chuong_trinh_cua_toi"),
    path("dao-tao-cua-toi/noi-dung/", views.xem_noi_dung_dao_tao, name="xem_noi_dung_dao_tao"),
    path("dao-tao-cua-toi/ket-qua/", views.ket_qua_dao_tao_cua_toi, name="ket_qua_dao_tao_cua_toi"),
]
