"""
Test minimized startup functionality
"""
import os
import sys
import tempfile
import configparser
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shared.config import ClientConfig


def test_start_minimized_config():
    """Test that start_minimized config property works correctly"""
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config_path = f.name
        f.write("""[server]
url = http://localhost:8765

[autostart]
enabled = false
auto_connect = true
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
        # Create config with custom path
        config = ClientConfig()
        config.config_file = config_path
        config.load()
        
        # Test that start_minimized returns True
        assert config.start_minimized, "start_minimized should be True"
        print("✓ Test passed: start_minimized config reads True correctly")
        
    finally:
        # Clean up
        os.unlink(config_path)


def test_start_minimized_default():
    """Test that start_minimized defaults to False"""
    
    # Create a temporary config file without start_minimized option
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config_path = f.name
        f.write("""[server]
url = http://localhost:8765

[autostart]
enabled = false
auto_connect = true

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
        # Create config with custom path
        config = ClientConfig()
        config.config_file = config_path
        config.load()
        
        # Test that start_minimized defaults to False
        assert not config.start_minimized, "start_minimized should default to False"
        print("✓ Test passed: start_minimized defaults to False when not specified")
        
    finally:
        # Clean up
        os.unlink(config_path)


def test_start_minimized_false():
    """Test that start_minimized can be explicitly set to False"""
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config_path = f.name
        f.write("""[server]
url = http://localhost:8765

[autostart]
enabled = false
auto_connect = true
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
        # Create config with custom path
        config = ClientConfig()
        config.config_file = config_path
        config.load()
        
        # Test that start_minimized returns False
        assert not config.start_minimized, "start_minimized should be False"
        print("✓ Test passed: start_minimized config reads False correctly")
        
    finally:
        # Clean up
        os.unlink(config_path)


if __name__ == "__main__":
    print("Testing minimized startup configuration...\n")
    
    try:
        test_start_minimized_config()
        test_start_minimized_default()
        test_start_minimized_false()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
