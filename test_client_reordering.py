#!/usr/bin/env python3
"""
Тест функциональности изменения порядка клиентов
"""

import tempfile
import os
from src.shared.database import Database, ClientModel


def test_client_reordering():
    """Тест изменения порядка отображения клиентов"""
    
    # Создаем временную БД
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        db = Database(db_path)
        
        # Создаем несколько тестовых клиентов
        print("\n1. Создание тестовых клиентов...")
        session = db.get_session()
        try:
            clients_data = [
                {'hwid': 'hwid1', 'name': 'Client A', 'ip': '192.168.1.1'},
                {'hwid': 'hwid2', 'name': 'Client B', 'ip': '192.168.1.2'},
                {'hwid': 'hwid3', 'name': 'Client C', 'ip': '192.168.1.3'},
                {'hwid': 'hwid4', 'name': 'Client D', 'ip': '192.168.1.4'},
            ]
            
            for i, data in enumerate(clients_data, 1):
                client = ClientModel(
                    hwid=data['hwid'],
                    name=data['name'],
                    ip_address=data['ip'],
                    display_order=i
                )
                session.add(client)
            
            session.commit()
            print(f"   ✓ Создано {len(clients_data)} клиентов")
        finally:
            session.close()
        
        # Проверяем начальный порядок
        print("\n2. Проверка начального порядка...")
        session = db.get_session()
        try:
            clients = session.query(ClientModel).order_by(ClientModel.display_order).all()
            print("   Порядок клиентов:")
            for client in clients:
                print(f"     {client.display_order}: {client.name}")
            
            assert clients[0].name == 'Client A'
            assert clients[1].name == 'Client B'
            assert clients[2].name == 'Client C'
            assert clients[3].name == 'Client D'
            print("   ✓ Начальный порядок корректен")
        finally:
            session.close()
        
        # Тест: перемещение Client B вверх (меняется местами с Client A)
        print("\n3. Перемещение Client B вверх (с позиции 2 на позицию 1)...")
        session = db.get_session()
        try:
            client_b = session.query(ClientModel).filter_by(name='Client B').first()
            client_a = session.query(ClientModel).filter_by(name='Client A').first()
            
            # Меняем display_order местами
            temp_order = client_b.display_order
            client_b.display_order = client_a.display_order
            client_a.display_order = temp_order
            
            session.commit()
            print("   ✓ Порядок изменен")
        finally:
            session.close()
        
        # Проверяем новый порядок
        print("\n4. Проверка порядка после перемещения...")
        session = db.get_session()
        try:
            clients = session.query(ClientModel).order_by(ClientModel.display_order).all()
            print("   Новый порядок клиентов:")
            for client in clients:
                print(f"     {client.display_order}: {client.name}")
            
            assert clients[0].name == 'Client B', f"Expected Client B first, got {clients[0].name}"
            assert clients[1].name == 'Client A', f"Expected Client A second, got {clients[1].name}"
            assert clients[2].name == 'Client C'
            assert clients[3].name == 'Client D'
            print("   ✓ Порядок после перемещения корректен")
        finally:
            session.close()
        
        # Тест: перемещение Client C вниз (меняется местами с Client D)
        print("\n5. Перемещение Client C вниз (с позиции 3 на позицию 4)...")
        session = db.get_session()
        try:
            client_c = session.query(ClientModel).filter_by(name='Client C').first()
            client_d = session.query(ClientModel).filter_by(name='Client D').first()
            
            # Меняем display_order местами
            temp_order = client_c.display_order
            client_c.display_order = client_d.display_order
            client_d.display_order = temp_order
            
            session.commit()
            print("   ✓ Порядок изменен")
        finally:
            session.close()
        
        # Проверяем финальный порядок
        print("\n6. Проверка финального порядка...")
        session = db.get_session()
        try:
            clients = session.query(ClientModel).order_by(ClientModel.display_order).all()
            print("   Финальный порядок клиентов:")
            for client in clients:
                print(f"     {client.display_order}: {client.name}")
            
            assert clients[0].name == 'Client B'
            assert clients[1].name == 'Client A'
            assert clients[2].name == 'Client D', f"Expected Client D third, got {clients[2].name}"
            assert clients[3].name == 'Client C', f"Expected Client C fourth, got {clients[3].name}"
            print("   ✓ Финальный порядок корректен")
        finally:
            session.close()
        
        print("\n✅ Все тесты изменения порядка пройдены успешно!")
        print("   - Клиенты корректно создаются с display_order")
        print("   - Порядок клиентов можно изменять")
        print("   - Сортировка по display_order работает правильно")


if __name__ == '__main__':
    test_client_reordering()
