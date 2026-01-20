"""
Test script for web server functionality
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from src.server.web_server import LibLockerWebServer
from src.server.server import LibLockerServer
from src.shared.config import ServerConfig
from src.shared.utils import hash_password

async def test_web_server():
    """Test web server initialization and basic functionality"""
    print("Testing web server initialization...")
    
    # Create config with web server enabled
    config = ServerConfig()
    
    # Set a test admin password
    test_password = "test123456"
    config.admin_password_hash = hash_password(test_password)
    config.set('server', 'web_server_enabled', 'true')
    config.save()
    
    print(f"✓ Config created with web_server_enabled: {config.web_server_enabled}")
    print(f"✓ Web port: {config.web_port}")
    print(f"✓ Admin password set: {bool(config.admin_password_hash)}")
    
    # Create server instance
    server = LibLockerServer(
        host=config.host,
        port=config.port,
        db_path=config.database_path,
        config=config
    )
    print("✓ Server instance created")
    
    # Create web server instance
    web_server = LibLockerWebServer(server, config)
    print("✓ Web server instance created")
    
    # Try to start web server
    try:
        await web_server.start()
        print(f"✓ Web server started on http://{config.host}:{config.web_port}")
        print("\nWeb server is running. You can access it at:")
        print(f"  http://localhost:{config.web_port}")
        print(f"\nTest credentials:")
        print(f"  Password: {test_password}")
        print("\nPress Ctrl+C to stop...")
        
        # Keep running for a bit to test
        await asyncio.sleep(10)
        
    except Exception as e:
        print(f"✗ Error starting web server: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop web server
        await web_server.stop()
        print("\n✓ Web server stopped")

if __name__ == "__main__":
    print("=" * 60)
    print("Web Server Test")
    print("=" * 60)
    asyncio.run(test_web_server())
    print("\nTest completed!")
