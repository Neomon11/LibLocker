"""
WebSocket клиент для LibLocker
Подключение к серверу и обработка команд
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Callable
import socketio

from ..shared.protocol import (
    Message, MessageType, ClientRegisterMessage, HeartbeatMessage,
    ClientSessionStopRequestMessage, InstallationAlertMessage
)
from ..shared.utils import get_hwid, get_mac_address, get_computer_name, get_local_ip
from ..shared.models import ClientStatus

logger = logging.getLogger(__name__)


class LibLockerClient:
    """Клиент LibLocker для подключения к серверу"""

    def __init__(self, server_url: str = "http://localhost:8765"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=0,  # Бесконечные попытки
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=True,
            engineio_logger=True
        )

        # Информация о клиенте
        self.hwid = get_hwid()
        self.name = get_computer_name()
        self.ip_address = get_local_ip()
        self.mac_address = get_mac_address()
        self.client_id: Optional[int] = None

        # Состояние
        self.connected = False
        self.status = ClientStatus.OFFLINE

        # Callbacks для обработки команд
        self.on_session_start: Optional[Callable] = None
        self.on_session_stop: Optional[Callable] = None
        self.on_session_time_update: Optional[Callable] = None
        self.on_session_tariff_update: Optional[Callable] = None
        self.on_password_update: Optional[Callable] = None
        self.on_shutdown: Optional[Callable] = None
        self.on_unlock: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_installation_monitor_toggle: Optional[Callable] = None
        
        # Callback для получения remaining_seconds (должен возвращать Optional[int])
        self.get_remaining_seconds: Optional[Callable[[], Optional[int]]] = None

        # Регистрация обработчиков
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков событий"""

        @self.sio.event
        async def connect():
            """Обработка подключения к серверу"""
            logger.info("Connected to server")
            self.connected = True
            await self._register_client()

            # Уведомляем о подключении
            if self.on_connected:
                try:
                    if asyncio.iscoroutinefunction(self.on_connected):
                        await self.on_connected()
                    else:
                        self.on_connected()
                except Exception as e:
                    logger.error(f"Error calling on_connected: {e}", exc_info=True)

        @self.sio.event
        async def disconnect():
            """Обработка отключения от сервера"""
            logger.info("Disconnected from server")
            self.connected = False
            self.status = ClientStatus.OFFLINE

        @self.sio.event
        async def connection_ack(data):
            """Подтверждение подключения"""
            logger.info(f"Connection acknowledged: {data}")

        @self.sio.event
        async def message(data):
            """Обработка входящего сообщения"""
            try:
                msg = Message.from_dict(data)
                await self._handle_message(msg)
            except Exception as e:
                logger.error(f"Error handling message: {e}")

        @self.sio.event
        async def error(data):
            """Обработка ошибки от сервера"""
            logger.error(f"Server error: {data}")

    async def _register_client(self):
        """Регистрация клиента на сервере"""
        register_msg = ClientRegisterMessage(
            hwid=self.hwid,
            name=self.name,
            ip_address=self.ip_address,
            mac_address=self.mac_address
        )

        await self.sio.emit('message', register_msg.to_message().to_dict())
        logger.info(f"Client registered: {self.name} (HWID: {self.hwid})")
        self.status = ClientStatus.ONLINE

    async def _handle_message(self, msg: Message):
        """Обработка сообщения от сервера"""
        msg_type = msg.type

        if msg_type == MessageType.SESSION_START.value:
            await self._handle_session_start(msg.data)
        elif msg_type == MessageType.SESSION_STOP.value:
            await self._handle_session_stop(msg.data)
        elif msg_type == MessageType.SESSION_TIME_UPDATE.value:
            await self._handle_session_time_update(msg.data)
        elif msg_type == MessageType.SESSION_TARIFF_UPDATE.value:
            await self._handle_session_tariff_update(msg.data)
        elif msg_type == MessageType.PASSWORD_UPDATE.value:
            await self._handle_password_update(msg.data)
        elif msg_type == MessageType.SHUTDOWN.value:
            await self._handle_shutdown()
        elif msg_type == MessageType.UNLOCK.value:
            await self._handle_unlock()
        elif msg_type == MessageType.INSTALLATION_MONITOR_TOGGLE.value:
            await self._handle_installation_monitor_toggle(msg.data)
        elif msg_type == MessageType.ACK.value:
            if 'client_id' in msg.data:
                self.client_id = msg.data['client_id']
                logger.info(f"Client ID assigned: {self.client_id}")
        elif msg_type == MessageType.PONG.value:
            logger.debug("Pong received")
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_session_start(self, data: dict):
        """Обработка команды начала сессии"""
        logger.info("=" * 60)
        logger.info(f"[Client] SESSION_START received")
        logger.info(f"[Client] Data: {data}")
        logger.info("=" * 60)
        self.status = ClientStatus.IN_SESSION

        if self.on_session_start:
            try:
                logger.info(f"[Client] Calling on_session_start callback")
                if asyncio.iscoroutinefunction(self.on_session_start):
                    await self.on_session_start(data)
                else:
                    self.on_session_start(data)
                logger.info(f"[Client] on_session_start callback completed")
            except Exception as e:
                logger.error(f"Error calling on_session_start: {e}", exc_info=True)
        else:
            logger.warning(f"[Client] on_session_start callback is not set!")

    async def _handle_session_stop(self, data: dict):
        """Обработка команды остановки сессии"""
        logger.info(f"Session stop command received: {data}")
        self.status = ClientStatus.ONLINE

        if self.on_session_stop:
            try:
                if asyncio.iscoroutinefunction(self.on_session_stop):
                    await self.on_session_stop(data)
                else:
                    self.on_session_stop(data)
            except Exception as e:
                logger.error(f"Error calling on_session_stop: {e}", exc_info=True)

    async def _handle_session_time_update(self, data: dict):
        """Обработка команды обновления времени сессии"""
        logger.info(f"Session time update command received: {data}")

        if self.on_session_time_update:
            try:
                if asyncio.iscoroutinefunction(self.on_session_time_update):
                    await self.on_session_time_update(data)
                else:
                    self.on_session_time_update(data)
            except Exception as e:
                logger.error(f"Error calling on_session_time_update: {e}", exc_info=True)

    async def _handle_session_tariff_update(self, data: dict):
        """Обработка команды обновления тарификации сессии"""
        logger.info(f"Session tariff update command received: {data}")

        if self.on_session_tariff_update:
            try:
                if asyncio.iscoroutinefunction(self.on_session_tariff_update):
                    await self.on_session_tariff_update(data)
                else:
                    self.on_session_tariff_update(data)
            except Exception as e:
                logger.error(f"Error calling on_session_tariff_update: {e}", exc_info=True)

    async def _handle_password_update(self, data: dict):
        """Обработка команды обновления пароля администратора"""
        logger.info(f"Password update command received")
        
        if self.on_password_update:
            try:
                if asyncio.iscoroutinefunction(self.on_password_update):
                    await self.on_password_update(data)
                else:
                    self.on_password_update(data)
            except Exception as e:
                logger.error(f"Error calling on_password_update: {e}", exc_info=True)

    async def _handle_shutdown(self):
        """Обработка команды выключения"""
        logger.info("Shutdown command received")

        if self.on_shutdown:
            try:
                if asyncio.iscoroutinefunction(self.on_shutdown):
                    await self.on_shutdown()
                else:
                    self.on_shutdown()
            except Exception as e:
                logger.error(f"Error calling on_shutdown: {e}", exc_info=True)

    async def _handle_unlock(self):
        """Обработка команды разблокировки"""
        logger.info("Unlock command received")

        if self.on_unlock:
            try:
                if asyncio.iscoroutinefunction(self.on_unlock):
                    await self.on_unlock()
                else:
                    self.on_unlock()
            except Exception as e:
                logger.error(f"Error calling on_unlock: {e}", exc_info=True)

    async def _handle_installation_monitor_toggle(self, data: dict):
        """Обработка команды включения/выключения мониторинга установки"""
        enabled = data.get('enabled', False)
        alert_volume = data.get('alert_volume', 80)  # Громкость с сервера
        logger.info(f"Installation monitor toggle command received: enabled={enabled}, alert_volume={alert_volume}")

        if self.on_installation_monitor_toggle:
            try:
                if asyncio.iscoroutinefunction(self.on_installation_monitor_toggle):
                    await self.on_installation_monitor_toggle(enabled, alert_volume)
                else:
                    self.on_installation_monitor_toggle(enabled, alert_volume)
            except Exception as e:
                logger.error(f"Error calling on_installation_monitor_toggle: {e}", exc_info=True)

    async def send_heartbeat(self, remaining_seconds: Optional[int] = None):
        """Отправка heartbeat на сервер"""
        if not self.connected:
            return

        heartbeat_msg = HeartbeatMessage(
            status=self.status.value,
            remaining_seconds=remaining_seconds
        )

        await self.sio.emit('message', heartbeat_msg.to_message().to_dict())
        logger.debug("Heartbeat sent")

    async def request_session_stop(self):
        """Запрос остановки сессии от клиента"""
        if not self.connected:
            logger.warning("Cannot request session stop: not connected to server")
            return
        
        stop_request_msg = ClientSessionStopRequestMessage(reason='user_request')
        await self.sio.emit('message', stop_request_msg.to_message().to_dict())
        logger.info("Session stop request sent to server")

    async def send_installation_alert(self, reason: str):
        """Отправка уведомления об обнаружении установки на сервер"""
        if not self.connected:
            logger.warning("Cannot send installation alert: not connected to server")
            return
        
        alert_msg = InstallationAlertMessage(
            reason=reason,
            timestamp=datetime.now().isoformat()
        )
        await self.sio.emit('message', alert_msg.to_message().to_dict())
        logger.info(f"Installation alert sent to server: {reason}")

    async def connect(self):
        """Подключение к серверу"""
        try:
            await self.sio.connect(self.server_url)
            logger.info(f"Connecting to {self.server_url}")
        except Exception as e:
            logger.error(f"Error connecting to server: {e}")

    async def disconnect(self):
        """Отключение от сервера"""
        await self.sio.disconnect()

    async def run(self):
        """Запуск клиента"""
        # Пытаемся подключиться, если не получается - повторяем каждые 10 секунд
        connection_retry_interval = 10  # секунд
        
        # Отправка heartbeat каждые 5 секунд
        try:
            while True:
                # Если не подключены, пытаемся подключиться
                if not self.connected:
                    await self.connect()
                    if not self.connected:
                        # Если подключение не удалось, ждем перед следующей попыткой
                        logger.info(f"Connection failed, retrying in {connection_retry_interval} seconds...")
                        await asyncio.sleep(connection_retry_interval)
                        continue
                
                # Если подключены, отправляем heartbeat
                if self.connected:
                    # Получаем remaining_seconds из callback если установлен
                    remaining_seconds = None
                    if self.get_remaining_seconds:
                        try:
                            remaining_seconds = self.get_remaining_seconds()
                        except Exception as e:
                            callback_name = getattr(self.get_remaining_seconds, '__name__', 'unknown')
                            logger.error(f"Error getting remaining_seconds from callback {callback_name}: {e}")
                    
                    await self.send_heartbeat(remaining_seconds)
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("Client stopping...")
        finally:
            await self.disconnect()


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Запуск клиента
    client = LibLockerClient()
    asyncio.run(client.run())

