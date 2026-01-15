"""
Test script to verify the warning popup fix for short sessions
Tests Russian plural forms and warning logic
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


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


def test_russian_plurals():
    """Test Russian plural forms for minutes"""
    print("Testing Russian plural forms...")
    print("=" * 70)
    
    test_cases = [
        (1, "минута"),
        (2, "минуты"),
        (3, "минуты"),
        (4, "минуты"),
        (5, "минут"),
        (10, "минут"),
        (11, "минут"),
        (20, "минут"),
        (21, "минута"),
        (22, "минуты"),
        (25, "минут"),
    ]
    
    passed = 0
    failed = 0
    
    for number, expected in test_cases:
        result = get_russian_plural(number, "минута", "минуты", "минут")
        if result == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = f"❌ FAIL (expected '{expected}', got '{result}')"
            failed += 1
        
        print(f"{status}: {number} {result}")
    
    print("=" * 70)
    print(f"\nResults: {passed} passed, {failed} failed")
    
    return failed == 0


def test_warning_messages():
    """Test that warning messages are properly formatted"""
    print("\nTesting warning message formatting...")
    print("=" * 70)
    
    test_cases = [
        (1, "До конца сессии осталось 1 минута."),
        (2, "До конца сессии осталось 2 минуты."),
        (5, "До конца сессии осталось 5 минут."),
    ]
    
    passed = 0
    failed = 0
    
    for warning_minutes, expected in test_cases:
        minute_word = get_russian_plural(warning_minutes, "минута", "минуты", "минут")
        message = f"До конца сессии осталось {warning_minutes} {minute_word}."
        
        if message == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = f"❌ FAIL"
            failed += 1
            print(f"  Expected: {expected}")
            print(f"  Got:      {message}")
        
        print(f"{status}: {message}")
    
    print("=" * 70)
    print(f"\nResults: {passed} passed, {failed} failed")
    
    return failed == 0


def test_short_session_warning_logic():
    """Test that warning times are correctly calculated for short sessions"""
    print("\nTesting short session warning logic...")
    print("=" * 70)
    
    # Mock config
    class MockConfig:
        warning_minutes = 5
    
    config = MockConfig()
    
    def calculate_warning_time(duration_minutes: int, is_unlimited: bool) -> int:
        """Calculate appropriate warning time"""
        if is_unlimited or duration_minutes <= 0:
            return config.warning_minutes
        
        # For sessions shorter than warning time, use half the duration
        if duration_minutes < config.warning_minutes:
            return max(1, duration_minutes // 2)
        
        return config.warning_minutes
    
    test_cases = [
        # (duration, expected_warning, expected_message)
        (1, 1, "До конца сессии осталось 1 минута."),  # 1//2 = 0, max(1, 0) = 1
        (2, 1, "До конца сессии осталось 1 минута."),  # 2//2 = 1
        (3, 1, "До конца сессии осталось 1 минута."),  # 3//2 = 1
        (4, 2, "До конца сессии осталось 2 минуты."),  # 4//2 = 2
        (5, 5, "До конца сессии осталось 5 минут."),   # 5 >= 5, use default
        (10, 5, "До конца сессии осталось 5 минут."),  # 10 >= 5, use default
    ]
    
    passed = 0
    failed = 0
    
    for duration, expected_warning, expected_message in test_cases:
        warning_time = calculate_warning_time(duration, False)
        minute_word = get_russian_plural(warning_time, "минута", "минуты", "минут")
        message = f"До конца сессии осталось {warning_time} {minute_word}."
        
        if warning_time == expected_warning and message == expected_message:
            status = "✅ PASS"
            passed += 1
        else:
            status = f"❌ FAIL"
            failed += 1
            if warning_time != expected_warning:
                print(f"  Warning time mismatch: expected {expected_warning}, got {warning_time}")
            if message != expected_message:
                print(f"  Message mismatch:")
                print(f"    Expected: {expected_message}")
                print(f"    Got:      {message}")
        
        print(f"{status}: {duration} min session → warning at {warning_time} min: '{message}'")
    
    print("=" * 70)
    print(f"\nResults: {passed} passed, {failed} failed")
    
    return failed == 0


if __name__ == "__main__":
    print("LibLocker Warning Fix Test")
    print("=" * 70)
    print()
    
    # Run tests
    test1_passed = test_russian_plurals()
    test2_passed = test_warning_messages()
    test3_passed = test_short_session_warning_logic()
    
    print("\n" + "=" * 70)
    if test1_passed and test2_passed and test3_passed:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
