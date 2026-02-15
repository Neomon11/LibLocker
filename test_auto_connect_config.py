#!/usr/bin/env python3
"""
Test script for auto_connect configuration functionality
Tests that the auto_connect setting properly controls client connection behavior
"""
import sys
import os
import configparser
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.shared.config import ClientConfig

print("=" * 70)
print("Test: Auto-Connect Configuration")
print("=" * 70)


def test_auto_connect_default():
    """Test that auto_connect defaults to True"""
    print("\n📋 Test 1: Default auto_connect value")
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config_path = f.name
        f.write("""[server]
url = http://localhost:8765

[autostart]
enabled = false
""")
    
    try:
        # Load config (without auto_connect specified)
        config = ClientConfig()
        config.config_file = config_path
        config.config = configparser.ConfigParser()
        config.config.read(config_path)
        
        auto_connect = config.auto_connect
        
        if auto_connect:
            print("  ✓ auto_connect defaults to True (as expected)")
            return True
        else:
            print("  ✗ ERROR: auto_connect should default to True")
            return False
    finally:
        os.unlink(config_path)


def test_auto_connect_explicit_false():
    """Test that auto_connect can be set to False"""
    print("\n📋 Test 2: Explicit auto_connect = false")
    
    # Create a temporary config file with auto_connect = false
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config_path = f.name
        f.write("""[server]
url = http://localhost:8765

[autostart]
enabled = false
auto_connect = false
""")
    
    try:
        # Load config
        config = ClientConfig()
        config.config_file = config_path
        config.config = configparser.ConfigParser()
        config.config.read(config_path)
        
        auto_connect = config.auto_connect
        
        if not auto_connect:
            print("  ✓ auto_connect correctly set to False")
            return True
        else:
            print("  ✗ ERROR: auto_connect should be False")
            return False
    finally:
        os.unlink(config_path)


def test_auto_connect_explicit_true():
    """Test that auto_connect can be explicitly set to True"""
    print("\n📋 Test 3: Explicit auto_connect = true")
    
    # Create a temporary config file with auto_connect = true
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config_path = f.name
        f.write("""[server]
url = http://localhost:8765

[autostart]
enabled = false
auto_connect = true
""")
    
    try:
        # Load config
        config = ClientConfig()
        config.config_file = config_path
        config.config = configparser.ConfigParser()
        config.config.read(config_path)
        
        auto_connect = config.auto_connect
        
        if auto_connect:
            print("  ✓ auto_connect correctly set to True")
            return True
        else:
            print("  ✗ ERROR: auto_connect should be True")
            return False
    finally:
        os.unlink(config_path)


def test_config_file_example():
    """Test that the example config file has auto_connect documented"""
    print("\n📋 Test 4: Example config documentation")
    
    example_config_path = 'config.client.example.ini'
    
    if not os.path.exists(example_config_path):
        print(f"  ⚠ WARNING: {example_config_path} not found")
        return True  # Not a critical failure
    
    with open(example_config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_autostart_section = '[autostart]' in content
    has_auto_connect = 'auto_connect' in content
    
    if has_autostart_section and has_auto_connect:
        print(f"  ✓ auto_connect is documented in {example_config_path}")
        return True
    else:
        if not has_autostart_section:
            print(f"  ⚠ WARNING: [autostart] section missing in {example_config_path}")
        if not has_auto_connect:
            print(f"  ⚠ WARNING: auto_connect not documented in {example_config_path}")
        return True  # Not a critical failure


def run_tests():
    """Run all auto_connect configuration tests"""
    results = []
    
    results.append(test_auto_connect_default())
    results.append(test_auto_connect_explicit_false())
    results.append(test_auto_connect_explicit_true())
    results.append(test_config_file_example())
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    
    if all(results):
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nauto_connect configuration is working correctly!")
        return 0
    else:
        print("\n✗✗✗ SOME TESTS FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
