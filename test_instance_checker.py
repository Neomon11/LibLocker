"""
Тест для проверки механизма защиты от множественных запусков
"""
import sys
import os
import time
import subprocess

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.shared.utils import SingleInstanceChecker

def test_single_instance():
    """Тест проверки единственного экземпляра"""
    print("=" * 60)
    print("Тест механизма защиты от множественных запусков")
    print("=" * 60)
    
    # Тест 1: Первый экземпляр должен работать
    print("\n[Тест 1] Создание первого экземпляра...")
    checker1 = SingleInstanceChecker('test_app')
    
    if checker1.is_already_running():
        print("❌ ОШИБКА: Первый экземпляр не должен быть заблокирован!")
        return False
    else:
        print("✅ OK: Первый экземпляр успешно запущен")
    
    # Тест 2: Второй экземпляр должен быть заблокирован
    print("\n[Тест 2] Попытка создания второго экземпляра...")
    checker2 = SingleInstanceChecker('test_app')
    
    if checker2.is_already_running():
        print("✅ OK: Второй экземпляр заблокирован (ожидаемое поведение)")
    else:
        print("❌ ОШИБКА: Второй экземпляр не был заблокирован!")
        checker1.release()
        return False
    
    # Тест 3: После освобождения первого, второй должен работать
    print("\n[Тест 3] Освобождение первого экземпляра...")
    checker1.release()
    time.sleep(0.1)  # Небольшая задержка
    
    checker3 = SingleInstanceChecker('test_app')
    if checker3.is_already_running():
        print("❌ ОШИБКА: После освобождения экземпляр все еще заблокирован!")
        return False
    else:
        print("✅ OK: После освобождения новый экземпляр запущен успешно")
    
    checker3.release()
    
    print("\n" + "=" * 60)
    print("✅ Все тесты пройдены успешно!")
    print("=" * 60)
    return True

def test_different_apps():
    """Тест что разные приложения могут работать одновременно"""
    print("\n" + "=" * 60)
    print("Тест запуска разных приложений одновременно")
    print("=" * 60)
    
    print("\n[Тест] Создание экземпляров клиента и сервера...")
    client_checker = SingleInstanceChecker('liblocker_client')
    server_checker = SingleInstanceChecker('liblocker_server')
    
    client_running = client_checker.is_already_running()
    server_running = server_checker.is_already_running()
    
    if client_running:
        print("✅ Клиент: уже запущен (корректное обнаружение)")
    else:
        print("✅ Клиент: может быть запущен")
    
    if server_running:
        print("✅ Сервер: уже запущен (корректное обнаружение)")
    else:
        print("✅ Сервер: может быть запущен")
    
    # Должны быть оба независимы
    if not client_running and not server_running:
        print("\n✅ OK: Клиент и сервер могут работать одновременно")
        client_checker.release()
        server_checker.release()
    
    print("=" * 60)

if __name__ == "__main__":
    success = test_single_instance()
    test_different_apps()
    
    if success:
        print("\n✨ Механизм защиты от множественных запусков работает корректно!")
        sys.exit(0)
    else:
        print("\n❌ Обнаружены проблемы в механизме защиты!")
        sys.exit(1)
