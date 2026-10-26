from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TrangThaiKhoa(models.TextChoices):
    CHUA_BAT_DAU = "Chưa bắt đầu", "Chưa bắt đầu"
    DANG_DIEN_RA = "Đang diễn ra", "Đang diễn ra"
    DA_KET_THUC = "Đã kết thúc", "Đã kết thúc"


class TienDoDaoTao(models.TextChoices):
    CHUA_HOAN_THANH = "Chưa hoàn thành", "Chưa hoàn thành"
    DA_HOAN_THANH = "Đã hoàn thành", "Đã hoàn thành"


class KetQuaDaoTao(models.TextChoices):
    CHO_DANH_GIA = "Chờ đánh giá", "Chờ đánh giá"
    DAT = "Đạt", "Đạt"
    CHUA_DAT = "Chưa đạt", "Chưa đạt"


class KhoaDaoTao(models.Model):
    """Bảng lưu trữ thông tin các khóa đào tạo nội bộ của Cake Crush."""

    makhoa = models.CharField(
        "Mã khóa đào tạo",
        max_length=20,
        primary_key=True,
        help_text="Mã định danh khóa học, ví dụ DT001, DT002...",
    )
    tenkhoa = models.CharField(
        "Tên khóa đào tạo",
        max_length=255,
        help_text="Tối đa 255 ký tự.",
    )
    noidung = models.TextField(
        "Nội dung đào tạo",
        help_text="Nội dung chi tiết của khóa đào tạo.",
    )
    ngaybatdau = models.DateField("Ngày bắt đầu")
    ngayketthuc = models.DateField("Ngày kết thúc")
    trangthai = models.CharField(
        "Trạng thái",
        max_length=20,
        choices=TrangThaiKhoa.choices,
        default=TrangThaiKhoa.CHUA_BAT_DAU,
    )
    ngaytao = models.DateTimeField(auto_now_add=True)
    ngaycapnhat = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "KHOADAOTAO"
        verbose_name = "Khóa đào tạo"
        verbose_name_plural = "Các khóa đào tạo"
        ordering = ["-ngaytao"]

    def __str__(self):
        return f"{self.makhoa} - {self.tenkhoa}"

    def clean(self):
        super().clean()
        if self.ngaybatdau and self.ngayketthuc:
            if self.ngayketthuc < self.ngaybatdau:
                raise ValidationError(
                    {"ngayketthuc": "Ngày kết thúc không trước ngày bắt đầu."}
                )

    def tinh_trang_thai_tu_dong(self, hom_nay=None):
        """Tính toán trạng thái của khóa học dựa trên ngày hiện tại."""
        if not hom_nay:
            hom_nay = timezone.localdate()
        if not self.ngaybatdau or not self.ngayketthuc:
            return self.trangthai
        if hom_nay < self.ngaybatdau:
            return TrangThaiKhoa.CHUA_BAT_DAU
        elif self.ngaybatdau <= hom_nay <= self.ngayketthuc:
            return TrangThaiKhoa.DANG_DIEN_RA
        else:
            return TrangThaiKhoa.DA_KET_THUC

    @property
    def so_nhan_vien(self):
        return self.danh_sach_phan_cong.count()


class PhanCongDaoTao(models.Model):
    """Bảng liên kết phân công nhân viên tham gia khóa đào tạo và kết quả."""

    nhanvien = models.ForeignKey(
        "nhan_su.NhanVien",
        on_delete=models.CASCADE,
        related_name="danh_sach_dao_tao",
        verbose_name="Nhân viên",
    )
    khoadaotao = models.ForeignKey(
        KhoaDaoTao,
        on_delete=models.CASCADE,
        related_name="danh_sach_phan_cong",
        verbose_name="Khóa đào tạo",
    )
    tiendo = models.CharField(
        "Tiến độ",
        max_length=20,
        choices=TienDoDaoTao.choices,
        default=TienDoDaoTao.CHUA_HOAN_THANH,
    )
    ngayhoanthanh = models.DateField(
        "Ngày hoàn thành",
        null=True,
        blank=True,
    )
    ketqua = models.CharField(
        "Kết quả",
        max_length=20,
        choices=KetQuaDaoTao.choices,
        default=KetQuaDaoTao.CHO_DANH_GIA,
    )
    ngaydanhgia = models.DateField(
        "Ngày đánh giá",
        null=True,
        blank=True,
    )
    nguoidanhgia = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="danh_gia_dao_tao_da_thuc_hien",
        verbose_name="Người đánh giá",
    )
    ngaytao = models.DateTimeField(auto_now_add=True)
    ngaycapnhat = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "PHANCONG_DAOTAO"
        verbose_name = "Phân công đào tạo"
        verbose_name_plural = "Danh sách phân công đào tạo"
        unique_together = ("nhanvien", "khoadaotao")
        ordering = ["-ngaytao"]

    def __str__(self):
        return f"{self.nhanvien.tennv} - {self.khoadaotao.tenkhoa}"
