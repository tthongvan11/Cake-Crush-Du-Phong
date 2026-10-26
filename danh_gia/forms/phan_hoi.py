"""UC-2.4: form phản hồi của nhân viên."""
from django import forms

from ..models import PhanHoi
from ._chung import FormMixin


class PhanHoiForm(FormMixin, forms.ModelForm):
    class Meta:
        model = PhanHoi
        fields = ["noidung"]
        labels = {"noidung": "Nội dung phản hồi"}
        widgets = {"noidung": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chuan_hoa_truong()
        self.fields["noidung"].error_messages["required"] = "Vui lòng nhập nội dung phản hồi"
