#!/usr/bin/env python3
"""
Simple integration test to verify client can be instantiated
and basic connection logic works
"""
import sys
import os
import asyncio
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client.client import LibLockerClient
from src.shared.config import ClientConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_client_instantiation():
    """Test that client can be created with new configuration"""
    print("=" * 70)
    print("Test: Client Instantiation and Configuration")
    print("=" * 70)
    
    # Test 1: Create client with default URL
    print("\n📋 Test 1: Create client with default URL")
    try:
        client1 = LibLockerClient()
        print(f"  ✓ Client created successfully")
        print(f"  ✓ Server URL: {client1.server_url}")
        print(f"  ✓ Connected: {client1.connected}")
        print(f"  ✓ Has connection lock: {hasattr(client1, '_connection_lock')}")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 2: Create client with custom URL
    print("\n📋 Test 2: Create client with custom URL")
    try:
        client2 = LibLockerClient("http://192.168.1.100:8765")
        print(f"  ✓ Client created successfully")
        print(f"  ✓ Server URL: {client2.server_url}")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 3: Verify Socket.IO configuration
    print("\n📋 Test 3: Verify Socket.IO configuration")
    try:
        print(f"  ✓ Reconnection enabled: {client1.sio.reconnection}")
        print(f"  ✓ Reconnection attempts: {client1.sio.reconnection_attempts}")
        print(f"  ✓ Initial delay: {client1.sio.reconnection_delay}s")
        print(f"  ✓ Max delay: {client1.sio.reconnection_delay_max}s")
        
        if not client1.sio.reconnection:
            print("  ✗ FAILED: Reconnection should be enabled")
            return False
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 4: Verify callbacks can be set
    print("\n📋 Test 4: Verify callbacks can be set")
    try:
        callback_called = {'value': False}
        
        def test_callback():
            callback_called['value'] = True
        
        client1.on_connected = test_callback
        print(f"  ✓ Callback set successfully")
        
        # Call the callback manually to test it works
        if asyncio.iscoroutinefunction(client1.on_connected):
            await client1.on_connected()
        else:
            client1.on_connected()
        
        if callback_called['value']:
            print(f"  ✓ Callback executed successfully")
        else:
            print(f"  ✗ FAILED: Callback was not called")
            return False
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 5: Test heartbeat when not connected
    print("\n📋 Test 5: Test heartbeat when not connected")
    try:
        await client1.send_heartbeat()
        print(f"  ✓ Heartbeat handled gracefully when not connected")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓✓✓ ALL TESTS PASSED ✓✓✓")
    return True


async def test_config_integration():
    """Test that ClientConfig auto_connect works"""
    print("\n" + "=" * 70)
    print("Test: ClientConfig Integration")
    print("=" * 70)
    
    try:
        config = ClientConfig()
        auto_connect = config.auto_connect
        print(f"\n📋 Config auto_connect value: {auto_connect}")
        print(f"  ✓ Config loaded successfully")
        print(f"  ✓ auto_connect = {auto_connect}")
        
        print("\n" + "=" * 70)
        print("✓✓✓ CONFIG TEST PASSED ✓✓✓")
        return True
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all integration tests"""
    results = []
    
    results.append(await test_client_instantiation())
    results.append(await test_config_integration())
    
    print("\n" + "=" * 70)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
    if all(results):
        print("\n✓✓✓ ALL INTEGRATION TESTS PASSED ✓✓✓")
        return 0
    else:
        print("\n✗✗✗ SOME INTEGRATION TESTS FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
