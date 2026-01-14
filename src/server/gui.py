"""
GUI для серверного приложения LibLocker
Панель администратора на PyQt6
"""
import sys
import asyncio
import logging
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QDialog,
    QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit, QMessageBox,
    QTabWidget, QGroupBox, QFormLayout, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QColor
import qasync

from .server import LibLockerServer
from ..shared.database import Database, ClientModel, SessionModel
from ..shared.models import ClientStatus
from ..shared.config import ServerConfig
from ..shared.utils import hash_password

logger = logging.getLogger(__name__)


class ServerThread(QThread):
    """Поток для запуска WebSocket сервера"""

    def __init__(self, server: LibLockerServer):
        super().__init__()
        self.server = server
        self.loop = None

    def run(self):
        """Запуск сервера в отдельном потоке"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.server.run())


class SessionDialog(QDialog):
    """Диалог создания сессии"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание сессии")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Заголовок
        header = QLabel("Выберите длительность сессии")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Быстрые кнопки
        quick_group = QGroupBox("Быстрый выбор")
        quick_buttons = QHBoxLayout()
        
        self.btn_30min = QPushButton("⏱️ +30 минут")
        self.btn_30min.setMinimumHeight(50)
        self.btn_30min.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        quick_buttons.addWidget(self.btn_30min)
        
        self.btn_unlimited = QPushButton("♾️ Безлимит")
        self.btn_unlimited.setMinimumHeight(50)
        self.btn_unlimited.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        quick_buttons.addWidget(self.btn_unlimited)
        
        quick_group.setLayout(quick_buttons)
        layout.addWidget(quick_group)

        # Произвольное время
        custom_group = QGroupBox("Произвольное время")
        custom_layout = QFormLayout()

        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 24)
        self.hours_spin.setMinimumHeight(30)
        custom_layout.addRow("Часы:", self.hours_spin)

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setMinimumHeight(30)
        custom_layout.addRow("Минуты:", self.minutes_spin)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Кнопки подтверждения
        buttons = QHBoxLayout()
        
        self.btn_ok = QPushButton("✅ Создать")
        self.btn_ok.setMinimumHeight(40)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        buttons.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("❌ Отмена")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        buttons.addWidget(self.btn_cancel)
        
        layout.addLayout(buttons)

        self.setLayout(layout)

        # Подключение сигналов
        self.btn_30min.clicked.connect(lambda: self.set_time(0, 30))
        self.btn_unlimited.clicked.connect(self.set_unlimited)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.is_unlimited = False

    def set_time(self, hours: int, minutes: int):
        """Установить время"""
        self.hours_spin.setValue(hours)
        self.minutes_spin.setValue(minutes)
        self.is_unlimited = False

    def set_unlimited(self):
        """Установить безлимит"""
        self.is_unlimited = True
        self.hours_spin.setValue(0)
        self.minutes_spin.setValue(0)

    def get_duration(self) -> tuple:
        """Получить длительность сессии"""
        if self.is_unlimited:
            return (0, True)
        total_minutes = self.hours_spin.value() * 60 + self.minutes_spin.value()
        return (total_minutes, False)


