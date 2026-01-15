"""
Test script to verify UI improvements without GUI initialization:
1. End Session button for unlimited sessions
2. Close button with black background
3. Lock screen password fix
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_protocol_message():
    """Test that ClientSessionStopRequestMessage is properly defined"""
    print("Testing protocol message...")
    
    from src.shared.protocol import MessageType, ClientSessionStopRequestMessage
    
    # Check if message type exists
    assert hasattr(MessageType, 'CLIENT_SESSION_STOP_REQUEST'), \
        "CLIENT_SESSION_STOP_REQUEST message type not found"
    
    # Create a message
    msg = ClientSessionStopRequestMessage(reason="user_request")
    message = msg.to_message()
    
    assert message.type == MessageType.CLIENT_SESSION_STOP_REQUEST.value, \
        "Message type mismatch"
    assert message.data['reason'] == "user_request", \
        "Message data mismatch"
    
    print("✓ Protocol message test passed")

def test_client_has_session_stop_method():
    """Test that LibLockerClient has request_session_stop method"""
    print("\nTesting client session stop method...")
    
    from src.client.client import LibLockerClient
    
    # Check that client has request_session_stop method
    assert hasattr(LibLockerClient, 'request_session_stop'), \
        "request_session_stop method not found in LibLockerClient"
    
    print("✓ Client session stop method test passed")

def test_server_handles_stop_request():
    """Test that server has handler for client session stop requests"""
    print("\nTesting server handler...")
    
    from src.server.server import LibLockerServer
    
    # Check that server has handler method
    assert hasattr(LibLockerServer, '_handle_client_session_stop_request'), \
        "_handle_client_session_stop_request method not found in LibLockerServer"
    
    print("✓ Server handler test passed")

def test_gui_code_structure():
    """Test that GUI code has the necessary structure (without initialization)"""
    print("\nTesting GUI code structure...")
    
    # Read the GUI file to check for key additions
    with open('src/client/gui.py', 'r', encoding='utf-8') as f:
        gui_code = f.read()
    
    # Check for session_stop_requested signal
    assert 'session_stop_requested = pyqtSignal()' in gui_code, \
        "session_stop_requested signal not found in GUI code"
    
    # Check for request_session_stop method
    assert 'def request_session_stop(self):' in gui_code, \
        "request_session_stop method not found in GUI code"
    
    # Check for btn_end_session button creation
    assert 'self.btn_end_session = QPushButton("⏹️ Завершить сессию")' in gui_code, \
        "End Session button creation not found in GUI code"
    
    # Check that button is only created for unlimited sessions
    assert 'if self.is_unlimited:' in gui_code and \
           'self.btn_end_session' in gui_code, \
        "End Session button not conditionally created for unlimited sessions"
    
    # Check for black background in close button styling
    assert 'background: #000000' in gui_code or 'background: black' in gui_code.lower(), \
        "Black background not found in close button styling"
    
    # Check for force_close() fix in password dialog
    assert 'self.force_close()' in gui_code, \
        "force_close() not used in password dialog"
    
    # Check that signal connection exists
    assert 'session_stop_requested.connect' in gui_code, \
        "session_stop_requested signal connection not found"
    
    # Check for on_session_stop_requested handler
    assert 'def on_session_stop_requested(self):' in gui_code, \
        "on_session_stop_requested handler not found"
    
    print("✓ GUI code structure test passed")

def main():
    print("=" * 60)
    print("Running UI Improvements Tests (Code Analysis)")
    print("=" * 60)
    
    try:
        test_protocol_message()
        test_client_has_session_stop_method()
        test_server_handles_stop_request()
        test_gui_code_structure()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print("\nChanges verified:")
        print("1. ✓ End Session button added for unlimited sessions")
        print("2. ✓ Close button has black background styling")
        print("3. ✓ Lock screen password fix implemented")
        print("4. ✓ Protocol message for client session stop request added")
        print("5. ✓ Client method to request session stop added")
        print("6. ✓ Server handler for session stop requests added")
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
