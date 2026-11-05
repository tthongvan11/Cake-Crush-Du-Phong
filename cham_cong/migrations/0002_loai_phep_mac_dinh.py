from django.db import migrations  # Lớp migration của Django.

LOAI_PHEP = [  # (Tên loại phép, hưởng lương, trừ phép năm) theo ví dụ trong ERD.
    ("Nghỉ phép năm hưởng lương", True, True),  # Duy nhất loại này trừ vào quỹ phép năm.
    ("Nghỉ việc riêng không hưởng lương", False, False),  # Dùng khi hết phép năm.
    ("Nghỉ ốm", True, False),  # Hưởng lương, không trừ phép năm.
    ("Nghỉ sinh", True, False),  # Hưởng lương, không trừ phép năm.
]  # Kết thúc danh mục.


def tao_loai_phep(apps, schema_editor):  # Tạo danh mục loại phép mặc định.
    LoaiPhep = apps.get_model("cham_cong", "LoaiPhep")  # Model tại thời điểm chạy migration.
    for ten, huong_luong, tru_phep in LOAI_PHEP:  # Duyệt từng loại.
        LoaiPhep.objects.get_or_create(  # Không tạo trùng khi chạy lại.
            tenloaiphep=ten, defaults={"huongluong": huong_luong, "tru_phepnam": tru_phep},  # Giá trị mặc định.
        )  # Kết thúc tạo.


def xoa_loai_phep(apps, schema_editor):  # Hoàn tác migration.
    apps.get_model("cham_cong", "LoaiPhep").objects.filter(tenloaiphep__in=[l[0] for l in LOAI_PHEP]).delete()  # Xóa danh mục mặc định.


class Migration(migrations.Migration):  # Khai báo migration dữ liệu.
    dependencies = [("cham_cong", "0001_initial")]  # Chạy sau khi tạo bảng.
    operations = [migrations.RunPython(tao_loai_phep, xoa_loai_phep)]  # Thao tác tạo và hoàn tác.
