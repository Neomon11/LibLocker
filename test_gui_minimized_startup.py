"""
Test GUI minimized startup behavior (configuration only)
"""
import os
import sys
import tempfile

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shared.config import ClientConfig


def test_minimized_startup_logic():
    """Test the GUI minimized startup configuration logic"""
    print("Testing GUI minimized startup configuration logic...\n")
    
    # Test 1: Normal startup (start_minimized = False)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config_path = f.name
        f.write("""[server]
url = http://localhost:8765
[autostart]
start_minimized = false
[widget]
position_x = 20
position_y = 20
[notifications]
warning_minutes = 5
[security]
admin_password_hash =
[logging]
level = INFO
file = logs/client.log
[installation_monitor]
enabled = false
""")
    
    try:
        config = ClientConfig()
        config.config_file = config_path
        config.load()
        
        # Verify config
        assert not config.start_minimized, "start_minimized should be False"
        print("✓ Test 1 passed: Config reads start_minimized=False correctly")
        
    finally:
        os.unlink(config_path)
    
    # Test 2: Minimized startup (start_minimized = True)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config_path = f.name
        f.write("""[server]
url = http://localhost:8765
[autostart]
start_minimized = true
[widget]
position_x = 20
position_y = 20
[notifications]
warning_minutes = 5
[security]
admin_password_hash =
[logging]
level = INFO
file = logs/client.log
[installation_monitor]
enabled = false
""")
    
    try:
        config = ClientConfig()
        config.config_file = config_path
        config.load()
        
        # Verify config
        assert config.start_minimized, "start_minimized should be True"
        print("✓ Test 2 passed: Config reads start_minimized=True correctly")
        
        # Note: We can't actually test window.showMinimized() without a display server,
        # but we've verified the config logic works correctly
        print("✓ Configuration logic validated successfully")
        
    finally:
        os.unlink(config_path)
    
    print("\n✅ All GUI logic tests passed!")
    print("\nImplementation notes:")
    print("- When start_minimized=true in config, window.showMinimized() is called instead of window.show()")
    print("- The system tray icon is always visible (see init_tray_icon() in gui.py)")
    print("- Users can restore the window by double-clicking the tray icon or using the context menu")


if __name__ == "__main__":
    try:
        test_minimized_startup_logic()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
