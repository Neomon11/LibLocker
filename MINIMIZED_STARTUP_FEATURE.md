# Minimized Startup Mode Feature - Implementation Summary

## Overview
This PR adds functionality to launch the LibLocker client application in a minimized state, allowing users to run the client in the background without the main window appearing on startup.

## Request
Original request (in Russian): "Добавь в клиент и клиентский конфиг функцию запуска в свернутом режиме"
Translation: "Add to the client and client config a function to launch in minimized mode"

## Changes Made

### 1. Configuration Files
**Files Modified:**
- `config.client.ini`
- `config.client.example.ini`

**Changes:**
Added new configuration option `start_minimized` to the `[autostart]` section:
```ini
[autostart]
# Автоматический запуск при загрузке Windows
enabled = false
# Автоматически подключаться к серверу
auto_connect = true
# Запускать приложение в свернутом виде
start_minimized = false
```

### 2. Configuration Class
**File Modified:** `src/shared/config.py`

**Changes:**
Added a new property to the `ClientConfig` class to read the `start_minimized` configuration:
```python
@property
def start_minimized(self) -> bool:
    return self.get_bool('autostart', 'start_minimized', False)
```

- Returns: `bool` - True if the client should start minimized, False otherwise
- Default: `False` (maintains backward compatibility)

### 3. Client GUI Initialization
**File Modified:** `src/client/gui.py`

**Changes:**
Updated the `main()` function to check the configuration and start the window minimized when enabled:
```python
# Проверяем настройку запуска в свернутом виде
if config.start_minimized:
    # Показываем окно минимизированным
    window.showMinimized()
    logger.info("Client window opened (minimized)")
else:
    window.show()
    logger.info("Client window opened")
```

### 4. Tests Added
**New Test Files:**
- `test_minimized_startup.py` - Tests configuration property reading
- `test_gui_minimized_startup.py` - Tests GUI configuration logic

**Test Coverage:**
- ✅ Reading `start_minimized=true` from config
- ✅ Reading `start_minimized=false` from config
- ✅ Default value when option is not specified
- ✅ Configuration logic integration

## User Experience

### When start_minimized = true:
1. Application starts with the window minimized to the taskbar
2. The system tray icon is visible
3. Users can restore the window by:
   - Double-clicking the system tray icon
   - Right-clicking the tray icon and selecting "Развернуть" (Expand)
4. All other functionality remains unchanged

### When start_minimized = false (default):
- Application behaves as before - window appears normally on startup
- Maintains full backward compatibility

## Configuration Example

To enable minimized startup, edit `config.client.ini`:
```ini
[autostart]
enabled = false
auto_connect = true
start_minimized = true  # Set to true to start minimized
```

## Testing Results
All tests pass successfully:
```
Testing minimized startup configuration...
✓ Test passed: start_minimized config reads True correctly
✓ Test passed: start_minimized defaults to False when not specified
✓ Test passed: start_minimized config reads False correctly
✅ All tests passed!

Testing GUI minimized startup configuration logic...
✓ Test 1 passed: Config reads start_minimized=False correctly
✓ Test 2 passed: Config reads start_minimized=True correctly
✓ Configuration logic validated successfully
✅ All GUI logic tests passed!
```

## Security Summary
✅ CodeQL security scan completed with **0 alerts** - no security vulnerabilities detected.

## Code Review
Code review completed successfully with minor style improvements applied:
- Improved boolean assertions in tests (using `assert config.start_minimized` instead of `== True`)
- All feedback has been addressed

## Backward Compatibility
✅ **Fully backward compatible**
- Default value is `False`, maintaining existing behavior
- Existing configurations without the new option continue to work unchanged
- No breaking changes to the API or configuration structure

## Technical Details

### PyQt6 Window States
The implementation uses PyQt6's `QMainWindow.showMinimized()` method:
- On Windows: Window appears minimized to the taskbar
- System tray icon remains accessible
- Window can be restored via standard OS mechanisms and tray icon

### System Tray Integration
The application already has system tray integration:
- Tray icon is always visible (implemented in `init_tray_icon()`)
- Tray menu includes "Развернуть" (Expand) option
- Double-click on tray icon restores the window
- No additional changes needed for tray functionality

## Minimal Changes Philosophy
This implementation follows the "minimal changes" approach:
- Only 4 production files modified (2 config files, 1 config class, 1 GUI file)
- Total changes: ~20 lines of code
- No changes to existing functionality
- No changes to system tray or window management logic
- Uses existing PyQt6 capabilities

## Files Changed Summary
| File | Changes | Lines Changed |
|------|---------|---------------|
| config.client.ini | Added start_minimized option | +2 |
| config.client.example.ini | Added start_minimized option | +2 |
| src/shared/config.py | Added start_minimized property | +4 |
| src/client/gui.py | Added conditional window display logic | +8 |
| test_minimized_startup.py | New test file | +163 |
| test_gui_minimized_startup.py | New test file | +113 |
| **Total Production Code** | | **+16** |
| **Total Test Code** | | **+276** |

## Next Steps
This feature is ready for use. To enable:
1. Edit `config.client.ini`
2. Set `start_minimized = true` in the `[autostart]` section
3. Restart the LibLocker client
4. The window will start minimized, accessible via system tray

## Notes
- This feature is particularly useful for auto-start scenarios where users want the client running in the background
- Compatible with the existing `autostart.enabled` option for Windows startup
- Works with all other client features (session monitoring, notifications, etc.)
