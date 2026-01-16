#!/usr/bin/env python3
"""
Test script to verify server handles installation_alert messages correctly
Tests:
1. Server receives and processes installation_alert message
2. Callback is invoked with correct data
3. Message type is recognized (no "Unknown message type" warning)
"""
import sys
import os
import asyncio
import logging
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Add path to src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.server.server import LibLockerServer
from src.shared.protocol import InstallationAlertMessage, Message, MessageType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_installation_alert_handler():
    """Test that server correctly handles installation_alert messages"""
    print("\n" + "=" * 70)
    print("TEST: Server installation_alert message handler")
    print("=" * 70)
    
    # Create a temporary database
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        print("\n1. Creating test server...")
        server = LibLockerServer(db_path=db_path)
        print("  ✓ Server created")
        
        # Setup mock callback
        callback_data = []
        
        def mock_callback(alert_data):
            print(f"  ✓ Callback invoked with data: {alert_data}")
            callback_data.append(alert_data)
        
        server.on_installation_alert = mock_callback
        print("  ✓ Callback registered")
        
        # Create test client connection
        print("\n2. Simulating client connection...")
        test_sid = "test_sid_12345"
        server.connected_clients[test_sid] = {
            'client_id': 1,
            'hwid': 'test_hwid',
            'name': 'Test Client'
        }
        print(f"  ✓ Test client added: {server.connected_clients[test_sid]}")
        
        # Create installation alert message
        print("\n3. Creating installation_alert message...")
        reason = "Обнаружено скачивание установочного файла"
        timestamp = datetime.now().isoformat()
        
        alert_msg = InstallationAlertMessage(
            reason=reason,
            timestamp=timestamp
        )
        message = alert_msg.to_message()
        print(f"  ✓ Message created:")
        print(f"    - Type: {message.type}")
        print(f"    - Reason: {reason}")
        print(f"    - Timestamp: {timestamp}")
        
        # Test that message is recognized
        print("\n4. Verifying message type is recognized...")
        assert message.type == MessageType.INSTALLATION_ALERT.value, "Message type should be installation_alert"
        print(f"  ✓ Message type is correct: {message.type}")
        
        # Process message through handler
        print("\n5. Processing message through server handler...")
        with patch.object(logger, 'warning') as mock_warning:
            await server._handle_message(test_sid, message)
            
            # Verify no "Unknown message type" warning
            warning_calls = [call for call in mock_warning.call_args_list 
                           if 'Unknown message type' in str(call)]
            
            if warning_calls:
                print(f"  ✗ Unexpected warning: {warning_calls}")
                return False
            else:
                print("  ✓ No 'Unknown message type' warning (message is recognized)")
        
        # Wait a bit for async processing
        await asyncio.sleep(0.1)
        
        # Verify callback was invoked
        print("\n6. Verifying callback was invoked...")
        assert len(callback_data) == 1, f"Callback should be invoked once, got {len(callback_data)}"
        print(f"  ✓ Callback invoked {len(callback_data)} time(s)")
        
        # Verify callback data
        print("\n7. Verifying callback data...")
        alert_data = callback_data[0]
        assert alert_data['client_id'] == 1, "Client ID should match"
        assert alert_data['client_name'] == 'Test Client', "Client name should match"
        assert alert_data['reason'] == reason, "Reason should match"
        assert alert_data['timestamp'] == timestamp, "Timestamp should match"
        print(f"  ✓ All callback data is correct:")
        print(f"    - Client ID: {alert_data['client_id']}")
        print(f"    - Client Name: {alert_data['client_name']}")
        print(f"    - Reason: {alert_data['reason']}")
        print(f"    - Timestamp: {alert_data['timestamp']}")
        
        print("\n" + "=" * 70)
        print("RESULT: ✓ TEST PASSED")
        print("=" * 70)
        return True
        
    except AssertionError as e:
        print(f"\n✗ ASSERTION FAILED: {e}")
        print("\n" + "=" * 70)
        print("RESULT: ✗ TEST FAILED")
        print("=" * 70)
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70)
        print("RESULT: ✗ TEST FAILED")
        print("=" * 70)
        return False
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass


async def test_message_type_enum():
    """Test that INSTALLATION_ALERT is defined in MessageType enum"""
    print("\n" + "=" * 70)
    print("TEST: MessageType.INSTALLATION_ALERT enum value")
    print("=" * 70)
    
    print("\n1. Checking MessageType enum...")
    assert hasattr(MessageType, 'INSTALLATION_ALERT'), "INSTALLATION_ALERT should be in MessageType enum"
    print("  ✓ MessageType.INSTALLATION_ALERT exists")
    
    print(f"\n2. Checking value: {MessageType.INSTALLATION_ALERT.value}")
    assert MessageType.INSTALLATION_ALERT.value == 'installation_alert', "Value should be 'installation_alert'"
    print("  ✓ Value is correct")
    
    print("\n" + "=" * 70)
    print("RESULT: ✓ TEST PASSED")
    print("=" * 70)
    return True


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("SERVER INSTALLATION ALERT HANDLER TESTS")
    print("=" * 70)
    
    results = []
    
    # Test 1: MessageType enum
    try:
        result1 = await test_message_type_enum()
        results.append(("MessageType enum", result1))
    except Exception as e:
        print(f"\n✗ ERROR in test 1: {e}")
        import traceback
        traceback.print_exc()
        results.append(("MessageType enum", False))
    
    # Test 2: Handler functionality
    try:
        result2 = await test_installation_alert_handler()
        results.append(("Handler functionality", result2))
    except Exception as e:
        print(f"\n✗ ERROR in test 2: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Handler functionality", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("\n" + "=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
