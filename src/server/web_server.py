"""
Веб-сервер для удаленного управления LibLocker через браузер
"""
import os
import logging
import json
from aiohttp import web
import aiohttp_jinja2
import jinja2
from ..shared.utils import verify_password

logger = logging.getLogger(__name__)


def validate_positive_integer(value, field_name, min_value=1, max_value=None):
    """
    Валидация положительного целого числа.
    
    Args:
        value: Значение для проверки
        field_name: Название поля для сообщения об ошибке
        min_value: Минимальное допустимое значение (по умолчанию 1)
        max_value: Максимальное допустимое значение (опционально)
        
    Returns:
        Кортеж (success: bool, error_message: str or None, validated_value: int or None)
    """
    if value is None:
        return False, f"{field_name} не указан", None
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        return False, f"{field_name} должен быть числом", None
    
    if int_value < min_value:
        return False, f"{field_name} должен быть >= {min_value}", None
    
    if max_value is not None and int_value > max_value:
        return False, f"{field_name} должен быть <= {max_value}", None
    
    return True, None, int_value


class LibLockerWebServer:
    """Веб-сервер для управления LibLocker через браузер"""

    def __init__(self, server, config):
        """
        Инициализация веб-сервера
        
        Args:
            server: Экземпляр LibLockerServer
            config: Конфигурация сервера
        """
        self.server = server
        self.config = config
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # Настройка шаблонов
        template_dir = os.path.join(os.path.dirname(__file__), 'web', 'templates')
        aiohttp_jinja2.setup(self.app, loader=jinja2.FileSystemLoader(template_dir))
        
        # Настройка статических файлов
        static_dir = os.path.join(os.path.dirname(__file__), 'web', 'static')
        self.app.router.add_static('/static/', static_dir, name='static')
        
        # Регистрация маршрутов
        self._setup_routes()

    def _setup_routes(self):
        """Настройка маршрутов веб-сервера"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_post('/api/login', self.login)
        self.app.router.add_get('/api/clients', self.get_clients)
        self.app.router.add_post('/api/start_session', self.start_session)
        self.app.router.add_post('/api/stop_session', self.stop_session)
        self.app.router.add_post('/api/unlock_client', self.unlock_client)
        self.app.router.add_post('/api/logout', self.logout)

    async def index(self, request):
        """Главная страница веб-интерфейса"""
        return aiohttp_jinja2.render_template('index.html', request, {})

    async def login(self, request):
        """Аутентификация пользователя"""
        try:
            data = await request.json()
            password = data.get('password', '')
            
            # Проверяем пароль
            admin_password_hash = self.config.admin_password_hash
            
            if not admin_password_hash:
                return web.json_response({
                    'success': False,
                    'error': 'Пароль администратора не установлен на сервере'
                }, status=401)
            
            if verify_password(password, admin_password_hash):
                # Успешная аутентификация
                # В реальном приложении здесь нужно создать сессию
                return web.json_response({
                    'success': True,
                    'token': 'authenticated'  # Упрощенная версия
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Неверный пароль'
                }, status=401)
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return web.json_response({
                'success': False,
                'error': 'Ошибка сервера'
            }, status=500)

    async def logout(self, request):
        """Выход из системы"""
        return web.json_response({'success': True})

    async def get_clients(self, request):
        """Получить список клиентов"""
        try:
            # Проверяем авторизацию
            auth_header = request.headers.get('Authorization', '')
            if auth_header != 'Bearer authenticated':
                return web.json_response({
                    'success': False,
                    'error': 'Не авторизован'
                }, status=401)
            
            # Получаем клиентов из базы данных
            db_session = self.server.db.get_session()
            try:
                from ..shared.database import ClientModel, SessionModel
                from ..shared.models import ClientStatus
                from datetime import datetime, timedelta
                
                clients = db_session.query(ClientModel).all()
                
                clients_data = []
                for client in clients:
                    # Получаем активную сессию если есть
                    active_session = db_session.query(SessionModel).filter_by(
                        client_id=client.id,
                        status='active'
                    ).first()
                    
                    # Вычисляем оставшееся время для активной сессии
                    remaining_minutes = 0
                    if active_session:
                        if active_session.is_unlimited:
                            remaining_minutes = -1  # -1 означает неограниченное время
                        else:
                            # Вычисляем время окончания сессии
                            end_time = active_session.start_time + timedelta(minutes=active_session.duration_minutes)
                            remaining = end_time - datetime.now()
                            remaining_seconds = remaining.total_seconds()
                            remaining_minutes = max(0, int(remaining_seconds / 60))
                    
                    # Определяем правильный статус клиента
                    # Если есть активная сессия, статус должен быть 'in_session'
                    client_status = client.status
                    if active_session:
                        client_status = ClientStatus.IN_SESSION.value
                    
                    clients_data.append({
                        'id': client.id,
                        'name': client.name,
                        'hwid': client.hwid,
                        'status': client_status,
                        'ip_address': client.ip_address,
                        'last_seen': client.last_seen.isoformat() if client.last_seen else None,
                        'has_session': active_session is not None,
                        'session_info': {
                            'remaining_minutes': remaining_minutes,
                            'is_unlimited': active_session.is_unlimited if active_session else False,
                        } if active_session else None
                    })
                
                return web.json_response({
                    'success': True,
                    'clients': clients_data
                })
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Get clients error: {e}")
            return web.json_response({
                'success': False,
                'error': 'Ошибка получения списка клиентов'
            }, status=500)

    async def start_session(self, request):
        """Начать сессию для клиента"""
        try:
            # Проверяем авторизацию
            auth_header = request.headers.get('Authorization', '')
            if auth_header != 'Bearer authenticated':
                return web.json_response({
                    'success': False,
                    'error': 'Не авторизован'
                }, status=401)
            
            data = await request.json()
            client_id = data.get('client_id')
            duration_minutes = data.get('duration_minutes', 30)
            is_unlimited = data.get('is_unlimited', False)
            
            # Валидация client_id
            success, error, validated_client_id = validate_positive_integer(
                client_id, 'ID клиента', min_value=1
            )
            if not success:
                return web.json_response({
                    'success': False,
                    'error': error
                }, status=400)
            
            # Валидация duration_minutes (если не безлимит)
            if not is_unlimited:
                success, error, validated_duration = validate_positive_integer(
                    duration_minutes, 'Длительность сессии', min_value=1, max_value=1440  # max 24 hours
                )
                if not success:
                    return web.json_response({
                        'success': False,
                        'error': error
                    }, status=400)
                duration_minutes = validated_duration
            
            # Получаем настройки тарификации
            free_mode = self.config.free_mode
            cost_per_hour = 0.0 if free_mode else self.config.hourly_rate
            
            # Запускаем сессию
            success = await self.server.start_session(
                client_id=validated_client_id,
                duration_minutes=duration_minutes,
                is_unlimited=is_unlimited,
                cost_per_hour=cost_per_hour,
                free_mode=free_mode
            )
            
            if success:
                return web.json_response({
                    'success': True,
                    'message': 'Сессия успешно запущена'
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Не удалось запустить сессию'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Start session error: {e}")
            return web.json_response({
                'success': False,
                'error': 'Ошибка запуска сессии'
            }, status=500)

    async def stop_session(self, request):
        """Остановить сессию клиента"""
        try:
            # Проверяем авторизацию
            auth_header = request.headers.get('Authorization', '')
            if auth_header != 'Bearer authenticated':
                return web.json_response({
                    'success': False,
                    'error': 'Не авторизован'
                }, status=401)
            
            data = await request.json()
            client_id = data.get('client_id')
            
            # Валидация client_id
            success, error, validated_client_id = validate_positive_integer(
                client_id, 'ID клиента', min_value=1
            )
            if not success:
                return web.json_response({
                    'success': False,
                    'error': error
                }, status=400)
            
            # Останавливаем сессию
            success = await self.server.stop_session(validated_client_id)
            
            if success:
                return web.json_response({
                    'success': True,
                    'message': 'Сессия успешно остановлена'
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Не удалось остановить сессию'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Stop session error: {e}")
            return web.json_response({
                'success': False,
                'error': 'Ошибка остановки сессии'
            }, status=500)

    async def unlock_client(self, request):
        """Разблокировать клиента"""
        try:
            # Проверяем авторизацию
            auth_header = request.headers.get('Authorization', '')
            if auth_header != 'Bearer authenticated':
                return web.json_response({
                    'success': False,
                    'error': 'Не авторизован'
                }, status=401)
            
            data = await request.json()
            client_id = data.get('client_id')
            
            # Валидация client_id
            success, error, validated_client_id = validate_positive_integer(
                client_id, 'ID клиента', min_value=1
            )
            if not success:
                return web.json_response({
                    'success': False,
                    'error': error
                }, status=400)
            
            # Разблокируем клиента
            success = await self.server.unlock_client(validated_client_id)
            
            if success:
                return web.json_response({
                    'success': True,
                    'message': 'Клиент успешно разблокирован'
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Не удалось разблокировать клиента'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Unlock client error: {e}")
            return web.json_response({
                'success': False,
                'error': 'Ошибка разблокировки клиента'
            }, status=500)

    async def start(self):
        """Запустить веб-сервер"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(
                self.runner, 
                self.config.host, 
                self.config.web_port
            )
            await self.site.start()
            logger.info(f"Web server started on http://{self.config.host}:{self.config.web_port}")
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise

    async def stop(self):
        """Остановить веб-сервер"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Web server stopped")
