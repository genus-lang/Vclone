@echo off
cd /d D:\dev\tts

echo Stopping any existing server on port 8000...
powershell -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

timeout /t 1 /nobreak >nul

echo Starting VoxAI TTS server...
D:\dev\tts\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
