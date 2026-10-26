from django.urls import path  # Khai báo đường dẫn URL.

from . import views  # Các view của phân hệ chấm công.

app_name = "cham_cong"  # Namespace, ví dụ cham_cong:hom_nay.

urlpatterns = [  # Danh sách URL của phân hệ.
    # ----- 4.1 Chấm công điện tử (Nhân viên) -----
    path("cham-cong/", views.cham_cong_hom_nay, name="hom_nay"),  # Chấm công hôm nay.
    path("cham-cong/check-in/", views.check_in, name="check_in"),  # Ghi nhận Check-in.
    path("cham-cong/check-out/", views.check_out, name="check_out"),  # Ghi nhận Check-out.
    path("cham-cong/lich-su/", views.lich_su, name="lich_su"),  # Lịch sử chấm công.
    # ----- 4.2 Đơn xin nghỉ phép (Nhân viên) -----
    path("nghi-phep/", views.don_cua_toi, name="don_cua_toi"),  # Danh sách đơn của tôi.
    path("nghi-phep/tao/", views.tao_don, name="tao_don"),  # Tạo đơn xin nghỉ.
    path("nghi-phep/<int:madon>/", views.chi_tiet_don_cua_toi, name="chi_tiet_don_cua_toi"),  # Chi tiết đơn của tôi.
    # ----- 4.3 Bảng chấm công (Quản lý) -----
    path("quan-ly/cham-cong/", views.bang_cham_cong, name="bang_cham_cong"),  # Bảng chấm công tổng hợp.
    path("quan-ly/cham-cong/xuat/", views.xuat_bang_cham_cong, name="xuat_bang_cham_cong"),  # Xuất file Excel.
    # ----- 4.4 Duyệt đơn và quỹ phép (Quản lý) -----
    path("quan-ly/nghi-phep/", views.duyet_don_list, name="duyet_don_list"),  # Danh sách đơn cần duyệt.
    path("quan-ly/nghi-phep/<int:madon>/", views.chi_tiet_duyet, name="chi_tiet_duyet"),  # Chi tiết đơn.
    path("quan-ly/nghi-phep/<int:madon>/phe-duyet/", views.phe_duyet, name="phe_duyet"),  # Phê duyệt.
    path("quan-ly/nghi-phep/<int:madon>/tu-choi/", views.tu_choi, name="tu_choi"),  # Từ chối.
    path("quan-ly/quy-phep/", views.quy_phep, name="quy_phep"),  # Quỹ phép năm.
    path("quan-ly/quy-phep/<str:manv>/", views.chi_tiet_quy_phep, name="chi_tiet_quy_phep"),  # Chi tiết quỹ phép.
]  # Kết thúc danh sách URL.
