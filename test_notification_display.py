"""
Test notification display fixes for LibLocker widget
Tests that notifications are properly displayed and not cut off
"""
import sys
import os
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def extract_method_content(file_content, method_name):
    """
    Extract a method's content from Python source code.
    Uses regex to find method boundaries.
    
    Args:
        file_content: Full source code as string
        method_name: Name of method to extract (e.g., 'show_warning_popup')
    
    Returns:
        Method content as string, or None if not found
    """
    # Pattern to match method definition (with or without leading newline)
    pattern = rf'(\n\s*)?def {re.escape(method_name)}\([^)]*\):'
    
    # Find method start
    method_match = re.search(pattern, file_content, re.MULTILINE)
    if not method_match:
        return None
    
    start_idx = method_match.start()
    
    # Find the actual start of the def line (after any leading newline)
    def_line_start = file_content[start_idx:].find('def ')
    start_idx = start_idx + def_line_start
    
    # Find the next method or class at the same indentation level
    # Get the indentation of this method
    def_line = file_content[start_idx:start_idx+100].split('\n')[0]
    indent = len(def_line) - len(def_line.lstrip())
    
    # Look for next def or class at same or lower indentation
    lines = file_content[start_idx:].split('\n')
    end_line_idx = 1  # Start after method definition line
    
    for i, line in enumerate(lines[1:], 1):
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            continue
        
        # Check if this line has equal or less indentation and starts with def or class
        if len(line) - len(line.lstrip()) <= indent and (line.strip().startswith('def ') or line.strip().startswith('class ')):
            end_line_idx = i
            break
    else:
        end_line_idx = len(lines)
    
    method_content = '\n'.join(lines[:end_line_idx])
    return method_content


def test_notification_not_parented_to_widget():
    """Test that notifications are created without widget parent"""
    print("\n" + "="*60)
    print("Testing notification independence from widget")
    print("="*60)
    
    # Read the source file and verify the fix
    gui_file = os.path.join(os.path.dirname(__file__), 'src', 'client', 'gui.py')
    
    with open(gui_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that show_warning_popup creates QMessageBox without parent
    method_content = extract_method_content(content, 'show_warning_popup')
    
    if method_content is None:
        print("✗ show_warning_popup method not found")
        return False
    
    # Check that it creates QMessageBox() without self as parent
    if 'msg = QMessageBox()' in method_content:
        print("✓ show_warning_popup creates independent QMessageBox")
    else:
        print("✗ show_warning_popup still uses widget as parent")
        return False
    
    # Check that it sets proper window flags
    if 'Qt.WindowType.Dialog' in method_content:
        print("✓ show_warning_popup sets Dialog window flag")
    else:
        print("✗ show_warning_popup missing Dialog window flag")
        return False
    
    # Check that update_session_time notification is also independent
    method_content = extract_method_content(content, 'update_session_time')
    
    if method_content is None:
        print("✗ update_session_time method not found")
        return False
    
    # Check for independent QMessageBox in nested function
    if 'msg = QMessageBox()' in method_content:
        print("✓ update_session_time notification creates independent QMessageBox")
    else:
        print("✗ update_session_time notification still uses widget as parent")
        return False
    
    # Check that it sets proper window flags
    if 'Qt.WindowType.Dialog' in method_content:
        print("✓ update_session_time notification sets Dialog window flag")
    else:
        print("✗ update_session_time notification missing Dialog window flag")
        return False
    
    print("\n✅ All notification dialogs are independent from widget")
    print("   This means they won't be cut off by small widget size")
    return True


def test_server_time_display_fix():
    """Test that server GUI time display fix is present"""
    print("\n" + "="*60)
    print("Testing server GUI time display fix")
    print("="*60)
    
    # Read the server GUI file
    server_gui_file = os.path.join(os.path.dirname(__file__), 'src', 'server', 'gui.py')
    
    with open(server_gui_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the fix that adds tolerance for clock sync
    if 'remaining_seconds < -5' in content:
        print("✓ Server GUI has clock sync tolerance (-5 seconds)")
    else:
        print("✗ Server GUI missing clock sync tolerance")
        return False
    
    # Check that we show remaining time even when slightly negative
    if 'max(0, int(remaining_seconds / 60))' in content:
        print("✓ Server GUI uses max(0, ...) to prevent negative display")
    else:
        print("✗ Server GUI might show negative times")
        return False
    
    print("\n✅ Server time display fix is present")
    print("   'Завершается...' only shows 5+ seconds after end")
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("NOTIFICATION AND TIME DISPLAY FIX VERIFICATION")
    print("="*70)
    print("\nThis test verifies that code changes are present:")
    print("1. Notification dialogs are independent (not constrained by widget)")
    print("2. Server time display has clock sync tolerance")
    print("="*70)
    
    try:
        success = True
        
        # Test 1: Notification independence
        if not test_notification_not_parented_to_widget():
            success = False
        
        # Test 2: Server time display
        if not test_server_time_display_fix():
            success = False
        
        if success:
            print("\n" + "="*70)
            print("✅ ALL VERIFICATIONS PASSED")
            print("\nThe fixes are in place:")
            print("- Notifications will display as full-sized independent dialogs")
            print("- Server won't show 'Завершается...' for active sessions")
            print("="*70)
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("❌ SOME VERIFICATIONS FAILED")
            print("="*70)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
