"""UC-1.1 (kỳ đánh giá) và UC-1.2 (tiêu chí)."""
from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from ..models import KyDanhGia, TieuChi
from ._chung import FormMixin


# ---------- UC-1.1: kỳ đánh giá ----------
class KyDanhGiaForm(FormMixin, forms.ModelForm):
    class Meta:
        model = KyDanhGia
        fields = ["tenky", "thoigianbatdau", "thoigianketthuc"]
        labels = {
            "tenky": "Tên kỳ đánh giá",
            "thoigianbatdau": "Ngày bắt đầu",
            "thoigianketthuc": "Ngày kết thúc",
        }
        widgets = {
            "thoigianbatdau": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "thoigianketthuc": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chuan_hoa_truong()
    # Quy tắc bắt đầu < kết thúc nằm ở KyDanhGia.clean() (dùng chung với Admin)


# ---------- UC-1.2: tiêu chí (formset nhập nhiều tiêu chí cho 1 kỳ) ----------
class TieuChiForm(FormMixin, forms.ModelForm):
    class Meta:
        model = TieuChi
        fields = ["tentieuchi", "mota"]
        widgets = {"mota": forms.TextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mockup đánh dấu * cho "Nội dung tiêu chí" => bắt buộc ở giao diện
        # (cột mota trong DB vẫn cho phép null theo đặc tả bảng).
        self.fields["mota"].required = True
        self.chuan_hoa_truong()


class TieuChiFormSetBase(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        ten_da_co = set()
        so_tieu_chi = 0
        for form in self.forms:
            cd = form.cleaned_data
            if not cd or cd.get("DELETE"):
                continue
            so_tieu_chi += 1
            ten = cd["tentieuchi"].strip().lower()
            if ten in ten_da_co:
                raise ValidationError("Tên tiêu chí bị trùng trong cùng kỳ đánh giá.")
            ten_da_co.add(ten)
        if so_tieu_chi == 0:
            raise ValidationError("Mỗi kỳ đánh giá phải có ít nhất một tiêu chí đánh giá.")


TieuChiFormSet = inlineformset_factory(
    KyDanhGia,
    TieuChi,
    form=TieuChiForm,
    formset=TieuChiFormSetBase,
    extra=0,  # dòng mới được thêm bằng khung "Thêm tiêu chí" (JS)
    can_delete=True,
)
