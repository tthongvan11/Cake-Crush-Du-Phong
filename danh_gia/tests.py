from datetime import date

from django.test import SimpleTestCase, TestCase

from .forms import KyDanhGiaForm
from .models import KyDanhGia
from .services import tinh_diem_trung_binh, xep_loai_tu_diem


class XepLoaiTest(SimpleTestCase):
    def test_nguong_xep_loai(self):
        self.assertEqual(xep_loai_tu_diem(10), "XUATSAC")
        self.assertEqual(xep_loai_tu_diem(9), "XUATSAC")
        self.assertEqual(xep_loai_tu_diem(8.5), "TOT")
        self.assertEqual(xep_loai_tu_diem(7), "KHA")
        self.assertEqual(xep_loai_tu_diem(5), "DAT")
        self.assertEqual(xep_loai_tu_diem(4.99), "CHUADAT")

    def test_diem_trung_binh(self):
        self.assertEqual(tinh_diem_trung_binh([8, 9, 10]), 9.0)


class KyDanhGiaTest(TestCase):
    def test_tu_sinh_ma(self):
        a = KyDanhGia.objects.create(
            tenky="Q1", thoigianbatdau=date(2026, 1, 1), thoigianketthuc=date(2026, 3, 31)
        )
        b = KyDanhGia.objects.create(
            tenky="Q2", thoigianbatdau=date(2026, 4, 1), thoigianketthuc=date(2026, 6, 30)
        )
        self.assertEqual((a.maky, b.maky), ("KY0001", "KY0002"))

    def test_ket_thuc_phai_sau_bat_dau(self):
        form = KyDanhGiaForm(
            {"tenky": "X", "thoigianbatdau": "2026-04-01", "thoigianketthuc": "2026-03-01"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Thời gian kết thúc phải sau thời gian bắt đầu", str(form.errors))

    def test_thieu_thong_tin(self):
        form = KyDanhGiaForm({})
        self.assertFalse(form.is_valid())
        self.assertIn("Yêu cầu nhập đầy đủ thông tin", str(form.errors))
