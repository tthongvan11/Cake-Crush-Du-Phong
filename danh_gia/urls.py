from django.urls import path

from . import views

app_name = "danh_gia"

urlpatterns = [
    path("", views.trang_chu, name="trang_chu"),

    # UC-1.1 / 1.2: kỳ đánh giá, tiêu chí
    path("ky/", views.ky_danh_sach, name="ky_ds"),
    path("ky/tao/", views.ky_tao, name="ky_tao"),
    path("ky/<str:maky>/tieu-chi/", views.tieu_chi_thiet_lap, name="tieu_chi"),
    path("ky/<str:maky>/ket-qua/", views.ky_ket_qua, name="ky_ket_qua"),

    # UC-1.3: chấm điểm (chọn kỳ + nhân viên ngay trên trang, qua ?ky=...&nv=...)
    path("cham-diem/", views.danh_gia_tao, name="danh_gia_tao"),
    path("cham-diem/xac-nhan/", views.danh_gia_xac_nhan, name="danh_gia_xac_nhan"),

    # UC-2.1 khen thưởng, UC-2.2 kỷ luật (mỗi loại một view, dùng chung logic ở views/ghi_nhan.py)
    path("khen-thuong/", views.khen_thuong, name="khen_thuong"),
    path("ky-luat/", views.ky_luat, name="ky_luat"),

    # UC-2.3, 2.4 (nhân viên)
    path("ket-qua/", views.ket_qua_cua_toi, name="ket_qua"),
    path("ket-qua/<str:madanhgia>/phan-hoi/", views.gui_phan_hoi, name="phan_hoi"),
]
