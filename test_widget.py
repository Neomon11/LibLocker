"""
Простой тест: симуляция получения сообщения SESSION_START клиентом
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from src.client.gui import MainClientWindow, TimerWidget
from src.shared.config import ClientConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_timer_widget():
    """Тест виджета таймера без подключения к серверу"""
    logger.info("="* 50)
    logger.info("Тест виджета таймера")
    logger.info("="* 50)

    app = QApplication(sys.argv)

    # Тестовые данные сессии
    session_data = {
        'duration_minutes': 1,  # 1 минута
        'is_unlimited': False,
        'cost_per_hour': 100.0,
        'free_mode': False,
        'session_id': 1
    }

    logger.info(f"Создание виджета таймера с данными: {session_data}")

    # Создаем виджет таймера
    config = ClientConfig()
    widget = TimerWidget(session_data, config)

    logger.info("Виджет создан. Показываем...")
    widget.show()

    logger.info("✅ Виджет должен быть виден на экране!")
    logger.info("Проверьте левый верхний угол экрана.")
    logger.info("Виджет покажет таймер на 1 минуту.")

    sys.exit(app.exec())

if __name__ == "__main__":
    test_timer_widget()

