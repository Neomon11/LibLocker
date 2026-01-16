"""
GUI для клиентского приложения LibLocker
Окно блокировки и виджет таймера
"""
import sys
import asyncio
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox, QDialog, QMenu, QSystemTrayIcon
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint
from PyQt6.QtGui import QFont, QColor, QPalette, QScreen, QAction, QIcon

# Windows-specific imports (optional for cross-platform compatibility)
try:
    import winsound
    import win32api
    import win32con
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

from .client import LibLockerClient
from ..shared.utils import verify_password
from ..shared.config import ClientConfig

logger = logging.getLogger(__name__)

# Log warning if Windows modules are not available
if not WINDOWS_AVAILABLE:
    logger.warning("Windows-specific modules not available (winsound, win32api, win32con)")

# Пароль администратора для разблокировки загружается из конфига


def get_russian_plural(number: int, form1: str, form2: str, form5: str) -> str:
    """
    Возвращает правильную форму слова для русского языка в зависимости от числа
    
    Args:
        number: Число
        form1: Форма для 1 (например, "минута")
        form2: Форма для 2-4 (например, "минуты")
        form5: Форма для 5+ (например, "минут")
    
    Returns:
        Правильная форма слова
    
    Examples:
        get_russian_plural(1, "минута", "минуты", "минут") -> "минута"
        get_russian_plural(2, "минута", "минуты", "минут") -> "минуты"
        get_russian_plural(5, "минута", "минуты", "минут") -> "минут"
    """
    n = abs(number)
    n %= 100
    if n >= 5 and n <= 20:
        return form5
    n %= 10
    if n == 1:
        return form1
    if n >= 2 and n <= 4:
        return form2
    return form5


class InstallationMonitorSignals(QWidget):
    """Signal wrapper for InstallationMonitor to ensure thread-safe callbacks"""
    installation_detected = pyqtSignal(str)  # reason


class ClientThread(QThread):
    """Поток для WebSocket клиента"""

    session_started = pyqtSignal(dict)
    session_stopped = pyqtSignal(dict)
    session_time_updated = pyqtSignal(dict)
    password_updated = pyqtSignal(dict)
    shutdown_requested = pyqtSignal()
    unlock_requested = pyqtSignal()  # Сигнал разблокировки от сервера
    connected_to_server = pyqtSignal()
    installation_monitor_toggle = pyqtSignal(bool, int)  # enabled, alert_volume

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

        def emit_session_time_updated(data):
            logger.info(f"[ClientThread] Emitting session_time_updated signal with data: {data}")
            self.session_time_updated.emit(data)

        def emit_password_updated(data):
            logger.info(f"[ClientThread] Emitting password_updated signal")
            self.password_updated.emit(data)

        def emit_shutdown():
            logger.info(f"[ClientThread] Emitting shutdown_requested signal")
            self.shutdown_requested.emit()
        
        def emit_unlock():
            logger.info(f"[ClientThread] Emitting unlock_requested signal")
            self.unlock_requested.emit()

        def emit_connected():
            logger.info(f"[ClientThread] Emitting connected_to_server signal")
            self.connected_to_server.emit()

        def emit_installation_monitor_toggle(enabled: bool, alert_volume: int = 80):
            logger.info(f"[ClientThread] Emitting installation_monitor_toggle signal: enabled={enabled}, volume={alert_volume}")
            self.installation_monitor_toggle.emit(enabled, alert_volume)

        self.client.on_session_start = emit_session_started
        self.client.on_session_stop = emit_session_stopped
        self.client.on_session_time_update = emit_session_time_updated
        self.client.on_password_update = emit_password_updated
        self.client.on_shutdown = emit_shutdown
        self.client.on_unlock = emit_unlock
        self.client.on_connected = emit_connected
        self.client.on_installation_monitor_toggle = emit_installation_monitor_toggle

        # Запуск клиента
        try:
            self.loop.run_until_complete(self.client.run())
        except Exception as e:
            logger.error(f"Client thread error: {e}", exc_info=True)


