import os
import sys

# Dam bao terminal Windows khong bi loi encode unicode
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import django
from datetime import date
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from nhan_su.models import PhongBan, NhanVien, HopDong

DEFAULT_PASSWORD = "cakecrush@123"

PHONG_BAN_DATA = [
    {
        "maphongban": "PB_BGD",
        "tenphongban": "Ban Điều hành & Quản lý",
        "mota": "Ban Giám đốc và quản trị toàn bộ hoạt động chuỗi cửa hàng Cake Crush."
    },
    {
        "maphongban": "PB_SXBB",
        "tenphongban": "Phòng Sản xuất - Bếp bánh",
        "mota": "Nghiên cứu, sơ chế, nướng và tạo hình các dòng bánh ngọt, bánh sinh nhật, bánh lạnh."
    },
    {
        "maphongban": "PB_CHDV",
        "tenphongban": "Phòng Cửa hàng và Dịch vụ khách hàng",
        "mota": "Bán lẻ trực tiếp tại quầy, phục vụ đồ uống barista, tư vấn và chăm sóc khách hàng."
    },
    {
        "maphongban": "PB_MHK",
        "tenphongban": "Phòng Mua hàng và Kho nguyên liệu",
        "mota": "Thu mua bơ, sữa, bột, hương liệu đạt chuẩn vệ sinh an toàn thực phẩm và quản lý tồn kho."
    },
    {
        "maphongban": "PB_KTTC",
        "tenphongban": "Phòng Kế toán - Tài chính",
        "mota": "Hạch toán sổ sách, đối soát doanh thu ca bán, tính lương và thanh toán công nợ."
    },
    {
        "maphongban": "PB_MKT",
        "tenphongban": "Phòng Marketing và Kinh doanh trực tuyến",
        "mota": "Phát triển thương hiệu, quản trị fanpage/website/TikTok và bán hàng qua các kênh online."
    },
    {
        "maphongban": "PB_GH",
        "tenphongban": "Bộ phận Giao hàng",
        "mota": "Vận chuyển bánh lạnh và bánh sự kiện đảm bảo nguyên vẹn tới tay khách hàng."
    },
]

