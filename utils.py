# utils.py (расширенная версия)
import os
import re
import math
import random
import string
import hashlib
from datetime import datetime

def format_bytes(bytes_value):
    """Форматирование байтов в читаемый вид"""
    if bytes_value is None or bytes_value == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    bytes_value = float(bytes_value)
    unit_index = 0
    
    while abs(bytes_value) >= 1024.0 and unit_index < len(units) - 1:
        bytes_value /= 1024.0
        unit_index += 1
    
    return f"{bytes_value:.2f} {units[unit_index]}"

def format_duration(seconds):
    """Форматирование секунд в читаемый вид"""
    if not seconds:
        return "00:00"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def sanitize_filename(filename):
    """Очистка имени файла"""
    if not filename:
        return 'video'
    
    # Удаление недопустимых символов
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Удаление управляющих символов
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    # Ограничение длины
    filename = filename[:100].strip()
    # Удаление точек в конце
    filename = filename.rstrip('.')
    
    return filename or 'video'

def format_number(num):
    """Форматирование больших чисел"""
    if not num:
        return '0'
    
    num = int(num)
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)

def is_valid_youtube_url(url):
    """Проверка валидности URL YouTube"""
    if not url or len(url) > 2000:
        return False
    
    patterns = [
        r'^(https?://)?(www\.)?(youtube\.com/watch\?v=[\w-]+)',
        r'^(https?://)?(www\.)?(youtu\.be/[\w-]+)',
        r'^(https?://)?(www\.)?youtube\.com/playlist\?list=[\w-]+',
        r'^(https?://)?(www\.)?youtube\.com/shorts/[\w-]+',
    ]
    
    return any(re.match(pattern, url) for pattern in patterns)

def parse_video_id(url):
    """Извлечение ID видео из URL"""
    patterns = [
        r'(?:v=|/)([\w-]{11})(?:&|$)',
        r'youtu\.be/([\w-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def generate_id(length=16):
    """Генерация уникального ID"""
    timestamp = str(int(datetime.now().timestamp() * 1000))
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{timestamp}_{random_part}"

def cleanup_old_files(directory, max_age_hours=24):
    """Очистка старых файлов"""
    if not os.path.exists(directory):
        return 0
    
    now = datetime.now()
    removed = 0
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            if os.path.isfile(filepath):
                file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                age_hours = (now - file_time).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    os.remove(filepath)
                    removed += 1
        except Exception:
            continue
    
    return removed

def get_file_hash(filepath, algorithm='md5'):
    """Вычисление хеша файла"""
    hash_obj = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

class DownloadProgress:
    """Класс для отслеживания прогресса"""
    
    def __init__(self, download_id):
        self.download_id = download_id
        self._data = {
            'status': 'starting',
            'percent': 0,
            'downloaded': '0 B',
            'total': '0 B',
            'speed': '0 B/s',
            'eta': '--:--',
            'filename': '',
            'created_at': datetime.now().isoformat()
        }
        self._lock = __import__('threading').Lock()
    
    def update(self, **kwargs):
        with self._lock:
            self._data.update(kwargs)
    
    def get(self):
        with self._lock:
            return self._data.copy()

class Timer:
    """Контекстный менеджер для замера времени"""
    
    def __init__(self, name="Operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = __import__('time').time()
        return self
    
    def __exit__(self, *args):
        self.end_time = __import__('time').time()
        duration = self.end_time - self.start_time
        print(f"{self.name} took {duration:.3f}s")
    
    @property
    def elapsed(self):
        if self.end_time:
            return self.end_time - self.start_time
        return __import__('time').time() - self.start_time

def retry(attempts=3, delay=1, backoff=2):
    """Декоратор для повторных попыток"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < attempts - 1:
                        __import__('time').sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator