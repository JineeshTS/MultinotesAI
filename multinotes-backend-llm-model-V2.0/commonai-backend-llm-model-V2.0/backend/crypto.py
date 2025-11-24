"""
Encryption Utilities for MultinotesAI.

This module provides:
- AES-256-GCM encryption for API keys
- Secure key derivation
- Token hashing
- Data encryption/decryption

Usage:
    from backend.crypto import encrypt_api_key, decrypt_api_key, hash_token

    # Encrypt sensitive data
    encrypted = encrypt_api_key("sk-abc123...")

    # Decrypt when needed
    decrypted = decrypt_api_key(encrypted)

    # Hash tokens for storage
    hashed = hash_token("user_token_xyz")
"""

import os
import base64
import hashlib
import hmac
import secrets
import logging
from typing import Optional, Tuple
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import cryptography library
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography package not installed. Using fallback encryption.")


# =============================================================================
# Configuration
# =============================================================================

# Salt for key derivation (should be in settings for production)
ENCRYPTION_SALT = getattr(
    settings,
    'ENCRYPTION_SALT',
    b'multinotes_encryption_salt_v1'
)

# Number of iterations for PBKDF2
PBKDF2_ITERATIONS = getattr(settings, 'PBKDF2_ITERATIONS', 100000)


# =============================================================================
# Key Derivation
# =============================================================================

@lru_cache(maxsize=1)
def _get_encryption_key() -> bytes:
    """
    Derive encryption key from Django SECRET_KEY.

    Uses PBKDF2 with SHA256 to derive a 256-bit key.
    Result is cached for performance.

    Returns:
        32-byte encryption key
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        # Fallback: use hashlib
        return hashlib.pbkdf2_hmac(
            'sha256',
            settings.SECRET_KEY.encode(),
            ENCRYPTION_SALT,
            PBKDF2_ITERATIONS,
            dklen=32
        )

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=ENCRYPTION_SALT,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend()
    )

    return kdf.derive(settings.SECRET_KEY.encode())


def _get_fernet_key() -> bytes:
    """
    Get Fernet-compatible key (base64-encoded 32-byte key).

    Returns:
        Fernet-compatible key
    """
    raw_key = _get_encryption_key()
    return base64.urlsafe_b64encode(raw_key)


# =============================================================================
# AES-GCM Encryption (Preferred)
# =============================================================================

def encrypt_aes_gcm(plaintext: str) -> str:
    """
    Encrypt plaintext using AES-256-GCM.

    Args:
        plaintext: String to encrypt

    Returns:
        Base64-encoded ciphertext (format: nonce||ciphertext||tag)
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        return encrypt_fernet_fallback(plaintext)

    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)

        # Generate random 96-bit nonce
        nonce = os.urandom(12)

        # Encrypt
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

        # Combine nonce and ciphertext
        encrypted = nonce + ciphertext

        return base64.urlsafe_b64encode(encrypted).decode()

    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise


def decrypt_aes_gcm(ciphertext: str) -> str:
    """
    Decrypt AES-256-GCM encrypted ciphertext.

    Args:
        ciphertext: Base64-encoded encrypted data

    Returns:
        Decrypted plaintext
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        return decrypt_fernet_fallback(ciphertext)

    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)

        # Decode base64
        encrypted = base64.urlsafe_b64decode(ciphertext)

        # Extract nonce and ciphertext
        nonce = encrypted[:12]
        ciphertext_bytes = encrypted[12:]

        # Decrypt
        plaintext = aesgcm.decrypt(nonce, ciphertext_bytes, None)

        return plaintext.decode()

    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise


# =============================================================================
# Fernet Encryption (Fallback)
# =============================================================================

def encrypt_fernet_fallback(plaintext: str) -> str:
    """
    Encrypt using Fernet (AES-128-CBC with HMAC).

    Args:
        plaintext: String to encrypt

    Returns:
        Base64-encoded ciphertext
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        # Ultimate fallback: XOR with key (NOT secure, for development only)
        logger.warning("Using insecure XOR encryption. Install cryptography package!")
        return _xor_encrypt(plaintext)

    try:
        key = _get_fernet_key()
        f = Fernet(key)
        encrypted = f.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Fernet encryption failed: {e}")
        raise


