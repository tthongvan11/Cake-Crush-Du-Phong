from django.urls import path
from . import views

urlpatterns = [
    path('', views.trang_nhan_vien, name='home'),
    path('login/', views.CakeCrushLoginView.as_view(), name='login'),
    path('logout/', views.CakeCrushLogoutView.as_view(), name='logout'),
    path('nhan-vien/', views.trang_nhan_vien, name='trang_nhan_vien'),
]