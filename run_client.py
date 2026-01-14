"""
Точка входа для клиентского приложения LibLocker
"""
import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client.gui import main

if __name__ == "__main__":
    main()

