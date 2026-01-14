# Testing the Widget Fix

This directory contains tests to verify the timer widget appearance fix.

## Quick Tests

### 1. Unit Test - Signal Mechanism
Tests the basic signal emission and reception:
```bash
python3 test_signal_unit.py
```

Expected output:
```
✅ SUCCESS: Signal was received!
✅ Data matches: True
```

### 2. Integration Test - Full Flow
Tests the complete flow with MainWindow:
```bash
python3 test_signal_flow.py
```

Expected output:
```
[MainWindow] *** on_session_started CALLED ***
[MainWindow] Timer widget shown successfully
```

### 3. Widget Display Test
Tests just the widget display without server:
```bash
python3 test_widget.py
```

This will show the timer widget for 1 minute.

## Full Client-Server Test

To test with the actual server:

1. **Start the server:**
   ```bash
   python run_server.py
   ```

2. **Start the client:**
   ```bash
   python run_client.py
   ```

3. **From server GUI:**
   - Select the connected client in the table
   - Click "Начать сессию" (Start Session)
   - Set duration (e.g., 1 minute)
   - Click OK

4. **Verify on client:**
   - Check logs for: `[MainWindow] *** on_session_started CALLED ***`
   - Timer widget should appear in the top-left corner
   - Widget shows countdown timer and cost

## What Was Fixed

The main issue was **cross-thread signal emission**. The fix includes:

1. ✅ Explicit `Qt.ConnectionType.QueuedConnection` for thread-safe signals
2. ✅ Enhanced logging throughout the signal path
3. ✅ Widget activation improvements (raise_, activateWindow)
4. ✅ Cross-platform compatibility (optional Windows imports)

See `WIDGET_FIX_NOTES.md` for detailed technical explanation.

## Troubleshooting

If the widget still doesn't appear:

1. Check the client logs for these messages:
   ```
   [Client] SESSION_START received
   [ClientThread] Callback called - emitting session_started signal
   [MainWindow] *** on_session_started CALLED ***
   [MainWindow] Timer widget shown successfully
   ```

2. If you see the first two but not the last two:
   - Signal connection issue (should be fixed by this PR)
   
3. If you see all messages but no widget:
   - Check if widget is behind other windows
   - Check widget position in config.client.ini

4. Enable DEBUG logging in config.client.ini:
   ```ini
   [logging]
   level = DEBUG
   ```
