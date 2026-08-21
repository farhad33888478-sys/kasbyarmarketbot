@echo off

echo Starting Psiphon...
start "" "C:\Psiphon\psiphon.exe"

echo Waiting for Psiphon connection...
timeout /t 60 /nobreak

echo Starting kasbyarmarket bot...
cd /d C:\Users\farhad\Downloads\kasbyarmarketbot

"C:\Users\farhad\AppData\Local\Programs\Python\Python312\python.exe" main.py

pause