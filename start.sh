<!-- start.sh -->
#!/bin/bash

# Скрипт запуска для macOS/Linux

echo "🚀 Запуск TubeFlow Pro..."

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация
source venv/bin/activate

# Установка зависимостей
echo "📥 Проверка зависимостей..."
pip install -q -r requirements.txt

# Проверка FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg не найден! Установите: brew install ffmpeg (macOS) или sudo apt install ffmpeg (Linux)"
    exit 1
fi

# Очистка старых файлов
echo "🧹 Очистка временных файлов..."
python -c "from utils import cleanup_old_files; cleanup_old_files('downloads')"

# Запуск
echo "✅ Запуск сервера на http://localhost:5001"
python app.py