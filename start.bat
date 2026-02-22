<!-- start.bat -->
@echo off
chcp 65001 >nul
title TubeFlow Pro

echo 🚀 Запуск TubeFlow Pro...

:: Проверка виртуального окружения
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

:: Активация
call venv\Scripts\activate

:: Установка зависимостей
echo 📥 Проверка зависимостей...
pip install -q -r requirements.txt

:: Проверка FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg не найден! Установите FFmpeg и добавьте в PATH
    pause
    exit /b 1
)

:: Запуск
echo ✅ Запуск сервера на http://localhost:5001
python app.py
pause