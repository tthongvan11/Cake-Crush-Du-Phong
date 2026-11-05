"""Gom các view lại để urls.py vẫn viết views.ky_tao, views.khen_thuong, ...

  trang_chu.py   trang chủ app
  ky_danh_gia.py UC-1.1, 1.2  kỳ + tiêu chí
  danh_gia.py    UC-1.3       chấm điểm + xác nhận
  ghi_nhan.py    logic chung của khen thưởng / kỷ luật
  khen_thuong.py UC-2.1
  ky_luat.py     UC-2.2
  nhan_vien.py   UC-2.3, 2.4  xem kết quả + phản hồi
"""
from .danh_gia import danh_gia_tao, danh_gia_xac_nhan  # noqa: F401
from .khen_thuong import khen_thuong  # noqa: F401
from .ky_danh_gia import ky_danh_sach, ky_ket_qua, ky_tao, tieu_chi_thiet_lap  # noqa: F401
from .ky_luat import ky_luat  # noqa: F401
from .nhan_vien import gui_phan_hoi, ket_qua_cua_toi  # noqa: F401
from .trang_chu import trang_chu  # noqa: F401
