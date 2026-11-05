"""UC-2.1 / UC-2.2: form dùng chung cho khen thưởng và kỷ luật (khác nhau ở tham số loai)."""
from django import forms
from django.core.exceptions import ValidationError

from ..models import KhenThuongKyLuat
from ..utils import hom_nay
from ._chung import FormMixin


class GhiNhanForm(FormMixin, forms.ModelForm):
    # Danh sách hình thức hiển thị trong ô chọn (mockup dùng dropdown). Nhóm tự chỉnh.
    HINH_THUC = {
        "KHENTHUONG": ["Tuyên dương và giấy khen", "Thưởng tiền mặt", "Tăng lương", "Thăng chức"],
        "KYLUAT": ["Khiển trách", "Kéo dài thời hạn nâng lương", "Cách chức", "Sa thải"],
    }
    NHAN = {
        "KHENTHUONG": {"hinhthuc": "Hình thức khen thưởng", "lydo": "Lý do khen thưởng",
                       "ngay": "Ngày thực hiện"},
        "KYLUAT": {"hinhthuc": "Hình thức kỷ luật", "lydo": "Lý do vi phạm",
                   "ngay": "Ngày kỷ luật"},
    }

    hinhthuc = forms.ChoiceField(
        choices=[],
        error_messages={"invalid_choice": "Thông tin không hợp lệ, vui lòng chọn lại hình thức"},
    )

    class Meta:
        model = KhenThuongKyLuat
        fields = ["hinhthuc", "ngay", "lydo", "ghichu"]
        labels = {"ghichu": "Ghi chú"}
        widgets = {
            "ngay": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "lydo": forms.Textarea(attrs={"rows": 3}),
            "ghichu": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, loai, **kwargs):
        super().__init__(*args, **kwargs)
        self.loai = loai
        for ten, nhan in self.NHAN[loai].items():
            self.fields[ten].label = nhan
        self.fields["hinhthuc"].choices = [("", "— Chọn hình thức —")] + [
            (x, x) for x in self.HINH_THUC[loai]
        ]
        self.fields["hinhthuc"].widget.attrs["class"] = "form-select"
        self.chuan_hoa_truong()
        if not self.is_bound:
            self.initial.setdefault("ngay", hom_nay())

    def clean_ngay(self):
        ngay = self.cleaned_data["ngay"]
        if ngay > hom_nay():
            raise ValidationError("Thông tin không hợp lệ: ngày thực hiện không được ở tương lai")
        return ngay
