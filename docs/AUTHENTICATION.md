# MultinotesAI Authentication Guide

## Overview

MultinotesAI uses **JWT (JSON Web Tokens)** for API authentication. This guide covers all authentication methods, token management, and security best practices.

---

## Table of Contents

- [Authentication Methods](#authentication-methods)
- [JWT Token Flow](#jwt-token-flow)
- [Token Types](#token-types)
- [Token Refresh](#token-refresh)
- [Social Authentication](#social-authentication)
- [API Key Authentication](#api-key-authentication)
- [Security Best Practices](#security-best-practices)
- [Common Authentication Scenarios](#common-authentication-scenarios)

---

## Authentication Methods

MultinotesAI supports multiple authentication methods:

1. **Email/Password Authentication** - Traditional username/password login
2. **Social Authentication** - Google, Facebook, Apple Sign-In
3. **API Key Authentication** - For programmatic access and integrations
4. **JWT Tokens** - Standard bearer token authentication

---

## JWT Token Flow

### 1. User Registration

```bash
curl -X POST https://api.multinotesai.com/authentication/v1/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Registration successful. Please verify your email.",
  "data": {
    "user": {
      "id": 123,
      "email": "john@example.com",
      "is_verified": false
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
  }
}
```

### 2. Email Verification

After registration, verify email using the token sent to the user's email:

```bash
curl -X POST https://api.multinotesai.com/authentication/v1/verify-email-token/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "email_verification_token_from_email"
  }'
```

### 3. Login

```bash
curl -X POST https://api.multinotesai.com/authentication/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 123,
      "email": "john@example.com",
      "role": "user",
      "is_verified": true
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    },
    "subscription": {
      "plan": "Free",
      "status": "active",
      "tokens_remaining": 1000
    }
  }
}
```

### 4. Making Authenticated Requests

Use the access token in the `Authorization` header:

```bash
curl -X GET https://api.multinotesai.com/authentication/get-user/123/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

---

## Token Types

### Access Token

- **Purpose:** Short-lived token for API authentication
- **Lifetime:** 15 minutes (default)
- **Usage:** Include in Authorization header for all authenticated requests
- **Format:** `Authorization: Bearer {access_token}`

**Example Access Token Payload:**
```json
{
  "token_type": "access",
  "exp": 1642780800,
  "iat": 1642779900,
  "jti": "unique-token-id",
  "user_id": 123,
  "username": "johndoe",
  "email": "john@example.com",
  "role": "user"
}
```

### Refresh Token

- **Purpose:** Long-lived token to obtain new access tokens
- **Lifetime:** 7 days (default)
- **Usage:** Exchange for new access token when current one expires
- **Security:** Store securely, never expose in URLs or logs

**Example Refresh Token Payload:**
```json
{
  "token_type": "refresh",
  "exp": 1643385600,
  "iat": 1642779900,
  "jti": "unique-token-id",
  "user_id": 123
}
```

---

## Token Refresh

When the access token expires, use the refresh token to obtain a new access token without requiring the user to login again.

### Refresh Token Endpoint

**Endpoint:** `POST /authentication/v1/token/refresh/`

**Request:**
```bash
curl -X POST https://api.multinotesai.com/authentication/v1/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

**Success Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Error Response (401 Unauthorized):**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_007",
    "message": "Token is expired or invalid."
  }
}
```

### Token Refresh Strategy

**Recommended approach:**

1. **Preemptive Refresh:** Refresh token before it expires
2. **Automatic Retry:** Intercept 401 errors and attempt token refresh
3. **Token Rotation:** Store new refresh token when received

**Example JavaScript Implementation:**

```javascript
class TokenManager {
  constructor() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  async refreshAccessToken() {
    try {
      const response = await fetch('https://api.multinotesai.com/authentication/v1/token/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: this.refreshToken })
      });

      if (response.ok) {
        const data = await response.json();
        this.accessToken = data.access;
        this.refreshToken = data.refresh;

        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);

        return data.access;
      } else {
        // Refresh token expired, need to re-login
        this.logout();
        throw new Error('Session expired. Please login again.');
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
      throw error;
    }
  }

  async makeAuthenticatedRequest(url, options = {}) {
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${this.accessToken}`
    };

    let response = await fetch(url, options);

    // If 401, try refreshing token
    if (response.status === 401) {
      await this.refreshAccessToken();
      options.headers['Authorization'] = `Bearer ${this.accessToken}`;
      response = await fetch(url, options);
    }

    return response;
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  }
}
```

---

## Social Authentication

MultinotesAI supports authentication via popular social providers.

### Supported Providers

1. **Google** - socialType: `1`
2. **Apple** - socialType: `2`
3. **Facebook** - socialType: `3`

### Social Login Flow

**Step 1: Authenticate with Social Provider**

Use the provider's SDK to authenticate and obtain user information:

- Google: https://developers.google.com/identity
- Apple: https://developer.apple.com/sign-in-with-apple
- Facebook: https://developers.facebook.com/docs/facebook-login

**Step 2: Send Credentials to MultinotesAI**

```bash
curl -X POST https://api.multinotesai.com/authentication/v1/social-login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "username": "johndoe",
    "socialId": "google_unique_user_id_123456",
    "socialType": 1,
    "deviceToken": "fcm_device_token"
  }'
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email from social provider |
| username | string | Yes | Username (can be derived from email) |
| socialId | string | Yes | Unique user ID from social provider |
| socialType | integer | Yes | 1=Google, 2=Apple, 3=Facebook |
| deviceToken | string | No | FCM device token for push notifications |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 123,
      "email": "john@example.com",
      "username": "johndoe",
      "socialType": 1,
      "is_verified": true
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    },
    "subscription": {
      "plan": "Free",
      "status": "active"
    },
    "is_new_user": false
  }
}
```

### Google Sign-In Example (JavaScript)

```javascript
// Initialize Google Sign-In
google.accounts.id.initialize({
  client_id: 'YOUR_GOOGLE_CLIENT_ID',
  callback: handleGoogleSignIn
});

async function handleGoogleSignIn(response) {
  // Decode JWT to get user info
  const userInfo = parseJwt(response.credential);

  // Send to MultinotesAI
  const multinotesResponse = await fetch('https://api.multinotesai.com/authentication/v1/social-login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: userInfo.email,
      username: userInfo.email.split('@')[0],
      socialId: userInfo.sub,
      socialType: 1
    })
  });

  const data = await multinotesResponse.json();

  if (data.success) {
    // Store tokens
    localStorage.setItem('access_token', data.data.tokens.access);
    localStorage.setItem('refresh_token', data.data.tokens.refresh);

    // Redirect to dashboard
    window.location.href = '/dashboard';
  }
}

function parseJwt(token) {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  return JSON.parse(window.atob(base64));
}
```

### Apple Sign-In Example (JavaScript)

```javascript
// Initialize Apple Sign-In
AppleID.auth.init({
  clientId: 'YOUR_APPLE_CLIENT_ID',
  scope: 'name email',
  redirectURI: 'https://yourapp.com/callback',
  usePopup: true
});

async function signInWithApple() {
  try {
    const data = await AppleID.auth.signIn();

    // Send to MultinotesAI
    const response = await fetch('https://api.multinotesai.com/authentication/v1/social-login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: data.user?.email || data.authorization.id_token.email,
        username: data.user?.email?.split('@')[0] || 'appleuser',
        socialId: data.authorization.id_token.sub,
        socialType: 2
      })
    });

    const result = await response.json();
    if (result.success) {
      // Store tokens and redirect
      localStorage.setItem('access_token', result.data.tokens.access);
      localStorage.setItem('refresh_token', result.data.tokens.refresh);
      window.location.href = '/dashboard';
    }
  } catch (error) {
    console.error('Apple Sign-In error:', error);
  }
}
```

---

## API Key Authentication

For programmatic access, server-to-server integration, or third-party applications, use API keys instead of JWT tokens.

### Creating an API Key

**Endpoint:** `POST /api/v1/api-keys/create/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```bash
curl -X POST https://api.multinotesai.com/api/v1/api-keys/create/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Integration",
    "scopes": ["read", "write", "generate"],
    "expires_in_days": 365,
    "rate_limit": 5000
  }'
```

**Available Scopes:**
- `read` - Read content and user data
- `write` - Create and modify content
- `generate` - Use AI generation features
- `export` - Export content
- `admin` - Full access (admin users only)

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 42,
    "name": "Production API Integration",
    "api_key": "mna_Ab3dEf9hIjK2mN5pQrS7uVwX9yZ1234567890abcdefghij",
    "prefix": "mna_Ab3d",
    "scopes": ["read", "write", "generate"],
    "rate_limit": 5000,
    "expires_at": "2025-01-20T00:00:00Z",
    "created_at": "2024-01-20T15:30:00Z"
  },
  "warning": "This API key will only be shown once. Please store it securely."
}
```

**Important:** The full API key is only returned once during creation. Store it securely!

### Using API Keys

API keys can be provided in two ways:

**Method 1: Authorization Header (Recommended)**
```bash
curl -X POST https://api.multinotesai.com/coreapp/openai_text_to_text/ \
  -H "Authorization: Bearer mna_Ab3dEf9hIjK2mN5pQrS7uVwX9yZ1234567890abcdefghij" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a story",
    "model_id": 1
  }'
```

**Method 2: X-API-Key Header**
```bash
curl -X POST https://api.multinotesai.com/coreapp/openai_text_to_text/ \
  -H "X-API-Key: mna_Ab3dEf9hIjK2mN5pQrS7uVwX9yZ1234567890abcdefghij" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a story",
    "model_id": 1
  }'
```

### API Key Format

All MultinotesAI API keys follow this format:
```
mna_{40_character_random_string}
```

- Prefix: `mna_` (MultinotesAI identifier)
- Length: 44 characters total
- Character set: URL-safe base64 (A-Z, a-z, 0-9, -, _)

### Managing API Keys

**List All Keys:**
```bash
curl -X GET https://api.multinotesai.com/api/v1/api-keys/ \
  -H "Authorization: Bearer {access_token}"
```

**Get Key Details:**
```bash
curl -X GET https://api.multinotesai.com/api/v1/api-keys/42/ \
  -H "Authorization: Bearer {access_token}"
```

**Revoke API Key:**
```bash
curl -X DELETE https://api.multinotesai.com/api/v1/api-keys/42/revoke/ \
  -H "Authorization: Bearer {access_token}"
```

**Rotate API Key:**
```bash
curl -X POST https://api.multinotesai.com/api/v1/api-keys/42/rotate/ \
  -H "Authorization: Bearer {access_token}"
```

Response will include a new API key. The old key is immediately revoked.

### API Key Rate Limits

Each API key has its own rate limit separate from user-based limits:

```
X-API-Key-Limit: 5000
X-API-Key-Remaining: 4987
X-API-Key-Reset: 1642784400
```

---

## Security Best Practices

### 1. Token Storage

**Web Applications:**
- ✅ Store access token in memory (React state, Vue store)
- ✅ Store refresh token in httpOnly cookie (server-side)
- ❌ Never store tokens in localStorage (XSS vulnerable)
- ❌ Never store tokens in sessionStorage

**Mobile Applications:**
- ✅ Use secure storage (iOS Keychain, Android Keystore)
- ✅ Implement biometric authentication for token access
- ❌ Never store tokens in shared preferences

**Server Applications:**
- ✅ Use API keys instead of JWT tokens
- ✅ Store API keys in environment variables
- ✅ Use secrets management service (AWS Secrets Manager, HashiCorp Vault)
- ❌ Never hardcode API keys in source code

### 2. Token Transmission

- ✅ Always use HTTPS for API requests
- ✅ Include tokens in Authorization header, not URL
- ❌ Never send tokens in query parameters
- ❌ Never log tokens in application logs

### 3. Password Security

**Requirements:**
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character

**Example Password Validation:**
```javascript
function validatePassword(password) {
  const minLength = 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasNumber = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);

  return password.length >= minLength &&
         hasUppercase &&
         hasLowercase &&
         hasNumber &&
         hasSpecial;
}
```

### 4. Two-Factor Authentication (2FA)

While not currently implemented, 2FA will be added in future versions:

- TOTP (Time-based One-Time Password)
- SMS-based verification
- Email-based verification

### 5. Session Management

**Best Practices:**
- Implement token blacklisting on logout
- Set appropriate token expiration times
- Implement concurrent session limits
- Log suspicious authentication attempts

### 6. API Key Security

- ✅ Rotate API keys regularly (every 90 days recommended)
- ✅ Use different keys for different environments (dev, staging, prod)
- ✅ Implement key rotation without downtime
- ✅ Monitor API key usage for anomalies
- ❌ Never commit API keys to version control
- ❌ Never share API keys via email or messaging

---

## Common Authentication Scenarios

### Scenario 1: Web Application Login Flow

```javascript
// 1. User submits login form
async function login(email, password) {
  const response = await fetch('https://api.multinotesai.com/authentication/v1/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  const data = await response.json();

  if (data.success) {
    // Store tokens
    sessionStorage.setItem('access_token', data.data.tokens.access);
    localStorage.setItem('refresh_token', data.data.tokens.refresh);

    // Store user info
    sessionStorage.setItem('user', JSON.stringify(data.data.user));

    return data.data.user;
  } else {
    throw new Error(data.error.message);
  }
}

// 2. Make authenticated requests
async function fetchUserProfile() {
  const token = sessionStorage.getItem('access_token');

  const response = await fetch('https://api.multinotesai.com/authentication/get-user/123/', {
    headers: { 'Authorization': `Bearer ${token}` }
  });

  return response.json();
}

// 3. Logout
function logout() {
  sessionStorage.clear();
  localStorage.removeItem('refresh_token');
  window.location.href = '/login';
}
```

### Scenario 2: Mobile App Authentication

```swift
// iOS - Swift Example

class AuthService {
    private let keychain = KeychainSwift()

    func login(email: String, password: String) async throws -> User {
        let url = URL(string: "https://api.multinotesai.com/authentication/v1/login/")!

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["email": email, "password": password]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(LoginResponse.self, from: data)

        // Store tokens securely in Keychain
        keychain.set(response.data.tokens.access, forKey: "access_token")
        keychain.set(response.data.tokens.refresh, forKey: "refresh_token")

        return response.data.user
    }

    func makeAuthenticatedRequest(url: URL) async throws -> Data {
        guard let token = keychain.get("access_token") else {
            throw AuthError.notAuthenticated
        }

        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let (data, response) = try await URLSession.shared.data(for: request)

        // Check for 401 and refresh token if needed
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 401 {
            try await refreshToken()
            return try await makeAuthenticatedRequest(url: url)
        }

        return data
    }

    func refreshToken() async throws {
        guard let refreshToken = keychain.get("refresh_token") else {
            throw AuthError.noRefreshToken
        }

        let url = URL(string: "https://api.multinotesai.com/authentication/v1/token/refresh/")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["refresh": refreshToken]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(TokenResponse.self, from: data)

        // Update tokens
        keychain.set(response.access, forKey: "access_token")
        keychain.set(response.refresh, forKey: "refresh_token")
    }

    func logout() {
        keychain.delete("access_token")
        keychain.delete("refresh_token")
    }
}
```

### Scenario 3: Server-to-Server Integration

```python
# Python Example using API Keys

import os
import requests
from typing import Optional, Dict, Any

class MultinotesAIClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('MULTINOTESAI_API_KEY')
        self.base_url = 'https://api.multinotesai.com'

        if not self.api_key:
            raise ValueError('API key is required')

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data
        )

        response.raise_for_status()
        return response.json()

    def generate_text(self, prompt: str, model_id: int = 1) -> Dict[str, Any]:
        """Generate text using AI."""
        return self._make_request(
            'POST',
            '/coreapp/openai_text_to_text/',
            data={
                'prompt': prompt,
                'model_id': model_id,
                'max_tokens': 500
            }
        )

    def create_folder(self, name: str, parent_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new folder."""
        return self._make_request(
            'POST',
            '/coreapp/create_folder/',
            data={
                'name': name,
                'parent_id': parent_id
            }
        )

# Usage
client = MultinotesAIClient(api_key='mna_your_api_key_here')

# Generate text
result = client.generate_text('Write a haiku about AI')
print(result['data']['response'])

# Create folder
folder = client.create_folder('My Documents')
print(f"Created folder: {folder['data']['name']}")
```

---

## Error Handling

### Authentication Errors

| Error Code | HTTP Status | Description | Action Required |
|------------|-------------|-------------|-----------------|
| AUTH_001 | 401 | Invalid credentials | Check email/password |
| AUTH_002 | 400 | Email already exists | Use different email |
| AUTH_003 | 400 | Username already exists | Choose different username |
| AUTH_004 | 403 | User blocked | Contact support |
| AUTH_005 | 403 | Email not verified | Verify email first |
| AUTH_006 | 401 | Invalid token | Re-authenticate |
| AUTH_007 | 401 | Token expired | Refresh token or re-login |
| AUTH_008 | 403 | Permission denied | Check user permissions |

### Example Error Response

```json
{
  "success": false,
  "error": {
    "code": "AUTH_007",
    "message": "Token is expired or invalid.",
    "details": {
      "token_type": "access",
      "expired_at": "2024-01-20T15:45:00Z"
    }
  }
}
```

---

## Support

For authentication issues:
- Email: auth-support@multinotesai.com
- Documentation: https://docs.multinotesai.com/authentication
- Security Issues: security@multinotesai.com
