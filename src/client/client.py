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
    Message, MessageType, ClientRegisterMessage, HeartbeatMessage
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
        self.on_shutdown: Optional[Callable] = None
        self.on_unlock: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None

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
        elif msg_type == MessageType.SHUTDOWN.value:
            await self._handle_shutdown()
        elif msg_type == MessageType.UNLOCK.value:
            await self._handle_unlock()
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
        logger.info(f"Session start command received: {data}")
        self.status = ClientStatus.IN_SESSION

        if self.on_session_start:
            try:
                if asyncio.iscoroutinefunction(self.on_session_start):
                    await self.on_session_start(data)
                else:
                    self.on_session_start(data)
            except Exception as e:
                logger.error(f"Error calling on_session_start: {e}", exc_info=True)

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
        await self.connect()

        # Отправка heartbeat каждые 5 секунд
        try:
            while True:
                if self.connected:
                    await self.send_heartbeat()
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

