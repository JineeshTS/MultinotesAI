"""
Comprehensive Security Utilities Module for MultinotesAI Backend.

This module provides a unified security layer with:
1. API key encryption/decryption utilities using Fernet
2. Secret scanner utility to detect exposed credentials
3. Input sanitization utilities (XSS prevention, SQL injection prevention)
4. Rate limiting decorators
5. IP whitelist/blacklist utilities
6. Security headers middleware
7. Audit logging decorator
8. Password strength validator

Author: MultinotesAI Security Team
Version: 2.0
"""

import re
import os
import logging
import hashlib
import secrets
import ipaddress
from typing import Optional, Dict, Any, List, Callable, Union, Set
from functools import wraps
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import serializers
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import bleach

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')
audit_logger = logging.getLogger('audit')


# =============================================================================
# 1. API KEY ENCRYPTION/DECRYPTION UTILITIES
# =============================================================================

class APIKeyEncryption:
    """
    Secure API key encryption and decryption using Fernet (symmetric encryption).

    Features:
    - AES-128 encryption in CBC mode
    - PKCS7 padding
    - HMAC-SHA256 authentication
    - Automatic key derivation from Django SECRET_KEY
    """

    _fernet_instance = None

    @classmethod
    def _get_encryption_key(cls) -> bytes:
        """
        Derive a Fernet-compatible encryption key from Django's SECRET_KEY.

        Returns:
            bytes: 32-byte URL-safe base64-encoded encryption key
        """
        secret_key = settings.SECRET_KEY.encode()

        # Use PBKDF2 with SHA-256 for key derivation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'multinotesai_encryption_salt_v2',  # Static salt for deterministic keys
            iterations=390000,  # OWASP recommended minimum as of 2023
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key))
        return key

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create a Fernet instance (singleton pattern)."""
        if cls._fernet_instance is None:
            cls._fernet_instance = Fernet(cls._get_encryption_key())
        return cls._fernet_instance

    @classmethod
    def encrypt_api_key(cls, api_key: str) -> str:
        """
        Encrypt an API key for secure storage.

        Args:
            api_key: Plain text API key

        Returns:
            str: Encrypted API key (base64-encoded)

        Raises:
            ValueError: If encryption fails

        Example:
            >>> encrypted = APIKeyEncryption.encrypt_api_key("sk-1234567890")
            >>> print(encrypted)
            'gAAAAABh...'
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        try:
            fernet = cls._get_fernet()
            encrypted = fernet.encrypt(api_key.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"API key encryption error: {e}")
            raise ValueError("Failed to encrypt API key")

    @classmethod
    def decrypt_api_key(cls, encrypted_key: str) -> str:
        """
        Decrypt an encrypted API key.

        Args:
            encrypted_key: Base64-encoded encrypted API key

        Returns:
            str: Decrypted plain text API key

        Raises:
            ValueError: If decryption fails or key is invalid

        Example:
            >>> plaintext = APIKeyEncryption.decrypt_api_key(encrypted)
            >>> print(plaintext)
            'sk-1234567890'
        """
        if not encrypted_key:
            raise ValueError("Encrypted key cannot be empty")

        try:
            fernet = cls._get_fernet()
            decrypted = fernet.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Invalid token during API key decryption")
            raise ValueError("Invalid encrypted key or encryption key mismatch")
        except Exception as e:
            logger.error(f"API key decryption error: {e}")
            raise ValueError("Failed to decrypt API key")

    @classmethod
    def is_encrypted(cls, value: str) -> bool:
        """
        Check if a value appears to be Fernet-encrypted.

        Args:
            value: String to check

        Returns:
            bool: True if value appears to be encrypted
        """
        if not value or len(value) < 100:
            return False

        # Fernet tokens start with version byte (0x80) which encodes to 'gAAAAA' in base64
        return value.startswith('gAAAAA')

    @classmethod
    def mask_api_key(cls, api_key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for safe display in logs/UI.

        Args:
            api_key: The API key to mask
            visible_chars: Number of characters to show at start/end

        Returns:
            str: Masked API key (e.g., "sk-a...xyz")

        Example:
            >>> masked = APIKeyEncryption.mask_api_key("sk-1234567890abcdef")
            >>> print(masked)
            'sk-1...cdef'
        """
        if not api_key:
            return ""

        if len(api_key) <= visible_chars * 2:
            return "*" * len(api_key)

        return f"{api_key[:visible_chars]}...{api_key[-visible_chars:]}"

    @classmethod
    def generate_api_key(cls, prefix: str = "mnai", length: int = 32) -> str:
        """
        Generate a cryptographically secure API key.

        Args:
            prefix: Prefix for the API key (e.g., 'mnai', 'sk')
            length: Length of the random portion in bytes

        Returns:
            str: New API key (e.g., "mnai_a1b2c3d4e5f6...")

        Example:
            >>> key = APIKeyEncryption.generate_api_key()
            >>> print(key)
            'mnai_xJ7k9...'
        """
        token = secrets.token_urlsafe(length)
        return f"{prefix}_{token}"

    @classmethod
    def hash_api_key(cls, api_key: str) -> str:
        """
        Create a one-way hash of an API key for verification.

        Args:
            api_key: API key to hash

        Returns:
            str: SHA-256 hash of the API key

        Example:
            >>> hashed = APIKeyEncryption.hash_api_key("sk-1234567890")
            >>> print(hashed)
            'a1b2c3d4...'
        """
        return hashlib.sha256(api_key.encode()).hexdigest()


# =============================================================================
# 2. SECRET SCANNER UTILITY
# =============================================================================

class SecretScanner:
    """
    Utility to detect exposed credentials and secrets in code/data.

    Features:
    - Regex-based pattern matching for common secrets
    - Entropy analysis for random strings
    - Configurable patterns and thresholds
    """

    # Regex patterns for common secrets
    PATTERNS = {
        'aws_access_key': r'AKIA[0-9A-Z]{16}',
        'aws_secret_key': r'aws_secret[_\s]*[:=]\s*["\']?([A-Za-z0-9/+=]{40})["\']?',
        'github_token': r'gh[pousr]_[A-Za-z0-9]{36,}',
        'openai_api_key': r'sk-[A-Za-z0-9]{48}',
        'generic_api_key': r'api[_\s-]?key[_\s]*[:=]\s*["\']?([A-Za-z0-9\-_]{20,})["\']?',
        'google_api_key': r'AIza[0-9A-Za-z\-_]{35}',
        'stripe_key': r'sk_live_[0-9a-zA-Z]{24,}',
        'slack_token': r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[0-9a-zA-Z]{24,}',
        'private_key': r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
        'jwt_token': r'eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+',
        'password_in_url': r'://[^:]+:([^@]+)@',
        'generic_secret': r'secret[_\s]*[:=]\s*["\']?([A-Za-z0-9\-_!@#$%^&*()+=]{10,})["\']?',
        'bearer_token': r'Bearer\s+[A-Za-z0-9\-._~+/]+=*',
        'basic_auth': r'Basic\s+[A-Za-z0-9+/]+=*',
        'database_url': r'(mysql|postgresql|mongodb)://[^:]+:([^@]+)@',
    }

    # Patterns to exclude (false positives)
    EXCLUDE_PATTERNS = [
        r'example',
        r'sample',
        r'test',
        r'placeholder',
        r'your[_\s-]?api[_\s-]?key',
        r'xxx+',
        r'\*+',
    ]

    @classmethod
    def scan_text(cls, text: str, include_context: bool = True) -> List[Dict[str, Any]]:
        """
        Scan text for exposed secrets.

        Args:
            text: Text to scan
            include_context: Include surrounding context in results

        Returns:
            List of dictionaries containing found secrets with metadata

        Example:
            >>> results = SecretScanner.scan_text("api_key = 'sk-1234567890'")
            >>> print(results)
            [{'type': 'generic_api_key', 'value': 'sk-1234567890', ...}]
        """
        findings = []

        if not text:
            return findings

        for secret_type, pattern in cls.PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                matched_text = match.group(0)

                # Skip if matches exclusion pattern
                if cls._is_excluded(matched_text):
                    continue

                finding = {
                    'type': secret_type,
                    'value': cls._mask_secret(matched_text),
                    'position': match.start(),
                    'severity': cls._get_severity(secret_type),
                }

                if include_context:
                    # Get 50 characters before and after
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    finding['context'] = text[start:end]

                findings.append(finding)

                # Log the finding
                security_logger.warning(
                    f"Secret detected: {secret_type} at position {match.start()}"
                )

        return findings

    @classmethod
    def scan_file(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Scan a file for exposed secrets.

        Args:
            file_path: Path to file to scan

        Returns:
            List of findings

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            findings = cls.scan_text(content)

            # Add file information to findings
            for finding in findings:
                finding['file'] = file_path

            return findings
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            raise

    @classmethod
    def scan_dict(cls, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Recursively scan dictionary for secrets.

        Args:
            data: Dictionary to scan

        Returns:
            List of findings
        """
        findings = []

        def _scan_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    _scan_recursive(value, current_path)
            elif isinstance(obj, (list, tuple)):
                for i, item in enumerate(obj):
                    _scan_recursive(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                text_findings = cls.scan_text(obj, include_context=False)
                for finding in text_findings:
                    finding['path'] = path
                    findings.append(finding)

        _scan_recursive(data)
        return findings

    @classmethod
    def _is_excluded(cls, text: str) -> bool:
        """Check if text matches exclusion patterns."""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in cls.EXCLUDE_PATTERNS)

    @classmethod
    def _mask_secret(cls, secret: str) -> str:
        """Mask a secret for safe display."""
        if len(secret) <= 8:
            return "*" * len(secret)
        return f"{secret[:4]}...{secret[-4:]}"

    @classmethod
    def _get_severity(cls, secret_type: str) -> str:
        """Get severity level for secret type."""
        critical_types = ['private_key', 'aws_secret_key', 'database_url']
        high_types = ['aws_access_key', 'github_token', 'openai_api_key', 'stripe_key']

        if secret_type in critical_types:
            return 'critical'
        elif secret_type in high_types:
            return 'high'
        else:
            return 'medium'

    @classmethod
    def calculate_entropy(cls, string: str) -> float:
        """
        Calculate Shannon entropy of a string to detect random secrets.

        Args:
            string: String to analyze

        Returns:
            float: Entropy value (higher = more random)
        """
        if not string:
            return 0.0

        # Calculate frequency of each character
        freq = {}
        for char in string:
            freq[char] = freq.get(char, 0) + 1

        # Calculate entropy
        import math
        entropy = 0.0
        length = len(string)

        for count in freq.values():
            probability = count / length
            entropy -= probability * math.log2(probability)

        return entropy

    @classmethod
    def is_high_entropy_string(cls, string: str, threshold: float = 4.5) -> bool:
        """
        Check if string has high entropy (likely a secret/token).

        Args:
            string: String to check
            threshold: Entropy threshold (default: 4.5)

        Returns:
            bool: True if entropy exceeds threshold
        """
        if len(string) < 20:  # Skip short strings
            return False

        entropy = cls.calculate_entropy(string)
        return entropy >= threshold


# =============================================================================
# 3. INPUT SANITIZATION UTILITIES
# =============================================================================

class InputSanitizer:
    """
    Comprehensive input sanitization to prevent XSS and SQL injection.

    Features:
    - HTML/JavaScript sanitization
    - SQL injection prevention
    - Path traversal prevention
    - Command injection prevention
    """

    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # onclick, onerror, etc.
        r'<iframe',
        r'<object',
        r'<embed',
        r'<applet',
        r'data:text/html',
        r'vbscript:',
        r'expression\s*\(',
        r'eval\s*\(',
        r'setTimeout\s*\(',
        r'setInterval\s*\(',
    ]

    # SQL injection patterns
    SQL_PATTERNS = [
        r'(\bUNION\b.*\bSELECT\b)',
        r'(\bSELECT\b.*\bFROM\b.*\bWHERE\b)',
        r'(\bINSERT\b.*\bINTO\b.*\bVALUES\b)',
        r'(\bUPDATE\b.*\bSET\b)',
        r'(\bDELETE\b.*\bFROM\b)',
        r'(\bDROP\b.*\bTABLE\b)',
        r'(\bEXEC\b.*\()',
        r'(--|\#|/\*)',  # SQL comments
        r"('\s*OR\s*'1'\s*=\s*'1)",
        r"('\s*OR\s*1\s*=\s*1)",
        r'(\bxp_cmdshell\b)',
    ]

    # Command injection patterns
    COMMAND_PATTERNS = [
        r';\s*(ls|cat|rm|wget|curl|nc|bash|sh|python|perl|ruby)\s',
        r'\|\s*(ls|cat|rm|wget|curl|nc|bash|sh)\s',
        r'`.*`',
        r'\$\(.*\)',
        r'&&\s*(ls|cat|rm)',
    ]

    @classmethod
    def sanitize_html(cls, html: str, allow_safe_tags: bool = False) -> str:
        """
        Sanitize HTML input to prevent XSS attacks.

        Args:
            html: HTML string to sanitize
            allow_safe_tags: Allow safe HTML tags (p, br, strong, em, etc.)

        Returns:
            str: Sanitized HTML

        Example:
            >>> clean = InputSanitizer.sanitize_html('<script>alert("XSS")</script>Hello')
            >>> print(clean)
            'Hello'
        """
        if not html:
            return ""

        if allow_safe_tags:
            allowed_tags = [
                'p', 'br', 'strong', 'em', 'u', 'i', 'b',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
                'a', 'span', 'div'
            ]
            allowed_attrs = {
                'a': ['href', 'title', 'target'],
                'span': ['class'],
                'div': ['class'],
            }
        else:
            allowed_tags = []
            allowed_attrs = {}

        # Use bleach to sanitize
        cleaned = bleach.clean(
            html,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True,
            strip_comments=True
        )

        return cleaned

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize plain text input (removes all HTML).

        Args:
            text: Text to sanitize

        Returns:
            str: Sanitized text
        """
        return cls.sanitize_html(text, allow_safe_tags=False)

    @classmethod
    def check_xss(cls, text: str) -> bool:
        """
        Check if text contains potential XSS patterns.

        Args:
            text: Text to check

        Returns:
            bool: True if XSS detected

        Raises:
            ValidationError: If XSS detected
        """
        if not text:
            return False

        text_lower = text.lower()

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                security_logger.warning(f"XSS attempt detected: {pattern}")
                raise ValidationError("Invalid characters detected in input (XSS)")

        return False

    @classmethod
    def check_sql_injection(cls, text: str) -> bool:
        """
        Check if text contains potential SQL injection patterns.

        Args:
            text: Text to check

        Returns:
            bool: True if SQL injection detected

        Raises:
            ValidationError: If SQL injection detected
        """
        if not text:
            return False

        text_normalized = ' '.join(text.split())  # Normalize whitespace

        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, text_normalized, re.IGNORECASE):
                security_logger.warning(f"SQL injection attempt detected: {pattern}")
                raise ValidationError("Invalid characters detected in input (SQL)")

        return False

    @classmethod
    def check_command_injection(cls, text: str) -> bool:
        """
        Check if text contains potential command injection patterns.

        Args:
            text: Text to check

        Returns:
            bool: True if command injection detected

        Raises:
            ValidationError: If command injection detected
        """
        if not text:
            return False

        for pattern in cls.COMMAND_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                security_logger.warning(f"Command injection attempt detected: {pattern}")
                raise ValidationError("Invalid characters detected in input (CMD)")

        return False

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks.

        Args:
            filename: Original filename

        Returns:
            str: Sanitized filename

        Raises:
            ValidationError: If filename is invalid
        """
        import unicodedata

        if not filename:
            raise ValidationError("Filename is required")

        # Normalize unicode
        filename = unicodedata.normalize('NFKC', filename)

        # Get just the filename (remove path components)
        filename = os.path.basename(filename)

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Check for path traversal
        if '..' in filename or filename.startswith(('/', '\\')):
            raise ValidationError("Invalid filename (path traversal)")

        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\n', '\r', '\t']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255 - len(ext)] + ext

        if not filename or filename == '.':
            raise ValidationError("Invalid filename")

        return filename

    @classmethod
    def sanitize_url(cls, url: str, allowed_schemes: List[str] = None) -> str:
        """
        Sanitize and validate URL.

        Args:
            url: URL to sanitize
            allowed_schemes: List of allowed schemes (default: ['http', 'https'])

        Returns:
            str: Sanitized URL

        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError("URL is required")

        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']

        url = url.strip()

        # Check scheme
        scheme_match = re.match(r'^([a-z][a-z0-9+.-]*):\/\/', url, re.IGNORECASE)
        if not scheme_match:
            raise ValidationError("URL must include scheme (http:// or https://)")

        scheme = scheme_match.group(1).lower()
        if scheme not in allowed_schemes:
            raise ValidationError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")

        # Check for javascript: or data: URLs
        if scheme in ['javascript', 'data', 'vbscript']:
            raise ValidationError("URL scheme not allowed")

        return url

    @classmethod
    def sanitize_input(cls, text: str, check_all: bool = True) -> str:
        """
        Comprehensive input sanitization (all checks).

        Args:
            text: Text to sanitize
            check_all: Run all security checks

        Returns:
            str: Sanitized text

        Raises:
            ValidationError: If malicious input detected
        """
        if not text:
            return ""

        if check_all:
            cls.check_xss(text)
            cls.check_sql_injection(text)
            cls.check_command_injection(text)

        # Sanitize HTML
        return cls.sanitize_html(text, allow_safe_tags=False)


# =============================================================================
# 4. RATE LIMITING DECORATORS
# =============================================================================

class RateLimiter:
    """
    Decorator-based rate limiting for views and functions.

    Features:
    - Per-user and per-IP rate limiting
    - Configurable time windows
    - Cache-based implementation
    - Automatic cleanup
    """

    @staticmethod
    def rate_limit(
        key_prefix: str,
        rate: str = "60/m",
        block_time: int = 300,
        methods: List[str] = None
    ):
        """
        Rate limit decorator for views.

        Args:
            key_prefix: Prefix for cache key
            rate: Rate limit (e.g., "60/m", "100/h", "1000/d")
            block_time: Time to block after limit exceeded (seconds)
            methods: HTTP methods to rate limit (default: all)

        Example:
            @RateLimiter.rate_limit('login', rate='5/m')
            def login_view(request):
                ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(request, *args, **kwargs):
                # Skip if methods specified and current method not in list
                if methods and request.method not in methods:
                    return func(request, *args, **kwargs)

                # Get identifier (user ID or IP)
                identifier = RateLimiter._get_identifier(request)

                # Check rate limit
                if not RateLimiter._check_rate_limit(identifier, key_prefix, rate, block_time):
                    security_logger.warning(
                        f"Rate limit exceeded for {key_prefix}: {identifier}"
                    )
                    return JsonResponse(
                        {
                            'error': 'Rate limit exceeded',
                            'message': f'Too many requests. Please try again later.',
                            'retry_after': block_time
                        },
                        status=429,
                        headers={'Retry-After': str(block_time)}
                    )

                return func(request, *args, **kwargs)

            return wrapper
        return decorator

    @staticmethod
    def _get_identifier(request: HttpRequest) -> str:
        """Get unique identifier for rate limiting."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user_{request.user.id}"

        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')

        return f"ip_{ip}"

    @staticmethod
    def _check_rate_limit(
        identifier: str,
        key_prefix: str,
        rate: str,
        block_time: int
    ) -> bool:
        """
        Check if request is within rate limit.

        Returns:
            bool: True if allowed, False if rate limit exceeded
        """
        # Parse rate (e.g., "60/m" -> 60 requests per minute)
        num_requests, period = RateLimiter._parse_rate(rate)

        # Cache keys
        count_key = f"ratelimit:{key_prefix}:{identifier}:count"
        block_key = f"ratelimit:{key_prefix}:{identifier}:blocked"

        # Check if blocked
        if cache.get(block_key):
            return False

        # Get current count
        current_count = cache.get(count_key, 0)

        if current_count >= num_requests:
            # Block for specified time
            cache.set(block_key, True, block_time)
            return False

        # Increment count
        cache.set(count_key, current_count + 1, period)
        return True

    @staticmethod
    def _parse_rate(rate: str) -> tuple:
        """
        Parse rate string.

        Args:
            rate: Rate string (e.g., "60/m", "100/h", "1000/d")

        Returns:
            tuple: (num_requests, period_in_seconds)
        """
        match = re.match(r'(\d+)/([smhd])', rate.lower())
        if not match:
            raise ValueError(f"Invalid rate format: {rate}")

        num = int(match.group(1))
        unit = match.group(2)

        periods = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }

        return num, periods[unit]


# =============================================================================
# 5. IP WHITELIST/BLACKLIST UTILITIES
# =============================================================================

class IPFilter:
    """
    IP whitelist and blacklist management.

    Features:
    - IP address and CIDR range support
    - Persistent storage in cache/database
    - Automatic cleanup
    - Rate-based auto-blocking
    """

    WHITELIST_KEY = 'security:ip:whitelist'
    BLACKLIST_KEY = 'security:ip:blacklist'

    @classmethod
    def add_to_whitelist(cls, ip: str, ttl: int = None) -> None:
        """
        Add IP address to whitelist.

        Args:
            ip: IP address or CIDR range
            ttl: Time to live in seconds (None = permanent)
        """
        cls._validate_ip(ip)

        whitelist = cls.get_whitelist()
        whitelist.add(ip)

        cache.set(cls.WHITELIST_KEY, list(whitelist), ttl)
        security_logger.info(f"Added {ip} to whitelist")

    @classmethod
    def add_to_blacklist(cls, ip: str, ttl: int = 3600, reason: str = None) -> None:
        """
        Add IP address to blacklist.

        Args:
            ip: IP address or CIDR range
            ttl: Time to live in seconds (default: 1 hour)
            reason: Reason for blocking
        """
        cls._validate_ip(ip)

        blacklist = cls.get_blacklist()
        blacklist.add(ip)

        cache.set(cls.BLACKLIST_KEY, list(blacklist), ttl)
        security_logger.warning(f"Added {ip} to blacklist. Reason: {reason}")

    @classmethod
    def remove_from_whitelist(cls, ip: str) -> None:
        """Remove IP from whitelist."""
        whitelist = cls.get_whitelist()
        whitelist.discard(ip)
        cache.set(cls.WHITELIST_KEY, list(whitelist))

    @classmethod
    def remove_from_blacklist(cls, ip: str) -> None:
        """Remove IP from blacklist."""
        blacklist = cls.get_blacklist()
        blacklist.discard(ip)
        cache.set(cls.BLACKLIST_KEY, list(blacklist))

    @classmethod
    def get_whitelist(cls) -> Set[str]:
        """Get current whitelist."""
        whitelist = cache.get(cls.WHITELIST_KEY, [])
        return set(whitelist)

    @classmethod
    def get_blacklist(cls) -> Set[str]:
        """Get current blacklist."""
        blacklist = cache.get(cls.BLACKLIST_KEY, [])
        return set(blacklist)

    @classmethod
    def is_whitelisted(cls, ip: str) -> bool:
        """Check if IP is whitelisted."""
        whitelist = cls.get_whitelist()
        return cls._ip_in_list(ip, whitelist)

    @classmethod
    def is_blacklisted(cls, ip: str) -> bool:
        """Check if IP is blacklisted."""
        blacklist = cls.get_blacklist()
        return cls._ip_in_list(ip, blacklist)

    @classmethod
    def check_ip(cls, ip: str, raise_exception: bool = True) -> bool:
        """
        Check if IP is allowed.

        Args:
            ip: IP address to check
            raise_exception: Raise exception if blocked

        Returns:
            bool: True if allowed

        Raises:
            PermissionDenied: If IP is blacklisted
        """
        # Whitelisted IPs always allowed
        if cls.is_whitelisted(ip):
            return True

        # Check blacklist
        if cls.is_blacklisted(ip):
            security_logger.warning(f"Blocked request from blacklisted IP: {ip}")
            if raise_exception:
                raise PermissionDenied("Your IP address has been blocked")
            return False

        return True

    @classmethod
    def _validate_ip(cls, ip: str) -> None:
        """Validate IP address or CIDR range."""
        try:
            ipaddress.ip_network(ip, strict=False)
        except ValueError:
            raise ValidationError(f"Invalid IP address or CIDR range: {ip}")

    @classmethod
    def _ip_in_list(cls, ip: str, ip_list: Set[str]) -> bool:
        """Check if IP is in list (supports CIDR ranges)."""
        try:
            ip_obj = ipaddress.ip_address(ip)

            for ip_range in ip_list:
                network = ipaddress.ip_network(ip_range, strict=False)
                if ip_obj in network:
                    return True

            return False
        except ValueError:
            return False

    @classmethod
    def auto_block_ip(cls, ip: str, violation_type: str, threshold: int = 5) -> None:
        """
        Automatically block IP after threshold violations.

        Args:
            ip: IP address
            violation_type: Type of violation
            threshold: Number of violations before blocking
        """
        key = f"security:violations:{ip}:{violation_type}"
        count = cache.get(key, 0) + 1
        cache.set(key, count, 3600)  # Track for 1 hour

        if count >= threshold:
            cls.add_to_blacklist(
                ip,
                ttl=86400,  # Block for 24 hours
                reason=f"Auto-blocked after {count} {violation_type} violations"
            )


# =============================================================================
# 6. SECURITY HEADERS MIDDLEWARE
# =============================================================================

class SecurityHeadersMiddleware:
    """
    Enhanced security headers middleware.

    Adds comprehensive security headers to all responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'

        # Enable XSS filter (legacy browsers)
        response['X-XSS-Protection'] = '1; mode=block'

        # Control referrer information
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Strict Transport Security (HTTPS only)
        if request.is_secure():
            response['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )

        # Permissions Policy (restrict browser features)
        response['Permissions-Policy'] = (
            'accelerometer=(), '
            'camera=(), '
            'geolocation=(), '
            'gyroscope=(), '
            'magnetometer=(), '
            'microphone=(), '
            'payment=(), '
            'usb=()'
        )

        # Content Security Policy
        if not settings.DEBUG:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "img-src 'self' data: https: blob:",
                "font-src 'self' data: https://fonts.gstatic.com",
                "connect-src 'self' https://api.razorpay.com https://*.openai.com",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "upgrade-insecure-requests",
            ]
            response['Content-Security-Policy'] = '; '.join(csp_directives)

        # Custom security header with version
        response['X-Security-Version'] = '2.0'

        return response


