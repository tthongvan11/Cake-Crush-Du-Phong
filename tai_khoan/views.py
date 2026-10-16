from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

class CakeCrushLoginView(LoginView):

    template_name = 'login.html'
    redirect_authenticated_user = False
    def get_success_url(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return '/admin/'
        return reverse_lazy('trang_nhan_vien')


class CakeCrushLogoutView(LogoutView):
    next_page = reverse_lazy('login')


@login_required
def trang_nhan_vien(request):
    return render(request, 'nhan_vien_home.html')