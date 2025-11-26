"""
Encryption utilities for securing sensitive data.

This module provides encryption/decryption functions for:
- API keys
- User credentials
- Sensitive configuration data
"""

import base64
import hashlib
import secrets
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Key Derivation
# =============================================================================

def get_encryption_key() -> bytes:
    """
    Derive an encryption key from Django's SECRET_KEY.

    Returns:
        bytes: 32-byte encryption key suitable for Fernet
    """
    secret_key = settings.SECRET_KEY.encode()

    # Use PBKDF2 to derive a key from SECRET_KEY
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'multinotesai_encryption_salt',  # Static salt for deterministic keys
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key))
    return key


def get_fernet() -> Fernet:
    """Get a Fernet instance with the derived key."""
    return Fernet(get_encryption_key())


# =============================================================================
# Encryption Functions
# =============================================================================

def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a string value.

    Args:
        plaintext: The string to encrypt

    Returns:
        str: Base64-encoded encrypted string

    Example:
        encrypted = encrypt_value("my-api-key-12345")
    """
    if not plaintext:
        return ""

    try:
        fernet = get_fernet()
        encrypted = fernet.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise ValueError("Failed to encrypt value")


def decrypt_value(encrypted: str) -> str:
    """
    Decrypt an encrypted string value.

    Args:
        encrypted: Base64-encoded encrypted string

    Returns:
        str: Decrypted plaintext string

    Example:
        plaintext = decrypt_value(encrypted_key)
    """
    if not encrypted:
        return ""

    try:
        fernet = get_fernet()
        decrypted = fernet.decrypt(encrypted.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.error("Invalid token during decryption - key may have changed")
        raise ValueError("Invalid encrypted value or key mismatch")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise ValueError("Failed to decrypt value")


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be encrypted (Fernet format).

    Args:
        value: String to check

    Returns:
        bool: True if value appears to be Fernet-encrypted
    """
    if not value:
        return False

    try:
        # Fernet tokens are base64-encoded and start with 'gAAAAA'
        return value.startswith('gAAAAA') and len(value) > 100
    except Exception:
        return False


# =============================================================================
# API Key Management
# =============================================================================

def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for secure storage.

    Args:
        api_key: Plain text API key

    Returns:
        str: Encrypted API key
    """
    if is_encrypted(api_key):
        # Already encrypted, return as-is
        return api_key
    return encrypt_value(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key for use.

    Args:
        encrypted_key: Encrypted API key

    Returns:
        str: Plain text API key
    """
    if not is_encrypted(encrypted_key):
        # Not encrypted (legacy data), return as-is
        return encrypted_key
    return decrypt_value(encrypted_key)


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    Mask an API key for display purposes.

    Args:
        api_key: The API key to mask
        visible_chars: Number of characters to show at start/end

    Returns:
        str: Masked API key (e.g., "sk-a...xyz")
    """
    if not api_key:
        return ""

    if len(api_key) <= visible_chars * 2:
        return "*" * len(api_key)

    return f"{api_key[:visible_chars]}...{api_key[-visible_chars:]}"


# =============================================================================
# Secure Token Generation
# =============================================================================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Length of the token in bytes (output will be hex, 2x length)

    Returns:
        str: Hexadecimal secure token
    """
    return secrets.token_hex(length)


def generate_api_key(prefix: str = "mnai") -> str:
    """
    Generate a new API key with a prefix.

    Args:
        prefix: Prefix for the API key

    Returns:
        str: New API key (e.g., "mnai_a1b2c3d4e5f6...")
    """
    token = secrets.token_urlsafe(32)
    return f"{prefix}_{token}"


def generate_referral_code(length: int = 8) -> str:
    """
    Generate a referral code.

    Args:
        length: Length of the code

    Returns:
        str: Alphanumeric referral code
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Exclude confusing chars
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# =============================================================================
# Hashing Functions
# =============================================================================

def hash_value(value: str) -> str:
    """
    Create a one-way hash of a value (for verification purposes).

    Args:
        value: Value to hash

    Returns:
        str: SHA-256 hash of the value
    """
    return hashlib.sha256(value.encode()).hexdigest()


def verify_hash(value: str, hash_value: str) -> bool:
    """
    Verify a value against its hash.

    Args:
        value: Value to verify
        hash_value: Expected hash

    Returns:
        bool: True if hash matches
    """
    return hash_value(value) == hash_value


# =============================================================================
# Encryption Model Mixin
# =============================================================================

class EncryptedFieldMixin:
    """
    Mixin for models with encrypted fields.

    Usage:
        class MyModel(EncryptedFieldMixin, models.Model):
            _encrypted_fields = ['api_key', 'secret']
            api_key = models.TextField()

    Note: Call encrypt_fields() before save and decrypt_fields() after load.
    """

    _encrypted_fields = []

    def encrypt_fields(self):
        """Encrypt all fields marked as encrypted."""
        for field_name in self._encrypted_fields:
            value = getattr(self, field_name, None)
            if value and not is_encrypted(value):
                setattr(self, field_name, encrypt_value(value))

    def decrypt_fields(self):
        """Decrypt all fields marked as encrypted."""
        for field_name in self._encrypted_fields:
            value = getattr(self, field_name, None)
            if value and is_encrypted(value):
                setattr(self, field_name, decrypt_value(value))

    def get_decrypted_field(self, field_name: str) -> Optional[str]:
        """Get a decrypted field value without modifying the model."""
        value = getattr(self, field_name, None)
        if value and is_encrypted(value):
            return decrypt_value(value)
        return value