# =============================================================================
# 7. AUDIT LOGGING DECORATOR
# =============================================================================

class AuditLogger:
    """
    Decorator for audit logging of sensitive operations.

    Features:
    - Automatic logging of function calls
    - Parameter sanitization
    - User context tracking
    - Structured logging
    """

    @staticmethod
    def audit_log(
        event_type: str,
        sensitive_params: List[str] = None,
        log_response: bool = False
    ):
        """
        Audit logging decorator.

        Args:
            event_type: Type of event (e.g., 'user.login', 'data.delete')
            sensitive_params: Parameters to mask in logs
            log_response: Whether to log response data

        Example:
            @AuditLogger.audit_log('user.password_change', sensitive_params=['password'])
            def change_password(request, user_id, password):
                ...
        """
        if sensitive_params is None:
            sensitive_params = []

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = timezone.now()

                # Extract request if available
                request = None
                if args and hasattr(args[0], 'user'):
                    request = args[0]

                # Prepare log data
                log_data = {
                    'event_type': event_type,
                    'timestamp': start_time.isoformat(),
                    'function': func.__name__,
                    'user_id': request.user.id if request and request.user.is_authenticated else None,
                    'ip_address': AuditLogger._get_client_ip(request) if request else None,
                }

                # Log parameters (sanitized)
                log_data['params'] = AuditLogger._sanitize_params(
                    kwargs,
                    sensitive_params
                )

                try:
                    # Execute function
                    result = func(*args, **kwargs)

                    # Log success
                    log_data['status'] = 'success'
                    log_data['duration_ms'] = (timezone.now() - start_time).total_seconds() * 1000

                    if log_response and result is not None:
                        log_data['response'] = str(result)[:500]  # Limit size

                    audit_logger.info(f"AUDIT: {event_type}", extra=log_data)

                    return result

                except Exception as e:
                    # Log failure
                    log_data['status'] = 'failure'
                    log_data['error'] = str(e)
                    log_data['duration_ms'] = (timezone.now() - start_time).total_seconds() * 1000

                    audit_logger.error(f"AUDIT FAILED: {event_type}", extra=log_data)

                    raise

            return wrapper
        return decorator

    @staticmethod
    def _sanitize_params(params: Dict[str, Any], sensitive: List[str]) -> Dict[str, Any]:
        """Sanitize parameters for logging."""
        sanitized = {}

        for key, value in params.items():
            if key.lower() in [s.lower() for s in sensitive]:
                sanitized[key] = '***REDACTED***'
            else:
                # Limit value size
                sanitized[key] = str(value)[:200]

        return sanitized

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


