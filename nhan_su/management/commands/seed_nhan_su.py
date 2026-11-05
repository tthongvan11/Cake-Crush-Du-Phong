from datetime import timedelta  # Tính ngày mẫu tương đối với ngày chạy lệnh.
from decimal import Decimal  # Lưu lương bằng số thập phân chính xác.

from django.contrib.auth import get_user_model  # Dùng đúng model tài khoản của dự án.
from django.contrib.auth.models import Group  # Đánh dấu tài khoản do lệnh tạo, không nhầm dữ liệu cũ.
from django.core.exceptions import ValidationError  # Nhận lỗi kiểm tra hồ sơ hoặc hợp đồng.
from django.core.management.base import BaseCommand, CommandError  # Đăng ký lệnh manage.py.
from django.db import transaction  # Thành công toàn bộ hoặc hoàn tác toàn bộ bộ mẫu.
from django.utils import timezone  # Các mốc ngày theo múi giờ Việt Nam đã cấu hình.

from nhan_su.forms import HopDongForm, NhanVienForm, VoHieuHoaNhanVienForm  # Tái dùng kiểm tra trên web.
from nhan_su.models import HopDong, NhanVien, PhongBan  # Các bảng nghiệp vụ cần nạp.
from nhan_su.services import _tao_ma, luu_hop_dong, luu_nhan_vien, vo_hieu_hoa_nhan_vien  # Dùng chung cấp mã và xử lý nghiệp vụ.


GROUP_NAME = "CakeCrush - Dữ liệu mẫu"  # Nhóm này không được cấp thêm quyền Django admin.
DEFAULT_PASSWORD = "CakeCrush@123"  # Mật khẩu dùng thử cho các tài khoản mới của bộ mẫu.
DEPARTMENTS = ("Cửa hàng", "Bếp bánh", "Nhân sự", "Marketing", "Kế toán", "Kho vận")  # Tái sử dụng phòng ban trùng tên.
MANAGER_JOBS = ("Quản lý cửa hàng", "Trưởng bộ phận sản xuất", "Trưởng phòng nhân sự", "Trưởng phòng marketing", "Trưởng phòng kế toán")  # Năm vị trí quản lý.
EMPLOYEE_JOBS = ("Nhân viên bán hàng", "Thợ bánh", "Nhân viên nhân sự", "Nhân viên marketing", "Kế toán viên", "Nhân viên kho")  # Chức vụ tương ứng các phòng ban.
NAMES = (  # Tên hư cấu để giao diện có dữ liệu tiếng Việt đa dạng.
    ("Nguyễn Minh Anh", "Nữ"), ("Trần Quốc Huy", "Nam"), ("Lê Thu Hà", "Nữ"), ("Phạm Đức Anh", "Nam"), ("Hoàng Ngọc Lan", "Nữ"),
    ("Nguyễn Văn An", "Nam"), ("Trần Thị Bình", "Nữ"), ("Lê Minh Đức", "Nam"), ("Phạm Thu Hằng", "Nữ"), ("Hoàng Gia Bảo", "Nam"),
    ("Võ Ngọc Mai", "Nữ"), ("Đặng Hoàng Nam", "Nam"), ("Bùi Thanh Trúc", "Nữ"), ("Đỗ Quang Minh", "Nam"), ("Hồ Khánh Linh", "Nữ"),
    ("Phan Anh Tuấn", "Nam"), ("Vũ Thảo Nguyên", "Nữ"), ("Ngô Hải Đăng", "Nam"), ("Dương Phương Anh", "Nữ"), ("Đinh Tuấn Kiệt", "Nam"),
    ("Nguyễn Bảo Ngọc", "Nữ"), ("Trần Đức Phúc", "Nam"), ("Lê Hải Yến", "Nữ"), ("Phạm Minh Khang", "Nam"), ("Hoàng Mỹ Duyên", "Nữ"),
    ("Võ Thành Đạt", "Nam"), ("Đặng Hồng Nhung", "Nữ"), ("Bùi Quốc Bảo", "Nam"), ("Đỗ Tú Anh", "Nữ"), ("Hồ Nhật Minh", "Nam"),
    ("Phan Diệu Linh", "Nữ"), ("Vũ Đình Phong", "Nam"), ("Ngô Thanh Hương", "Nữ"), ("Dương Việt Hoàng", "Nam"), ("Đinh Kim Ngân", "Nữ"),
    ("Nguyễn Trọng Nhân", "Nam"), ("Trần Gia Hân", "Nữ"), ("Lê Quốc Khánh", "Nam"), ("Phạm Ngọc Ánh", "Nữ"), ("Hoàng Anh Dũng", "Nam"),
    ("Võ Minh Châu", "Nữ"), ("Đặng Hữu Nghĩa", "Nam"), ("Bùi Phương Thảo", "Nữ"), ("Đỗ Thành Công", "Nam"), ("Hồ Lan Chi", "Nữ"),
    ("Phan Đức Long", "Nam"), ("Vũ Yến Nhi", "Nữ"), ("Ngô Hồng Sơn", "Nam"), ("Dương Khánh Vy", "Nữ"), ("Đinh Bảo Long", "Nam"),
)  # Không sử dụng thông tin nhân sự thật để tạo dữ liệu mẫu.


