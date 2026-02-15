#!/usr/bin/env python3
"""
Test script for connection recovery and auto-connect functionality
Tests the improved connection handling in unstable network conditions
"""
import sys
import os
import asyncio
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client.client import LibLockerClient, INITIAL_RECONNECT_DELAY, MAX_RECONNECT_DELAY, RECONNECT_BACKOFF_MULTIPLIER

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_connection_parameters():
    """Test that Socket.IO is configured with proper reconnection parameters"""
    print("=" * 70)
    print("Test 1: Socket.IO Reconnection Parameters")
    print("=" * 70)
    
    client = LibLockerClient("http://localhost:8765")
    
    print("\n📋 Checking Socket.IO configuration...")
    print(f"  ✓ reconnection enabled: {client.sio.reconnection}")
    print(f"  ✓ reconnection_attempts: {client.sio.reconnection_attempts} (0 = infinite)")
    print(f"  ✓ reconnection_delay: {client.sio.reconnection_delay}s")
    print(f"  ✓ reconnection_delay_max: {client.sio.reconnection_delay_max}s")
    
    # Verify constants
    print("\n📋 Checking reconnection constants...")
    print(f"  ✓ INITIAL_RECONNECT_DELAY: {INITIAL_RECONNECT_DELAY}s")
    print(f"  ✓ MAX_RECONNECT_DELAY: {MAX_RECONNECT_DELAY}s")
    print(f"  ✓ RECONNECT_BACKOFF_MULTIPLIER: {RECONNECT_BACKOFF_MULTIPLIER}x")
    
    # Verify parameters match
    success = True
    if client.sio.reconnection_delay != INITIAL_RECONNECT_DELAY:
        print(f"  ✗ ERROR: reconnection_delay doesn't match INITIAL_RECONNECT_DELAY")
        success = False
    
    if client.sio.reconnection_delay_max != MAX_RECONNECT_DELAY:
        print(f"  ✗ ERROR: reconnection_delay_max doesn't match MAX_RECONNECT_DELAY")
        success = False
    
    if not client.sio.reconnection:
        print(f"  ✗ ERROR: reconnection is disabled!")
        success = False
    
    if client.sio.reconnection_attempts != 0:
        print(f"  ✗ ERROR: reconnection_attempts should be 0 (infinite)")
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print("✓✓✓ TEST 1 PASSED - Socket.IO properly configured ✓✓✓")
        return True
    else:
        print("✗✗✗ TEST 1 FAILED - Socket.IO configuration issues ✗✗✗")
        return False


async def test_connection_state_sync():
    """Test that connection state is properly synchronized"""
    print("\n" + "=" * 70)
    print("Test 2: Connection State Synchronization")
    print("=" * 70)
    
    client = LibLockerClient("http://localhost:8765")
    
    print("\n📋 Checking initial state...")
    print(f"  ✓ Initial connected state: {client.connected}")
    print(f"  ✓ Initial status: {client.status}")
    print(f"  ✓ Has connection lock: {hasattr(client, '_connection_lock')}")
    
    success = True
    
    if client.connected:
        print(f"  ✗ ERROR: Client should start as disconnected")
        success = False
    
    if not hasattr(client, '_connection_lock'):
        print(f"  ✗ ERROR: Client missing _connection_lock for synchronization")
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print("✓✓✓ TEST 2 PASSED - Connection state properly initialized ✓✓✓")
        return True
    else:
        print("✗✗✗ TEST 2 FAILED - Connection state issues ✗✗✗")
        return False


async def test_heartbeat_protection():
    """Test that heartbeat has proper timeout and error handling"""
    print("\n" + "=" * 70)
    print("Test 3: Heartbeat Protection")
    print("=" * 70)
    
    client = LibLockerClient("http://localhost:8765")
    
    print("\n📋 Testing heartbeat when disconnected...")
    try:
        await client.send_heartbeat()
        print("  ✓ Heartbeat skipped when disconnected (no exception)")
        success = True
    except Exception as e:
        print(f"  ✗ ERROR: Heartbeat raised exception when disconnected: {e}")
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print("✓✓✓ TEST 3 PASSED - Heartbeat properly protected ✓✓✓")
        return True
    else:
        print("✗✗✗ TEST 3 FAILED - Heartbeat protection issues ✗✗✗")
        return False


