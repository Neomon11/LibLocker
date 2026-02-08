"""
Диалог для обнаружения серверов LibLocker в локальной сети
"""
import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QListWidget, QLineEdit, QMessageBox, 
    QProgressBar, QListWidgetItem, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from ..shared.discovery import ServerDiscovery, ServerInfo

logger = logging.getLogger(__name__)


class DiscoveryThread(QThread):
    """Поток для обнаружения серверов"""
    
    servers_found = pyqtSignal(list)  # List[ServerInfo]
    discovery_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, timeout: float = 5.0):
        super().__init__()
        self.timeout = timeout
    
    def run(self):
        """Запуск поиска серверов"""
        try:
            logger.info("Starting server discovery...")
            servers = ServerDiscovery.discover_servers(timeout=self.timeout)
            self.servers_found.emit(servers)
            logger.info(f"Discovery complete. Found {len(servers)} servers")
        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.discovery_finished.emit()


class ServerDiscoveryDialog(QDialog):
    """Диалог для обнаружения и выбора сервера"""
    
    def __init__(self, parent=None, current_url: str = None):
        super().__init__(parent)
        self.setWindowTitle("Поиск сервера LibLocker")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.selected_server: Optional[ServerInfo] = None
        self.manual_url: Optional[str] = None
        self.current_url = current_url
        
        self._setup_ui()
        self.discovery_thread: Optional[DiscoveryThread] = None
    
    def _setup_ui(self):
        """Настройка пользовательского интерфейса"""
        layout = QVBoxLayout()
        
        # Заголовок
        title = QLabel("Обнаружение сервера LibLocker")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Информация
        info_text = QLabel(
            "Выполните поиск серверов в локальной сети или введите адрес вручную."
        )
        info_text.setWordWrap(True)
        info_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_text)
        
        # Текущий URL (если есть)
        if self.current_url:
            current_label = QLabel(f"Текущий адрес: {self.current_url}")
            current_label.setStyleSheet("color: #666; font-style: italic;")
            current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(current_label)
        
        layout.addSpacing(10)
        
        # Группа автоматического поиска
        auto_group = QGroupBox("Автоматический поиск")
        auto_layout = QVBoxLayout()
        
        # Кнопка поиска
        search_button_layout = QHBoxLayout()
        self.search_button = QPushButton("🔍 Найти серверы")
        self.search_button.clicked.connect(self._start_discovery)
        search_button_layout.addStretch()
        search_button_layout.addWidget(self.search_button)
        search_button_layout.addStretch()
        auto_layout.addLayout(search_button_layout)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Индикатор неопределенного прогресса
        self.progress_bar.setVisible(False)
        auto_layout.addWidget(self.progress_bar)
        
        # Список найденных серверов
        self.server_list = QListWidget()
        self.server_list.itemDoubleClicked.connect(self._on_server_double_clicked)
        auto_layout.addWidget(self.server_list)
        
        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)
        
        # Группа ручного ввода
        manual_group = QGroupBox("Ручной ввод адреса")
        manual_layout = QVBoxLayout()
        
        manual_input_layout = QHBoxLayout()
        manual_label = QLabel("Адрес сервера:")
        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText("http://192.168.1.100:8765")
        manual_input_layout.addWidget(manual_label)
        manual_input_layout.addWidget(self.manual_input)
        manual_layout.addLayout(manual_input_layout)
        
        manual_hint = QLabel("Формат: http://IP:PORT (например, http://192.168.1.100:8765)")
        manual_hint.setStyleSheet("color: #666; font-size: 9pt;")
        manual_layout.addWidget(manual_hint)
        
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)
        
        # Группа настроек автозапуска
        settings_group = QGroupBox("Настройки запуска")
        settings_layout = QVBoxLayout()
        
        from ..shared.utils import is_autostart_enabled
        from PyQt6.QtWidgets import QCheckBox
        
        self.autostart_checkbox = QCheckBox("🚀 Автозапуск при загрузке Windows")
        self.autostart_checkbox.setChecked(is_autostart_enabled())
        self.autostart_checkbox.stateChanged.connect(self._on_autostart_changed)
        settings_layout.addWidget(self.autostart_checkbox)
        
        autostart_hint = QLabel("При включении клиент будет автоматически запускаться в свернутом режиме при старте системы")
        autostart_hint.setStyleSheet("color: #666; font-size: 9pt;")
        autostart_hint.setWordWrap(True)
        settings_layout.addWidget(autostart_hint)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Подключиться")
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setEnabled(False)
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Подключаем сигналы для включения кнопки OK
        self.server_list.itemSelectionChanged.connect(self._update_ok_button)
        self.manual_input.textChanged.connect(self._update_ok_button)
    
    def _update_ok_button(self):
        """Обновляет состояние кнопки OK"""
        has_selection = len(self.server_list.selectedItems()) > 0
        has_manual_input = len(self.manual_input.text().strip()) > 0
        self.ok_button.setEnabled(has_selection or has_manual_input)
    
    def _start_discovery(self):
        """Запускает поиск серверов"""
        logger.info("Starting server discovery from UI")
        
        # Очищаем список
        self.server_list.clear()
        
        # Показываем прогресс
        self.progress_bar.setVisible(True)
        self.search_button.setEnabled(False)
        
        # Запускаем поток поиска
        self.discovery_thread = DiscoveryThread(timeout=5.0)
        self.discovery_thread.servers_found.connect(self._on_servers_found)
        self.discovery_thread.discovery_finished.connect(self._on_discovery_finished)
        self.discovery_thread.error_occurred.connect(self._on_discovery_error)
        self.discovery_thread.start()
    
    def _on_servers_found(self, servers):
        """Обработка найденных серверов"""
        logger.info(f"Found {len(servers)} servers")
        
        if not servers:
            item = QListWidgetItem("Серверы не найдены")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.server_list.addItem(item)
        else:
            for server in servers:
                item = QListWidgetItem(f"{server.name} - {server.url}")
                item.setData(Qt.ItemDataRole.UserRole, server)
                self.server_list.addItem(item)
    
    def _on_discovery_finished(self):
        """Обработка завершения поиска"""
        logger.info("Discovery finished")
        self.progress_bar.setVisible(False)
        self.search_button.setEnabled(True)
    
    def _on_discovery_error(self, error_msg: str):
        """Обработка ошибки поиска"""
        logger.error(f"Discovery error: {error_msg}")
        QMessageBox.warning(
            self,
            "Ошибка поиска",
            f"Произошла ошибка при поиске серверов:\n{error_msg}"
        )
    
    def _on_server_double_clicked(self, item: QListWidgetItem):
        """Обработка двойного клика по серверу"""
        server = item.data(Qt.ItemDataRole.UserRole)
        if server:
            self.selected_server = server
            self.accept()
    
    def _on_ok_clicked(self):
        """Обработка нажатия кнопки OK"""
        # Приоритет у выбранного из списка сервера
        selected_items = self.server_list.selectedItems()
        if selected_items:
            server = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if server:
                self.selected_server = server
                self.accept()
                return
        
        # Иначе используем ручной ввод
        manual_url = self.manual_input.text().strip()
        if manual_url:
            # Валидация URL
            if not manual_url.startswith('http://') and not manual_url.startswith('https://'):
                QMessageBox.warning(
                    self,
                    "Неверный формат",
                    "Адрес должен начинаться с http:// или https://"
                )
                return
            
            self.manual_url = manual_url
            self.accept()
            return
        
        QMessageBox.warning(
            self,
            "Не выбран сервер",
            "Пожалуйста, выберите сервер из списка или введите адрес вручную."
        )
    
    def _on_autostart_changed(self, state):
        """Обработка изменения чекбокса автозапуска"""
        from ..shared.utils import setup_autostart
        
        # Используем isChecked() для более ясного намерения
        checked = self.autostart_checkbox.isChecked()
        
        # Пытаемся настроить автозапуск (всегда с опцией --minimized)
        success = setup_autostart(checked, minimized=True)
        
        if success:
            status = "включен" if checked else "отключен"
            logger.info(f"Autostart {status}")
        else:
            # Если не удалось, показываем ошибку и возвращаем чекбокс обратно
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось изменить настройки автозапуска.\n"
                "Возможно, у приложения недостаточно прав."
            )
            # Блокируем сигналы чтобы избежать рекурсии
            self.autostart_checkbox.blockSignals(True)
            self.autostart_checkbox.setChecked(not checked)
            self.autostart_checkbox.blockSignals(False)
    
    def get_selected_url(self) -> Optional[str]:
        """Возвращает выбранный URL сервера"""
        if self.selected_server:
            return self.selected_server.url
        return self.manual_url


def show_server_discovery_dialog(parent=None, current_url: str = None) -> Optional[str]:
    """
    Показывает диалог обнаружения сервера и возвращает выбранный URL
    
    Args:
        parent: Родительское окно
        current_url: Текущий URL сервера (если есть)
        
    Returns:
        URL выбранного сервера или None если отменено
    """
    dialog = ServerDiscoveryDialog(parent, current_url)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_selected_url()
    return None
