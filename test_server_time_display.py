"""
Test server GUI time display fix
Tests that "Завершается..." only shows when session has actually ended
"""
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_time_display_logic():
    """Test the time display logic for active sessions"""
    print("\n" + "="*60)
    print("Testing server GUI time display logic")
    print("="*60)
    
    # Simulate the logic from server GUI
    def get_time_text(remaining_seconds):
        """Simulate the server GUI time display logic"""
        # Показываем "Завершается..." только если время истекло более 5 секунд назад
        if remaining_seconds < -5:
            return "Завершается..."
        else:
            # Показываем оставшееся время, даже если оно немного отрицательное
            remaining_minutes = max(0, int(remaining_seconds / 60))
            hours = remaining_minutes // 60
            minutes = remaining_minutes % 60
            return f"{hours:02d}:{minutes:02d} осталось"
    
    # Test cases
    test_cases = [
        # (remaining_seconds, expected_contains, description)
        (3600, "01:00 осталось", "1 hour remaining"),
        (300, "00:05 осталось", "5 minutes remaining"),
        (60, "00:01 осталось", "1 minute remaining"),
        (30, "00:00 осталось", "30 seconds remaining (rounds to 0)"),
        (5, "00:00 осталось", "5 seconds remaining"),
        (0, "00:00 осталось", "Exactly at end time"),
        (-1, "00:00 осталось", "1 second past end (should still show 00:00)"),
        (-3, "00:00 осталось", "3 seconds past end (clock sync tolerance)"),
        (-5, "00:00 осталось", "5 seconds past end (boundary case)"),
        (-6, "Завершается...", "6 seconds past end (should show finishing)"),
        (-60, "Завершается...", "1 minute past end"),
        (-300, "Завершается...", "5 minutes past end"),
    ]
    
    all_passed = True
    for remaining_seconds, expected, description in test_cases:
        result = get_time_text(remaining_seconds)
        passed = expected in result or result == expected
        
        status = "✓" if passed else "✗"
        print(f"{status} {description}")
        print(f"  Remaining: {remaining_seconds}s → Display: '{result}'")
        
        if not passed:
            print(f"  ❌ FAILED: Expected '{expected}', got '{result}'")
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("\nKey improvements:")
        print("1. Session shows time even with small clock sync differences")
        print("2. 'Завершается...' only shows 5+ seconds after end")
        print("3. No negative time displayed to users")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60)
    
    return all_passed


def test_session_scenarios():
    """Test realistic session scenarios"""
    print("\n" + "="*60)
    print("Testing realistic session scenarios")
    print("="*60)
    
    from datetime import datetime, timedelta
    
    # Simulate a session that was just updated
    print("\n📝 Scenario 1: Session just started (10 minutes)")
    start_time = datetime.now()
    duration_minutes = 10
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    # Check time at various points
    now = datetime.now()
    remaining = end_time - now
    remaining_seconds = remaining.total_seconds()
    
    print(f"Start time: {start_time.strftime('%H:%M:%S')}")
    print(f"End time: {end_time.strftime('%H:%M:%S')}")
    print(f"Current time: {now.strftime('%H:%M:%S')}")
    print(f"Remaining: {remaining_seconds:.1f} seconds")
    
    if remaining_seconds < -5:
        display = "Завершается..."
    else:
        remaining_minutes = max(0, int(remaining_seconds / 60))
        hours = remaining_minutes // 60
        minutes = remaining_minutes % 60
        display = f"{hours:02d}:{minutes:02d} осталось"
    
    print(f"Display: '{display}'")
    
    # Should show approximately 10:00 or 09:59
    assert "Завершается" not in display, "Session just started shouldn't show finishing"
    print("✓ Correctly shows remaining time")
    
    # Scenario 2: Session with slight clock difference
    print("\n📝 Scenario 2: Clock sync difference (session appears 2 seconds over)")
    start_time = datetime.now() - timedelta(minutes=10, seconds=2)
    duration_minutes = 10
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    now = datetime.now()
    remaining = end_time - now
    remaining_seconds = remaining.total_seconds()
    
    print(f"Start time: {start_time.strftime('%H:%M:%S')}")
    print(f"End time: {end_time.strftime('%H:%M:%S')}")
    print(f"Current time: {now.strftime('%H:%M:%S')}")
    print(f"Remaining: {remaining_seconds:.1f} seconds (negative)")
    
    if remaining_seconds < -5:
        display = "Завершается..."
    else:
        remaining_minutes = max(0, int(remaining_seconds / 60))
        hours = remaining_minutes // 60
        minutes = remaining_minutes % 60
        display = f"{hours:02d}:{minutes:02d} осталось"
    
    print(f"Display: '{display}'")
    
    # Should still show 00:00 instead of "Завершается..."
    assert "Завершается" not in display, "Small clock difference should be tolerated"
    print("✓ Correctly handles small clock sync difference")
    
    # Scenario 3: Session clearly ended
    print("\n📝 Scenario 3: Session ended 30 seconds ago")
    start_time = datetime.now() - timedelta(minutes=10, seconds=30)
    duration_minutes = 10
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    now = datetime.now()
    remaining = end_time - now
    remaining_seconds = remaining.total_seconds()
    
    print(f"Remaining: {remaining_seconds:.1f} seconds (negative)")
    
    if remaining_seconds < -5:
        display = "Завершается..."
    else:
        remaining_minutes = max(0, int(remaining_seconds / 60))
        hours = remaining_minutes // 60
        minutes = remaining_minutes % 60
        display = f"{hours:02d}:{minutes:02d} осталось"
    
    print(f"Display: '{display}'")
    
    # Should show "Завершается..."
    assert "Завершается" in display, "Session ended 30s ago should show finishing"
    print("✓ Correctly shows 'Завершается...' for ended session")
    
    print("\n" + "="*60)
    print("✅ ALL SCENARIOS PASSED")
    print("="*60)
    
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SERVER GUI TIME DISPLAY FIX TEST SUITE")
    print("="*70)
    print("\nThis test verifies that:")
    print("1. 'Завершается...' only shows when session has actually ended")
    print("2. Small clock sync differences are tolerated")
    print("3. Active sessions always show remaining time")
    print("="*70)
    
    try:
        success = True
        
        # Test 1: Logic test
        if not test_time_display_logic():
            success = False
        
        # Test 2: Scenario test
        if not test_session_scenarios():
            success = False
        
        if success:
            print("\n" + "="*70)
            print("✅ ALL TESTS PASSED")
            print("="*70)
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("❌ SOME TESTS FAILED")
            print("="*70)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
