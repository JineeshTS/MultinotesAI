# Security Module - Quick Reference

## 🔐 API Key Encryption

```python
from backend.security import APIKeyEncryption

# Encrypt
encrypted = APIKeyEncryption.encrypt_api_key("sk-1234567890")

# Decrypt
plaintext = APIKeyEncryption.decrypt_api_key(encrypted)

# Generate
new_key = APIKeyEncryption.generate_api_key()

# Mask for display
masked = APIKeyEncryption.mask_api_key(api_key)  # "sk-1...890"
```

---

## 🔍 Secret Scanner

```python
from backend.security import SecretScanner

# Scan text
findings = SecretScanner.scan_text(code)

# Scan file
findings = SecretScanner.scan_file('.env')

# Scan dictionary
findings = SecretScanner.scan_dict(config_dict)

# Check entropy
if SecretScanner.is_high_entropy_string(token):
    print("Possible secret detected!")
```

---

## 🧹 Input Sanitization

```python
from backend.security import InputSanitizer

# Remove XSS
clean = InputSanitizer.sanitize_html(user_input)

# Check for attacks
InputSanitizer.check_xss(text)
InputSanitizer.check_sql_injection(text)
InputSanitizer.check_command_injection(text)

# Sanitize filename
safe_name = InputSanitizer.sanitize_filename(filename)

# Sanitize URL
safe_url = InputSanitizer.sanitize_url(url)
```

---

## ⏱️ Rate Limiting

```python
from backend.security import RateLimiter

# Decorator usage
@RateLimiter.rate_limit('login', rate='5/m', block_time=300)
def login_view(request):
    pass

# Rate formats:
# '60/s'  - 60 per second
# '100/m' - 100 per minute
# '1000/h' - 1000 per hour
# '5000/d' - 5000 per day
```

---

## 🌐 IP Filtering

```python
from backend.security import IPFilter

# Whitelist
IPFilter.add_to_whitelist('192.168.1.100')
IPFilter.add_to_whitelist('10.0.0.0/8')  # CIDR

# Blacklist
IPFilter.add_to_blacklist('1.2.3.4', ttl=86400, reason='Abuse')

# Check
IPFilter.check_ip(client_ip, raise_exception=True)

# Auto-block
IPFilter.auto_block_ip(ip, 'login_failure', threshold=5)
```

---

## 🛡️ Security Headers

```python
# Add to settings.py MIDDLEWARE
MIDDLEWARE = [
    # ...
    'backend.security.SecurityHeadersMiddleware',
    # ...
]
```

**Headers added:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: (restricted)`
- `Strict-Transport-Security` (HTTPS only)
- `Content-Security-Policy`

---

## 📝 Audit Logging

```python
from backend.security import AuditLogger

@AuditLogger.audit_log(
    'user.password_change',
    sensitive_params=['password'],
    log_response=True
)
def change_password(request, user_id, password):
    # Automatically logs:
    # - Event type, timestamp, function
    # - User ID, IP address
    # - Parameters (sensitive masked)
    # - Success/failure, duration
    pass
```

---

## 🔑 Password Validation

```python
from backend.security import PasswordValidator

# Validate
result = PasswordValidator.validate_password(
    password,
    username=username,
    email=email
)

if result['valid']:
    print(f"Strength: {result['strength']}")  # very_strong
    print(f"Score: {result['score']}/5")      # 5/5
else:
    print(f"Errors: {result['errors']}")

# Generate
secure_pwd = PasswordValidator.generate_secure_password(length=16)
```

**Validation checks:**
- ✅ Minimum length (default: 8)
- ✅ Uppercase letter
- ✅ Lowercase letter
- ✅ Digit
- ✅ Special character
- ✅ Not common password
- ✅ No sequential chars
- ✅ No repeated chars
- ✅ Not in username/email

---

## 🔧 Utility Functions

```python
from backend.security import (
    get_client_ip,
    is_safe_redirect_url,
    secure_compare
)

# Get client IP (handles X-Forwarded-For)
ip = get_client_ip(request)

# Safe redirect check (prevent open redirect)
if is_safe_redirect_url(url):
    return redirect(url)

# Timing-safe string comparison
if secure_compare(token1, token2):
    print("Tokens match")
```

---

## 📋 Complete Example

```python
from backend.security import (
    RateLimiter,
    InputSanitizer,
    PasswordValidator,
    AuditLogger,
    IPFilter,
    get_client_ip
)

@RateLimiter.rate_limit('register', rate='5/h')
@AuditLogger.audit_log('user.register', sensitive_params=['password'])
def register_view(request):
    # 1. Check IP
    ip = get_client_ip(request)
    IPFilter.check_ip(ip, raise_exception=True)

    # 2. Sanitize inputs
    username = InputSanitizer.sanitize_input(request.POST['username'])
    InputSanitizer.check_xss(username)

    # 3. Validate password
    result = PasswordValidator.validate_password(
        request.POST['password'],
        username=username
    )

    if not result['valid']:
        return JsonResponse({'errors': result['errors']}, status=400)

    # 4. Create user
    user = User.objects.create_user(...)
    return JsonResponse({'success': True})
```

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test backend.test_security

# Run specific test class
python manage.py test backend.test_security.PasswordValidatorTestCase

# Run with coverage
coverage run --source='backend' manage.py test backend.test_security
coverage report
```

---

## ⚙️ Configuration

### Required Settings

```python
# settings.py

# Secret key (REQUIRED - used for encryption)
SECRET_KEY = 'your-secret-key-here'

# Cache (for rate limiting and IP filtering)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Logging
LOGGING = {
    'loggers': {
        'security': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
        'audit': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

---

## 🚨 Common Patterns

### Secure API Endpoint

```python
from rest_framework.views import APIView
from backend.security import RateLimiter, InputSanitizer

class SecureAPIView(APIView):
    @RateLimiter.rate_limit('api', rate='100/h')
    def post(self, request):
        # Sanitize all inputs
        data = {
            k: InputSanitizer.sanitize_input(v)
            for k, v in request.data.items()
        }

        # Process safely
        return Response({'status': 'ok'})
```

### Protect Admin Routes

```python
from backend.security import IPFilter, get_client_ip

def admin_middleware(get_response):
    def middleware(request):
        if request.path.startswith('/admin/'):
            ip = get_client_ip(request)
            IPFilter.check_ip(ip, raise_exception=True)
        return get_response(request)
    return middleware
```

### Scan Secrets Before Deployment

```python
from backend.security import SecretScanner

def check_secrets():
    files = ['.env', 'settings.py', 'config.yaml']
    all_findings = []

    for f in files:
        try:
            findings = SecretScanner.scan_file(f)
            all_findings.extend(findings)
        except FileNotFoundError:
            pass

    if all_findings:
        print("⚠️  Secrets detected!")
        for f in all_findings:
            print(f"  {f['file']}: {f['type']}")
        return False

    print("✅ No secrets detected")
    return True
```

---

## 📚 More Info

- Full documentation: `SECURITY_USAGE.md`
- Source code: `backend/security.py`
- Tests: `backend/test_security.py`

---

**Version**: 2.0 | **Last Updated**: 2024-01-15
