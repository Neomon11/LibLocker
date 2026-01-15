"""
WebSocket сервер для LibLocker
Управление подключениями клиентов и обработка сообщений
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import socketio
from aiohttp import web

from ..shared.protocol import Message, MessageType
from ..shared.models import Client, ClientStatus
from ..shared.database import Database, ClientModel, SessionModel

logger = logging.getLogger(__name__)


class LibLockerServer:
    """Основной класс сервера LibLocker"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765, db_path: str = "data/liblocker.db"):
        self.host = host
        self.port = port
        self.db = Database(db_path)

        # WebSocket сервер
        self.sio = socketio.AsyncServer(
            async_mode='aiohttp',
            cors_allowed_origins='*',
            logger=True,
            engineio_logger=True
        )
        self.app = web.Application()
        self.sio.attach(self.app)

        # Подключенные клиенты {sid: client_info}
        self.connected_clients: Dict[str, dict] = {}

        # Регистрация обработчиков событий
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков WebSocket событий"""

        @self.sio.event
        async def connect(sid, environ):
            """Обработка подключения клиента"""
            logger.info(f"Client connecting: {sid}")
            await self.sio.emit('connection_ack', {'status': 'ok'}, room=sid)

        @self.sio.event
        async def disconnect(sid):
            """Обработка отключения клиента"""
            logger.info(f"Client disconnected: {sid}")
            await self._handle_disconnect(sid)

        @self.sio.event
        async def message(sid, data):
            """Обработка входящего сообщения"""
            try:
                msg = Message.from_dict(data)
                await self._handle_message(sid, msg)
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await self.sio.emit('error', {'message': str(e)}, room=sid)

    async def _handle_message(self, sid: str, msg: Message):
        """Обработка сообщения от клиента"""
        msg_type = msg.type

        if msg_type == MessageType.CLIENT_REGISTER.value:
            await self._handle_client_register(sid, msg.data)
        elif msg_type == MessageType.CLIENT_HEARTBEAT.value:
            await self._handle_heartbeat(sid, msg.data)
        elif msg_type == MessageType.SESSION_SYNC.value:
            await self._handle_session_sync(sid, msg.data)
        elif msg_type == MessageType.CLIENT_SESSION_STOP_REQUEST.value:
            await self._handle_client_session_stop_request(sid, msg.data)
        elif msg_type == MessageType.PING.value:
            await self.sio.emit('message', {
                'type': MessageType.PONG.value,
                'data': {},
                'timestamp': datetime.now().isoformat()
            }, room=sid)
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_client_register(self, sid: str, data: dict):
        """Обработка регистрации клиента"""
        hwid = data.get('hwid')
        name = data.get('name')
        ip_address = data.get('ip_address')
        mac_address = data.get('mac_address')

        logger.info(f"Registering client: {name} (HWID: {hwid})")

        # Сохранение в БД
        db_session = self.db.get_session()
        try:
            # Проверяем, существует ли клиент
            client = db_session.query(ClientModel).filter_by(hwid=hwid).first()

            if client:
                # Обновляем существующего клиента
                client.name = name
                client.ip_address = ip_address
                client.mac_address = mac_address
                client.status = ClientStatus.ONLINE.value
                client.last_seen = datetime.now()
            else:
                # Создаем нового клиента
                client = ClientModel(
                    hwid=hwid,
                    name=name,
                    ip_address=ip_address,
                    mac_address=mac_address,
                    status=ClientStatus.ONLINE.value,
                    last_seen=datetime.now()
                )
                db_session.add(client)

            db_session.commit()

            # Сохраняем информацию о подключении
            self.connected_clients[sid] = {
                'client_id': client.id,
                'hwid': hwid,
                'name': name
            }

            # Отправляем подтверждение
            await self.sio.emit('message', {
                'type': MessageType.ACK.value,
                'data': {'client_id': client.id, 'status': 'registered'},
                'timestamp': datetime.now().isoformat()
            }, room=sid)

            logger.info(f"Client registered: {name} (ID: {client.id})")

        except Exception as e:
            logger.error(f"Error registering client: {e}")
            db_session.rollback()
        finally:
            db_session.close()

    async def _handle_heartbeat(self, sid: str, data: dict):
        """Обработка heartbeat от клиента"""
        if sid in self.connected_clients:
            client_info = self.connected_clients[sid]

            # Обновляем last_seen в БД
            db_session = self.db.get_session()
            try:
                client = db_session.query(ClientModel).filter_by(
                    id=client_info['client_id']
                ).first()
                if client:
                    client.last_seen = datetime.now()
                    client.status = data.get('status', ClientStatus.ONLINE.value)
                    db_session.commit()
            except Exception as e:
                logger.error(f"Error updating heartbeat: {e}")
                db_session.rollback()
            finally:
                db_session.close()

    async def _handle_session_sync(self, sid: str, data: dict):
        """Обработка синхронизации сессии (для автономного режима)"""
        logger.info(f"Session sync from {sid}: {data}")
        # TODO: Реализовать синхронизацию автономных сессий

    async def _handle_client_session_stop_request(self, sid: str, data: dict):
        """Обработка запроса остановки сессии от клиента"""
        logger.info(f"Client session stop request from {sid}: {data}")
        
        # Находим client_id по sid
        if sid not in self.connected_clients:
            logger.error(f"Client {sid} not found in connected_clients")
            return
        
        client_id = self.connected_clients[sid].get('client_id')
        if not client_id:
            logger.error(f"Client ID not found for sid {sid}")
            return
        
        # Останавливаем сессию для этого клиента
        logger.info(f"Stopping session for client {client_id} by user request")
        await self.stop_session(client_id)

    async def _handle_disconnect(self, sid: str):
        """Обработка отключения клиента"""
        if sid in self.connected_clients:
            client_info = self.connected_clients[sid]

            # Обновляем статус в БД
            db_session = self.db.get_session()
            try:
                client = db_session.query(ClientModel).filter_by(
                    id=client_info['client_id']
                ).first()
                if client:
                    client.status = ClientStatus.OFFLINE.value
                    client.last_seen = datetime.now()
                    db_session.commit()
            except Exception as e:
                logger.error(f"Error updating disconnect: {e}")
                db_session.rollback()
            finally:
                db_session.close()

            # Удаляем из списка подключенных
            del self.connected_clients[sid]

    async def start_session(self, client_id: int, duration_minutes: int = 0,
                          is_unlimited: bool = False, cost_per_hour: float = 0.0,
                          free_mode: bool = True) -> bool:
        """Начать сессию для клиента"""
        logger.info(f"Starting session for client {client_id}")

        # Находим sid клиента
        client_sid = None
        for sid, info in self.connected_clients.items():
            if info['client_id'] == client_id:
                client_sid = sid
                break

        if not client_sid:
            logger.error(f"Client {client_id} not connected")
            return False

        # Создаем сессию в БД
        db_session = self.db.get_session()
        try:
            session = SessionModel(
                client_id=client_id,
                duration_minutes=duration_minutes,
                is_unlimited=is_unlimited,
                cost=0.0,
                cost_per_hour=cost_per_hour,
                free_mode=free_mode,
                status='active'
            )
            db_session.add(session)
            db_session.commit()
            session_id = session.id

            # Отправляем команду клиенту
            from ..shared.protocol import SessionStartMessage

            start_msg = SessionStartMessage(
                duration_minutes=duration_minutes,
                is_unlimited=is_unlimited,
                cost_per_hour=cost_per_hour,
                free_mode=free_mode
            )

            message_dict = start_msg.to_message().to_dict()
            message_dict['data']['session_id'] = session_id  # Добавляем session_id

            await self.sio.emit('message', message_dict, room=client_sid)

            logger.info(f"Session {session_id} started for client {client_id}")
            return True

        except Exception as e:
            logger.error(f"Error starting session: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()

    async def stop_session(self, client_id: int) -> bool:
        """Остановить сессию для клиента"""
        logger.info(f"Stopping session for client {client_id}")

        # Находим sid клиента
        client_sid = None
        for sid, info in self.connected_clients.items():
            if info['client_id'] == client_id:
                client_sid = sid
                break

        if not client_sid:
            logger.error(f"Client {client_id} not connected")
            return False

        # Отправляем команду остановки
        from ..shared.protocol import SessionStopMessage

        stop_msg = SessionStopMessage(reason='manual')
        await self.sio.emit('message', stop_msg.to_message().to_dict(), room=client_sid)

        # Завершаем активную сессию в БД
        db_session = self.db.get_session()
        try:
            active_session = db_session.query(SessionModel).filter_by(
                client_id=client_id,
                status='active'
            ).first()

            if active_session:
                active_session.end_time = datetime.now()
                active_session.status = 'completed'
                # Расчет фактической длительности
                duration = (active_session.end_time - active_session.start_time).total_seconds() / 60
                active_session.actual_duration = int(duration)
                
                # Расчет стоимости сессии
                if not active_session.free_mode and active_session.cost_per_hour > 0:
                    # Валидация значений
                    if duration < 0:
                        logger.warning(f"Negative duration detected: {duration} minutes, setting to 0")
                        duration = 0
                    if active_session.cost_per_hour < 0:
                        logger.warning(f"Negative cost_per_hour detected: {active_session.cost_per_hour}, setting to 0")
                        active_session.cost_per_hour = 0
                    
                    # Переводим длительность в часы и умножаем на стоимость
                    duration_hours = duration / 60.0
                    active_session.cost = duration_hours * active_session.cost_per_hour
                    logger.info(f"Session cost calculated: {active_session.cost:.2f} руб. ({duration:.1f} min at {active_session.cost_per_hour} руб./hour)")
                else:
                    active_session.cost = 0.0
                    logger.info(f"Session is free (free_mode={active_session.free_mode})")
                
                db_session.commit()
                logger.info(f"Session {active_session.id} stopped")

            return True
        except Exception as e:
            logger.error(f"Error stopping session: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()

    async def update_session_time(self, client_id: int, new_duration_minutes: int) -> bool:
        """Обновить время сессии для клиента"""
        logger.info(f"Updating session time for client {client_id} to {new_duration_minutes} minutes")

        # Находим sid клиента
        client_sid = None
        for sid, info in self.connected_clients.items():
            if info['client_id'] == client_id:
                client_sid = sid
                break

        if not client_sid:
            logger.error(f"Client {client_id} not connected")
            return False

        # Обновляем сессию в БД
        db_session = self.db.get_session()
        try:
            active_session = db_session.query(SessionModel).filter_by(
                client_id=client_id,
                status='active'
            ).first()

            if not active_session:
                logger.error(f"No active session for client {client_id}")
                return False

            # Обновляем длительность
            active_session.duration_minutes = new_duration_minutes
            db_session.commit()

            # Отправляем команду клиенту
            from ..shared.protocol import SessionTimeUpdateMessage

            update_msg = SessionTimeUpdateMessage(
                new_duration_minutes=new_duration_minutes,
                reason="admin_update"
            )

            await self.sio.emit('message', update_msg.to_message().to_dict(), room=client_sid)

            logger.info(f"Session time updated for client {client_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating session time: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()

    async def shutdown_client(self, client_id: int) -> bool:
        """Отправить команду выключения клиента"""
        logger.info(f"Shutting down client {client_id}")

        # Находим sid клиента
        client_sid = None
        for sid, info in self.connected_clients.items():
            if info['client_id'] == client_id:
                client_sid = sid
                break

        if not client_sid:
            logger.error(f"Client {client_id} not connected")
            return False

        # Отправляем команду выключения
        from ..shared.protocol import Message

        shutdown_msg = Message(
            type=MessageType.SHUTDOWN.value,
            data={},
            timestamp=datetime.now().isoformat()
        )
        await self.sio.emit('message', shutdown_msg.to_dict(), room=client_sid)

        return True

    async def broadcast_password_update(self, admin_password_hash: str):
        """Отправить обновление пароля администратора всем подключенным клиентам"""
        from ..shared.protocol import PasswordUpdateMessage
        
        logger.info(f"Broadcasting password update to {len(self.connected_clients)} connected clients")
        
        password_msg = PasswordUpdateMessage(
            admin_password_hash=admin_password_hash
        )
        
        # Отправляем всем подключенным клиентам
        for sid in self.connected_clients.keys():
            try:
                await self.sio.emit('message', password_msg.to_message().to_dict(), room=sid)
                logger.info(f"Password update sent to client {sid}")
            except Exception as e:
                logger.error(f"Error sending password update to {sid}: {e}")

    def get_connected_clients(self) -> list:
        """Получить список подключенных клиентов"""
        return [
            {
                'sid': sid,
                'client_id': info['client_id'],
                'name': info['name'],
                'hwid': info['hwid']
            }
            for sid, info in self.connected_clients.items()
        ]

    async def run(self):
        """Запуск сервера"""
        logger.info(f"Starting LibLocker Server on {self.host}:{self.port}")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info("Server started successfully")

        # Держим сервер запущенным
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
        finally:
            await runner.cleanup()
            self.db.close()


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Запуск сервера
    server = LibLockerServer()
    asyncio.run(server.run())

