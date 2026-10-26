from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
     path("", include("nhan_su.urls")),  # Bổ sung URL phân hệ nhân sự (Vân)
    path("", include("cham_cong.urls")),  # Bổ sung URL phân hệ chấm công và quản lý phép
    path('', include('tai_khoan.urls')),
]

urlpatterns += staticfiles_urlpatterns()
