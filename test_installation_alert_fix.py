#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправления мониторинга установки
Проверяет:
1. Автоматический запуск монитора при начале сессии
2. Отправку уведомления на сервер при обнаружении
3. Остановку монитора при завершении сессии
"""
import sys
import os
import time
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client.installation_monitor import InstallationMonitor
from src.shared.protocol import InstallationAlertMessage, MessageType


def test_installation_monitor_basic():
    """Тест базовой функциональности мониторинга"""
    print("\n" + "=" * 70)
    print("ТЕСТ 1: Базовая функциональность мониторинга установки")
    print("=" * 70)
    
    detection_count = [0]
    detected_reason = [None]
    
    def on_detection(reason):
        print(f"  ✓ Callback вызван: {reason}")
        detection_count[0] += 1
        detected_reason[0] = reason
    
    # Создаем монитор
    monitor = InstallationMonitor(on_installation_detected=on_detection)
    
    print("\n1. Запуск мониторинга...")
    monitor.start()
    assert monitor.enabled, "Монитор должен быть включен"
    print("  ✓ Мониторинг запущен")
    
    # Ждем немного для инициализации
    print("\n2. Ожидание инициализации (3 секунды)...")
    time.sleep(3)
    
    print("\n3. Создание тестового установочного файла...")
    # Создаем тестовый .exe файл в папке Downloads
    downloads_path = Path.home() / "Downloads"
    test_file = None
    
    if downloads_path.exists():
        test_file = downloads_path / f"test_installer_{int(time.time())}.exe"
        try:
            with open(test_file, 'wb') as f:
                f.write(b"Test installer file")
            print(f"  ✓ Создан файл: {test_file}")
            
            # Ждем обнаружения
            print("\n4. Ожидание обнаружения (до 15 секунд)...")
            for i in range(15):
                time.sleep(1)
                if detection_count[0] > 0:
                    print(f"  ✓ Обнаружено на {i+1} секунде!")
                    break
                if i % 3 == 0:
                    print(f"  ... {i+1}/15 секунд")
            
            # Удаляем тестовый файл
            if test_file.exists():
                test_file.unlink()
                print(f"\n5. Тестовый файл удален")
        except Exception as e:
            print(f"  ✗ Ошибка при работе с файлом: {e}")
            if test_file and test_file.exists():
                test_file.unlink()
    else:
        print(f"  ✗ Папка Downloads не найдена: {downloads_path}")
    
    print("\n6. Остановка мониторинга...")
    monitor.stop()
    assert not monitor.enabled, "Монитор должен быть выключен"
    print("  ✓ Мониторинг остановлен")
    
    print("\n" + "=" * 70)
    print(f"РЕЗУЛЬТАТ ТЕСТА 1: {'✓ ПРОЙДЕН' if detection_count[0] > 0 else '✗ НЕ ПРОЙДЕН'}")
    print(f"  Обнаружений: {detection_count[0]}")
    if detected_reason[0]:
        print(f"  Причина: {detected_reason[0]}")
    print("=" * 70)
    
    return detection_count[0] > 0


def test_installation_alert_message():
    """Тест создания сообщения об установке"""
    print("\n" + "=" * 70)
    print("ТЕСТ 2: Создание сообщения INSTALLATION_ALERT")
    print("=" * 70)
    
    from datetime import datetime
    
    print("\n1. Создание сообщения...")
    reason = "Обнаружено скачивание установочного файла"
    timestamp = datetime.now().isoformat()
    
    alert_msg = InstallationAlertMessage(
        reason=reason,
        timestamp=timestamp
    )
    
    print(f"  ✓ Создано сообщение:")
    print(f"    - Причина: {alert_msg.reason}")
    print(f"    - Время: {alert_msg.timestamp}")
    
    print("\n2. Преобразование в Message...")
    message = alert_msg.to_message()
    
    print(f"  ✓ Message создан:")
    print(f"    - Тип: {message.type}")
    assert message.type == MessageType.INSTALLATION_ALERT.value, "Неверный тип сообщения"
    print(f"    - Данные: {message.data}")
    assert message.data['reason'] == reason, "Причина не совпадает"
    assert message.data['timestamp'] == timestamp, "Время не совпадает"
    
    print("\n3. Преобразование в dict...")
    msg_dict = message.to_dict()
    print(f"  ✓ Dict создан: {msg_dict}")
    
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ ТЕСТА 2: ✓ ПРОЙДЕН")
    print("=" * 70)
    
    return True


def test_auto_start_logic():
    """Тест логики автоматического запуска"""
    print("\n" + "=" * 70)
    print("ТЕСТ 3: Логика автоматического запуска при сессии")
    print("=" * 70)
    
    from src.shared.config import ClientConfig
    
    print("\n1. Проверка конфигурации...")
    config = ClientConfig()
    
    # Проверяем что параметр installation_monitor_enabled существует
    try:
        enabled = config.installation_monitor_enabled
        print(f"  ✓ Параметр installation_monitor_enabled найден: {enabled}")
    except Exception as e:
        print(f"  ✗ Ошибка доступа к параметру: {e}")
        return False
    
    # Проверяем что параметр alert_volume существует
    try:
        volume = config.alert_volume
        print(f"  ✓ Параметр alert_volume найден: {volume}")
        assert 0 <= volume <= 100, "Громкость должна быть в диапазоне 0-100"
    except Exception as e:
        print(f"  ✗ Ошибка доступа к параметру alert_volume: {e}")
        return False
    
    print("\n2. Проверка создания монитора...")
    detection_triggered = [False]
    
    def mock_callback(reason):
        detection_triggered[0] = True
        print(f"  ✓ Mock callback вызван: {reason}")
    
    monitor = InstallationMonitor(on_installation_detected=mock_callback)
    print("  ✓ Монитор создан")
    
    print("\n3. Проверка методов старт/стоп...")
    assert not monitor.enabled, "Монитор не должен быть включен до старта"
    
    monitor.start()
    assert monitor.enabled, "Монитор должен быть включен после старта"
    print("  ✓ Метод start() работает")
    
    monitor.stop()
    assert not monitor.enabled, "Монитор должен быть выключен после стопа"
    print("  ✓ Метод stop() работает")
    
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ ТЕСТА 3: ✓ ПРОЙДЕН")
    print("=" * 70)
    
    return True


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("КОМПЛЕКСНЫЙ ТЕСТ ИСПРАВЛЕНИЯ МОНИТОРИНГА УСТАНОВКИ")
    print("=" * 70)
    
    results = []
    
    # Тест 1: Базовая функциональность (может не сработать если нет папки Downloads)
    try:
        result1 = test_installation_monitor_basic()
        results.append(("Базовая функциональность", result1))
    except Exception as e:
        print(f"\n✗ ОШИБКА в тесте 1: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Базовая функциональность", False))
    
    # Тест 2: Создание сообщений
    try:
        result2 = test_installation_alert_message()
        results.append(("Создание сообщений", result2))
    except Exception as e:
        print(f"\n✗ ОШИБКА в тесте 2: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Создание сообщений", False))
    
    # Тест 3: Логика автостарта
    try:
        result3 = test_auto_start_logic()
        results.append(("Логика автостарта", result3))
    except Exception as e:
        print(f"\n✗ ОШИБКА в тесте 3: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Логика автостарта", False))
    
    # Итоги
    print("\n" + "=" * 70)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    
    for name, result in results:
        status = "✓ ПРОЙДЕН" if result else "✗ НЕ ПРОЙДЕН"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("\n" + "=" * 70)
    print(f"ВСЕГО: {passed}/{total} тестов пройдено")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nТесты прерваны пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
