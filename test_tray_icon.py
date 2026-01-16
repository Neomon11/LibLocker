"""
Test system tray icon implementation in LibLocker client
Verifies that the tray icon functionality is properly implemented
"""
import sys
import os
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_tray_imports():
    """Test that QSystemTrayIcon and QIcon are imported"""
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for QSystemTrayIcon import
    assert 'QSystemTrayIcon' in content, "QSystemTrayIcon should be imported"
    assert 'QIcon' in content, "QIcon should be imported"
    
    print("✓ Tray icon imports are present")


def test_init_tray_icon_method():
    """Test that init_tray_icon method exists"""
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for init_tray_icon method
    assert 'def init_tray_icon(self):' in content, "init_tray_icon method should exist"
    
    # Check that it's called in __init__
    assert 'self.init_tray_icon()' in content, "init_tray_icon should be called in __init__"
    
    print("✓ init_tray_icon method exists and is called")


def test_tray_menu_actions():
    """Test that tray menu has required actions"""
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for "Развернуть" action
    assert 'Развернуть' in content, "Show action should exist"
    assert 'show_action' in content, "show_action should be defined"
    
    # Check for "Закрыть клиент" action
    assert 'Закрыть клиент' in content, "Exit action should exist"
    assert 'exit_action' in content, "exit_action should be defined"
    
    # Check for separator
    assert 'tray_menu.addSeparator()' in content, "Menu should have separator"
    
    print("✓ Tray menu actions are present")


def test_password_check_on_exit():
    """Test that exit requires password check"""
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for exit_with_password_check method
    assert 'def exit_with_password_check(self):' in content, "exit_with_password_check method should exist"
    
    # Check that it's connected to exit action
    assert 'exit_action.triggered.connect(self.exit_with_password_check)' in content, \
        "exit_action should be connected to exit_with_password_check"
    
    # Check for password verification
    assert 'verify_password(password, admin_password_hash)' in content, \
        "Password verification should be performed"
    
    print("✓ Password check on exit is implemented")


def test_force_exit_method():
    """Test that force_exit method exists and properly cleans up"""
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for force_exit method
    assert 'def force_exit(self):' in content, "force_exit method should exist"
    
    # Check that it hides tray icon
    assert 'self.tray_icon.hide()' in content, "Tray icon should be hidden on exit"
    
    # Check that it calls QApplication.quit()
    assert 'QApplication.quit()' in content, "Application should quit"
    
    print("✓ force_exit method is implemented")


def test_close_event_minimizes_to_tray():
    """Test that closeEvent minimizes to tray instead of closing"""
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the closeEvent method in MainClientWindow
    # Look for the method after class MainClientWindow
    main_window_start = content.find('class MainClientWindow(QMainWindow):')
    assert main_window_start > 0, "MainClientWindow class should exist"
    
    # Find closeEvent after MainClientWindow
    close_event_pos = content.find('def closeEvent(self, event):', main_window_start)
    assert close_event_pos > main_window_start, "closeEvent should exist in MainClientWindow"
    
    # Get the closeEvent content (next 500 chars)
    close_event_content = content[close_event_pos:close_event_pos + 500]
    
    # Check that it ignores the close event
    assert 'event.ignore()' in close_event_content, "Close event should be ignored"
    
    # Check that it hides the window
    assert 'self.hide()' in close_event_content, "Window should be hidden"
    
    # Check for tray notification
    assert 'showMessage' in close_event_content or 'tray_icon' in close_event_content, \
        "Tray notification should be shown"
    
    print("✓ closeEvent minimizes to tray")


def test_show_window_method():
    """Test that show_window method exists and shows the window"""
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for show_window method
    assert 'def show_window(self):' in content, "show_window method should exist"
    
    # Check that it shows the window
    assert 'self.show()' in content, "Window should be shown"
    assert 'self.raise_()' in content, "Window should be raised"
    assert 'self.activateWindow()' in content, "Window should be activated"
    
    print("✓ show_window method is implemented")


def test_double_click_shows_window():
    """Test that double-clicking tray icon shows window"""
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for on_tray_icon_activated method
    assert 'def on_tray_icon_activated(self, reason):' in content, \
        "on_tray_icon_activated method should exist"
    
    # Check that it's connected
    assert 'self.tray_icon.activated.connect(self.on_tray_icon_activated)' in content, \
        "activated signal should be connected"
    
    # Check for DoubleClick handling
    assert 'ActivationReason.DoubleClick' in content, "DoubleClick should be handled"
    
    print("✓ Double-click shows window")


def run_all_tests():
    """Run all tests"""
    print("Running system tray icon tests...\n")
    
    tests = [
        test_tray_imports,
        test_init_tray_icon_method,
        test_tray_menu_actions,
        test_password_check_on_exit,
        test_force_exit_method,
        test_close_event_minimizes_to_tray,
        test_show_window_method,
        test_double_click_shows_window,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    if failed == 0:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
