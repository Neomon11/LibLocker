"""
GUI для серверного приложения LibLocker
Панель администратора на PyQt6
"""
import sys
import asyncio
import logging
import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QDialog,
    QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit, QMessageBox,
    QTabWidget, QGroupBox, QFormLayout, QHeaderView, QDateEdit, QComboBox,
    QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QDate
from PyQt6.QtGui import QIcon, QColor
import qasync

from .server import LibLockerServer
from ..shared.database import Database, ClientModel, SessionModel
from ..shared.models import ClientStatus
from ..shared.config import ServerConfig
from ..shared.utils import hash_password

logger = logging.getLogger(__name__)

# Constants
MIN_PASSWORD_LENGTH = 8
RECOMMENDED_PASSWORD_LENGTH = 8

# Button styles
BUTTON_STYLE_PRIMARY = """
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
"""

BUTTON_STYLE_DANGER = """
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
"""

BUTTON_STYLE_WARNING = """
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
"""

BUTTON_STYLE_INFO = """
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
"""

BUTTON_STYLE_SECONDARY = """
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
    QPushButton:pressed {
        background-color: #424242;
    }
"""

BUTTON_STYLE_PURPLE = """
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
    QPushButton:pressed {
        background-color: #6A1B9A;
    }
"""

TABLE_STYLE = """
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
"""


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
        self.btn_30min.setStyleSheet(BUTTON_STYLE_INFO)
        quick_buttons.addWidget(self.btn_30min)
        
        self.btn_unlimited = QPushButton("♾️ Безлимит")
        self.btn_unlimited.setMinimumHeight(50)
        self.btn_unlimited.setStyleSheet(BUTTON_STYLE_PURPLE)
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
        self.btn_ok.setStyleSheet(BUTTON_STYLE_PRIMARY)
        buttons.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("❌ Отмена")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setStyleSheet(BUTTON_STYLE_SECONDARY)
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


