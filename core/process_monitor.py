import psutil
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from threading import Thread, Event
import json
import os

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    create_time: float
    cmdline: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'pid': self.pid,
            'name': self.name,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'status': self.status,
            'create_time': self.create_time,
            'cmdline': self.cmdline
        }

class ProcessMonitor:
    def __init__(self, log_file: str = "process_spy.log"):
        self.log_file = log_file
        self.logger = self._setup_logger()
        self.monitoring = False
        self.monitor_thread = None
        self.stop_event = Event()
        self.update_interval = 1.0
        self.process_cache = {}
        self.callbacks = []
        
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('ProcessSpy')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def add_callback(self, callback: Callable[[List[ProcessInfo]], None]):
        """Добавить callback для получения обновлений процессов"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[List[ProcessInfo]], None]):
        """Удалить callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_processes(self) -> List[ProcessInfo]:
        """Получить список всех процессов"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time', 'cmdline']):
            try:
                info = proc.info
                process_info = ProcessInfo(
                    pid=info['pid'],
                    name=info['name'] or 'Unknown',
                    cpu_percent=info['cpu_percent'] or 0.0,
                    memory_percent=info['memory_percent'] or 0.0,
                    status=info['status'] or 'unknown',
                    create_time=info['create_time'] or 0.0,
                    cmdline=info['cmdline'] or []
                )
                processes.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return processes
    
    def get_process_by_name(self, name: str) -> List[ProcessInfo]:
        """Найти процессы по имени"""
        processes = self.get_processes()
        return [p for p in processes if name.lower() in p.name.lower()]
    
    def kill_process(self, pid: int) -> bool:
        """Завершить процесс по PID"""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=5)
            self.logger.info(f"Process {pid} ({proc.name()}) terminated")
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
            self.logger.error(f"Failed to terminate process {pid}: {e}")
            return False
    
    def start_monitoring(self):
        """Начать мониторинг процессов"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.stop_event.clear()
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Process monitoring started")
    
    def stop_monitoring(self):
        """Остановить мониторинг процессов"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self.logger.info("Process monitoring stopped")
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while not self.stop_event.is_set():
            try:
                processes = self.get_processes()
                self._detect_changes(processes)
                
                # Уведомить всех подписчиков
                for callback in self.callbacks:
                    try:
                        callback(processes)
                    except Exception as e:
                        self.logger.error(f"Callback error: {e}")
                
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                time.sleep(self.update_interval)
    
    def _detect_changes(self, current_processes: List[ProcessInfo]):
        """Обнаружение изменений в процессах"""
        current_pids = {p.pid: p for p in current_processes}
        cached_pids = set(self.process_cache.keys())
        
        # Новые процессы
        new_pids = set(current_pids.keys()) - cached_pids
        for pid in new_pids:
            proc = current_pids[pid]
            self.logger.info(f"New process: {proc.name} (PID: {proc.pid})")
        
        # Завершенные процессы
        dead_pids = cached_pids - set(current_pids.keys())
        for pid in dead_pids:
            proc = self.process_cache[pid]
            self.logger.info(f"Process terminated: {proc.name} (PID: {proc.pid})")
        
        # Обновить кэш
        self.process_cache = current_pids
    
    def save_snapshot(self, filename: str):
        """Сохранить снимок текущих процессов"""
        processes = self.get_processes()
        data = {
            'timestamp': datetime.now().isoformat(),
            'processes': [p.to_dict() for p in processes]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Snapshot saved to {filename}")