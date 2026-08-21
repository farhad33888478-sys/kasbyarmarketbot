@echo off
chcp 65001 >nul
title کسب‌یار مارکت - سرور وب
cd /d %~dp0

echo در حال بررسی نصب بودن پیش‌نیازها ...
pip install -q -r requirements.txt

if exist "C:\Psiphon\psiphon.exe" (
    echo در حال روشن‌کردن پراکسی Psiphon ^(برای دسترسی به عکس‌های تلگرام^) ...
    start "" "C:\Psiphon\psiphon.exe"
    timeout /t 25 /nobreak >nul
) else (
    echo [توجه] Psiphon پیدا نشد؛ اگر عکس‌های کسب‌وکارها نمایش داده نمی‌شوند، Psiphon را روشن کن.
)

echo.
echo در حال راه‌اندازی سایت کسب‌یار مارکت ...
echo آدرس سایت: http://127.0.0.1:8000
echo آدرس پنل مدیریت: http://127.0.0.1:8000/admin/login
echo.

start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000"
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000

pause
