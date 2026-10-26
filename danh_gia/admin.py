from django.contrib import admin

from .models import ChiTietDanhGia, DanhGia, KhenThuongKyLuat, KyDanhGia, PhanHoi, TieuChi


@admin.register(KyDanhGia)
class KyDanhGiaAdmin(admin.ModelAdmin):
    list_display = ("maky", "tenky", "thoigianbatdau", "thoigianketthuc")
    readonly_fields = ("maky",)


@admin.register(TieuChi)
class TieuChiAdmin(admin.ModelAdmin):
    list_display = ("matieuchi", "tentieuchi", "maky")
    list_filter = ("maky",)
    readonly_fields = ("matieuchi",)


class ChiTietInline(admin.TabularInline):
    model = ChiTietDanhGia
    extra = 0
    readonly_fields = ("machitietdg",)


@admin.register(DanhGia)
class DanhGiaAdmin(admin.ModelAdmin):
    list_display = ("madanhgia", "manv", "maky", "ngaydanhgia", "xeploai")
    list_filter = ("maky", "xeploai")
    readonly_fields = ("madanhgia",)
    inlines = [ChiTietInline]


@admin.register(KhenThuongKyLuat)
class KhenThuongKyLuatAdmin(admin.ModelAdmin):
    list_display = ("maktkl", "loaiphieu", "madanhgia", "hinhthuc", "ngay")
    list_filter = ("loaiphieu",)
    readonly_fields = ("maktkl",)


@admin.register(PhanHoi)
class PhanHoiAdmin(admin.ModelAdmin):
    list_display = ("maph", "manv", "madanhgia", "ngayphanhoi")
    readonly_fields = ("maph",)
