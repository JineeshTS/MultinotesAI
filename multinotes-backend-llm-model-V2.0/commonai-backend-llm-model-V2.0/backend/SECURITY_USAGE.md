# Security Utilities Module - Usage Guide

This guide demonstrates how to use the comprehensive security utilities in the MultinotesAI backend.

## Table of Contents

1. [API Key Encryption](#1-api-key-encryption)
2. [Secret Scanner](#2-secret-scanner)
3. [Input Sanitization](#3-input-sanitization)
4. [Rate Limiting](#4-rate-limiting)
5. [IP Filtering](#5-ip-filtering)
6. [Security Headers](#6-security-headers)
7. [Audit Logging](#7-audit-logging)
8. [Password Validation](#8-password-validation)

---

## 1. API Key Encryption

### Basic Usage

```python
from backend.security import APIKeyEncryption

# Encrypt an API key before storing in database
api_key = "sk-1234567890abcdef"
encrypted = APIKeyEncryption.encrypt_api_key(api_key)
# Save 'encrypted' to database

# Decrypt when needed for API calls
decrypted = APIKeyEncryption.decrypt_api_key(encrypted)
# Use 'decrypted' for API requests
```

### Generate New API Keys

```python
# Generate a new API key for users
api_key = APIKeyEncryption.generate_api_key(prefix="mnai")
# Returns: "mnai_xJ7k9pL2mQvR8z..."

# Hash for verification (one-way)
hashed = APIKeyEncryption.hash_api_key(api_key)
# Store hash in database for verification
```

### Mask Keys for Display

```python
# Safely display API keys in UI/logs
masked = APIKeyEncryption.mask_api_key(api_key)
# Returns: "sk-1...cdef"
```

### Example: Django Model

```python
from django.db import models
from backend.security import APIKeyEncryption

class UserAPIKey(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    encrypted_key = models.TextField()
    key_hash = models.CharField(max_length=64)  # For verification

    def set_api_key(self, api_key):
        """Encrypt and store API key."""
        self.encrypted_key = APIKeyEncryption.encrypt_api_key(api_key)
        self.key_hash = APIKeyEncryption.hash_api_key(api_key)

    def get_api_key(self):
        """Decrypt and return API key."""
        return APIKeyEncryption.decrypt_api_key(self.encrypted_key)

    def display_key(self):
        """Return masked version for display."""
        decrypted = self.get_api_key()
        return APIKeyEncryption.mask_api_key(decrypted)
```

---

## 2. Secret Scanner

### Scan Text for Exposed Secrets

```python
from backend.security import SecretScanner

# Scan code or configuration for exposed secrets
code = """
API_KEY = 'sk-1234567890abcdef'
AWS_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'
"""

findings = SecretScanner.scan_text(code)
for finding in findings:
    print(f"Found {finding['type']}: {finding['value']}")
    print(f"Severity: {finding['severity']}")
```

### Scan Files

```python
# Scan a file for secrets before committing
findings = SecretScanner.scan_file('.env')

if findings:
    print("⚠️  WARNING: Secrets detected in file!")
    for finding in findings:
        print(f"  - {finding['type']} at line {finding['position']}")
```

### Scan Dictionary/JSON Data

```python
# Scan user-provided configuration
config = {
    'api_settings': {
        'openai_key': 'sk-1234567890',
        'database_url': 'postgresql://user:password@localhost/db'
    }
}

findings = SecretScanner.scan_dict(config)
if findings:
    print(f"Found {len(findings)} potential secrets in configuration")
```

### Entropy Analysis

```python
# Detect high-entropy strings (likely secrets/tokens)
token = "xJ7k9pL2mQvR8zAbCdEf1234"

if SecretScanner.is_high_entropy_string(token):
    print("⚠️  High entropy string detected - likely a secret!")

# Calculate entropy
entropy = SecretScanner.calculate_entropy(token)
print(f"Entropy: {entropy:.2f}")
```

### Example: Pre-commit Hook

```python
import sys
from backend.security import SecretScanner

def check_secrets_before_commit():
    """Check for secrets in staged files."""
    files_to_check = ['.env', 'config.py', 'settings.py']

    all_findings = []
    for file_path in files_to_check:
        try:
            findings = SecretScanner.scan_file(file_path)
            all_findings.extend(findings)
        except FileNotFoundError:
            pass

    if all_findings:
        print("❌ COMMIT BLOCKED: Secrets detected!")
        for finding in all_findings:
            print(f"  {finding['file']}: {finding['type']} ({finding['severity']})")
        sys.exit(1)

    print("✅ No secrets detected")
```

---

## 3. Input Sanitization

### XSS Prevention

```python
from backend.security import InputSanitizer
from django.core.exceptions import ValidationError

# Sanitize HTML input
user_html = '<p>Hello</p><script>alert("XSS")</script>'
clean_html = InputSanitizer.sanitize_html(user_html, allow_safe_tags=True)
# Returns: '<p>Hello</p>' (script removed)

# Check for XSS before processing
try:
    InputSanitizer.check_xss(user_input)
    # Safe to process
except ValidationError as e:
    return JsonResponse({'error': str(e)}, status=400)
```

### SQL Injection Prevention

```python
# Check user input for SQL injection attempts
search_query = request.data.get('search', '')

try:
    InputSanitizer.check_sql_injection(search_query)
    # Safe to use in query
    results = Model.objects.filter(name__icontains=search_query)
except ValidationError:
    return JsonResponse({'error': 'Invalid search query'}, status=400)
```

### Command Injection Prevention

```python
# Validate filename before processing
filename = request.data.get('filename', '')

try:
    InputSanitizer.check_command_injection(filename)
    safe_filename = InputSanitizer.sanitize_filename(filename)
    # Safe to use
except ValidationError:
    return JsonResponse({'error': 'Invalid filename'}, status=400)
```

### URL Validation

```python
# Validate redirect URLs
redirect_url = request.GET.get('next', '/')

try:
    safe_url = InputSanitizer.sanitize_url(redirect_url)
    return redirect(safe_url)
except ValidationError:
    return redirect('/dashboard')  # Default safe redirect
```

### Example: DRF Serializer

```python
from rest_framework import serializers
from backend.security import InputSanitizer

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['text', 'author']

    def validate_text(self, value):
        """Sanitize and validate comment text."""
        # Check for XSS
        InputSanitizer.check_xss(value)

        # Check for SQL injection
        InputSanitizer.check_sql_injection(value)

        # Sanitize HTML (allow safe formatting)
        clean_text = InputSanitizer.sanitize_html(value, allow_safe_tags=True)

        return clean_text
```

---

## 4. Rate Limiting

### View-Level Rate Limiting

```python
from backend.security import RateLimiter
from django.http import JsonResponse

@RateLimiter.rate_limit('login', rate='5/m', block_time=300)
def login_view(request):
    """Login endpoint with rate limiting."""
    # Only 5 login attempts per minute
    # Blocked for 5 minutes after exceeding limit
    username = request.POST.get('username')
    password = request.POST.get('password')
    # ... authentication logic
```

### Custom Rate Limits

```python
# Strict rate limit for sensitive operations
@RateLimiter.rate_limit('password_reset', rate='3/h', block_time=3600)
def password_reset_view(request):
    """Only 3 password reset attempts per hour."""
    pass

# Generous rate limit for read operations
@RateLimiter.rate_limit('api_read', rate='1000/h', block_time=60)
def api_read_view(request):
    """1000 API reads per hour."""
    pass
```

### Method-Specific Rate Limiting

```python
# Only rate limit POST requests
@RateLimiter.rate_limit('api_write', rate='100/h', methods=['POST', 'PUT', 'PATCH'])
def api_view(request):
    """Rate limit only write operations."""
    if request.method == 'GET':
        # Not rate limited
        pass
    elif request.method == 'POST':
        # Rate limited
        pass
```

### Example: DRF View

```python
from rest_framework.views import APIView
from backend.security import RateLimiter

class LoginAPIView(APIView):
    @RateLimiter.rate_limit('api_login', rate='5/m', block_time=300)
    def post(self, request):
        """Rate limited login endpoint."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ... authentication logic
```

---

## 5. IP Filtering

### Whitelist Management

```python
from backend.security import IPFilter

# Add trusted IPs to whitelist
IPFilter.add_to_whitelist('192.168.1.100')
IPFilter.add_to_whitelist('10.0.0.0/8')  # CIDR range

# Check if IP is whitelisted
if IPFilter.is_whitelisted(client_ip):
    # Allow unrestricted access
    pass
```

### Blacklist Management

```python
# Block malicious IPs
IPFilter.add_to_blacklist(
    '123.45.67.89',
    ttl=86400,  # Block for 24 hours
    reason='Multiple failed login attempts'
)

# Check if IP is blocked
if IPFilter.is_blacklisted(client_ip):
    return JsonResponse({'error': 'Access denied'}, status=403)
```

### Automatic IP Blocking

```python
# Auto-block after threshold violations
def handle_failed_login(request):
    client_ip = get_client_ip(request)

    # Track violation
    IPFilter.auto_block_ip(
        client_ip,
        violation_type='login_failure',
        threshold=5  # Block after 5 failures
    )
```

### Example: Middleware

```python
from backend.security import IPFilter, get_client_ip

class IPFilterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip = get_client_ip(request)

        # Check IP (raises PermissionDenied if blocked)
        IPFilter.check_ip(client_ip, raise_exception=True)

        response = self.get_response(request)
        return response
```

### Example: Admin Panel Protection

```python
from django.contrib.admin.views.decorators import staff_member_required
from backend.security import IPFilter, get_client_ip

def admin_access_check(view_func):
    """Decorator to restrict admin access by IP."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        client_ip = get_client_ip(request)

        # Only allow admin access from whitelisted IPs
        if not IPFilter.is_whitelisted(client_ip):
            raise PermissionDenied("Admin access restricted to authorized IPs")

        return view_func(request, *args, **kwargs)

    return wrapper

@admin_access_check
@staff_member_required
def admin_dashboard(request):
    """Admin dashboard accessible only from whitelisted IPs."""
    pass
```

---

## 6. Security Headers

### Add to Django Settings

```python
# settings.py

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'backend.security.SecurityHeadersMiddleware',  # Add this
    # ... other middleware
]
```

### Headers Applied Automatically

The middleware adds these security headers to all responses:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: (restricts browser features)`
- `Strict-Transport-Security: max-age=31536000` (HTTPS only)
- `Content-Security-Policy: (customizable)`

### Custom CSP Configuration

The default CSP can be customized by modifying the middleware:

```python
# In your middleware
csp_directives = [
    "default-src 'self'",
    "script-src 'self' https://trusted-cdn.com",
    "style-src 'self' 'unsafe-inline'",
    # Add your custom directives
]
```

---

## 7. Audit Logging

### Basic Usage

```python
from backend.security import AuditLogger

@AuditLogger.audit_log('user.password_change', sensitive_params=['password'])
def change_password(request, user_id, password):
    """Password change with audit logging."""
    # Function execution is automatically logged
    user = User.objects.get(id=user_id)
    user.set_password(password)
    user.save()
    return True
```

### Log Sensitive Operations

```python
@AuditLogger.audit_log(
    'data.delete',
    sensitive_params=['data_id'],
    log_response=True
)
def delete_user_data(request, user_id, data_id):
    """Delete user data with full audit trail."""
    data = UserData.objects.get(id=data_id, user_id=user_id)
    data.delete()
    return {'deleted': True, 'data_id': data_id}
```

### Logged Information

The decorator automatically logs:

- Event type
- Timestamp
- Function name
- User ID (if authenticated)
- IP address
- Parameters (sensitive ones masked)
- Execution status (success/failure)
- Duration
- Error details (on failure)

### Example: View with Audit

```python
from rest_framework.views import APIView
from backend.security import AuditLogger

class UserDeleteAPIView(APIView):
    @AuditLogger.audit_log(
        'admin.user.delete',
        sensitive_params=['user_id'],
        log_response=True
    )
    def delete(self, request, user_id):
        """Delete user with audit logging."""
        user = User.objects.get(id=user_id)
        user.delete()

        return Response({
            'message': f'User {user_id} deleted successfully'
        })
```

### Review Audit Logs

```python
# View audit logs (stored in 'audit' logger)
# Check logs/audit.log or your logging backend

# Example audit log entry:
{
    "event_type": "user.password_change",
    "timestamp": "2024-01-15T10:30:00Z",
    "function": "change_password",
    "user_id": 123,
    "ip_address": "192.168.1.100",
    "params": {"password": "***REDACTED***"},
    "status": "success",
    "duration_ms": 45.2
}
```

---

## 8. Password Validation

### Validate Password Strength

```python
from backend.security import PasswordValidator

# Validate user password
password = request.data.get('password')
result = PasswordValidator.validate_password(
    password,
    min_length=8,
    require_uppercase=True,
    require_lowercase=True,
    require_digit=True,
    require_special=True,
    check_common=True,
    username=request.user.username,
    email=request.user.email
)

if not result['valid']:
    return JsonResponse({
        'error': 'Invalid password',
        'details': result['errors']
    }, status=400)

# Password is strong
print(f"Password strength: {result['strength']}")  # e.g., "strong"
print(f"Password score: {result['score']}/5")
```

### Generate Secure Passwords

```python
# Generate password for user
secure_password = PasswordValidator.generate_secure_password(length=16)
# Returns: "xJ7k9!pL2mQ#vR8z"

# Send to user via secure channel
send_email(user.email, f"Your temporary password: {secure_password}")
```

### Example: Registration View

```python
from backend.security import PasswordValidator

class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        # Validate password
        result = PasswordValidator.validate_password(
            password,
            username=username,
            email=email
        )

        if not result['valid']:
            return Response({
                'error': 'Password does not meet requirements',
                'details': result['errors'],
                'strength': result['strength']
            }, status=400)

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        return Response({
            'message': 'User created successfully',
            'password_strength': result['strength']
        })
```

### Password Strength Indicator for Frontend

```python
@api_view(['POST'])
def check_password_strength(request):
    """API endpoint to check password strength in real-time."""
    password = request.data.get('password', '')

    result = PasswordValidator.validate_password(
        password,
        check_common=True
    )

    return Response({
        'score': result['score'],
        'strength': result['strength'],
        'valid': result['valid'],
        'errors': result['errors']
    })
```

---

## Complete Integration Example

### Secure User Registration

```python
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response

from backend.security import (
    PasswordValidator,
    InputSanitizer,
    RateLimiter,
    IPFilter,
    AuditLogger,
    get_client_ip
)

User = get_user_model()

class SecureRegisterView(APIView):
    """
    Fully secured user registration endpoint.
    """

    @RateLimiter.rate_limit('registration', rate='5/h', block_time=3600)
    @AuditLogger.audit_log('user.registration', sensitive_params=['password'])
    def post(self, request):
        # 1. Check IP
        client_ip = get_client_ip(request)
        IPFilter.check_ip(client_ip, raise_exception=True)

        # 2. Sanitize inputs
        try:
            username = InputSanitizer.sanitize_input(
                request.data.get('username', '')
            )
            email = InputSanitizer.sanitize_input(
                request.data.get('email', '')
            )
            password = request.data.get('password', '')

            # Check for XSS and SQL injection
            InputSanitizer.check_xss(username)
            InputSanitizer.check_sql_injection(username)

        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

        # 3. Validate password
        pwd_result = PasswordValidator.validate_password(
            password,
            username=username,
            email=email
        )

        if not pwd_result['valid']:
            return Response({
                'error': 'Invalid password',
                'details': pwd_result['errors']
            }, status=400)

        # 4. Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            return Response({
                'message': 'User created successfully',
                'user_id': user.id
            }, status=201)

        except Exception as e:
            # Track failed registration
            IPFilter.auto_block_ip(
                client_ip,
                'registration_failure',
                threshold=10
            )
            return Response({'error': str(e)}, status=400)
```

---

## Configuration

### Django Settings

```python
# settings.py

# Enable security features
SECURITY_ENABLED = True

# Configure logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'logs/security.log',
            'formatter': 'verbose',
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/audit.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Rate limiting cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

---

## Best Practices

1. **Always encrypt sensitive data** before storing in database
2. **Scan for secrets** before committing code or deploying
3. **Sanitize all user input** to prevent XSS and injection attacks
4. **Apply rate limiting** to all authentication and sensitive endpoints
5. **Use IP filtering** to restrict admin access and block malicious actors
6. **Enable security headers** middleware in production
7. **Audit log** all sensitive operations for compliance
8. **Enforce strong passwords** for all user accounts

---

## Testing

Run the test suite to verify security utilities:

```bash
# Run all security tests
python manage.py test backend.test_security

# Run specific test
python manage.py test backend.test_security.PasswordValidatorTestCase

# Run with coverage
coverage run --source='backend' manage.py test backend.test_security
coverage report
```

---

## Support

For issues or questions about the security utilities:

- Check the inline documentation in `backend/security.py`
- Review test cases in `backend/test_security.py`
- Contact the security team

---

**Last Updated**: 2024-01-15
**Version**: 2.0
