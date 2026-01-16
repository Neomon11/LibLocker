#!/usr/bin/env python3
"""
Тестовый скрипт для проверки синхронизации настроек модуля антиустановки
"""
import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.shared.config import ServerConfig, ClientConfig
from src.shared.protocol import InstallationMonitorToggleMessage

def test_server_config():
    """Тест конфигурации сервера"""
    print("=" * 60)
    print("Тест конфигурации модуля антиустановки на сервере")
    print("=" * 60)
    
    try:
        config = ServerConfig()
        print("\n✓ Конфигурация сервера загружена успешно")
        
        # Проверяем настройки по умолчанию
        print(f"  - Installation monitor enabled: {config.installation_monitor_enabled}")
        print(f"  - Alert volume: {config.installation_monitor_alert_volume}")
        
        # Изменяем настройки
        print("\nИзменение настроек...")
        config.installation_monitor_enabled = True
        config.installation_monitor_alert_volume = 75
        config.save()
        print("✓ Настройки сохранены")
        
        # Перезагружаем и проверяем
        print("\nПерезагрузка конфигурации...")
        config2 = ServerConfig()
        assert config2.installation_monitor_enabled == True, "Enabled должен быть True"
        assert config2.installation_monitor_alert_volume == 75, "Volume должен быть 75"
        print("✓ Настройки сохранились корректно")
        
        # Восстанавливаем значения по умолчанию
        config2.installation_monitor_enabled = False
        config2.installation_monitor_alert_volume = 80
        config2.save()
        
        return True
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_client_config():
    """Тест конфигурации клиента"""
    print("\n" + "=" * 60)
    print("Тест конфигурации клиента")
    print("=" * 60)
    
    try:
        config = ClientConfig()
        print("\n✓ Конфигурация клиента загружена успешно")
        print(f"  - Installation monitor enabled: {config.installation_monitor_enabled}")
        print(f"  - Alert volume: {config.alert_volume}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_protocol_message():
    """Тест протокола передачи настроек"""
    print("\n" + "=" * 60)
    print("Тест протокола синхронизации настроек")
    print("=" * 60)
    
    try:
        # Создаем сообщение с настройками
        msg = InstallationMonitorToggleMessage(enabled=True, alert_volume=65)
        print("\n✓ Сообщение создано")
        print(f"  - Enabled: {msg.enabled}")
        print(f"  - Alert volume: {msg.alert_volume}")
        
        # Конвертируем в dict
        msg_dict = msg.to_message().to_dict()
        print("\n✓ Сообщение преобразовано в dict:")
        print(f"  - Type: {msg_dict['type']}")
        print(f"  - Data: {msg_dict['data']}")
        
        # Проверяем, что данные корректны
        assert msg_dict['type'] == 'installation_monitor_toggle'
        assert msg_dict['data']['enabled'] == True
        assert msg_dict['data']['alert_volume'] == 65
        print("\n✓ Все поля присутствуют и корректны")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 60)
    print("ЗАПУСК ТЕСТОВ СИНХРОНИЗАЦИИ НАСТРОЕК")
    print("=" * 60)
    
    results = {
        "Server Config": test_server_config(),
        "Client Config": test_client_config(),
        "Protocol Message": test_protocol_message()
    }
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("✗ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
