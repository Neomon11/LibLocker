"""
Test that web server doesn't start when disabled
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import aiohttp
from src.server.server import LibLockerServer
from src.shared.config import ServerConfig
from src.shared.utils import hash_password

async def test_web_server_disabled():
    """Test server with web server disabled"""
    print("Testing server with web server disabled...")
    
    # Create config with web server DISABLED
    config = ServerConfig()
    config.set('server', 'web_server_enabled', 'false')
    config.set('server', 'port', '8765')
    config.set('server', 'web_port', '8080')
    config.save()
    
    print(f"✓ Config: web_server_enabled={config.web_server_enabled}")
    
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
        
        print("\nVerifying web server is NOT running...")
        
        # Try to access web server - should fail
        base_url = f"http://127.0.0.1:{config.web_port}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{base_url}/", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    # If we get here, web server is running (BAD)
                    print("✗ FAIL: Web server is running when it should be disabled!")
                    raise AssertionError("Web server should not be accessible when disabled")
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
                # Expected - connection should fail
                print("✓ Web server is correctly disabled (connection refused)")
        
        print("\n" + "=" * 60)
        print("Test passed! ✓")
        print("=" * 60)
        print("Web server correctly respects the 'enabled' setting")
        
    except AssertionError:
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
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
    print("Web Server Disabled Test")
    print("=" * 60)
    asyncio.run(test_web_server_disabled())
    print("\nTest completed!")
