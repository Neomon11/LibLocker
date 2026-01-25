"""
Модуль работы с конфигурацией LibLocker
"""
import configparser
import os
from typing import Any
import logging

logger = logging.getLogger(__name__)


class Config:
    """Класс для работы с конфигурацией"""

    def __init__(self, config_file: str = "config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        """Загрузка конфигурации из файла"""
        if not os.path.exists(self.config_file):
            logger.warning(f"Config file {self.config_file} not found. Using defaults.")
            self._create_default_config()
        else:
            self.config.read(self.config_file, encoding='utf-8')
            logger.info(f"Config loaded from {self.config_file}")

    def _create_default_config(self):
        """Создание конфигурации по умолчанию"""
        # Попытка скопировать из example файла
        example_file = self.config_file.replace('.ini', '.example.ini')
        if os.path.exists(example_file):
            import shutil
            shutil.copy(example_file, self.config_file)
            self.config.read(self.config_file, encoding='utf-8')
            logger.info(f"Config created from {example_file}")

    def save(self):
        """Сохранение конфигурации в файл"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
        logger.info(f"Config saved to {self.config_file}")

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Получить значение из конфигурации"""
        try:
            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Получить целочисленное значение"""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Получить дробное значение"""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """Получить булево значение"""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def set(self, section: str, key: str, value: Any):
        """Установить значение в конфигурации"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))


class ServerConfig(Config):
    """Конфигурация сервера"""

    def __init__(self):
        super().__init__("config.ini")

    @property
    def host(self) -> str:
        return self.get('server', 'host', '0.0.0.0')

    @property
    def port(self) -> int:
        port = self.get_int('server', 'port', 8765)
        if not (1 <= port <= 65535):
            logger.warning(f"Invalid port {port}, using default 8765")
            return 8765
        return port

    @property
    def web_port(self) -> int:
        port = self.get_int('server', 'web_port', 8080)
        if not (1 <= port <= 65535):
            logger.warning(f"Invalid web_port {port}, using default 8080")
            return 8080
        return port

    @property
    def web_server_enabled(self) -> bool:
        return self.get_bool('server', 'web_server_enabled', False)

    @property
    def database_path(self) -> str:
        path = self.get('database', 'path', 'data/liblocker.db')
        # Если путь относительный, преобразуем в абсолютный
        if not os.path.isabs(path):
            from .utils import get_data_directory
            # Получаем только имя файла, игнорируя 'data/' в начале
            db_filename = os.path.basename(path)
            data_dir = get_data_directory()
            path = os.path.join(data_dir, db_filename)
        return path

    @property
    def free_mode(self) -> bool:
        return self.get_bool('tariff', 'free_mode', True)

    @property
    def hourly_rate(self) -> float:
        return self.get_float('tariff', 'hourly_rate', 100.0)

    @property
    def rounding_minutes(self) -> int:
        return self.get_int('tariff', 'rounding_minutes', 5)

    @property
    def admin_password_hash(self) -> str:
        return self.get('security', 'admin_password_hash', '')

    @admin_password_hash.setter
    def admin_password_hash(self, value: str):
        self.set('security', 'admin_password_hash', value)

    @property
    def log_level(self) -> str:
        return self.get('logging', 'level', 'INFO')

    @property
    def log_file(self) -> str:
        path = self.get('logging', 'file', 'logs/server.log')
        # Если путь относительный, преобразуем в абсолютный
        if not os.path.isabs(path):
            from .utils import get_application_path
            app_path = get_application_path()
            path = os.path.join(app_path, path)
        return path

    @property
    def installation_monitor_enabled(self) -> bool:
        return self.get_bool('installation_monitor', 'enabled', False)

    @installation_monitor_enabled.setter
    def installation_monitor_enabled(self, value: bool):
        self.set('installation_monitor', 'enabled', value)

    @property
    def installation_monitor_alert_volume(self) -> int:
        return self.get_int('installation_monitor', 'alert_volume', 80)

    @installation_monitor_alert_volume.setter
    def installation_monitor_alert_volume(self, value: int):
        self.set('installation_monitor', 'alert_volume', value)


class ClientConfig(Config):
    """Конфигурация клиента"""

    def __init__(self):
        super().__init__("config.client.ini")

    @property
    def server_url(self) -> str:
        return self.get('server', 'url', 'http://localhost:8765')

    @property
    def connection_timeout(self) -> int:
        return self.get_int('server', 'connection_timeout', 10)

    @property
    def reconnect_interval(self) -> int:
        return self.get_int('server', 'reconnect_interval', 5)

    @property
    def widget_position(self) -> tuple:
        x = self.get_int('widget', 'position_x', 20)
        y = self.get_int('widget', 'position_y', 20)
        return (x, y)

    @property
    def widget_size(self) -> tuple:
        w = self.get_int('widget', 'width', 200)
        h = self.get_int('widget', 'height', 100)
        return (w, h)

    @property
    def widget_opacity(self) -> int:
        return self.get_int('widget', 'opacity', 240)

    @property
    def auto_hide_after(self) -> int:
        return self.get_int('widget', 'auto_hide_after', 0)

    @property
    def warning_minutes(self) -> int:
        return self.get_int('notifications', 'warning_minutes', 5)

    @property
    def sound_enabled(self) -> bool:
        return self.get_bool('notifications', 'sound_enabled', True)

    @property
    def popup_enabled(self) -> bool:
        return self.get_bool('notifications', 'popup_enabled', True)

    @property
    def admin_password_hash(self) -> str:
        return self.get('security', 'admin_password_hash', '')

    @admin_password_hash.setter
    def admin_password_hash(self, value: str):
        self.set('security', 'admin_password_hash', value)

    @property
    def auto_unlock_timeout(self) -> int:
        return self.get_int('security', 'auto_unlock_timeout', 10)

    @property
    def log_level(self) -> str:
        return self.get('logging', 'level', 'INFO')

    @property
    def log_file(self) -> str:
        path = self.get('logging', 'file', 'logs/client.log')
        # Если путь относительный, преобразуем в абсолютный
        if not os.path.isabs(path):
            from .utils import get_application_path
            app_path = get_application_path()
            path = os.path.join(app_path, path)
        return path

    @property
    def autostart_enabled(self) -> bool:
        return self.get_bool('autostart', 'enabled', False)

    @property
    def auto_connect(self) -> bool:
        return self.get_bool('autostart', 'auto_connect', True)

    @property
    def start_minimized(self) -> bool:
        return self.get_bool('autostart', 'start_minimized', False)

    @property
    def installation_monitor_enabled(self) -> bool:
        return self.get_bool('installation_monitor', 'enabled', False)

    @installation_monitor_enabled.setter
    def installation_monitor_enabled(self, value: bool):
        self.set('installation_monitor', 'enabled', value)

    @property
    def alert_volume(self) -> int:
        return self.get_int('installation_monitor', 'alert_volume', 80)

    @alert_volume.setter
    def alert_volume(self, value: int):
        self.set('installation_monitor', 'alert_volume', value)

