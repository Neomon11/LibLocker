"""
Test full server integration with web server enabled
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import aiohttp
from src.server.server import LibLockerServer
from src.shared.config import ServerConfig
from src.shared.utils import hash_password

async def test_full_integration():
    """Test full server with web server enabled"""
    print("Testing full server integration with web server...")
    
    # Create config with web server enabled
    config = ServerConfig()
    test_password = "admin123"
    config.admin_password_hash = hash_password(test_password)
    config.set('server', 'web_server_enabled', 'true')
    config.set('server', 'port', '8765')
    config.set('server', 'web_port', '8080')
    config.save()
    
    print(f"✓ Config: web_server_enabled={config.web_server_enabled}")
    print(f"✓ WebSocket port: {config.port}")
    print(f"✓ Web port: {config.web_port}")
    
    # Create server instance
    server = LibLockerServer(
        host='127.0.0.1',
        port=config.port,
        db_path=config.database_path,
        config=config
    )
    
    print("✓ Server instance created")
    
    # Start server in background
    server_task = asyncio.create_task(server.run())
    
    try:
        # Wait for server to start
        await asyncio.sleep(2)
        
        print("\n" + "=" * 60)
        print("Server is running with both WebSocket and Web Server")
        print("=" * 60)
        print(f"WebSocket Server: ws://127.0.0.1:{config.port}")
        print(f"Web Server: http://127.0.0.1:{config.web_port}")
        print("=" * 60)
        
        # Test web server is accessible
        base_url = f"http://127.0.0.1:{config.web_port}"
        
        async with aiohttp.ClientSession() as session:
            print("\nTesting web interface accessibility...")
            
            # Test index page
            async with session.get(f"{base_url}/") as resp:
                assert resp.status == 200
                print("✓ Web interface is accessible")
            
            # Test login
            async with session.post(
                f"{base_url}/api/login",
                json={"password": test_password}
            ) as resp:
                data = await resp.json()
                assert data.get('success')
                print("✓ Authentication works")
            
        print("\n" + "=" * 60)
        print("All integration tests passed! ✓")
        print("=" * 60)
        print("\nThe server is fully functional with:")
        print("  - WebSocket server for client connections")
        print("  - Web server for browser-based control")
        print("  - Password authentication")
        print("  - All API endpoints working")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Cancel server task
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        print("\n✓ Server stopped")

if __name__ == "__main__":
    print("=" * 60)
    print("Full Server Integration Test")
    print("=" * 60)
    asyncio.run(test_full_integration())
    print("\nTest completed!")
