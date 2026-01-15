# Fixes Summary

This document describes the fixes implemented for two critical issues in the LibLocker system.

## Issue 1: Admin Password Should Unlock, Not Close Application

### Problem
When an administrator entered the correct password in the lock screen (shown after session expiration), the application would close completely instead of just removing the lock screen and returning to the main window.

### Root Cause
In `LockScreen.check_password()`, when the correct password was entered, the code called `self.force_close()` which closed the lock screen. However, since the main window was hidden and the timer widget was already closed, there were no visible windows left, causing the entire application to quit.

### Solution
1. Added an `unlocked` signal to the `LockScreen` class
2. Modified `check_password()` to emit the `unlocked` signal instead of directly calling `force_close()`
3. Added `on_lock_screen_unlocked()` handler in `MainClientWindow` that:
   - Closes the lock screen
   - Shows the main window
   - Clears the session data
4. Connected the signal in `on_timer_finished()` when creating the lock screen

### Files Changed
- `src/client/gui.py`:
  - Line 142: Added `unlocked = pyqtSignal()` to `LockScreen` class
  - Lines 321, 328: Changed `self.force_close()` to `self.unlocked.emit()`
  - Lines 872: Connected `self.lock_screen.unlocked` signal
  - Lines 875-887: Added `on_lock_screen_unlocked()` handler

## Issue 2: Session Statistics Always Show as Free

### Problem
In the statistics view, all sessions were showing as free ("Бесплатно") even when they were configured as paid sessions with a specific cost per hour.

### Root Cause
When a session was created in the database, the `cost` field was initialized to 0.0. When the session was stopped, only the `actual_duration` was calculated, but the `cost` was never updated based on the session's `free_mode` and `cost_per_hour` settings.

Additionally, the `free_mode` and `cost_per_hour` parameters were not being stored in the database, so there was no way to calculate the cost accurately when the session ended.

### Solution
1. Updated the `SessionModel` database schema to include:
   - `cost_per_hour` field (Float, default=0.0)
   - `free_mode` field (Boolean, default=True)

2. Modified `start_session()` in `server.py` to store these fields when creating a session

3. Modified `stop_session()` in `server.py` to calculate the cost:
   - Calculate actual duration in minutes
   - If `free_mode` is False and `cost_per_hour` > 0:
     - Convert duration to hours
     - Calculate cost = duration_hours × cost_per_hour
   - Otherwise, set cost to 0.0

### Files Changed
- `src/shared/database.py`:
  - Lines 61-62: Added `cost_per_hour` and `free_mode` columns to `SessionModel`

- `src/server/server.py`:
  - Lines 241-242: Store `cost_per_hour` and `free_mode` when creating session
  - Lines 310-318: Calculate session cost based on actual duration and pricing settings

### Cost Calculation Formula
```python
if not free_mode and cost_per_hour > 0:
    duration_hours = actual_duration_minutes / 60.0
    cost = duration_hours * cost_per_hour
else:
    cost = 0.0
```

### Examples
- Free session (60 minutes): cost = 0.00 руб.
- Paid session (60 minutes, 100 руб/hour): cost = 100.00 руб.
- Paid session (30 minutes, 50 руб/hour): cost = 25.00 руб.

## Testing
Both fixes have been validated:
1. Syntax checking confirmed no compilation errors
2. Cost calculation logic tested with various scenarios (free sessions, paid sessions with different durations and rates)
3. Signal emission structure verified in the GUI code

## Database Migration Note
Existing databases will automatically receive the new `cost_per_hour` and `free_mode` columns when the application starts, as SQLAlchemy's `create_all()` will add missing columns. However, existing sessions in the database will have default values (0.0 for cost_per_hour, True for free_mode), so their costs will remain at 0.0.
