"""
Common validators for input validation across the application.

This module provides reusable validation functions for:
- Password strength
- Email format and domain
- Username rules
- Phone numbers
- File uploads
- Text sanitization
"""

import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from rest_framework import serializers
import bleach


# =============================================================================
# Password Validators
# =============================================================================

def validate_password_strength(password):
    """
    Validate password meets security requirements.

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise serializers.ValidationError(
            "Password must be at least 8 characters long."
        )

    if not re.search(r'[A-Z]', password):
        raise serializers.ValidationError(
            "Password must contain at least one uppercase letter."
        )

    if not re.search(r'[a-z]', password):
        raise serializers.ValidationError(
            "Password must contain at least one lowercase letter."
        )

    if not re.search(r'\d', password):
        raise serializers.ValidationError(
            "Password must contain at least one digit."
        )

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~]', password):
        raise serializers.ValidationError(
            "Password must contain at least one special character."
        )

    # Check for common weak passwords
    common_passwords = [
        'password', '12345678', 'qwerty12', 'admin123', 'letmein1',
        'welcome1', 'password1', 'Password1', 'Qwerty123'
    ]
    if password.lower() in [p.lower() for p in common_passwords]:
        raise serializers.ValidationError(
            "This password is too common. Please choose a stronger password."
        )

    return password


def validate_password_match(password1, password2):
    """Validate two passwords match."""
    if password1 != password2:
        raise serializers.ValidationError(
            "Passwords do not match."
        )
    return True


# =============================================================================
# Email Validators
# =============================================================================

def validate_email_format(email):
    """
    Validate email format with stricter rules.
    """
    email = email.strip().lower()

    # Basic format check
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise serializers.ValidationError(
            "Please enter a valid email address."
        )

    # Check for consecutive dots
    if '..' in email:
        raise serializers.ValidationError(
            "Email address cannot contain consecutive dots."
        )

    # Check local part doesn't start/end with dot
    local_part = email.split('@')[0]
    if local_part.startswith('.') or local_part.endswith('.'):
        raise serializers.ValidationError(
            "Email address format is invalid."
        )

    return email


def validate_email_domain(email):
    """
    Validate email domain is not from disposable email services.
    """
    disposable_domains = [
        'tempmail.com', 'throwaway.com', 'mailinator.com', 'guerrillamail.com',
        'temp-mail.org', '10minutemail.com', 'fakeinbox.com', 'trashmail.com',
        'sharklasers.com', 'yopmail.com', 'maildrop.cc', 'getairmail.com'
    ]

    domain = email.split('@')[1].lower()
    if domain in disposable_domains:
        raise serializers.ValidationError(
            "Please use a valid email address. Disposable emails are not allowed."
        )

    return email


# =============================================================================
# Username Validators
# =============================================================================

def validate_username(username):
    """
    Validate username meets requirements.

    Requirements:
    - 3-30 characters
    - Only alphanumeric, underscore, hyphen
    - Cannot start with number or special character
    - No consecutive special characters
    """
    username = username.strip()

    if len(username) < 3:
        raise serializers.ValidationError(
            "Username must be at least 3 characters long."
        )

    if len(username) > 30:
        raise serializers.ValidationError(
            "Username cannot exceed 30 characters."
        )

    # Check allowed characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise serializers.ValidationError(
            "Username can only contain letters, numbers, underscores, and hyphens."
        )

    # Must start with letter
    if not username[0].isalpha():
        raise serializers.ValidationError(
            "Username must start with a letter."
        )

    # No consecutive special characters
    if '--' in username or '__' in username or '-_' in username or '_-' in username:
        raise serializers.ValidationError(
            "Username cannot contain consecutive special characters."
        )

    # Check for reserved usernames
    reserved_usernames = [
        'admin', 'administrator', 'root', 'system', 'support', 'help',
        'moderator', 'mod', 'staff', 'api', 'null', 'undefined', 'test'
    ]
    if username.lower() in reserved_usernames:
        raise serializers.ValidationError(
            "This username is reserved. Please choose another."
        )

    return username


# =============================================================================
# Phone Number Validators
# =============================================================================

def validate_phone_number(phone):
    """
    Validate phone number format.
    """
    if not phone:
        return phone

    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)

    # Should only contain digits and optionally start with +
    if not re.match(r'^\+?\d{7,15}$', cleaned):
        raise serializers.ValidationError(
            "Please enter a valid phone number (7-15 digits)."
        )

    return cleaned


def validate_country_code(code):
    """
    Validate country code format.
    """
    if not code:
        return code

    # Remove + if present
    cleaned = code.lstrip('+')

    if not re.match(r'^\d{1,4}$', cleaned):
        raise serializers.ValidationError(
            "Please enter a valid country code (1-4 digits)."
        )

    return cleaned


# =============================================================================
# Text Input Validators
# =============================================================================

def sanitize_text(text):
    """
    Sanitize text input to prevent XSS attacks.
    """
    if not text:
        return text

    # Use bleach to clean HTML
    allowed_tags = []  # No HTML tags allowed by default
    allowed_attrs = {}

    cleaned = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True
    )

    return cleaned


def sanitize_html(html, allow_formatting=True):
    """
    Sanitize HTML content while preserving safe formatting.
    """
    if not html:
        return html

    if allow_formatting:
        allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'span'
        ]
        allowed_attrs = {
            'a': ['href', 'title', 'target'],
            'span': ['class'],
        }
    else:
        allowed_tags = []
        allowed_attrs = {}

    cleaned = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True
    )

    # Also linkify URLs in the content
    if allow_formatting:
        cleaned = bleach.linkify(cleaned)

    return cleaned


def validate_no_script_injection(text):
    """
    Check for potential script injection attempts.
    """
    if not text:
        return text

    # Patterns that indicate script injection
    dangerous_patterns = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',  # onclick, onerror, etc.
        r'data:text/html',
        r'vbscript:',
        r'expression\s*\(',
    ]

    text_lower = text.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            raise serializers.ValidationError(
                "Invalid characters detected in input."
            )

    return text


def validate_prompt_text(text):
    """
    Validate prompt text input.
    """
    if not text:
        raise serializers.ValidationError(
            "Prompt text is required."
        )

    text = text.strip()

    if len(text) < 2:
        raise serializers.ValidationError(
            "Prompt must be at least 2 characters long."
        )

    if len(text) > 10000:
        raise serializers.ValidationError(
            "Prompt cannot exceed 10,000 characters."
        )

    # Sanitize but allow the text through
    text = validate_no_script_injection(text)

    return text


# =============================================================================
# File Upload Validators
# =============================================================================

def validate_file_size(file, max_size_mb=10):
    """
    Validate file size.
    """
    max_size_bytes = max_size_mb * 1024 * 1024

    if file.size > max_size_bytes:
        raise serializers.ValidationError(
            f"File size cannot exceed {max_size_mb}MB."
        )

    return file


def validate_image_file(file):
    """
    Validate image file type and size.
    """
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    # Check content type
    if hasattr(file, 'content_type') and file.content_type not in allowed_types:
        raise serializers.ValidationError(
            "Invalid image format. Allowed formats: JPEG, PNG, GIF, WebP."
        )

    # Check file extension
    filename = file.name.lower() if hasattr(file, 'name') else ''
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise serializers.ValidationError(
            "Invalid image file extension."
        )

    # Check file size (max 5MB for images)
    validate_file_size(file, max_size_mb=5)

    return file


def validate_document_file(file):
    """
    Validate document file type and size.
    """
    allowed_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ]
    allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx']

    # Check content type
    if hasattr(file, 'content_type') and file.content_type not in allowed_types:
        raise serializers.ValidationError(
            "Invalid document format. Allowed formats: PDF, DOC, DOCX, TXT, XLS, XLSX."
        )

    # Check file extension
    filename = file.name.lower() if hasattr(file, 'name') else ''
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise serializers.ValidationError(
            "Invalid document file extension."
        )

    # Check file size (max 25MB for documents)
    validate_file_size(file, max_size_mb=25)

    return file


def validate_audio_file(file):
    """
    Validate audio file type and size.
    """
    allowed_types = [
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave',
        'audio/x-wav', 'audio/ogg', 'audio/webm', 'audio/m4a'
    ]
    allowed_extensions = ['.mp3', '.wav', '.ogg', '.webm', '.m4a']

    # Check content type
    if hasattr(file, 'content_type') and file.content_type not in allowed_types:
        raise serializers.ValidationError(
            "Invalid audio format. Allowed formats: MP3, WAV, OGG, WebM, M4A."
        )

    # Check file extension
    filename = file.name.lower() if hasattr(file, 'name') else ''
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise serializers.ValidationError(
            "Invalid audio file extension."
        )

    # Check file size (max 50MB for audio)
    validate_file_size(file, max_size_mb=50)

    return file


# =============================================================================
# Numeric Validators
# =============================================================================

def validate_positive_integer(value):
    """
    Validate value is a positive integer.
    """
    if not isinstance(value, int) or value < 0:
        raise serializers.ValidationError(
            "Value must be a positive integer."
        )
    return value


def validate_rating(value):
    """
    Validate rating is between 1 and 5.
    """
    if not isinstance(value, (int, float)):
        raise serializers.ValidationError(
            "Rating must be a number."
        )

    if value < 1 or value > 5:
        raise serializers.ValidationError(
            "Rating must be between 1 and 5."
        )

    return value


# =============================================================================
# ID/Code Validators
# =============================================================================

def validate_referral_code(code):
    """
    Validate referral code format.
    """
    if not code:
        return code

    code = code.strip().upper()

    if not re.match(r'^[A-Z0-9]{6,12}$', code):
        raise serializers.ValidationError(
            "Invalid referral code format."
        )

    return code


def validate_otp(otp):
    """
    Validate OTP format.
    """
    if not otp:
        raise serializers.ValidationError(
            "OTP is required."
        )

    otp = str(otp).strip()

    if not re.match(r'^\d{4,6}$', otp):
        raise serializers.ValidationError(
            "Invalid OTP format. Must be 4-6 digits."
        )

    return otp


# =============================================================================
# URL Validators
# =============================================================================

def validate_url(url):
    """
    Validate URL format and protocol.
    """
    if not url:
        return url

    url = url.strip()

    # Must start with http:// or https://
    if not url.startswith(('http://', 'https://')):
        raise serializers.ValidationError(
            "URL must start with http:// or https://"
        )

    # Basic URL pattern
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if not url_pattern.match(url):
        raise serializers.ValidationError(
            "Please enter a valid URL."
        )

    return url


# =============================================================================
# Django Regex Validators (for models)
# =============================================================================

username_validator = RegexValidator(
    regex=r'^[a-zA-Z][a-zA-Z0-9_-]{2,29}$',
    message='Username must start with a letter and contain only letters, numbers, underscores, and hyphens (3-30 chars).'
)

phone_validator = RegexValidator(
    regex=r'^\+?\d{7,15}$',
    message='Phone number must be 7-15 digits, optionally starting with +'
)

referral_code_validator = RegexValidator(
    regex=r'^[A-Z0-9]{6,12}$',
    message='Referral code must be 6-12 alphanumeric characters.'
)