def mot_nam_sau(ngay, so_nam=1):  # Giữ đúng ngày, tháng khi tạo hợp đồng một năm.
    try:  # Ngày 29/02 có thể không tồn tại ở năm đích.
        return ngay.replace(year=ngay.year + so_nam)  # Cộng hoặc trừ đúng số năm lịch.
    except ValueError:  # Xử lý riêng ngày nhuận.
        return ngay.replace(year=ngay.year + so_nam, day=28)  # Dùng ngày cuối tháng 02 của năm đích.


def kich_ban(index, hom_nay):  # Chọn loại và thời hạn cho hợp đồng chính của từng hồ sơ.
    if index < 5:  # Các quản lý có hợp đồng không xác định thời hạn.
        return HopDong.Loai.KHONG_XAC_DINH, hom_nay - timedelta(days=700), None
    thu_tu = index - 5  # Đánh số riêng cho 45 nhân viên.
    if thu_tu < 20:  # Nhóm có hợp đồng một năm còn hiệu lực.
        so_ngay = (1, 7, 14, 15, 30, 0, 10, 20, 25, 29)[thu_tu] if thu_tu < 10 else 180 + (thu_tu - 10) * 7  # Có đủ mốc cảnh báo.
        ket_thuc = hom_nay + timedelta(days=so_ngay)  # Bao gồm trường hợp hết hạn hôm nay.
        return HopDong.Loai.XAC_DINH_1_NAM, mot_nam_sau(ket_thuc, -1), ket_thuc
    if thu_tu < 25:  # Nhân viên thâm niên có hợp đồng không thời hạn.
        return HopDong.Loai.KHONG_XAC_DINH, hom_nay - timedelta(days=600), None
    if thu_tu < 30:  # Năm hồ sơ đang thử việc.
        bat_dau = hom_nay - timedelta(days=20 + (thu_tu - 25) * 2)  # Đã làm việc được vài tuần.
        return HopDong.Loai.THU_VIEC, bat_dau, bat_dau + timedelta(days=60)
    if thu_tu < 35:  # Năm hợp đồng chưa đến ngày bắt đầu.
        bat_dau = hom_nay + timedelta(days=7 + (thu_tu - 30) * 2)  # Bắt đầu trong một đến ba tuần tới.
    elif thu_tu < 40:  # Năm hợp đồng đã hết hạn tự nhiên.
        ket_thuc = hom_nay - timedelta(days=15 + (thu_tu - 35) * 15)  # Đã quá hạn trước ngày chạy lệnh.
        return HopDong.Loai.XAC_DINH_1_NAM, mot_nam_sau(ket_thuc, -1), ket_thuc
    else:  # Năm hồ sơ cuối sẽ được vô hiệu hóa qua service sau khi tạo hợp đồng.
        bat_dau = hom_nay - timedelta(days=180)  # Hợp đồng vẫn còn hạn trước lúc nghỉ.
    return HopDong.Loai.XAC_DINH_1_NAM, bat_dau, mot_nam_sau(bat_dau)  # Thời hạn đúng một năm.


