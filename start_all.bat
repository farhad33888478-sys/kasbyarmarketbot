@echo off
chcp 65001 >nul
title کسب‌یار مارکت - راه‌اندازی کامل
cd /d %~dp0

echo در حال بررسی نصب بودن پیش‌نیازها ...
pip install -q -r requirements.txt

if exist "C:\Psiphon\psiphon.exe" (
    echo در حال روشن‌کردن پراکسی Psiphon ^(برای دسترسی به تلگرام^) ...
    start "" "C:\Psiphon\psiphon.exe"
    echo چند لحظه صبر کن تا پراکسی وصل شود ...
    timeout /t 25 /nobreak >nul
) else (
    echo [توجه] Psiphon پیدا نشد. اگر عکس‌های کسب‌وکارها در سایت نمایش داده نمی‌شوند،
    echo مطمئن شو Psiphon روی مسیر C:\Psiphon\psiphon.exe نصب و روشن است.
)

echo.
echo در حال راه‌اندازی ربات تلگرام در یک پنجره جداگانه ...
start "کسب‌یار مارکت - ربات" cmd /k python main.py

echo در حال راه‌اندازی سایت در یک پنجره جداگانه ...
start "کسب‌یار مارکت - وب" cmd /k python -m uvicorn web.app:app --host 127.0.0.1 --port 8000

timeout /t 3 /nobreak >nul
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000"

echo.
echo هر دو سرویس در حال اجرا هستند. این پنجره را می‌توانید ببندید.
pause
