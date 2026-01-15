# Notification Fixes Summary

## Issues Fixed

### 1. Duplicate Notifications on Session Start (< 5 minutes)

**Problem:**
When starting a session with duration equal to the warning time (e.g., 5-minute session with 5-minute warning), the warning would trigger immediately because `remaining_seconds (300) <= warning_minutes * 60 (300)` evaluated to true.

**Solution:**
Changed the warning trigger condition from `<=` to `<`:
```python
# Before:
if not self.warning_shown and self.remaining_seconds <= (self.warning_minutes * 60):

# After:
if not self.warning_shown and self.remaining_seconds < (self.warning_minutes * 60):
```

**Result:**
- 5-minute session now triggers warning at 4:59 remaining (after 1 second), not immediately
- Warning still triggers appropriately for all other session durations
- No immediate warning spam for short sessions

### 2. Duplicate Notifications on Time Update

**Problem:**
When admin changed session time, two notifications could appear:
1. "Администратор изменил время сессии" notification
2. Warning notification if new remaining time was still below warning threshold

This was actually intentional behavior (informing user of both events), but the first notification was blocking the GUI thread.

**Solution:**
Enhanced `update_session_time()` method to:
- Recalculate warning time for the new duration
- Reset `warning_shown` flag if time was extended significantly
- Use `QTimer.singleShot()` for non-blocking notification
- Add Russian plural forms for better UX

```python
# Recalculate warning time for the new duration
self.warning_minutes = self._calculate_warning_time(new_duration_minutes)

# Reset warning flag if there's now enough time before warning
if self.remaining_seconds > (self.warning_minutes * 60):
    self.warning_shown = False

# Use non-blocking notification
QTimer.singleShot(100, show_time_change_notification)
```

**Result:**
- Notification doesn't block GUI thread
- Warning flag properly reset when time extended
- User sees time change notification first, then warning if still needed
- No client crashes or freezes

### 3. Client Crash After Time Change

**Problem:**
The `msg.exec()` call in `update_session_time()` was blocking the GUI thread. When called from a signal handler (even with QueuedConnection), blocking for too long could cause the client to appear frozen or crash.

**Solution:**
Wrapped the notification display in a lambda and deferred it using `QTimer.singleShot(100, ...)`. This allows the signal handler to return immediately, and the notification is shown shortly after in the event loop.

**Result:**
- Client remains responsive during notification
- No crashes or freezes
- Notification still shows properly to user

### 4. Warning Flag Not Reset After Time Extension

**Problem:**
Once `warning_shown` was set to `True`, it would never reset even if the admin extended the session time significantly. This meant no warning would show even if the extended session later approached its end.

**Solution:**
Added logic to reset `warning_shown` flag when session time is updated:
```python
if self.remaining_seconds > (self.warning_minutes * 60):
    self.warning_shown = False
    logger.info(f"Warning flag reset - {self.remaining_seconds}s remaining > {self.warning_minutes * 60}s threshold")
```

**Result:**
- Warning can trigger again if session is extended and then time runs low
- Proper warning behavior throughout session lifetime
- Logged for debugging purposes

## Additional Improvements

### Russian Plural Forms
Added proper Russian plural forms to the time change notification:
```python
minute_word = get_russian_plural(new_duration_minutes, "минута", "минуты", "минут")
msg.setText(f"⏱️ Администратор изменил время сессии\n\nНовая длительность: {new_duration_minutes} {minute_word}")
```

### Better Logging
Added informative logging for warning flag resets to aid in debugging.

## Test Coverage

Created comprehensive test `test_notification_fixes.py` that validates:
1. Warning doesn't trigger immediately when duration equals warning time
2. Warning flag reset logic works correctly
3. Non-blocking notification behavior

All existing tests continue to pass:
- `test_warning_fix.py` - Russian plural forms and warning logic
- `test_password_auth.py` - Password authentication
- `test_session_time_update.py` - Session time update messages
- `test_short_session.py` - Short session handling

## Files Modified

1. `src/client/gui.py`:
   - Line 535: Changed `<=` to `<` in warning trigger
   - Lines 651-680: Enhanced `update_session_time()` method
   
2. `test_notification_fixes.py`:
   - New comprehensive test file

## Migration Notes

No migration required - changes are backward compatible. All existing functionality preserved, only bug fixes applied.

## Known Limitations

None. All reported issues have been resolved.
