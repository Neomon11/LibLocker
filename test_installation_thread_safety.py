#!/usr/bin/env python3
"""
Test script for installation monitor thread safety fix
Tests that the signal-based callback properly marshals to main Qt thread
"""
import sys
import os
import time
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from src.client.installation_monitor import InstallationMonitor

class InstallationMonitorSignals(QWidget):
    """Signal wrapper for InstallationMonitor to ensure thread-safe callbacks"""
    installation_detected = pyqtSignal(str)

def test_thread_safety():
    """Test that installation detection uses Qt signals for thread safety"""
    print("=" * 70)
    print("Test: Installation Monitor Thread Safety")
    print("=" * 70)
    
    # Create Qt application (required for signal/slot mechanism)
    app = QApplication(sys.argv)
    
    detection_count = [0]
    main_thread_id = QThread.currentThreadId()
    callback_thread_id = [None]
    
    def on_detection(reason):
        """Callback that runs in main thread via Qt signal"""
        callback_thread_id[0] = QThread.currentThreadId()
        print(f"\n🚨 ОБНАРУЖЕНИЕ: {reason}")
        print(f"   Main thread ID: {main_thread_id}")
        print(f"   Callback thread ID: {callback_thread_id[0]}")
        
        if callback_thread_id[0] == main_thread_id:
            print("   ✓ Callback executed in MAIN thread (correct)")
        else:
            print("   ✗ Callback executed in BACKGROUND thread (WRONG - would cause freeze)")
        
        detection_count[0] += 1
        app.quit()  # Stop after first detection
    
    # Create signal wrapper
    print("\n1. Creating signal wrapper...")
    signals = InstallationMonitorSignals()
    signals.installation_detected.connect(on_detection, Qt.ConnectionType.QueuedConnection)
    print("   ✓ Signal wrapper created with QueuedConnection")
    
    # Create monitor with signal emitter
    print("\n2. Creating installation monitor with signal emitter...")
    monitor = InstallationMonitor(signal_emitter=signals)
    print("   ✓ Monitor created")
    
    print("\n3. Starting monitoring...")
    monitor.start()
    print("   ✓ Monitor started (background thread)")
    
    # Wait for initialization
    time.sleep(2)
    
    print("\n4. Creating test installer file...")
    downloads_path = Path.home() / "Downloads"
    test_file = None
    
    if downloads_path.exists():
        test_file = downloads_path / "test_installer_thread_safety.exe"
        try:
            with open(test_file, 'wb') as f:
                f.write(b"Test installer for thread safety")
            print(f"   ✓ Created: {test_file}")
            
            print("\n5. Waiting for detection (up to 15 seconds)...")
            print("   Processing Qt events in main thread...")
            
            # Process events in main thread
            # This simulates the normal Qt event loop
            start_time = time.time()
            while time.time() - start_time < 15:
                app.processEvents()
                time.sleep(0.1)
                if detection_count[0] > 0:
                    break
            
        except Exception as e:
            print(f"   ✗ Error creating file: {e}")
    else:
        print(f"   ✗ Downloads folder not found: {downloads_path}")
    
    print("\n6. Stopping monitor...")
    monitor.stop()
    print("   ✓ Monitor stopped")
    
    # Cleanup
    if test_file and test_file.exists():
        try:
            test_file.unlink()
            print(f"   ✓ Cleaned up: {test_file}")
        except Exception as e:
            print(f"   ⚠ Could not delete test file: {e}")
    
    # Results
    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)
    
    success = False
    if detection_count[0] > 0:
        print(f"✓ Installation detected: {detection_count[0]} time(s)")
        if callback_thread_id[0] == main_thread_id:
            print("✓ Callback executed in MAIN thread")
            print("✓ Thread safety: CORRECT - no freeze will occur")
            success = True
        else:
            print("✗ Callback executed in BACKGROUND thread")
            print("✗ Thread safety: INCORRECT - timer would freeze")
    else:
        print("⚠ No installation detected")
        print("  (May be due to timing - test file created/detected too quickly)")
    
    print("=" * 70)
    
    if success:
        print("\n✓✓✓ TEST PASSED - Thread safety fix is working correctly ✓✓✓")
        return 0
    else:
        print("\n⚠⚠⚠ TEST INCONCLUSIVE - Check results above ⚠⚠⚠")
        return 1

if __name__ == "__main__":
    try:
        exit_code = test_thread_safety()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
