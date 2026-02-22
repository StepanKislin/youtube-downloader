
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Конфигурация приложения"""
    
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Настройки загрузки
    DOWNLOAD_FOLDER = os.environ.get('DOWNLOAD_FOLDER') or 'downloads'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE', 16 * 1024 * 1024 * 1024))  # 16GB
    
    # Настройки сервера
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5001))
    DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
    
    # Настройки CORS
    CORS_ORIGINS = ['*']
    
    # Настройки yt-dlp
    YTDLP_OPTIONS = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    # Очистка временных файлов (в секундах)
    CLEANUP_DELAY = 3600  # 1 час

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # В продакшене используем Nginx для статики
    STATIC_FOLDER = None

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}