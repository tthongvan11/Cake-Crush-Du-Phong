from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg

from .utils import sinh_ma


class TuSinhMa(models.Model):
    """Lớp cha trừu tượng: tự sinh khóa chính khi lưu lần đầu (không cho sửa)."""

    TRUONG_MA = None
    TIEN_TO = ""
    DO_DAI = 5

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not getattr(self, self.TRUONG_MA):
            setattr(
                self,
                self.TRUONG_MA,
                sinh_ma(type(self), self.TRUONG_MA, self.TIEN_TO, self.DO_DAI),
            )
        super().save(*args, **kwargs)


class KyDanhGia(TuSinhMa):
    TRUONG_MA, TIEN_TO, DO_DAI = "maky", "KY", 4

    maky = models.CharField(max_length=10, primary_key=True, editable=False)
    tenky = models.CharField(max_length=100)
    thoigianbatdau = models.DateField()
    thoigianketthuc = models.DateField()

    class Meta:
        ordering = ["-thoigianbatdau"]
        # Quyền dùng cho phân quyền (cấp trong Admin > Groups)
        permissions = [
            ("quan_ly_danh_gia", "Quản lý kỳ, tiêu chí và đánh giá nhân viên"),
            ("ghi_nhan_khen_thuong", "Ghi nhận khen thưởng"),
            ("quan_ly_ky_luat", "Quản lý kỷ luật"),
        ]

    def clean(self):
        super().clean()
        if (
            self.thoigianbatdau
            and self.thoigianketthuc
            and self.thoigianketthuc <= self.thoigianbatdau
        ):
            raise ValidationError(
                {"thoigianketthuc": "Thời gian kết thúc phải sau thời gian bắt đầu"}
            )

    def __str__(self):
        return self.tenky


class TieuChi(TuSinhMa):
    TRUONG_MA, TIEN_TO, DO_DAI = "matieuchi", "TC", 5

    matieuchi = models.CharField(max_length=10, primary_key=True, editable=False)
    maky = models.ForeignKey(KyDanhGia, on_delete=models.PROTECT)
    tentieuchi = models.CharField(max_length=100)
    mota = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["matieuchi"]

    def __str__(self):
        return self.tentieuchi


class DanhGia(TuSinhMa):
    TRUONG_MA, TIEN_TO, DO_DAI = "madanhgia", "DG", 5

    XEP_LOAI_CHOICES = [
        ("XUATSAC", "Xuất sắc"),
        ("TOT", "Tốt"),
        ("KHA", "Khá"),
        ("DAT", "Đạt"),
        ("CHUADAT", "Chưa đạt"),
    ]

    madanhgia = models.CharField(max_length=10, primary_key=True, editable=False)
    manv = models.ForeignKey("nhan_su.NhanVien", on_delete=models.PROTECT)
    maky = models.ForeignKey(KyDanhGia, on_delete=models.PROTECT)
    ngaydanhgia = models.DateField()
    xeploai = models.CharField(max_length=20, choices=XEP_LOAI_CHOICES)
    nhanxet = models.TextField(null=True, blank=True)

    class Meta:
        # Mỗi nhân viên chỉ có 1 bản đánh giá trong 1 kỳ
        constraints = [
            models.UniqueConstraint(fields=["manv", "maky"], name="unique_manv_maky")
        ]
        ordering = ["-ngaydanhgia", "-madanhgia"]

    @property
    def diem_trung_binh(self):
        """Điểm tổng hợp = trung bình điểm các tiêu chí (tính khi cần, không lưu)."""
        tb = self.chitietdanhgia_set.aggregate(tb=Avg("diem"))["tb"]
        return round(tb, 2) if tb is not None else None

    def __str__(self):
        return f"{self.madanhgia} - {self.manv_id} - {self.maky_id}"


class ChiTietDanhGia(TuSinhMa):
    TRUONG_MA, TIEN_TO, DO_DAI = "machitietdg", "CT", 6

    machitietdg = models.CharField(max_length=10, primary_key=True, editable=False)
    madanhgia = models.ForeignKey(DanhGia, on_delete=models.PROTECT)
    matieuchi = models.ForeignKey(TieuChi, on_delete=models.PROTECT)
    diem = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    nhanxet = models.TextField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["madanhgia", "matieuchi"], name="unique_madanhgia_matieuchi"
            )
        ]
        ordering = ["matieuchi"]

    def __str__(self):
        return f"{self.madanhgia_id} - {self.matieuchi_id}: {self.diem}"


class KhenThuongKyLuat(TuSinhMa):
    TRUONG_MA, TIEN_TO, DO_DAI = "maktkl", "KT", 5

    LOAI_CHOICES = [("KHENTHUONG", "Khen thưởng"), ("KYLUAT", "Kỷ luật")]

    maktkl = models.CharField(max_length=10, primary_key=True, editable=False)
    madanhgia = models.ForeignKey(DanhGia, on_delete=models.PROTECT)
    loaiphieu = models.CharField(max_length=20, choices=LOAI_CHOICES)
    hinhthuc = models.CharField(max_length=100)
    ngay = models.DateField()
    lydo = models.TextField()
    ghichu = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-ngay", "-maktkl"]

    def __str__(self):
        return f"{self.get_loaiphieu_display()} - {self.hinhthuc}"


class PhanHoi(TuSinhMa):
    TRUONG_MA, TIEN_TO, DO_DAI = "maph", "PH", 5

    maph = models.CharField(max_length=10, primary_key=True, editable=False)
    manv = models.ForeignKey("nhan_su.NhanVien", on_delete=models.PROTECT)
    madanhgia = models.ForeignKey(DanhGia, on_delete=models.PROTECT)
    noidung = models.TextField()
    ngayphanhoi = models.DateField()

    class Meta:
        ordering = ["-ngayphanhoi", "-maph"]

    def __str__(self):
        return f"Phản hồi {self.maph}"
