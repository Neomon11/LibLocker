"""
Протокол связи между сервером и клиентом
WebSocket сообщения
"""
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


class MessageType(Enum):
    """Типы сообщений протокола"""
    # Клиент -> Сервер
    CLIENT_REGISTER = "client_register"
    CLIENT_HEARTBEAT = "client_heartbeat"
    CLIENT_STATUS_UPDATE = "client_status_update"
    SESSION_SYNC = "session_sync"

    # Сервер -> Клиент
    SESSION_START = "session_start"
    SESSION_STOP = "session_stop"
    SESSION_TIME_UPDATE = "session_time_update"
    SHUTDOWN = "shutdown"
    UNLOCK = "unlock"
    CONFIG_UPDATE = "config_update"
    PASSWORD_UPDATE = "password_update"

    # Двунаправленные
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    ACK = "ack"


@dataclass
class Message:
    """Базовое сообщение протокола"""
    type: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data: dict):
        return Message(
            type=data.get('type', ''),
            data=data.get('data', {}),
            timestamp=data.get('timestamp')
        )


@dataclass
class SessionStartMessage:
    """Сообщение начала сессии"""
    duration_minutes: int = 0
    is_unlimited: bool = False
    cost_per_hour: float = 0.0
    free_mode: bool = True

    def to_message(self) -> Message:
        return Message(
            type=MessageType.SESSION_START.value,
            data=asdict(self)
        )


@dataclass
class SessionStopMessage:
    """Сообщение окончания сессии"""
    reason: str = "manual"  # manual, timeout, error

    def to_message(self) -> Message:
        return Message(
            type=MessageType.SESSION_STOP.value,
            data=asdict(self)
        )


@dataclass
class ClientRegisterMessage:
    """Сообщение регистрации клиента"""
    hwid: str
    name: str
    ip_address: str
    mac_address: str

    def to_message(self) -> Message:
        return Message(
            type=MessageType.CLIENT_REGISTER.value,
            data=asdict(self)
        )


@dataclass
class HeartbeatMessage:
    """Сообщение heartbeat от клиента"""
    status: str
    remaining_seconds: Optional[int] = None

    def to_message(self) -> Message:
        return Message(
            type=MessageType.CLIENT_HEARTBEAT.value,
            data=asdict(self)
        )


@dataclass
class SessionTimeUpdateMessage:
    """Сообщение об изменении времени сессии администратором"""
    new_duration_minutes: int
    reason: str = "admin_update"

    def to_message(self) -> Message:
        return Message(
            type=MessageType.SESSION_TIME_UPDATE.value,
            data=asdict(self)
        )


@dataclass
class PasswordUpdateMessage:
    """Сообщение об обновлении пароля администратора"""
    admin_password_hash: str

    def to_message(self) -> Message:
        return Message(
            type=MessageType.PASSWORD_UPDATE.value,
            data=asdict(self)
        )