class Command(BaseCommand):  # Chạy bằng python manage.py seed_nhan_su.
    help = "Thêm 50 hồ sơ, 50 tài khoản liên kết và 60 hợp đồng mẫu; chạy lại không tạo trùng."

    def add_arguments(self, parser):  # Các tùy chọn nhỏ phục vụ chạy lại hoặc thử trước.
        parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Mật khẩu cho tài khoản mới; không đổi mật khẩu tài khoản cũ.")
        parser.add_argument("--dry-run", action="store_true", help="Kiểm tra toàn bộ dữ liệu rồi hoàn tác, không lưu database.")

    def handle(self, *args, **options):  # Điểm bắt đầu của management command.
        if not options["password"]:  # Không tạo tài khoản có mật khẩu trống.
            raise CommandError("Mật khẩu mẫu không được để trống.")
        self.hom_nay = timezone.localdate()  # Tất cả hợp đồng dùng cùng một mốc ngày.
        User = get_user_model()  # Dùng tài khoản Django hiện có của dự án.
        self.tai_khoan_moi = {}  # Chuẩn bị hash trước giao dịch để SQLite không bị khóa quá lâu.
        self.usernames = [f"demo_ql{i + 1:02d}" if i < 5 else f"demo_nv{i - 4:02d}" for i in range(50)]  # Tên ổn định giúp chạy lại không trùng.
        da_co = set(User.objects.filter(username__in=self.usernames).values_list("username", flat=True))  # Không đổi mật khẩu tài khoản đã có.
        for index, username in enumerate(self.usernames):  # Chỉ băm mật khẩu cho tài khoản chưa tồn tại.
            if username in da_co:  # Tài khoản cũ sẽ được kiểm tra nguồn gốc bên trong giao dịch.
                continue
            ho, ten = NAMES[index][0].split(" ", 1)  # first_name và last_name ghép lại đúng họ tên trên giao diện.
            user = User(username=username, email=f"{username}@example.com", first_name=ho, last_name=ten, is_staff=index < 5)  # Không tạo superuser mẫu.
            user.set_password(options["password"])  # Lưu hash chuẩn Django, không lưu mật khẩu dạng rõ.
            self.tai_khoan_moi[username] = user  # Chưa ghi dữ liệu vào database tại bước chuẩn bị.
        try:  # Một lỗi bất kỳ phải hoàn tác cả bộ mẫu, không để hồ sơ thiếu tài khoản.
            with transaction.atomic():  # Dùng cấu hình IMMEDIATE hiện tại để cấp mã tuần tự an toàn trên SQLite.
                so_moi = self.nap_du_lieu(User)  # Tạo hồ sơ, hợp đồng và xử lý nghỉ việc qua service chung.
                if options["dry_run"]:  # Kiểm tra chạy thử cũng thực hiện đủ các bước nghiệp vụ.
                    transaction.set_rollback(True)  # Hoàn tác trước khi rời giao dịch.
        except ValidationError as loi:  # Hiển thị lỗi dữ liệu dễ đọc khi chạy lệnh.
            raise CommandError(f"Chưa lưu bộ mẫu: {loi}") from loi
        nhan = "CHẠY THỬ, KHÔNG LƯU" if options["dry_run"] else "ĐÃ NẠP"  # Phân biệt rõ kết quả thật và thử.
        self.stdout.write(self.style.SUCCESS(f"{nhan}: thêm {so_moi['ho_so']} hồ sơ, {so_moi['tai_khoan']} tài khoản, {so_moi['hop_dong']} hợp đồng."))
        self.stdout.write("Tài khoản thử: demo_ql01 (quản lý), demo_nv01 (nhân viên). Mật khẩu chỉ áp dụng cho tài khoản mới.")  # Không in mật khẩu tùy chọn ra log.

    def nap_du_lieu(self, User):  # Toàn bộ hàm này được gọi bên trong transaction.atomic.
        nhom, _ = Group.objects.get_or_create(name=GROUP_NAME)  # Nhóm chỉ để nhận diện dữ liệu mẫu, không gán quyền admin.
        phong_ban = []  # Giữ danh mục trong bộ nhớ để không truy vấn lặp.
        for ten in DEPARTMENTS:  # Tái sử dụng cả phòng ban cũ đã có cùng tên.
            pb = PhongBan.objects.filter(tenphongban=ten).first()  # Không đổi mã hoặc mô tả phòng ban của người dùng.
            if pb is None:  # Chỉ tạo phòng ban còn thiếu.
                pb = PhongBan(maphongban=_tao_ma(PhongBan, "PB"), tenphongban=ten, mota="Danh mục phục vụ dữ liệu mẫu Cake Crush.")
                pb.full_clean()  # Kiểm tra độ dài và tính duy nhất trước khi lưu.
                pb.save(force_insert=True)  # Không ghi đè phòng ban trùng mã.
            phong_ban.append(pb)  # Mỗi hồ sơ chọn phòng ban từ danh mục này.
        so_moi = {"ho_so": 0, "tai_khoan": 0, "hop_dong": 0}  # Báo đúng số bản ghi vừa bổ sung.
        quan_ly = None  # Quản lý mẫu đầu tiên được dùng làm người thực hiện nghiệp vụ.
        for index, username in enumerate(self.usernames):  # Tạo đúng 5 quản lý và 45 nhân viên mẫu.
            user = User.objects.filter(username=username).first()  # Không tự cập nhật tài khoản đã tồn tại.
            if user is None:  # Chỉ lưu hash đã chuẩn bị cho tài khoản mới.
                user = self.tai_khoan_moi[username]  # Không băm lại khi đã giữ quyền ghi SQLite.
                user.full_clean()  # Kiểm tra tên đăng nhập và dữ liệu tài khoản.
                user.save(force_insert=True)  # Tài khoản mẫu luôn là bản ghi mới.
                user.groups.add(nhom)  # Đánh dấu nguồn gốc để lần sau nhận diện chính xác.
                so_moi["tai_khoan"] += 1  # Cộng số tài khoản mới.
            elif user.email != f"{username}@example.com" or not user.groups.filter(pk=nhom.pk).exists():  # Tránh nhầm tài khoản có sẵn của người dùng.
                raise CommandError(f"Tài khoản {username} đã tồn tại nhưng không thuộc bộ mẫu; không ghi đè.")
            if index == 0:  # Chọn người quản lý thực hiện các service.
                if not user.is_active or not (user.is_staff or user.is_superuser):  # Không nâng quyền hoặc mở khóa tài khoản khi chạy lại.
                    raise CommandError("demo_ql01 không còn quyền quản lý hoạt động; giữ nguyên dữ liệu và dừng nạp.")
                quan_ly = user  # Không cần tạo superuser để seed nghiệp vụ.
            loai, bat_dau, ket_thuc = kich_ban(index, self.hom_nay)  # Đa dạng hợp đồng theo ngày chạy lần đầu.
            nv = NhanVien.objects.filter(id_taikhoan=user).first()  # Mỗi tài khoản chỉ có một hồ sơ.
            if nv is not None:  # Bộ mẫu luôn được lưu toàn bộ trong một giao dịch.
                continue  # Chạy lại giữ cả chỉnh sửa, mật khẩu, lịch sử và trạng thái nghỉ việc đã có.
            slot = index + 1  # Chọn số liên hệ hư cấu riêng cho từng người.
            while NhanVien.objects.filter(sdt=f"0999{slot:06d}").exists() or NhanVien.objects.filter(cccd=f"999999{slot:06d}").exists():  # Tránh trùng dữ liệu cũ.
                slot += 50  # Đổi số mẫu mà không sửa bản ghi đang sử dụng số đó.
            ngay_vao = min(bat_dau - timedelta(days=61), self.hom_nay - timedelta(days=30))  # Lịch sử thử việc luôn trước hợp đồng chính.
            if loai == HopDong.Loai.THU_VIEC:  # Nhân viên mới đang thử việc bắt đầu cùng ngày vào làm.
                ngay_vao = bat_dau
            nv = luu_nhan_vien(form=NhanVienForm({  # Tái sử dụng toàn bộ kiểm tra của màn hình hồ sơ.
                "tennv": NAMES[index][0], "gioitinh": NAMES[index][1], "ngaysinh": self.hom_nay.replace(year=self.hom_nay.year - 24 - index % 18, month=1 + index % 12, day=1 + index % 27),  # Ngày sinh luôn tồn tại.
                "sdt": f"0999{slot:06d}", "cccd": f"999999{slot:06d}", "email": user.email,  # Dữ liệu hư cấu có định dạng hợp lệ.
                "diachi": f"Địa chỉ mẫu {index + 1:02d}, Đà Nẵng", "maphong": phong_ban[index % 6].pk,  # Không dùng địa chỉ cá nhân thật.
                "chucvu": MANAGER_JOBS[index] if index < 5 else EMPLOYEE_JOBS[index % 6], "ngayvaolam": ngay_vao, "id_taikhoan": user.pk,  # Liên kết ngay với tài khoản đăng nhập.
            }), nguoi_thuc_hien=quan_ly)  # Mã nhân viên vẫn tăng theo NV001, NV002...
            so_moi["ho_so"] += 1  # Ghi nhận hồ sơ mới.
            self.them_hop_dong(nv, loai, bat_dau, ket_thuc, quan_ly, index)  # Cấp HD-QL hoặc HD-NV theo tài khoản thực tế.
            so_moi["hop_dong"] += 1  # Mỗi hồ sơ mới có một hợp đồng chính.
            if index < 10:  # Thêm 10 hợp đồng lịch sử để tổng bộ mẫu là 60.
                self.them_hop_dong(nv, HopDong.Loai.THU_VIEC, nv.ngayvaolam, nv.ngayvaolam + timedelta(days=60), quan_ly, index)  # Thử việc kết thúc trước hợp đồng chính.
                so_moi["hop_dong"] += 1  # Hợp đồng lịch sử được tính là Hết hạn từ ngày thực tế.
            if index >= 45:  # Năm nhân viên cuối nghỉ việc, chỉ thực hiện lúc tạo mới.
                vo_hieu_hoa_nhan_vien(form=VoHieuHoaNhanVienForm({  # Dùng đúng luồng nghiệp vụ đã kiểm thử.
                    "ngaynghiviec": self.hom_nay - timedelta(days=10 + (index - 45) * 5), "lydonghiviec": "Dữ liệu mẫu: nghỉ theo nguyện vọng cá nhân.",
                }, nhan_vien=nv), nguoi_thuc_hien=quan_ly)  # Khóa tài khoản, hợp đồng chuyển Hết hiệu lực và giữ lịch sử.
        return so_moi  # Chạy lần hai trả toàn bộ số mới bằng 0.

    def them_hop_dong(self, nv, loai, bat_dau, ket_thuc, quan_ly, index):  # Dùng chung cho hợp đồng chính và lịch sử.
        luong = Decimal(18_000_000 + index * 1_000_000) if index < 5 else Decimal(6_000_000 + index % 9 * 500_000)  # Lương hư cấu khác nhau theo vị trí.
        return luu_hop_dong(form=HopDongForm({  # Không bỏ qua validation hoặc cấp mã riêng bằng UUID.
            "manv": nv.pk, "loaihd": loai, "ngayky": bat_dau - timedelta(days=3), "ngaybatdau": bat_dau, "ngayhethan": ket_thuc or "", "luongcoban": luong,
        }), nguoi_thuc_hien=quan_ly)  # Service kiểm tra trùng, tính trạng thái và lưu hợp đồng.
