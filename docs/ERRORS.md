# MultinotesAI Error Handling Guide

## Overview

MultinotesAI uses standardized error responses across all API endpoints. This guide covers error formats, error codes, HTTP status codes, and troubleshooting common errors.

---

## Table of Contents

- [Error Response Format](#error-response-format)
- [HTTP Status Codes](#http-status-codes)
- [Error Code Reference](#error-code-reference)
- [Common Errors](#common-errors)
- [Error Handling Best Practices](#error-handling-best-practices)
- [Troubleshooting Guide](#troubleshooting-guide)

---

## Error Response Format

All error responses follow a consistent JSON structure:

### Standard Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `false` for errors |
| `error.code` | string | Machine-readable error code (e.g., "AUTH_001") |
| `error.message` | string | Human-readable error message |
| `error.details` | object/array | Additional context (optional) |

### Examples

#### Simple Error

```json
{
  "success": false,
  "error": {
    "code": "AUTH_001",
    "message": "Invalid email or password."
  }
}
```

#### Error with Details

```json
{
  "success": false,
  "error": {
    "code": "RES_003",
    "message": "Validation error.",
    "details": {
      "email": ["This field is required."],
      "password": ["Password must be at least 8 characters."]
    }
  }
}
```

#### Error with Additional Context

```json
{
  "success": false,
  "error": {
    "code": "SUB_001",
    "message": "Insufficient tokens. Please upgrade your subscription.",
    "details": {
      "tokens_required": 500,
      "tokens_available": 50,
      "tokens_needed": 450,
      "upgrade_url": "https://multinotesai.com/pricing"
    }
  }
}
```

---

## HTTP Status Codes

MultinotesAI uses standard HTTP status codes to indicate request outcomes:

### Success Codes (2xx)

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted for processing |
| 204 | No Content | Successful request with no response body |

### Client Error Codes (4xx)

| Code | Name | Description |
|------|------|-------------|
| 400 | Bad Request | Invalid request data or parameters |
| 401 | Unauthorized | Authentication required or invalid token |
| 402 | Payment Required | Subscription upgrade or payment needed |
| 403 | Forbidden | Authenticated but insufficient permissions |
| 404 | Not Found | Resource not found |
| 405 | Method Not Allowed | HTTP method not supported for endpoint |
| 409 | Conflict | Request conflicts with existing resource |
| 413 | Payload Too Large | Request entity exceeds size limit |
| 422 | Unprocessable Entity | Valid request but semantic errors |
| 429 | Too Many Requests | Rate limit exceeded |

### Server Error Codes (5xx)

| Code | Name | Description |
|------|------|-------------|
| 500 | Internal Server Error | Unexpected server error |
| 502 | Bad Gateway | Invalid response from upstream server |
| 503 | Service Unavailable | Service temporarily unavailable |
| 504 | Gateway Timeout | Upstream server timeout |

---

## Error Code Reference

Error codes follow a pattern: `CATEGORY_NUMBER`

### Authentication Errors (AUTH_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| AUTH_001 | 401 | Invalid email or password | Login credentials incorrect |
| AUTH_002 | 400 | Email already exists | Email is already registered |
| AUTH_003 | 400 | Username already exists | Username is taken |
| AUTH_004 | 403 | User account blocked | Account has been blocked by admin |
| AUTH_005 | 403 | Email not verified | Email verification required |
| AUTH_006 | 401 | Invalid token | Token is malformed or invalid |
| AUTH_007 | 401 | Token expired | Token has expired |
| AUTH_008 | 403 | Permission denied | Insufficient permissions |

**Example:**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_007",
    "message": "Token is expired or invalid.",
    "details": {
      "token_type": "access",
      "expired_at": "2024-01-20T15:45:00Z",
      "current_time": "2024-01-20T16:00:00Z"
    }
  }
}
```

### Subscription Errors (SUB_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| SUB_001 | 402 | Insufficient tokens | Not enough tokens for operation |
| SUB_002 | 402 | Subscription expired | Subscription has expired |
| SUB_003 | 402 | Storage limit exceeded | Storage quota exceeded |
| SUB_004 | 404 | Subscription not found | No active subscription |
| SUB_005 | 409 | Subscription already active | Active subscription exists |

**Example:**
```json
{
  "success": false,
  "error": {
    "code": "SUB_001",
    "message": "Insufficient tokens. Please upgrade your subscription.",
    "details": {
      "tokens_required": 500,
      "tokens_available": 50,
      "current_plan": "Free",
      "suggested_plan": "Pro",
      "upgrade_url": "/pricing"
    }
  }
}
```

### LLM Errors (LLM_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| LLM_001 | 400 | AI model not found | Requested model doesn't exist |
| LLM_002 | 503 | AI model disconnected | Model temporarily unavailable |
| LLM_003 | 500 | Content generation failed | Error during generation |
| LLM_004 | 429 | AI rate limit exceeded | AI generation rate limit hit |
| LLM_005 | 400 | Invalid input | Prompt or parameters invalid |

**Example:**
```json
{
  "success": false,
  "error": {
    "code": "LLM_003",
    "message": "An error occurred during content generation.",
    "details": {
      "model_id": 1,
      "model_name": "GPT-4",
      "error_type": "timeout",
      "retry_possible": true
    }
  }
}
```

### Payment Errors (PAY_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| PAY_001 | 400 | Invalid payment details | Payment information incorrect |
| PAY_002 | 400 | Payment failed | Payment processing failed |
| PAY_003 | 400 | Invalid coupon | Coupon code invalid |
| PAY_004 | 400 | Coupon expired | Coupon has expired |
| PAY_005 | 404 | Payment order not found | Order ID not found |
| PAY_006 | 400 | Invalid signature | Payment signature verification failed |

**Example:**
```json
{
  "success": false,
  "error": {
    "code": "PAY_002",
    "message": "Payment processing failed. Please try again.",
    "details": {
      "payment_id": "pay_xyz123",
      "failure_code": "card_declined",
      "failure_message": "Your card was declined by your bank.",
      "retry_allowed": true,
      "next_steps": "Please contact your bank or try a different card."
    }
  }
}
```

### Resource Errors (RES_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| RES_001 | 404 | Resource not found | Requested resource doesn't exist |
| RES_002 | 409 | Resource already exists | Duplicate resource |
| RES_003 | 400 | Invalid data | Request data validation failed |
| RES_004 | 413 | File too large | File exceeds size limit |
| RES_005 | 400 | Invalid file type | File type not supported |

**Example:**
```json
{
  "success": false,
  "error": {
    "code": "RES_004",
    "message": "File size exceeds the maximum allowed limit.",
    "details": {
      "file_size": 52428800,
      "max_size": 10485760,
      "file_size_mb": 50,
      "max_size_mb": 10,
      "current_plan": "Free",
      "upgrade_required": "Basic"
    }
  }
}
```

### Server Errors (SRV_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| SRV_001 | 500 | Internal server error | Unexpected server error |
| SRV_002 | 503 | Service unavailable | Service temporarily down |
| SRV_003 | 429 | Rate limit exceeded | Too many requests |

**Example:**
```json
{
  "success": false,
  "error": {
    "code": "SRV_003",
    "message": "Request was throttled. Please wait 3600 seconds.",
    "details": {
      "limit": 1000,
      "window": "hour",
      "retry_after": 3600,
      "reset_at": "2024-01-20T16:00:00Z"
    }
  }
}
```

---

## Common Errors

### 1. Invalid Credentials

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_001",
    "message": "Invalid email or password."
  }
}
```

**Causes:**
- Incorrect email address
- Wrong password
- Account doesn't exist

**Solutions:**
- Verify email and password
- Use "Forgot Password" to reset
- Check if using social login instead

### 2. Token Expired

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_007",
    "message": "Token is expired or invalid."
  }
}
```

**Causes:**
- Access token expired (15 min default)
- Token was revoked
- Invalid token format

**Solutions:**
- Use refresh token to get new access token
- Re-authenticate if refresh token expired
- Check token format and storage

**Example Fix:**
```javascript
async function makeAuthenticatedRequest(url, options) {
  let response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`
    }
  });

  // Handle 401 - token expired
  if (response.status === 401) {
    const errorData = await response.json();

    if (errorData.error.code === 'AUTH_007') {
      // Try to refresh token
      const newToken = await refreshAccessToken();

      // Retry request with new token
      response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${newToken}`
        }
      });
    }
  }

  return response;
}
```

### 3. Insufficient Tokens

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "SUB_001",
    "message": "Insufficient tokens. Please upgrade your subscription.",
    "details": {
      "tokens_required": 500,
      "tokens_available": 50
    }
  }
}
```

