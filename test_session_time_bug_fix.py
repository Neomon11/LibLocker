"""
Test that session time update sets absolute time from now, not relative to start_time
This test verifies Bug 2 fix: session time should be set to the specified duration from NOW,
not from the original start time.
"""
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_session_time_update_absolute():
    """Test that update_session_time sets end_time from current time, not start_time"""
    from client.gui import TimerWidget
    from shared.config import ClientConfig
    
    # Create a session that started 10 minutes ago
    session_data = {
        'duration_minutes': 60,
        'is_unlimited': False,
        'cost_per_hour': 100.0,
        'free_mode': False
    }
    
    config = ClientConfig()
    
    # Create the widget (normally starts now, but we'll simulate it started earlier)
    widget = TimerWidget(session_data, config)
    
    # Simulate that the session started 10 minutes ago
    widget.start_time = datetime.now() - timedelta(minutes=10)
    widget.end_time = widget.start_time + timedelta(minutes=60)
    
    # Initially, there should be about 50 minutes remaining (60 - 10)
    now = datetime.now()
    expected_remaining_before = int((widget.end_time - now).total_seconds())
    
    print(f"Initial state:")
    print(f"  Start time: {widget.start_time}")
    print(f"  End time (before update): {widget.end_time}")
    print(f"  Expected remaining: ~{expected_remaining_before} seconds (~50 minutes)")
    
    # Now update the session time to 30 minutes
    # BUG BEHAVIOR (before fix): end_time = start_time + 30 min = 20 minutes remaining
    # CORRECT BEHAVIOR (after fix): end_time = now + 30 min = 30 minutes remaining
    new_duration_minutes = 30
    widget.update_session_time(new_duration_minutes)
    
    print(f"\nAfter updating to {new_duration_minutes} minutes:")
    print(f"  End time (after update): {widget.end_time}")
    print(f"  Remaining seconds: {widget.remaining_seconds}")
    
    # After the fix, remaining_seconds should be approximately 30 minutes (1800 seconds)
    # Allow some tolerance for execution time (±5 seconds)
    expected_remaining = new_duration_minutes * 60
    tolerance = 5
    
    assert abs(widget.remaining_seconds - expected_remaining) <= tolerance, \
        f"Expected remaining_seconds to be ~{expected_remaining} (±{tolerance}), but got {widget.remaining_seconds}"
    
    # Also verify that end_time is approximately now + new_duration_minutes
    now_after_update = datetime.now()
    expected_end_time = now_after_update + timedelta(minutes=new_duration_minutes)
    time_diff = abs((widget.end_time - expected_end_time).total_seconds())
    
    assert time_diff <= tolerance, \
        f"Expected end_time to be ~{expected_end_time}, but got {widget.end_time} (difference: {time_diff}s)"
    
    print(f"\n✓ Session time update correctly sets absolute time from current time")
    print(f"  Remaining seconds: {widget.remaining_seconds} (~{widget.remaining_seconds // 60} minutes)")
    print(f"  Time difference from expected: {time_diff:.2f} seconds")
    
    widget.force_close()


def test_session_time_update_multiple_times():
    """Test that multiple time updates work correctly"""
    from client.gui import TimerWidget
    from shared.config import ClientConfig
    
    session_data = {
        'duration_minutes': 60,
        'is_unlimited': False,
        'cost_per_hour': 100.0,
        'free_mode': False
    }
    
    config = ClientConfig()
    widget = TimerWidget(session_data, config)
    
    # Simulate passage of time
    widget.start_time = datetime.now() - timedelta(minutes=5)
    widget.end_time = widget.start_time + timedelta(minutes=60)
    
    print("Testing multiple time updates:")
    
    # First update: set to 45 minutes
    widget.update_session_time(45)
    remaining_after_first = widget.remaining_seconds
    print(f"  After first update (45 min): {remaining_after_first} seconds (~{remaining_after_first // 60} minutes)")
    assert abs(remaining_after_first - 45 * 60) <= 5
    
    # Second update: set to 30 minutes
    widget.update_session_time(30)
    remaining_after_second = widget.remaining_seconds
    print(f"  After second update (30 min): {remaining_after_second} seconds (~{remaining_after_second // 60} minutes)")
    assert abs(remaining_after_second - 30 * 60) <= 5
    
    # Third update: extend to 90 minutes
    widget.update_session_time(90)
    remaining_after_third = widget.remaining_seconds
    print(f"  After third update (90 min): {remaining_after_third} seconds (~{remaining_after_third // 60} minutes)")
    assert abs(remaining_after_third - 90 * 60) <= 5
    
    print("✓ Multiple time updates work correctly")
    
    widget.force_close()


def test_session_time_update_with_short_time():
    """Test that time updates work correctly with short durations"""
    from client.gui import TimerWidget
    from shared.config import ClientConfig
    
    session_data = {
        'duration_minutes': 60,
        'is_unlimited': False,
        'cost_per_hour': 100.0,
        'free_mode': False
    }
    
    config = ClientConfig()
    widget = TimerWidget(session_data, config)
    
    # Simulate that session has been running for 55 minutes
    widget.start_time = datetime.now() - timedelta(minutes=55)
    widget.end_time = widget.start_time + timedelta(minutes=60)
    
    # Update to just 5 minutes from now
    widget.update_session_time(5)
    
    print(f"Testing short time update (5 minutes):")
    print(f"  Remaining seconds: {widget.remaining_seconds} (~{widget.remaining_seconds // 60} minutes)")
    
    # Should have approximately 5 minutes remaining
    assert abs(widget.remaining_seconds - 5 * 60) <= 5
    
    print("✓ Short time updates work correctly")
    
    widget.force_close()


if __name__ == "__main__":
    print("Testing session time update bug fix...")
    print("=" * 70)
    print()
    
    try:
        test_session_time_update_absolute()
        print()
        test_session_time_update_multiple_times()
        print()
        test_session_time_update_with_short_time()
        
        print()
        print("=" * 70)
        print("All session time update bug fix tests passed! ✅")
        print("=" * 70)
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"Test failed: {e} ❌")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"Error during testing: {e} ❌")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