class MainWindow(QMainWindow):
    """Главное окно серверного приложения"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibLocker - Панель администратора")
        self.setMinimumSize(1000, 600)

        # Инициализация
        self.db = Database()
        self.config = ServerConfig()
        self.server = LibLockerServer()
        self.server_thread = None

        # Таймеры
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_clients_table)
        self.update_timer.start(1000)  # Обновление каждую секунду

        self.init_ui()
        self.load_settings()
        self.start_server()

    def init_ui(self):
        """Инициализация интерфейса"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Вкладки
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Вкладка "Клиенты"
        clients_tab = self.create_clients_tab()
        tabs.addTab(clients_tab, "Клиенты")

        # Вкладка "Статистика"
        stats_tab = self.create_stats_tab()
        tabs.addTab(stats_tab, "Статистика")

        # Вкладка "Настройки"
        settings_tab = self.create_settings_tab()
        tabs.addTab(settings_tab, "Настройки")

        # Статус бар
        self.statusBar().showMessage("Сервер запускается...")

    def create_clients_tab(self) -> QWidget:
        """Создать вкладку клиентов"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Заголовок
        header_label = QLabel("Управление клиентами")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(header_label)

        # Таблица клиентов
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(6)
        self.clients_table.setHorizontalHeaderLabels([
            "ID", "Имя", "IP", "Статус", "Время сессии", "Действия"
        ])
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.clients_table.setAlternatingRowColors(True)
        self.clients_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.clients_table)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        self.btn_start_session = QPushButton("🎮 Начать сессию")
        self.btn_start_session.clicked.connect(self.start_session)
        self.btn_start_session.setMinimumHeight(40)
        self.btn_start_session.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        buttons_layout.addWidget(self.btn_start_session)

        self.btn_stop_session = QPushButton("⏹️ Остановить сессию")
        self.btn_stop_session.clicked.connect(self.stop_session)
        self.btn_stop_session.setMinimumHeight(40)
        self.btn_stop_session.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1160a;
            }
        """)
        buttons_layout.addWidget(self.btn_stop_session)

        self.btn_shutdown = QPushButton("🔌 Выключить ПК")
        self.btn_shutdown.clicked.connect(self.shutdown_client)
        self.btn_shutdown.setMinimumHeight(40)
        self.btn_shutdown.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:pressed {
                background-color: #cc7a00;
            }
        """)
        buttons_layout.addWidget(self.btn_shutdown)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        return widget

    def create_stats_tab(self) -> QWidget:
        """Создать вкладку статистики"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Заголовок
        header_label = QLabel("История сессий")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(header_label)

        # Таблица сессий
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(6)
        self.sessions_table.setHorizontalHeaderLabels([
            "ID", "Клиент", "Начало", "Окончание", "Длительность", "Стоимость"
        ])
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.sessions_table)

        # Кнопки
        buttons_layout = QHBoxLayout()

        self.btn_export_pdf = QPushButton("📄 Экспорт в PDF")
        self.btn_export_pdf.clicked.connect(self.export_to_pdf)
        self.btn_export_pdf.setMinimumHeight(40)
        self.btn_export_pdf.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        buttons_layout.addWidget(self.btn_export_pdf)

        self.btn_refresh_stats = QPushButton("🔄 Обновить")
        self.btn_refresh_stats.clicked.connect(self.update_sessions_table)
        self.btn_refresh_stats.setMinimumHeight(40)
        self.btn_refresh_stats.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        buttons_layout.addWidget(self.btn_refresh_stats)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # Обновление таблицы сессий
        self.update_sessions_table()

        return widget

    def create_settings_tab(self) -> QWidget:
        """Создать вкладку настроек"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Группа безопасности
        security_group = QGroupBox("Безопасность")
        security_layout = QVBoxLayout()

        # Статус пароля
        password_status_layout = QHBoxLayout()
        password_status_label = QLabel("Пароль администратора:")
        self.password_status = QLabel()
        self.update_password_status()
        password_status_layout.addWidget(password_status_label)
        password_status_layout.addWidget(self.password_status)
        password_status_layout.addStretch()
        security_layout.addLayout(password_status_layout)

        # Поля для ввода пароля
        password_form = QFormLayout()
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setPlaceholderText("Введите новый пароль")
        self.new_password_input.textChanged.connect(self.check_password_strength)
        password_form.addRow("Новый пароль:", self.new_password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Подтвердите пароль")
        password_form.addRow("Подтверждение:", self.confirm_password_input)

        # Индикатор надежности пароля
        self.password_strength_label = QLabel()
        self.password_strength_label.setStyleSheet("color: gray; font-style: italic;")
        password_form.addRow("Надежность:", self.password_strength_label)

        security_layout.addLayout(password_form)

        # Кнопка установки пароля
        btn_set_password_layout = QHBoxLayout()
        self.btn_set_password = QPushButton("Установить пароль")
        self.btn_set_password.clicked.connect(self.set_admin_password)
        self.btn_set_password.setMinimumHeight(35)
        btn_set_password_layout.addWidget(self.btn_set_password)
        btn_set_password_layout.addStretch()
        security_layout.addLayout(btn_set_password_layout)

        security_group.setLayout(security_layout)
        layout.addWidget(security_group)

        # Группа тарификации
        tariff_group = QGroupBox("Тарификация")
        tariff_layout = QFormLayout()

        self.free_mode_check = QCheckBox("Бесплатный режим")
        self.free_mode_check.setChecked(True)
        tariff_layout.addRow("", self.free_mode_check)

        self.hourly_rate_spin = QDoubleSpinBox()
        self.hourly_rate_spin.setRange(0, 10000)
        self.hourly_rate_spin.setSuffix(" руб./час")
        tariff_layout.addRow("Стоимость:", self.hourly_rate_spin)

        self.rounding_spin = QSpinBox()
        self.rounding_spin.setRange(1, 60)
        self.rounding_spin.setValue(5)
        self.rounding_spin.setSuffix(" мин")
        tariff_layout.addRow("Округление:", self.rounding_spin)

        tariff_group.setLayout(tariff_layout)
        layout.addWidget(tariff_group)

        # Группа сети
        network_group = QGroupBox("Сетевые настройки")
        network_layout = QFormLayout()

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8765)
        network_layout.addRow("Порт:", self.port_spin)

        self.web_port_spin = QSpinBox()
        self.web_port_spin.setRange(1024, 65535)
        self.web_port_spin.setValue(8080)
        network_layout.addRow("Веб-порт:", self.web_port_spin)

        network_group.setLayout(network_layout)
        layout.addWidget(network_group)

        # Кнопка сохранения общих настроек
        self.btn_save_settings = QPushButton("Сохранить настройки")
        self.btn_save_settings.clicked.connect(self.save_settings)
        self.btn_save_settings.setMinimumHeight(35)
        layout.addWidget(self.btn_save_settings)

        layout.addStretch()

        return widget

    def start_server(self):
        """Запуск WebSocket сервера"""
        self.server_thread = ServerThread(self.server)
        self.server_thread.start()
        self.statusBar().showMessage("Сервер запущен")
        logger.info("Server thread started")

    def update_clients_table(self):
        """Обновление таблицы клиентов"""
        db_session = self.db.get_session()
        try:
            clients = db_session.query(ClientModel).all()
            self.clients_table.setRowCount(len(clients))

            for row, client in enumerate(clients):
                self.clients_table.setItem(row, 0, QTableWidgetItem(str(client.id)))
                self.clients_table.setItem(row, 1, QTableWidgetItem(client.name))
                self.clients_table.setItem(row, 2, QTableWidgetItem(client.ip_address or ""))

                # Статус с цветом
                status_item = QTableWidgetItem(client.status)
                if client.status == ClientStatus.ONLINE.value:
                    status_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
                elif client.status == ClientStatus.IN_SESSION.value:
                    status_item.setBackground(QColor(173, 216, 230))  # Светло-голубой
                else:
                    status_item.setBackground(QColor(211, 211, 211))  # Светло-серый

                self.clients_table.setItem(row, 3, status_item)

                # Время сессии (TODO: реализовать подсчет)
                self.clients_table.setItem(row, 4, QTableWidgetItem(""))

                # Действия (пока пусто)
                self.clients_table.setItem(row, 5, QTableWidgetItem(""))

        except Exception as e:
            logger.error(f"Error updating clients table: {e}")
        finally:
            db_session.close()

    def update_sessions_table(self):
        """Обновление таблицы сессий"""
        db_session = self.db.get_session()
        try:
            sessions = db_session.query(SessionModel).order_by(
                SessionModel.start_time.desc()
            ).limit(100).all()

            self.sessions_table.setRowCount(len(sessions))

            for row, session in enumerate(sessions):
                self.sessions_table.setItem(row, 0, QTableWidgetItem(str(session.id)))

                # Имя клиента
                client = db_session.query(ClientModel).filter_by(id=session.client_id).first()
                client_name = client.name if client else "Unknown"
                self.sessions_table.setItem(row, 1, QTableWidgetItem(client_name))

                # Время начала
                start_time = session.start_time.strftime("%Y-%m-%d %H:%M:%S")
                self.sessions_table.setItem(row, 2, QTableWidgetItem(start_time))

                # Время окончания
                end_time = session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "Активна"
                self.sessions_table.setItem(row, 3, QTableWidgetItem(end_time))

                # Длительность
                duration = f"{session.actual_duration} мин" if session.actual_duration else "-"
                self.sessions_table.setItem(row, 4, QTableWidgetItem(duration))

                # Стоимость
                cost = f"{session.cost:.2f} руб." if session.cost > 0 else "Бесплатно"
                self.sessions_table.setItem(row, 5, QTableWidgetItem(cost))

        except Exception as e:
            logger.error(f"Error updating sessions table: {e}")
        finally:
            db_session.close()

    def start_session(self):
        """Начать сессию для выбранного клиента"""
        selected_rows = self.clients_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента")
            return

        row = selected_rows[0].row()
        client_id = int(self.clients_table.item(row, 0).text())

        # Открываем диалог создания сессии
        dialog = SessionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            duration, is_unlimited = dialog.get_duration()

            # Получаем настройки тарификации
            free_mode = self.free_mode_check.isChecked()
            hourly_rate = self.hourly_rate_spin.value()

            # Запускаем сессию через asyncio
            asyncio.run_coroutine_threadsafe(
                self.server.start_session(
                    client_id, duration, is_unlimited, hourly_rate, free_mode
                ),
                self.server_thread.loop
            )

            QMessageBox.information(self, "Успех", "Сессия начата")

    def stop_session(self):
        """Остановить сессию для выбранного клиента"""
        selected_rows = self.clients_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента")
            return

        row = selected_rows[0].row()
        client_id = int(self.clients_table.item(row, 0).text())

        # Останавливаем сессию
        asyncio.run_coroutine_threadsafe(
            self.server.stop_session(client_id),
            self.server_thread.loop
        )

        QMessageBox.information(self, "Успех", "Сессия остановлена")

    def shutdown_client(self):
        """Выключить компьютер клиента"""
        selected_rows = self.clients_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента")
            return

        row = selected_rows[0].row()
        client_id = int(self.clients_table.item(row, 0).text())

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите выключить этот компьютер?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            asyncio.run_coroutine_threadsafe(
                self.server.shutdown_client(client_id),
                self.server_thread.loop
            )
            QMessageBox.information(self, "Успех", "Команда выключения отправлена")

    def save_settings(self):
        """Сохранить настройки"""
        try:
            # Сохранение настроек тарификации
            self.config.set('tariff', 'free_mode', str(self.free_mode_check.isChecked()).lower())
            self.config.set('tariff', 'hourly_rate', str(self.hourly_rate_spin.value()))
            self.config.set('tariff', 'rounding_minutes', str(self.rounding_spin.value()))

            # Сохранение сетевых настроек (требует перезапуска)
            self.config.set('server', 'port', str(self.port_spin.value()))
            self.config.set('server', 'web_port', str(self.web_port_spin.value()))

            self.config.save()
            QMessageBox.information(self, "Успех", "Настройки сохранены\n\nСетевые настройки вступят в силу после перезапуска сервера.")
            logger.info("Settings saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки:\n{str(e)}")
            logger.error(f"Error saving settings: {e}")

    def load_settings(self):
        """Загрузить настройки из конфига"""
        try:
            self.free_mode_check.setChecked(self.config.free_mode)
            self.hourly_rate_spin.setValue(self.config.hourly_rate)
            self.rounding_spin.setValue(self.config.rounding_minutes)
            self.port_spin.setValue(self.config.port)
            self.web_port_spin.setValue(self.config.web_port)
            logger.info("Settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def update_password_status(self):
        """Обновить статус пароля"""
        if self.config.admin_password_hash:
            self.password_status.setText("✅ Установлен")
            self.password_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.password_status.setText("❌ Не установлен")
            self.password_status.setStyleSheet("color: red; font-weight: bold;")

    def check_password_strength(self):
        """Проверить надежность пароля"""
        password = self.new_password_input.text()
        
        if not password:
            self.password_strength_label.setText("")
            self.password_strength_label.setStyleSheet("color: gray; font-style: italic;")
            return

        strength = 0
        feedback = []

        # Длина
        if len(password) >= 8:
            strength += 1
        else:
            feedback.append("минимум 8 символов")

        # Наличие цифр
        if any(c.isdigit() for c in password):
            strength += 1
        else:
            feedback.append("добавьте цифры")

        # Наличие букв
        if any(c.isalpha() for c in password):
            strength += 1
        else:
            feedback.append("добавьте буквы")

        # Наличие спецсимволов
        if any(not c.isalnum() for c in password):
            strength += 1

        # Наличие заглавных и строчных букв
        if any(c.isupper() for c in password) and any(c.islower() for c in password):
            strength += 1

        # Отображение надежности
        if strength <= 2:
            self.password_strength_label.setText("⚠️ Слабый" + (" (" + ", ".join(feedback) + ")" if feedback else ""))
            self.password_strength_label.setStyleSheet("color: red; font-weight: bold;")
        elif strength == 3:
            self.password_strength_label.setText("⚡ Средний")
            self.password_strength_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.password_strength_label.setText("✅ Надежный")
            self.password_strength_label.setStyleSheet("color: green; font-weight: bold;")

    def set_admin_password(self):
        """Установить пароль администратора"""
        password = self.new_password_input.text()
        confirm = self.confirm_password_input.text()

        # Валидация
        if not password:
            QMessageBox.warning(self, "Ошибка", "Введите пароль")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен содержать минимум 6 символов")
            return

        if password != confirm:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return

        # Подтверждение
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите установить новый пароль администратора?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Хеширование пароля
                hashed = hash_password(password)
                
                # Сохранение в конфиг
                self.config.admin_password_hash = hashed
                self.config.save()

                # Очистка полей
                self.new_password_input.clear()
                self.confirm_password_input.clear()
                self.password_strength_label.setText("")

                # Обновление статуса
                self.update_password_status()

                QMessageBox.information(self, "Успех", "Пароль администратора успешно установлен!")
                logger.info("Admin password set successfully")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось установить пароль:\n{str(e)}")
                logger.error(f"Error setting admin password: {e}")

    def export_to_pdf(self):
        """Экспорт отчета в PDF"""
        # TODO: Реализовать экспорт в PDF
        QMessageBox.information(self, "Информация", "Функция экспорта в разработке")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        reply = QMessageBox.question(
            self, "Выход",
            "Вы уверены, что хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Остановка сервера
            if self.server_thread:
                self.server_thread.terminate()
                self.server_thread.wait()
            event.accept()
        else:
            event.ignore()


def main():
    """Точка входа в приложение"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

