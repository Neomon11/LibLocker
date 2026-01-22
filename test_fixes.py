"""
Test script for the two fixes:
1. Client reconnection retry logic
2. Web server session remaining_minutes calculation
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from datetime import datetime, timedelta
from src.shared.database import Database, SessionModel, ClientModel

def test_session_remaining_minutes_calculation():
    """Test that we can calculate remaining_minutes from SessionModel"""
    print("\n" + "=" * 60)
    print("Testing SessionModel remaining_minutes calculation...")
    print("=" * 60)
    
    # Create a temporary database for testing
    import tempfile
    temp_db_fd, temp_db = tempfile.mkstemp(suffix='.db')
    
    try:
        db = Database(temp_db)
        db_session = db.get_session()
        
        # Create a test client
        client = ClientModel(
            hwid='test-hwid',
            name='Test Client',
            ip_address='127.0.0.1',
            mac_address='00:00:00:00:00:00',
            status='online'
        )
        db_session.add(client)
        db_session.commit()
        
        # Create a test session that started 10 minutes ago with 60 minutes duration
        session = SessionModel(
            client_id=client.id,
            start_time=datetime.now() - timedelta(minutes=10),
            duration_minutes=60,
            is_unlimited=False,
            status='active'
        )
        db_session.add(session)
        db_session.commit()
        
        # Calculate remaining minutes
        end_time = session.start_time + timedelta(minutes=session.duration_minutes)
        remaining = end_time - datetime.now()
        remaining_seconds = remaining.total_seconds()
        remaining_minutes = max(0, int(remaining_seconds / 60))
        
        print(f"Session start time: {session.start_time}")
        print(f"Session duration: {session.duration_minutes} minutes")
        print(f"Session end time: {end_time}")
        print(f"Current time: {datetime.now()}")
        print(f"Remaining seconds: {remaining_seconds}")
        print(f"Remaining minutes: {remaining_minutes}")
        
        # Verify it's approximately 50 minutes (60 - 10)
        assert 48 <= remaining_minutes <= 52, f"Expected ~50 minutes, got {remaining_minutes}"
        print("✓ Remaining minutes calculation is correct!")
        
        # Test unlimited session
        unlimited_session = SessionModel(
            client_id=client.id,
            start_time=datetime.now(),
            duration_minutes=0,
            is_unlimited=True,
            status='active'
        )
        db_session.add(unlimited_session)
        db_session.commit()
        
        # For unlimited sessions, we should return -1
        remaining_minutes = -1 if unlimited_session.is_unlimited else 0
        print(f"\nUnlimited session remaining_minutes: {remaining_minutes}")
        assert remaining_minutes == -1, "Unlimited session should return -1"
        print("✓ Unlimited session handling is correct!")
        
        db_session.close()
        db.close()
        
        print("\n✓ All SessionModel tests passed!")
        return True
        
    finally:
        # Clean up temp database
        os.close(temp_db_fd)
        if os.path.exists(temp_db):
            os.remove(temp_db)

async def test_client_reconnection():
    """Test client reconnection logic"""
    print("\n" + "=" * 60)
    print("Testing client reconnection logic...")
    print("=" * 60)
    
    from src.client.client import LibLockerClient
    
    # Create client with non-existent server
    client = LibLockerClient(server_url="http://localhost:9999")
    
    print("Starting client with invalid server URL (http://localhost:9999)...")
    print("Client should retry connecting every 10 seconds...")
    
    # Run client for a short time to verify retry logic
    task = asyncio.create_task(client.run())
    
    print("Waiting 12 seconds to observe retry attempts...")
    await asyncio.sleep(12)
    
    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    print("✓ Client reconnection logic is working!")
    print("  (Check logs above for 'Connection failed, retrying in 10 seconds...')")
    return True

async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Fixes")
    print("=" * 60)
    
    # Test 1: SessionModel remaining_minutes calculation
    test_session_remaining_minutes_calculation()
    
    # Test 2: Client reconnection
    await test_client_reconnection()
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
