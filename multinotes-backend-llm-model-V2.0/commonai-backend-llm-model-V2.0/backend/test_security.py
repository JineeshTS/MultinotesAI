"""
Test suite for security utilities module.

This file demonstrates usage of all security features and includes
unit tests for validation.

Run tests with:
    python manage.py test backend.test_security
"""

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework import serializers

from .security import (
    APIKeyEncryption,
    SecretScanner,
    InputSanitizer,
    RateLimiter,
    IPFilter,
    AuditLogger,
    PasswordValidator,
    get_client_ip,
    is_safe_redirect_url,
    secure_compare,
)

User = get_user_model()


# =============================================================================
# API Key Encryption Tests
# =============================================================================

class APIKeyEncryptionTestCase(TestCase):
    """Test API key encryption/decryption."""

    def test_encrypt_decrypt_api_key(self):
        """Test basic encryption and decryption."""
        original_key = "sk-1234567890abcdef"

        # Encrypt
        encrypted = APIKeyEncryption.encrypt_api_key(original_key)
        self.assertNotEqual(original_key, encrypted)
        self.assertTrue(APIKeyEncryption.is_encrypted(encrypted))

        # Decrypt
        decrypted = APIKeyEncryption.decrypt_api_key(encrypted)
        self.assertEqual(original_key, decrypted)

    def test_is_encrypted_detection(self):
        """Test encrypted value detection."""
        plain_text = "sk-1234567890"
        encrypted = APIKeyEncryption.encrypt_api_key(plain_text)

        self.assertFalse(APIKeyEncryption.is_encrypted(plain_text))
        self.assertTrue(APIKeyEncryption.is_encrypted(encrypted))

    def test_mask_api_key(self):
        """Test API key masking."""
        api_key = "sk-1234567890abcdef"
        masked = APIKeyEncryption.mask_api_key(api_key)

        self.assertIn("...", masked)
        self.assertNotEqual(api_key, masked)
        self.assertTrue(masked.startswith("sk-1"))
        self.assertTrue(masked.endswith("cdef"))

    def test_generate_api_key(self):
        """Test API key generation."""
        key1 = APIKeyEncryption.generate_api_key()
        key2 = APIKeyEncryption.generate_api_key()

        self.assertTrue(key1.startswith("mnai_"))
        self.assertNotEqual(key1, key2)
        self.assertGreater(len(key1), 40)

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "sk-1234567890"
        hash1 = APIKeyEncryption.hash_api_key(api_key)
        hash2 = APIKeyEncryption.hash_api_key(api_key)

        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA-256 hex

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        with self.assertRaises(ValueError):
            APIKeyEncryption.encrypt_api_key("")

    def test_decrypt_invalid_token(self):
        """Test decryption of invalid token."""
        with self.assertRaises(ValueError):
            APIKeyEncryption.decrypt_api_key("invalid_token")


# =============================================================================
# Secret Scanner Tests
# =============================================================================

