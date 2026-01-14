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
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Быстрые кнопки
        quick_buttons = QHBoxLayout()
        self.btn_30min = QPushButton("+30 минут")
        self.btn_unlimited = QPushButton("Безлимит")
        quick_buttons.addWidget(self.btn_30min)
        quick_buttons.addWidget(self.btn_unlimited)
        layout.addLayout(quick_buttons)

        # Произвольное время
        custom_group = QGroupBox("Произвольное время")
        custom_layout = QFormLayout()

        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 24)
        custom_layout.addRow("Часы:", self.hours_spin)

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        custom_layout.addRow("Минуты:", self.minutes_spin)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Кнопки подтверждения
        buttons = QHBoxLayout()
        self.btn_ok = QPushButton("Создать")
        self.btn_cancel = QPushButton("Отмена")
        buttons.addWidget(self.btn_ok)
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
        self.server = LibLockerServer()
        self.server_thread = None

        # Таймеры
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_clients_table)
        self.update_timer.start(1000)  # Обновление каждую секунду

        self.init_ui()
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

        # Таблица клиентов
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(6)
        self.clients_table.setHorizontalHeaderLabels([
            "ID", "Имя", "IP", "Статус", "Время сессии", "Действия"
        ])
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.clients_table)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        self.btn_start_session = QPushButton("Начать сессию")
        self.btn_start_session.clicked.connect(self.start_session)
        buttons_layout.addWidget(self.btn_start_session)

        self.btn_stop_session = QPushButton("Остановить сессию")
        self.btn_stop_session.clicked.connect(self.stop_session)
        buttons_layout.addWidget(self.btn_stop_session)

        self.btn_shutdown = QPushButton("Выключить ПК")
        self.btn_shutdown.clicked.connect(self.shutdown_client)
        buttons_layout.addWidget(self.btn_shutdown)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        return widget

    def create_stats_tab(self) -> QWidget:
        """Создать вкладку статистики"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Таблица сессий
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(6)
        self.sessions_table.setHorizontalHeaderLabels([
            "ID", "Клиент", "Начало", "Окончание", "Длительность", "Стоимость"
        ])
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.sessions_table)

        # Кнопки
        buttons_layout = QHBoxLayout()

        self.btn_export_pdf = QPushButton("Экспорт в PDF")
        self.btn_export_pdf.clicked.connect(self.export_to_pdf)
        buttons_layout.addWidget(self.btn_export_pdf)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # Обновление таблицы сессий
        self.update_sessions_table()

        return widget

    def create_settings_tab(self) -> QWidget:
        """Создать вкладку настроек"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

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

        # Кнопка сохранения
        self.btn_save_settings = QPushButton("Сохранить настройки")
        self.btn_save_settings.clicked.connect(self.save_settings)
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
        # TODO: Реализовать сохранение настроек в БД
        QMessageBox.information(self, "Успех", "Настройки сохранены")

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

