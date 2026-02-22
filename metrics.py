# metrics.py
import time
import json
from collections import defaultdict, deque
from threading import Lock
from datetime import datetime

class MetricsCollector:
    """Сбор метрик производительности"""
    
    def __init__(self, window_size=3600):
        self.request_times = deque(maxlen=10000)
        self.endpoint_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'errors': 0})
        self.status_codes = defaultdict(int)
        self.error_types = defaultdict(int)
        self.hourly_stats = deque(maxlen=24)
        self.lock = Lock()
        self.start_time = time.time()
    
    def record_request(self, endpoint, status_code, duration):
        """Запись метрик запроса"""
        with self.lock:
            self.request_times.append({
                'timestamp': time.time(),
                'duration': duration,
                'endpoint': endpoint,
                'status': status_code
            })
            
            self.endpoint_stats[endpoint]['count'] += 1
            self.endpoint_stats[endpoint]['total_time'] += duration
            self.status_codes[status_code] += 1
            
            if status_code >= 400:
                self.endpoint_stats[endpoint]['errors'] += 1
    
    def record_error(self, error_type):
        """Запись ошибки"""
        with self.lock:
            self.error_types[error_type] += 1
    
    def record_cache_hit(self):
        """Запись попадания в кэш"""
        pass  # Реализовано в CacheManager
    
    def record_cache_miss(self):
        """Запись промаха кэша"""
        pass
    
    def get_summary(self):
        """Сводка метрик"""
        with self.lock:
            total_requests = len(self.request_times)
            if total_requests == 0:
                return {'message': 'No data yet'}
            
            recent_requests = [
                r for r in self.request_times 
                if time.time() - r['timestamp'] < 3600
            ]
            
            avg_response_time = sum(r['duration'] for r in recent_requests) / len(recent_requests) if recent_requests else 0
            
            return {
                'total_requests': total_requests,
                'requests_last_hour': len(recent_requests),
                'avg_response_time': f"{avg_response_time:.3f}s",
                'uptime': f"{(time.time() - self.start_time) / 3600:.1f}h",
                'endpoints': dict(self.endpoint_stats),
                'status_codes': dict(self.status_codes),
                'error_types': dict(self.error_types)
            }
    
    def export_prometheus(self):
        """Экспорт в формате Prometheus"""
        lines = []
        lines.append("# HELP tubeflow_requests_total Total requests")
        lines.append("# TYPE tubeflow_requests_total counter")
        
        for endpoint, stats in self.endpoint_stats.items():
            lines.append(f'tubeflow_requests_total{{endpoint="{endpoint}"}} {stats["count"]}')
        
        return '\n'.join(lines)

class RateLimiter:
    """Продвинутый rate limiter с bucket алгоритмом"""
    
    def __init__(self, rate=10, per=60):
        self.rate = rate
        self.per = per
        self.buckets = {}
        self.lock = Lock()
    
    def is_allowed(self, key):
        """Проверка разрешения запроса"""
        with self.lock:
            now = time.time()
            
            if key not in self.buckets:
                self.buckets[key] = {
                    'tokens': self.rate,
                    'last_update': now
                }
            
            bucket = self.buckets[key]
            elapsed = now - bucket['last_update']
            bucket['tokens'] = min(
                self.rate,
                bucket['tokens'] + elapsed * (self.rate / self.per)
            )
            bucket['last_update'] = now
            
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            return False
    
    def get_wait_time(self, key):
        """Время ожидания до следующего запроса"""
        with self.lock:
            if key not in self.buckets:
                return 0
            
            bucket = self.buckets[key]
            needed = 1 - bucket['tokens']
            if needed <= 0:
                return 0
            
            return needed / (self.rate / self.per)