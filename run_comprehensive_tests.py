#!/usr/bin/env python3
"""
Comprehensive testing script for LibLocker application
Runs unit tests, integration tests, and bug checks
"""
import sys
import os
import subprocess
import tempfile
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_result(test_name, passed):
    """Print test result"""
    symbol = "✓" if passed else "✗"
    status = "PASSED" if passed else "FAILED"
    print(f"{symbol} {test_name}: {status}")

def test_imports():
    """Test that all critical modules can be imported"""
    print_header("Testing Module Imports")
    tests = []
    
    try:
        from shared.database import Database, ClientModel, SessionModel
        tests.append(("Database module", True))
    except Exception as e:
        tests.append(("Database module", False))
        print(f"  Error: {e}")
    
    try:
        from shared.protocol import Message, MessageType, ClientRegisterMessage
        tests.append(("Protocol module", True))
    except Exception as e:
        tests.append(("Protocol module", False))
        print(f"  Error: {e}")
    
    try:
        from shared.models import Client, ClientStatus
        tests.append(("Models module", True))
    except Exception as e:
        tests.append(("Models module", False))
        print(f"  Error: {e}")
    
    try:
        from shared.utils import get_hwid, get_local_ip, hash_password
        tests.append(("Utils module", True))
    except Exception as e:
        tests.append(("Utils module", False))
        print(f"  Error: {e}")
    
    try:
        from server.server import LibLockerServer
        tests.append(("Server module", True))
    except Exception as e:
        tests.append(("Server module", False))
        print(f"  Error: {e}")
    
    try:
        from client.client import LibLockerClient
        tests.append(("Client module", True))
    except Exception as e:
        tests.append(("Client module", False))
        print(f"  Error: {e}")
    
    for test_name, passed in tests:
        print_result(test_name, passed)
    
    return all(passed for _, passed in tests)

def test_database():
    """Test database operations"""
    print_header("Testing Database Operations")
    tests = []
    db_path = None
    
    try:
        from shared.database import Database, ClientModel, SessionModel
        from datetime import datetime
        import time
        
        # Create test database with better unique filename
        db_path = os.path.join(tempfile.gettempdir(), f'test_liblocker_{int(time.time())}_{os.getpid()}.db')
        db = Database(db_path)
        tests.append(("Create database", True))
        
        # Test session
        db_session = db.get_session()
        tests.append(("Get DB session", True))
        
        try:
            # Add client
            client = ClientModel(
                hwid='TEST-HWID-789',
                name='Test Client',
                ip_address='127.0.0.1',
                mac_address='00:00:00:00:00:00',
                status='offline'
            )
            db_session.add(client)
            db_session.commit()
            tests.append(("Add client", True))
            
            # Query client
            found = db_session.query(ClientModel).filter_by(hwid='TEST-HWID-789').first()
            tests.append(("Query client", found is not None))
            
            # Update client
            if found:
                found.status = 'online'
                db_session.commit()
                updated = db_session.query(ClientModel).filter_by(hwid='TEST-HWID-789').first()
                tests.append(("Update client", updated.status == 'online'))
                
                # Add session
                session = SessionModel(
                    client_id=found.id,
                    duration_minutes=30,
                    cost_per_hour=50.0,
                    free_mode=False
                )
                db_session.add(session)
                db_session.commit()
                tests.append(("Add session", True))
            
        finally:
            # Cleanup - ensure resources are freed
            try:
                db_session.close()
            except Exception as e:
                print(f"  Warning: Error closing session: {e}")
            
            try:
                db.close()
            except Exception as e:
                print(f"  Warning: Error closing database: {e}")
        
        tests.append(("Cleanup", True))
        
    except Exception as e:
        tests.append(("Database initialization", False))
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always try to remove test database file
        if db_path and os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception as e:
                print(f"  Warning: Could not remove test database: {e}")
    
    for test_name, passed in tests:
        print_result(test_name, passed)
    
    return all(passed for _, passed in tests)