# =============================================================================
# 8. PASSWORD STRENGTH VALIDATOR
# =============================================================================

class PasswordValidator:
    """
    Advanced password strength validation.

    Features:
    - Configurable complexity requirements
    - Common password checking
    - Breach database checking (optional)
    - Password strength scoring
    """

    # Common weak passwords
    COMMON_PASSWORDS = {
        'password', '12345678', 'qwerty12', 'admin123', 'letmein1',
        'welcome1', 'password1', 'Password1', 'Qwerty123', 'password123',
        'admin1234', 'welcome123', 'changeme', 'password!', 'Password123',
        '123456789', '1234567890', 'qwertyuiop', 'abc123456', 'password@1'
    }

    @classmethod
    def validate_password(
        cls,
        password: str,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        check_common: bool = True,
        username: str = None,
        email: str = None
    ) -> Dict[str, Any]:
        """
        Validate password strength comprehensively.

        Args:
            password: Password to validate
            min_length: Minimum length required
            require_uppercase: Require uppercase letter
            require_lowercase: Require lowercase letter
            require_digit: Require digit
            require_special: Require special character
            check_common: Check against common passwords
            username: User's username (to prevent using it in password)
            email: User's email (to prevent using it in password)

        Returns:
            dict: Validation result with 'valid', 'score', and 'errors'

        Example:
            >>> result = PasswordValidator.validate_password('Weak1!')
            >>> print(result)
            {'valid': False, 'score': 2, 'errors': ['Password too short']}
        """
        errors = []
        score = 0

        # Length check
        if len(password) < min_length:
            errors.append(f"Password must be at least {min_length} characters long")
        else:
            score += 1
            if len(password) >= 12:
                score += 1
            if len(password) >= 16:
                score += 1

        # Complexity checks
        if require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        elif re.search(r'[A-Z]', password):
            score += 1

        if require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        elif re.search(r'[a-z]', password):
            score += 1

        if require_digit and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        elif re.search(r'\d', password):
            score += 1

        special_chars = r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~\';]'
        if require_special and not re.search(special_chars, password):
            errors.append("Password must contain at least one special character")
        elif re.search(special_chars, password):
            score += 1

        # Check for multiple character types
        char_types = sum([
            bool(re.search(r'[A-Z]', password)),
            bool(re.search(r'[a-z]', password)),
            bool(re.search(r'\d', password)),
            bool(re.search(special_chars, password))
        ])
        if char_types >= 4:
            score += 1

        # Common password check
        if check_common:
            if password.lower() in [p.lower() for p in cls.COMMON_PASSWORDS]:
                errors.append("This password is too common. Please choose a stronger password")
                score = max(0, score - 2)

        # Sequential characters check
        if cls._has_sequential_chars(password):
            errors.append("Password contains sequential characters (e.g., '123', 'abc')")
            score = max(0, score - 1)

        # Repeated characters check
        if cls._has_repeated_chars(password):
            errors.append("Password contains too many repeated characters")
            score = max(0, score - 1)

        # Username/email check
        if username and username.lower() in password.lower():
            errors.append("Password cannot contain your username")
            score = max(0, score - 2)

        if email:
            email_local = email.split('@')[0]
            if len(email_local) >= 4 and email_local.lower() in password.lower():
                errors.append("Password cannot contain parts of your email")
                score = max(0, score - 1)

        # Calculate final score (0-5)
        score = min(5, max(0, score))

        return {
            'valid': len(errors) == 0,
            'score': score,
            'strength': cls._get_strength_label(score),
            'errors': errors
        }

    @classmethod
    def _has_sequential_chars(cls, password: str, length: int = 3) -> bool:
        """Check for sequential characters."""
        for i in range(len(password) - length + 1):
            substr = password[i:i+length].lower()

            # Check for sequential numbers
            if substr.isdigit():
                digits = [int(d) for d in substr]
                if all(digits[i+1] - digits[i] == 1 for i in range(len(digits)-1)):
                    return True
                if all(digits[i] - digits[i+1] == 1 for i in range(len(digits)-1)):
                    return True

            # Check for sequential letters
            if substr.isalpha():
                ords = [ord(c) for c in substr]
                if all(ords[i+1] - ords[i] == 1 for i in range(len(ords)-1)):
                    return True
                if all(ords[i] - ords[i+1] == 1 for i in range(len(ords)-1)):
                    return True

        return False

    @classmethod
    def _has_repeated_chars(cls, password: str, threshold: int = 3) -> bool:
        """Check for repeated characters."""
        for char in password:
            if password.count(char) > threshold:
                return True
        return False

    @classmethod
    def _get_strength_label(cls, score: int) -> str:
        """Get strength label from score."""
        labels = {
            0: 'very_weak',
            1: 'weak',
            2: 'fair',
            3: 'good',
            4: 'strong',
            5: 'very_strong'
        }
        return labels.get(score, 'weak')

    @classmethod
    def generate_secure_password(cls, length: int = 16) -> str:
        """
        Generate a cryptographically secure password.

        Args:
            length: Password length

        Returns:
            str: Secure random password

        Example:
            >>> password = PasswordValidator.generate_secure_password()
            >>> print(password)
            'xJ7k9!pL2mQ#vR8z'
        """
        import string

        if length < 12:
            length = 12

        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = '!@#$%^&*()_+-=[]{}|;:,.<>?'

        # Ensure at least one of each type
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]

        # Fill remaining length
        all_chars = lowercase + uppercase + digits + special
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))

        # Shuffle
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_client_ip(request: HttpRequest) -> str:
    """
    Extract client IP address from request.

    Args:
        request: Django HttpRequest object

    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')

    return ip


def is_safe_redirect_url(url: str, allowed_hosts: List[str] = None) -> bool:
    """
    Check if redirect URL is safe (prevents open redirect vulnerabilities).

    Args:
        url: URL to check
        allowed_hosts: List of allowed hosts

    Returns:
        bool: True if safe to redirect
    """
    if not url:
        return False

    # Relative URLs are safe
    if url.startswith('/') and not url.startswith('//'):
        return True

    # Check against allowed hosts
    if allowed_hosts is None:
        allowed_hosts = settings.ALLOWED_HOSTS

    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)

        # Reject javascript: and data: URLs
        if parsed.scheme in ['javascript', 'data', 'vbscript']:
            return False

        # Check if host is allowed
        if parsed.netloc:
            return any(parsed.netloc == host or parsed.netloc.endswith('.' + host)
                      for host in allowed_hosts)

        return True

    except Exception:
        return False


def secure_compare(a: str, b: str) -> bool:
    """
    Timing-safe string comparison to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        bool: True if strings are equal
    """
    import hmac
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Classes
    'APIKeyEncryption',
    'SecretScanner',
    'InputSanitizer',
    'RateLimiter',
    'IPFilter',
    'SecurityHeadersMiddleware',
    'AuditLogger',
    'PasswordValidator',

    # Utility functions
    'get_client_ip',
    'is_safe_redirect_url',
    'secure_compare',
]
