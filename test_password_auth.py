"""
Test password authentication functionality
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shared.utils import hash_password, verify_password


def test_password_hashing():
    """Test that password hashing works correctly"""
    password = "test_password_123"
    hashed = hash_password(password)
    
    # Check that hash is not empty
    assert hashed, "Password hash should not be empty"
    
    # Check that hash is different from original password
    assert hashed != password, "Hash should be different from password"
    
    print("✓ Password hashing works correctly")


def test_password_verification():
    """Test that password verification works correctly"""
    password = "secure_password_456"
    wrong_password = "wrong_password"
    
    hashed = hash_password(password)
    
    # Correct password should verify
    assert verify_password(password, hashed), "Correct password should verify"
    
    # Wrong password should not verify
    assert not verify_password(wrong_password, hashed), "Wrong password should not verify"
    
    print("✓ Password verification works correctly")


def test_multiple_hashes():
    """Test that same password produces different hashes (salt)"""
    password = "same_password"
    
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    
    # Hashes should be different (due to salt)
    assert hash1 != hash2, "Same password should produce different hashes"
    
    # But both should verify
    assert verify_password(password, hash1), "Password should verify with first hash"
    assert verify_password(password, hash2), "Password should verify with second hash"
    
    print("✓ Multiple hashes work correctly (salt is used)")


if __name__ == "__main__":
    print("Testing password authentication...")
    print()
    
    try:
        test_password_hashing()
        test_password_verification()
        test_multiple_hashes()
        
        print()
        print("=" * 50)
        print("All password authentication tests passed! ✅")
        print("=" * 50)
    except AssertionError as e:
        print()
        print("=" * 50)
        print(f"Test failed: {e} ❌")
        print("=" * 50)
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 50)
        print(f"Error during testing: {e} ❌")
        print("=" * 50)
        sys.exit(1)
