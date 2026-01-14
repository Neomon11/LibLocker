"""
Unit test to verify signal connections and emission
This test checks if signals can be emitted and received properly
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from src.client.gui import ClientThread

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class TestReceiver(QObject):
    """Test class to receive signals"""
    def __init__(self):
        super().__init__()
        self.session_started_called = False
        self.received_data = None
    
    def on_session_started(self, data):
        """Handler for session_started signal"""
        logger.info("="*60)
        logger.info("TEST RECEIVER: on_session_started CALLED!")
        logger.info(f"Data received: {data}")
        logger.info("="*60)
        self.session_started_called = True
        self.received_data = data

def test_signal_connection():
    """Test that signals can be emitted and received"""
    logger.info("="* 60)
    logger.info("Testing signal connection and emission")
    logger.info("="* 60)

    app = QApplication(sys.argv)
    
    # Create a test receiver
    receiver = TestReceiver()
    
    # Create ClientThread (but don't start it to avoid connection attempts)
    client_thread = ClientThread("http://localhost:9999")
    
    # Connect the signal with explicit QueuedConnection
    client_thread.session_started.connect(
        receiver.on_session_started, 
        Qt.ConnectionType.QueuedConnection
    )
    
    logger.info("Signal connected successfully")
    
    # Test data
    test_data = {
        'duration_minutes': 1,
        'is_unlimited': False,
        'cost_per_hour': 100.0,
        'free_mode': False,
        'session_id': 1
    }
    
    def emit_signal():
        """Emit test signal"""
        logger.info("\n" + "="* 60)
        logger.info("EMITTING TEST SIGNAL")
        logger.info("="* 60)
        try:
            client_thread.session_started.emit(test_data)
            logger.info("Signal emitted successfully")
        except Exception as e:
            logger.error(f"Error emitting signal: {e}", exc_info=True)
    
    def check_result():
        """Check if signal was received"""
        logger.info("\n" + "="* 60)
        logger.info("CHECKING RESULTS")
        logger.info("="* 60)
        if receiver.session_started_called:
            logger.info("✅ SUCCESS: Signal was received!")
            logger.info(f"✅ Data matches: {receiver.received_data == test_data}")
        else:
            logger.error("❌ FAILURE: Signal was NOT received!")
        app.quit()
    
    # Emit signal after 100ms
    QTimer.singleShot(100, emit_signal)
    
    # Check result after 500ms
    QTimer.singleShot(500, check_result)
    
    logger.info("\n✅ Application started. Testing signal emission...\n")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_signal_connection()
