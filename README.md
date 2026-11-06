# Cake-Crush

Website quản lý nhân sự Cake Crush.

## Database

Ứng dụng dùng PostgreSQL khi có `DATABASE_URL`; khi chạy local có thể dùng
`DATABASE_PUBLIC_URL`. Trên Railway,
tạo một dịch vụ PostgreSQL cùng project với ứng dụng và nối biến `DATABASE_URL`
của dịch vụ PostgreSQL vào dịch vụ web. Các bản chạy của ứng dụng trong cùng
project sẽ dùng chung dữ liệu qua kết nối riêng. PostgreSQL 15 trở lên phù hợp
với phiên bản Django hiện tại.

Ở máy phát triển, nếu không có `DATABASE_URL`, ứng dụng vẫn dùng SQLite tại
`db.sqlite3`. Không đưa URL có mật khẩu lên Git. Nếu chạy ứng dụng bên ngoài
Railway, có thể đặt URL kết nối công khai vào `DATABASE_PUBLIC_URL` trong biến
môi trường hoặc `.venv/.env`; bảo vệ URL này như mật khẩu. Cấu hình đọc thêm
`.venv/.env` để thuận tiện trên máy local, thư mục `.venv` đã bị Git bỏ qua.

## Chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

Không cần cấu hình DB để chạy local trên SQLite. Tạo tài khoản quản lý bằng
`python manage.py createsuperuser` nếu cần đăng nhập bằng tài khoản mới.

## Chuyển dữ liệu SQLite sang PostgreSQL

Tạo bản xuất từ SQLite hiện tại trước khi cấu hình `DATABASE_URL`. Tạm dừng
các thay đổi dữ liệu trong lúc chuyển để bản xuất không bị lệch:

```powershell
python manage.py dumpdata --natural-foreign --natural-primary `
  --exclude=contenttypes --exclude=auth.permission `
  --exclude=sessions --exclude=admin.logentry `
  --output="$env:TEMP\cakecrush-seed.json"
```

Sau khi tạo PostgreSQL và đặt `DATABASE_URL` trong `.env` hoặc biến môi trường
của dịch vụ ứng dụng, tạo schema rồi nhập dữ liệu vào database PostgreSQL đang
còn trống:

```powershell
python manage.py migrate
python manage.py loaddata "$env:TEMP\cakecrush-seed.json"
```

Lệnh xuất giữ lại tài khoản, nhân viên, hợp đồng, chấm công, nghỉ phép, đào tạo,
đánh giá và dữ liệu ứng dụng khác; Django tạo lại quyền và content type trên
PostgreSQL khi chạy migration. Không chạy `loaddata` lặp lại trên database đã có
dữ liệu.

## Cloudflare D1 (legacy)

Đặt đủ ba biến môi trường `CF_ACCOUNT_ID`, `CF_D1_DATABASE_ID` và
`CF_API_TOKEN` để dùng Cloudflare D1 khi chưa có `DATABASE_URL`. Cấu hình
PostgreSQL qua `DATABASE_URL` được ưu tiên. Không commit file `.env` hoặc giá trị
bí mật lên Git.
