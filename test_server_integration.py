"""
Integration test for server startup with PyInstaller path handling
Simulates the full server initialization flow
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))


def test_server_initialization_flow():
    """Test the complete server initialization flow"""
    print("Testing server initialization flow...")
    
    # Simulate a clean environment
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.shared.utils as utils_module
        original_func = utils_module.get_application_path
        
        # Mock get_application_path to return temp directory
        def mock_get_application_path():
            return tmpdir
        
        utils_module.get_application_path = mock_get_application_path
        
        try:
            print(f"✅ Test environment created at: {tmpdir}")
            
            # Step 1: Import and initialize config (as done in run_server.py)
            from src.shared.config import ServerConfig
            config = ServerConfig()
            
            print(f"✅ ServerConfig initialized")
            print(f"   Database path: {config.database_path}")
            
            # Verify the path is absolute
            assert os.path.isabs(config.database_path), "Database path should be absolute"
            
            # Step 2: Initialize database (as done in server/gui.py)
            from src.shared.database import Database
            db = Database()
            
            print(f"✅ Database initialized successfully")
            
            # Verify database file was created
            db_path = os.path.join(tmpdir, 'data', 'liblocker.db')
            assert os.path.exists(db_path), f"Database file should exist at: {db_path}"
            
            print(f"   Database file created at: {db_path}")
            
            # Step 3: Test database operations
            from src.shared.database import ClientModel
            session = db.get_session()
            
            try:
                # Create a test client
                test_client = ClientModel(
                    hwid='test-hwid-12345',
                    name='Test Client',
                    ip_address='192.168.1.100',
                    status='online'
                )
                session.add(test_client)
                session.commit()
                
                print(f"✅ Test client created with ID: {test_client.id}")
                
                # Query the client
                clients = session.query(ClientModel).all()
                assert len(clients) == 1, "Should have one client"
                assert clients[0].hwid == 'test-hwid-12345', "Client HWID should match"
                
                print(f"✅ Database operations working correctly")
                print(f"   Retrieved {len(clients)} client(s) from database")
                
            finally:
                session.close()
                db.close()
            
            print(f"\n✅ Server initialization flow completed successfully!")
            return True
            
        finally:
            utils_module.get_application_path = original_func


def test_pyinstaller_frozen_server_flow():
    """Test server initialization in PyInstaller frozen mode"""
    print("\nTesting PyInstaller frozen mode server initialization...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate PyInstaller frozen state
        original_frozen = getattr(sys, 'frozen', None)
        original_executable = sys.executable
        
        # Set frozen mode (simulating LibLockerServer.exe in tmpdir)
        sys.frozen = True
        sys.executable = os.path.join(tmpdir, 'LibLockerServer.exe')
        
        try:
            print(f"✅ Simulating PyInstaller environment:")
            print(f"   sys.frozen = {sys.frozen}")
            print(f"   sys.executable = {sys.executable}")
            
            # Import utilities
            from src.shared.utils import get_application_path, get_data_directory
            
            app_path = get_application_path()
            print(f"   Application path: {app_path}")
            assert app_path == tmpdir, "Application path should be exe directory"
            
            data_dir = get_data_directory()
            print(f"   Data directory: {data_dir}")
            assert data_dir == os.path.join(tmpdir, 'data'), "Data dir should be in exe directory"
            assert os.path.exists(data_dir), "Data directory should be created"
            
            # Initialize database
            from src.shared.database import Database
            db = Database()
            
            # Verify database was created in the correct location
            expected_db_path = os.path.join(tmpdir, 'data', 'liblocker.db')
            assert os.path.exists(expected_db_path), f"Database should be at: {expected_db_path}"
            
            print(f"✅ Database created at: {expected_db_path}")
            
            # Test database is functional
            from src.shared.database import ClientModel
            session = db.get_session()
            try:
                clients = session.query(ClientModel).all()
                print(f"✅ Database is functional in frozen mode (found {len(clients)} clients)")
            finally:
                session.close()
                db.close()
            
            print(f"\n✅ PyInstaller frozen mode test completed successfully!")
            return True
            
        finally:
            # Restore original state
            if original_frozen is None:
                delattr(sys, 'frozen')
            else:
                sys.frozen = original_frozen
            sys.executable = original_executable


if __name__ == "__main__":
    print("=" * 70)
    print("Server Initialization Integration Tests")
    print("=" * 70)
    print()
    
    try:
        # Test 1: Normal server flow
        test_server_initialization_flow()
        
        # Test 2: PyInstaller frozen mode
        test_pyinstaller_frozen_server_flow()
        
        print()
        print("=" * 70)
        print("✅ All integration tests passed!")
        print("=" * 70)
        print()
        print("This fix ensures that:")
        print("  1. Database files are created in the correct location")
        print("  2. Works in both normal Python and PyInstaller environments")
        print("  3. Automatically creates necessary directories")
        print("  4. Handles both absolute and relative paths correctly")
        print()
        sys.exit(0)
        
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"❌ Test failed: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70)
        sys.exit(1)
