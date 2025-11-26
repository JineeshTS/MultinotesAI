#!/usr/bin/env python
"""
Security Module Demo Script

This script demonstrates all features of the security module.
Run with: python backend/security_demo.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.security import (
    APIKeyEncryption,
    SecretScanner,
    InputSanitizer,
    PasswordValidator,
    get_client_ip,
    is_safe_redirect_url,
    secure_compare,
)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_api_key_encryption():
    """Demonstrate API key encryption."""
    print_section("1. API KEY ENCRYPTION")

    # Generate a new API key
    api_key = APIKeyEncryption.generate_api_key()
    print(f"✅ Generated API key: {api_key}")

    # Encrypt the key
    encrypted = APIKeyEncryption.encrypt_api_key(api_key)
    print(f"🔒 Encrypted: {encrypted[:50]}...")

    # Decrypt the key
    decrypted = APIKeyEncryption.decrypt_api_key(encrypted)
    print(f"🔓 Decrypted: {decrypted}")

    # Verify they match
    assert api_key == decrypted, "Decryption failed!"
    print("✅ Encryption/Decryption successful!")

    # Mask for display
    masked = APIKeyEncryption.mask_api_key(api_key)
    print(f"👁️  Masked for display: {masked}")

    # Hash for verification
    hashed = APIKeyEncryption.hash_api_key(api_key)
    print(f"#️⃣  Hash (for verification): {hashed[:32]}...")


def demo_secret_scanner():
    """Demonstrate secret scanning."""
    print_section("2. SECRET SCANNER")

    # Sample code with secrets
    code_with_secrets = """
    # Configuration file
    OPENAI_API_KEY = 'sk-' + 'a' * 48
    AWS_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'
    DATABASE_URL = 'postgresql://user:secretpass123@localhost/db'
    """

    print("🔍 Scanning code for exposed secrets...")
    findings = SecretScanner.scan_text(code_with_secrets)

    if findings:
        print(f"⚠️  Found {len(findings)} potential secrets:")
        for finding in findings:
            print(f"   - Type: {finding['type']}")
            print(f"     Value: {finding['value']}")
            print(f"     Severity: {finding['severity']}")
    else:
        print("✅ No secrets detected")

    # Entropy analysis
    print("\n🧮 Entropy Analysis:")
    random_string = "xJ7k9pL2mQvR8zAbCdEf1234"
    entropy = SecretScanner.calculate_entropy(random_string)
    is_high_entropy = SecretScanner.is_high_entropy_string(random_string)
    print(f"   String: {random_string}")
    print(f"   Entropy: {entropy:.2f}")
    print(f"   High entropy: {is_high_entropy}")


def demo_input_sanitization():
    """Demonstrate input sanitization."""
    print_section("3. INPUT SANITIZATION")

    # XSS Prevention
    print("🧹 XSS Prevention:")
    xss_input = '<p>Hello</p><script>alert("XSS")</script><img onerror="alert(1)">'
    print(f"   Input: {xss_input}")

    clean = InputSanitizer.sanitize_html(xss_input, allow_safe_tags=True)
    print(f"   Cleaned: {clean}")

    # SQL Injection Detection
    print("\n💉 SQL Injection Detection:")
    sql_inputs = [
        "normal search",
        "' OR '1'='1",
        "admin'--",
    ]

    for sql_input in sql_inputs:
        try:
            InputSanitizer.check_sql_injection(sql_input)
            print(f"   ✅ Safe: {sql_input}")
        except Exception:
            print(f"   ⚠️  SQL Injection detected: {sql_input}")

    # Filename Sanitization
    print("\n📁 Filename Sanitization:")
    dirty_filename = "my<file>name?.txt"
    clean_filename = InputSanitizer.sanitize_filename(dirty_filename)
    print(f"   Input: {dirty_filename}")
    print(f"   Cleaned: {clean_filename}")


def demo_password_validation():
    """Demonstrate password validation."""
    print_section("4. PASSWORD VALIDATION")

    passwords = [
        ("weak", "Weak password"),
        ("password", "Common password"),
        ("Pass123!", "Moderate password"),
        ("Str0ng!P@ssw0rd", "Strong password"),
    ]

    print("🔑 Password Strength Analysis:\n")

    for password, description in passwords:
        result = PasswordValidator.validate_password(password)

        print(f"Password: {description}")
        print(f"   Input: {'*' * len(password)}")
        print(f"   Valid: {result['valid']}")
        print(f"   Strength: {result['strength']}")
        print(f"   Score: {result['score']}/5")

        if not result['valid']:
            print(f"   Errors: {', '.join(result['errors'][:2])}")
        print()

    # Generate secure password
    print("🎲 Generate Secure Password:")
    secure_pwd = PasswordValidator.generate_secure_password(length=16)
    print(f"   Generated: {secure_pwd}")

    result = PasswordValidator.validate_password(secure_pwd)
    print(f"   Strength: {result['strength']} (Score: {result['score']}/5)")


def demo_utility_functions():
    """Demonstrate utility functions."""
    print_section("5. UTILITY FUNCTIONS")

    # Safe redirect URL checking
    print("🔗 Safe Redirect URL Checking:")
    urls = [
        ("/dashboard", "Relative URL"),
        ("https://example.com", "Absolute URL"),
        ("javascript:alert(1)", "JavaScript URL"),
        ("//evil.com", "Protocol-relative URL"),
    ]

    for url, desc in urls:
        is_safe = is_safe_redirect_url(url)
        status = "✅ Safe" if is_safe else "⚠️  Unsafe"
        print(f"   {status}: {desc} ({url})")

    # Secure string comparison
    print("\n🔒 Timing-Safe String Comparison:")
    token1 = "secret_token_12345"
    token2 = "secret_token_12345"
    token3 = "different_token_67890"

    match1 = secure_compare(token1, token2)
    match2 = secure_compare(token1, token3)

    print(f"   '{token1}' == '{token2}': {match1}")
    print(f"   '{token1}' == '{token3}': {match2}")


def demo_comprehensive_security():
    """Demonstrate comprehensive security workflow."""
    print_section("6. COMPREHENSIVE SECURITY WORKFLOW")

    print("🛡️  Simulating secure user registration:\n")

    # 1. User inputs
    username = "john_doe"
    email = "john@example.com"
    password = "Str0ng!P@ssw0rd"

    print(f"1️⃣  User Input:")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Password: {'*' * len(password)}")

    # 2. Sanitize inputs
    print(f"\n2️⃣  Input Sanitization:")
    try:
        clean_username = InputSanitizer.sanitize_input(username)
        InputSanitizer.check_xss(clean_username)
        InputSanitizer.check_sql_injection(clean_username)
        print(f"   ✅ Username sanitized and validated")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
        return

    # 3. Validate password
    print(f"\n3️⃣  Password Validation:")
    pwd_result = PasswordValidator.validate_password(
        password,
        username=username,
        email=email
    )

    if pwd_result['valid']:
        print(f"   ✅ Password valid")
        print(f"   Strength: {pwd_result['strength']}")
        print(f"   Score: {pwd_result['score']}/5")
    else:
        print(f"   ❌ Password invalid: {pwd_result['errors']}")
        return

    # 4. Generate and encrypt API key
    print(f"\n4️⃣  API Key Generation:")
    api_key = APIKeyEncryption.generate_api_key()
    encrypted_key = APIKeyEncryption.encrypt_api_key(api_key)
    print(f"   ✅ API key generated: {APIKeyEncryption.mask_api_key(api_key)}")
    print(f"   🔒 Encrypted for storage")

    # 5. Scan for secrets
    print(f"\n5️⃣  Secret Scanning:")
    config_data = {
        'username': username,
        'email': email,
        'api_key': api_key,
    }
    findings = SecretScanner.scan_dict(config_data)
    if findings:
        print(f"   ⚠️  Detected {len(findings)} potential secrets")
        for f in findings:
            print(f"      - {f['type']}: {f['value']}")
    else:
        print(f"   ✅ No exposed secrets detected")

    print(f"\n✅ Registration workflow complete and secure!")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("  MULTINOTESAI SECURITY MODULE DEMONSTRATION")
    print("  Version 2.0")
    print("=" * 70)

    try:
        demo_api_key_encryption()
        demo_secret_scanner()
        demo_input_sanitization()
        demo_password_validation()
        demo_utility_functions()
        demo_comprehensive_security()

        print("\n" + "=" * 70)
        print("  ✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nFor more information:")
        print("  - Full documentation: backend/SECURITY_USAGE.md")
        print("  - Quick reference: backend/SECURITY_QUICKREF.md")
        print("  - Source code: backend/security.py")
        print("  - Tests: backend/test_security.py")
        print()

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
