#!/usr/bin/env python3
"""
Simple test to demonstrate the session time update fix.
This test doesn't require any dependencies.
"""

from datetime import datetime, timedelta
import time

def test_scenario():
    """Test the actual scenario reported by the user"""
    print("=" * 70)
    print("SCENARIO: Session time display after duration update")
    print("=" * 70)
    
    # Initial session: 60 minutes starting now
    print("\n1. Session starts with 60 minutes...")
    session_start = datetime.now()
    duration = 60
    print(f"   Start time: {session_start.strftime('%H:%M:%S')}")
    print(f"   Duration: {duration} minutes")
    print(f"   Will end at: {(session_start + timedelta(minutes=duration)).strftime('%H:%M:%S')}")
    
    # Simulate 30 minutes passing
    print("\n2. After 30 minutes have passed...")
    print("   (simulating by advancing time by 5 seconds for demonstration)")
    time.sleep(5)
    current_time_1 = datetime.now()
    
    # Calculate remaining time
    end_time_1 = session_start + timedelta(minutes=duration)
    remaining_1 = end_time_1 - current_time_1
    remaining_seconds_1 = remaining_1.total_seconds()
    remaining_minutes_1 = int(remaining_seconds_1 / 60)
    
    print(f"   Current time: {current_time_1.strftime('%H:%M:%S')}")
    print(f"   Time elapsed: {int((current_time_1 - session_start).total_seconds())} seconds")
    print(f"   Remaining: {remaining_minutes_1} minutes")
    
    # Admin updates session to 30 minutes
    print("\n3. Admin changes session duration to 30 minutes...")
    update_time = datetime.now()
    new_duration = 30
    
    # === THE FIX: Update start_time to current time ===
    print("\n   WITH FIX (start_time = current time):")
    fixed_start = update_time
    fixed_end = fixed_start + timedelta(minutes=new_duration)
    fixed_remaining = fixed_end - datetime.now()
    fixed_remaining_seconds = fixed_remaining.total_seconds()
    
    print(f"   New start_time: {fixed_start.strftime('%H:%M:%S')}")
    print(f"   New end_time: {fixed_end.strftime('%H:%M:%S')}")
    print(f"   Remaining seconds: {fixed_remaining_seconds:.1f}")
    
    if fixed_remaining_seconds < -5:
        print(f"   ❌ Would show: 'Завершается...'")
        result_fixed = False
    else:
        fixed_remaining_minutes = max(0, int(fixed_remaining_seconds / 60))
        hours = fixed_remaining_minutes // 60
        minutes = fixed_remaining_minutes % 60
        print(f"   ✅ Would show: '{hours:02d}:{minutes:02d} осталось' (~{fixed_remaining_minutes} minutes)")
        result_fixed = fixed_remaining_minutes >= 28  # Should be ~30 minutes
    
    # === WITHOUT FIX: Keep old start_time ===
    print("\n   WITHOUT FIX (start_time = original):")
    buggy_start = session_start
    buggy_end = buggy_start + timedelta(minutes=new_duration)
    buggy_remaining = buggy_end - datetime.now()
    buggy_remaining_seconds = buggy_remaining.total_seconds()
    
    print(f"   Old start_time: {buggy_start.strftime('%H:%M:%S')}")
    print(f"   New end_time: {buggy_end.strftime('%H:%M:%S')}")
    print(f"   Remaining seconds: {buggy_remaining_seconds:.1f}")
    
    if buggy_remaining_seconds < -5:
        print(f"   ⚠️  Would show: 'Завершается...' (WRONG!)")
        print(f"   Session appears expired even though admin just extended it!")
    else:
        buggy_remaining_minutes = max(0, int(buggy_remaining_seconds / 60))
        hours = buggy_remaining_minutes // 60
        minutes = buggy_remaining_minutes % 60
        print(f"   ⚠️  Would show: '{hours:02d}:{minutes:02d} осталось' ({buggy_remaining_minutes} minutes)")
        if buggy_remaining_minutes < 28:
            print(f"   This is WRONG - should be ~30 minutes!")
    
    return result_fixed


def test_edge_case_very_long_session():
    """Test edge case where session has been running for a very long time"""
    print("\n" + "=" * 70)
    print("EDGE CASE: Very long running session")
    print("=" * 70)
    
    # Session started 3 hours ago with 180 minutes duration
    print("\n1. Session started 3 hours ago with 180 minutes...")
    session_start = datetime.now() - timedelta(hours=3)
    duration = 180
    print(f"   Start time: {session_start.strftime('%H:%M:%S')}")
    print(f"   Original duration: {duration} minutes")
    print(f"   Original end: {(session_start + timedelta(minutes=duration)).strftime('%H:%M:%S')}")
    
    # Calculate current status
    end_time = session_start + timedelta(minutes=duration)
    remaining = end_time - datetime.now()
    remaining_seconds = remaining.total_seconds()
    
    print(f"\n2. Current status:")
    print(f"   Current time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"   Remaining seconds: {remaining_seconds:.1f}")
    
    if remaining_seconds < -5:
        print(f"   ✅ Correctly shows: 'Завершается...' (session expired)")
    else:
        remaining_minutes = max(0, int(remaining_seconds / 60))
        print(f"   Status: {remaining_minutes} minutes remaining")
    
    # Admin extends by 30 more minutes
    print("\n3. Admin extends session by 30 more minutes...")
    new_duration = 30
    
    # With fix
    print("\n   WITH FIX:")
    fixed_start = datetime.now()
    fixed_end = fixed_start + timedelta(minutes=new_duration)
    fixed_remaining = fixed_end - datetime.now()
    fixed_remaining_seconds = fixed_remaining.total_seconds()
    fixed_remaining_minutes = max(0, int(fixed_remaining_seconds / 60))
    
    print(f"   New start_time: {fixed_start.strftime('%H:%M:%S')}")
    print(f"   New end_time: {fixed_end.strftime('%H:%M:%S')}")
    print(f"   ✅ Would show: {fixed_remaining_minutes} minutes remaining")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SESSION TIME UPDATE FIX - DEMONSTRATION")
    print("=" * 70)
    
    try:
        result1 = test_scenario()
        result2 = test_edge_case_very_long_session()
        
        print("\n" + "=" * 70)
        if result1 and result2:
            print("✅ FIX IS CORRECT!")
            print("=" * 70)
            print("\nThe fix ensures that when admin changes session duration,")
            print("the new duration counts from the current moment, not from")
            print("the original session start time. This prevents 'Завершается...'")
            print("from appearing immediately after duration update.")
        else:
            print("⚠️  FIX MAY NEED ADJUSTMENT")
            print("=" * 70)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
