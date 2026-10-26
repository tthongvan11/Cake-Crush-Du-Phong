"""Thành phần dùng chung cho mọi form của app danh_gia."""

THIEU_THONG_TIN = "Yêu cầu nhập đầy đủ thông tin"


class FormMixin:
    """Gắn class Bootstrap + thông báo 'thiếu thông tin' thống nhất cho mọi field."""

    def chuan_hoa_truong(self):
        for f in self.fields.values():
            f.error_messages["required"] = THIEU_THONG_TIN
            f.widget.attrs.setdefault("class", "form-control")
