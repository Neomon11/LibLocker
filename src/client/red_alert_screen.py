"""
Красный экран тревоги при обнаружении установки программ
"""
import os
import sys
import logging
import base64
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDialog, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from ..shared.utils import verify_password

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtCore import QUrl
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False
    logger.warning("PyQt6.QtMultimedia not available, audio will not play")

# Windows-specific imports for volume control
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

# Встроенный аудио-файл сирены (base64 для встраивания в программу)
SIREN_AUDIO_BASE64 = None  # Будет загружен при первом использовании


def load_siren_audio():
    """Загрузка аудио-файла сирены"""
    global SIREN_AUDIO_BASE64
    
    if SIREN_AUDIO_BASE64 is not None:
        return SIREN_AUDIO_BASE64
    
    # Путь к файлу сирены
    siren_path = Path(__file__).parent.parent.parent / "siren.wav"
    
    try:
        if siren_path.exists():
            with open(siren_path, 'rb') as f:
                SIREN_AUDIO_BASE64 = base64.b64encode(f.read()).decode('utf-8')
                logger.info(f"Siren audio loaded from {siren_path}")
        else:
            logger.error(f"Siren audio file not found: {siren_path}")
            SIREN_AUDIO_BASE64 = ""
    except Exception as e:
        logger.error(f"Error loading siren audio: {e}", exc_info=True)
        SIREN_AUDIO_BASE64 = ""
    
    return SIREN_AUDIO_BASE64