**Causes:**
- Used all allocated tokens for current period
- Requesting expensive operation

**Solutions:**
- Wait for token refresh (daily/monthly)
- Upgrade subscription plan
- Optimize token usage

### 4. Rate Limit Exceeded

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "SRV_003",
    "message": "Rate limit exceeded. Please wait 3600 seconds.",
    "details": {
      "retry_after": 3600
    }
  }
}
```

**Causes:**
- Too many requests in time window
- Burst of requests

**Solutions:**
- Implement exponential backoff
- Use rate limit headers to pace requests
- Upgrade plan for higher limits

**Example Fix:**
```javascript
async function makeRequestWithBackoff(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fetch(url, options);

    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After');
      const delay = parseInt(retryAfter) * 1000;

      console.log(`Rate limited. Waiting ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
      continue;
    }

    return response;
  }

  throw new Error('Max retries exceeded');
}
```

### 5. Validation Errors

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "RES_003",
    "message": "Validation error.",
    "details": {
      "email": ["Enter a valid email address."],
      "password": [
        "Password must be at least 8 characters.",
        "Password must contain at least one uppercase letter."
      ]
    }
  }
}
```

**Causes:**
- Missing required fields
- Invalid data format
- Failed validation rules

**Solutions:**
- Check all required fields are provided
- Validate data format before sending
- Review API documentation for requirements

**Example Fix:**
```javascript
function validateRegistrationData(data) {
  const errors = {};

  // Email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!data.email) {
    errors.email = ['Email is required'];
  } else if (!emailRegex.test(data.email)) {
    errors.email = ['Enter a valid email address'];
  }

  // Password validation
  if (!data.password) {
    errors.password = ['Password is required'];
  } else {
    const passwordErrors = [];
    if (data.password.length < 8) {
      passwordErrors.push('Password must be at least 8 characters');
    }
    if (!/[A-Z]/.test(data.password)) {
      passwordErrors.push('Password must contain at least one uppercase letter');
    }
    if (!/[a-z]/.test(data.password)) {
      passwordErrors.push('Password must contain at least one lowercase letter');
    }
    if (!/[0-9]/.test(data.password)) {
      passwordErrors.push('Password must contain at least one number');
    }
    if (passwordErrors.length > 0) {
      errors.password = passwordErrors;
    }
  }

  return Object.keys(errors).length > 0 ? errors : null;
}

