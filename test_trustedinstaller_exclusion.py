#!/usr/bin/env python3
"""
Тест для проверки, что TrustedInstaller не вызывает ложных срабатываний
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client.installation_monitor import InstallationMonitor


class TestTrustedInstallerExclusion(unittest.TestCase):
    """Тесты для проверки исключения системных процессов"""
    
    def setUp(self):
        """Настройка теста"""
        self.detection_called = False
        self.detection_reason = None
        
        def on_detection(reason):
            self.detection_called = True
            self.detection_reason = reason
        
        self.monitor = InstallationMonitor(on_installation_detected=on_detection)
    
    def tearDown(self):
        """Очистка после теста"""
        if self.monitor.enabled:
            self.monitor.stop()
    
    def test_trustedinstaller_in_exclusion_list(self):
        """Проверка, что trustedinstaller.exe в списке исключений"""
        self.assertIn('trustedinstaller.exe', InstallationMonitor.SYSTEM_PROCESS_EXCLUSIONS)
        print("✓ trustedinstaller.exe находится в списке исключений")
    
    def test_tiworker_in_exclusion_list(self):
        """Проверка, что tiworker.exe в списке исключений"""
        self.assertIn('tiworker.exe', InstallationMonitor.SYSTEM_PROCESS_EXCLUSIONS)
        print("✓ tiworker.exe находится в списке исключений")
    
    @patch('psutil.process_iter')
    def test_trustedinstaller_not_detected(self, mock_process_iter):
        """Тест: TrustedInstaller.exe не должен вызывать тревогу"""
        
        # Создаем мок процесса TrustedInstaller
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.name.return_value = "TrustedInstaller.exe"
        mock_proc.create_time.return_value = datetime.now().timestamp()
        
        # Возвращаем мок процесс
        mock_process_iter.return_value = [mock_proc]
        
        # Проверяем процессы
        result = self.monitor._check_installer_processes()
        
        # TrustedInstaller НЕ должен быть обнаружен как установщик
        self.assertFalse(result, "TrustedInstaller.exe НЕ должен триггерить тревогу")
        print("✓ TrustedInstaller.exe правильно игнорируется")
    
    @patch('psutil.process_iter')
    def test_legitimate_installer_detected(self, mock_process_iter):
        """Тест: Настоящий установщик должен быть обнаружен"""
        
        # Создаем мок настоящего установщика
        mock_proc = MagicMock()
        mock_proc.pid = 54321
        mock_proc.name.return_value = "setup.exe"
        mock_proc.create_time.return_value = datetime.now().timestamp()
        
        # Возвращаем мок процесс
        mock_process_iter.return_value = [mock_proc]
        
        # Проверяем процессы
        result = self.monitor._check_installer_processes()
        
        # setup.exe ДОЛЖЕН быть обнаружен
        self.assertTrue(result, "setup.exe должен быть обнаружен как установщик")
        print("✓ setup.exe правильно обнаружен как установщик")
    
    @patch('psutil.process_iter')
    def test_mixed_processes(self, mock_process_iter):
        """Тест: Смешанные процессы - системные и установщики"""
        
        # Создаем моки разных процессов
        mock_trusted = MagicMock()
        mock_trusted.pid = 1000
        mock_trusted.name.return_value = "TrustedInstaller.exe"
        mock_trusted.create_time.return_value = datetime.now().timestamp()
        
        mock_tiworker = MagicMock()
        mock_tiworker.pid = 2000
        mock_tiworker.name.return_value = "tiworker.exe"
        mock_tiworker.create_time.return_value = datetime.now().timestamp()
        
        mock_installer = MagicMock()
        mock_installer.pid = 3000
        mock_installer.name.return_value = "installer.exe"
        mock_installer.create_time.return_value = datetime.now().timestamp()
        
        # Возвращаем все процессы
        mock_process_iter.return_value = [mock_trusted, mock_tiworker, mock_installer]
        
        # Проверяем процессы
        result = self.monitor._check_installer_processes()
        
        # Должен быть обнаружен только installer.exe
        self.assertTrue(result, "installer.exe должен быть обнаружен")
        print("✓ Смешанные процессы обрабатываются правильно")
    
    @patch('psutil.process_iter')
    def test_case_insensitive_exclusion(self, mock_process_iter):
        """Тест: Проверка регистронезависимости для исключений"""
        
        # TrustedInstaller с разным регистром
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.name.return_value = "TRUSTEDINSTALLER.EXE"  # Верхний регистр
        mock_proc.create_time.return_value = datetime.now().timestamp()
        
        mock_process_iter.return_value = [mock_proc]
        
        # Проверяем процессы (name().lower() должен сработать)
        result = self.monitor._check_installer_processes()
        
        self.assertFalse(result, "TRUSTEDINSTALLER.EXE (верхний регистр) не должен триггерить тревогу")
        print("✓ Регистронезависимое исключение работает правильно")


def run_tests():
    """Запуск всех тестов"""
    print("=" * 70)
    print("Тест исключений для системных процессов Windows")
    print("=" * 70)
    print()
    
    # Создаем тестовый набор
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTrustedInstallerExclusion)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
    else:
        print("✗ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nТесты прерваны пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Ошибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
