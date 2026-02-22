# security.py
import re
import hashlib
import ipaddress
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

class SecurityManager:
    """Управление безопасностью приложения"""
    
    def __init__(self):
        self.blocked_ips = set()
        self.suspicious_ips = defaultdict(lambda: {'count': 0, 'last_seen': None})
        self.request_counts = defaultdict(lambda: {'count': 0, 'window_start': datetime.now()})
        self.lock = Lock()
        self.max_requests_per_minute = 60
        self.block_threshold = 100
    
    def check_request(self, request):
        """Проверка запроса на подозрительность"""
        ip = request.remote_addr
        
        with self.lock:
            # Проверка блокировки
            if ip in self.blocked_ips:
                raise SecurityException(f"IP {ip} is blocked")
            
            # Проверка на сканирование
            user_agent = request.headers.get('User-Agent', '')
            if self._is_suspicious_ua(user_agent):
                self.suspicious_ips[ip]['count'] += 1
            
            # Rate limiting
            self._check_rate_limit(ip)
            
            # Обновление статистики
            self.suspicious_ips[ip]['last_seen'] = datetime.now()
    
    def _is_suspicious_ua(self, user_agent):
        """Проверка User-Agent на подозрительность"""
        suspicious_patterns = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zgrab',
            'gobuster', 'dirb', 'wfuzz', 'burp', 'metasploit'
        ]
        ua_lower = user_agent.lower()
        return any(pattern in ua_lower for pattern in suspicious_patterns)
    
    def _check_rate_limit(self, ip):
        """Проверка лимита запросов"""
        now = datetime.now()
        data = self.request_counts[ip]
        
        # Сброс окна
        if now - data['window_start'] > timedelta(minutes=1):
            data['count'] = 0
            data['window_start'] = now
        
        data['count'] += 1
        
        if data['count'] > self.max_requests_per_minute:
            self.suspicious_ips[ip]['count'] += 10
        
        # Автоблокировка
        if self.suspicious_ips[ip]['count'] > self.block_threshold:
            self.blocked_ips.add(ip)
            raise SecurityException(f"IP {ip} blocked due to suspicious activity")
    
    def block_ip(self, ip, reason=""):
        """Ручная блокировка IP"""
        with self.lock:
            try:
                # Валидация IP
                ipaddress.ip_address(ip)
                self.blocked_ips.add(ip)
                return True
            except ValueError:
                return False
    
    def unblock_ip(self, ip):
        """Разблокировка IP"""
        with self.lock:
            self.blocked_ips.discard(ip)
            self.suspicious_ips.pop(ip, None)
            return True
    
    def get_blocked_ips(self):
        """Список заблокированных IP"""
        return list(self.blocked_ips)
    
    def sanitize_input(self, data):
        """Очистка входных данных"""
        if isinstance(data, str):
            # Удаление потенциально опасных символов
            sanitized = re.sub(r'[<>\"\'%;()&+]', '', data)
            return sanitized[:1000]  # Ограничение длины
        return data

class SecurityException(Exception):
    """Исключение безопасности"""
    pass

class InputValidator:
    """Валидация входных данных"""
    
    @staticmethod
    def validate_url(url):
        """Валидация URL"""
        if not url or len(url) > 2000:
            return False
        
        # Разрешенные схемы
        allowed_schemes = ['http', 'https']
        pattern = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
        
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_format_id(format_id):
        """Валидация ID формата"""
        # Разрешенные символы
        return bool(re.match(r'^[a-zA-Z0-9_+-]+$', format_id)) and len(format_id) < 50
    
    @staticmethod
    def sanitize_filename(filename):
        """Очистка имени файла"""
        # Удаление путей
        filename = filename.replace('../', '').replace('..\\', '')
        # Разрешенные символы
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        return filename[:255]