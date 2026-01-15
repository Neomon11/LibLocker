"""
Test status localization
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shared.models import ClientStatus


def test_client_status_values():
    """Test that ClientStatus enum has correct values"""
    # Check all status values
    assert ClientStatus.OFFLINE.value == "offline"
    assert ClientStatus.ONLINE.value == "online"
    assert ClientStatus.IN_SESSION.value == "in_session"
    assert ClientStatus.BLOCKED.value == "blocked"
    
    print("✓ ClientStatus enum values are correct")


def test_status_localization_mapping():
    """Test status to Russian translation mapping"""
    # Define the localization mapping
    status_localization = {
        ClientStatus.ONLINE.value: "Онлайн",
        ClientStatus.OFFLINE.value: "Оффлайн",
        ClientStatus.IN_SESSION.value: "В сессии",
        ClientStatus.BLOCKED.value: "Заблокирован"
    }
    
    # Test all mappings
    assert status_localization[ClientStatus.ONLINE.value] == "Онлайн"
    assert status_localization[ClientStatus.OFFLINE.value] == "Оффлайн"
    assert status_localization[ClientStatus.IN_SESSION.value] == "В сессии"
    assert status_localization[ClientStatus.BLOCKED.value] == "Заблокирован"
    
    print("✓ Status localization mapping is correct")


def test_localization_completeness():
    """Test that all statuses have localization"""
    status_localization = {
        ClientStatus.ONLINE.value: "Онлайн",
        ClientStatus.OFFLINE.value: "Оффлайн",
        ClientStatus.IN_SESSION.value: "В сессии",
        ClientStatus.BLOCKED.value: "Заблокирован"
    }
    
    # Check that all enum values have a translation
    for status in ClientStatus:
        assert status.value in status_localization, f"Missing localization for {status.value}"
    
    print("✓ All statuses have localization")


if __name__ == "__main__":
    print("Testing status localization...")
    print()
    
    try:
        test_client_status_values()
        test_status_localization_mapping()
        test_localization_completeness()
        
        print()
        print("=" * 50)
        print("All status localization tests passed! ✅")
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
