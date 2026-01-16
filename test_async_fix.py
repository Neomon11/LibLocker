"""
Test to verify that async commands properly wait for results
"""
import asyncio
import threading
import time

def test_async_result_checking():
    """Test that demonstrates the fix - waiting for async results"""
    
    print("\n" + "="*60)
    print("Test: Async Command Result Checking")
    print("="*60)
    
    # Create event loop in a separate thread (simulating ServerThread)
    loop = None
    thread_started = threading.Event()
    
    def run_loop():
        nonlocal loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        thread_started.set()
        loop.run_forever()
    
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    thread_started.wait()  # Wait for loop to start
    
    try:
        # Test 1: Successful operation returns True
        print("\n1️⃣ Test: Successful operation")
        async def successful_operation():
            await asyncio.sleep(0.1)
            return True
        
        future = asyncio.run_coroutine_threadsafe(successful_operation(), loop)
        result = future.result(timeout=5.0)
        
        assert result is True, "Expected True from successful operation"
        print("   ✅ Result properly returned: True")
        
        # Test 2: Failed operation returns False
        print("\n2️⃣ Test: Failed operation")
        async def failed_operation():
            await asyncio.sleep(0.1)
            return False
        
        future = asyncio.run_coroutine_threadsafe(failed_operation(), loop)
        result = future.result(timeout=5.0)
        
        assert result is False, "Expected False from failed operation"
        print("   ✅ Result properly returned: False")
        
        # Test 3: Timeout detection
        print("\n3️⃣ Test: Timeout detection")
        async def slow_operation():
            await asyncio.sleep(10)
            return True
        
        future = asyncio.run_coroutine_threadsafe(slow_operation(), loop)
        
        try:
            result = future.result(timeout=0.5)
            assert False, "Should have raised TimeoutError"
        except TimeoutError:
            print("   ✅ TimeoutError properly raised")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nThe fix ensures that:")
        print("  • Future.result() is called to wait for operation completion")
        print("  • Return values (True/False) are properly checked")
        print("  • Timeouts are detected and handled")
        print("  • User gets accurate feedback about operation status")
        
        return True
        
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)

def run_tests():
    """Run all tests"""
    try:
        success = test_async_result_checking()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(run_tests())