class LockScreen(QMainWindow):
    """Полноэкранное окно блокировки (показывается ПОСЛЕ окончания сессии)"""

    unlocked = pyqtSignal()  # Сигнал разблокировки администратором

    def __init__(self, session_data: dict, config: ClientConfig = None):
        super().__init__()
        self.session_data = session_data
        self.config = config or ClientConfig()

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
            admin_password_hash = self.config.admin_password_hash
            
            # Если пароль не установлен, предупреждаем но разрешаем
            if not admin_password_hash:
                QMessageBox.warning(
                    dialog, 
                    "Предупреждение", 
                    "Пароль администратора не установлен!\nОбратитесь к администратору для настройки безопасности."
                )
                dialog.accept()
                self.unlocked.emit()
                return
            
            # Проверяем пароль через verify_password
            if verify_password(password, admin_password_hash):
                QMessageBox.information(dialog, "Успех", "Разблокировка выполнена")
                dialog.accept()
                self.unlocked.emit()
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
    session_stop_requested = pyqtSignal()  # Сигнал запроса остановки сессии пользователем
    installation_monitor_toggle_requested = pyqtSignal(bool)  # Сигнал запроса изменения мониторинга установки

    def __init__(self, session_data: dict, config: ClientConfig = None, installation_monitor_enabled: bool = False):
        super().__init__()
        self.session_data = session_data
        self.start_time = datetime.now()
        self.config = config or ClientConfig()
        self.installation_monitor_enabled = installation_monitor_enabled

        # Расчет времени окончания
        duration_minutes = session_data.get('duration_minutes', 0)
        self.is_unlimited = session_data.get('is_unlimited', False)

        if self.is_unlimited:
            self.end_time = None
            self.total_seconds = None
            self.remaining_seconds = 0  # Use 0 instead of None for consistency
        else:
            self.end_time = self.start_time + timedelta(minutes=duration_minutes)
            self.total_seconds = duration_minutes * 60
            self.remaining_seconds = self.total_seconds

        # Настройки тарификации
        self.cost_per_hour = session_data.get('cost_per_hour', 0.0)
        self.free_mode = session_data.get('free_mode', True)

        # Флаги для уведомлений
        self.warning_shown = False
        # Adjust warning time for short sessions - don't warn if session is shorter than warning time
        self.warning_minutes = self._calculate_warning_time(duration_minutes)

        # Таймер обновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Обновление каждую секунду

        self.is_hidden = False
        self.btn_end_session = None  # Инициализируем для безопасности
        self.init_ui()

    def _calculate_warning_time(self, duration_minutes: int) -> int:
        """
        Calculate appropriate warning time for a session
        For short sessions, use half the duration (min 1 minute)
        For longer sessions, use the configured warning time
        """
        if self.is_unlimited or duration_minutes <= 0:
            return self.config.warning_minutes
        
        # For sessions shorter than warning time, use half the duration
        if duration_minutes < self.config.warning_minutes:
            return max(1, duration_minutes // 2)
        
        return self.config.warning_minutes

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("LibLocker Timer")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

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
        self.btn_hide.setStyleSheet("QPushButton { background: #000000; color: #999; font-size: 16px; border: none; border-radius: 3px; } QPushButton:hover { background: #222222; color: #fff; }")
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

        # Кнопка завершения сессии (только для безлимитных сессий)
        if self.is_unlimited:
            self.btn_end_session = QPushButton("⏹️ Завершить сессию")
            self.btn_end_session.setMinimumHeight(30)
            self.btn_end_session.clicked.connect(self.request_session_stop)
            self.btn_end_session.setStyleSheet("""
                QPushButton {
                    background-color: #d32f2f;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #b71c1c;
                }
                QPushButton:pressed {
                    background-color: #8b0000;
                }
            """)
            layout.addWidget(self.btn_end_session)

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
                # Use < instead of <= to avoid triggering warning at session start
                if not self.warning_shown and self.remaining_seconds < (self.warning_minutes * 60):
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

        # Принудительно показываем виджет если он был скрыт (ПЕРЕД показом popup)
        if self.is_hidden:
            self.toggle_visibility()

        # Звуковое уведомление
        if self.config.sound_enabled and WINDOWS_AVAILABLE:
            try:
                # Проигрываем системный звук предупреждения
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception as e:
                logger.error(f"Error playing sound: {e}")

        # Всплывающее уведомление
        if self.config.popup_enabled:
            self.show_warning_popup()

    def show_warning_popup(self):
        """Показать всплывающее предупреждение"""
        # Create dialog with parent to prevent app quit when closed
        # The dialog is still independent in size/position due to WindowStaysOnTopHint
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("LibLocker - Предупреждение")
        
        # Use correct Russian plural form
        minute_word = get_russian_plural(self.warning_minutes, "минута", "минуты", "минут")
        msg.setText(f"⚠️ Внимание!\n\nДо конца сессии осталось {self.warning_minutes} {minute_word}.")
        msg.setInformativeText("Для продления времени обратитесь к администратору.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        # Make it stay on top and be independent
        msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        msg.exec()

    def toggle_visibility(self):
        """Переключение видимости виджета"""
        if self.is_hidden:
            # Показываем полный виджет
            width, height = self.config.widget_size
            self.resize(width, height)
            self.timer_label.show()
            self.cost_label.show()
            if self.btn_end_session:
                self.btn_end_session.show()
            self.btn_hide.setText("×")
            self.is_hidden = False
            # Восстанавливаем обычную прозрачность
            opacity = self.config.widget_opacity
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: rgba(40, 40, 40, {opacity});
                    color: white;
                    border-radius: 10px;
                }}
            """)
        else:
            # Минимизируем виджет - делаем его почти невидимым с прозрачным фоном
            self.resize(30, 20)
            self.timer_label.hide()
            self.cost_label.hide()
            if self.btn_end_session:
                self.btn_end_session.hide()
            self.btn_hide.setText("⏱")
            self.is_hidden = True
            # Полностью прозрачный фон, только иконка видна
            self.setStyleSheet("""
                QWidget {
                    background-color: transparent;
                    color: rgba(255, 255, 255, 0.6);
                    border-radius: 5px;
                }
                QPushButton {
                    background: transparent;
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 16px;
                    border: none;
                }
                QPushButton:hover {
                    color: rgba(255, 255, 255, 0.9);
                }
            """)

    def stop_timer(self):
        """Остановить таймер"""
        self.update_timer.stop()

    def request_session_stop(self):
        """Запросить остановку сессии (для безлимитных сессий)"""
        logger.info("User requested to stop unlimited session")
        
        # Показываем диалог подтверждения
        reply = QMessageBox.question(
            self, 
            "Завершить сессию",
            "Вы уверены, что хотите завершить сессию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logger.info("User confirmed session stop request")
            self.session_stop_requested.emit()
        else:
            logger.info("User cancelled session stop request")

    def update_session_time(self, new_duration_minutes: int):
        """Обновить время сессии (вызывается при изменении админом)"""
        logger.info(f"Updating session time to {new_duration_minutes} minutes")
        
        if self.is_unlimited:
            logger.warning("Cannot update time for unlimited session")
            return
        
        # Обновляем время окончания
        self.end_time = self.start_time + timedelta(minutes=new_duration_minutes)
        self.total_seconds = new_duration_minutes * 60
        
        # Пересчитываем remaining_seconds
        now = datetime.now()
        if now >= self.end_time:
            self.remaining_seconds = 0
        else:
            remaining = self.end_time - now
            self.remaining_seconds = int(remaining.total_seconds())
        
        # Recalculate warning time for the new duration
        self.warning_minutes = self._calculate_warning_time(new_duration_minutes)
        
        # Reset warning flag if there's now enough time before warning
        # (e.g., if time was extended significantly)
        if self.remaining_seconds > (self.warning_minutes * 60):
            self.warning_shown = False
            logger.info(f"Warning flag reset - {self.remaining_seconds}s remaining > {self.warning_minutes * 60}s threshold")
        
        # Обновляем отображение (this may trigger warning if time is still low)
        self.update_display()
        
        # Показываем уведомление о изменении времени (non-blocking)
        # Use QTimer.singleShot to avoid blocking the signal handler
        def show_time_change_notification():
            from PyQt6.QtWidgets import QMessageBox
            # Create dialog with parent to prevent app quit when closed
            # The dialog is still independent in size/position due to WindowStaysOnTopHint
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("LibLocker - Изменение времени")
            minute_word = get_russian_plural(new_duration_minutes, "минута", "минуты", "минут")
            msg.setText(f"⏱️ Администратор изменил время сессии\n\nНовая длительность: {new_duration_minutes} {minute_word}")
            msg.setInformativeText("Время окончания сессии было обновлено.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            # Make it stay on top and be independent
            msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
            msg.exec()
        
        # Show notification after a short delay to avoid blocking
        QTimer.singleShot(100, show_time_change_notification)

    def contextMenuEvent(self, event):
        """Обработка правого клика для показа контекстного меню"""
        context_menu = QMenu(self)
        
        # Добавляем пункт мониторинга установки
        monitor_action = QAction("Включить мониторинг установки программ", self)
        monitor_action.setCheckable(True)
        monitor_action.setChecked(self.installation_monitor_enabled)
        monitor_action.triggered.connect(self.toggle_installation_monitor)
        context_menu.addAction(monitor_action)
        
        # Показываем меню
        context_menu.exec(event.globalPos())
    
    def toggle_installation_monitor(self):
        """Переключение мониторинга установки"""
        self.installation_monitor_enabled = not self.installation_monitor_enabled
        logger.info(f"Installation monitor toggle requested: {self.installation_monitor_enabled}")
        self.installation_monitor_toggle_requested.emit(self.installation_monitor_enabled)
    
    def set_installation_monitor_status(self, enabled: bool):
        """Установка статуса мониторинга установки (вызывается извне)"""
        self.installation_monitor_enabled = enabled
        logger.info(f"Installation monitor status updated: {enabled}")

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
        self.red_alert_screen = None
        
        # Installation monitor with thread-safe signal wrapper
        self.installation_monitor_signals = InstallationMonitorSignals()
        self.installation_monitor_signals.installation_detected.connect(
            self.on_installation_detected, Qt.ConnectionType.QueuedConnection
        )
        
        from .installation_monitor import InstallationMonitor
        self.installation_monitor = InstallationMonitor(
            signal_emitter=self.installation_monitor_signals
        )

        # WebSocket клиент
        self.client_thread = ClientThread(server_url)
        # Используем Qt.ConnectionType.QueuedConnection для потокобезопасной передачи сигналов
        self.client_thread.session_started.connect(
            self.on_session_started, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.session_stopped.connect(
            self.on_session_stopped, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.session_time_updated.connect(
            self.on_session_time_updated, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.password_updated.connect(
            self.on_password_updated, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.shutdown_requested.connect(
            self.on_shutdown_requested, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.unlock_requested.connect(
            self.on_unlock_requested, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.connected_to_server.connect(
            self.on_connected_to_server, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.installation_monitor_toggle.connect(
            self.on_installation_monitor_toggle, Qt.ConnectionType.QueuedConnection
        )
        self.client_thread.start()

        self.init_ui()
        self.init_tray_icon()

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

    def init_tray_icon(self):
        """Инициализация иконки в системном трее"""
        # Создаем иконку трея
        self.tray_icon = QSystemTrayIcon(self)
        
        # Создаем иконку (используем встроенную иконку Qt или можно загрузить свою)
        # Для простоты используем стандартную иконку приложения
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        
        # Создаем контекстное меню для трея
        tray_menu = QMenu()
        
        # Действие "Развернуть"
        show_action = QAction("Развернуть", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        # Разделитель
        tray_menu.addSeparator()
        
        # Действие "Закрыть клиент" (с проверкой пароля)
        exit_action = QAction("Закрыть клиент", self)
        exit_action.triggered.connect(self.exit_with_password_check)
        tray_menu.addAction(exit_action)
        
        # Устанавливаем меню
        self.tray_icon.setContextMenu(tray_menu)
        
        # Двойной клик по иконке показывает окно
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # Показываем иконку
        self.tray_icon.show()
        
        # Устанавливаем подсказку
        self.tray_icon.setToolTip("LibLocker Client")

    def on_tray_icon_activated(self, reason):
        """Обработка кликов по иконке в трее"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        """Показать главное окно"""
        self.show()
        self.raise_()
        self.activateWindow()

    def exit_with_password_check(self):
        """Выход из приложения с проверкой пароля администратора"""
        # Показываем диалог ввода пароля
        dialog = QDialog(self)
        dialog.setWindowTitle("Закрытие клиента")
        dialog.setModal(True)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout()

        label = QLabel("Для закрытия клиента введите пароль администратора:")
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
            admin_password_hash = self.config.admin_password_hash
            
            # Если пароль не установлен, предупреждаем но разрешаем
            if not admin_password_hash:
                reply = QMessageBox.question(
                    dialog, 
                    "Предупреждение", 
                    "Пароль администратора не установлен!\nВы уверены, что хотите закрыть клиент?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    dialog.accept()
                    self.force_exit()
                return
            
            # Проверяем пароль через verify_password
            if verify_password(password, admin_password_hash):
                dialog.accept()
                self.force_exit()
            else:
                QMessageBox.warning(dialog, "Ошибка", "Неверный пароль")
                password_input.clear()
                password_input.setFocus()

        btn_ok.clicked.connect(check_password)
        btn_cancel.clicked.connect(dialog.reject)
        
        # Обработка Enter в поле пароля
        password_input.returnPressed.connect(check_password)

        dialog.exec()

    def force_exit(self):
        """Принудительное закрытие приложения"""
        logger.info("Force exit requested - closing application")
        
        # Останавливаем мониторинг установки
        if self.installation_monitor:
            self.installation_monitor.stop()
        
        # Закрываем все окна
        if self.lock_screen:
            self.lock_screen.force_close()
        if self.timer_widget:
            self.timer_widget.force_close()
        if self.red_alert_screen:
            self.red_alert_screen.force_close()
        
        # Скрываем иконку трея
        self.tray_icon.hide()
        
        # Завершаем приложение
        QApplication.quit()

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

            # Подключаем сигнал запроса остановки сессии
            self.timer_widget.session_stop_requested.connect(self.on_session_stop_requested)
            logger.info("[MainWindow] Signal connected to on_session_stop_requested")

            # Подключаем сигнал переключения мониторинга установки
            self.timer_widget.installation_monitor_toggle_requested.connect(self.on_timer_widget_monitor_toggle_requested)
            logger.info("[MainWindow] Signal connected to on_timer_widget_monitor_toggle_requested")
            
            # Устанавливаем текущий статус мониторинга в виджет
            self.timer_widget.set_installation_monitor_status(self.config.installation_monitor_enabled)
            
            # Автоматически запускаем мониторинг установки если включено в конфигурации
            if self.config.installation_monitor_enabled:
                logger.info("[MainWindow] Auto-starting installation monitor (enabled in config)")
                self.installation_monitor.start()
            else:
                logger.info("[MainWindow] Installation monitor not started (disabled in config)")

            # Устанавливаем callback для получения remaining_seconds
            if self.client_thread.client:
                try:
                    self.client_thread.client.get_remaining_seconds = self.get_remaining_seconds
                    logger.info("[MainWindow] Callback for get_remaining_seconds set")
                except Exception as e:
                    logger.error(f"[MainWindow] Failed to set get_remaining_seconds callback: {e}")

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

    def get_remaining_seconds(self) -> Optional[int]:
        """Получить оставшееся время сессии в секундах"""
        if self.timer_widget:
            return self.timer_widget.remaining_seconds
        return None

    def on_timer_finished(self):
        """Обработка окончания времени сессии - показываем блокировку"""
        logger.info("Session time finished - showing lock screen")
        
        # Останавливаем мониторинг установки если он был запущен
        if self.installation_monitor.enabled:
            logger.info("Stopping installation monitor (session time finished)")
            self.installation_monitor.stop()

        # Закрываем виджет таймера
        if self.timer_widget:
            self.timer_widget.force_close()
            self.timer_widget = None

        # Показываем полноэкранную блокировку с конфигом
        self.lock_screen = LockScreen(self.current_session_data, self.config)
        self.lock_screen.unlocked.connect(self.on_lock_screen_unlocked)
        self.lock_screen.show()

    def on_lock_screen_unlocked(self):
        """Обработка разблокировки экрана администратором"""
        logger.info("Lock screen unlocked by administrator")
        
        # Закрываем окно блокировки
        if self.lock_screen:
            # Отключаем сигнал перед закрытием
            try:
                self.lock_screen.unlocked.disconnect(self.on_lock_screen_unlocked)
            except TypeError:
                # Сигнал уже был отключен или не был подключен
                logger.debug("Signal was not connected or already disconnected")
            
            self.lock_screen.force_close()
            self.lock_screen = None
        
        # Показываем главное окно
        self.show()
        self.current_session_data = None

    def on_session_stop_requested(self):
        """Обработка запроса остановки сессии от пользователя"""
        logger.info("User requested session stop - sending request to server")
        
        # Отправляем запрос на сервер через WebSocket клиент
        if self.client_thread.client:
            # Нужно вызвать асинхронную функцию из синхронного контекста
            # Используем asyncio для запуска задачи в event loop клиента
            if self.client_thread.loop:
                asyncio.run_coroutine_threadsafe(
                    self.client_thread.client.request_session_stop(),
                    self.client_thread.loop
                )
            else:
                logger.error("Client event loop not available")
        else:
            logger.error("WebSocket client not available")

    def on_session_stopped(self, data: dict):
        """Обработка остановки сессии (команда от сервера)"""
        logger.info(f"Session stopped: {data}")
        
        # Останавливаем мониторинг установки если он был запущен
        if self.installation_monitor.enabled:
            logger.info("Stopping installation monitor (session stopped)")
            self.installation_monitor.stop()

        # Закрываем виджет таймера если активен
        if self.timer_widget:
            self.timer_widget.force_close()
            self.timer_widget = None

        # Обновляем данные сессии с финальными значениями из stop message
        if self.current_session_data and data:
            # Обновляем actual_duration и cost из stop message
            if 'actual_duration' in data:
                self.current_session_data['duration_minutes'] = data['actual_duration']
            if 'cost' in data:
                # Если есть итоговая стоимость, используем её
                # Пересчитываем cost_per_hour для корректного отображения
                if data['cost'] > 0 and data.get('actual_duration', 0) > 0:
                    duration_hours = data['actual_duration'] / 60.0
                    self.current_session_data['cost_per_hour'] = data['cost'] / duration_hours
                    self.current_session_data['free_mode'] = False
                else:
                    self.current_session_data['free_mode'] = True

        # Показываем экран блокировки (как при истечении времени)
        # Используем обновленные данные сессии для отображения стоимости
        if self.current_session_data:
            self.lock_screen = LockScreen(self.current_session_data, self.config)
            self.lock_screen.unlocked.connect(self.on_lock_screen_unlocked)
            self.lock_screen.show()
        else:
            # Если данных сессии нет, просто показываем главное окно
            logger.warning("No session data available for lock screen")
            self.show()
            
        # Не очищаем current_session_data здесь, т.к. оно нужно для lock screen

    def on_session_time_updated(self, data: dict):
        """Обработка обновления времени сессии"""
        logger.info(f"Session time updated: {data}")
        
        # Обновляем виджет таймера если активен
        if self.timer_widget:
            new_duration_minutes = data.get('new_duration_minutes', 0)
            self.timer_widget.update_session_time(new_duration_minutes)
            
            # Обновляем данные сессии
            if self.current_session_data:
                self.current_session_data['duration_minutes'] = new_duration_minutes

    def on_password_updated(self, data: dict):
        """Обработка обновления пароля администратора"""
        logger.info(f"Password updated from server")
        
        try:
            # Получаем новый хеш пароля
            new_hash = data.get('admin_password_hash', '')
            
            if new_hash:
                # Сохраняем в конфиг
                self.config.admin_password_hash = new_hash
                self.config.save()
                logger.info("Admin password hash updated and saved")
                
                # Show success notification (important security update - always show)
                # Use QTimer.singleShot to avoid blocking
                def show_password_update_notification():
                    # Always show password update notification, even during active session
                    # This is a critical security event that users should be aware of
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setWindowTitle("LibLocker - Обновление пароля")
                    msg.setText("Пароль администратора был обновлен на сервере.\n\n"
                                "Новый пароль сохранен и будет использоваться для разблокировки.")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    # Make it stay on top to ensure visibility
                    msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
                    msg.exec()
                
                QTimer.singleShot(100, show_password_update_notification)
            else:
                logger.warning("Received empty password hash from server")
                # Show warning for empty password (critical issue)
                # Use QTimer.singleShot for consistency and non-blocking behavior
                def show_empty_password_warning():
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setWindowTitle("LibLocker - Предупреждение")
                    msg.setText("Получен пустой пароль от сервера. Пароль не был обновлен.")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
                    msg.exec()
                
                QTimer.singleShot(100, show_empty_password_warning)
                
        except Exception as e:
            logger.error(f"Error updating admin password: {e}", exc_info=True)
            # Show error message to user (critical issue)
            # Use QTimer.singleShot for consistency and non-blocking behavior
            def show_password_error():
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("LibLocker - Ошибка")
                msg.setText(f"Не удалось обновить пароль администратора:\n{str(e)}\n\n"
                           "Обратитесь к администратору.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
                msg.exec()
            
            QTimer.singleShot(100, show_password_error)

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
    
    def on_unlock_requested(self):
        """Обработка команды разблокировки от сервера"""
        logger.info("Unlock requested from server")
        
        # Разблокируем красный экран тревоги если он активен
        if self.red_alert_screen:
            logger.info("Unlocking red alert screen")
            self.red_alert_screen.force_close()
            self.red_alert_screen = None
        
        # Разблокируем экран блокировки конца сессии если он активен
        if self.lock_screen:
            logger.info("Unlocking lock screen")
            self.lock_screen.force_close()
            self.lock_screen = None

    def on_connected_to_server(self):
        """Обработка успешного подключения к серверу"""
        logger.info("Connected to server - updating UI")
        self.connection_label.setText("✅ Подключено к серверу")
        self.connection_label.setStyleSheet("color: green;")

    def on_installation_monitor_toggle(self, enabled: bool, alert_volume: int = 80):
        """Обработка команды переключения мониторинга установки от сервера"""
        logger.info(f"Installation monitor toggle received from server: enabled={enabled}, volume={alert_volume}")
        
        # Сохраняем настройки в конфиг
        self.config.installation_monitor_enabled = enabled
        self.config.alert_volume = alert_volume
        self.config.save()
        
        # Запускаем или останавливаем мониторинг
        if enabled:
            self.installation_monitor.start()
        else:
            self.installation_monitor.stop()
        
        # Обновляем статус в виджете таймера если он активен
        if self.timer_widget:
            self.timer_widget.set_installation_monitor_status(enabled)
    
    def on_timer_widget_monitor_toggle_requested(self, enabled: bool):
        """Обработка запроса переключения мониторинга от виджета таймера"""
        logger.info(f"Installation monitor toggle requested from timer widget: {enabled}")
        
        # Отправляем запрос на сервер через клиента
        # Сервер должен будет отправить команду обратно всем клиентам
        # Пока просто локально обрабатываем
        self.on_installation_monitor_toggle(enabled)
    
    def on_installation_detected(self, reason: str):
        """Обработка обнаружения установки программы"""
        logger.critical(f"INSTALLATION DETECTED: {reason}")
        
        # Отправляем уведомление на сервер асинхронно
        if self.client_thread.client and self.client_thread.loop:
            logger.info("Sending installation alert to server")
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.client_thread.client.send_installation_alert(reason),
                    self.client_thread.loop
                )
                # Даем немного времени на отправку (неблокирующая проверка)
                try:
                    future.result(timeout=0.5)
                    logger.info("Installation alert sent successfully")
                except TimeoutError:
                    # Таймаут - отправка все еще может быть в процессе
                    logger.warning("Installation alert send timed out after 0.5s (may still be sending in background)")
                except Exception as e:
                    # Реальная ошибка отправки
                    logger.error(f"Failed to send installation alert: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Failed to schedule installation alert send: {e}", exc_info=True)
        else:
            logger.warning("Cannot send installation alert - client not available")
        
        # Прерываем текущую сессию если она есть
        if self.timer_widget:
            self.timer_widget.force_close()
            self.timer_widget = None
        
        if self.lock_screen:
            self.lock_screen.close()
            self.lock_screen = None
        
        # Показываем красный экран тревоги
        from .red_alert_screen import RedAlertLockScreen
        self.red_alert_screen = RedAlertLockScreen(
            reason=reason,
            alert_volume=self.config.alert_volume,
            config=self.config
        )
        # Подключаем сигнал разблокировки
        self.red_alert_screen.unlocked.connect(self.on_red_alert_unlocked)
        self.red_alert_screen.show()
    
    def on_red_alert_unlocked(self):
        """Обработка разблокировки красного экрана тревоги"""
        logger.info("Red alert screen unlocked by admin password")
        if self.red_alert_screen:
            self.red_alert_screen.force_close()
            self.red_alert_screen = None

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Останавливаем мониторинг установки
        if self.installation_monitor:
            self.installation_monitor.stop()
        
        # Минимизируем в трей вместо закрытия
        event.ignore()
        self.hide()
        
        # Показываем уведомление при первом сворачивании
        if not hasattr(self, '_tray_notification_shown'):
            self.tray_icon.showMessage(
                "LibLocker Client",
                "Клиент свернут в системный трей. Для выхода используйте контекстное меню.",
                QSystemTrayIcon.MessageIcon.Information,
                3000  # 3 секунды
            )
            self._tray_notification_shown = True


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