NHAN_VIEN_DATA = [
    # 1. Admin
    {
        "manv": "NV001",
        "username": "admin",
        "tennv": "Trần Gia Bảo",
        "email": "admin@cakecrush.vn",
        "is_superuser": True,
        "is_staff": True,
        "chucvu": "Giám đốc điều hành",
        "maphong": "PB_BGD",
        "gioitinh": "Nam",
        "ngaysinh": date(1988, 5, 12),
        "sdt": "0903112233",
        "cccd": "079088001122",
        "diachi": "124 Nguyễn Thị Minh Khai, P. Bến Thành, Quận 1, TP.HCM",
        "ngayvaolam": date(2023, 1, 1),
        "luong": Decimal("35000000"),
    },
    # 2. Quản lý
    {
        "manv": "NV002",
        "username": "quanly",
        "tennv": "Nguyễn Hoàng Minh",
        "email": "quanly@cakecrush.vn",
        "is_superuser": False,
        "is_staff": True,
        "chucvu": "Cửa hàng trưởng / Quản lý chung",
        "maphong": "PB_BGD",
        "gioitinh": "Nam",
        "ngaysinh": date(1992, 8, 20),
        "sdt": "0918223344",
        "cccd": "079092003344",
        "diachi": "45 Lê Văn Sỹ, Phường 13, Quận 3, TP.HCM",
        "ngayvaolam": date(2023, 3, 15),
        "luong": Decimal("22000000"),
    },
    # 3-7. Phòng Sản xuất - Bếp bánh (5 NV)
    {
        "manv": "NV003",
        "username": "maianh.le",
        "tennv": "Lê Thị Mai Anh",
        "email": "maianh.le@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Bếp trưởng bánh ngọt",
        "maphong": "PB_SXBB",
        "gioitinh": "Nữ",
        "ngaysinh": date(1993, 4, 10),
        "sdt": "0971001001",
        "cccd": "079093001001",
        "diachi": "88 Cách Mạng Tháng 8, Phường 6, Quận 3, TP.HCM",
        "ngayvaolam": date(2023, 4, 1),
        "luong": Decimal("18000000"),
    },
    {
        "manv": "NV004",
        "username": "quoctuan.pham",
        "tennv": "Phạm Quốc Tuấn",
        "email": "quoctuan.pham@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Thợ làm bánh chính",
        "maphong": "PB_SXBB",
        "gioitinh": "Nam",
        "ngaysinh": date(1995, 9, 15),
        "sdt": "0971001002",
        "cccd": "079095001002",
        "diachi": "12 Phan Xích Long, Phường 2, Phú Nhuận, TP.HCM",
        "ngayvaolam": date(2023, 5, 10),
        "luong": Decimal("14000000"),
    },
    {
        "manv": "NV005",
        "username": "quynhnhu.do",
        "tennv": "Đỗ Quỳnh Như",
        "email": "quynhnhu.do@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Thợ bánh mì & bánh lạnh",
        "maphong": "PB_SXBB",
        "gioitinh": "Nữ",
        "ngaysinh": date(1998, 2, 28),
        "sdt": "0971001003",
        "cccd": "079098001003",
        "diachi": "230 Nguyễn Trãi, Phường 3, Quận 5, TP.HCM",
        "ngayvaolam": date(2023, 8, 1),
        "luong": Decimal("12000000"),
    },
    {
        "manv": "NV006",
        "username": "vanphuc.hoang",
        "tennv": "Hoàng Văn Phúc",
        "email": "vanphuc.hoang@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Thợ nướng & trang trí bánh",
        "maphong": "PB_SXBB",
        "gioitinh": "Nam",
        "ngaysinh": date(1997, 11, 5),
        "sdt": "0971001004",
        "cccd": "079097001004",
        "diachi": "56 Hoàng Văn Thụ, Phường 9, Phú Nhuận, TP.HCM",
        "ngayvaolam": date(2023, 10, 15),
        "luong": Decimal("12000000"),
    },
    {
        "manv": "NV007",
        "username": "thaovy.nguyen",
        "tennv": "Nguyễn Thảo Vy",
        "email": "thaovy.nguyen@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Phụ bếp & Chuẩn bị nguyên liệu",
        "maphong": "PB_SXBB",
        "gioitinh": "Nữ",
        "ngaysinh": date(2001, 7, 18),
        "sdt": "0971001005",
        "cccd": "079101001005",
        "diachi": "17 Điện Biên Phủ, Phường 15, Bình Thạnh, TP.HCM",
        "ngayvaolam": date(2024, 2, 1),
        "luong": Decimal("9000000"),
    },
    # 8-12. Phòng Cửa hàng và Dịch vụ khách hàng (5 NV)
    {
        "manv": "NV008",
        "username": "thutrang.vu",
        "tennv": "Vũ Thu Trang",
        "email": "thutrang.vu@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Cửa hàng phó / Thu ngân chính",
        "maphong": "PB_CHDV",
        "gioitinh": "Nữ",
        "ngaysinh": date(1996, 6, 22),
        "sdt": "0982002001",
        "cccd": "079096002001",
        "diachi": "310 Hai Bà Trưng, Phường Tân Định, Quận 1, TP.HCM",
        "ngayvaolam": date(2023, 4, 15),
        "luong": Decimal("13000000"),
    },
    {
        "manv": "NV009",
        "username": "minhkhoa.dang",
        "tennv": "Đặng Minh Khoa",
        "email": "minhkhoa.dang@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Barista kiêm Phục vụ",
        "maphong": "PB_CHDV",
        "gioitinh": "Nam",
        "ngaysinh": date(1999, 12, 12),
        "sdt": "0982002002",
        "cccd": "079099002002",
        "diachi": "79 Xô Viết Nghệ Tĩnh, Phường 21, Bình Thạnh, TP.HCM",
        "ngayvaolam": date(2023, 6, 1),
        "luong": Decimal("10000000"),
    },
    {
        "manv": "NV010",
        "username": "phuonglinh.bui",
        "tennv": "Bùi Phương Linh",
        "email": "phuonglinh.bui@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Nhân viên tư vấn & Bán hàng",
        "maphong": "PB_CHDV",
        "gioitinh": "Nữ",
        "ngaysinh": date(2000, 3, 14),
        "sdt": "0982002003",
        "cccd": "079100002003",
        "diachi": "142 Võ Thị Sáu, Phường Võ Thị Sáu, Quận 3, TP.HCM",
        "ngayvaolam": date(2023, 9, 1),
        "luong": Decimal("9500000"),
    },
    {
        "manv": "NV011",
        "username": "thanhdat.ngo",
        "tennv": "Ngô Thành Đạt",
        "email": "thanhdat.ngo@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Nhân viên bán hàng & Phục vụ bàn",
        "maphong": "PB_CHDV",
        "gioitinh": "Nam",
        "ngaysinh": date(2002, 10, 2),
        "sdt": "0982002004",
        "cccd": "079102002004",
        "diachi": "68 Trần Quang Khải, Phường Tân Định, Quận 1, TP.HCM",
        "ngayvaolam": date(2024, 1, 10),
        "luong": Decimal("9000000"),
    },
    {
        "manv": "NV012",
        "username": "kimngan.trinh",
        "tennv": "Trịnh Kim Ngân",
        "email": "kimngan.trinh@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Chăm sóc khách hàng & Đặt tiệc",
        "maphong": "PB_CHDV",
        "gioitinh": "Nữ",
        "ngaysinh": date(1998, 7, 25),
        "sdt": "0982002005",
        "cccd": "079098002005",
        "diachi": "205 Nam Kỳ Khởi Nghĩa, Phường 7, Quận 3, TP.HCM",
        "ngayvaolam": date(2023, 7, 1),
        "luong": Decimal("11000000"),
    },
    # 13-14. Phòng Mua hàng và Kho nguyên liệu (2 NV)
    {
        "manv": "NV013",
        "username": "tanphat.phan",
        "tennv": "Phan Tấn Phát",
        "email": "tanphat.phan@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Chuyên viên thu mua nguyên liệu",
        "maphong": "PB_MHK",
        "gioitinh": "Nam",
        "ngaysinh": date(1994, 1, 16),
        "sdt": "0933003001",
        "cccd": "079094003001",
        "diachi": "52 Bà Huyện Thanh Quan, Phường 9, Quận 3, TP.HCM",
        "ngayvaolam": date(2023, 3, 1),
        "luong": Decimal("13500000"),
    },
    {
        "manv": "NV014",
        "username": "haiyen.duong",
        "tennv": "Dương Hải Yến",
        "email": "haiyen.duong@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Quản lý kho & Bảo quản nguyên liệu",
        "maphong": "PB_MHK",
        "gioitinh": "Nữ",
        "ngaysinh": date(1996, 8, 30),
        "sdt": "0933003002",
        "cccd": "079096003002",
        "diachi": "118 Hoàng Sa, Phường Đa Kao, Quận 1, TP.HCM",
        "ngayvaolam": date(2023, 6, 15),
        "luong": Decimal("12000000"),
    },
    # 15-16. Phòng Kế toán - Tài chính (2 NV)
    {
        "manv": "NV015",
        "username": "thuynga.luong",
        "tennv": "Lương Thúy Nga",
        "email": "thuynga.luong@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Kế toán tổng hợp",
        "maphong": "PB_KTTC",
        "gioitinh": "Nữ",
        "ngaysinh": date(1993, 10, 11),
        "sdt": "0944004001",
        "cccd": "079093004001",
        "diachi": "24 Lý Tự Trọng, P. Bến Nghé, Quận 1, TP.HCM",
        "ngayvaolam": date(2023, 2, 1),
        "luong": Decimal("15000000"),
    },
    {
        "manv": "NV016",
        "username": "huunghia.dinh",
        "tennv": "Đinh Hữu Nghĩa",
        "email": "huunghia.dinh@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Kế toán thanh toán & Kho",
        "maphong": "PB_KTTC",
        "gioitinh": "Nam",
        "ngaysinh": date(1997, 5, 23),
        "sdt": "0944004002",
        "cccd": "079097004002",
        "diachi": "89 Pasteur, P. Bến Nghé, Quận 1, TP.HCM",
        "ngayvaolam": date(2023, 7, 20),
        "luong": Decimal("11500000"),
    },
    # 17-19. Phòng Marketing và Kinh doanh trực tuyến (3 NV)
    {
        "manv": "NV017",
        "username": "thuychi.nguyen",
        "tennv": "Nguyễn Thùy Chi",
        "email": "thuychi.nguyen@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Chuyên viên Content & Social",
        "maphong": "PB_MKT",
        "gioitinh": "Nữ",
        "ngaysinh": date(1998, 11, 9),
        "sdt": "0965005001",
        "cccd": "079098005001",
        "diachi": "15 Lê Duẩn, P. Bến Nghé, Quận 1, TP.HCM",
        "ngayvaolam": date(2023, 5, 1),
        "luong": Decimal("13000000"),
    },
    {
        "manv": "NV018",
        "username": "tuankhang.tran",
        "tennv": "Trần Tuấn Khang",
        "email": "tuankhang.tran@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Chuyên viên Ads & E-commerce",
        "maphong": "PB_MKT",
        "gioitinh": "Nam",
        "ngaysinh": date(1996, 3, 27),
        "sdt": "0965005002",
        "cccd": "079096005002",
        "diachi": "208 Nguyễn Gia Trí, Phường 25, Bình Thạnh, TP.HCM",
        "ngayvaolam": date(2023, 6, 1),
        "luong": Decimal("14000000"),
    },
    {
        "manv": "NV019",
        "username": "baongoc.lam",
        "tennv": "Lâm Bảo Ngọc",
        "email": "baongoc.lam@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Thiết kế đồ họa & Hình ảnh sản phẩm",
        "maphong": "PB_MKT",
        "gioitinh": "Nữ",
        "ngaysinh": date(1999, 4, 15),
        "sdt": "0965005003",
        "cccd": "079099005003",
        "diachi": "35 Huỳnh Thúc Kháng, P. Bến Nghé, Quận 1, TP.HCM",
        "ngayvaolam": date(2023, 9, 15),
        "luong": Decimal("12500000"),
    },
    # 20-21. Bộ phận Giao hàng (2 NV)
    {
        "manv": "NV020",
        "username": "ductrong.ta",
        "tennv": "Tạ Đức Trọng",
        "email": "ductrong.ta@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Nhân viên giao hàng bánh kem",
        "maphong": "PB_GH",
        "gioitinh": "Nam",
        "ngaysinh": date(1995, 12, 1),
        "sdt": "0912006001",
        "cccd": "079095006001",
        "diachi": "44 Ung Văn Khiêm, Phường 25, Bình Thạnh, TP.HCM",
        "ngayvaolam": date(2023, 7, 10),
        "luong": Decimal("10000000"),
    },
    {
        "manv": "NV021",
        "username": "tanlong.huynh",
        "tennv": "Huỳnh Tấn Long",
        "email": "tanlong.huynh@cakecrush.vn",
        "is_superuser": False,
        "is_staff": False,
        "chucvu": "Nhân viên giao hàng & Vận chuyển",
        "maphong": "PB_GH",
        "gioitinh": "Nam",
        "ngaysinh": date(1997, 8, 19),
        "sdt": "0912006002",
        "cccd": "079097006002",
        "diachi": "180 Đinh Tiên Hoàng, Phường Đa Kao, Quận 1, TP.HCM",
        "ngayvaolam": date(2023, 8, 15),
        "luong": Decimal("10000000"),
    },
]

