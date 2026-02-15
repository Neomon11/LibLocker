#!/usr/bin/env python3
"""
Тест исправления дублирования клиентов
"""

import asyncio
import tempfile
import os
from src.shared.database import Database, ClientModel
from src.server.server import LibLockerServer


async def test_client_duplication():
    """Тест, что клиент не дублируется при повторном подключении"""
    
    # Создаем временную БД
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        db = Database(db_path)
        
        # Создаем тестовый сервер
        server = LibLockerServer(
            host='127.0.0.1',
            port=18765,
            db_path=db_path
        )
        
        # Симулируем первое подключение клиента
        print("\n1. Первое подключение клиента...")
        await server._handle_client_register('sid1', {
            'hwid': 'test-hwid-123',
            'name': 'Test Client',
            'ip_address': '192.168.1.100',
            'mac_address': '00:11:22:33:44:55'
        })
        
        # Проверяем, что клиент добавлен
        session = db.get_session()
        try:
            clients = session.query(ClientModel).all()
            print(f"   Клиентов в БД: {len(clients)}")
            assert len(clients) == 1, f"Expected 1 client, got {len(clients)}"
            print(f"   ✓ Клиент создан: {clients[0].name}")
        finally:
            session.close()
        
        # Проверяем connected_clients
        print(f"   Подключенных клиентов: {len(server.connected_clients)}")
        assert len(server.connected_clients) == 1, f"Expected 1 connected client, got {len(server.connected_clients)}"
        assert 'sid1' in server.connected_clients
        print(f"   ✓ Клиент добавлен в connected_clients")
        
        # Симулируем повторное подключение того же клиента с новым sid
        print("\n2. Повторное подключение того же клиента (новый socket)...")
        await server._handle_client_register('sid2', {
            'hwid': 'test-hwid-123',  # Тот же HWID
            'name': 'Test Client',
            'ip_address': '192.168.1.100',
            'mac_address': '00:11:22:33:44:55'
        })
        
        # Проверяем, что в БД все еще один клиент
        session = db.get_session()
        try:
            clients = session.query(ClientModel).all()
            print(f"   Клиентов в БД: {len(clients)}")
            assert len(clients) == 1, f"Expected 1 client, got {len(clients)} (duplication detected!)"
            print(f"   ✓ Дубликат в БД не создан")
        finally:
            session.close()
        
        # Проверяем, что старое подключение удалено из connected_clients
        print(f"   Подключенных клиентов: {len(server.connected_clients)}")
        assert len(server.connected_clients) == 1, f"Expected 1 connected client, got {len(server.connected_clients)}"
        assert 'sid1' not in server.connected_clients, "Old connection should be removed"
        assert 'sid2' in server.connected_clients, "New connection should be present"
        print(f"   ✓ Старое подключение удалено, новое активно")
        
        # Проверяем, что оба socket ID указывают на одного и того же client_id
        client_id_1 = server.connected_clients['sid2']['client_id']
        session = db.get_session()
        try:
            client = session.query(ClientModel).filter_by(hwid='test-hwid-123').first()
            assert client_id_1 == client.id, "Connected client ID should match database client ID"
            print(f"   ✓ Client ID совпадает: {client_id_1}")
        finally:
            session.close()
        
        # Симулируем подключение другого клиента
        print("\n3. Подключение другого клиента...")
        await server._handle_client_register('sid3', {
            'hwid': 'test-hwid-456',  # Другой HWID
            'name': 'Another Client',
            'ip_address': '192.168.1.101',
            'mac_address': '00:11:22:33:44:66'
        })
        
        # Проверяем, что теперь два клиента в БД
        session = db.get_session()
        try:
            clients = session.query(ClientModel).all()
            print(f"   Клиентов в БД: {len(clients)}")
            assert len(clients) == 2, f"Expected 2 clients, got {len(clients)}"
            print(f"   ✓ Второй клиент создан")
        finally:
            session.close()
        
        # Проверяем connected_clients
        print(f"   Подключенных клиентов: {len(server.connected_clients)}")
        assert len(server.connected_clients) == 2, f"Expected 2 connected clients, got {len(server.connected_clients)}"
        print(f"   ✓ Оба клиента подключены")
        
        print("\n✅ Все тесты пройдены успешно!")
        print("   - Дублирование клиентов исправлено")
        print("   - Повторное подключение корректно обрабатывается")
        print("   - Старые socket ID удаляются при новом подключении")


if __name__ == '__main__':
    asyncio.run(test_client_duplication())