// Use before API call
const validationErrors = validateRegistrationData(formData);
if (validationErrors) {
  displayErrors(validationErrors);
  return;
}

// Proceed with API call
await registerUser(formData);
```

### 6. File Upload Errors

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "RES_004",
    "message": "File size exceeds the maximum allowed limit.",
    "details": {
      "file_size_mb": 50,
      "max_size_mb": 10
    }
  }
}
```

**Causes:**
- File too large for current plan
- Unsupported file type
- Storage quota exceeded

**Solutions:**
- Compress file before upload
- Upgrade plan for larger file limits
- Delete old files to free up storage

**Example Fix:**
```javascript
async function validateAndUploadFile(file) {
  const maxSizeMB = 10;
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];

  // Check file size
  const fileSizeMB = file.size / 1024 / 1024;
  if (fileSizeMB > maxSizeMB) {
    throw new Error(`File too large. Maximum size is ${maxSizeMB}MB`);
  }

  // Check file type
  if (!allowedTypes.includes(file.type)) {
    throw new Error(`File type not supported. Allowed types: ${allowedTypes.join(', ')}`);
  }

  // Upload file
  const formData = new FormData();
  formData.append('image', file);

  const response = await fetch('https://api.multinotesai.com/authentication/uploadImage/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    },
    body: formData
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error.message);
  }

  return response.json();
}
```

