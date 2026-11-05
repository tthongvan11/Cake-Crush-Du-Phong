from datetime import date, timedelta  # Dùng mốc ngày cố định để kiểm tra nghiệp vụ.
from decimal import Decimal  # Tránh sai số khi kiểm tra tiền.
from importlib import import_module  # Nạp hàm đồng bộ dữ liệu của migration.
from types import SimpleNamespace  # Chỉ cần connection của schema_editor khi thử migration dữ liệu.
from unittest.mock import patch  # Mô phỏng lỗi để kiểm tra hoàn tác giao dịch.
from urllib.parse import urlencode  # Tạo liên kết chỉnh sửa có ghi nhớ nguồn mở form.

from django.apps import apps  # Registry model dùng để kiểm tra migration.
from django.contrib.auth import get_user_model  # Model tài khoản của dự án.
from django.core.exceptions import ValidationError  # Lỗi nghiệp vụ cần được chặn.
from django.db import connection  # Database kiểm thử riêng, không dùng dữ liệu thật.
from django.db.models.query import QuerySet  # Mô phỏng lỗi khóa tài khoản.
from django.test import Client, TestCase  # Kiểm tra service và request thực.
from django.urls import reverse  # Không ghi cứng URL trong kiểm thử.

from . import services  # Các nghiệp vụ cần bảo vệ khỏi lỗi lặp lại.
from .forms import GiaHanHopDongForm, HopDongForm, NhanVienForm, VoHieuHoaNhanVienForm  # Form thật.
from .models import HopDong, NhanVien, PhongBan  # Model thật trên database kiểm thử.


TODAY = date(2026, 10, 18)  # Mọi ca kiểm thử dùng cùng một ngày.