def run():
    print("=== BAT DAU SEED DU LIEU LEN CLOUDFLARE D1 ===")
    
    # 1. Tao phong ban
    print("1. Dang tao cac Phong Ban...")
    pb_map = {}
    for pb_data in PHONG_BAN_DATA:
        pb, created = PhongBan.objects.get_or_create(
            maphongban=pb_data["maphongban"],
            defaults={
                "tenphongban": pb_data["tenphongban"],
                "mota": pb_data["mota"]
            }
        )
        pb_map[pb.maphongban] = pb
        status = "Tao moi" if created else "Da ton tai"
        print(f"   [{status}] {pb.maphongban}: {pb.tenphongban}")

    # 2. Tao User, NhanVien, HopDong
    print("\n2. Dang tao Tai khoan, Ho so Nhan vien va Hop dong...")
    for item in NHAN_VIEN_DATA:
        # A. User
        name_parts = item["tennv"].split()
        first_name = name_parts[-1]
        last_name = " ".join(name_parts[:-1])

        user = User.objects.filter(username=item["username"]).first()
        if not user:
            user = User(
                username=item["username"],
                email=item["email"],
                first_name=first_name,
                last_name=last_name,
                is_staff=item["is_staff"],
                is_superuser=item["is_superuser"],
            )
            user.set_password(DEFAULT_PASSWORD)
            user.save()
            user_status = "Tao moi User"
        else:
            user.set_password(DEFAULT_PASSWORD)
            user.is_staff = item["is_staff"]
            user.is_superuser = item["is_superuser"]
            user.save()
            user_status = "Cap nhat User"

        # B. NhanVien
        pb = pb_map[item["maphong"]]
        nv = NhanVien.objects.filter(manv=item["manv"]).first()
        if not nv:
            nv = NhanVien(
                manv=item["manv"],
                id_taikhoan=user,
                maphong=pb,
                tennv=item["tennv"],
                ngaysinh=item["ngaysinh"],
                gioitinh=item["gioitinh"],
                sdt=item["sdt"],
                email=item["email"],
                cccd=item["cccd"],
                diachi=item["diachi"],
                chucvu=item["chucvu"],
                ngayvaolam=item["ngayvaolam"],
                trangthai=True
            )
            nv.save()
            nv_status = "Tao moi NhanVien"
        else:
            nv.id_taikhoan = user
            nv.maphong = pb
            nv.tennv = item["tennv"]
            nv.chucvu = item["chucvu"]
            nv.save()
            nv_status = "Cap nhat NhanVien"

        # C. HopDong
        ma_hd = f"HD{item['manv'][2:]}"  # Vi du: HD001, HD002,...
        hd = HopDong.objects.filter(mahd=ma_hd).first()
        if not hd:
            hd = HopDong(
                mahd=ma_hd,
                manv=nv,
                loaihd=HopDong.Loai.KHONG_XAC_DINH,
                ngayky=item["ngayvaolam"],
                ngaybatdau=item["ngayvaolam"],
                ngayhethan=None,
                luongcoban=item["luong"],
                trangthai=HopDong.TrangThai.DANG_HIEU_LUC
            )
            hd.save()
            hd_status = "Tao moi HD"
        else:
            hd_status = "Da co HD"

        print(f"   [{user_status} | {nv_status} | {hd_status}] {item['manv']} - {item['tennv']} ({item['username']})")

    print("\n=== HOAN TAT SEED DU LIEU THANH CONG ===")

if __name__ == '__main__':
    run()
