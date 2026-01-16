"""
Test session tariff update functionality
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shared.protocol import SessionTariffUpdateMessage, MessageType


def test_session_tariff_update_message_creation():
    """Test that SessionTariffUpdateMessage can be created correctly"""
    free_mode = False
    cost_per_hour = 100.0
    
    msg = SessionTariffUpdateMessage(
        free_mode=free_mode,
        cost_per_hour=cost_per_hour
    )
    
    assert msg.free_mode == free_mode
    assert msg.cost_per_hour == cost_per_hour
    
    print("✓ SessionTariffUpdateMessage creation works")


def test_session_tariff_update_message_to_message():
    """Test that SessionTariffUpdateMessage converts to Message correctly"""
    free_mode = True
    cost_per_hour = 0.0
    
    update_msg = SessionTariffUpdateMessage(
        free_mode=free_mode,
        cost_per_hour=cost_per_hour
    )
    
    message = update_msg.to_message()
    
    # Check message type
    assert message.type == MessageType.SESSION_TARIFF_UPDATE.value
    
    # Check data
    assert message.data['free_mode'] == free_mode
    assert message.data['cost_per_hour'] == cost_per_hour
    
    print("✓ SessionTariffUpdateMessage to Message conversion works")


def test_session_tariff_update_message_serialization():
    """Test that message can be serialized to dict"""
    update_msg = SessionTariffUpdateMessage(
        free_mode=False,
        cost_per_hour=150.5
    )
    
    message = update_msg.to_message()
    message_dict = message.to_dict()
    
    # Check dictionary structure
    assert 'type' in message_dict
    assert 'data' in message_dict
    assert message_dict['type'] == MessageType.SESSION_TARIFF_UPDATE.value
    assert message_dict['data']['free_mode'] == False
    assert message_dict['data']['cost_per_hour'] == 150.5
    
    print("✓ Message serialization to dict works")


def test_message_type_exists():
    """Test that SESSION_TARIFF_UPDATE message type exists in MessageType enum"""
    # Check that the message type exists
    assert hasattr(MessageType, 'SESSION_TARIFF_UPDATE')
    assert MessageType.SESSION_TARIFF_UPDATE.value == "session_tariff_update"
    
    print("✓ SESSION_TARIFF_UPDATE message type exists in MessageType enum")


def test_free_to_paid_transition():
    """Test transition from free to paid session"""
    # Start with free session
    msg1 = SessionTariffUpdateMessage(
        free_mode=True,
        cost_per_hour=0.0
    )
    
    assert msg1.free_mode == True
    assert msg1.cost_per_hour == 0.0
    
    # Change to paid session
    msg2 = SessionTariffUpdateMessage(
        free_mode=False,
        cost_per_hour=100.0
    )
    
    assert msg2.free_mode == False
    assert msg2.cost_per_hour == 100.0
    
    print("✓ Free to paid session transition works")


def test_paid_to_free_transition():
    """Test transition from paid to free session"""
    # Start with paid session
    msg1 = SessionTariffUpdateMessage(
        free_mode=False,
        cost_per_hour=100.0
    )
    
    assert msg1.free_mode == False
    assert msg1.cost_per_hour == 100.0
    
    # Change to free session
    msg2 = SessionTariffUpdateMessage(
        free_mode=True,
        cost_per_hour=0.0
    )
    
    assert msg2.free_mode == True
    assert msg2.cost_per_hour == 0.0
    
    print("✓ Paid to free session transition works")


if __name__ == "__main__":
    print("Testing session tariff update functionality...")
    print()
    
    try:
        test_message_type_exists()
        test_session_tariff_update_message_creation()
        test_session_tariff_update_message_to_message()
        test_session_tariff_update_message_serialization()
        test_free_to_paid_transition()
        test_paid_to_free_transition()
        
        print()
        print("=" * 50)
        print("All session tariff update tests passed! ✅")
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
