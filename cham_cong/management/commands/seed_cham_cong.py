import random  # Sinh dữ liệu mẫu ngẫu nhiên nhưng lặp lại được.
from datetime import date, datetime, time, timedelta  # Làm việc với ngày giờ.

from django.core.management.base import BaseCommand, CommandError  # Đăng ký lệnh manage.py.
from django.db import transaction  # Thành công toàn bộ hoặc hoàn tác toàn bộ.
from django.utils import timezone  # Ngày hiện tại theo múi giờ Việt Nam.

from cham_cong import services  # Dùng chung công thức tính giờ và đồng bộ bảng công.
from cham_cong.models import ChamCong, DonNghiPhep, LoaiPhep  # Các bảng cần nạp dữ liệu.
from nhan_su.models import NhanVien  # Hồ sơ nhân viên do lệnh seed_nhan_su tạo.


def _cong_phut(gio, so_phut):  # Cộng/trừ số phút vào một giờ trong ngày.
    return (datetime.combine(date.today(), gio) + timedelta(minutes=so_phut)).time()  # Trả về giờ mới.


class Command(BaseCommand):  # Lệnh: python manage.py seed_cham_cong
    help = "Nạp dữ liệu mẫu chấm công và đơn nghỉ phép (chạy sau seed_nhan_su)."  # Mô tả lệnh.

    @transaction.atomic  # Lỗi giữa chừng thì hoàn tác toàn bộ.
    def handle(self, *args, **options):  # Hàm chính của lệnh.
        hom_nay = timezone.localdate()  # Ngày chạy lệnh.
        ds_nv = list(NhanVien.objects.filter(trangthai=True, id_taikhoan__isnull=False).order_by("manv"))  # Nhân viên đang làm.
        if not ds_nv:  # Chưa có hồ sơ.
            raise CommandError("Chưa có hồ sơ nhân viên. Hãy chạy: python manage.py seed_nhan_su")  # Hướng dẫn.
        so_don = self._tao_don_mau(ds_nv, hom_nay)  # Đơn trước, để ngày nghỉ được ghi vào bảng công trước.
        so_cong = self._tao_cham_cong(ds_nv, hom_nay)  # Sau đó mới tạo dữ liệu Check-in/Check-out.
        self.stdout.write(self.style.SUCCESS(f"ĐÃ NẠP: {so_cong} bản ghi chấm công, {so_don} đơn nghỉ phép."))  # Kết quả.
        self.stdout.write("Thử: demo_nv01 (nhân viên, vượt quỹ phép), demo_ql01 (quản lý duyệt đơn). Mật khẩu: CakeCrush@123")  # Gợi ý.

    def _tao_cham_cong(self, ds_nv, hom_nay):  # Chấm công tháng trước và tháng này đến hôm qua.
        dau_thang_truoc = (hom_nay.replace(day=1) - timedelta(days=1)).replace(day=1)  # Ngày 1 của tháng trước.
        bat_dau, ket_thuc = services.cau_hinh("GIO_BAT_DAU"), services.cau_hinh("GIO_KET_THUC")  # Giờ ca.
        ban_ghi = []  # Danh sách bản ghi sẽ lưu.
        for nv in ds_nv:  # Duyệt từng nhân viên.
            ngay = max(dau_thang_truoc, nv.ngayvaolam)  # Không tạo dữ liệu trước ngày vào làm.
            while ngay < hom_nay:  # Đến hết hôm qua; hôm nay để trống cho người dùng tự Check-in.
                ngau_nhien = random.Random(f"{nv.manv}-{ngay}")  # Cùng nhân viên, cùng ngày → cùng kết quả.
                r = ngau_nhien.random()  # Số từ 0 đến 1 để chọn tình huống.
                if r < 0.04:  # 4% vắng không phép (tiệm bánh làm cả tuần, có cả Chủ nhật).
                    ngay += timedelta(days=1)  # Không tạo bản ghi.
                    continue  # Sang ngày kế tiếp.
                vao = _cong_phut(bat_dau, -ngau_nhien.randint(0, 5))  # Mặc định vào sớm 0–5 phút.
                ra = ket_thuc  # Mặc định ra đúng giờ.
                if r < 0.14:  # 10% đi trễ.
                    vao = _cong_phut(bat_dau, ngau_nhien.randint(5, 25))  # Trễ 5–25 phút.
                elif r < 0.21:  # 7% về sớm.
                    ra = _cong_phut(ket_thuc, -ngau_nhien.randint(10, 30))  # Sớm 10–30 phút.
                elif r < 0.30:  # 9% làm thêm.
                    ra = _cong_phut(ket_thuc, ngau_nhien.choice([30, 60, 90]))  # Thêm 0,5–1,5 giờ.
                ban_ghi.append(ChamCong(  # Bản ghi một ngày.
                    manv=nv, ngaychamcong=ngay, gio_checkin=vao, gio_checkout=ra,  # Giờ vào, ra.
                    thoigianditre=services.tinh_di_tre(vao), trangthai=ChamCong.TrangThai.DI_LAM,  # Đi trễ, trạng thái.
                    **services.tinh_ket_qua_checkout(vao, ra),  # Giờ làm, về sớm, làm thêm theo đúng công thức.
                ))  # Kết thúc bản ghi.
                ngay += timedelta(days=1)  # Sang ngày kế tiếp.
        truoc = ChamCong.objects.count()  # Số bản ghi trước khi nạp.
        ChamCong.objects.bulk_create(ban_ghi, ignore_conflicts=True)  # Bỏ qua ngày đã có (ngày nghỉ phép, lần chạy trước).
        return ChamCong.objects.count() - truoc  # Số bản ghi thật sự được thêm.

    def _tao_don_mau(self, ds_nv, hom_nay):  # Đơn nghỉ phép mẫu cho các tình huống trong mockup.
        if DonNghiPhep.objects.exists():  # Đã có đơn (chạy lại lệnh).
            return 0  # Không tạo trùng.
        nam_phep = LoaiPhep.objects.get(tenloaiphep="Nghỉ phép năm hưởng lương")  # Loại trừ phép năm.
        viec_rieng = LoaiPhep.objects.get(tenloaiphep="Nghỉ việc riêng không hưởng lương")  # Loại không lương.
        nghi_om = LoaiPhep.objects.get(tenloaiphep="Nghỉ ốm")  # Loại hưởng lương, không trừ phép.
        theo_ma = {nv.id_taikhoan.username: nv for nv in ds_nv}  # Tra hồ sơ theo tên đăng nhập.
        quan_ly = theo_ma["demo_ql01"]  # Người duyệt các đơn mẫu.
        dem = 0  # Đếm số đơn đã tạo.

        def tao(ten_dn, loai, lui_ngay, so_ngay, ly_do, trang_thai="CHODUYET", phan_hoi=None, gui_truoc=3):  # Tạo một đơn.
            nonlocal dem  # Dùng biến đếm bên ngoài.
            nv = theo_ma.get(ten_dn)  # Hồ sơ nhân viên.
            if not nv:  # Bộ mẫu không có tài khoản này.
                return  # Bỏ qua.
            bd = hom_nay + timedelta(days=lui_ngay)  # Ngày bắt đầu, tính lùi/tới từ hôm nay.
            kt = bd + timedelta(days=so_ngay - 1)  # Ngày kết thúc.
            don = DonNghiPhep.objects.create(  # Lưu đơn (bỏ qua kiểm tra "không chọn ngày quá khứ" vì là dữ liệu mẫu).
                manv=nv, maloaiphep=loai, ngaybatdau=bd, ngayketthuc=kt, songaynghi=services.so_ngay_nghi(bd, kt),  # Ngày nghỉ.
                lydo=ly_do, trangthai=trang_thai, phanhoi=phan_hoi,  # Lý do, trạng thái, phản hồi.
                nguoiduyet=None if trang_thai == "CHODUYET" else quan_ly,  # Người xử lý.
                ngayduyet=None if trang_thai == "CHODUYET" else services.thoi_diem(bd - timedelta(days=1), time(14, 15)),  # Lúc xử lý.
            )  # Kết thúc tạo đơn.
            gui = min(bd, hom_nay) - timedelta(days=gui_truoc)  # Ngày gửi đơn giả lập.
            DonNghiPhep.objects.filter(pk=don.pk).update(thoigianguidon=services.thoi_diem(gui, time(9, 10)))  # Ghi đè thời gian gửi.
            if trang_thai == "DADUYET":  # Đơn đã duyệt.
                services.dong_bo_bang_cong(don)  # Ghi Nghỉ có phép vào bảng công.
            dem += 1  # Tăng biến đếm.

        tao("demo_nv01", nam_phep, -40, 5, "Về quê có việc gia đình.", "DADUYET")  # NV dùng nhiều phép: đã dùng 5.
        tao("demo_nv01", nam_phep, -25, 6, "Đi du lịch cùng gia đình.", "DADUYET")  # Đã dùng thêm 6 → còn 1 ngày.
        tao("demo_nv01", nam_phep, 3, 3, "Có công việc cá nhân.")  # Chờ duyệt 3 ngày → vượt quỹ 2 ngày như mockup.
        tao("demo_nv02", nam_phep, -30, 2, "Giải quyết việc cá nhân.", "DADUYET")  # Đơn đã duyệt.
        tao("demo_nv02", nam_phep, -12, 1, "Công việc gia đình.", "DADUYET")  # Đơn đã duyệt.
        tao("demo_nv02", viec_rieng, -8, 1, "Có công việc gia đình cần giải quyết.", "TUCHOI",  # Đơn bị từ chối.
            "Cửa hàng chưa bố trí được nhân sự thay thế trong ngày đề xuất. Vui lòng trao đổi để chọn ngày nghỉ phù hợp.")  # Lý do.
        tao("demo_nv02", nam_phep, 4, 2, "Giải quyết công việc gia đình.")  # Chờ duyệt, trong quỹ.
        tao("demo_nv03", nghi_om, -15, 2, "Bị sốt, có giấy khám bệnh.", "DADUYET")  # Nghỉ ốm không trừ phép.
        tao("demo_nv04", viec_rieng, 6, 1, "Đưa người thân đi khám bệnh.")  # Chờ duyệt, không lương.
        tao("demo_ql02", nam_phep, 8, 2, "Tham dự đám cưới người thân.")  # Đơn của quản lý khác: demo_ql01 duyệt được.
        tao("demo_ql01", nam_phep, 10, 1, "Việc cá nhân.")  # Đơn của chính demo_ql01: không tự duyệt được.
        return dem  # Số đơn đã tạo.
