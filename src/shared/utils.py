"""
Утилиты для работы с системой и идентификации оборудования
"""
import hashlib
import uuid
import platform
import os
import sys
from typing import Optional


class SingleInstanceChecker:
    """
    Класс для проверки того, что запущен только один экземпляр приложения
    Использует lock-файлы для предотвращения запуска нескольких копий
    """
    
    def __init__(self, app_name: str):
        """
        Инициализация checker
        
        Args:
            app_name: Имя приложения (например, 'liblocker_client' или 'liblocker_server')
        """
        self.app_name = app_name
        # Используем безопасную временную директорию
        import tempfile
        temp_dir = tempfile.gettempdir()
        self.lock_dir = os.path.join(temp_dir, 'liblocker')
        
        # Создаем директорию если не существует
        os.makedirs(self.lock_dir, exist_ok=True)
        
        self.lock_file = os.path.join(self.lock_dir, f'{app_name}.lock')
        self.lock_fd = None
        self._locked = False
    
    def is_already_running(self) -> bool:
        """
        Проверка, запущен ли уже экземпляр приложения
        
        Returns:
            True если приложение уже запущено, False если нет
        """
        if self._locked:
            # Уже заблокировано этим экземпляром
            return False
            
        if platform.system() == 'Windows':
            return self._check_windows()
        else:
            return self._check_unix()
    
    def _check_windows(self) -> bool:
        """Проверка для Windows используя эксклюзивный доступ к файлу"""
        try:
            # Пытаемся открыть файл в эксклюзивном режиме
            import msvcrt
            self.lock_fd = open(self.lock_file, 'w')
            msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            # Записываем PID
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            self._locked = True
            return False
        except (IOError, OSError):
            # Файл уже заблокирован другим процессом
            if self.lock_fd:
                try:
                    self.lock_fd.close()
                except (IOError, OSError):
                    pass
                self.lock_fd = None
            return True
    
    def _check_unix(self) -> bool:
        """Проверка для Unix-подобных систем используя fcntl"""
        try:
            import fcntl
            # Открываем файл для чтения/записи, создаем если не существует
            self.lock_fd = open(self.lock_file, 'w')
            # Пытаемся получить эксклюзивную блокировку без ожидания
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Записываем PID
            self.lock_fd.truncate(0)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            self._locked = True
            return False
        except (IOError, OSError, BlockingIOError) as e:
            # Файл уже заблокирован другим процессом
            if self.lock_fd:
                try:
                    self.lock_fd.close()
                except (IOError, OSError):
                    pass
                self.lock_fd = None
            return True
    
    def release(self):
        """Освобождение lock-файла"""
        if self.lock_fd and self._locked:
            try:
                if platform.system() != 'Windows':
                    import fcntl
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
                self._locked = False
            except (IOError, OSError):
                pass
            finally:
                self.lock_fd = None
                # Удаляем lock-файл
                try:
                    if os.path.exists(self.lock_file):
                        os.remove(self.lock_file)
                except (OSError, FileNotFoundError):
                    pass
    
    def __del__(self):
        """Автоматическое освобождение при удалении объекта"""
        self.release()


def get_hwid() -> str:
    """
    Генерация уникального идентификатора оборудования (HWID)
    Основан на UUID машины и серийных номерах оборудования
    """
    try:
        # Для Windows используем UUID узла и имя компьютера
        if platform.system() == 'Windows':
            import wmi
            c = wmi.WMI()

            # Серийный номер материнской платы
            bios_info = c.Win32_BIOS()[0]
            bios_serial = bios_info.SerialNumber

            # Серийный номер процессора
            cpu_info = c.Win32_Processor()[0]
            cpu_id = cpu_info.ProcessorId

            # Комбинируем для уникального ID
            hwid_string = f"{bios_serial}-{cpu_id}-{uuid.getnode()}"
            return hashlib.sha256(hwid_string.encode()).hexdigest()
        else:
            # Для других ОС используем MAC-адрес
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()
    except Exception as e:
        # Fallback на MAC-адрес
        return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()


def get_mac_address() -> str:
    """Получение MAC-адреса"""
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                    for elements in range(0, 2*6, 2)][::-1])
    return mac


def get_computer_name() -> str:
    """Получение имени компьютера"""
    return platform.node()


def get_local_ip() -> str:
    """Получение локального IP-адреса"""
    import socket
    try:
        # Создаем UDP соединение (не отправляем данные)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def hash_password(password: str) -> str:
    """Хеширование пароля с использованием bcrypt"""
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Проверка пароля"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def get_application_path() -> str:
    """
    Получение базового пути приложения
    Учитывает запуск через PyInstaller (использует sys._MEIPASS)
    
    Returns:
        Путь к директории с исполняемым файлом или скриптом
    """
    if getattr(sys, 'frozen', False):
        # Запуск из PyInstaller executable
        # sys.executable - путь к .exe файлу
        return os.path.dirname(sys.executable)
    else:
        # Обычный запуск Python скрипта
        # Возвращаем директорию корня проекта (где находится run_server.py)
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_data_directory() -> str:
    """
    Получение пути к директории данных приложения
    Создает директорию, если она не существует
    
    Returns:
        Путь к директории data
    """
    base_path = get_application_path()
    data_dir = os.path.join(base_path, 'data')
    
    # Создаем директорию, если не существует
    os.makedirs(data_dir, exist_ok=True)
    
    return data_dir

