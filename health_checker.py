# health_checker.py
import os
import psutil
import shutil
from datetime import datetime

class HealthChecker:
    """Проверка здоровья системы"""
    
    def __init__(self):
        self.checks = {
            'disk': self.check_disk,
            'memory': self.check_memory,
            'downloads_folder': self.check_downloads_folder,
            'ffmpeg': self.check_ffmpeg,
            'permissions': self.check_permissions
        }
    
    def check_all(self):
        """Выполнение всех проверок"""
        results = {}
        for name, check_func in self.checks.items():
            try:
                results[name] = check_func()
            except Exception as e:
                results[name] = {'status': 'error', 'message': str(e)}
        return results
    
    def check_disk(self):
        """Проверка места на диске"""
        disk = psutil.disk_usage('/')
        free_percent = disk.free / disk.total * 100
        
        status = 'ok'
        if free_percent < 5:
            status = 'critical'
        elif free_percent < 10:
            status = 'warning'
        
        return {
            'status': status,
            'free_gb': disk.free / (1024**3),
            'total_gb': disk.total / (1024**3),
            'free_percent': round(free_percent, 2)
        }
    
    def check_memory(self):
        """Проверка памяти"""
        memory = psutil.virtual_memory()
        
        status = 'ok'
        if memory.percent > 90:
            status = 'critical'
        elif memory.percent > 80:
            status = 'warning'
        
        return {
            'status': status,
            'available_gb': memory.available / (1024**3),
            'percent_used': memory.percent
        }
    
    def check_downloads_folder(self):
        """Проверка папки загрузок"""
        folder = 'downloads'
        if not os.path.exists(folder):
            return {'status': 'error', 'message': 'Folder does not exist'}
        
        # Подсчет файлов
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        total_size = sum(os.path.getsize(os.path.join(folder, f)) for f in files)
        
        return {
            'status': 'ok',
            'file_count': len(files),
            'total_size_gb': total_size / (1024**3)
        }
    
    def check_ffmpeg(self):
        """Проверка наличия FFmpeg"""
        if shutil.which('ffmpeg'):
            return {'status': 'ok', 'installed': True}
        return {'status': 'warning', 'installed': False, 'message': 'FFmpeg not found'}
    
    def check_permissions(self):
        """Проверка прав доступа"""
        checks = {
            'read_downloads': os.access('downloads', os.R_OK),
            'write_downloads': os.access('downloads', os.W_OK),
            'write_logs': os.access('logs', os.W_OK) if os.path.exists('logs') else False
        }
        
        all_ok = all(checks.values())
        return {
            'status': 'ok' if all_ok else 'warning',
            'checks': checks
        }