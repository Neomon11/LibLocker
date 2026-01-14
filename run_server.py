"""
Точка входа для серверного приложения LibLocker
"""
import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.shared.utils import SingleInstanceChecker
from src.server.gui import main

if __name__ == "__main__":
    # Проверка на наличие уже запущенного экземпляра
    instance_checker = SingleInstanceChecker('liblocker_server')
    
    if instance_checker.is_already_running():
        print("Ошибка: Сервер LibLocker уже запущен на этом компьютере!")
        print("Закройте запущенный экземпляр перед запуском нового.")
        input("Нажмите Enter для выхода...")
        sys.exit(1)
    
    try:
        main()
    finally:
        # Освобождаем lock-файл при выходе
        instance_checker.release()

