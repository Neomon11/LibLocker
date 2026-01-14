"""
Утилиты для работы с системой и идентификации оборудования
"""
import hashlib
import uuid
import platform
from typing import Optional


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