class SecretScannerTestCase(TestCase):
    """Test secret detection."""

    def test_detect_openai_key(self):
        """Test detection of OpenAI API key."""
        text = "My API key is sk-" + "a" * 48
        findings = SecretScanner.scan_text(text)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['type'], 'openai_api_key')
        self.assertEqual(findings[0]['severity'], 'high')

    def test_detect_aws_key(self):
        """Test detection of AWS credentials."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        findings = SecretScanner.scan_text(text)

        self.assertGreater(len(findings), 0)
        self.assertTrue(any(f['type'] == 'aws_access_key' for f in findings))

    def test_detect_private_key(self):
        """Test detection of private key."""
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."
        findings = SecretScanner.scan_text(text)

        self.assertGreater(len(findings), 0)
        self.assertTrue(any(f['type'] == 'private_key' for f in findings))
        self.assertTrue(any(f['severity'] == 'critical' for f in findings))

    def test_detect_generic_api_key(self):
        """Test detection of generic API key."""
        text = "api_key = 'abcdef1234567890ghijklmn'"
        findings = SecretScanner.scan_text(text)

        self.assertGreater(len(findings), 0)

    def test_exclude_false_positives(self):
        """Test exclusion of false positives."""
        text = "api_key = 'your_api_key_here'"
        findings = SecretScanner.scan_text(text)

        self.assertEqual(len(findings), 0)

    def test_entropy_calculation(self):
        """Test entropy calculation."""
        # High entropy string (random)
        high_entropy = "xJ7k9!pL2mQ#vR8z"
        entropy1 = SecretScanner.calculate_entropy(high_entropy)

        # Low entropy string (repeated)
        low_entropy = "aaaaaaaaaaaaaaaa"
        entropy2 = SecretScanner.calculate_entropy(low_entropy)

        self.assertGreater(entropy1, entropy2)

    def test_high_entropy_detection(self):
        """Test high entropy string detection."""
        random_token = "xJ7k9pL2mQvR8zAbCdEf1234"
        self.assertTrue(SecretScanner.is_high_entropy_string(random_token))

        simple_string = "password"
        self.assertFalse(SecretScanner.is_high_entropy_string(simple_string))

    def test_scan_dictionary(self):
        """Test scanning dictionary for secrets."""
        data = {
            'username': 'john',
            'api_key': 'sk-' + 'a' * 48,
            'nested': {
                'aws_key': 'AKIAIOSFODNN7EXAMPLE'
            }
        }

        findings = SecretScanner.scan_dict(data)
        self.assertGreater(len(findings), 0)


# =============================================================================
# Input Sanitization Tests
# =============================================================================

class InputSanitizerTestCase(TestCase):
    """Test input sanitization."""

    def test_sanitize_html_xss(self):
        """Test XSS removal from HTML."""
        malicious = '<script>alert("XSS")</script>Hello'
        clean = InputSanitizer.sanitize_html(malicious)

        self.assertNotIn('<script>', clean)
        self.assertIn('Hello', clean)

    def test_sanitize_html_with_safe_tags(self):
        """Test HTML sanitization preserving safe tags."""
        html = '<p>Hello</p><script>alert("XSS")</script>'
        clean = InputSanitizer.sanitize_html(html, allow_safe_tags=True)

        self.assertIn('<p>Hello</p>', clean)
        self.assertNotIn('<script>', clean)

    def test_check_xss_detection(self):
        """Test XSS pattern detection."""
        xss_inputs = [
            '<script>alert("XSS")</script>',
            'javascript:alert("XSS")',
            '<img onerror="alert(1)">',
            '<iframe src="evil.com">',
        ]

        for xss in xss_inputs:
            with self.assertRaises(ValidationError):
                InputSanitizer.check_xss(xss)

    def test_check_sql_injection(self):
        """Test SQL injection detection."""
        sql_injections = [
            "' OR '1'='1",
            "1; DROP TABLE users--",
            "UNION SELECT * FROM passwords",
            "admin'--",
        ]

        for sql in sql_injections:
            with self.assertRaises(ValidationError):
                InputSanitizer.check_sql_injection(sql)

    def test_check_command_injection(self):
        """Test command injection detection."""
        cmd_injections = [
            "; ls -la",
            "| cat /etc/passwd",
            "`whoami`",
            "$(rm -rf /)",
        ]

        for cmd in cmd_injections:
            with self.assertRaises(ValidationError):
                InputSanitizer.check_command_injection(cmd)

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test path traversal prevention
        with self.assertRaises(ValidationError):
            InputSanitizer.sanitize_filename("../../etc/passwd")

        # Test dangerous character removal
        dirty = "my<file>name?.txt"
        clean = InputSanitizer.sanitize_filename(dirty)
        self.assertNotIn('<', clean)
        self.assertNotIn('>', clean)
        self.assertNotIn('?', clean)

        # Test normal filename
        normal = "document.pdf"
        clean = InputSanitizer.sanitize_filename(normal)
        self.assertEqual(normal, clean)

    def test_sanitize_url(self):
        """Test URL sanitization."""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://localhost:8000",
        ]

        for url in valid_urls:
            clean = InputSanitizer.sanitize_url(url)
            self.assertEqual(url, clean)

        # Invalid URLs
        invalid_urls = [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "not-a-url",
        ]

        for url in invalid_urls:
            with self.assertRaises(ValidationError):
                InputSanitizer.sanitize_url(url)

    def test_sanitize_input_comprehensive(self):
        """Test comprehensive input sanitization."""
        malicious = '<script>alert("XSS")</script>Hello'
        clean = InputSanitizer.sanitize_input(malicious)

        self.assertNotIn('<script>', clean)
        self.assertIn('Hello', clean)


# =============================================================================
# IP Filter Tests
# =============================================================================

class IPFilterTestCase(TestCase):
    """Test IP whitelist/blacklist."""

    def setUp(self):
        """Clear IP lists before each test."""
        from django.core.cache import cache
        cache.delete(IPFilter.WHITELIST_KEY)
        cache.delete(IPFilter.BLACKLIST_KEY)

    def test_add_to_whitelist(self):
        """Test adding IP to whitelist."""
        ip = "192.168.1.100"
        IPFilter.add_to_whitelist(ip)

        self.assertTrue(IPFilter.is_whitelisted(ip))
        self.assertFalse(IPFilter.is_blacklisted(ip))

    def test_add_to_blacklist(self):
        """Test adding IP to blacklist."""
        ip = "10.0.0.1"
        IPFilter.add_to_blacklist(ip, reason="Suspicious activity")

        self.assertTrue(IPFilter.is_blacklisted(ip))
        self.assertFalse(IPFilter.is_whitelisted(ip))

    def test_cidr_range_whitelist(self):
        """Test CIDR range in whitelist."""
        IPFilter.add_to_whitelist("192.168.1.0/24")

        self.assertTrue(IPFilter.is_whitelisted("192.168.1.100"))
        self.assertTrue(IPFilter.is_whitelisted("192.168.1.200"))
        self.assertFalse(IPFilter.is_whitelisted("192.168.2.100"))

    def test_cidr_range_blacklist(self):
        """Test CIDR range in blacklist."""
        IPFilter.add_to_blacklist("10.0.0.0/8")

        self.assertTrue(IPFilter.is_blacklisted("10.0.0.1"))
        self.assertTrue(IPFilter.is_blacklisted("10.255.255.255"))
        self.assertFalse(IPFilter.is_blacklisted("11.0.0.1"))

    def test_check_ip_allowed(self):
        """Test IP check for allowed IP."""
        ip = "192.168.1.100"
        result = IPFilter.check_ip(ip, raise_exception=False)
        self.assertTrue(result)

    def test_check_ip_blocked(self):
        """Test IP check for blocked IP."""
        ip = "10.0.0.1"
        IPFilter.add_to_blacklist(ip)

        with self.assertRaises(PermissionDenied):
            IPFilter.check_ip(ip, raise_exception=True)

    def test_whitelist_overrides_blacklist(self):
        """Test that whitelist takes precedence."""
        ip = "192.168.1.100"

        IPFilter.add_to_blacklist(ip)
        IPFilter.add_to_whitelist(ip)

        result = IPFilter.check_ip(ip, raise_exception=False)
        self.assertTrue(result)

    def test_auto_block_ip(self):
        """Test automatic IP blocking after violations."""
        ip = "10.0.0.1"

        # Simulate violations
        for _ in range(5):
            IPFilter.auto_block_ip(ip, 'login_failure', threshold=5)

        self.assertTrue(IPFilter.is_blacklisted(ip))


# =============================================================================
# Password Validator Tests
# =============================================================================

class PasswordValidatorTestCase(TestCase):
    """Test password validation."""

    def test_validate_strong_password(self):
        """Test validation of strong password."""
        password = "Str0ng!P@ssw0rd"
        result = PasswordValidator.validate_password(password)

        self.assertTrue(result['valid'])
        self.assertGreaterEqual(result['score'], 3)

    def test_validate_weak_password(self):
        """Test validation of weak password."""
        password = "weak"
        result = PasswordValidator.validate_password(password)

        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)

    def test_reject_common_password(self):
        """Test rejection of common passwords."""
        common_passwords = ['password', 'password1', 'Password1', '12345678']

        for password in common_passwords:
            result = PasswordValidator.validate_password(password)
            self.assertFalse(result['valid'])

    def test_detect_sequential_characters(self):
        """Test detection of sequential characters."""
        passwords_with_sequential = [
            'Abc123!Pass',  # Sequential numbers
            'Xyz789!Word',  # Sequential letters
        ]

        for password in passwords_with_sequential:
            result = PasswordValidator.validate_password(password)
            self.assertGreater(len(result['errors']), 0)

    def test_reject_password_with_username(self):
        """Test rejection of password containing username."""
        result = PasswordValidator.validate_password(
            'john1234!A',
            username='john'
        )

        self.assertFalse(result['valid'])
        self.assertTrue(any('username' in err.lower() for err in result['errors']))

    def test_reject_password_with_email(self):
        """Test rejection of password containing email."""
        result = PasswordValidator.validate_password(
            'john.doe123!A',
            email='john.doe@example.com'
        )

        self.assertFalse(result['valid'])

    def test_password_strength_scoring(self):
        """Test password strength scoring."""
        passwords = [
            ('weak', 0),
            ('Weak123!', 2),
            ('Str0ng!P@ss', 3),
            ('V3ry$tr0ng!P@ssw0rd', 4),
        ]

        for password, min_expected_score in passwords:
            result = PasswordValidator.validate_password(password)
            # Score should be at least the expected minimum
            self.assertGreaterEqual(result['score'], min_expected_score)

    def test_generate_secure_password(self):
        """Test secure password generation."""
        password = PasswordValidator.generate_secure_password()

        # Should be strong
        result = PasswordValidator.validate_password(password)
        self.assertTrue(result['valid'])
        self.assertGreaterEqual(result['score'], 4)

        # Should be unique
        password2 = PasswordValidator.generate_secure_password()
        self.assertNotEqual(password, password2)


# =============================================================================
# Utility Function Tests
# =============================================================================

class UtilityFunctionTestCase(TestCase):
    """Test utility functions."""

    def setUp(self):
        """Set up test request factory."""
        self.factory = RequestFactory()

    def test_get_client_ip_direct(self):
        """Test getting client IP from direct connection."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'

        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')

    def test_get_client_ip_forwarded(self):
        """Test getting client IP from X-Forwarded-For header."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '10.0.0.1')

    def test_is_safe_redirect_url_relative(self):
        """Test safe redirect for relative URLs."""
        self.assertTrue(is_safe_redirect_url('/dashboard'))
        self.assertTrue(is_safe_redirect_url('/api/users'))
        self.assertFalse(is_safe_redirect_url('//evil.com'))

    def test_is_safe_redirect_url_javascript(self):
        """Test rejection of javascript: URLs."""
        self.assertFalse(is_safe_redirect_url('javascript:alert(1)'))
        self.assertFalse(is_safe_redirect_url('data:text/html,<script>'))

    def test_secure_compare(self):
        """Test timing-safe string comparison."""
        self.assertTrue(secure_compare('secret123', 'secret123'))
        self.assertFalse(secure_compare('secret123', 'secret456'))
        self.assertFalse(secure_compare('short', 'longer_string'))


# =============================================================================
# Integration Tests
# =============================================================================

class SecurityIntegrationTestCase(TestCase):
    """Integration tests for security components."""

    def test_full_password_workflow(self):
        """Test complete password security workflow."""
        # Generate secure password
        password = PasswordValidator.generate_secure_password()

        # Validate it
        result = PasswordValidator.validate_password(password)
        self.assertTrue(result['valid'])

        # Encrypt API key
        api_key = APIKeyEncryption.generate_api_key()
        encrypted = APIKeyEncryption.encrypt_api_key(api_key)

        # Decrypt and verify
        decrypted = APIKeyEncryption.decrypt_api_key(encrypted)
        self.assertEqual(api_key, decrypted)

    def test_input_sanitization_workflow(self):
        """Test input sanitization workflow."""
        malicious_input = '<script>alert("XSS")</script>Hello World'

        # Sanitize
        clean = InputSanitizer.sanitize_input(malicious_input)

        # Verify clean
        self.assertNotIn('<script>', clean)
        self.assertIn('Hello World', clean)

        # Should pass XSS check now
        try:
            InputSanitizer.check_xss(clean)
            passed = True
        except ValidationError:
            passed = False

        self.assertTrue(passed)

    def test_security_layering(self):
        """Test multiple security layers working together."""
        # 1. Validate password
        password = "Str0ng!P@ssw0rd"
        pwd_result = PasswordValidator.validate_password(password)
        self.assertTrue(pwd_result['valid'])

        # 2. Sanitize input
        user_input = "Hello <script>alert('xss')</script>"
        clean_input = InputSanitizer.sanitize_input(user_input)
        self.assertNotIn('<script>', clean_input)

        # 3. Encrypt sensitive data
        api_key = "sk-1234567890"
        encrypted = APIKeyEncryption.encrypt_api_key(api_key)
        self.assertTrue(APIKeyEncryption.is_encrypted(encrypted))

        # 4. Scan for secrets
        code = "api_key = 'sk-" + "a" * 48 + "'"
        findings = SecretScanner.scan_text(code)
        self.assertGreater(len(findings), 0)


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == '__main__':
    import django
    django.setup()
    pytest.main([__file__, '-v'])