### 7. Payment Failures

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "PAY_002",
    "message": "Payment processing failed. Please try again.",
    "details": {
      "failure_code": "card_declined"
    }
  }
}
```

**Causes:**
- Card declined by bank
- Insufficient funds
- Invalid card details
- Payment gateway issue

**Solutions:**
- Contact bank about decline
- Try different payment method
- Verify card details are correct
- Check if card supports international payments

---

## Error Handling Best Practices

### 1. Always Check Response Status

```javascript
async function makeAPICall(url, options) {
  const response = await fetch(url, options);

  if (!response.ok) {
    const error = await response.json();
    handleAPIError(error, response.status);
    return null;
  }

  return response.json();
}
```

### 2. Handle Errors by Category

```javascript
function handleAPIError(error, status) {
  const errorCode = error.error.code;

  // Authentication errors
  if (errorCode.startsWith('AUTH_')) {
    handleAuthError(error);
  }
  // Subscription errors
  else if (errorCode.startsWith('SUB_')) {
    handleSubscriptionError(error);
  }
  // Payment errors
  else if (errorCode.startsWith('PAY_')) {
    handlePaymentError(error);
  }
  // Generic errors
  else {
    handleGenericError(error);
  }
}

function handleAuthError(error) {
  if (error.error.code === 'AUTH_007') {
    // Token expired - try refresh
    refreshToken();
  } else if (error.error.code === 'AUTH_001') {
    // Invalid credentials - show error
    showLoginError('Invalid email or password');
  }
}

function handleSubscriptionError(error) {
  if (error.error.code === 'SUB_001') {
    // Insufficient tokens - offer upgrade
    showUpgradeDialog(error.error.details);
  }
}
```

### 3. Display User-Friendly Messages

```javascript
const ERROR_MESSAGES = {
  'AUTH_001': 'Invalid login credentials. Please check your email and password.',
  'AUTH_007': 'Your session has expired. Please login again.',
  'SUB_001': 'You\'ve run out of AI tokens. Upgrade your plan to continue.',
  'RES_004': 'File is too large. Please choose a smaller file.',
  'SRV_003': 'You\'re sending requests too quickly. Please slow down.'
};

function getUserFriendlyMessage(error) {
  return ERROR_MESSAGES[error.error.code] || error.error.message;
}

// Usage
try {
  await makeAPICall();
} catch (error) {
  showNotification({
    type: 'error',
    message: getUserFriendlyMessage(error)
  });
}
```

### 4. Log Errors for Debugging

```javascript
function logError(error, context) {
  console.error('API Error:', {
    code: error.error.code,
    message: error.error.message,
    details: error.error.details,
    context: context,
    timestamp: new Date().toISOString(),
    user_id: getCurrentUserId(),
    url: context.url
  });

  // Send to error tracking service
  if (typeof Sentry !== 'undefined') {
    Sentry.captureException(error, {
      extra: context
    });
  }
}
```

### 5. Retry on Transient Errors

```javascript
const RETRYABLE_ERROR_CODES = ['LLM_002', 'LLM_003', 'SRV_001', 'SRV_002'];