def test_protocol():
    """Test protocol messages"""
    print_header("Testing Protocol Messages")
    tests = []
    
    try:
        from shared.protocol import (
            Message, MessageType, ClientRegisterMessage, 
            SessionStartMessage, SessionStopMessage, HeartbeatMessage
        )
        from shared.models import ClientStatus
        
        # Test ClientRegisterMessage
        register_msg = ClientRegisterMessage(
            hwid='TEST-HWID-001',
            name='Test PC',
            ip_address='192.168.1.100',
            mac_address='AA:BB:CC:DD:EE:FF'
        )
        msg = register_msg.to_message()
        tests.append(("ClientRegisterMessage", msg.type == MessageType.CLIENT_REGISTER.value))
        
        # Test SessionStartMessage
        session_start = SessionStartMessage(
            duration_minutes=60,
            is_unlimited=False,
            cost_per_hour=100.0,
            free_mode=False
        )
        msg = session_start.to_message()
        tests.append(("SessionStartMessage", msg.type == MessageType.SESSION_START.value))
        
        # Test SessionStopMessage
        session_stop = SessionStopMessage(
            reason="manual",
            actual_duration=55,
            cost=91.67
        )
        msg = session_stop.to_message()
        tests.append(("SessionStopMessage", msg.type == MessageType.SESSION_STOP.value))
        
        # Test HeartbeatMessage
        heartbeat = HeartbeatMessage(status=ClientStatus.ONLINE)
        msg = heartbeat.to_message()
        tests.append(("HeartbeatMessage", msg.type == MessageType.CLIENT_HEARTBEAT.value))
        
    except Exception as e:
        tests.append(("Protocol test", False))
        print(f"  Error: {e}")
    
    for test_name, passed in tests:
        print_result(test_name, passed)
    
    return all(passed for _, passed in tests)

def test_utils():
    """Test utility functions"""
    print_header("Testing Utility Functions")
    tests = []
    
    try:
        from shared.utils import get_hwid, get_local_ip, get_computer_name, hash_password, verify_password
        
        # Test HWID generation
        hwid = get_hwid()
        tests.append(("Get HWID", len(hwid) > 0))
        
        # Test IP detection
        ip = get_local_ip()
        tests.append(("Get local IP", len(ip) > 0))
        
        # Test computer name
        name = get_computer_name()
        tests.append(("Get computer name", len(name) > 0))
        
        # Test password hashing
        password = "test_password_123"
        hashed = hash_password(password)
        tests.append(("Hash password", len(hashed) > 0))
        
        # Test password verification
        is_valid = verify_password(password, hashed)
        tests.append(("Verify correct password", is_valid))
        
        is_invalid = verify_password("wrong_password", hashed)
        tests.append(("Reject wrong password", not is_invalid))
        
    except Exception as e:
        tests.append(("Utils test", False))
        print(f"  Error: {e}")
    
    for test_name, passed in tests:
        print_result(test_name, passed)
    
    return all(passed for _, passed in tests)

def test_config():
    """Test configuration system"""
    print_header("Testing Configuration System")
    tests = []
    
    try:
        from shared.config import ServerConfig, ClientConfig
        
        # Test ServerConfig creation
        server_config = ServerConfig()
        tests.append(("Create ServerConfig", True))
        tests.append(("Server has host", hasattr(server_config, 'host')))
        tests.append(("Server has port", hasattr(server_config, 'port')))
        
        # Test ClientConfig creation
        client_config = ClientConfig()
        tests.append(("Create ClientConfig", True))
        tests.append(("Client has server_url", hasattr(client_config, 'server_url')))
        
    except Exception as e:
        tests.append(("Config test", False))
        print(f"  Error: {e}")
    
    for test_name, passed in tests:
        print_result(test_name, passed)
    
    return all(passed for _, passed in tests)

def run_all_tests():
    """Run all tests"""
    print_header("LibLocker Comprehensive Test Suite")
    print(f"Started at: {datetime.now()}")
    
    results = []
    
    # Run test suites
    results.append(("Module Imports", test_imports()))
    results.append(("Database Operations", test_database()))
    results.append(("Protocol Messages", test_protocol()))
    results.append(("Utility Functions", test_utils()))
    results.append(("Configuration System", test_config()))
    
    # Print summary
    print_header("Test Summary")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_suite, passed in results:
        print_result(test_suite, passed)
    
    print(f"\nTotal: {passed_count}/{total_count} test suites passed")
    
    if passed_count == total_count:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} test suite(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
