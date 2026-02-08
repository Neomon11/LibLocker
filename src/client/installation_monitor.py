"""
Модуль мониторинга установки программ
Отслеживает скачивание установочных файлов в базовые директории
"""
import os
import sys
import time
import logging
from pathlib import Path
from typing import Callable, Optional, Set
from threading import Thread, Event
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InstallationMonitor:
    """Мониторинг установки программ - отслеживание установочных файлов в базовых директориях"""
    
    # Расширения установочных файлов (зависят от платформы)
    INSTALLER_EXTENSIONS = {'.exe', '.msi', '.bat', '.cmd', '.ps1', '.vbs', '.jar'}
    
    # Добавляем специфичные расширения для других платформ
    if sys.platform == 'darwin':  # macOS
        INSTALLER_EXTENSIONS.update({'.dmg', '.pkg'})
    elif sys.platform.startswith('linux'):  # Linux
        INSTALLER_EXTENSIONS.update({'.deb', '.rpm', '.sh'})
    
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
        
        # Отслеживание уже проверенных файлов
        self.known_files: Set[str] = set()
        
        # Инициализация - запоминаем текущие файлы
        self._initialize_known_state()
    
    def _initialize_known_state(self):
        """Инициализация состояния - запоминаем текущие файлы"""
        try:
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
                # Проверка новых файлов в папках загрузок
                if self._check_download_folders():
                    self._trigger_alert("Обнаружено скачивание установочного файла")
                    break
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            
            # Проверка каждые 2 секунды
            self.stop_event.wait(2)
    
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