class HoSoHopDongTests(TestCase):  # Mỗi ca được hoàn tác trên database kiểm thử.
    @classmethod
    def setUpTestData(cls):  # Tạo dữ liệu một lần cho cả nhóm kiểm thử.
        User = get_user_model()  # Lấy model tài khoản hiện hành.
        cls.manager = User.objects.create_user("quanly_test", password="Old!CakeCrush936", is_staff=True)
        cls.user = User.objects.create_user("nhanvien_test", password="Old!CakeCrush936")
        cls.other = User.objects.create_user("khac_test", password="Old!CakeCrush936")
        cls.unlinked = User.objects.create_user("chua_gan_test", password="Old!CakeCrush936")
        cls.pb = PhongBan.objects.create(maphongban="PB001", tenphongban="Bán hàng")
        cls.nv = cls.profile("NV001", cls.user, 1)  # Hồ sơ của nhân viên.
        cls.nv_other = cls.profile("NV002", cls.other, 2)  # Dùng thử truy cập dữ liệu người khác.
        cls.nv_manager = cls.profile("NV003", cls.manager, 3)  # Quản lý cũng có hồ sơ cá nhân.
        cls.hd = cls.contract("HD-NV-001", cls.nv, TODAY + timedelta(days=20))
        cls.hd_other = cls.contract("HD-NV-002", cls.nv_other, TODAY + timedelta(days=40))
        cls.hd_manager = cls.contract("HD-QL-001", cls.nv_manager, None)

    @classmethod
    def profile(cls, code, user, suffix):  # Tạo hồ sơ có các trường duy nhất hợp lệ.
        return NhanVien.objects.create(
            manv=code, id_taikhoan=user, maphong=cls.pb, tennv=f"Nhân viên {suffix}",
            gioitinh="Nữ", sdt=f"090000{suffix:04d}", email=f"nv{suffix}@example.com",
            cccd=f"040000{suffix:06d}", diachi="Đà Nẵng", chucvu="Nhân viên bán hàng",
            ngayvaolam=TODAY - timedelta(days=700),
        )

    @classmethod
    def contract(cls, code, nv, end, start=None):  # Cho phép thử cả hữu hạn, vô hạn và tương lai.
        return HopDong.objects.create(
            mahd=code, manv=nv,
            loaihd=HopDong.Loai.XAC_DINH_1_NAM if end else HopDong.Loai.KHONG_XAC_DINH,
            ngayky=TODAY - timedelta(days=600), ngaybatdau=start or TODAY - timedelta(days=500),
            ngayhethan=end, luongcoban=Decimal("8500000.00"),
            trangthai=HopDong.TrangThai.DANG_HIEU_LUC,
        )

    def setUp(self):  # Không phụ thuộc ngày chạy test trong tương lai.
        self.clock = patch("nhan_su.services.timezone.localdate", return_value=TODAY)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def offboard(self, nv=None, day=None):  # Gọi đúng luồng form và service đang dùng trên web.
        nv = nv or self.nv
        form = VoHieuHoaNhanVienForm(
            {"ngaynghiviec": day or TODAY, "lydonghiviec": "Nghỉ theo nguyện vọng."}, nhan_vien=nv,
        )
        return services.vo_hieu_hoa_nhan_vien(form=form, nguoi_thuc_hien=self.manager)

    def test_offboarding_ends_current_future_and_indefinite_contracts(self):
        future = self.contract("HD-NV-003", self.nv, TODAY + timedelta(days=400), TODAY + timedelta(days=5))
        indefinite = self.contract("HD-NV-004", self.nv, None)
        old = self.contract("HD-NV-005", self.nv, TODAY - timedelta(days=100))
        original_end = self.hd.ngayhethan  # Nghỉ việc không được ghi đè thời hạn đã ký.
        self.offboard()
        for hd in (self.hd, future, indefinite):
            hd.refresh_from_db()
            self.assertEqual(hd.trangthai, HopDong.TrangThai.CHAM_DUT)
            self.assertEqual(services.tinh_trang_thai(hd), HopDong.TrangThai.CHAM_DUT)
        old.refresh_from_db()
        self.assertEqual(old.trangthai, HopDong.TrangThai.HET_HAN)
        self.assertEqual(self.hd.ngayhethan, original_end)
        self.assertEqual(HopDong.objects.filter(manv=self.nv).count(), 4)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_backdated_departure_ends_contract_that_expired_after_departure(self):
        hd = self.contract("HD-NV-003", self.nv, TODAY - timedelta(days=5))
        self.offboard(day=TODAY - timedelta(days=10))
        hd.refresh_from_db()
        self.assertEqual(hd.trangthai, HopDong.TrangThai.CHAM_DUT)

    def test_offboarding_rolls_back_profile_contracts_and_account_together(self):
        real_update = QuerySet.update  # Chỉ gây lỗi ở bước khóa tài khoản.
        def fail_account(query, **kwargs):
            if query.model is get_user_model():
                raise RuntimeError("Lỗi khóa tài khoản giả lập")
            return real_update(query, **kwargs)
        with patch.object(QuerySet, "update", fail_account), self.assertRaises(RuntimeError):
            self.offboard()
        self.nv.refresh_from_db()
        self.hd.refresh_from_db()
        self.user.refresh_from_db()
        self.assertTrue(self.nv.trangthai)
        self.assertEqual(self.hd.trangthai, HopDong.TrangThai.DANG_HIEU_LUC)
        self.assertTrue(self.user.is_active)

    def test_manager_cannot_offboard_self(self):
        with self.assertRaises(ValidationError):
            self.offboard(self.nv_manager)

    def test_employee_cannot_offboard_someone(self):
        form = VoHieuHoaNhanVienForm(
            {"ngaynghiviec": TODAY, "lydonghiviec": "Thử quyền"}, nhan_vien=self.nv_other,
        )
        from django.core.exceptions import PermissionDenied  # Quyền phải được chặn cả tại service.
        with self.assertRaises(PermissionDenied):
            services.vo_hieu_hoa_nhan_vien(form=form, nguoi_thuc_hien=self.user)

    def test_cannot_offboard_twice(self):
        self.offboard()
        with self.assertRaises(ValidationError):
            self.offboard()

    def test_expired_history_remains_expired_after_departure(self):
        old = self.contract("HD-NV-003", self.nv, TODAY - timedelta(days=100))
        self.offboard(day=TODAY - timedelta(days=10))
        old.refresh_from_db()
        self.assertEqual(services.tinh_trang_thai(old), HopDong.TrangThai.HET_HAN)

    def test_legacy_inactive_profile_display_and_filter_agree(self):
        self.nv.trangthai = False
        self.nv.ngaynghiviec = TODAY - timedelta(days=10)
        self.nv.save()
        self.hd.refresh_from_db()
        self.assertEqual(services.tinh_trang_thai(self.hd), HopDong.TrangThai.CHAM_DUT)
        conditions = services.dieu_kien_trang_thai()
        self.assertTrue(HopDong.objects.filter(conditions["CHAMDUT"], pk=self.hd.pk).exists())
        self.assertFalse(HopDong.objects.filter(conditions["DANGHIEULUC"], pk=self.hd.pk).exists())
        self.client.force_login(self.manager)
        ended = self.client.get(reverse("nhan_su:danh_sach_hop_dong"), {"trang_thai": "CHAMDUT"})
        active = self.client.get(reverse("nhan_su:danh_sach_hop_dong"), {"trang_thai": "DANGHIEULUC"})
        self.assertContains(ended, self.hd.pk)
        self.assertNotContains(active, self.hd.pk)

    def test_data_migration_repairs_legacy_records_and_is_idempotent(self):
        self.nv.trangthai = False
        self.nv.ngaynghiviec = TODAY - timedelta(days=10)
        self.nv.save()
        old = self.contract("HD-NV-003", self.nv, TODAY - timedelta(days=100))
        migration = import_module("nhan_su.migrations.0002_hop_dong_het_hieu_luc")
        editor = SimpleNamespace(connection=connection)  # Không mở schema editor trong giao dịch của TestCase.
        migration.dong_bo_hop_dong_da_nghi(apps, editor)
        migration.dong_bo_hop_dong_da_nghi(apps, editor)  # Chạy lại không đổi kết quả.
        self.hd.refresh_from_db()
        old.refresh_from_db()
        self.assertEqual(self.hd.trangthai, HopDong.TrangThai.CHAM_DUT)
        self.assertEqual(old.trangthai, HopDong.TrangThai.HET_HAN)
        self.hd_other.refresh_from_db()
        self.assertEqual(self.hd_other.trangthai, HopDong.TrangThai.DANG_HIEU_LUC)

    def test_cannot_edit_or_renew_after_departure_even_with_direct_post(self):
        self.offboard()
        for Form, data in (
            (GiaHanHopDongForm, {"ngaygiahan": TODAY, "ngayhethan": TODAY + timedelta(days=400), "luongcoban": "9000000"}),
            (HopDongForm, {"manv": self.nv.pk, "loaihd": self.hd.loaihd, "ngayky": self.hd.ngayky,
                          "ngaybatdau": self.hd.ngaybatdau, "ngayhethan": self.hd.ngayhethan, "luongcoban": "9000000"}),
        ):
            self.hd.refresh_from_db()
            with self.subTest(form=Form.__name__), self.assertRaises(ValidationError):
                services.luu_hop_dong(form=Form(data, instance=self.hd), nguoi_thuc_hien=self.manager)
        self.client.force_login(self.manager)
        response = self.client.get(reverse("nhan_su:chi_tiet_hop_dong", args=[self.hd.pk]))
        self.assertNotContains(response, reverse("nhan_su:gia_han_hop_dong", args=[self.hd.pk]))
        self.assertContains(response, "Hết hiệu lực")

    def test_own_pages_are_distinct_and_read_only_for_both_roles(self):
        for user, own in ((self.user, self.hd), (self.manager, self.hd_manager)):
            self.client.force_login(user)
            profile = self.client.get(reverse("nhan_su:ho_so_cua_toi"))
            contracts = self.client.get(reverse("nhan_su:hop_dong_cua_toi"))
            self.assertTemplateUsed(profile, "nhan_su/ho_so_cua_toi.html")
            self.assertTemplateUsed(contracts, "nhan_su/hop_dong_cua_toi.html")
            self.assertContains(profile, "Thông tin cá nhân")
            self.assertContains(contracts, own.pk)
            self.assertNotContains(contracts, self.hd_other.pk)
            self.assertNotContains(contracts, reverse("nhan_su:sua_hop_dong", args=[own.pk]))

    def test_contract_ownership_is_checked_in_url(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("nhan_su:chi_tiet_hop_dong_cua_toi", args=[self.hd_other.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("nhan_su:danh_sach_nhan_vien")).status_code, 403)

    def test_unlinked_account_has_helpful_empty_pages(self):
        self.client.force_login(self.unlinked)
        self.assertContains(self.client.get(reverse("nhan_su:ho_so_cua_toi")), "Chưa có hồ sơ liên kết")
        self.assertContains(self.client.get(reverse("nhan_su:hop_dong_cua_toi")), "Chưa có hợp đồng")

    def test_anonymous_is_redirected_to_existing_login(self):
        for route in ("ho_so_cua_toi", "hop_dong_cua_toi", "doi_mat_khau"):
            self.assertRedirects(self.client.get(reverse(f"nhan_su:{route}")),
                                 reverse("login") + "?next=" + reverse(f"nhan_su:{route}"))

    def test_account_link_form_rejects_occupied_account(self):
        form = NhanVienForm(instance=self.nv)
        self.assertIn(self.user, form.fields["id_taikhoan"].queryset)
        self.assertIn(self.unlinked, form.fields["id_taikhoan"].queryset)
        self.assertNotIn(self.other, form.fields["id_taikhoan"].queryset)

    def test_link_account_makes_existing_profile_visible_to_its_owner(self):
        nv = self.profile("NV004", None, 4)
        data = {field: getattr(nv, field) for field in NhanVienForm.Meta.fields}
        data["maphong"] = self.pb.pk
        data["id_taikhoan"] = self.unlinked.pk
        services.luu_nhan_vien(form=NhanVienForm(data, instance=nv), nguoi_thuc_hien=self.manager)
        self.client.force_login(self.unlinked)
        self.assertContains(self.client.get(reverse("nhan_su:ho_so_cua_toi")), nv.tennv)

    def test_departed_account_link_is_locked(self):
        self.offboard()
        self.nv.refresh_from_db()
        form = NhanVienForm(instance=self.nv)
        self.assertTrue(form.fields["id_taikhoan"].disabled)
        self.assertIn(self.user, form.fields["id_taikhoan"].queryset)

    def test_post_requires_csrf_and_get_does_not_offboard(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.manager)
        url = reverse("nhan_su:vo_hieu_hoa_nhan_vien", args=[self.nv.pk])
        self.assertEqual(client.get(url).status_code, 200)
        self.nv.refresh_from_db()
        self.assertTrue(self.nv.trangthai)
        self.assertEqual(client.post(url, {"ngaynghiviec": TODAY, "lydonghiviec": "Thử CSRF"}).status_code, 403)

    def test_offboarding_invalidates_existing_employee_session(self):
        employee = Client()
        employee.force_login(self.user)
        self.offboard()
        self.assertEqual(employee.get(reverse("nhan_su:ho_so_cua_toi")).status_code, 302)

    def test_expiry_banner_excludes_departed_employee(self):
        self.offboard()
        self.client.force_login(self.manager)
        response = self.client.get(reverse("nhan_su:danh_sach_hop_dong"), {"trang_thai": "SAP_HET_HAN"})
        self.assertEqual(response.context["so_sap_het_han"], 0)
        self.assertNotContains(response, self.hd.pk)

    def test_password_change_retains_session_and_updates_password(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("nhan_su:doi_mat_khau"), {
            "old_password": "Old!CakeCrush936", "new_password1": "New!CakeCrush527",
            "new_password2": "New!CakeCrush527",
        })
        self.assertRedirects(response, reverse("nhan_su:doi_mat_khau_xong"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New!CakeCrush527"))
        self.assertEqual(self.client.get(reverse("nhan_su:ho_so_cua_toi")).status_code, 200)

    def test_all_manager_pages_render_and_report_field_errors(self):
        self.client.force_login(self.manager)
        routes = (
            ("danh_sach_nhan_vien", []), ("them_nhan_vien", []),
            ("chi_tiet_nhan_vien", [self.nv.pk]), ("sua_nhan_vien", [self.nv.pk]),
            ("vo_hieu_hoa_nhan_vien", [self.nv.pk]), ("danh_sach_hop_dong", []),
            ("them_hop_dong", []), ("chi_tiet_hop_dong", [self.hd.pk]),
            ("sua_hop_dong", [self.hd.pk]), ("gia_han_hop_dong", [self.hd.pk]),
        )
        for name, args in routes:
            with self.subTest(route=name):
                self.assertEqual(self.client.get(reverse("nhan_su:" + name, args=args)).status_code, 200)
        invalid = self.client.post(reverse("nhan_su:them_nhan_vien"), {})
        self.assertEqual(invalid.status_code, 200)
        self.assertTrue(invalid.context["form"].errors)

    def test_expiry_boundaries_match_badges_and_filters(self):
        self.client.force_login(self.manager)
        for days in (-1, 0, 1, 14, 15, 30, 31):  # Phân biệt hôm nay với khoảng cảnh báo 1–30 ngày.
            with self.subTest(days=days):
                self.hd.ngayhethan = TODAY + timedelta(days=days)
                self.hd.save(update_fields=["ngayhethan"])
                response = self.client.get(reverse("nhan_su:danh_sach_hop_dong"), {"trang_thai": "SAP_HET_HAN"})
                self.assertEqual(response.context["so_sap_het_han"], int(1 <= days <= 30))
                ids = [hd.pk for hd in response.context["page_obj"]]
                self.assertEqual(self.hd.pk in ids, 1 <= days <= 30)

    def test_personal_contract_prioritizes_active_over_newer_future_contract(self):
        future = self.contract("HD-NV-003", self.nv, TODAY + timedelta(days=400), TODAY + timedelta(days=5))
        self.client.force_login(self.user)
        response = self.client.get(reverse("nhan_su:hop_dong_cua_toi"))
        self.assertEqual(response.context["hop_dong"].pk, self.hd.pk)
        self.assertIn(future.pk, [hd.pk for hd in response.context["lich_su"]])

    def test_pagination_preserves_filters_and_highlights_current_page(self):
        for suffix in range(4, 15):  # Có nhiều hơn một trang sau khi lọc phòng ban.
            self.profile(f"NV{suffix:03}", None, suffix)
        self.client.force_login(self.manager)
        response = self.client.get(reverse("nhan_su:danh_sach_nhan_vien"), {"phong_ban": self.pb.pk, "page": "2"})
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertContains(response, 'aria-current="page">2</span>')
        self.assertContains(response, "phong_ban=PB001&amp;page=1")

    def test_new_profile_and_contract_keep_numbered_codes_with_account_link(self):
        data = {field: getattr(self.nv, field) for field in NhanVienForm.Meta.fields}
        data.update(tennv="Hồ sơ mới", maphong=self.pb.pk, id_taikhoan=self.unlinked.pk,
                    email="new@example.com", sdt="0909999999", cccd="040999999999")
        nv = services.luu_nhan_vien(form=NhanVienForm(data), nguoi_thuc_hien=self.manager)
        self.assertEqual(nv.pk, "NV004")
        hd = services.luu_hop_dong(form=HopDongForm({
            "manv": nv.pk, "loaihd": HopDong.Loai.KHONG_XAC_DINH, "ngayky": TODAY,
            "ngaybatdau": TODAY, "ngayhethan": "", "luongcoban": "8000000",
        }), nguoi_thuc_hien=self.manager)
        self.assertEqual(hd.pk, "HD-NV-003")

    def test_edit_back_cancel_and_save_return_to_original_filtered_list(self):
        self.client.force_login(self.manager)
        nv_data = {field: getattr(self.nv, field) for field in NhanVienForm.Meta.fields}
        nv_data = {field: value.pk if hasattr(value, "pk") else value if value is not None else "" for field, value in nv_data.items()}
        nv_data["tennv"] = "Họ tên vừa chỉnh sửa"
        hd_data = {"manv": self.nv.pk, "loaihd": self.hd.loaihd, "ngayky": self.hd.ngayky,
                   "ngaybatdau": self.hd.ngaybatdau, "ngayhethan": self.hd.ngayhethan, "luongcoban": "9000000"}
        for edit_name, pk, list_name, query, data in (
            ("sua_nhan_vien", self.nv.pk, "danh_sach_nhan_vien", "phong_ban=PB001&page=2", nv_data),
            ("sua_hop_dong", self.hd.pk, "danh_sach_hop_dong", "loai_hd=XAC_DINH_1_NAM&page=2", hd_data),
        ):
            with self.subTest(page=edit_name):
                target = reverse("nhan_su:" + list_name) + "?" + query
                edit = reverse("nhan_su:" + edit_name, args=[pk]) + "?" + urlencode({"next": target})
                response = self.client.get(edit)
                self.assertEqual(response.context["url_huy"], target)
                self.assertContains(response, 'href="' + target.replace("&", "&amp;") + '"', count=2)
                self.assertRedirects(self.client.post(edit, data), target)
        self.nv.refresh_from_db()
        self.hd.refresh_from_db()
        self.assertEqual(self.nv.tennv, nv_data["tennv"])
        self.assertEqual(self.hd.luongcoban, Decimal("9000000"))

    def test_edit_from_detail_returns_to_detail_and_rejects_external_next(self):
        self.client.force_login(self.manager)
        for edit_name, detail_name, list_name, pk in (
            ("sua_nhan_vien", "chi_tiet_nhan_vien", "danh_sach_nhan_vien", self.nv.pk),
            ("sua_hop_dong", "chi_tiet_hop_dong", "danh_sach_hop_dong", self.hd.pk),
        ):
            edit = reverse("nhan_su:" + edit_name, args=[pk])
            detail = reverse("nhan_su:" + detail_name, args=[pk])
            self.assertEqual(self.client.get(edit, {"next": detail}).context["url_huy"], detail)
            for target in ("https://example.com/", "//example.com/", "https://[", "/admin/", ""):
                with self.subTest(page=edit_name, next=target):
                    response = self.client.get(edit, {"next": target})
                    self.assertEqual(response.context["url_huy"], reverse("nhan_su:" + list_name))

    def test_removed_date_filters_and_subtitles_no_longer_affect_employee_list(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("nhan_su:danh_sach_nhan_vien"), {"tu_ngay": "invalid", "den_ngay": "1900-01-01"})
        self.assertEqual(response.context["page_obj"].paginator.count, 3)
        for text in ('name="tu_ngay"', 'name="den_ngay"', "Lọc theo ngày vào làm", "Quản lý thông tin và tình trạng làm việc."):
            self.assertNotContains(response, text)

    def test_contract_policy_is_fixed_and_expiry_day_count_is_hidden(self):
        self.client.force_login(self.manager)
        listing = self.client.get(reverse("nhan_su:danh_sach_hop_dong"))
        self.assertContains(listing, "Sắp hết hạn")
        self.assertNotContains(listing, "Còn 20 ngày")
        self.assertNotContains(listing, "Theo dõi loại hợp đồng, thời hạn và tình trạng hiệu lực.")
        for route, user in (("chi_tiet_hop_dong", self.manager), ("chi_tiet_hop_dong_cua_toi", self.user)):
            self.client.force_login(user)
            response = self.client.get(reverse("nhan_su:" + route, args=[self.hd.pk]))
            for text in ("Công ty TNHH Cake Crush", "48 giờ/tuần · Theo lịch phân công", "12 ngày phép/năm theo chính sách công ty", "BHXH, BHYT, BHTN theo quy định"):
                self.assertContains(response, text)
            self.assertNotContains(response, "Chưa cập nhật")
            self.assertNotContains(response, "Hợp đồng còn 20 ngày")
