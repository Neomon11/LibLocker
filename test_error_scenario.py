"""
Integration test to simulate the exact error scenario from the issue
"""
import sqlite3
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from src.shared.database import Database, SessionModel, ClientModel


def test_exact_error_scenario():
    """
    Simulate the exact error from the issue:
    ERROR - Error starting session: (sqlite3.OperationalError) table sessions has no column named cost_per_hour
    [SQL: INSERT INTO sessions (client_id, start_time, end_time, duration_minutes, actual_duration, is_unlimited, cost, cost_per_hour, free_mode, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)]
    [parameters: (1, '2026-01-16 11:39:08.918814', None, 30, None, 0, 0.0, 30.0, 0, 'active')]
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'liblocker.db')
        
        print("Step 1: Creating database with old schema (simulating user's existing database)...")
        
        # Create old schema database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hwid VARCHAR(64) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                ip_address VARCHAR(45),
                mac_address VARCHAR(17),
                status VARCHAR(20) DEFAULT 'offline',
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Old sessions table WITHOUT cost_per_hour and free_mode
        cursor.execute('''
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                duration_minutes INTEGER DEFAULT 0,
                actual_duration INTEGER,
                is_unlimited BOOLEAN DEFAULT 0,
                cost FLOAT DEFAULT 0.0,
                status VARCHAR(20) DEFAULT 'active',
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        ''')
        
        # Insert a test client (client_id=1 as in the error)
        cursor.execute('''
            INSERT INTO clients (hwid, name, ip_address) 
            VALUES ('test-hwid-123', 'TestClient', '127.0.0.1')
        ''')
        
        conn.commit()
        
        # Verify old schema
        cursor.execute('PRAGMA table_info(sessions)')
        old_columns = [row[1] for row in cursor.fetchall()]
        print(f"  Old schema columns: {old_columns}")
        assert 'cost_per_hour' not in old_columns
        assert 'free_mode' not in old_columns
        conn.close()
        
        print("  ✅ Old database created successfully")
        
        print("\nStep 2: Initializing Database class (should trigger migration)...")
        
        # Initialize Database - this should migrate the schema
        db = Database(db_path=db_path)
        
        # Verify migration added columns
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(sessions)')
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"  New schema columns: {new_columns}")
        assert 'cost_per_hour' in new_columns
        assert 'free_mode' in new_columns
        conn.close()
        
        print("  ✅ Migration completed successfully")
        
        print("\nStep 3: Creating session with exact parameters from the error...")
        
        from datetime import datetime
        
        # Try to create session with exact parameters from the error
        session = db.get_session()
        try:
            new_session = SessionModel(
                client_id=1,
                start_time=datetime.fromisoformat('2026-01-16 11:39:08.918814'),
                end_time=None,
                duration_minutes=30,
                actual_duration=None,
                is_unlimited=False,
                cost=0.0,
                cost_per_hour=30.0,
                free_mode=False,
                status='active'
            )
            session.add(new_session)
            session.commit()
            
            print(f"  ✅ Session created successfully!")
            print(f"     Session ID: {new_session.id}")
            print(f"     Client ID: {new_session.client_id}")
            print(f"     Duration: {new_session.duration_minutes} minutes")
            print(f"     Cost per hour: {new_session.cost_per_hour}")
            print(f"     Free mode: {new_session.free_mode}")
            print(f"     Status: {new_session.status}")
            
            # Verify it was saved correctly
            saved_session = session.query(SessionModel).filter_by(id=new_session.id).first()
            assert saved_session is not None
            assert saved_session.client_id == 1
            assert saved_session.duration_minutes == 30
            assert saved_session.cost_per_hour == 30.0
            assert saved_session.free_mode is False
            assert saved_session.status == 'active'
            
            print("\n  ✅ Session verified in database")
            
        except Exception as e:
            print(f"\n  ❌ Error creating session: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            session.close()
            db.close()
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS: The exact error scenario is now fixed!")
        print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("Testing the exact error scenario from the issue")
    print("=" * 60)
    print()
    
    try:
        test_exact_error_scenario()
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        sys.exit(1)
