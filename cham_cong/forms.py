from django import forms  # Lớp biểu mẫu của Django.

from .models import DonNghiPhep, LoaiPhep  # Model dùng cho biểu mẫu.

BAT_BUOC = "Vui lòng điền đầy đủ thông tin trước khi gửi."  # Thông báo chung khi để trống trường bắt buộc.


class DonNghiPhepForm(forms.ModelForm):  # Biểu mẫu tạo đơn xin nghỉ phép (UC-NP-3.01).
    class Meta:  # Cấu hình biểu mẫu theo model.
        model = DonNghiPhep  # Lưu vào bảng DONNGHIPHEP.
        fields = ["maloaiphep", "ngaybatdau", "ngayketthuc", "lydo"]  # Chỉ các trường nhân viên được nhập.
        widgets = {  # Kiểu ô nhập trên trình duyệt.
            "ngaybatdau": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),  # Ô chọn ngày bắt đầu.
            "ngayketthuc": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),  # Ô chọn ngày kết thúc.
            "lydo": forms.Textarea(attrs={"rows": 4, "placeholder": "Nhập lý do cụ thể"}),  # Ô lý do nhiều dòng.
        }  # Kết thúc widgets.
        labels = {  # Nhãn hiển thị giống mockup.
            "maloaiphep": "Loại phép", "ngaybatdau": "Ngày bắt đầu",  # Nhãn loại phép và ngày bắt đầu.
            "ngayketthuc": "Ngày kết thúc", "lydo": "Lý do xin nghỉ",  # Nhãn ngày kết thúc và lý do.
        }  # Kết thúc nhãn.
        error_messages = {truong: {"required": BAT_BUOC} for truong in fields}  # Cùng một thông báo khi bỏ trống.

    def __init__(self, *args, **kwargs):  # Tùy chỉnh khi khởi tạo biểu mẫu.
        super().__init__(*args, **kwargs)  # Gọi khởi tạo của lớp cha.
        self.fields["maloaiphep"].queryset = LoaiPhep.objects.all()  # Danh sách loại phép.
        self.fields["maloaiphep"].empty_label = "Chọn loại phép"  # Dòng gợi ý đầu danh sách.

    def clean_lydo(self):  # Không chấp nhận lý do chỉ có khoảng trắng.
        ly_do = (self.cleaned_data.get("lydo") or "").strip()  # Bỏ khoảng trắng hai đầu.
        if not ly_do:  # Lý do rỗng.
            raise forms.ValidationError(BAT_BUOC)  # Báo cần điền đầy đủ.
        return ly_do  # Trả lý do đã làm sạch.


class TuChoiForm(forms.Form):  # Biểu mẫu nhập lý do từ chối đơn.
    phanhoi = forms.CharField(  # Ô nhập phản hồi.
        label="Lý do từ chối", required=False,  # Kiểm tra bắt buộc ở service để dùng đúng câu thông báo.
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Nhập lý do phản hồi cho nhân viên"}),  # Ô nhiều dòng.
    )  # Kết thúc khai báo trường.
