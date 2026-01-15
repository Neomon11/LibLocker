# Fix Summary: Short Session Warning Issues

## Problem Description (Russian)
Возникает ошибка при запуске сессии менее 5 минут, предупреждение о том что осталось 5 минут обрезано и его невозможно закрыть.

**Translation**: An error occurs when starting a session of less than 5 minutes, the warning about 5 minutes remaining is cut off and cannot be closed.

## Root Causes Identified

### 1. Warning Popup Clipping Issue
When the timer widget was minimized (reduced to 30x20 pixels), the warning popup's parent was the tiny widget. This caused:
- The dialog to be positioned at the widget's location (potentially off-screen or in a corner)
- The dialog to be clipped or have rendering issues
- The dialog to be hard to interact with or close

**Technical Details**:
- `QMessageBox(self)` parented the dialog to the TimerWidget
- When minimized, the widget becomes only 30x20px (line 550 in gui.py)
- The visibility restoration happened AFTER the popup was shown (line 515-516)

### 2. Russian Grammar Errors
The warning message always used "минут" (plural form for 5+), which is grammatically incorrect:
- 1 minute should be "минута" (singular)
- 2-4 minutes should be "минуты" (plural form 1)
- 5+ minutes should be "минут" (plural form 2)
- Special rule: 11-20 always use "минут"

## Solutions Implemented

### 1. Fixed Warning Popup Parent and Display Order
**File**: `src/client/gui.py`, lines 528-546

**Changes**:
```python
def show_warning(self):
    """Показать предупреждение о скором окончании сессии"""
    logger.info(f"Warning: {self.warning_minutes} minutes remaining")

    # Принудительно показываем виджет если он был скрыт (ПЕРЕД показом popup)
    if self.is_hidden:
        self.toggle_visibility()  # NOW BEFORE popup

    # ... sound notification ...

    # Всплывающее уведомление
    if self.config.popup_enabled:
        self.show_warning_popup()
```

**In show_warning_popup()** (lines 548-561):
```python
def show_warning_popup(self):
    """Показать всплывающее предупреждение"""
    # Use None as parent to ensure dialog is centered on screen
    msg = QMessageBox(None)  # Changed from QMessageBox(self)
    # ... rest of code ...
```

**Result**: 
- Dialog is now centered on screen regardless of widget state
- Widget is restored to full size before showing popup
- User can always interact with and close the dialog

### 2. Added Russian Pluralization Helper
**File**: `src/client/gui.py`, lines 41-68

**New Function**:
```python
def get_russian_plural(number: int, form1: str, form2: str, form5: str) -> str:
    """
    Возвращает правильную форму слова для русского языка в зависимости от числа
    
    Args:
        number: Число
        form1: Форма для 1 (например, "минута")
        form2: Форма для 2-4 (например, "минуты")
        form5: Форма для 5+ (например, "минут")
    
    Returns:
        Правильная форма слова
    """
    n = abs(number)
    n %= 100
    if n >= 5 and n <= 20:
        return form5
    n %= 10
    if n == 1:
        return form1
    if n >= 2 and n <= 4:
        return form2
    return form5
```

**Updated Warning Message** (lines 556-557):
```python
minute_word = get_russian_plural(self.warning_minutes, "минута", "минуты", "минут")
msg.setText(f"⚠️ Внимание!\n\nДо конца сессии осталось {self.warning_minutes} {minute_word}.")
```

**Result**:
- 1 minute: "До конца сессии осталось 1 минута."
- 2 minutes: "До конца сессии осталось 2 минуты."
- 5 minutes: "До конца сессии осталось 5 минут."

## Testing

### Test Coverage
1. **test_short_session.py** (existing): 8/8 tests passing
   - Warning time calculation for various session durations
   - Session data structure validation

2. **test_warning_fix.py** (new): 20/20 tests passing
   - Russian plural forms (11 tests)
   - Warning message formatting (3 tests)
   - Short session warning logic (6 tests)

### Test Results
```
✅ ALL TESTS PASSED (28/28)
```

### Example Test Cases
```python
# Russian Plurals
get_russian_plural(1, "минута", "минуты", "минут") → "минута"
get_russian_plural(2, "минута", "минуты", "минут") → "минуты"
get_russian_plural(5, "минута", "минуты", "минут") → "минут"
get_russian_plural(21, "минута", "минуты", "минут") → "минута"

# Warning Messages
1 min session → warning at 1 min: 'До конца сессии осталось 1 минута.'
2 min session → warning at 1 min: 'До конца сессии осталось 1 минута.'
4 min session → warning at 2 min: 'До конца сессии осталось 2 минуты.'
5 min session → warning at 5 min: 'До конца сессии осталось 5 минут.'
```

## Code Quality

### Code Review
✅ No issues found

### Security Scan (CodeQL)
✅ No vulnerabilities detected

## Impact

### User Experience Improvements
1. **Accessibility**: Warning dialog is now always visible and accessible
2. **Grammar**: Correct Russian grammar for all time durations
3. **Usability**: Dialog can always be closed properly

### Technical Improvements
1. **Robustness**: Dialog positioning is now independent of widget state
2. **Maintainability**: Reusable pluralization function for future use
3. **Code Quality**: Clear separation of concerns

## Files Changed
- `src/client/gui.py`: 41 lines added/modified
  - Added `get_russian_plural()` helper function (28 lines)
  - Modified `show_warning()` method (order change)
  - Modified `show_warning_popup()` method (parent and text)
- `test_warning_fix.py`: New test file (187 lines)

## Backwards Compatibility
✅ All existing tests pass
✅ No breaking changes
✅ Configuration remains unchanged

## Manual Testing Recommendations

To verify the fix works correctly in production:

1. **Test Short Session (2 minutes)**:
   - Start a 2-minute session from server
   - Wait for 1 minute (warning should appear)
   - Verify:
     - Warning appears centered on screen
     - Text says "До конца сессии осталось 1 минута."
     - Dialog can be closed with OK button

2. **Test with Minimized Widget**:
   - Start a 4-minute session
   - Minimize the timer widget (click × button)
   - Wait for 2 minutes (warning should appear)
   - Verify:
     - Widget automatically restores to full size
     - Warning appears properly centered
     - Text says "До конца сессии осталось 2 минуты."

3. **Test Different Durations**:
   - 1 minute: "1 минута"
   - 3 minutes: "1 минута" (warning at halfway point)
   - 5 minutes: "5 минут"
   - 10 minutes: "5 минут"

## Conclusion

Both issues have been successfully resolved:
1. ✅ Warning popup is no longer clipped and can be closed properly
2. ✅ Russian grammar is correct for all time durations

The fix is minimal, well-tested, and does not introduce any breaking changes or security vulnerabilities.
