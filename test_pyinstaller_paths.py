"""
Test PyInstaller path handling for database and data directories
"""
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(__file__))

from src.shared.utils import get_application_path, get_data_directory
from src.shared.database import Database


def test_get_application_path_normal_execution():
    """Test get_application_path during normal Python execution"""
    # In normal execution, sys.frozen is not set
    app_path = get_application_path()
    
    # Should return the project root directory
    assert os.path.exists(app_path), f"Application path should exist: {app_path}"
    assert os.path.isabs(app_path), f"Application path should be absolute: {app_path}"
    
    print(f"✅ get_application_path() returned: {app_path}")
    print(f"   sys.frozen = {getattr(sys, 'frozen', False)}")


def test_get_data_directory_creates_directory():
    """Test that get_data_directory creates the data directory"""
    # Temporarily override get_application_path to use temp directory
    import src.shared.utils as utils_module
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_func = utils_module.get_application_path
        
        # Mock get_application_path to return temp directory
        def mock_get_application_path():
            return tmpdir
        
        utils_module.get_application_path = mock_get_application_path
        
        try:
            data_dir = get_data_directory()
            
            # Check that data directory was created
            assert os.path.exists(data_dir), "Data directory should be created"
            assert os.path.isdir(data_dir), "Data directory should be a directory"
            assert data_dir == os.path.join(tmpdir, 'data'), f"Data directory path should be correct: {data_dir}"
            
            print(f"✅ get_data_directory() created directory: {data_dir}")
            
        finally:
            # Restore original function
            utils_module.get_application_path = original_func


def test_database_relative_path_conversion():
    """Test that Database converts relative paths to absolute paths"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test database with relative path
        import src.shared.utils as utils_module
        original_func = utils_module.get_application_path
        
        # Mock get_application_path to return temp directory
        def mock_get_application_path():
            return tmpdir
        
        utils_module.get_application_path = mock_get_application_path
        
        try:
            # Initialize database with relative path
            db = Database(db_path="data/test.db")
            
            # Check that database file was created in the correct location
            expected_db_path = os.path.join(tmpdir, 'data', 'test.db')
            assert os.path.exists(expected_db_path), f"Database file should be created at: {expected_db_path}"
            
            print(f"✅ Database created at absolute path: {expected_db_path}")
            
            # Test that we can use the database
            session = db.get_session()
            assert session is not None, "Should be able to get a database session"
            session.close()
            
            db.close()
            
        finally:
            utils_module.get_application_path = original_func


def test_database_absolute_path_handling():
    """Test that Database handles absolute paths correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create absolute path
        abs_db_path = os.path.join(tmpdir, 'custom', 'location', 'test.db')
        
        # Initialize database with absolute path
        db = Database(db_path=abs_db_path)
        
        # Check that database file was created at the absolute path
        assert os.path.exists(abs_db_path), f"Database file should be created at: {abs_db_path}"
        assert os.path.isabs(abs_db_path), "Path should be absolute"
        
        print(f"✅ Database created at custom absolute path: {abs_db_path}")
        
        # Test that we can use the database
        session = db.get_session()
        assert session is not None, "Should be able to get a database session"
        session.close()
        
        db.close()


def test_pyinstaller_frozen_simulation():
    """Test behavior when simulating PyInstaller frozen executable"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate PyInstaller frozen state
        original_frozen = getattr(sys, 'frozen', None)
        original_executable = sys.executable
        
        # Set frozen mode
        sys.frozen = True
        sys.executable = os.path.join(tmpdir, 'LibLockerServer.exe')
        
        try:
            app_path = get_application_path()
            
            # Should return the directory of the executable
            assert app_path == tmpdir, f"Application path should be exe directory: {app_path}"
            assert os.path.isabs(app_path), "Application path should be absolute"
            
            print(f"✅ Simulated PyInstaller frozen mode:")
            print(f"   sys.frozen = {sys.frozen}")
            print(f"   sys.executable = {sys.executable}")
            print(f"   get_application_path() = {app_path}")
            
            # Test data directory creation in frozen mode
            data_dir = get_data_directory()
            expected_data_dir = os.path.join(tmpdir, 'data')
            
            assert data_dir == expected_data_dir, f"Data dir should be: {expected_data_dir}"
            assert os.path.exists(data_dir), "Data directory should be created"
            
            print(f"   get_data_directory() = {data_dir}")
            
        finally:
            # Restore original state
            if original_frozen is None:
                delattr(sys, 'frozen')
            else:
                sys.frozen = original_frozen
            sys.executable = original_executable


def test_database_initialization_in_clean_environment():
    """Test full database initialization in a clean environment (simulates first run)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.shared.utils as utils_module
        original_func = utils_module.get_application_path
        
        # Mock get_application_path to return temp directory
        def mock_get_application_path():
            return tmpdir
        
        utils_module.get_application_path = mock_get_application_path
        
        try:
            # Verify no data directory exists initially
            data_dir = os.path.join(tmpdir, 'data')
            assert not os.path.exists(data_dir), "Data directory should not exist initially"
            
            # Initialize database (should create directory and database)
            db = Database(db_path="data/liblocker.db")
            
            # Verify data directory and database file were created
            assert os.path.exists(data_dir), "Data directory should be created"
            db_file = os.path.join(data_dir, 'liblocker.db')
            assert os.path.exists(db_file), f"Database file should be created: {db_file}"
            
            print(f"✅ Clean environment test passed:")
            print(f"   Data directory created: {data_dir}")
            print(f"   Database file created: {db_file}")
            
            # Verify database is functional
            from src.shared.database import ClientModel
            session = db.get_session()
            try:
                # Try to query (should not fail even with empty database)
                clients = session.query(ClientModel).all()
                assert isinstance(clients, list), "Should be able to query database"
                print(f"   Database is functional (found {len(clients)} clients)")
            finally:
                session.close()
                db.close()
            
        finally:
            utils_module.get_application_path = original_func


if __name__ == "__main__":
    print("Testing PyInstaller path handling...")
    print("=" * 70)
    print()
    
    tests = [
        ("Application path (normal execution)", test_get_application_path_normal_execution),
        ("Data directory creation", test_get_data_directory_creates_directory),
        ("Database relative path conversion", test_database_relative_path_conversion),
        ("Database absolute path handling", test_database_absolute_path_handling),
        ("PyInstaller frozen mode simulation", test_pyinstaller_frozen_simulation),
        ("Clean environment initialization", test_database_initialization_in_clean_environment),
    ]
    
    failed = []
    
    for test_name, test_func in tests:
        try:
            print(f"Running: {test_name}")
            test_func()
            print()
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            print()
            failed.append((test_name, e))
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            print()
            failed.append((test_name, e))
    
    print("=" * 70)
    if not failed:
        print("✅ All tests passed!")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"❌ {len(failed)} test(s) failed:")
        for test_name, error in failed:
            print(f"   - {test_name}: {error}")
        print("=" * 70)
        sys.exit(1)
