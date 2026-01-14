"""
Скрипт настройки LibLocker
Создает конфигурационные файлы из примеров
"""
import os
import shutil
from pathlib import Path


def setup_config_files():
    """Создание конфигурационных файлов"""

    # Конфигурация сервера
    if not os.path.exists('config.ini'):
        if os.path.exists('config.example.ini'):
            shutil.copy('config.example.ini', 'config.ini')
            print("✅ Создан config.ini из config.example.ini")
        else:
            print("❌ Файл config.example.ini не найден")
    else:
        print("ℹ️  config.ini уже существует")

    # Конфигурация клиента
    if not os.path.exists('config.client.ini'):
        if os.path.exists('config.client.example.ini'):
            shutil.copy('config.client.example.ini', 'config.client.ini')
            print("✅ Создан config.client.ini из config.client.example.ini")
        else:
            print("❌ Файл config.client.example.ini не найден")
    else:
        print("ℹ️  config.client.ini уже существует")

    # Создание директорий
    directories = ['data', 'logs']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Создана директория {directory}/")
        else:
            print(f"ℹ️  Директория {directory}/ уже существует")

    print("\n" + "=" * 50)
    print("Настройка завершена!")
    print("=" * 50)
    print("\nТеперь вы можете:")
    print("1. Отредактировать config.ini для настройки сервера")
    print("2. Отредактировать config.client.ini для настройки клиента")
    print("3. Запустить приложения:")
    print("   - python run_server.py")
    print("   - python run_client.py")


if __name__ == "__main__":
    print("LibLocker - Скрипт настройки")
    print("=" * 50)
    setup_config_files()

