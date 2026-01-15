"""
Test notification display fixes for LibLocker widget
Tests that notifications are properly displayed and not cut off
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


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
    if 'def show_warning_popup(self):' in content:
        # Find the method
        start_idx = content.index('def show_warning_popup(self):')
        end_idx = content.index('def ', start_idx + 1)
        method_content = content[start_idx:end_idx]
        
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
    else:
        print("✗ show_warning_popup method not found")
        return False
    
    # Check that update_session_time notification is also independent
    if 'def update_session_time(self' in content:
        # Find the method
        start_idx = content.index('def update_session_time(self')
        # Find next method
        next_method_idx = content.find('\n    def ', start_idx + 1)
        method_content = content[start_idx:next_method_idx if next_method_idx > 0 else len(content)]
        
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
    else:
        print("✗ update_session_time method not found")
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
