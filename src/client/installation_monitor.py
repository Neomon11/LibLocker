"""
Модуль мониторинга установки программ
Отслеживает запуск установщиков и скачивание установочных файлов
"""
import os
import sys
import time
import logging
import psutil
from pathlib import Path
from typing import Callable, Optional, Set
from threading import Thread, Event
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InstallationMonitor:
    """Мониторинг установки программ и скачивания установочных файлов"""
    
    # Расширения установочных файлов (зависят от платформы)
    INSTALLER_EXTENSIONS = {'.exe', '.msi', '.bat', '.cmd', '.ps1', '.vbs', '.jar'}
    
    # Добавляем специфичные расширения для других платформ
    if sys.platform == 'darwin':  # macOS
        INSTALLER_EXTENSIONS.update({'.dmg', '.pkg'})
    elif sys.platform.startswith('linux'):  # Linux
        INSTALLER_EXTENSIONS.update({'.deb', '.rpm', '.sh'})
    
    # Процессы установщиков (имена)
    INSTALLER_PROCESSES = {
        'msiexec.exe', 'setup.exe', 'install.exe', 'installer.exe',
        'unins000.exe', 'uninst.exe', 'uninstall.exe',
        'inno_updater.exe', 'installshield.exe', 'wise.exe',
        'nsis.exe', 'isetup.exe'
    }
    
    # Системные процессы-исключения (не триггерят тревогу даже если содержат 'setup' или 'install')
    SYSTEM_PROCESS_EXCLUSIONS = {
        'trustedinstaller.exe',  # Windows Modules Installer (Windows Update service)
        'tiworker.exe',  # Windows Update worker process
        'wuauclt.exe',  # Windows Update AutoUpdate Client
        'facefoduninstaller.exe',  # Windows Feature on Demand Uninstaller
    }
    
    # Папки для мониторинга загрузок
    DOWNLOAD_FOLDERS = [
        Path.home() / "Downloads",
        Path.home() / "Загрузки",
        Path.home() / "Desktop",
        Path.home() / "Рабочий стол"
    ]
    
    def __init__(self, on_installation_detected: Optional[Callable] = None, signal_emitter=None):
        """
        Инициализация монитора
        
        Args:
            on_installation_detected: Callback при обнаружении установки (deprecated - use signal_emitter)
            signal_emitter: Qt signal emitter for thread-safe callbacks (InstallationMonitorSignals)
        """
        self.on_installation_detected = on_installation_detected
        self.signal_emitter = signal_emitter
        self.enabled = False
        self.monitoring_thread: Optional[Thread] = None
        self.stop_event = Event()
        
        # Отслеживание уже проверенных процессов и файлов
        self.known_processes: Set[int] = set()
        self.known_files: Set[str] = set()
        
        # Инициализация - запоминаем текущие процессы и файлы
        self._initialize_known_state()
    
    def _initialize_known_state(self):
        """Инициализация состояния - запоминаем текущие процессы и файлы"""
        try:
            # Запоминаем все текущие процессы
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    self.known_processes.add(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Запоминаем существующие файлы в папках загрузок
            for folder in self.DOWNLOAD_FOLDERS:
                if folder.exists():
                    for file_path in folder.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in self.INSTALLER_EXTENSIONS:
                            self.known_files.add(str(file_path))
        except Exception as e:
            logger.error(f"Error initializing known state: {e}", exc_info=True)
    
    def start(self):
        """Запуск мониторинга"""
        if self.enabled:
            logger.warning("Installation monitor is already running")
            return
        
        self.enabled = True
        self.stop_event.clear()
        
        # Обновляем известное состояние при запуске
        self._initialize_known_state()
        
        self.monitoring_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Installation monitoring started")
    
    def stop(self):
        """Остановка мониторинга"""
        if not self.enabled:
            return
        
        self.enabled = False
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
            self.monitoring_thread = None
        
        logger.info("Installation monitoring stopped")
    
    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while not self.stop_event.is_set():
            try:
                # Проверка процессов
                if self._check_installer_processes():
                    self._trigger_alert("Обнаружен запуск программы установки")
                    break
                
                # Проверка новых файлов в папках загрузок
                if self._check_download_folders():
                    self._trigger_alert("Обнаружено скачивание установочного файла")
                    break
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            
            # Проверка каждые 2 секунды
            self.stop_event.wait(2)
    
    def _check_installer_processes(self) -> bool:
        """
        Проверка запущенных процессов установщиков
        
        Returns:
            True если обнаружен новый процесс установки
        """
        try:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    pid = proc.pid
                    name = proc.name().lower() if proc.name() else ""
                    
                    # Пропускаем уже известные процессы
                    if pid in self.known_processes:
                        continue
                    
                    # Добавляем в известные
                    self.known_processes.add(pid)
                    
                    # Пропускаем системные процессы из списка исключений
                    # (name уже в нижнем регистре, см. строку 154)
                    if name in self.SYSTEM_PROCESS_EXCLUSIONS:
                        continue
                    
                    # Проверяем, является ли это установщиком
                    if name in self.INSTALLER_PROCESSES or 'setup' in name or 'install' in name:
                        # Проверяем, что процесс создан недавно (в последние 10 секунд)
                        create_time = datetime.fromtimestamp(proc.create_time())
                        if datetime.now() - create_time < timedelta(seconds=10):
                            logger.warning(f"Installer process detected: {name} (PID: {pid})")
                            return True
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        
        except Exception as e:
            logger.error(f"Error checking processes: {e}", exc_info=True)
        
        return False
    
    def _check_download_folders(self) -> bool:
        """
        Проверка папок загрузок на новые установочные файлы
        
        Returns:
            True если обнаружен новый установочный файл
        """
        try:
            for folder in self.DOWNLOAD_FOLDERS:
                if not folder.exists():
                    continue
                
                for file_path in folder.iterdir():
                    try:
                        if not file_path.is_file():
                            continue
                        
                        # Проверяем расширение
                        if file_path.suffix.lower() not in self.INSTALLER_EXTENSIONS:
                            continue
                        
                        file_str = str(file_path)
                        
                        # Пропускаем известные файлы
                        if file_str in self.known_files:
                            continue
                        
                        # Добавляем в известные
                        self.known_files.add(file_str)
                        
                        # Проверяем, что файл создан недавно (в последние 30 секунд)
                        file_stat = file_path.stat()
                        create_time = datetime.fromtimestamp(file_stat.st_ctime)
                        if datetime.now() - create_time < timedelta(seconds=30):
                            logger.warning(f"New installer file detected: {file_path}")
                            return True
                    
                    except (OSError, PermissionError) as e:
                        logger.debug(f"Cannot access file {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"Error checking download folders: {e}", exc_info=True)
        
        return False
    
    def _trigger_alert(self, reason: str):
        """
        Вызов callback при обнаружении установки
        
        Args:
            reason: Причина срабатывания
        """
        logger.critical(f"INSTALLATION DETECTED: {reason}")
        
        # Используем Qt signal для thread-safe вызова (приоритет)
        if self.signal_emitter:
            try:
                # Emit signal - Qt automatically marshals to main thread
                self.signal_emitter.installation_detected.emit(reason)
                logger.info("Installation alert signal emitted successfully")
            except Exception as e:
                logger.error(f"Error emitting installation detected signal: {e}", exc_info=True)
        # Fallback на старый callback (может быть небезопасно для Qt)
        elif self.on_installation_detected:
            try:
                self.on_installation_detected(reason)
            except Exception as e:
                logger.error(f"Error calling installation detected callback: {e}", exc_info=True)
