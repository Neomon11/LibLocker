#!/usr/bin/env python3
"""
Тестовый скрипт для проверки мониторинга установки
"""
import sys
import os
import time
import tempfile
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client.installation_monitor import InstallationMonitor

def test_installation_monitor():
    """Тест мониторинга установки"""
    print("=" * 60)
    print("Тест мониторинга установки программ")
    print("=" * 60)
    
    detection_count = [0]
    
    def on_detection(reason):
        print(f"\n🚨 ОБНАРУЖЕНИЕ: {reason}")
        detection_count[0] += 1
    
    # Создаем монитор
    monitor = InstallationMonitor(on_installation_detected=on_detection)
    
    print("\n1. Запуск мониторинга...")
    monitor.start()
    print("✓ Мониторинг запущен")
    
    # Ждем немного для инициализации
    time.sleep(3)
    
    print("\n2. Создание тестового установочного файла...")
    # Создаем тестовый .exe файл в папке Downloads
    downloads_path = Path.home() / "Downloads"
    if downloads_path.exists():
        test_file = downloads_path / "test_installer.exe"
        try:
            with open(test_file, 'wb') as f:
                f.write(b"Test installer file")
            print(f"✓ Создан файл: {test_file}")
            
            # Ждем обнаружения
            print("\n3. Ожидание обнаружения (10 секунд)...")
            for i in range(10):
                time.sleep(1)
                print(f"   {i+1}/10 секунд...")
                if detection_count[0] > 0:
                    break
            
            # Удаляем тестовый файл
            if test_file.exists():
                test_file.unlink()
                print(f"✓ Удален файл: {test_file}")
        except Exception as e:
            print(f"✗ Ошибка при работе с файлом: {e}")
    else:
        print(f"✗ Папка Downloads не найдена: {downloads_path}")
    
    print("\n4. Остановка мониторинга...")
    monitor.stop()
    print("✓ Мониторинг остановлен")
    
    print("\n" + "=" * 60)
    print(f"Результат: обнаружено {detection_count[0]} установок")
    if detection_count[0] > 0:
        print("✓ ТЕСТ ПРОЙДЕН")
    else:
        print("⚠ ТЕСТ НЕ ПРОЙДЕН (обнаружений не было)")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_installation_monitor()
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
    except Exception as e:
        print(f"\n\n✗ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
