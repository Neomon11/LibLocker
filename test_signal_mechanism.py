#!/usr/bin/env python3
"""
Unit test for installation monitor signal-based callback
Tests thread safety without requiring actual file creation
"""
import sys
import os
import time
from threading import Thread

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from src.client.installation_monitor import InstallationMonitor

class InstallationMonitorSignals(QWidget):
    """Signal wrapper for InstallationMonitor to ensure thread-safe callbacks"""
    installation_detected = pyqtSignal(str)

def test_signal_mechanism():
    """Test that the signal mechanism properly marshals thread context"""
    print("=" * 70)
    print("Test: Installation Monitor Signal Mechanism (Unit Test)")
    print("=" * 70)
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    main_thread_id = QThread.currentThreadId()
    callback_thread_id = [None]
    callback_called = [False]
    
    def on_detection(reason):
        """Callback that should run in main thread"""
        callback_thread_id[0] = QThread.currentThreadId()
        callback_called[0] = True
        print(f"\n✓ Callback invoked with reason: {reason}")
        print(f"  Main thread ID: {main_thread_id}")
        print(f"  Callback thread ID: {callback_thread_id[0]}")
        app.quit()
    
    # Create signal wrapper
    print("\n1. Creating signal wrapper...")
    signals = InstallationMonitorSignals()
    signals.installation_detected.connect(on_detection, Qt.ConnectionType.QueuedConnection)
    print("   ✓ Signal connected with QueuedConnection")
    
    # Create monitor
    print("\n2. Creating monitor with signal emitter...")
    monitor = InstallationMonitor(signal_emitter=signals)
    print("   ✓ Monitor created")
    
    # Manually trigger alert from a background thread
    print("\n3. Triggering alert from background thread...")
    
    def background_trigger():
        """Simulate background thread triggering alert"""
        background_thread_id = QThread.currentThreadId()
        print(f"   Background thread ID: {background_thread_id}")
        time.sleep(0.1)  # Simulate some work
        
        # This is the key test - calling _trigger_alert from background thread
        print("   Calling _trigger_alert()...")
        monitor._trigger_alert("Test installation detected")
        print("   _trigger_alert() returned (non-blocking)")
    
    bg_thread = Thread(target=background_trigger, daemon=True)
    bg_thread.start()
    
    # Process events in main thread
    print("\n4. Processing Qt events in main thread...")
    start_time = time.time()
    while time.time() - start_time < 3:
        app.processEvents()
        time.sleep(0.05)
        if callback_called[0]:
            break
    
    bg_thread.join(timeout=1)
    
    # Results
    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)
    
    success = True
    
    if callback_called[0]:
        print("✓ Callback was invoked")
        
        if callback_thread_id[0] == main_thread_id:
            print("✓ Callback executed in MAIN thread")
            print("✓ Signal properly marshaled thread context")
            print("✓ This prevents Qt GUI freeze issues")
        else:
            print("✗ Callback executed in WRONG thread")
            print(f"  Expected: {main_thread_id}")
            print(f"  Got: {callback_thread_id[0]}")
            success = False
    else:
        print("✗ Callback was NOT invoked")
        success = False
    
    print("=" * 70)
    
    if success:
        print("\n✓✓✓ TEST PASSED - Signal mechanism works correctly ✓✓✓")
        return 0
    else:
        print("\n✗✗✗ TEST FAILED - Signal mechanism is broken ✗✗✗")
        return 1

if __name__ == "__main__":
    try:
        exit_code = test_signal_mechanism()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
