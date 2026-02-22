# cache_manager.py
import time
import json
import hashlib
import pickle
import os
from threading import Lock
from collections import OrderedDict
from functools import wraps

class CacheManager:
    """Продвинутый менеджер кэширования с LRU политикой"""
    
    def __init__(self, max_size=1000, default_ttl=3600):
        self.cache = OrderedDict()
        self.timestamps = {}
        self.ttl = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
        self.disk_cache_dir = 'cache'
        os.makedirs(self.disk_cache_dir, exist_ok=True)
    
    def get(self, key):
        """Получение значения из кэша"""
        with self.lock:
            # Проверка памяти
            if key in self.cache:
                if self._is_valid(key):
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return self.cache[key]
                else:
                    self._remove(key)
            
            # Проверка диска
            disk_value = self._get_from_disk(key)
            if disk_value is not None:
                self._set_memory(key, disk_value, self.default_ttl)
                self.hits += 1
                return disk_value
            
            self.misses += 1
            return None
    
    def set(self, key, value, ttl=None):
        """Установка значения в кэш"""
        ttl = ttl or self.default_ttl
        with self.lock:
            self._set_memory(key, value, ttl)
            self._save_to_disk(key, value, ttl)
    
    def _set_memory(self, key, value, ttl):
        """Установка в память"""
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self.ttl[key] = ttl
        self.cache.move_to_end(key)
    
    def _is_valid(self, key):
        """Проверка валидности записи"""
        if key not in self.timestamps:
            return False
        age = time.time() - self.timestamps[key]
        return age < self.ttl[key]
    
    def _remove(self, key):
        """Удаление записи"""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)
        self.ttl.pop(key, None)
        self._remove_from_disk(key)
    
    def _evict_oldest(self):
        """Удаление самой старой записи"""
        if self.cache:
            oldest = next(iter(self.cache))
            self._remove(oldest)
    
    def _get_from_disk(self, key):
        """Чтение с диска"""
        filepath = os.path.join(self.disk_cache_dir, f"{key}.cache")
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                if data['expires'] > time.time():
                    return data['value']
                else:
                    os.remove(filepath)
        except Exception:
            pass
        return None
    
    def _save_to_disk(self, key, value, ttl):
        """Сохранение на диск"""
        filepath = os.path.join(self.disk_cache_dir, f"{key}.cache")
        try:
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'expires': time.time() + ttl,
                    'value': value
                }, f)
        except Exception as e:
            print(f"Cache save error: {e}")
    
    def _remove_from_disk(self, key):
        """Удаление с диска"""
        filepath = os.path.join(self.disk_cache_dir, f"{key}.cache")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
    
    def clear(self):
        """Очистка кэша"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
            self.ttl.clear()
            self.hits = 0
            self.misses = 0
            
            # Очистка диска
            for f in os.listdir(self.disk_cache_dir):
                if f.endswith('.cache'):
                    try:
                        os.remove(os.path.join(self.disk_cache_dir, f))
                    except Exception:
                        pass
    
    def stats(self):
        """Статистика кэша"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.2%}",
            'max_size': self.max_size
        }

def cached(ttl=3600, key_func=None):
    """Декоратор для кэширования функций"""
    def decorator(f):
        cache = CacheManager()
        
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Генерация ключа
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = hashlib.md5(
                    f"{f.__name__}:{str(args)}:{str(kwargs)}".encode()
                ).hexdigest()
            
            # Проверка кэша
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Выполнение функции
            result = f(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        wrapper.cache = cache
        return wrapper
    return decorator