"""
Модели данных для LibLocker
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


class ClientStatus(Enum):
    """Статус клиента"""
    OFFLINE = "offline"
    ONLINE = "online"
    IN_SESSION = "in_session"
    BLOCKED = "blocked"


class SessionStatus(Enum):
    """Статус сессии"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Client:
    """Модель клиента (подконтрольного ПК)"""
    id: Optional[int] = None
    hwid: str = ""  # Уникальный идентификатор оборудования
    name: str = ""  # Имя компьютера
    ip_address: str = ""
    mac_address: str = ""
    status: ClientStatus = ClientStatus.OFFLINE
    last_seen: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        """Преобразование в словарь для передачи по сети"""
        return {
            'id': self.id,
            'hwid': self.hwid,
            'name': self.name,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'status': self.status.value,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class Session:
    """Модель сессии использования"""
    id: Optional[int] = None
    client_id: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_minutes: int = 0  # Запланированная длительность
    actual_duration: Optional[int] = None  # Фактическая длительность
    is_unlimited: bool = False
    cost: float = 0.0
    status: SessionStatus = SessionStatus.ACTIVE

    def to_dict(self):
        """Преобразование в словарь для передачи по сети"""
        return {
            'id': self.id,
            'client_id': self.client_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': self.duration_minutes,
            'actual_duration': self.actual_duration,
            'is_unlimited': self.is_unlimited,
            'cost': self.cost,
            'status': self.status.value
        }


@dataclass
class TariffSettings:
    """Настройки тарификации"""
    hourly_rate: float = 0.0  # Стоимость руб./час
    rounding_minutes: int = 5  # Округление до N минут
    free_mode: bool = True  # Бесплатный режим

    def to_dict(self):
        return {
            'hourly_rate': self.hourly_rate,
            'rounding_minutes': self.rounding_minutes,
            'free_mode': self.free_mode
        }


@dataclass
class ServerConfig:
    """Конфигурация сервера"""
    host: str = "0.0.0.0"
    port: int = 8765
    web_port: int = 8080
    admin_password_hash: str = ""
    database_path: str = "data/liblocker.db"

    def to_dict(self):
        return {
            'host': self.host,
            'port': self.port,
            'web_port': self.web_port,
            'database_path': self.database_path
        }

