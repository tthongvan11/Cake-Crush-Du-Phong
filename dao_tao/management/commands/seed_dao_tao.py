from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from nhan_su.models import NhanVien
from dao_tao.models import KhoaDaoTao, PhanCongDaoTao, TrangThaiKhoa, TienDoDaoTao, KetQuaDaoTao


class Command(BaseCommand):
    help = "Nạp dữ liệu mẫu các khóa đào tạo và phân công nhân viên theo hình ảnh thiết kế."

    def handle(self, *args, **options):
        with transaction.atomic():
            # 1. Tạo 4 khóa đào tạo mẫu chuẩn thiết kế
            khoa_data = [
                {
                    "makhoa": "DT001",
                    "tenkhoa": "An toàn vệ sinh thực phẩm",
                    "noidung": "Quy chuẩn vệ sinh an toàn thực phẩm trong chế biến và bảo quản bánh kem tại chuỗi Cake Crush. Hướng dẫn kiểm tra hạn dùng nguyên liệu, khử trùng thiết bị và tiêu chuẩn ISO 22000.",
                    "ngaybatdau": date(2026, 10, 5),
                    "ngayketthuc": date(2026, 10, 28),  # Đang diễn ra
                    "trangthai": TrangThaiKhoa.DANG_DIEN_RA,
                },
                {
                    "makhoa": "DT002",
                    "tenkhoa": "Kỹ năng phục vụ khách hàng",
                    "noidung": "Phương pháp giao tiếp chuyên nghiệp, xử lý tình huống khách hàng khó tính, quy trình tư vấn bánh tiệc và chăm sóc sau bán hàng.",
                    "ngaybatdau": date(2026, 7, 14),
                    "ngayketthuc": date(2026, 7, 16),
                    "trangthai": TrangThaiKhoa.DA_KET_THUC,
                },
                {
                    "makhoa": "DT003",
                    "tenkhoa": "Quy trình làm bánh tiêu chuẩn",
                    "noidung": "Kỹ thuật đánh kem, pha màu tự nhiên, trang trí bánh kem nhiều tầng và công thức bánh cupcake cốt dâu tươi tiêu chuẩn Cake Crush.",
                    "ngaybatdau": date(2026, 9, 5),
                    "ngayketthuc": date(2026, 9, 12),
                    "trangthai": TrangThaiKhoa.DA_KET_THUC,
                },
                {
                    "makhoa": "DT004",
                    "tenkhoa": "Kỹ năng làm việc nhóm",
                    "noidung": "Xây dựng tinh thần đồng đội, phối hợp nhịp nhàng giữa bộ phận bán hàng và thợ làm bánh trong các dịp lễ cao điểm.",
                    "ngaybatdau": date(2026, 11, 20),
                    "ngayketthuc": date(2026, 11, 25),
                    "trangthai": TrangThaiKhoa.CHUA_BAT_DAU,
                },
            ]

            khoa_objs = {}
            for k in khoa_data:
                obj, created = KhoaDaoTao.objects.update_or_create(
                    makhoa=k["makhoa"],
                    defaults=k,
                )
                khoa_objs[k["makhoa"]] = obj

            self.stdout.write(self.style.SUCCESS(f"Đã tạo/cập nhật {len(khoa_objs)} khóa đào tạo mẫu."))

            # 2. Phân công nhân viên mẫu
            nhan_viens = list(NhanVien.objects.filter(trangthai=True).order_by("manv"))
            if not nhan_viens:
                self.stdout.write(self.style.WARNING("Chưa có nhân viên trong hệ thống để phân công. Vui lòng chạy seed_nhan_su trước."))
                return

            # Phân công DT001: 5 nhân viên
            nv_dt001 = nhan_viens[:5]
            for i, nv in enumerate(nv_dt001):
                PhanCongDaoTao.objects.update_or_create(
                    nhanvien=nv,
                    khoadaotao=khoa_objs["DT001"],
                    defaults={
                        "tiendo": TienDoDaoTao.DA_HOAN_THANH if i < 3 else TienDoDaoTao.CHUA_HOAN_THANH,
                        "ngayhoanthanh": date(2026, 10, 7) if i < 3 else None,
                        "ketqua": KetQuaDaoTao.DAT if i == 0 else (KetQuaDaoTao.CHUA_DAT if i == 1 else KetQuaDaoTao.CHO_DANH_GIA),
                        "ngaydanhgia": date(2026, 10, 8) if i < 2 else None,
                    },
                )

            # Phân công DT002: 8 nhân viên
            nv_dt002 = nhan_viens[:8]
            for i, nv in enumerate(nv_dt002):
                PhanCongDaoTao.objects.update_or_create(
                    nhanvien=nv,
                    khoadaotao=khoa_objs["DT002"],
                    defaults={
                        "tiendo": TienDoDaoTao.DA_HOAN_THANH,
                        "ngayhoanthanh": date(2026, 7, 16),
                        "ketqua": KetQuaDaoTao.DAT if i % 4 != 0 else KetQuaDaoTao.CHUA_DAT,
                        "ngaydanhgia": date(2026, 7, 17),
                    },
                )

            # Phân công DT003: 10 nhân viên
            nv_dt003 = nhan_viens[:10]
            for i, nv in enumerate(nv_dt003):
                PhanCongDaoTao.objects.update_or_create(
                    nhanvien=nv,
                    khoadaotao=khoa_objs["DT003"],
                    defaults={
                        "tiendo": TienDoDaoTao.DA_HOAN_THANH,
                        "ngayhoanthanh": date(2026, 9, 12),
                        "ketqua": KetQuaDaoTao.DAT,
                        "ngaydanhgia": date(2026, 9, 13),
                    },
                )

            # Phân công DT004: 7 nhân viên
            nv_dt004 = nhan_viens[:7]
            for nv in nv_dt004:
                PhanCongDaoTao.objects.update_or_create(
                    nhanvien=nv,
                    khoadaotao=khoa_objs["DT004"],
                    defaults={
                        "tiendo": TienDoDaoTao.CHUA_HOAN_THANH,
                        "ngayhoanthanh": None,
                        "ketqua": KetQuaDaoTao.CHO_DANH_GIA,
                        "ngaydanhgia": None,
                    },
                )

            self.stdout.write(self.style.SUCCESS("ĐÃ NẠP: 4 khóa đào tạo và phân công nhân viên mẫu thành công!"))