def decrypt_fernet_fallback(ciphertext: str) -> str:
    """
    Decrypt Fernet encrypted ciphertext.

    Args:
        ciphertext: Fernet token

    Returns:
        Decrypted plaintext
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        return _xor_decrypt(ciphertext)

    try:
        key = _get_fernet_key()
        f = Fernet(key)
        decrypted = f.decrypt(ciphertext.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Fernet decryption failed: {e}")
        raise


# =============================================================================
# Simple XOR (Development Only - NOT SECURE)
# =============================================================================

def _xor_encrypt(plaintext: str) -> str:
    """XOR encryption - FOR DEVELOPMENT ONLY."""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    plaintext_bytes = plaintext.encode()
    encrypted = bytes(p ^ k for p, k in zip(plaintext_bytes, key * (len(plaintext_bytes) // len(key) + 1)))
    return base64.urlsafe_b64encode(encrypted).decode()


def _xor_decrypt(ciphertext: str) -> str:
    """XOR decryption - FOR DEVELOPMENT ONLY."""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    encrypted = base64.urlsafe_b64decode(ciphertext)
    decrypted = bytes(e ^ k for e, k in zip(encrypted, key * (len(encrypted) // len(key) + 1)))
    return decrypted.decode()


# =============================================================================
# API Key Specific Functions
# =============================================================================

def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for storage.

    Args:
        api_key: Plain text API key

    Returns:
        Encrypted API key
    """
    if not api_key:
        return ''

    return encrypt_aes_gcm(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt a stored API key.

    Args:
        encrypted_key: Encrypted API key

    Returns:
        Plain text API key
    """
    if not encrypted_key:
        return ''

    return decrypt_aes_gcm(encrypted_key)


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    Mask an API key for display purposes.

    Args:
        api_key: Full API key
        visible_chars: Number of characters to show at end

    Returns:
        Masked key like "sk-...abc123"
    """
    if not api_key:
        return ''

    if len(api_key) <= visible_chars:
        return '*' * len(api_key)

    # Keep prefix (e.g., "sk-") and last N characters
    if '-' in api_key:
        prefix = api_key.split('-')[0] + '-'
        suffix = api_key[-visible_chars:]
        return f"{prefix}...{suffix}"

    return f"...{api_key[-visible_chars:]}"


# =============================================================================
# Token Hashing
# =============================================================================

def hash_token(token: str) -> str:
    """
    Create a secure hash of a token for storage.

    Uses SHA-256 with a prefix for identification.

    Args:
        token: Token to hash

    Returns:
        Hex-encoded hash
    """
    if not token:
        return ''

    # Use HMAC with SECRET_KEY as the key
    h = hmac.new(
        settings.SECRET_KEY.encode(),
        token.encode(),
        hashlib.sha256
    )

    return h.hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a token against its hash.

    Args:
        token: Token to verify
        token_hash: Expected hash

    Returns:
        True if token matches hash
    """
    if not token or not token_hash:
        return False

    computed_hash = hash_token(token)

    # Use constant-time comparison
    return hmac.compare_digest(computed_hash, token_hash)


def hash_password_token(token: str) -> str:
    """
    Hash a password reset or verification token.

    Uses bcrypt-like approach with salt embedded.

    Args:
        token: Token to hash

    Returns:
        Salted hash
    """
    salt = os.urandom(16)

    h = hashlib.pbkdf2_hmac(
        'sha256',
        token.encode(),
        salt,
        10000  # Fewer iterations for tokens that change frequently
    )

    # Combine salt and hash
    combined = salt + h
    return base64.urlsafe_b64encode(combined).decode()


def verify_password_token(token: str, stored_hash: str) -> bool:
    """
    Verify a password token against stored hash.

    Args:
        token: Token to verify
        stored_hash: Stored hash with embedded salt

    Returns:
        True if token is valid
    """
    try:
        combined = base64.urlsafe_b64decode(stored_hash)
        salt = combined[:16]
        stored_digest = combined[16:]

        computed_digest = hashlib.pbkdf2_hmac(
            'sha256',
            token.encode(),
            salt,
            10000
        )

        return hmac.compare_digest(computed_digest, stored_digest)

    except Exception:
        return False


# =============================================================================
# Secure Random Generation
# =============================================================================

def generate_api_key(prefix: str = 'mn', length: int = 32) -> str:
    """
    Generate a secure random API key.

    Args:
        prefix: Key prefix (e.g., 'mn' for multinotes)
        length: Length of random portion

    Returns:
        API key like "mn_abc123..."
    """
    random_part = secrets.token_urlsafe(length)
    return f"{prefix}_{random_part}"


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.

    Args:
        length: Token length in bytes (output is base64-encoded)

    Returns:
        URL-safe base64-encoded token
    """
    return secrets.token_urlsafe(length)


def generate_verification_code(length: int = 6) -> str:
    """
    Generate a numeric verification code.

    Args:
        length: Number of digits

    Returns:
        Numeric code like "123456"
    """
    return ''.join(secrets.choice('0123456789') for _ in range(length))


# =============================================================================
# Data Encryption for Database Fields
# =============================================================================

class EncryptedFieldMixin:
    """
    Mixin for Django model fields that should be encrypted.

    Usage:
        class MyModel(models.Model):
            api_key = EncryptedCharField(max_length=500)
    """

    def from_db_value(self, value, expression, connection):
        """Decrypt value when reading from database."""
        if value is None:
            return value
        try:
            return decrypt_api_key(value)
        except Exception:
            # Return as-is if decryption fails (might be plaintext)
            return value

    def get_prep_value(self, value):
        """Encrypt value when writing to database."""
        if value is None:
            return value
        return encrypt_api_key(value)


# =============================================================================
# Key Rotation
# =============================================================================

class KeyRotator:
    """
    Handle encryption key rotation.

    Usage:
        rotator = KeyRotator()
        rotator.rotate_key(old_key, new_key, Model, 'encrypted_field')
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def rotate_key(
        self,
        old_key: bytes,
        new_key: bytes,
        model_class,
        field_name: str,
        batch_size: int = 100
    ) -> Tuple[int, int]:
        """
        Rotate encryption key for all records.

        Args:
            old_key: Old encryption key
            new_key: New encryption key
            model_class: Django model class
            field_name: Name of encrypted field
            batch_size: Records to process at once

        Returns:
            Tuple of (success_count, error_count)
        """
        success = 0
        errors = 0

        # Process in batches
        queryset = model_class.objects.exclude(**{f'{field_name}__isnull': True})
        total = queryset.count()

        self.logger.info(f"Starting key rotation for {total} records")

        for obj in queryset.iterator(chunk_size=batch_size):
            try:
                encrypted_value = getattr(obj, field_name)

                # Decrypt with old key
                decrypted = self._decrypt_with_key(encrypted_value, old_key)

                # Re-encrypt with new key
                new_encrypted = self._encrypt_with_key(decrypted, new_key)

                # Update record
                setattr(obj, field_name, new_encrypted)
                obj.save(update_fields=[field_name])

                success += 1

            except Exception as e:
                self.logger.error(f"Failed to rotate key for {obj.pk}: {e}")
                errors += 1

        self.logger.info(f"Key rotation complete: {success} success, {errors} errors")
        return success, errors

    def _decrypt_with_key(self, ciphertext: str, key: bytes) -> str:
        """Decrypt with specific key."""
        if not CRYPTOGRAPHY_AVAILABLE:
            raise RuntimeError("cryptography package required for key rotation")

        aesgcm = AESGCM(key)
        encrypted = base64.urlsafe_b64decode(ciphertext)
        nonce = encrypted[:12]
        ciphertext_bytes = encrypted[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext_bytes, None)
        return plaintext.decode()

    def _encrypt_with_key(self, plaintext: str, key: bytes) -> str:
        """Encrypt with specific key."""
        if not CRYPTOGRAPHY_AVAILABLE:
            raise RuntimeError("cryptography package required for key rotation")

        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        encrypted = nonce + ciphertext
        return base64.urlsafe_b64encode(encrypted).decode()


# =============================================================================
# Singleton Instances
# =============================================================================

key_rotator = KeyRotator()
