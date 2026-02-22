# task_queue.py
import queue
import threading
import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Any
from collections import deque

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    id: str
    function: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    created_at: float = field(default_factory=time.time)
    started_at: float = None
    completed_at: float = None
    priority: int = 5  # 1-10, меньше = важнее

class TaskQueue:
    """Потокобезопасная очередь задач с приоритетами"""
    
    def __init__(self, max_workers=3):
        self.task_queue = queue.PriorityQueue()
        self.tasks = {}
        self.workers = []
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        self.results = {}
        
        # Запуск воркеров
        for i in range(max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True, name=f"Worker-{i}")
            worker.start()
            self.workers.append(worker)
    
    def submit(self, func: Callable, *args, priority=5, **kwargs) -> str:
        """Добавление задачи в очередь"""
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            function=func,
            args=args,
            kwargs=kwargs,
            priority=priority
        )
        
        with self.lock:
            self.tasks[task_id] = task
        
        # (priority, timestamp, task_id) для корректной сортировки
        self.task_queue.put((priority, time.time(), task_id))
        
        return task_id
    
    def _worker_loop(self):
        """Основной цикл воркера"""
        while not self.shutdown_event.is_set():
            try:
                # Ожидание задачи с таймаутом
                priority, timestamp, task_id = self.task_queue.get(timeout=1)
                
                with self.lock:
                    task = self.tasks.get(task_id)
                    if not task or task.status != TaskStatus.PENDING:
                        continue
                    
                    task.status = TaskStatus.RUNNING
                    task.started_at = time.time()
                
                # Выполнение задачи
                try:
                    result = task.function(*task.args, **task.kwargs)
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                
                task.completed_at = time.time()
                
                with self.lock:
                    self.results[task_id] = {
                        'status': task.status.value,
                        'result': task.result,
                        'error': task.error,
                        'duration': task.completed_at - task.started_at if task.started_at else None
                    }
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")
    
    def get_status(self, task_id: str) -> dict:
        """Получение статуса задачи"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {
                    'id': task.id,
                    'status': task.status.value,
                    'created_at': task.created_at,
                    'started_at': task.started_at,
                    'completed_at': task.completed_at
                }
            return None
    
    def get_result(self, task_id: str) -> dict:
        """Получение результата задачи"""
        with self.lock:
            return self.results.get(task_id)
    
    def cancel(self, task_id: str) -> bool:
        """Отмена задачи"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    return True
        return False
    
    def size(self) -> int:
        """Размер очереди"""
        return self.task_queue.qsize()
    
    def position(self, task_id: str) -> int:
        """Позиция задачи в очереди"""
        # Примитивная реализация - в реальности нужно сканировать очередь
        return 0
    
    def estimated_wait(self) -> int:
        """Оценка времени ожидания в секундах"""
        queue_size = self.size()
        # Предполагаем среднее время выполнения 30 секунд
        return queue_size * 30 // self.max_workers
    
    def shutdown(self):
        """Graceful shutdown"""
        self.shutdown_event.set()
        for worker in self.workers:
            worker.join(timeout=5)

class PriorityTaskQueue:
    """Очередь с поддержкой приоритетов и зависимостей"""
    
    def __init__(self):
        self.tasks = {}
        self.dependencies = {}
        self.ready_queue = queue.PriorityQueue()
        self.lock = threading.Lock()
    
    def add_task(self, task_id, func, priority=5, dependencies=None):
        """Добавление задачи с зависимостями"""
        with self.lock:
            self.tasks[task_id] = {
                'func': func,
                'priority': priority,
                'status': 'pending',
                'dependencies': set(dependencies or [])
            }
            
            self.dependencies[task_id] = set(dependencies or [])
            
            # Проверка готовности
            if not self.dependencies[task_id]:
                self.ready_queue.put((priority, time.time(), task_id))
    
    def complete_task(self, task_id):
        """Отметка задачи как выполненной"""
        with self.lock:
            for tid, deps in self.dependencies.items():
                if task_id in deps:
                    deps.remove(task_id)
                    if not deps and self.tasks[tid]['status'] == 'pending':
                        self.ready_queue.put(
                            (self.tasks[tid]['priority'], time.time(), tid)
                        )