#!/usr/bin/env python3
"""
Test script for unlock features - Code structure validation
Tests code structure without running Qt code
"""
import sys
import logging
import re
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_red_alert_screen_modifications():
    """Test that red alert screen has been modified correctly"""
    try:
        red_alert_path = Path("src/client/red_alert_screen.py")
        content = red_alert_path.read_text()
        
        # Check for unlocked signal
        assert 'unlocked = pyqtSignal()' in content, "Missing unlocked signal"
        logger.info("✓ Red alert screen has unlocked signal")
        
        # Check for corner click tracking
        assert 'corner_clicks' in content, "Missing corner_clicks variable"
        logger.info("✓ Red alert screen has corner click tracking")
        
        # Check for mousePressEvent
        assert 'def mousePressEvent' in content, "Missing mousePressEvent"
        logger.info("✓ Red alert screen has mousePressEvent")
        
        # Check for show_password_dialog
        assert 'def show_password_dialog' in content, "Missing show_password_dialog"
        logger.info("✓ Red alert screen has show_password_dialog")
        
        # Check for force_close method
        assert 'def force_close' in content, "Missing force_close method"
        logger.info("✓ Red alert screen has force_close method")
        
        # Check for triple-click detection (3 clicks)
        assert 'corner_clicks >= 3' in content, "Missing triple-click detection"
        logger.info("✓ Red alert screen has triple-click detection")
        
        # Check for admin password hint
        assert 'тройной клик' in content or 'triple' in content.lower(), "Missing admin hint"
        logger.info("✓ Red alert screen has admin hint")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        return False

def test_client_gui_modifications():
    """Test that client GUI has unlock handling"""
    try:
        client_gui_path = Path("src/client/gui.py")
        content = client_gui_path.read_text()
        
        # Check for unlock_requested signal
        assert 'unlock_requested = pyqtSignal()' in content, "Missing unlock_requested signal"
        logger.info("✓ Client GUI has unlock_requested signal")
        
        # Check for on_unlock_requested handler
        assert 'def on_unlock_requested' in content, "Missing on_unlock_requested handler"
        logger.info("✓ Client GUI has on_unlock_requested handler")
        
        # Check that red_alert_screen gets config
        assert 'config=self.config' in content, "Red alert screen not receiving config"
        logger.info("✓ Red alert screen receives config parameter")
        
        # Check for unlock signal connection
        assert 'unlocked.connect' in content or 'on_red_alert_unlocked' in content, "Missing unlock signal connection"
        logger.info("✓ Red alert unlock signal is connected")
        
        # Check for emit_unlock callback
        assert 'def emit_unlock' in content, "Missing emit_unlock callback"
        logger.info("✓ Client thread has emit_unlock callback")
        
        # Check that client.on_unlock is set
        assert 'self.client.on_unlock = emit_unlock' in content, "client.on_unlock not set"
        logger.info("✓ Client on_unlock callback is set")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        return False

def test_server_gui_modifications():
    """Test that server GUI has context menu"""
    try:
        server_gui_path = Path("src/server/gui.py")
        content = server_gui_path.read_text()
        
        # Check for QMenu import
        assert 'QMenu' in content, "Missing QMenu import"
        logger.info("✓ Server GUI imports QMenu")
        
        # Check for QAction import
        assert 'QAction' in content, "Missing QAction import"
        logger.info("✓ Server GUI imports QAction")
        
        # Check for context menu policy
        assert 'setContextMenuPolicy' in content, "Missing context menu policy"
        logger.info("✓ Client table has context menu policy")
        
        # Check for show_client_context_menu method
        assert 'def show_client_context_menu' in content, "Missing show_client_context_menu method"
        logger.info("✓ Server GUI has show_client_context_menu method")
        
        # Check for unlock_client method in GUI
        assert 'def unlock_client' in content, "Missing unlock_client method in GUI"
        logger.info("✓ Server GUI has unlock_client method")
        
        # Check that buttons were removed from layout
        # The edit_session, shutdown, and toggle_monitor buttons should not be in buttons_layout anymore
        lines = content.split('\n')
        in_clients_tab = False
        found_removed_buttons = False
        for i, line in enumerate(lines):
            if 'def create_clients_tab' in line:
                in_clients_tab = True
            if in_clients_tab and 'return widget' in line:
                # Check the section - should not have btn_edit_session, btn_shutdown, btn_toggle_monitor in buttons_layout
                section = '\n'.join(lines[i-50:i])
                if 'btn_edit_session' not in section or 'buttons_layout.addWidget(self.btn_edit_session)' not in section:
                    found_removed_buttons = True
                break
        
        if found_removed_buttons or 'customContextMenuRequested.connect' in content:
            logger.info("✓ Buttons moved to context menu")
        
        # Check for context menu actions
        assert 'Изменить время сессии' in content or 'edit_time_action' in content, "Missing session time action"
        logger.info("✓ Context menu has session time action")
        
        assert 'Переключить мониторинг' in content or 'monitor_action' in content, "Missing monitor action"
        logger.info("✓ Context menu has monitor action")
        
        assert 'Выключить компьютер' in content or 'shutdown_action' in content, "Missing shutdown action"
        logger.info("✓ Context menu has shutdown action")
        
        assert 'Разблокировать' in content or 'unlock_action' in content, "Missing unlock action"
        logger.info("✓ Context menu has unlock action")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        return False

def test_server_modifications():
    """Test that server has unlock_client method"""
    try:
        server_path = Path("src/server/server.py")
        content = server_path.read_text()
        
        # Check for unlock_client method
        assert 'async def unlock_client' in content, "Missing unlock_client method"
        logger.info("✓ Server has unlock_client method")
        
        # Check that it sends UNLOCK message
        assert 'MessageType.UNLOCK' in content, "unlock_client doesn't send UNLOCK message"
        logger.info("✓ unlock_client sends UNLOCK message")
        
        # Check method signature
        assert 'client_id: int' in content, "unlock_client missing client_id parameter"
        logger.info("✓ unlock_client has correct signature")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        return False

def test_protocol():
    """Test that protocol has UNLOCK message type"""
    try:
        protocol_path = Path("src/shared/protocol.py")
        content = protocol_path.read_text()
        
        # Check for UNLOCK in MessageType
        assert 'UNLOCK = "unlock"' in content, "Missing UNLOCK in MessageType"
        logger.info("✓ Protocol has UNLOCK message type")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Testing Unlock Features - Code Structure Validation")
    logger.info("=" * 60)
    
    tests = [
        ("Red Alert Screen Modifications", test_red_alert_screen_modifications),
        ("Client GUI Modifications", test_client_gui_modifications),
        ("Server GUI Modifications", test_server_gui_modifications),
        ("Server Modifications", test_server_modifications),
        ("Protocol", test_protocol),
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
    
    if passed == total:
        logger.info("\n🎉 All tests passed! Implementation looks good.")
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed. Please review the code.")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
