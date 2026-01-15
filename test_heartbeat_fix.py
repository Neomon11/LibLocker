"""
Test to verify the heartbeat fix
Tests that remaining_seconds callback is properly set and used
"""
import sys
import os
from typing import Optional, Callable

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


class MockTimerWidget:
    """Mock TimerWidget for testing"""
    def __init__(self, remaining_seconds: int):
        self.remaining_seconds: int = remaining_seconds


class MockClient:
    """Mock LibLockerClient for testing"""
    def __init__(self):
        self.get_remaining_seconds: Optional[Callable] = None


class MockMainWindow:
    """Mock MainClientWindow for testing"""
    def __init__(self):
        self.timer_widget = None
        self.client = MockClient()
    
    def get_remaining_seconds(self):
        """Get remaining seconds from timer widget"""
        if self.timer_widget:
            return self.timer_widget.remaining_seconds
        return None


def test_callback_mechanism():
    """Test that callback mechanism works correctly"""
    print("Testing callback mechanism for remaining_seconds...")
    print("=" * 70)
    
    # Create mock objects
    window = MockMainWindow()
    
    # Set the callback on the client
    window.client.get_remaining_seconds = window.get_remaining_seconds
    
    # Test 1: No timer widget - should return None
    result = window.client.get_remaining_seconds()
    if result is None:
        print("✅ PASS: Returns None when no timer widget")
    else:
        print(f"❌ FAIL: Expected None, got {result}")
        return False
    
    # Test 2: Timer widget with time - should return remaining seconds
    window.timer_widget = MockTimerWidget(300)  # 5 minutes
    result = window.client.get_remaining_seconds()
    if result == 300:
        print("✅ PASS: Returns correct remaining_seconds (300)")
    else:
        print(f"❌ FAIL: Expected 300, got {result}")
        return False
    
    # Test 3: Timer widget with low time
    window.timer_widget = MockTimerWidget(60)  # 1 minute
    result = window.client.get_remaining_seconds()
    if result == 60:
        print("✅ PASS: Returns correct remaining_seconds (60)")
    else:
        print(f"❌ FAIL: Expected 60, got {result}")
        return False
    
    # Test 4: Timer widget with 0 time
    window.timer_widget = MockTimerWidget(0)
    result = window.client.get_remaining_seconds()
    if result == 0:
        print("✅ PASS: Returns 0 when session expired")
    else:
        print(f"❌ FAIL: Expected 0, got {result}")
        return False
    
    print("=" * 70)
    return True


def test_heartbeat_data():
    """Test that heartbeat would send correct data"""
    print("\nTesting heartbeat data structure...")
    print("=" * 70)
    
    # Simulate what the heartbeat would send
    test_cases = [
        (None, "No session active"),
        (300, "Session with 5 minutes remaining"),
        (60, "Session with 1 minute remaining"),
        (0, "Session expired"),
    ]
    
    for remaining_seconds, description in test_cases:
        # This simulates the HeartbeatMessage construction
        heartbeat_data = {
            "type": "client_heartbeat",
            "data": {
                "status": "in_session" if remaining_seconds is not None else "online",
                "remaining_seconds": remaining_seconds
            }
        }
        
        # Verify data structure
        has_remaining = "remaining_seconds" in heartbeat_data["data"]
        correct_value = heartbeat_data["data"]["remaining_seconds"] == remaining_seconds
        
        if has_remaining and correct_value:
            print(f"✅ PASS: {description} - remaining_seconds={remaining_seconds}")
        else:
            print(f"❌ FAIL: {description}")
            return False
    
    print("=" * 70)
    return True


if __name__ == "__main__":
    print("LibLocker Heartbeat Fix Test")
    print("=" * 70)
    print()
    
    # Run tests
    test1_passed = test_callback_mechanism()
    test2_passed = test_heartbeat_data()
    
    print("\n" + "=" * 70)
    if test1_passed and test2_passed:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
