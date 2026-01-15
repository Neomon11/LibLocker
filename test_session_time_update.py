"""
Test session time update functionality
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shared.protocol import SessionTimeUpdateMessage, MessageType
from datetime import datetime, timedelta


def test_session_time_update_message_creation():
    """Test that SessionTimeUpdateMessage can be created correctly"""
    new_duration = 60
    reason = "admin_update"
    
    msg = SessionTimeUpdateMessage(
        new_duration_minutes=new_duration,
        reason=reason
    )
    
    assert msg.new_duration_minutes == new_duration
    assert msg.reason == reason
    
    print("✓ SessionTimeUpdateMessage creation works")


def test_session_time_update_message_to_message():
    """Test that SessionTimeUpdateMessage converts to Message correctly"""
    new_duration = 45
    
    update_msg = SessionTimeUpdateMessage(
        new_duration_minutes=new_duration,
        reason="admin_update"
    )
    
    message = update_msg.to_message()
    
    # Check message type
    assert message.type == MessageType.SESSION_TIME_UPDATE.value
    
    # Check data
    assert message.data['new_duration_minutes'] == new_duration
    assert message.data['reason'] == "admin_update"
    
    print("✓ SessionTimeUpdateMessage to Message conversion works")


def test_session_time_update_message_serialization():
    """Test that message can be serialized to dict"""
    update_msg = SessionTimeUpdateMessage(
        new_duration_minutes=30,
        reason="admin_update"
    )
    
    message = update_msg.to_message()
    message_dict = message.to_dict()
    
    # Check dictionary structure
    assert 'type' in message_dict
    assert 'data' in message_dict
    assert message_dict['type'] == MessageType.SESSION_TIME_UPDATE.value
    assert message_dict['data']['new_duration_minutes'] == 30
    
    print("✓ Message serialization to dict works")


def test_message_type_exists():
    """Test that SESSION_TIME_UPDATE message type exists in MessageType enum"""
    # Check that the message type exists
    assert hasattr(MessageType, 'SESSION_TIME_UPDATE')
    assert MessageType.SESSION_TIME_UPDATE.value == "session_time_update"
    
    print("✓ SESSION_TIME_UPDATE message type exists in MessageType enum")


if __name__ == "__main__":
    print("Testing session time update functionality...")
    print()
    
    try:
        test_message_type_exists()
        test_session_time_update_message_creation()
        test_session_time_update_message_to_message()
        test_session_time_update_message_serialization()
        
        print()
        print("=" * 50)
        print("All session time update tests passed! ✅")
        print("=" * 50)
    except AssertionError as e:
        print()
        print("=" * 50)
        print(f"Test failed: {e} ❌")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 50)
        print(f"Error during testing: {e} ❌")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        sys.exit(1)
