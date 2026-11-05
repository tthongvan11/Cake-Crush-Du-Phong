"""UC-1.3: form chấm điểm động theo số tiêu chí của kỳ."""
from django import forms

from ._chung import FormMixin


class DanhGiaForm(FormMixin, forms.Form):
    nhanxet = forms.CharField(
        label="Nhận xét hiệu suất và năng lực",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, *args, tieu_chi_list, **kwargs):
        super().__init__(*args, **kwargs)
        self.tieu_chi_list = list(tieu_chi_list)
        for tc in self.tieu_chi_list:
            self.fields[f"diem_{tc.matieuchi}"] = forms.IntegerField(
                label=tc.tentieuchi,
                min_value=0,
                max_value=10,
                error_messages={
                    "required": f"Chưa nhập điểm cho tiêu chí “{tc.tentieuchi}”",
                    "invalid": "Điểm đánh giá không hợp lệ, vui lòng nhập số nguyên từ 0 đến 10",
                    "min_value": "Điểm đánh giá không hợp lệ, điểm phải từ 0 đến 10",
                    "max_value": "Điểm đánh giá không hợp lệ, điểm phải từ 0 đến 10",
                },
                widget=forms.NumberInput(
                    attrs={"min": 0, "max": 10, "step": 1, "class": "form-control o-diem",
                           "placeholder": "Chưa có điểm"}
                ),
            )
        self.chuan_hoa_truong()
        for tc in self.tieu_chi_list:  # giữ thông báo riêng của ô điểm
            self.fields[f"diem_{tc.matieuchi}"].error_messages["required"] = (
                f"Chưa nhập điểm cho tiêu chí “{tc.tentieuchi}”"
            )

    def cac_dong(self):
        """Dùng trong template: (tiêu chí, ô điểm)."""
        return [(tc, self[f"diem_{tc.matieuchi}"]) for tc in self.tieu_chi_list]

    def du_lieu_phien(self):
        """Dữ liệu (JSON an toàn) giữ tạm trong session giữa bước nhập và xác nhận."""
        cd = self.cleaned_data
        return {
            "diem": {tc.matieuchi: cd[f"diem_{tc.matieuchi}"] for tc in self.tieu_chi_list},
            "nhanxet": cd["nhanxet"],
        }

    @staticmethod
    def initial_tu_phien(nhap):
        init = {"nhanxet": nhap.get("nhanxet", "")}
        for ma, d in nhap.get("diem", {}).items():
            init[f"diem_{ma}"] = d
        return init
