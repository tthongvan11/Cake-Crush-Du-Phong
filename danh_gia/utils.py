def sinh_ma(model, truong, tien_to, do_dai):
    """Sinh mã tự tăng dạng <tiền tố><số có đệm 0>, ví dụ KY0001, DG00012.

    Lấy mã lớn nhất hiện có (so sánh chuỗi, an toàn vì số đã đệm 0 cố định)
    rồi cộng 1. Gọi bên trong transaction.atomic ở nơi lưu để hạn chế trùng.
    """
    ma_cuoi = (
        model.objects.filter(**{f"{truong}__startswith": tien_to})
        .order_by(f"-{truong}")
        .values_list(truong, flat=True)
        .first()
    )
    so = int(ma_cuoi[len(tien_to):]) + 1 if ma_cuoi else 1
    return f"{tien_to}{so:0{do_dai}d}"
