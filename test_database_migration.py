"""
Test database migration for missing columns in sessions table
"""
import sqlite3
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from src.shared.database import Database, SessionModel


def test_migration_adds_missing_columns():
    """Test that migration adds missing columns to existing database"""
    # Create a temporary database with old schema
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        
        # Create database with old schema (without cost_per_hour and free_mode)
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
        
        cursor.execute('''
            INSERT INTO clients (hwid, name, ip_address) 
            VALUES ('test-hwid-123', 'TestClient', '127.0.0.1')
        ''')
        
        conn.commit()
        
        # Verify columns are missing
        cursor.execute('PRAGMA table_info(sessions)')
        columns_before = {row[1] for row in cursor.fetchall()}
        assert 'cost_per_hour' not in columns_before, "cost_per_hour should not exist yet"
        assert 'free_mode' not in columns_before, "free_mode should not exist yet"
        conn.close()
        
        print("✅ Created test database without cost_per_hour and free_mode columns")
        
        # Initialize Database (should trigger migration)
        db = Database(db_path=db_path)
        
        # Verify columns were added
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(sessions)')
        columns_after = {row[1] for row in cursor.fetchall()}
        conn.close()
        
        assert 'cost_per_hour' in columns_after, "cost_per_hour should be added by migration"
        assert 'free_mode' in columns_after, "free_mode should be added by migration"
        
        print("✅ Migration successfully added missing columns")
        
        # Test creating a session with new columns
        session = db.get_session()
        try:
            new_session = SessionModel(
                client_id=1,
                duration_minutes=30,
                is_unlimited=False,
                cost=0.0,
                cost_per_hour=30.0,
                free_mode=False,
                status='active'
            )
            session.add(new_session)
            session.commit()
            
            assert new_session.id is not None, "Session should be created with id"
            assert new_session.cost_per_hour == 30.0, "cost_per_hour should be saved"
            assert new_session.free_mode == False, "free_mode should be saved"
            
            print(f"✅ Successfully created session with id={new_session.id}")
            print(f"   cost_per_hour={new_session.cost_per_hour}, free_mode={new_session.free_mode}")
            
        finally:
            session.close()
            db.close()


def test_migration_handles_existing_columns():
    """Test that migration doesn't fail when columns already exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test2.db')
        
        # Create database with new schema (columns already exist)
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
                cost_per_hour FLOAT DEFAULT 0.0,
                free_mode BOOLEAN DEFAULT 1,
                status VARCHAR(20) DEFAULT 'active',
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        ''')
        
        cursor.execute('''
            INSERT INTO clients (hwid, name, ip_address) 
            VALUES ('test-hwid-456', 'TestClient2', '127.0.0.2')
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Created test database with all columns")
        
        # Initialize Database (migration should skip existing columns)
        db = Database(db_path=db_path)
        
        # Test creating a session
        session = db.get_session()
        try:
            new_session = SessionModel(
                client_id=1,
                duration_minutes=60,
                is_unlimited=True,
                cost=0.0,
                cost_per_hour=50.0,
                free_mode=True,
                status='active'
            )
            session.add(new_session)
            session.commit()
            
            assert new_session.id is not None, "Session should be created"
            print(f"✅ Successfully created session with existing columns: id={new_session.id}")
            
        finally:
            session.close()
            db.close()


if __name__ == "__main__":
    print("Testing database migration for sessions table...")
    print()
    
    try:
        test_migration_adds_missing_columns()
        print()
        test_migration_handles_existing_columns()
        print()
        print("=" * 50)
        print("✅ All migration tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print()
        print("=" * 50)
        print(f"❌ Test failed: {e}")
        print("=" * 50)
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 50)
        sys.exit(1)
