"""
Test script to verify session_start signal flow from ClientThread to MainWindow
This simulates receiving a session_start message and verifies the widget appears
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.client.gui import MainClientWindow
from src.shared.config import ClientConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_signal_emission():
    """Тест эмиссии сигнала session_started"""
    logger.info("="* 60)
    logger.info("Starting signal flow test")
    logger.info("="* 60)

    app = QApplication(sys.argv)
    
    # Create main window (this will start the ClientThread)
    config = ClientConfig()
    # Use a non-existent server to avoid actual connection
    window = MainClientWindow("http://localhost:9999", config)
    window.show()
    
    logger.info("Main window created and shown")
    logger.info(f"Main thread ID: {app.thread().currentThreadId()}")
    
    # Test data for session
    test_session_data = {
        'duration_minutes': 1,
        'is_unlimited': False,
        'cost_per_hour': 100.0,
        'free_mode': False,
        'session_id': 1
    }
    
    def emit_test_signal():
        """Emit test signal after 2 seconds"""
        logger.info("\n" + "="* 60)
        logger.info("EMITTING TEST session_started SIGNAL")
        logger.info("="* 60)
        try:
            # Directly emit the signal from the client thread
            window.client_thread.session_started.emit(test_session_data)
            logger.info("Signal emitted successfully")
        except Exception as e:
            logger.error(f"Error emitting signal: {e}", exc_info=True)
    
    # Schedule signal emission after 2 seconds
    QTimer.singleShot(2000, emit_test_signal)
    
    # Exit after 10 seconds if widget doesn't appear
    QTimer.singleShot(10000, app.quit)
    
    logger.info("\n✅ Application started. Will emit test signal in 2 seconds...")
    logger.info("Watch for the timer widget to appear!")
    logger.info("Application will exit in 10 seconds if no issues occur.\n")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_signal_emission()
