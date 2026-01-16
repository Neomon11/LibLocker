"""
Test to verify aiohttp ClientWSTimeout fix
This test verifies that the aiohttp version supports ClientWSTimeout
which is required by python-engineio for WebSocket connections.
"""
import sys
import os

def test_aiohttp_version():
    """Test that aiohttp has the required version and ClientWSTimeout"""
    import aiohttp
    from packaging import version
    
    # Check version is at least 3.11.0
    aiohttp_version = version.parse(aiohttp.__version__)
    required_version = version.parse('3.11.0')
    
    assert aiohttp_version >= required_version, (
        f"aiohttp version {aiohttp.__version__} is too old. "
        f"Need at least 3.11.0 for ClientWSTimeout support"
    )
    print(f"✓ aiohttp version {aiohttp.__version__} is compatible")

def test_client_ws_timeout_exists():
    """Test that ClientWSTimeout is available in aiohttp"""
    import aiohttp
    
    assert hasattr(aiohttp, 'ClientWSTimeout'), (
        "aiohttp.ClientWSTimeout is not available. "
        "This is required by python-engineio for WebSocket connections."
    )
    print("✓ aiohttp.ClientWSTimeout is available")

def test_client_ws_timeout_instantiation():
    """Test that ClientWSTimeout can be instantiated"""
    from aiohttp import ClientWSTimeout
    
    # Test creating a ClientWSTimeout instance (as used by engineio)
    timeout = ClientWSTimeout(ws_close=30)
    assert timeout.ws_close == 30
    print("✓ ClientWSTimeout can be instantiated successfully")

def test_socketio_client_creation():
    """Test that socketio AsyncClient can be created"""
    import socketio
    
    # Test creating a socketio client (which internally uses aiohttp)
    client = socketio.AsyncClient(
        reconnection=True,
        reconnection_attempts=0,
        reconnection_delay=1,
        reconnection_delay_max=5,
        logger=False,
        engineio_logger=False
    )
    
    assert client is not None
    print("✓ socketio.AsyncClient created successfully")

def test_liblocker_client_import():
    """Test that LibLockerClient can be imported and instantiated"""
    # Add src to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    from src.client.client import LibLockerClient
    
    # Test creating a LibLockerClient instance
    client = LibLockerClient('http://localhost:8765')
    assert client.server_url == 'http://localhost:8765'
    print("✓ LibLockerClient imported and instantiated successfully")

if __name__ == '__main__':
    print("Testing aiohttp ClientWSTimeout fix...")
    print("=" * 60)
    
    try:
        test_aiohttp_version()
        test_client_ws_timeout_exists()
        test_client_ws_timeout_instantiation()
        test_socketio_client_creation()
        test_liblocker_client_import()
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("\nThe aiohttp fix is working correctly.")
        print("The client should now be able to connect to the server via WebSocket.")
    except AssertionError as e:
        print("\n✗ Test failed:", str(e))
        sys.exit(1)
    except Exception as e:
        print("\n✗ Unexpected error:", str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
