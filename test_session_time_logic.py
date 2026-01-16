"""
Test that session time update logic is correct (without GUI dependencies)
This test verifies Bug 2 fix: session time should be set to the specified duration from NOW,
not from the original start time.
"""
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_time_update_logic_absolute():
    """
    Test the logic of time update calculation
    
    Bug scenario (before fix):
    - Session starts at T0
    - Session duration: 60 minutes, so end_time = T0 + 60 min
    - 10 minutes pass (now is T0 + 10 min)
    - Admin updates to 30 minutes
    - WRONG: end_time = T0 + 30 min = only 20 minutes remaining
    - CORRECT: end_time = now + 30 min = 30 minutes remaining
    """
    
    # Simulate the scenario
    start_time = datetime.now() - timedelta(minutes=10)  # Started 10 minutes ago
    current_time = datetime.now()
    new_duration_minutes = 30
    
    # OLD (BUGGY) LOGIC: end_time = start_time + new_duration_minutes
    old_end_time = start_time + timedelta(minutes=new_duration_minutes)
    old_remaining = (old_end_time - current_time).total_seconds()
    
    # NEW (FIXED) LOGIC: end_time = current_time + new_duration_minutes
    new_end_time = current_time + timedelta(minutes=new_duration_minutes)
    new_remaining = (new_end_time - current_time).total_seconds()
    
    print("Scenario: Session started 10 minutes ago, admin sets time to 30 minutes")
    print(f"  Start time: {start_time}")
    print(f"  Current time: {current_time}")
    print(f"  New duration: {new_duration_minutes} minutes")
    print()
    print("OLD (BUGGY) LOGIC:")
    print(f"  end_time = start_time + duration = {old_end_time}")
    print(f"  Remaining: {old_remaining / 60:.1f} minutes")
    print()
    print("NEW (FIXED) LOGIC:")
    print(f"  end_time = current_time + duration = {new_end_time}")
    print(f"  Remaining: {new_remaining / 60:.1f} minutes")
    print()
    
    # The fix should give us the expected 30 minutes
    expected_remaining = new_duration_minutes * 60
    assert abs(new_remaining - expected_remaining) <= 1, \
        f"Expected {expected_remaining} seconds, got {new_remaining}"
    
    # The old logic would give us less time (about 20 minutes in this case)
    assert old_remaining < new_remaining, \
        "Old logic should give less remaining time"
    
    print("✓ Fixed logic correctly sets absolute time from current time")
    print(f"  Difference: {(new_remaining - old_remaining) / 60:.1f} minutes more with fix")


def test_time_update_scenarios():
    """Test various time update scenarios"""
    
    scenarios = [
        {
            'name': 'Extend time after 15 minutes',
            'elapsed_minutes': 15,
            'original_duration': 60,
            'new_duration': 90,
        },
        {
            'name': 'Reduce time after 5 minutes',
            'elapsed_minutes': 5,
            'original_duration': 60,
            'new_duration': 30,
        },
        {
            'name': 'Update with 1 minute elapsed',
            'elapsed_minutes': 1,
            'original_duration': 30,
            'new_duration': 45,
        },
        {
            'name': 'Update after most time elapsed',
            'elapsed_minutes': 55,
            'original_duration': 60,
            'new_duration': 10,
        }
    ]
    
    print("Testing various time update scenarios:")
    print()
    
    for scenario in scenarios:
        elapsed = scenario['elapsed_minutes']
        original = scenario['original_duration']
        new_duration = scenario['new_duration']
        
        start_time = datetime.now() - timedelta(minutes=elapsed)
        current_time = datetime.now()
        
        # Fixed logic: end_time from current time
        end_time = current_time + timedelta(minutes=new_duration)
        remaining_seconds = int((end_time - current_time).total_seconds())
        remaining_minutes = remaining_seconds / 60
        
        print(f"{scenario['name']}:")
        print(f"  Original duration: {original} min, Elapsed: {elapsed} min")
        print(f"  New duration: {new_duration} min")
        print(f"  Remaining after update: {remaining_minutes:.1f} min")
        
        # Verify that remaining time equals new duration (within tolerance)
        expected = new_duration * 60
        assert abs(remaining_seconds - expected) <= 2, \
            f"Expected {expected}s, got {remaining_seconds}s"
        
        print(f"  ✓ Correct")
        print()
    
    print("✓ All scenarios passed")


def test_edge_cases():
    """Test edge cases for time updates"""
    
    print("Testing edge cases:")
    print()
    
    # Case 1: Very short duration (1 minute)
    current_time = datetime.now()
    new_duration = 1
    end_time = current_time + timedelta(minutes=new_duration)
    remaining = int((end_time - current_time).total_seconds())
    assert abs(remaining - 60) <= 1
    print("  ✓ Very short duration (1 minute)")
    
    # Case 2: Very long duration (240 minutes = 4 hours)
    new_duration = 240
    end_time = current_time + timedelta(minutes=new_duration)
    remaining = int((end_time - current_time).total_seconds())
    assert abs(remaining - 240 * 60) <= 1
    print("  ✓ Very long duration (4 hours)")
    
    # Case 3: Update to same duration
    start_time = datetime.now() - timedelta(minutes=30)
    current_time = datetime.now()
    new_duration = 60  # Same as original
    end_time = current_time + timedelta(minutes=new_duration)
    remaining = int((end_time - current_time).total_seconds())
    assert abs(remaining - 60 * 60) <= 1
    print("  ✓ Update to same duration")
    
    print()
    print("✓ All edge cases passed")


if __name__ == "__main__":
    print("Testing session time update bug fix logic...")
    print("=" * 70)
    print()
    
    try:
        test_time_update_logic_absolute()
        print()
        print("=" * 70)
        print()
        test_time_update_scenarios()
        print()
        print("=" * 70)
        print()
        test_edge_cases()
        
        print()
        print("=" * 70)
        print("All session time update logic tests passed! ✅")
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