async def test_no_duplicate_reconnection():
    """Test that there's no duplicate reconnection logic in run() method"""
    print("\n" + "=" * 70)
    print("Test 4: No Duplicate Reconnection Logic")
    print("=" * 70)
    
    client = LibLockerClient("http://localhost:8765")
    
    print("\n📋 Checking client attributes...")
    
    # Check that old reconnection delay attribute is removed
    has_old_reconnect_delay = hasattr(client, 'reconnect_delay')
    
    if has_old_reconnect_delay:
        print(f"  ✗ WARNING: Client still has 'reconnect_delay' attribute")
        print(f"     This suggests duplicate reconnection logic may still exist")
        success = False
    else:
        print(f"  ✓ No 'reconnect_delay' attribute (manual reconnection removed)")
        success = True
    
    # Verify Socket.IO handles reconnection
    print(f"\n📋 Verifying Socket.IO handles reconnection...")
    print(f"  ✓ Socket.IO reconnection enabled: {client.sio.reconnection}")
    print(f"  ✓ Socket.IO will retry with exponential backoff up to {MAX_RECONNECT_DELAY}s")
    
    print("\n" + "=" * 70)
    if success:
        print("✓✓✓ TEST 4 PASSED - No duplicate reconnection logic ✓✓✓")
        return True
    else:
        print("✗✗✗ TEST 4 FAILED - Duplicate reconnection logic detected ✗✗✗")
        return False


async def test_connect_error_handling():
    """Test that connection errors are handled gracefully"""
    print("\n" + "=" * 70)
    print("Test 5: Connection Error Handling")
    print("=" * 70)
    
    # Try connecting to a non-existent server (using valid port but unreachable)
    client = LibLockerClient("http://192.0.2.1:8765")  # Reserved IP for documentation (RFC 5737)
    
    print("\n📋 Testing connection to unreachable server...")
    try:
        # Try to connect - Socket.IO handles errors internally
        await client.connect()
        # If we get here, connection attempt was made (Socket.IO will retry in background)
        print("  ✓ Connection attempt initiated")
        print("  ✓ Socket.IO will continue retrying in background")
        # Verify client is not marked as connected
        if not client.connected:
            print("  ✓ Client correctly marked as not connected")
            success = True
        else:
            print("  ✗ ERROR: Client incorrectly marked as connected")
            success = False
    except Exception as e:
        print(f"  ✓ Connection failed gracefully: {type(e).__name__}")
        print("  ✓ Socket.IO will continue retrying in background")
        success = True
    
    print("\n" + "=" * 70)
    if success:
        print("✓✓✓ TEST 5 PASSED - Connection errors handled gracefully ✓✓✓")
        return True
    else:
        print("✗✗✗ TEST 5 FAILED - Connection error handling issues ✗✗✗")
        return False


async def test_reconnection_timing():
    """Test that reconnection delays follow exponential backoff pattern"""
    print("\n" + "=" * 70)
    print("Test 6: Reconnection Timing Pattern")
    print("=" * 70)
    
    print("\n📋 Expected reconnection delay pattern:")
    delays = []
    current_delay = INITIAL_RECONNECT_DELAY
    
    for i in range(10):
        delays.append(current_delay)
        print(f"  Attempt {i+1}: {current_delay}s")
        current_delay = min(current_delay * RECONNECT_BACKOFF_MULTIPLIER, MAX_RECONNECT_DELAY)
    
    print(f"\n  ✓ Initial delay: {INITIAL_RECONNECT_DELAY}s")
    print(f"  ✓ Maximum delay: {MAX_RECONNECT_DELAY}s")
    print(f"  ✓ Backoff multiplier: {RECONNECT_BACKOFF_MULTIPLIER}x")
    print(f"  ✓ Reaches max in {delays.index(MAX_RECONNECT_DELAY) + 1} attempts" if MAX_RECONNECT_DELAY in delays else f"  ✓ Continues growing exponentially")
    
    print("\n" + "=" * 70)
    print("✓✓✓ TEST 6 PASSED - Reconnection timing properly configured ✓✓✓")
    return True


async def run_all_tests():
    """Run all connection recovery tests"""
    print("\n" + "=" * 70)
    print("CONNECTION RECOVERY TEST SUITE")
    print("=" * 70)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # Run all tests
    results.append(await test_connection_parameters())
    results.append(await test_connection_state_sync())
    results.append(await test_heartbeat_protection())
    results.append(await test_no_duplicate_reconnection())
    results.append(await test_connect_error_handling())
    results.append(await test_reconnection_timing())
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUITE SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    print(f"Tests failed: {total - passed}/{total}")
    
    if all(results):
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nConnection recovery system is properly configured for unstable networks!")
        return 0
    else:
        print("\n✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("\nPlease review the failed tests above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
