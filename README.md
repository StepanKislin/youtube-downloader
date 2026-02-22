<!-- README.md -->
# TubeFlow Pro 🎬

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-red)](https://github.com/yt-dlp/yt-dlp)

> Современный веб-загрузчик видео с YouTube с красивым интерфейсом и поддержкой высоких разрешений.



## ✨ Возможности

- 📹 **Загрузка видео** — от 144p до 4K/8K (при наличии)
- 🎵 **Извлечение аудио** — MP3 высокого качества
- 📊 **Прогресс в реальном времени** — скорость, оставшееся время, размер
- 🎨 **Современный UI** — glassmorphism, анимации, адаптивный дизайн
- 📱 **Все устройства** — работает на телефонах, планшетах и ПК
- 🔒 **Безопасность** — изоляция через виртуальное окружение
- ⚡ **Быстрая работа** — многопоточная загрузка и обработка

## 🚀 Быстрый старт

### Требования

- Python 3.8+
- FFmpeg (для конвертации)
- macOS / Linux / Windows

### Установка

```bash
# 1. Клонирование репозитория
git clone https://github.com/yourusername/tubeflow-pro.git
cd tubeflow-pro

# 2. Создание виртуального окружения
python3 -m venv venv

# 3. Активация окружения
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. Установка зависимостей
pip install -r requirements.txt

# 5. Установка FFmpeg
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg
# Windows: скачайте с https://ffmpeg.org/download.html

# 6. Запустите проект
python3 app.py