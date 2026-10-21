@echo off
chcp 65001 > nul
title Google Flow AI Studio
echo ==========================================================
echo        GOOGLE FLOW AI STUDIO - KHOI DONG HE THONG
echo ==========================================================
echo.
echo [*] Dang kiem tra moi truong Python...
python --version
if errorlevel 1 (
    echo [x] Khong tim thay Python. Vui long cai dat Python 3.10 tro len.
    pause
    exit /b 1
)

echo [*] Dang khoi dong Web Server tai http://localhost:7860...
start "" http://localhost:7860
python -m uvicorn app:app --host 127.0.0.1 --port 7860 --reload
pause
