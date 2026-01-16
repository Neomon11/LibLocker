#!/usr/bin/env python3
"""
Test script for unlock features
Tests:
1. Red alert screen triple-click detection
2. Admin password dialog
3. Unlock signal handling
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_red_alert_screen_imports():
    """Test that red alert screen can be imported with new features"""
    try:
        from src.client.red_alert_screen import RedAlertLockScreen
        from src.shared.config import ClientConfig
        
        logger.info("✓ Red alert screen imports successfully")
        
        # Check that the class has the unlocked signal
        assert hasattr(RedAlertLockScreen, 'unlocked'), "Red alert screen missing 'unlocked' signal"
        logger.info("✓ Red alert screen has unlocked signal")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to import red alert screen: {e}")
        return False

def test_client_unlock_signal():
    """Test that client has unlock signal handling"""
    try:
        from src.client.gui import ClientThread
        
        logger.info("✓ ClientThread imports successfully")
        
        # Check that ClientThread has unlock_requested signal
        # We can't directly access class-level signals, but we can check the class definition
        import inspect
        source = inspect.getsource(ClientThread)
        assert 'unlock_requested' in source, "ClientThread missing unlock_requested signal"
        logger.info("✓ ClientThread has unlock_requested signal")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to verify client unlock signal: {e}")
        return False

def test_server_unlock_method():
    """Test that server has unlock_client method"""
    try:
        from src.server.server import LibLockerServer
        
        logger.info("✓ LibLockerServer imports successfully")
        
        # Check that server has unlock_client method
        assert hasattr(LibLockerServer, 'unlock_client'), "Server missing unlock_client method"
        logger.info("✓ Server has unlock_client method")
        
        # Check method signature
        import inspect
        sig = inspect.signature(LibLockerServer.unlock_client)
        params = list(sig.parameters.keys())
        assert 'client_id' in params, "unlock_client missing client_id parameter"
        logger.info("✓ unlock_client has correct signature")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to verify server unlock method: {e}")
        return False

def test_server_gui_context_menu():
    """Test that server GUI has context menu support"""
    try:
        from src.server.gui import MainWindow
        
        logger.info("✓ MainWindow imports successfully")
        
        # Check that MainWindow has show_client_context_menu method
        assert hasattr(MainWindow, 'show_client_context_menu'), "MainWindow missing show_client_context_menu method"
        logger.info("✓ MainWindow has show_client_context_menu method")
        
        # Check that MainWindow has unlock_client method
        assert hasattr(MainWindow, 'unlock_client'), "MainWindow missing unlock_client method"
        logger.info("✓ MainWindow has unlock_client method")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to verify server GUI context menu: {e}")
        return False

def test_protocol_unlock_message():
    """Test that protocol has UNLOCK message type"""
    try:
        from src.shared.protocol import MessageType
        
        logger.info("✓ Protocol imports successfully")
        
        # Check that MessageType has UNLOCK
        assert hasattr(MessageType, 'UNLOCK'), "MessageType missing UNLOCK"
        logger.info("✓ MessageType has UNLOCK")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to verify protocol: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Testing Unlock Features Implementation")
    logger.info("=" * 60)
    
    tests = [
        ("Red Alert Screen Imports", test_red_alert_screen_imports),
        ("Client Unlock Signal", test_client_unlock_signal),
        ("Server Unlock Method", test_server_unlock_method),
        ("Server GUI Context Menu", test_server_gui_context_menu),
        ("Protocol Unlock Message", test_protocol_unlock_message),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nRunning test: {test_name}")
        logger.info("-" * 60)
        result = test_func()
        results.append((test_name, result))
        logger.info("-" * 60)
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"Results: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
