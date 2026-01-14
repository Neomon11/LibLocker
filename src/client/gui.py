"""
GUI для клиентского приложения LibLocker
Окно блокировки и виджет таймера
"""
import sys
import asyncio
import os
import logging
import winsound
from datetime import datetime, timedelta
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint
from PyQt6.QtGui import QFont, QColor, QPalette, QScreen
import win32api
import win32con

from .client import LibLockerClient
from ..shared.utils import verify_password
from ..shared.config import ClientConfig

logger = logging.getLogger(__name__)

# Пароль администратора для разблокировки (TODO: загружать из конфига)
ADMIN_PASSWORD_HASH = ""  # Пустой для отладки


class ClientThread(QThread):
    """Поток для WebSocket клиента"""

    session_started = pyqtSignal(dict)
    session_stopped = pyqtSignal(dict)
    shutdown_requested = pyqtSignal()
    connected_to_server = pyqtSignal()

    def __init__(self, server_url: str):
        super().__init__()
        self.server_url = server_url
        self.client = None
        self.loop = None

    def run(self):
        """Запуск клиента в отдельном потоке"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.client = LibLockerClient(self.server_url)

        # Подключение callbacks - используем потокобезопасный способ
        def emit_session_started(data):
            logger.info(f"[ClientThread] Callback called - emitting session_started signal")
            logger.info(f"[ClientThread] Data: {data}")
            logger.info(f"[ClientThread] Thread ID: {QThread.currentThreadId()}")
            try:
                self.session_started.emit(data)
                logger.info(f"[ClientThread] Signal emitted successfully")
            except Exception as e:
                logger.error(f"[ClientThread] Error emitting signal: {e}", exc_info=True)

        def emit_session_stopped(data):
            logger.info(f"[ClientThread] Emitting session_stopped signal with data: {data}")
            self.session_stopped.emit(data)

        def emit_shutdown():
            logger.info(f"[ClientThread] Emitting shutdown_requested signal")
            self.shutdown_requested.emit()

        def emit_connected():
            logger.info(f"[ClientThread] Emitting connected_to_server signal")
            self.connected_to_server.emit()

        self.client.on_session_start = emit_session_started
        self.client.on_session_stop = emit_session_stopped
        self.client.on_shutdown = emit_shutdown
        self.client.on_connected = emit_connected

        # Запуск клиента
        try:
            self.loop.run_until_complete(self.client.run())
        except Exception as e:
            logger.error(f"Client thread error: {e}", exc_info=True)


class LockScreen(QMainWindow):
    """Полноэкранное окно блокировки (показывается ПОСЛЕ окончания сессии)"""

    def __init__(self, session_data: dict):
        super().__init__()
        self.session_data = session_data

        # Настройки тарификации (для отображения итоговой стоимости)
        self.cost_per_hour = session_data.get('cost_per_hour', 0.0)
        self.free_mode = session_data.get('free_mode', True)
        self.duration_minutes = session_data.get('duration_minutes', 0)

        # Счетчик кликов для ввода пароля
        self.corner_clicks = 0
        self.last_click_time = None

        self.init_ui()
        self.setup_fullscreen()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("LibLocker - Сессия завершена")

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Иконка/Заголовок
        title_label = QLabel("🔒")
        title_font = QFont()
        title_font.setPointSize(72)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        layout.addSpacing(30)

        # Главное сообщение
        message_label = QLabel("Время сессии истекло")
        message_font = QFont()
        message_font.setPointSize(42)
        message_font.setBold(True)
        message_label.setFont(message_font)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)

        layout.addSpacing(20)

        # Подзаголовок
        subtitle_label = QLabel("Компьютер заблокирован")
        subtitle_font = QFont()
        subtitle_font.setPointSize(24)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)

        layout.addSpacing(40)

        # Итоговая стоимость
        if not self.free_mode and self.cost_per_hour > 0:
            total_hours = self.duration_minutes / 60
            cost = total_hours * self.cost_per_hour
            cost_label = QLabel(f"Стоимость сессии: {cost:.2f} руб.")
        else:
            cost_label = QLabel("Бесплатная сессия")

        cost_font = QFont()
        cost_font.setPointSize(28)
        cost_font.setBold(True)
        cost_label.setFont(cost_font)
        cost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(cost_label)

        layout.addSpacing(60)

        # Информационное сообщение
        info_label = QLabel("Для разблокировки обратитесь к администратору\nили оплатите новую сессию")
        info_font = QFont()
        info_font.setPointSize(18)
        info_label.setFont(info_font)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        layout.addSpacing(20)

        # Подсказка для админа
        hint_label = QLabel("(Администратор: тройной клик в правом верхнем углу)")
        hint_font = QFont()
        hint_font.setPointSize(12)
        hint_label.setFont(hint_font)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: #666;")
        layout.addWidget(hint_label)

        # Установка фона
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(20, 20, 20))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Скрыть поле для ввода пароля (будет показано по клику)
        self.password_input = None

    def setup_fullscreen(self):
        """Настройка полноэкранного режима"""
        # Убираем рамку окна
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint
        )

        # Полный экран
        self.showFullScreen()

        # Захват клавиатуры и мыши
        self.setFocus()
        self.activateWindow()

    def mousePressEvent(self, event):
        """Обработка кликов мыши для показа поля пароля"""
        # Клик в правом верхнем углу
        if event.pos().x() > self.width() - 100 and event.pos().y() < 100:
            current_time = datetime.now()

            # Проверка двойного клика (в течение 1 секунды)
            if self.last_click_time and (current_time - self.last_click_time).total_seconds() < 1:
                self.corner_clicks += 1
            else:
                self.corner_clicks = 1

            self.last_click_time = current_time

            # Если 3 клика - показываем поле пароля
            if self.corner_clicks >= 3:
                self.show_password_dialog()
                self.corner_clicks = 0

    def show_password_dialog(self):
        """Показать диалог ввода пароля администратора"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Разблокировка")
        dialog.setModal(True)

        layout = QVBoxLayout()

        label = QLabel("Введите пароль администратора:")
        layout.addWidget(label)

        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_input)

        buttons = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Отмена")
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)

        dialog.setLayout(layout)

        def check_password():
            password = password_input.text()
            # TODO: Проверка пароля через verify_password
            if password == "admin" or not ADMIN_PASSWORD_HASH:  # Отладка
                QMessageBox.information(dialog, "Успех", "Разблокировка выполнена")
                dialog.accept()
                self.close()
            else:
                QMessageBox.warning(dialog, "Ошибка", "Неверный пароль")

        btn_ok.clicked.connect(check_password)
        btn_cancel.clicked.connect(dialog.reject)

        dialog.exec()

    def keyPressEvent(self, event):
        """Блокировка опасных горячих клавиш"""
        # Блокируем Alt+F4, Alt+Tab и другие
        if event.key() == Qt.Key.Key_F4 and event.modifiers() == Qt.KeyboardModifier.AltModifier:
            event.ignore()
            return

        # Блокируем Escape
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return

        # Блокируем Win клавишу (частично)
        if event.key() == Qt.Key.Key_Meta:
            event.ignore()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Предотвращение закрытия окна"""
        # Окно может быть закрыто только программно или по паролю
        if not hasattr(self, '_allow_close'):
            event.ignore()
        else:
            event.accept()

    def force_close(self):
        """Принудительное закрытие окна"""
        self._allow_close = True
        self.close()


class TimerWidget(QWidget):
    """Компактный виджет таймера для отображения оставшегося времени во время сессии"""

    session_finished = pyqtSignal()  # Сигнал окончания времени сессии

    def __init__(self, session_data: dict, config: ClientConfig = None):
        super().__init__()
        self.session_data = session_data
        self.start_time = datetime.now()
        self.config = config or ClientConfig()

        # Расчет времени окончания
        duration_minutes = session_data.get('duration_minutes', 0)
        self.is_unlimited = session_data.get('is_unlimited', False)

        if self.is_unlimited:
            self.end_time = None
            self.total_seconds = None
        else:
            self.end_time = self.start_time + timedelta(minutes=duration_minutes)
            self.total_seconds = duration_minutes * 60

        self.remaining_seconds = self.total_seconds

        # Настройки тарификации
        self.cost_per_hour = session_data.get('cost_per_hour', 0.0)
        self.free_mode = session_data.get('free_mode', True)

        # Флаги для уведомлений
        self.warning_shown = False
        self.warning_minutes = self.config.warning_minutes

        # Таймер обновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Обновление каждую секунду

        self.is_hidden = False
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("LibLocker Timer")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Заголовок
        header_layout = QHBoxLayout()
        title_label = QLabel("⏱️ Сессия")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        # Кнопка скрыть
        self.btn_hide = QPushButton("×")
        self.btn_hide.setMaximumSize(20, 20)
        self.btn_hide.clicked.connect(self.toggle_visibility)
        self.btn_hide.setStyleSheet("QPushButton { background: transparent; color: #666; font-size: 16px; border: none; }")
        header_layout.addWidget(self.btn_hide)

        layout.addLayout(header_layout)

        # Таймер
        self.timer_label = QLabel("00:00:00")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.timer_label.setFont(font)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_label)

        # Стоимость
        self.cost_label = QLabel("")
        cost_font = QFont()
        cost_font.setPointSize(9)
        self.cost_label.setFont(cost_font)
        self.cost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.cost_label)

        self.setLayout(layout)

        # Стиль с настраиваемой прозрачностью
        opacity = self.config.widget_opacity
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(40, 40, 40, {opacity});
                color: white;
                border-radius: 10px;
            }}
        """)

        # Размер и позиция из конфигурации
        width, height = self.config.widget_size
        self.resize(width, height)

        x, y = self.config.widget_position
        self.move(x, y)

        # Начальное обновление
        self.update_display()

    def update_display(self):
        """Обновление отображения таймера и стоимости"""
        if self.is_unlimited:
            # Безлимитная сессия
            elapsed = datetime.now() - self.start_time
            elapsed_seconds = int(elapsed.total_seconds())
            hours = elapsed_seconds // 3600
            minutes = (elapsed_seconds % 3600) // 60
            seconds = elapsed_seconds % 60
            self.timer_label.setText(f"∞ {hours:02d}:{minutes:02d}:{seconds:02d}")

            # Стоимость для безлимита
            if not self.free_mode and self.cost_per_hour > 0:
                elapsed_hours = elapsed_seconds / 3600
                cost = elapsed_hours * self.cost_per_hour
                self.cost_label.setText(f"{cost:.2f} руб.")
            else:
                self.cost_label.setText("Бесплатно")
        else:
            # Ограниченная сессия
            now = datetime.now()
            if now >= self.end_time:
                # Время вышло - запускаем блокировку
                self.timer_label.setText("00:00:00")
                self.update_timer.stop()
                self.session_finished.emit()
            else:
                remaining = self.end_time - now
                self.remaining_seconds = int(remaining.total_seconds())

                hours = self.remaining_seconds // 3600
                minutes = (self.remaining_seconds % 3600) // 60
                secs = self.remaining_seconds % 60

                # Изменяем цвет при малом остатке времени
                if self.remaining_seconds <= 60:  # Последняя минута
                    self.timer_label.setStyleSheet("color: #ff4444;")
                elif self.remaining_seconds <= 300:  # Последние 5 минут
                    self.timer_label.setStyleSheet("color: #ffaa00;")
                else:
                    self.timer_label.setStyleSheet("color: white;")

                self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")

                # Предупреждение за N минут до конца
                if not self.warning_shown and self.remaining_seconds <= (self.warning_minutes * 60):
                    self.show_warning()
                    self.warning_shown = True

                # Стоимость
                if not self.free_mode and self.cost_per_hour > 0:
                    total_hours = self.total_seconds / 3600
                    cost = total_hours * self.cost_per_hour
                    self.cost_label.setText(f"{cost:.2f} руб.")
                else:
                    self.cost_label.setText("Бесплатно")

    def show_warning(self):
        """Показать предупреждение о скором окончании сессии"""
        logger.info(f"Warning: {self.warning_minutes} minutes remaining")

        # Звуковое уведомление
        if self.config.sound_enabled:
            try:
                # Проигрываем системный звук предупреждения
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception as e:
                logger.error(f"Error playing sound: {e}")

        # Всплывающее уведомление
        if self.config.popup_enabled:
            self.show_warning_popup()

        # Принудительно показываем виджет если он был скрыт
        if self.is_hidden:
            self.toggle_visibility()

    def show_warning_popup(self):
        """Показать всплывающее предупреждение"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("LibLocker - Предупреждение")
        msg.setText(f"⚠️ Внимание!\n\nДо конца сессии осталось {self.warning_minutes} минут.")
        msg.setInformativeText("Для продления времени обратитесь к администратору.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        msg.exec()

    def toggle_visibility(self):
        """Переключение видимости виджета"""
        if self.is_hidden:
            # Показываем полный виджет
            self.resize(200, 100)
            self.timer_label.show()
            self.cost_label.show()
            self.btn_hide.setText("×")
            self.is_hidden = False
        else:
            # Минимизируем виджет
            self.resize(50, 30)
            self.timer_label.hide()
            self.cost_label.hide()
            self.btn_hide.setText("⏱")
            self.is_hidden = True

    def stop_timer(self):
        """Остановить таймер"""
        self.update_timer.stop()

    def force_close(self):
        """Принудительное закрытие виджета"""
        self.update_timer.stop()
        self.close()


class MainClientWindow(QMainWindow):
    """Главное окно клиентского приложения"""

    def __init__(self, server_url: str = None, config: ClientConfig = None):
        super().__init__()
        self.setWindowTitle("LibLocker Client")
        self.resize(400, 200)

        # Загрузка конфигурации
        self.config = config or ClientConfig()

        # Использовать URL из аргументов или из конфигурации
        server_url = server_url or self.config.server_url

        self.lock_screen = None
        self.timer_widget = None
        self.current_session_data = None

        # WebSocket клиент
        self.client_thread = ClientThread(server_url)
        # Используем Qt.ConnectionType.QueuedConnection для потокобезопасной передачи сигналов
        self.client_thread.session_started.connect(
            self.on_session_started, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.session_stopped.connect(
            self.on_session_stopped, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.shutdown_requested.connect(
            self.on_shutdown_requested, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.connected_to_server.connect(
            self.on_connected_to_server, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.start()

        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        status_label = QLabel("LibLocker Client")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        status_label.setFont(font)
        layout.addWidget(status_label)

        self.connection_label = QLabel("Подключение к серверу...")
        self.connection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.connection_label)

        layout.addStretch()

    def on_session_started(self, data: dict):
        """Обработка начала сессии"""
        logger.info("=" * 60)
        logger.info(f"[MainWindow] *** on_session_started CALLED ***")
        logger.info(f"[MainWindow] Thread ID: {QThread.currentThreadId()}")
        logger.info(f"[MainWindow] Session data received: {data}")
        logger.info("=" * 60)

        try:
            self.current_session_data = data

            # Показываем виджет таймера с конфигурацией
            logger.info("[MainWindow] Creating timer widget...")
            self.timer_widget = TimerWidget(data, self.config)
            logger.info(f"[MainWindow] Timer widget created: {self.timer_widget}")
            
            self.timer_widget.session_finished.connect(self.on_timer_finished)
            logger.info("[MainWindow] Signal connected to on_timer_finished")

            logger.info("[MainWindow] Showing timer widget...")
            self.timer_widget.show()
            self.timer_widget.raise_()  # Поднимаем окно наверх
            self.timer_widget.activateWindow()  # Активируем окно
            logger.info("[MainWindow] Timer widget shown successfully")

            # Скрываем главное окно
            self.hide()
            logger.info("[MainWindow] Main window hidden")
        except Exception as e:
            logger.error(f"[MainWindow] Error in on_session_started: {e}", exc_info=True)

    def on_timer_finished(self):
        """Обработка окончания времени сессии - показываем блокировку"""
        logger.info("Session time finished - showing lock screen")

        # Закрываем виджет таймера
        if self.timer_widget:
            self.timer_widget.force_close()
            self.timer_widget = None

        # Показываем полноэкранную блокировку
        self.lock_screen = LockScreen(self.current_session_data)
        self.lock_screen.show()

    def on_session_stopped(self, data: dict):
        """Обработка остановки сессии (команда от сервера)"""
        logger.info(f"Session stopped: {data}")

        # Закрываем виджет таймера если активен
        if self.timer_widget:
            self.timer_widget.force_close()
            self.timer_widget = None

        # Закрываем окно блокировки если активно
        if self.lock_screen:
            self.lock_screen.force_close()
            self.lock_screen = None

        # Показываем главное окно
        self.show()
        self.current_session_data = None

    def on_shutdown_requested(self):
        """Обработка команды выключения"""
        logger.info("Shutdown requested")

        reply = QMessageBox.question(
            self, "Выключение",
            "Получена команда выключения компьютера. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Выключение компьютера (Windows)
            os.system("shutdown /s /t 5")

    def on_connected_to_server(self):
        """Обработка успешного подключения к серверу"""
        logger.info("Connected to server - updating UI")
        self.connection_label.setText("✅ Подключено к серверу")
        self.connection_label.setStyleSheet("color: green;")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Сворачиваем в трей вместо закрытия
        event.ignore()
        self.hide()


def main():
    """Точка входа в клиентское приложение"""
    # Загрузка конфигурации
    config = ClientConfig()

    # Настройка логирования
    log_file = config.log_file
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logger.info("=" * 50)
    logger.info("LibLocker Client starting...")
    logger.info(f"Config loaded: {config.config_file}")

    import sys
    # URL из аргументов командной строки имеет приоритет
    server_url = sys.argv[1] if len(sys.argv) > 1 else None

    app = QApplication(sys.argv)
    window = MainClientWindow(server_url, config)
    window.show()

    logger.info("Client window opened")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

