from django.urls import path
from . import views

urlpatterns = [
    path('', views.trang_chao_mung, name='trang_chu'),
    path('welcome/', views.trang_chao_mung, name='welcome'),
    path('login/', views.CakeCrushLoginView.as_view(), name='login'),
    path('logout/', views.CakeCrushLogoutView.as_view(), name='logout'),
    path('dashboard/', views.dieu_huong_dashboard, name='dashboard'),
    path('home/', views.dieu_huong_dashboard, name='home'),
    path('quan-ly/', views.trang_quan_ly, name='trang_quan_ly'),
    path('nhan-vien/', views.trang_nhan_vien, name='trang_nhan_vien'),
]
