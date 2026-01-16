"""
Модуль для автоматического обнаружения сервера LibLocker в локальной сети
Использует UDP broadcast для обнаружения серверов
"""
import socket
import json
import threading
import time
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Константы для обнаружения
DISCOVERY_PORT = 8766  # Порт для UDP broadcast
DISCOVERY_MAGIC = "LIBLOCKER_DISCOVERY"  # Магическая строка для идентификации
DISCOVERY_TIMEOUT = 5  # Таймаут ожидания ответа в секундах


class ServerInfo:
    """Информация о найденном сервере"""
    
    def __init__(self, ip: str, port: int, name: str = "LibLocker Server"):
        self.ip = ip
        self.port = port
        self.name = name
        self.url = f"http://{ip}:{port}"
    
    def __repr__(self):
        return f"ServerInfo(ip={self.ip}, port={self.port}, name={self.name})"
    
    def __eq__(self, other):
        if isinstance(other, ServerInfo):
            return self.ip == other.ip and self.port == other.port
        return False
    
    def __hash__(self):
        return hash((self.ip, self.port))


class ServerDiscovery:
    """Класс для поиска серверов в локальной сети"""
    
    @staticmethod
    def discover_servers(timeout: float = DISCOVERY_TIMEOUT) -> List[ServerInfo]:
        """
        Ищет серверы LibLocker в локальной сети
        
        Args:
            timeout: Таймаут ожидания ответов в секундах
            
        Returns:
            Список найденных серверов
        """
        servers = []
        found_servers = set()  # Для избежания дубликатов
        
        try:
            # Создаем UDP сокет для отправки broadcast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            
            # Формируем запрос обнаружения
            request = {
                'magic': DISCOVERY_MAGIC,
                'type': 'discovery_request',
                'timestamp': time.time()
            }
            request_data = json.dumps(request).encode('utf-8')
            
            logger.info(f"Sending discovery broadcast on port {DISCOVERY_PORT}")
            
            # Отправляем broadcast запрос
            sock.sendto(request_data, ('<broadcast>', DISCOVERY_PORT))
            
            # Слушаем ответы
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        break
                    
                    sock.settimeout(min(remaining_time, 1.0))
                    data, addr = sock.recvfrom(4096)
                    
                    # Парсим ответ
                    response = json.loads(data.decode('utf-8'))
                    
                    # Проверяем, что это валидный ответ от сервера LibLocker
                    if (response.get('magic') == DISCOVERY_MAGIC and 
                        response.get('type') == 'discovery_response'):
                        
                        server_ip = addr[0]
                        server_port = response.get('port', 8765)
                        server_name = response.get('name', 'LibLocker Server')
                        
                        server_info = ServerInfo(server_ip, server_port, server_name)
                        
                        # Добавляем только уникальные серверы
                        if server_info not in found_servers:
                            found_servers.add(server_info)
                            servers.append(server_info)
                            logger.info(f"Found server: {server_info}")
                
                except socket.timeout:
                    continue
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse response: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error receiving response: {e}")
                    continue
            
            sock.close()
            
        except Exception as e:
            logger.error(f"Error during server discovery: {e}")
        
        logger.info(f"Discovery complete. Found {len(servers)} server(s)")
        return servers


class ServerAnnouncer:
    """Класс для анонсирования сервера в локальной сети"""
    
    def __init__(self, port: int = 8765, name: str = "LibLocker Server"):
        self.port = port
        self.name = name
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.sock: Optional[socket.socket] = None
    
    def start(self):
        """Запускает анонсирование сервера"""
        if self.running:
            logger.warning("Server announcer is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._announce_loop, daemon=True)
        self.thread.start()
        logger.info(f"Server announcer started on port {DISCOVERY_PORT}")
    
    def stop(self):
        """Останавливает анонсирование сервера"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error closing announcer socket: {e}")
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("Server announcer stopped")
    
    def _announce_loop(self):
        """Цикл ожидания запросов обнаружения"""
        try:
            # Создаем UDP сокет для приема broadcast
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Для Windows нужно bind к '', для Linux к '<broadcast>'
            try:
                self.sock.bind(('', DISCOVERY_PORT))
            except OSError:
                self.sock.bind(('0.0.0.0', DISCOVERY_PORT))
            
            self.sock.settimeout(1.0)  # Таймаут для проверки флага running
            
            logger.info(f"Listening for discovery requests on port {DISCOVERY_PORT}")
            
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    
                    # Парсим запрос
                    request = json.loads(data.decode('utf-8'))
                    
                    # Проверяем, что это валидный запрос обнаружения
                    if (request.get('magic') == DISCOVERY_MAGIC and 
                        request.get('type') == 'discovery_request'):
                        
                        logger.info(f"Received discovery request from {addr[0]}")
                        
                        # Формируем ответ
                        response = {
                            'magic': DISCOVERY_MAGIC,
                            'type': 'discovery_response',
                            'port': self.port,
                            'name': self.name,
                            'timestamp': time.time()
                        }
                        response_data = json.dumps(response).encode('utf-8')
                        
                        # Отправляем ответ
                        self.sock.sendto(response_data, addr)
                        logger.info(f"Sent discovery response to {addr[0]}")
                
                except socket.timeout:
                    continue
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse discovery request: {e}")
                    continue
                except Exception as e:
                    if self.running:  # Игнорируем ошибки при остановке
                        logger.error(f"Error in announce loop: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Fatal error in announcer: {e}")
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass


def scan_network_for_servers(start_ip: str = None, timeout: float = 0.5, max_ips: int = 254) -> List[ServerInfo]:
    """
    Сканирует локальную сеть на наличие серверов LibLocker методом прямого подключения
    Используется как fallback если UDP broadcast не работает
    
    ВНИМАНИЕ: Этот метод может быть медленным для больших сетей, так как сканирует 
    каждый IP последовательно. Рекомендуется использовать UDP broadcast вместо него.
    
    Args:
        start_ip: Начальный IP адрес (если None, определяется автоматически)
        timeout: Таймаут подключения к каждому IP (в секундах)
        max_ips: Максимальное количество IP для сканирования (по умолчанию 254)
        
    Returns:
        Список найденных серверов
    """
    servers = []
    
    try:
        # Получаем локальный IP
        if start_ip is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Не устанавливает соединение, просто определяет маршрут
                s.connect(('10.255.255.255', 1))
                local_ip = s.getsockname()[0]
            finally:
                s.close()
        else:
            local_ip = start_ip
        
        # Определяем подсеть (первые 3 октета)
        ip_parts = local_ip.split('.')
        subnet = '.'.join(ip_parts[:3])
        
        logger.info(f"Scanning subnet {subnet}.* for servers (up to {max_ips} IPs)")
        logger.warning("Network scan is slow - consider using UDP broadcast discovery instead")
        
        # Сканируем подсеть (ограничено max_ips)
        scan_range = min(max_ips, 254)
        for i in range(1, scan_range + 1):
            if not threading.current_thread().is_alive():
                break
            
            ip = f"{subnet}.{i}"
            
            # Пропускаем свой IP
            if ip == local_ip:
                continue
            
            # Пытаемся подключиться к стандартному порту
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, 8765))
                sock.close()
                
                if result == 0:
                    # Порт открыт, возможно это наш сервер
                    server_info = ServerInfo(ip, 8765, f"LibLocker Server ({ip})")
                    servers.append(server_info)
                    logger.info(f"Found potential server at {ip}:8765")
            
            except Exception:
                continue
        
        logger.info(f"Network scan complete. Found {len(servers)} server(s)")
        
    except Exception as e:
        logger.error(f"Error during network scan: {e}")
    
    return servers
