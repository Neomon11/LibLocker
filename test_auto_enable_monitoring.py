#!/usr/bin/env python3
"""
Test script for auto-enable installation monitoring feature
Verifies that the server auto-enables monitoring when session starts (if configured)
"""
import sys
import os
import asyncio
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.shared.config import ServerConfig
from src.server.server import LibLockerServer
from src.shared.database import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_auto_enable_monitoring():
    """Test that server auto-enables monitoring on session start when configured"""
    print("=" * 70)
    print("Test: Auto-Enable Installation Monitoring on Session Start")
    print("=" * 70)
    
    # Setup
    print("\n1. Setting up test configuration...")
    config = ServerConfig()
    original_enabled = config.installation_monitor_enabled
    original_volume = config.installation_monitor_alert_volume
    
    # Enable auto-monitoring in config
    config.installation_monitor_enabled = True
    config.installation_monitor_alert_volume = 85
    config.save()
    print(f"   ✓ Config saved: monitoring enabled={config.installation_monitor_enabled}, volume={config.installation_monitor_alert_volume}")
    
    # Create server instance
    print("\n2. Creating server instance...")
    server = LibLockerServer(host='localhost', port=8766, db_path='test_auto_monitor.db', config=config)
    print("   ✓ Server created")
    
    # Track emitted messages
    emitted_messages = []
    
    # Mock the sio.emit method to capture messages
    original_emit = server.sio.emit
    async def mock_emit(event, data, room=None):
        logger.info(f"Mock emit: event={event}, room={room}, data={data}")
        emitted_messages.append({'event': event, 'data': data, 'room': room})
    
    server.sio.emit = mock_emit
    
    # Simulate a connected client
    print("\n3. Simulating connected client...")
    test_client_id = 1
    test_client_sid = 'test_client_123'
    server.connected_clients[test_client_sid] = {
        'client_id': test_client_id,
        'hwid': 'TEST_HWID',
        'name': 'Test Client'
    }
    print(f"   ✓ Client connected: ID={test_client_id}, SID={test_client_sid}")
    
    # Start a session
    print("\n4. Starting session for client...")
    emitted_messages.clear()
    
    result = await server.start_session(
        client_id=test_client_id,
        duration_minutes=30,
        is_unlimited=False,
        cost_per_hour=100.0,
        free_mode=False
    )
    
    if result:
        print("   ✓ Session started successfully")
    else:
        print("   ✗ Session failed to start")
    
    # Wait a moment for any async operations
    await asyncio.sleep(0.5)
    
    # Analyze emitted messages
    print("\n5. Analyzing emitted messages...")
    print(f"   Total messages emitted: {len(emitted_messages)}")
    
    session_start_found = False
    monitor_toggle_found = False
    monitor_enabled = False
    monitor_volume = None
    
    for msg in emitted_messages:
        logger.info(f"Message: {msg}")
        if msg['event'] == 'message' and isinstance(msg['data'], dict):
            msg_type = msg['data'].get('type')
            print(f"   - Message type: {msg_type}")
            
            if msg_type == 'session_start':
                session_start_found = True
                print("     ✓ SESSION_START message found")
            
            elif msg_type == 'installation_monitor_toggle':
                monitor_toggle_found = True
                msg_data = msg['data'].get('data', {})
                monitor_enabled = msg_data.get('enabled', False)
                monitor_volume = msg_data.get('alert_volume', None)
                print(f"     ✓ INSTALLATION_MONITOR_TOGGLE message found")
                print(f"       - enabled: {monitor_enabled}")
                print(f"       - alert_volume: {monitor_volume}")
    
    # Restore original config
    print("\n6. Restoring original configuration...")
    config.installation_monitor_enabled = original_enabled
    config.installation_monitor_alert_volume = original_volume
    config.save()
    print("   ✓ Config restored")
    
    # Cleanup
    import os
    if os.path.exists('test_auto_monitor.db'):
        os.remove('test_auto_monitor.db')
    
    # Results
    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)
    
    success = True
    
    if session_start_found:
        print("✓ SESSION_START message was sent")
    else:
        print("✗ SESSION_START message NOT found")
        success = False
    
    if monitor_toggle_found:
        print("✓ INSTALLATION_MONITOR_TOGGLE message was sent")
        
        if monitor_enabled:
            print("✓ Monitoring was ENABLED")
        else:
            print("✗ Monitoring was NOT enabled")
            success = False
        
        if monitor_volume == 85:
            print(f"✓ Alert volume is correct: {monitor_volume}")
        else:
            print(f"✗ Alert volume is incorrect: {monitor_volume} (expected 85)")
            success = False
    else:
        print("✗ INSTALLATION_MONITOR_TOGGLE message NOT found")
        print("  This means auto-enable is NOT working")
        success = False
    
    print("=" * 70)
    
    if success:
        print("\n✓✓✓ TEST PASSED - Auto-enable monitoring is working ✓✓✓")
        return 0
    else:
        print("\n✗✗✗ TEST FAILED - Auto-enable monitoring is NOT working ✗✗✗")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(test_auto_enable_monitoring())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
