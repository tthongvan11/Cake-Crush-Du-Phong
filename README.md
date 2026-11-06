# Cake-Crush

Website quản lý nhân sự Cake Crush.

## Chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

Nếu chưa đặt thông tin Cloudflare D1, dự án dùng SQLite ở `db.sqlite3` và không
cần cấu hình Cloudflare. Tạo tài khoản quản lý bằng
`python manage.py createsuperuser` nếu cần đăng nhập bằng tài khoản mới.

## Cloudflare D1

Đặt đủ ba biến môi trường `CF_ACCOUNT_ID`, `CF_D1_DATABASE_ID` và
`CF_API_TOKEN` để dùng Cloudflare D1. Nếu chỉ đặt một phần, ứng dụng báo rõ biến
nào đang thiếu. Không commit file `.env` hoặc giá trị bí mật lên Git.