class RedAlertLockScreen(QMainWindow):
    """Красный экран блокировки при обнаружении установки программ"""
    
    # Constants for triple-click detection
    CORNER_CLICK_ZONE_SIZE = 100  # pixels from corner
    TRIPLE_CLICK_TIMEOUT = 1.0  # seconds between clicks
    
    unlocked = pyqtSignal()  # Сигнал разблокировки администратором
    
    def __init__(self, reason: str = "Обнаружена попытка установки программы", alert_volume: int = 80, config=None):
        super().__init__()
        self.reason = reason
        self.alert_volume = alert_volume
        self.media_player = None
        self.audio_output = None
        self.config = config
        
        # Счетчик кликов для ввода пароля (triple-click в углу)
        self.corner_clicks = 0
        self.last_click_time = None
        
        self.init_ui()
        self.setup_fullscreen()
        self.setup_audio()
        self.start_siren()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("LibLocker - ТРЕВОГА")
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Заголовок тревоги
        title_label = QLabel("⚠️ ТРЕВОГА ⚠️")
        title_font = QFont()
        title_font.setPointSize(80)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        layout.addSpacing(50)
        
        # Главное сообщение
        message_label = QLabel("ОБНАРУЖЕНА ПОПЫТКА\nУСТАНОВКИ ПРОГРАММЫ")
        message_font = QFont()
        message_font.setPointSize(48)
        message_font.setBold(True)
        message_label.setFont(message_font)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)
        
        layout.addSpacing(40)
        
        # Причина
        reason_label = QLabel(self.reason)
        reason_font = QFont()
        reason_font.setPointSize(28)
        reason_label.setFont(reason_font)
        reason_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(reason_label)
        
        layout.addSpacing(60)
        
        # Инструкция
        info_label = QLabel("Компьютер заблокирован!\n\nОбратитесь к администратору немедленно")
        info_font = QFont()
        info_font.setPointSize(24)
        info_font.setBold(True)
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
        hint_label.setStyleSheet("color: #FFB6C1;")  # Светло-розовый для читабельности на красном
        layout.addWidget(hint_label)
        
        # Установка КРАСНОГО фона
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(200, 0, 0))  # Ярко-красный
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        
        # Эффект мигания
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.toggle_blink)
        self.blink_timer.start(500)  # Мигание каждые 500 мс
        self.blink_state = False
    
    def toggle_blink(self):
        """Переключение мигания экрана"""
        self.blink_state = not self.blink_state
        palette = self.palette()
        if self.blink_state:
            palette.setColor(QPalette.ColorRole.Window, QColor(255, 0, 0))  # Более яркий красный
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor(200, 0, 0))  # Темнее
        self.setPalette(palette)
    
    def setup_fullscreen(self):
        """Настройка полноэкранного режима"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.showFullScreen()
        
        # Отключаем курсор
        self.setCursor(Qt.CursorShape.BlankCursor)
    
    def setup_audio(self):
        """Настройка аудио-плеера"""
        if not MULTIMEDIA_AVAILABLE:
            logger.warning("Multimedia not available, skipping audio setup")
            return
        
        try:
            # Создаем временный файл для аудио
            load_siren_audio()
            
            if SIREN_AUDIO_BASE64:
                # Декодируем base64 в временный файл
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_audio_path = os.path.join(temp_dir, "liblocker_siren.wav")
                
                with open(temp_audio_path, 'wb') as f:
                    f.write(base64.b64decode(SIREN_AUDIO_BASE64))
                
                # Создаем плеер
                self.audio_output = QAudioOutput()
                self.media_player = QMediaPlayer()
                self.media_player.setAudioOutput(self.audio_output)
                
                # Устанавливаем громкость (0.0 - 1.0)
                volume = self.alert_volume / 100.0
                self.audio_output.setVolume(volume)
                
                # Загружаем файл
                self.media_player.setSource(QUrl.fromLocalFile(temp_audio_path))
                
                logger.info(f"Audio player setup complete, volume: {volume}")
            else:
                logger.error("Siren audio not available")
        
        except Exception as e:
            logger.error(f"Error setting up audio: {e}", exc_info=True)
    
    def start_siren(self):
        """Запуск воспроизведения сирены"""
        try:
            # Устанавливаем системную громкость (Windows)
            if sys.platform == 'win32':
                try:
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    
                    # Устанавливаем системную громкость
                    volume.SetMasterVolumeLevelScalar(self.alert_volume / 100.0, None)
                    logger.info(f"System volume set to {self.alert_volume}%")
                except Exception as e:
                    logger.warning(f"Could not set system volume: {e}")
            
            # Воспроизводим звук
            if MULTIMEDIA_AVAILABLE and self.media_player:
                # Зацикливаем воспроизведение
                self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
                self.media_player.play()
                logger.info("Siren started playing (PyQt6.QtMultimedia)")
            elif WINSOUND_AVAILABLE:
                # Fallback to winsound
                logger.info("Using winsound for alert")
                # Play system sound repeatedly in a timer
                self.sound_timer = QTimer()
                self.sound_timer.timeout.connect(lambda: winsound.MessageBeep(winsound.MB_ICONEXCLAMATION))
                self.sound_timer.start(500)
            else:
                logger.warning("No audio playback available")
        
        except Exception as e:
            logger.error(f"Error starting siren: {e}", exc_info=True)
    
    def _on_media_status_changed(self, status):
        """Обработка изменения статуса медиа для зацикливания"""
        if not MULTIMEDIA_AVAILABLE:
            return
        
        from PyQt6.QtMultimedia import QMediaPlayer
        
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Перезапускаем воспроизведение
            self.media_player.setPosition(0)
            self.media_player.play()
    
    def keyPressEvent(self, event):
        """Блокировка нажатий клавиш"""
        # Блокируем все клавиши
        event.ignore()
    
    def mousePressEvent(self, event):
        """Обработка кликов мыши для показа поля пароля"""
        # Клик в правом верхнем углу
        if event.pos().x() > self.width() - self.CORNER_CLICK_ZONE_SIZE and event.pos().y() < self.CORNER_CLICK_ZONE_SIZE:
            current_time = datetime.now()
            
            # Проверка тройного клика (в течение заданного времени)
            if self.last_click_time and (current_time - self.last_click_time).total_seconds() < self.TRIPLE_CLICK_TIMEOUT:
                self.corner_clicks += 1
            else:
                self.corner_clicks = 1
            
            self.last_click_time = current_time
            
            # Если 3 клика - показываем поле пароля
            if self.corner_clicks >= 3:
                self.show_password_dialog()
                self.corner_clicks = 0
        else:
            # Блокируем все другие клики
            event.ignore()
    
    def show_password_dialog(self):
        """Показать диалог ввода пароля администратора"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Разблокировка")
        dialog.setModal(True)
        dialog.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        
        layout = QVBoxLayout()
        
        label = QLabel("Введите пароль администратора для разблокировки:")
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
            
            # Если config не передан или пароль не установлен
            if not self.config or not self.config.admin_password_hash:
                QMessageBox.warning(
                    dialog,
                    "Предупреждение",
                    "Пароль администратора не установлен!\nОбратитесь к администратору для настройки безопасности."
                )
                dialog.accept()
                self.unlocked.emit()
                return
            
            # Проверяем пароль через verify_password
            if verify_password(password, self.config.admin_password_hash):
                QMessageBox.information(dialog, "Успех", "Разблокировка выполнена")
                dialog.accept()
                self.unlocked.emit()
            else:
                QMessageBox.warning(dialog, "Ошибка", "Неверный пароль")
        
        btn_ok.clicked.connect(check_password)
        btn_cancel.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def closeEvent(self, event):
        """Блокировка закрытия окна"""
        # Останавливаем аудио при закрытии
        if MULTIMEDIA_AVAILABLE and self.media_player:
            self.media_player.stop()
        
        if hasattr(self, 'sound_timer') and self.sound_timer:
            self.sound_timer.stop()
        
        if self.blink_timer:
            self.blink_timer.stop()
        
        # Окно может быть закрыто только программно или по паролю
        if not hasattr(self, '_allow_close'):
            event.ignore()
        else:
            event.accept()
    
    def force_close(self):
        """Принудительное закрытие окна"""
        self._allow_close = True
        self.close()
