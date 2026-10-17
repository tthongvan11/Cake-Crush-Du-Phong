from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

class CakeCrushLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = False

    def get_success_url(self):
        user = self.request.user
        # Quản lý -> Vào đúng giao diện Dashboard Quản lý
        if user.is_staff or user.is_superuser:
            return reverse_lazy('trang_quan_ly')
        # Nhân viên -> Vào Dashboard Nhân viên
        return reverse_lazy('trang_nhan_vien')


class CakeCrushLogoutView(LogoutView):
    next_page = reverse_lazy('login')


@login_required
def trang_nhan_vien(request):
    return render(request, 'nhan_vien_home.html')


@login_required
def trang_quan_ly(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('trang_nhan_vien')
    return render(request, 'quan_ly_home.html')


def trang_chu(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_staff or request.user.is_superuser:
        return redirect('trang_quan_ly')
    return redirect('trang_nhan_vien')