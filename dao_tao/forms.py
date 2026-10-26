from django import forms
from django.core.exceptions import ValidationError
from nhan_su.models import NhanVien
from .models import KhoaDaoTao, PhanCongDaoTao, TrangThaiKhoa, KetQuaDaoTao


class KhoaDaoTaoForm(forms.ModelForm):
    """Form tạo mới hoặc chỉnh sửa khóa đào tạo."""

    makhoa = forms.CharField(
        label="Mã khóa đào tạo",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "dt-input",
                "placeholder": "Tạo mã khóa đào tạo",
            }
        ),
    )
    tenkhoa = forms.CharField(
        label="Tên khóa đào tạo",
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "dt-input",
                "placeholder": "Nhập tên khóa đào tạo...",
            }
        ),
        help_text="Tối đa 255 ký tự.",
    )
    noidung = forms.CharField(
        label="Nội dung đào tạo",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "dt-textarea",
                "rows": 4,
                "placeholder": "Nhập nội dung đào tạo...",
            }
        ),
    )
    ngaybatdau = forms.DateField(
        label="Ngày bắt đầu",
        required=True,
        widget=forms.DateInput(
            attrs={
                "class": "dt-input",
                "type": "date",
                "placeholder": "dd/mm/yyyy",
            }
        ),
    )
    ngayketthuc = forms.DateField(
        label="Ngày kết thúc",
        required=True,
        widget=forms.DateInput(
            attrs={
                "class": "dt-input",
                "type": "date",
                "placeholder": "dd/mm/yyyy",
            }
        ),
        help_text="Ngày kết thúc không trước ngày bắt đầu.",
    )
    trangthai = forms.ChoiceField(
        label="Trạng thái",
        choices=[("", "Chọn trạng thái")] + list(TrangThaiKhoa.choices),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "dt-select",
            }
        ),
    )

    class Meta:
        model = KhoaDaoTao
        fields = ["makhoa", "tenkhoa", "noidung", "ngaybatdau", "ngayketthuc", "trangthai"]

    def clean(self):
        cleaned_data = super().clean()
        ngaybatdau = cleaned_data.get("ngaybatdau")
        ngayketthuc = cleaned_data.get("ngayketthuc")

        if ngaybatdau and ngayketthuc and ngayketthuc < ngaybatdau:
            self.add_error("ngayketthuc", "Ngày kết thúc không trước ngày bắt đầu.")

        return cleaned_data


class CapNhatNoiDungKhoaForm(forms.ModelForm):
    """Form chỉ cho phép cập nhật nội dung khóa đào tạo."""

    noidung = forms.CharField(
        label="Nội dung đào tạo",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "dt-textarea",
                "rows": 5,
                "placeholder": "Nhập nội dung đào tạo...",
            }
        ),
    )

    class Meta:
        model = KhoaDaoTao
        fields = ["noidung"]


class PhanCongDaoTaoForm(forms.ModelForm):
    """Form phân công nhân viên vào khóa đào tạo."""

    nhanvien = forms.ModelChoiceField(
        queryset=NhanVien.objects.filter(trangthai=True).order_by("tennv"),
        label="Nhân viên",
        empty_label="Chọn nhân viên",
        widget=forms.Select(attrs={"class": "dt-select", "id": "id_nhanvien"}),
    )
    khoadaotao = forms.ModelChoiceField(
        queryset=KhoaDaoTao.objects.all().order_by("-ngaybatdau"),
        label="Khóa đào tạo",
        empty_label="Chọn khóa đào tạo",
        widget=forms.Select(attrs={"class": "dt-select", "id": "id_khoadaotao"}),
    )

    class Meta:
        model = PhanCongDaoTao
        fields = ["nhanvien", "khoadaotao"]

    def clean(self):
        cleaned_data = super().clean()
        nhanvien = cleaned_data.get("nhanvien")
        khoadaotao = cleaned_data.get("khoadaotao")

        if nhanvien and khoadaotao:
            if PhanCongDaoTao.objects.filter(nhanvien=nhanvien, khoadaotao=khoadaotao).exists():
                raise ValidationError("Nhân viên này đã được phân công vào khóa đào tạo đã chọn.")

        return cleaned_data


class CapNhatKetQuaForm(forms.Form):
    """Form ghi nhận kết quả đánh giá thực hành của Quản lý."""

    ketqua = forms.ChoiceField(
        label="Kết quả",
        choices=[
            ("", "Chọn Đạt hoặc Chưa đạt"),
            (KetQuaDaoTao.DAT, "Đạt"),
            (KetQuaDaoTao.CHUA_DAT, "Chưa đạt"),
        ],
        widget=forms.Select(attrs={"class": "dt-select"}),
    )