async function makeRequestWithRetry(url, options, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url, options);

      if (response.ok) {
        return response.json();
      }

      const error = await response.json();

      // Retry on transient errors
      if (RETRYABLE_ERROR_CODES.includes(error.error.code) && attempt < maxRetries - 1) {
        const delay = Math.pow(2, attempt) * 1000;
        console.log(`Retrying after ${delay}ms (attempt ${attempt + 1}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }

      throw error;
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;
      }
    }
  }
}
```

---

## Troubleshooting Guide

### Authentication Issues

**Problem:** Can't login

**Checklist:**
- [ ] Email address is correct (case-insensitive)
- [ ] Password is correct (case-sensitive)
- [ ] Account exists (check if using social login)
- [ ] Email is verified
- [ ] Account is not blocked
- [ ] Not hitting rate limit (5 attempts/minute)

**Debug Steps:**
1. Try "Forgot Password" flow
2. Check if registration email was received
3. Verify using correct authentication method (email vs. social)

---

**Problem:** Token keeps expiring

**Checklist:**
- [ ] Implementing token refresh properly
- [ ] Storing tokens securely
- [ ] Not exposing tokens in URLs or logs
- [ ] Handling 401 responses correctly

**Debug Steps:**
1. Check token expiration time in JWT payload
2. Verify refresh token is valid
3. Implement automatic token refresh

---

### Payment Issues

**Problem:** Payment fails

**Checklist:**
- [ ] Card details are correct
- [ ] Card has sufficient funds
- [ ] Card supports international payments
- [ ] Not using a prepaid card (if restricted)
- [ ] Payment signature is valid

**Debug Steps:**
1. Check error details for failure reason
2. Try different payment method
3. Contact bank if card declined
4. Verify Razorpay integration

---

### API Request Issues

**Problem:** Getting 404 errors

**Checklist:**
- [ ] Endpoint URL is correct
- [ ] Using correct HTTP method
- [ ] Resource ID exists
- [ ] User has access to resource
- [ ] API version in URL is correct

**Debug Steps:**
1. Check API documentation for correct endpoint
2. Verify resource exists
3. Check user permissions

---

**Problem:** Slow API responses

**Checklist:**
- [ ] Network connection is stable
- [ ] Not hitting rate limits
- [ ] Request payload is not too large
- [ ] Using appropriate endpoints

**Debug Steps:**
1. Check response time headers
2. Monitor rate limit headers
3. Use pagination for large datasets
4. Consider upgrading plan for better performance

---

## Error Monitoring

### Recommended Tools

- **Sentry:** Real-time error tracking
- **Datadog:** Full-stack monitoring
- **LogRocket:** Session replay with errors
- **New Relic:** Application performance monitoring

### Setup Example (Sentry)

```javascript
import * as Sentry from "@sentry/browser";

Sentry.init({
  dsn: "YOUR_SENTRY_DSN",
  integrations: [new Sentry.BrowserTracing()],
  tracesSampleRate: 1.0,
});

// Capture API errors
async function makeAPICall(url, options) {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const error = await response.json();

      // Send to Sentry
      Sentry.captureException(new Error(error.error.message), {
        extra: {
          error_code: error.error.code,
          error_details: error.error.details,
          endpoint: url,
          status: response.status
        },
        tags: {
          error_category: error.error.code.split('_')[0]
        }
      });

      throw error;
    }

    return response.json();
  } catch (error) {
    Sentry.captureException(error);
    throw error;
  }
}
```

---

## Support

For error-related support:
- Email: support@multinotesai.com
- API Support: api-support@multinotesai.com
- Documentation: https://docs.multinotesai.com
- Status Page: https://status.multinotesai.com

### Reporting Bugs

When reporting errors, include:
1. Error code and message
2. Request URL and method
3. Request payload (without sensitive data)
4. User ID (if applicable)
5. Timestamp
6. Steps to reproduce

**Example Bug Report:**

```
Error Code: LLM_003
Message: An error occurred during content generation
Endpoint: POST /coreapp/openai_text_to_text/
User ID: 123
Timestamp: 2024-01-20T15:30:00Z

Steps to reproduce:
1. Login as user 123
2. Navigate to AI generation page
3. Enter prompt: "Write a story..."
4. Select GPT-4 model
5. Click "Generate"
6. Error occurs after 30 seconds

Expected: Generated text response
Actual: LLM_003 error
```
