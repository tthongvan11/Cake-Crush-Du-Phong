from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase, Client
from django.urls import reverse

from nhan_su.models import NhanVien, PhongBan
from .models import KhoaDaoTao, PhanCongDaoTao, TrangThaiKhoa, TienDoDaoTao, KetQuaDaoTao
from .services import (
    tao_ma_khoa,
    lay_thong_ke_dao_tao,
    phan_cong_nhan_vien,
    xac_nhan_hoan_thanh,
    cap_nhat_ket_qua_dao_tao,
)

User = get_user_model()


def tao_nhan_vien_test(manv, user, suffix, phong):
    return NhanVien.objects.create(
        manv=manv,
        tennv=f"Nhân Viên {suffix}",
        id_taikhoan=user,
        maphong=phong,
        gioitinh="Nữ",
        sdt=f"098800{suffix:04d}",
        email=f"testnv{suffix}@cakecrush.com",
        cccd=f"079000{suffix:06d}",
        diachi="TP. Hồ Chí Minh",
        chucvu="Nhân viên làm bánh",
        ngayvaolam=date(2025, 1, 1),
        ngaysinh=date(2000, 1, 1),
        trangthai=True,
    )


class DaoTaoModelAndServiceTests(TestCase):
    def setUp(self):
        self.phong = PhongBan.objects.create(maphongban="PB01", tenphongban="Bếp bánh")
        self.user_nv = User.objects.create_user(username="nv_test", password="password123")
        self.nhan_vien = tao_nhan_vien_test("NV999", self.user_nv, 1, self.phong)

    def test_tao_ma_khoa_tu_dong(self):
        self.assertEqual(tao_ma_khoa(), "DT001")
        KhoaDaoTao.objects.create(
            makhoa="DT001",
            tenkhoa="Khóa 1",
            noidung="Nội dung",
            ngaybatdau=date.today(),
            ngayketthuc=date.today() + timedelta(days=5),
        )
        self.assertEqual(tao_ma_khoa(), "DT002")

    def test_validation_ngay_ket_thuc_truoc_ngay_bat_dau(self):
        khoa = KhoaDaoTao(
            makhoa="DT099",
            tenkhoa="Khóa lỗi ngày",
            noidung="Mô tả",
            ngaybatdau=date(2026, 10, 10),
            ngayketthuc=date(2026, 10, 5),
        )
        with self.assertRaises(ValidationError):
            khoa.full_clean()

    def test_phan_cong_va_xac_nhan_hoan_thanh(self):
        khoa = KhoaDaoTao.objects.create(
            makhoa="DT005",
            tenkhoa="Vệ sinh bếp",
            noidung="Nội dung",
            ngaybatdau=date.today(),
            ngayketthuc=date.today() + timedelta(days=3),
        )
        pc, created = phan_cong_nhan_vien(self.nhan_vien, khoa)
        self.assertTrue(created)
        self.assertEqual(pc.tiendo, TienDoDaoTao.CHUA_HOAN_THANH)
        self.assertEqual(pc.ketqua, KetQuaDaoTao.CHO_DANH_GIA)

        # Trùng lặp
        pc2, created2 = phan_cong_nhan_vien(self.nhan_vien, khoa)
        self.assertFalse(created2)

        # Nhân viên xác nhận hoàn thành
        xac_nhan_hoan_thanh(pc)
        pc.refresh_from_db()
        self.assertEqual(pc.tiendo, TienDoDaoTao.DA_HOAN_THANH)
        self.assertIsNotNone(pc.ngayhoanthanh)

        # Quản lý chấm kết quả
        cap_nhat_ket_qua_dao_tao(pc, KetQuaDaoTao.DAT)
        pc.refresh_from_db()
        self.assertEqual(pc.ketqua, KetQuaDaoTao.DAT)
        self.assertIsNotNone(pc.ngaydanhgia)


class DaoTaoViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.phong = PhongBan.objects.create(maphongban="PB02", tenphongban="Cửa hàng")

        # Quản lý
        self.user_ql = User.objects.create_user(username="ql_test", password="password123", is_staff=True)
        self.ql_nv = tao_nhan_vien_test("NV001", self.user_ql, 2, self.phong)

        # Nhân viên thường
        self.user_nv = User.objects.create_user(username="nv_test", password="password123", is_staff=False)
        self.nv_thuong = tao_nhan_vien_test("NV002", self.user_nv, 3, self.phong)

        # Khóa đào tạo mẫu
        self.khoa = KhoaDaoTao.objects.create(
            makhoa="DT001",
            tenkhoa="An toàn thực phẩm",
            noidung="Nội dung chi tiết",
            ngaybatdau=date.today(),
            ngayketthuc=date.today() + timedelta(days=7),
            trangthai=TrangThaiKhoa.DANG_DIEN_RA,
        )

    def test_quyen_truy_cap_quan_ly(self):
        # Chưa đăng nhập -> redirect login
        res = self.client.get(reverse("dao_tao:danh_sach_khoa"))
        self.assertEqual(res.status_code, 302)

        # Nhân viên thường đăng nhập -> PermissionDenied (403)
        self.client.login(username="nv_test", password="password123")
        res_nv = self.client.get(reverse("dao_tao:danh_sach_khoa"))
        self.assertEqual(res_nv.status_code, 403)

        # Quản lý đăng nhập -> 200 OK
        self.client.login(username="ql_test", password="password123")
        res_ql = self.client.get(reverse("dao_tao:danh_sach_khoa"))
        self.assertEqual(res_ql.status_code, 200)

    def test_quan_ly_tao_khoa_dao_tao(self):
        self.client.login(username="ql_test", password="password123")
        res_get = self.client.get(reverse("dao_tao:tao_khoa"))
        self.assertEqual(res_get.status_code, 200)

        post_data = {
            "makhoa": "DT099",
            "tenkhoa": "Khóa đào tạo mới",
            "noidung": "Mô tả khóa",
            "ngaybatdau": date.today().strftime("%Y-%m-%d"),
            "ngayketthuc": (date.today() + timedelta(days=10)).strftime("%Y-%m-%d"),
            "trangthai": TrangThaiKhoa.DANG_DIEN_RA,
        }
        res_post = self.client.post(reverse("dao_tao:tao_khoa"), data=post_data)
        self.assertEqual(res_post.status_code, 302)
        self.assertTrue(KhoaDaoTao.objects.filter(makhoa="DT099").exists())

    def test_quan_ly_cap_nhat_noi_dung(self):
        self.client.login(username="ql_test", password="password123")
        res = self.client.post(
            reverse("dao_tao:cap_nhat_noi_dung_khoa", args=[self.khoa.makhoa]),
            data={"noidung": "Nội dung đã được cập nhật mới"},
        )
        self.assertEqual(res.status_code, 302)
        self.khoa.refresh_from_db()
        self.assertEqual(self.khoa.noidung, "Nội dung đã được cập nhật mới")

    def test_quan_ly_phan_cong_nhan_vien(self):
        self.client.login(username="ql_test", password="password123")
        res = self.client.post(
            reverse("dao_tao:phan_cong_dao_tao"),
            data={"nhanvien": self.nv_thuong.manv, "khoadaotao": self.khoa.makhoa},
        )
        self.assertEqual(res.status_code, 302)
        self.assertTrue(
            PhanCongDaoTao.objects.filter(nhanvien=self.nv_thuong, khoadaotao=self.khoa).exists()
        )

    def test_nhan_vien_xem_va_xac_nhan_hoan_thanh(self):
        # Phân công
        pc, _ = phan_cong_nhan_vien(self.nv_thuong, self.khoa)

        self.client.login(username="nv_test", password="password123")

        # Màn hình 8: Chương trình của tôi
        res8 = self.client.get(reverse("dao_tao:chuong_trinh_cua_toi"))
        self.assertEqual(res8.status_code, 200)

        # Màn hình 9: Xem nội dung & POST xác nhận
        res9 = self.client.get(f"{reverse('dao_tao:xem_noi_dung_dao_tao')}?khoa={self.khoa.makhoa}")
        self.assertEqual(res9.status_code, 200)

        res_confirm = self.client.post(
            reverse("dao_tao:xem_noi_dung_dao_tao"),
            data={"khoa": self.khoa.makhoa},
        )
        self.assertEqual(res_confirm.status_code, 302)
        pc.refresh_from_db()
        self.assertEqual(pc.tiendo, TienDoDaoTao.DA_HOAN_THANH)

        # Màn hình 10: Xem kết quả của tôi
        res10 = self.client.get(f"{reverse('dao_tao:ket_qua_dao_tao_cua_toi')}?khoa={self.khoa.makhoa}")
        self.assertEqual(res10.status_code, 200)