class DetailedClientStatisticsDialog(QDialog):
    """Диалог детальной статистики по клиенту"""

    def __init__(self, client: ClientModel, db: Database, parent=None):
        super().__init__(parent)
        self.client = client
        self.db = db
        self.setWindowTitle(f"Статистика клиента: {client.name}")
        self.setModal(True)
        self.setMinimumSize(900, 600)
        self.init_ui()
        self.update_statistics()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Заголовок с информацией о клиенте
        header = QLabel(f"📊 Детальная статистика: {self.client.name}")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Фильтры
        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout()

        # Фильтр по периоду
        filter_layout.addWidget(QLabel("Период:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Все время", "Сегодня", "Эта неделя", "Этот месяц", "Произвольный период"])
        self.period_combo.currentIndexChanged.connect(self.on_period_changed)
        filter_layout.addWidget(self.period_combo)

        # Даты для произвольного периода
        filter_layout.addWidget(QLabel("От:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setEnabled(False)
        self.start_date.dateChanged.connect(self.update_statistics)
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("До:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setEnabled(False)
        self.end_date.dateChanged.connect(self.update_statistics)
        filter_layout.addWidget(self.end_date)

        filter_layout.addStretch()

        # Кнопка применить фильтр
        btn_apply_filter = QPushButton("🔍 Применить")
        btn_apply_filter.clicked.connect(self.update_statistics)
        btn_apply_filter.setStyleSheet(BUTTON_STYLE_INFO)
        filter_layout.addWidget(btn_apply_filter)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Сводка
        summary_group = QGroupBox("Сводка")
        summary_layout = QHBoxLayout()

        self.total_sessions_label = QLabel("Сессий: 0")
        self.total_sessions_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        summary_layout.addWidget(self.total_sessions_label)

        self.total_time_label = QLabel("Общее время: 0 мин")
        self.total_time_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        summary_layout.addWidget(self.total_time_label)

        self.total_cost_label = QLabel("Общая стоимость: 0.00 руб")
        self.total_cost_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        summary_layout.addWidget(self.total_cost_label)

        summary_layout.addStretch()
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Таблица сессий
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(5)
        self.sessions_table.setHorizontalHeaderLabels([
            "ID", "Начало", "Окончание", "Длительность (мин)", "Стоимость (руб)"
        ])
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.setStyleSheet(TABLE_STYLE)
        layout.addWidget(self.sessions_table)

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        btn_export = QPushButton("📄 Экспорт в PDF")
        btn_export.clicked.connect(self.export_client_stats)
        btn_export.setMinimumHeight(35)
        btn_export.setMinimumWidth(200)
        btn_export.setStyleSheet(BUTTON_STYLE_INFO)
        buttons_layout.addWidget(btn_export)

        btn_clear = QPushButton("🗑️ Очистить статистику")
        btn_clear.clicked.connect(self.clear_statistics)
        btn_clear.setMinimumHeight(35)
        btn_clear.setMinimumWidth(200)
        btn_clear.setStyleSheet(BUTTON_STYLE_DANGER)
        buttons_layout.addWidget(btn_clear)

        btn_close = QPushButton("✖️ Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_close.setMinimumHeight(35)
        btn_close.setMinimumWidth(200)
        btn_close.setStyleSheet(BUTTON_STYLE_SECONDARY)
        buttons_layout.addWidget(btn_close)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def on_period_changed(self, index):
        """Обработка изменения периода"""
        # Включаем/выключаем поля дат для произвольного периода
        custom_period = (index == 4)  # "Произвольный период"
        self.start_date.setEnabled(custom_period)
        self.end_date.setEnabled(custom_period)
        
        if not custom_period:
            self.update_statistics()

    def get_date_range(self):
        """Получить диапазон дат на основе выбранного фильтра"""
        period_index = self.period_combo.currentIndex()
        current_date = datetime.now()
        
        if period_index == 0:  # Все время
            return None, None
        elif period_index == 1:  # Сегодня
            start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = current_date
            return start, end
        elif period_index == 2:  # Эта неделя
            start = current_date - timedelta(days=current_date.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = current_date
            return start, end
        elif period_index == 3:  # Этот месяц
            start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = current_date
            return start, end
        elif period_index == 4:  # Произвольный период
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()
            start = datetime.combine(start_date, datetime.min.time())
            end = datetime.combine(end_date, datetime.max.time())
            return start, end
        
        return None, None

    def update_statistics(self):
        """Обновление статистики"""
        db_session = self.db.get_session()
        try:
            # Получаем диапазон дат
            start_date, end_date = self.get_date_range()
            
            # Базовый запрос
            query = db_session.query(SessionModel).filter_by(client_id=self.client.id)
            
            # Применяем фильтр по датам
            if start_date:
                query = query.filter(SessionModel.start_time >= start_date)
            if end_date:
                query = query.filter(SessionModel.start_time <= end_date)
            
            # Сортируем по времени начала
            sessions = query.order_by(SessionModel.start_time.desc()).all()
            
            # Обновляем таблицу
            self.sessions_table.setRowCount(len(sessions))
            
            total_sessions = len(sessions)
            total_duration = 0
            total_cost = 0.0
            
            for row, session in enumerate(sessions):
                self.sessions_table.setItem(row, 0, QTableWidgetItem(str(session.id)))
                
                start_time = session.start_time.strftime("%Y-%m-%d %H:%M:%S")
                self.sessions_table.setItem(row, 1, QTableWidgetItem(start_time))
                
                end_time = session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "Активна"
                self.sessions_table.setItem(row, 2, QTableWidgetItem(end_time))
                
                duration = session.actual_duration if session.actual_duration else 0
                self.sessions_table.setItem(row, 3, QTableWidgetItem(str(duration)))
                total_duration += duration
                
                cost = session.cost if session.cost else 0.0
                self.sessions_table.setItem(row, 4, QTableWidgetItem(f"{cost:.2f}"))
                total_cost += cost
            
            # Обновляем сводку
            self.total_sessions_label.setText(f"Сессий: {total_sessions}")
            self.total_time_label.setText(f"Общее время: {total_duration} мин ({total_duration // 60} ч {total_duration % 60} мин)")
            self.total_cost_label.setText(f"Общая стоимость: {total_cost:.2f} руб")
            
        except Exception as e:
            logger.error(f"Error updating client statistics: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить статистику:\n{str(e)}")
        finally:
            db_session.close()

    def export_client_stats(self):
        """Экспорт статистики клиента в PDF"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            
            # Генерируем имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"statistics_{self.client.name}_{timestamp}.pdf"
            
            # Создаем PDF
            doc = SimpleDocTemplate(filename, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Заголовок
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=30,
                alignment=1  # Center
            )
            
            title = Paragraph(f"Статистика клиента: {self.client.name}", title_style)
            elements.append(title)
            elements.append(Spacer(1, 12))
            
            # Период
            start_date, end_date = self.get_date_range()
            if start_date and end_date:
                period_text = f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
            else:
                period_text = "Период: Все время"
            
            period = Paragraph(period_text, styles['Normal'])
            elements.append(period)
            elements.append(Spacer(1, 12))
            
            # Сводная информация
            summary_data = [
                ['Метрика', 'Значение'],
                ['Количество сессий', self.total_sessions_label.text().split(': ')[1]],
                ['Общее время', self.total_time_label.text().split(': ')[1]],
                ['Общая стоимость', self.total_cost_label.text().split(': ')[1]]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(summary_table)
            elements.append(Spacer(1, 20))
            
            # Детальная таблица сессий
            details_label = Paragraph("Детальная информация о сессиях", styles['Heading2'])
            elements.append(details_label)
            elements.append(Spacer(1, 12))
            
            # Данные таблицы
            table_data = [['ID', 'Начало', 'Окончание', 'Длительность', 'Стоимость']]
            
            for row in range(self.sessions_table.rowCount()):
                row_data = []
                for col in range(self.sessions_table.columnCount()):
                    item = self.sessions_table.item(row, col)
                    row_data.append(item.text() if item else "")
                table_data.append(row_data)
            
            sessions_table = Table(table_data, colWidths=[0.5*inch, 1.5*inch, 1.5*inch, 1.2*inch, 1.2*inch])
            sessions_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(sessions_table)
            
            # Генерируем PDF
            doc.build(elements)
            
            QMessageBox.information(self, "Успех", f"Статистика экспортирована в файл:\n{filename}")
            logger.info(f"Client statistics exported to {filename}")
            
        except ImportError:
            QMessageBox.warning(
                self, "Ошибка", 
                "Для экспорта в PDF требуется библиотека reportlab.\nУстановите её командой: pip install reportlab"
            )
        except Exception as e:
            logger.error(f"Error exporting client statistics: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать статистику:\n{str(e)}")

    def clear_statistics(self):
        """Очистка статистики клиента"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите очистить статистику клиента {self.client.name}?\n\n"
            "Это действие удалит все записи о сессиях для выбранного периода.\n"
            "Это действие необратимо!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            db_session = self.db.get_session()
            try:
                # Получаем диапазон дат
                start_date, end_date = self.get_date_range()
                
                # Базовый запрос
                query = db_session.query(SessionModel).filter_by(client_id=self.client.id)
                
                # Применяем фильтр по датам
                if start_date:
                    query = query.filter(SessionModel.start_time >= start_date)
                if end_date:
                    query = query.filter(SessionModel.start_time <= end_date)
                
                # Удаляем сессии
                count = query.delete()
                db_session.commit()
                
                QMessageBox.information(self, "Успех", f"Удалено записей: {count}")
                logger.info(f"Cleared {count} session records for client {self.client.id}")
                
                # Обновляем отображение
                self.update_statistics()
                
            except Exception as e:
                logger.error(f"Error clearing client statistics: {e}")
                db_session.rollback()
                QMessageBox.critical(self, "Ошибка", f"Не удалось очистить статистику:\n{str(e)}")
            finally:
                db_session.close()


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
        self.clients_table.setStyleSheet(TABLE_STYLE)
        layout.addWidget(self.clients_table)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        self.btn_start_session = QPushButton("🎮 Начать сессию")
        self.btn_start_session.clicked.connect(self.start_session)
        self.btn_start_session.setMinimumHeight(40)
        self.btn_start_session.setMinimumWidth(200)
        self.btn_start_session.setStyleSheet(BUTTON_STYLE_PRIMARY)
        buttons_layout.addWidget(self.btn_start_session)

        self.btn_edit_session = QPushButton("⏱️ Изменить время")
        self.btn_edit_session.clicked.connect(self.edit_session_time)
        self.btn_edit_session.setMinimumHeight(40)
        self.btn_edit_session.setMinimumWidth(200)
        self.btn_edit_session.setStyleSheet(BUTTON_STYLE_INFO)
        buttons_layout.addWidget(self.btn_edit_session)

        self.btn_stop_session = QPushButton("⏹️ Остановить сессию")
        self.btn_stop_session.clicked.connect(self.stop_session)
        self.btn_stop_session.setMinimumHeight(40)
        self.btn_stop_session.setMinimumWidth(200)
        self.btn_stop_session.setStyleSheet(BUTTON_STYLE_DANGER)
        buttons_layout.addWidget(self.btn_stop_session)

        self.btn_shutdown = QPushButton("🔌 Выключить ПК")
        self.btn_shutdown.clicked.connect(self.shutdown_client)
        self.btn_shutdown.setMinimumHeight(40)
        self.btn_shutdown.setMinimumWidth(200)
        self.btn_shutdown.setStyleSheet(BUTTON_STYLE_WARNING)
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

        # Вкладки для разных представлений
        stats_tabs = QTabWidget()
        layout.addWidget(stats_tabs)

        # Вкладка "Все сессии"
        all_sessions_widget = QWidget()
        all_sessions_layout = QVBoxLayout(all_sessions_widget)
        
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(6)
        self.sessions_table.setHorizontalHeaderLabels([
            "ID", "Клиент", "Начало", "Окончание", "Длительность", "Стоимость"
        ])
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.setStyleSheet(TABLE_STYLE)
        all_sessions_layout.addWidget(self.sessions_table)
        
        stats_tabs.addTab(all_sessions_widget, "Все сессии")

        # Вкладка "По клиентам"
        by_client_widget = QWidget()
        by_client_layout = QVBoxLayout(by_client_widget)
        
        self.client_stats_table = QTableWidget()
        self.client_stats_table.setColumnCount(5)
        self.client_stats_table.setHorizontalHeaderLabels([
            "Клиент", "Количество сессий", "Общее время (мин)", "Средняя длительность (мин)", "Общая стоимость (руб)"
        ])
        self.client_stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.client_stats_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.client_stats_table.setAlternatingRowColors(True)
        self.client_stats_table.setStyleSheet(TABLE_STYLE)
        self.client_stats_table.doubleClicked.connect(self.show_detailed_client_stats)
        by_client_layout.addWidget(self.client_stats_table)
        
        stats_tabs.addTab(by_client_widget, "По клиентам")

        # Кнопки
        buttons_layout = QHBoxLayout()

        self.btn_export_pdf = QPushButton("📄 Экспорт в PDF")
        self.btn_export_pdf.clicked.connect(self.export_to_pdf)
        self.btn_export_pdf.setMinimumHeight(40)
        self.btn_export_pdf.setMinimumWidth(250)
        self.btn_export_pdf.setStyleSheet(BUTTON_STYLE_INFO)
        buttons_layout.addWidget(self.btn_export_pdf)

        self.btn_clear_all_stats = QPushButton("🗑️ Очистить всю статистику")
        self.btn_clear_all_stats.clicked.connect(self.clear_all_statistics)
        self.btn_clear_all_stats.setMinimumHeight(40)
        self.btn_clear_all_stats.setMinimumWidth(250)
        self.btn_clear_all_stats.setStyleSheet(BUTTON_STYLE_DANGER)
        buttons_layout.addWidget(self.btn_clear_all_stats)

        self.btn_refresh_stats = QPushButton("🔄 Обновить")
        self.btn_refresh_stats.clicked.connect(self.update_sessions_table)
        self.btn_refresh_stats.setMinimumHeight(40)
        self.btn_refresh_stats.setMinimumWidth(250)
        self.btn_refresh_stats.setStyleSheet(BUTTON_STYLE_PRIMARY)
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

            # Получаем список подключенных клиентов
            connected_client_ids = {info['client_id'] for info in self.server.connected_clients.values()}

            for row, client in enumerate(clients):
                self.clients_table.setItem(row, 0, QTableWidgetItem(str(client.id)))
                self.clients_table.setItem(row, 1, QTableWidgetItem(client.name))
                self.clients_table.setItem(row, 2, QTableWidgetItem(client.ip_address or ""))

                # Определяем реальный статус на основе подключения
                is_connected = client.id in connected_client_ids
                
                # Локализация статуса
                if is_connected:
                    if client.status == ClientStatus.IN_SESSION.value:
                        status_text = "В сессии"
                        status_color = QColor(173, 216, 230)  # Светло-голубой
                    else:
                        status_text = "Онлайн"
                        status_color = QColor(144, 238, 144)  # Светло-зеленый
                else:
                    status_text = "Оффлайн"
                    status_color = QColor(211, 211, 211)  # Светло-серый

                status_item = QTableWidgetItem(status_text)
                status_item.setBackground(status_color)
                self.clients_table.setItem(row, 3, status_item)

                # Время сессии - получаем из активной сессии
                time_text = ""
                if client.status == ClientStatus.IN_SESSION.value:
                    active_session = db_session.query(SessionModel).filter_by(
                        client_id=client.id,
                        status='active'
                    ).first()
                    
                    if active_session:
                        from datetime import datetime, timedelta
                        if active_session.is_unlimited:
                            # Для безлимита показываем прошедшее время
                            elapsed = datetime.now() - active_session.start_time
                            elapsed_minutes = int(elapsed.total_seconds() / 60)
                            hours = elapsed_minutes // 60
                            minutes = elapsed_minutes % 60
                            time_text = f"∞ {hours:02d}:{minutes:02d}"
                        else:
                            # Для ограниченных сессий показываем оставшееся время
                            end_time = active_session.start_time + timedelta(minutes=active_session.duration_minutes)
                            remaining = end_time - datetime.now()
                            remaining_seconds = remaining.total_seconds()
                            
                            # Показываем "Завершается..." только если время истекло более 5 секунд назад
                            # (защита от небольших расхождений в синхронизации времени)
                            if remaining_seconds < -5:
                                time_text = "Завершается..."
                            else:
                                # Показываем оставшееся время, даже если оно немного отрицательное
                                # (округляем до 0, чтобы не показывать отрицательные значения)
                                remaining_minutes = max(0, int(remaining_seconds / 60))
                                hours = remaining_minutes // 60
                                minutes = remaining_minutes % 60
                                time_text = f"{hours:02d}:{minutes:02d} осталось"
                
                self.clients_table.setItem(row, 4, QTableWidgetItem(time_text))

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

            # Обновление статистики по клиентам
            self.update_client_stats_table(db_session)

        except Exception as e:
            logger.error(f"Error updating sessions table: {e}")
        finally:
            db_session.close()

    def update_client_stats_table(self, db_session):
        """Обновление таблицы статистики по клиентам"""
        try:
            # Получаем всех клиентов
            clients = db_session.query(ClientModel).all()
            
            self.client_stats_table.setRowCount(len(clients))
            
            for row, client in enumerate(clients):
                # Получаем все сессии клиента
                sessions = db_session.query(SessionModel).filter_by(client_id=client.id).all()
                
                # Подсчитываем статистику с обработкой None значений
                total_sessions = len(sessions)
                total_duration = sum(s.actual_duration or 0 for s in sessions)
                total_cost = sum(s.cost or 0 for s in sessions)
                avg_duration = total_duration / total_sessions if total_sessions > 0 else 0
                
                # Заполняем таблицу
                self.client_stats_table.setItem(row, 0, QTableWidgetItem(client.name))
                self.client_stats_table.setItem(row, 1, QTableWidgetItem(str(total_sessions)))
                self.client_stats_table.setItem(row, 2, QTableWidgetItem(f"{total_duration:.0f}"))
                self.client_stats_table.setItem(row, 3, QTableWidgetItem(f"{avg_duration:.1f}"))
                self.client_stats_table.setItem(row, 4, QTableWidgetItem(f"{total_cost:.2f}"))
                
                # Сохраняем ID клиента в первом элементе строки для последующего использования
                item = self.client_stats_table.item(row, 0)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole, client.id)
                
        except Exception as e:
            logger.error(f"Error updating client stats table: {e}")

    def show_detailed_client_stats(self, index):
        """Показать детальную статистику по клиенту"""
        try:
            row = index.row()
            # Получаем ID клиента из данных первого элемента строки
            item = self.client_stats_table.item(row, 0)
            if not item:
                return
            
            client_id = item.data(Qt.ItemDataRole.UserRole)
            if not client_id:
                return
            
            # Получаем клиента из БД
            db_session = self.db.get_session()
            try:
                client = db_session.query(ClientModel).filter_by(id=client_id).first()
                if client:
                    # Открываем диалог детальной статистики
                    dialog = DetailedClientStatisticsDialog(client, self.db, self)
                    dialog.exec()
                else:
                    QMessageBox.warning(self, "Ошибка", "Клиент не найден")
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error showing detailed client stats: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть детальную статистику:\n{str(e)}")

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

    def edit_session_time(self):
        """Изменить время активной сессии"""
        selected_rows = self.clients_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента")
            return

        row = selected_rows[0].row()
        client_id = int(self.clients_table.item(row, 0).text())
        
        # Проверяем, есть ли активная сессия
        db_session = self.db.get_session()
        try:
            active_session = db_session.query(SessionModel).filter_by(
                client_id=client_id,
                status='active'
            ).first()
            
            if not active_session:
                QMessageBox.warning(self, "Ошибка", "У выбранного клиента нет активной сессии")
                return
            
            if active_session.is_unlimited:
                QMessageBox.information(self, "Информация", "Невозможно изменить время для безлимитной сессии")
                return
            
            # Открываем диалог для ввода нового времени
            dialog = SessionDialog(self)
            current_minutes = active_session.duration_minutes
            dialog.hours_spin.setValue(current_minutes // 60)
            dialog.minutes_spin.setValue(current_minutes % 60)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                duration, is_unlimited = dialog.get_duration()
                
                if is_unlimited:
                    QMessageBox.warning(self, "Ошибка", "Нельзя изменить ограниченную сессию на безлимитную")
                    return
                
                if duration <= 0:
                    QMessageBox.warning(self, "Ошибка", "Время сессии должно быть больше 0")
                    return
                
                # Обновляем время сессии
                asyncio.run_coroutine_threadsafe(
                    self.server.update_session_time(client_id, duration),
                    self.server_thread.loop
                )
                
                QMessageBox.information(self, "Успех", f"Время сессии изменено на {duration} минут")
                
        except Exception as e:
            logger.error(f"Error editing session time: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось изменить время сессии:\n{str(e)}")
        finally:
            db_session.close()

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
        if len(password) >= MIN_PASSWORD_LENGTH:
            strength += 1
        else:
            feedback.append(f"минимум {MIN_PASSWORD_LENGTH} символов")

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

        if len(password) < MIN_PASSWORD_LENGTH:
            QMessageBox.warning(
                self, "Ошибка", 
                f"Пароль должен содержать минимум {MIN_PASSWORD_LENGTH} символов"
            )
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
                
                # Попытка сохранить конфиг
                try:
                    self.config.save()
                except Exception as save_error:
                    # Если сохранение не удалось, откатываем изменение в памяти
                    self.config.admin_password_hash = self.config.get('security', 'admin_password_hash', '')
                    raise save_error

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

    def clear_all_statistics(self):
        """Очистить всю статистику"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "⚠️ ВНИМАНИЕ!\n\n"
            "Вы уверены, что хотите удалить ВСЮ статистику?\n\n"
            "Это действие удалит все записи о сессиях для всех клиентов.\n"
            "Информация о самих клиентах (имена, IP-адреса) будет сохранена.\n\n"
            "Это действие необратимо!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Дополнительное подтверждение
            confirm_text, ok = QInputDialog.getText(
                self, "Подтверждение удаления",
                "Для подтверждения введите: УДАЛИТЬ"
            )
            
            if ok and confirm_text == "УДАЛИТЬ":
                db_session = self.db.get_session()
                try:
                    # Удаляем все сессии
                    count = db_session.query(SessionModel).delete()
                    db_session.commit()
                    
                    QMessageBox.information(self, "Успех", f"Удалено записей: {count}")
                    logger.info(f"Cleared all statistics: {count} session records deleted")
                    
                    # Обновляем отображение
                    self.update_sessions_table()
                    
                except Exception as e:
                    logger.error(f"Error clearing all statistics: {e}")
                    db_session.rollback()
                    QMessageBox.critical(self, "Ошибка", f"Не удалось очистить статистику:\n{str(e)}")
                finally:
                    db_session.close()
            else:
                QMessageBox.information(self, "Отмена", "Операция отменена")

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

