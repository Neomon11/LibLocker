#!/usr/bin/env python3
"""
Debug script to check session time calculations and database storage.
This script checks for potential issues with datetime storage and retrieval.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shared.database import Database, SessionModel, ClientModel
from datetime import datetime, timedelta
import time

def check_datetime_storage():
    """Check how datetime is stored and retrieved from database"""
    print("=" * 70)
    print("CHECKING DATETIME STORAGE IN SQLite")
    print("=" * 70)
    
    # Create a test database
    db = Database(":memory:")
    session = db.get_session()
    
    try:
        # Create a test client
        client = ClientModel(
            hwid="TEST001",
            name="Test Client",
            status="online"
        )
        session.add(client)
        session.commit()
        
        # Create a test session with known start time
        print("\n1. Creating session...")
        now = datetime.now()
        print(f"   Current time: {now}")
        print(f"   Type: {type(now)}")
        
        test_session = SessionModel(
            client_id=client.id,
            start_time=now,
            duration_minutes=60,
            is_unlimited=False,
            status='active'
        )
        session.add(test_session)
        session.commit()
        session_id = test_session.id
        
        # Retrieve it immediately
        print("\n2. Retrieving session immediately...")
        retrieved = session.query(SessionModel).filter_by(id=session_id).first()
        print(f"   Retrieved start_time: {retrieved.start_time}")
        print(f"   Type: {type(retrieved.start_time)}")
        print(f"   Match: {retrieved.start_time == now}")
        
        # Calculate end time
        print("\n3. Calculating end time...")
        end_time = retrieved.start_time + timedelta(minutes=retrieved.duration_minutes)
        print(f"   End time: {end_time}")
        
        # Wait a bit and check remaining time
        print("\n4. Checking remaining time...")
        time.sleep(2)
        current = datetime.now()
        remaining = end_time - current
        remaining_seconds = remaining.total_seconds()
        print(f"   Current time: {current}")
        print(f"   Remaining seconds: {remaining_seconds}")
        print(f"   Remaining minutes: {int(remaining_seconds / 60)}")
        
        # Check if it would show "Завершается..."
        if remaining_seconds < -5:
            print(f"   ⚠️  Would show 'Завершается...'")
        else:
            remaining_minutes = max(0, int(remaining_seconds / 60))
            hours = remaining_minutes // 60
            minutes = remaining_minutes % 60
            time_text = f"{hours:02d}:{minutes:02d} осталось"
            print(f"   ✓ Would show: {time_text}")
        
        # Simulate what happens after server restart
        print("\n5. Simulating server restart...")
        session.close()
        
        # Reconnect
        session2 = db.get_session()
        retrieved2 = session2.query(SessionModel).filter_by(id=session_id).first()
        print(f"   Retrieved start_time after 'restart': {retrieved2.start_time}")
        print(f"   Original start_time: {now}")
        print(f"   Match: {retrieved2.start_time.replace(microsecond=0) == now.replace(microsecond=0)}")
        
        # Check timezone info
        print("\n6. Checking timezone information...")
        print(f"   Original tzinfo: {now.tzinfo}")
        print(f"   Retrieved tzinfo: {retrieved2.start_time.tzinfo}")
        print(f"   Both are naive: {now.tzinfo is None and retrieved2.start_time.tzinfo is None}")
        
        session2.close()
        
    finally:
        db.close()
    
    print("\n" + "=" * 70)
    print("✓ Datetime storage check completed")
    print("=" * 70)


def check_real_database():
    """Check the actual database if it exists"""
    print("\n" + "=" * 70)
    print("CHECKING REAL DATABASE (if exists)")
    print("=" * 70)
    
    db_path = "data/liblocker.db"
    if not os.path.exists(db_path):
        print(f"\n⚠️  Database not found at: {db_path}")
        print("   This is normal if server hasn't been run yet.")
        return
    
    db = Database(db_path)
    session = db.get_session()
    
    try:
        # Get all active sessions
        active_sessions = session.query(SessionModel).filter_by(status='active').all()
        
        if not active_sessions:
            print("\n✓ No active sessions in database")
            return
        
        print(f"\n📊 Found {len(active_sessions)} active session(s):")
        
        for sess in active_sessions:
            print(f"\n   Session ID: {sess.id}")
            print(f"   Client ID: {sess.client_id}")
            print(f"   Start time: {sess.start_time}")
            print(f"   Duration: {sess.duration_minutes} minutes")
            print(f"   Is unlimited: {sess.is_unlimited}")
            
            if not sess.is_unlimited:
                # Calculate remaining time
                end_time = sess.start_time + timedelta(minutes=sess.duration_minutes)
                remaining = end_time - datetime.now()
                remaining_seconds = remaining.total_seconds()
                
                print(f"   End time (calculated): {end_time}")
                print(f"   Current time: {datetime.now()}")
                print(f"   Remaining seconds: {remaining_seconds:.1f}")
                
                if remaining_seconds < -5:
                    print(f"   ⚠️  Status: Would show 'Завершается...'")
                else:
                    remaining_minutes = max(0, int(remaining_seconds / 60))
                    hours = remaining_minutes // 60
                    minutes = remaining_minutes % 60
                    time_text = f"{hours:02d}:{minutes:02d} осталось"
                    print(f"   ✓ Status: {time_text}")
            else:
                elapsed = datetime.now() - sess.start_time
                elapsed_minutes = int(elapsed.total_seconds() / 60)
                hours = elapsed_minutes // 60
                minutes = elapsed_minutes % 60
                print(f"   ✓ Status: ∞ {hours:02d}:{minutes:02d}")
    
    finally:
        session.close()
        db.close()
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        check_datetime_storage()
        check_real_database()
        print("\n✅ All checks completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during checks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
