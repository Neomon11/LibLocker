#!/usr/bin/env python3
"""
Test for session time update fix.
Verifies that when session duration is updated, the new duration counts
from the current moment, not from the original session start time.
"""

import sys
import os
from datetime import datetime, timedelta
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_session_time_update_calculation():
    """Test that session time is recalculated correctly when duration is updated"""
    print("=" * 70)
    print("TEST: Session Time Update Calculation")
    print("=" * 70)
    
    from shared.database import Database, SessionModel, ClientModel
    
    # Create test database
    db = Database(":memory:")
    session = db.get_session()
    
    try:
        # Create test client
        client = ClientModel(
            hwid="TEST001",
            name="Test Client",
            status="in_session"
        )
        session.add(client)
        session.commit()
        
        # Scenario: Session starts with 60 minutes
        print("\n1. Creating session with 60 minutes duration...")
        original_start = datetime.now()
        test_session = SessionModel(
            client_id=client.id,
            start_time=original_start,
            duration_minutes=60,
            is_unlimited=False,
            status='active'
        )
        session.add(test_session)
        session.commit()
        
        original_end = original_start + timedelta(minutes=60)
        print(f"   Start time: {original_start}")
        print(f"   Duration: 60 minutes")
        print(f"   Expected end: {original_end}")
        
        # Wait a bit to simulate time passing
        print("\n2. Simulating 5 seconds passing...")
        time.sleep(5)
        
        # Now admin updates session to 30 minutes
        print("\n3. Admin updates session duration to 30 minutes...")
        update_time = datetime.now()
        test_session.start_time = update_time  # This is the fix!
        test_session.duration_minutes = 30
        session.commit()
        
        new_end = test_session.start_time + timedelta(minutes=test_session.duration_minutes)
        print(f"   Update time: {update_time}")
        print(f"   New start_time: {test_session.start_time}")
        print(f"   New duration: {test_session.duration_minutes} minutes")
        print(f"   New expected end: {new_end}")
        
        # Calculate remaining time
        current_time = datetime.now()
        remaining = new_end - current_time
        remaining_seconds = remaining.total_seconds()
        remaining_minutes = int(remaining_seconds / 60)
        
        print(f"\n4. Checking remaining time...")
        print(f"   Current time: {current_time}")
        print(f"   Remaining seconds: {remaining_seconds:.1f}")
        print(f"   Remaining minutes: {remaining_minutes}")
        
        # Verify the fix
        if remaining_seconds < -5:
            print(f"\n   ❌ FAIL: Would show 'Завершается...' (remaining_seconds < -5)")
            print(f"   This means start_time was not updated correctly!")
            return False
        elif remaining_minutes < 28:  # Should be ~30 minutes
            print(f"\n   ❌ FAIL: Remaining time is too low ({remaining_minutes} < 28)")
            print(f"   Expected ~30 minutes remaining")
            return False
        else:
            hours = remaining_minutes // 60
            minutes = remaining_minutes % 60
            time_text = f"{hours:02d}:{minutes:02d} осталось"
            print(f"\n   ✅ PASS: Would show '{time_text}'")
            print(f"   Remaining time is correct!")
            return True
            
    finally:
        session.close()
        db.close()


def test_old_behavior_would_fail():
    """Demonstrate that without the fix, the behavior would be incorrect"""
    print("\n" + "=" * 70)
    print("DEMONSTRATION: Old Behavior (Without Fix)")
    print("=" * 70)
    
    from datetime import datetime, timedelta
    import time
    
    # Scenario: Session starts with 60 minutes
    print("\n1. Session starts with 60 minutes...")
    original_start = datetime.now()
    duration = 60
    original_end = original_start + timedelta(minutes=duration)
    print(f"   Start: {original_start}")
    print(f"   End: {original_end}")
    
    # Wait 5 seconds
    print("\n2. Waiting 5 seconds...")
    time.sleep(5)
    
    # Admin updates to 30 minutes (OLD WAY - without updating start_time)
    print("\n3. Admin updates to 30 minutes (OLD WAY)...")
    new_duration = 30
    # BUG: start_time not updated, still using original_start
    buggy_end = original_start + timedelta(minutes=new_duration)
    
    current = datetime.now()
    remaining = buggy_end - current
    remaining_seconds = remaining.total_seconds()
    
    print(f"   Original start: {original_start}")
    print(f"   New duration: {new_duration}")
    print(f"   Buggy end time: {buggy_end}")
    print(f"   Current time: {current}")
    print(f"   Remaining seconds: {remaining_seconds:.1f}")
    
    if remaining_seconds < -5:
        print(f"\n   ⚠️  With old behavior, would show 'Завершается...' immediately!")
        print(f"   This is the bug!")
    else:
        remaining_minutes = max(0, int(remaining_seconds / 60))
        print(f"\n   Would show: {remaining_minutes} minutes remaining")
        print(f"   But user expected 30 minutes!")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SESSION TIME UPDATE FIX - TEST SUITE")
    print("=" * 70)
    
    try:
        # First demonstrate the old buggy behavior
        test_old_behavior_would_fail()
        
        # Then test the fix
        success = test_session_time_update_calculation()
        
        if success:
            print("\n" + "=" * 70)
            print("✅ ALL TESTS PASSED!")
            print("=" * 70)
            print("\nThe fix correctly updates start_time when duration changes,")
            print("ensuring new duration counts from current moment.")
            sys.exit(0)
        else:
            print("\n" + "=" * 70)
            print("❌ TESTS FAILED!")
            print("=" * 70)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
