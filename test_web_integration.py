"""
Integration test for web server endpoints
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import aiohttp
from src.server.web_server import LibLockerWebServer
from src.server.server import LibLockerServer
from src.shared.config import ServerConfig
from src.shared.utils import hash_password

async def test_web_endpoints():
    """Test web server endpoints"""
    print("Testing web server endpoints...")
    
    # Create config with web server enabled
    config = ServerConfig()
    test_password = "test123456"
    config.admin_password_hash = hash_password(test_password)
    config.set('server', 'web_server_enabled', 'true')
    config.save()
    
    # Create server and web server instances
    server = LibLockerServer(
        host='127.0.0.1',
        port=8765,
        db_path=config.database_path,
        config=config
    )
    
    web_server = LibLockerWebServer(server, config)
    
    try:
        # Start web server
        await web_server.start()
        print(f"✓ Web server started on http://127.0.0.1:{config.web_port}")
        
        # Wait a bit for server to be ready
        await asyncio.sleep(1)
        
        base_url = f"http://127.0.0.1:{config.web_port}"
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Index page
            print("\n1. Testing index page...")
            async with session.get(f"{base_url}/") as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                content = await resp.text()
                assert "LibLocker" in content, "Page should contain LibLocker"
                print("   ✓ Index page loads correctly")
            
            # Test 2: Login with wrong password
            print("\n2. Testing login with wrong password...")
            async with session.post(
                f"{base_url}/api/login",
                json={"password": "wrongpassword"}
            ) as resp:
                assert resp.status == 401, f"Expected 401, got {resp.status}"
                data = await resp.json()
                assert not data.get('success'), "Login should fail"
                print("   ✓ Login fails with wrong password")
            
            # Test 3: Login with correct password
            print("\n3. Testing login with correct password...")
            async with session.post(
                f"{base_url}/api/login",
                json={"password": test_password}
            ) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                data = await resp.json()
                assert data.get('success'), "Login should succeed"
                token = data.get('token')
                assert token, "Token should be returned"
                print("   ✓ Login succeeds with correct password")
            
            # Test 4: Get clients without auth
            print("\n4. Testing get clients without auth...")
            async with session.get(f"{base_url}/api/clients") as resp:
                assert resp.status == 401, f"Expected 401, got {resp.status}"
                print("   ✓ Unauthorized access denied")
            
            # Test 5: Get clients with auth
            print("\n5. Testing get clients with auth...")
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(f"{base_url}/api/clients", headers=headers) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                data = await resp.json()
                assert data.get('success'), "Should succeed"
                assert 'clients' in data, "Should return clients list"
                print(f"   ✓ Get clients succeeds (found {len(data['clients'])} clients)")
            
            # Test 6: Start session without auth
            print("\n6. Testing start session without auth...")
            async with session.post(
                f"{base_url}/api/start_session",
                json={"client_id": 1, "duration_minutes": 30}
            ) as resp:
                assert resp.status == 401, f"Expected 401, got {resp.status}"
                print("   ✓ Unauthorized access denied")
            
            # Test 7: Stop session without auth
            print("\n7. Testing stop session without auth...")
            async with session.post(
                f"{base_url}/api/stop_session",
                json={"client_id": 1}
            ) as resp:
                assert resp.status == 401, f"Expected 401, got {resp.status}"
                print("   ✓ Unauthorized access denied")
            
            # Test 8: Unlock client without auth
            print("\n8. Testing unlock client without auth...")
            async with session.post(
                f"{base_url}/api/unlock_client",
                json={"client_id": 1}
            ) as resp:
                assert resp.status == 401, f"Expected 401, got {resp.status}"
                print("   ✓ Unauthorized access denied")
            
            # Test 9: Logout
            print("\n9. Testing logout...")
            async with session.post(
                f"{base_url}/api/logout",
                headers=headers
            ) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                data = await resp.json()
                assert data.get('success'), "Logout should succeed"
                print("   ✓ Logout succeeds")
            
            print("\n" + "=" * 60)
            print("All tests passed! ✓")
            print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Stop web server
        await web_server.stop()
        print("\n✓ Web server stopped")

if __name__ == "__main__":
    print("=" * 60)
    print("Web Server Integration Test")
    print("=" * 60)
    asyncio.run(test_web_endpoints())
    print("\nTest completed successfully!")
