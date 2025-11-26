# MultinotesAI Rate Limiting Guide

## Overview

MultinotesAI implements rate limiting to ensure fair usage and system stability. This guide explains rate limits, how to check your current usage, and best practices for handling rate limits.

---

## Table of Contents

- [Rate Limit Tiers](#rate-limit-tiers)
- [Endpoint-Specific Limits](#endpoint-specific-limits)
- [Rate Limit Headers](#rate-limit-headers)
- [Handling Rate Limits](#handling-rate-limits)
- [Best Practices](#best-practices)
- [Enterprise Tier Limits](#enterprise-tier-limits)

---

## Rate Limit Tiers

Rate limits vary based on your subscription plan and authentication method.

### Subscription-Based Limits

| Plan | Requests/Hour | Requests/Minute | AI Generations/Hour | Image Generations/Hour | File Uploads/Day |
|------|---------------|-----------------|---------------------|------------------------|------------------|
| **Anonymous** | 100 | 10 | N/A | N/A | N/A |
| **Free** | 1000 | 60 | 10 | 5 | 10 |
| **Basic** | 5000 | 100 | 50 | 20 | 50 |
| **Pro** | 20000 | 300 | 200 | 100 | 200 |
| **Enterprise** | Unlimited* | 1000 | 1000 | 500 | 1000 |

*Enterprise tier has effectively unlimited requests but implements soft limits to prevent abuse.

### Authentication Method Limits

| Method | Default Limit | Notes |
|--------|---------------|-------|
| JWT Token (User) | Based on subscription tier | Per user account |
| API Key | Custom per key | Configurable when creating key |
| Anonymous | 100/hour | Per IP address |

---

## Endpoint-Specific Limits

Different endpoints have different rate limit rules based on resource intensity.

### Authentication Endpoints

To prevent brute force attacks and abuse:

| Endpoint | Limit | Window | Scope |
|----------|-------|--------|-------|
| `/authentication/v1/login/` | 5 requests | 1 minute | Per IP |
| `/authentication/v1/login/` | 20 requests | 1 hour | Per IP |
| `/authentication/v1/register/` | 5 requests | 1 hour | Per IP |
| `/authentication/v1/forgot-password/` | 3 requests | 1 hour | Per email |
| `/authentication/v1/reset-password/` | 10 requests | 1 hour | Per IP |
| `/authentication/v1/verify-email-token/` | 10 requests | 1 hour | Per IP |

**Example Response When Rate Limited:**
```json
{
  "success": false,
  "error": {
    "code": "SRV_003",
    "message": "Too many login attempts. Please wait 60 seconds before trying again."
  }
}
```

**HTTP Status:** `429 Too Many Requests`

### AI Generation Endpoints

AI generation endpoints have tiered limits based on computational cost:

#### Text Generation

| Plan | Requests/Hour | Concurrent Requests | Max Tokens/Request |
|------|---------------|---------------------|-------------------|
| Free | 10 | 1 | 500 |
| Basic | 50 | 2 | 2000 |
| Pro | 200 | 5 | 4000 |
| Enterprise | 1000 | 20 | 8000 |

**Endpoints:**
- `/coreapp/openai_text_to_text/`
- `/coreapp/mistral_text_to_text/`
- `/coreapp/llama2_text_to_text/`
- `/coreapp/gemini_pro_text_to_text/`

#### Image Generation

| Plan | Requests/Hour | Concurrent Requests | Max Image Size |
|------|---------------|---------------------|----------------|
| Free | 5 | 1 | 512x512 |
| Basic | 20 | 1 | 1024x1024 |
| Pro | 100 | 3 | 1024x1024 |
| Enterprise | 500 | 10 | 1024x1024 |

**Endpoints:**
- `/coreapp/gemini_text_to_image/`
- `/coreapp/gemini_picture_to_text/`

#### Streaming Endpoints

For real-time streaming AI responses:

| Plan | Requests/Hour | Concurrent Streams |
|------|---------------|--------------------|
| Free | 5 | 1 |
| Basic | 30 | 2 |
| Pro | 100 | 5 |
| Enterprise | 10000 | 50 |

### File Upload Endpoints

| Plan | Uploads/Day | Uploads/Hour | Max File Size | Total Storage |
|------|-------------|--------------|---------------|---------------|
| Free | 10 | 5 | 5 MB | 1 GB |
| Basic | 50 | 20 | 25 MB | 10 GB |
| Pro | 200 | 50 | 100 MB | 100 GB |
| Enterprise | 1000 | 200 | 500 MB | 1 TB |

**Endpoints:**
- `/authentication/uploadImage/`
- `/coreapp/upload_data/`
- `/authentication/upload_complete_data/`

### Payment Endpoints

Payment endpoints have strict limits to prevent abuse:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/planandsubscription/payment/create-order/` | 10 | 1 hour |
| `/planandsubscription/payment/verify/` | 20 | 1 hour |
| `/planandsubscription/payment/refund/` | 5 | 1 hour |
| `/planandsubscription/payment/webhook/` | 100 | 1 minute |

### Admin Endpoints

For admin/staff users:

| Endpoint Type | Limit |
|---------------|-------|
| Admin Dashboard | 5000/hour |
| User Management | 1000/hour |
| Reports & Analytics | 500/hour |

---

## Rate Limit Headers

Every API response includes headers showing your current rate limit status:

### Standard Headers

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642784400
X-RateLimit-Reset-After: 3540
```

**Header Descriptions:**

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Maximum requests allowed in the window | `1000` |
| `X-RateLimit-Remaining` | Requests remaining in current window | `995` |
| `X-RateLimit-Reset` | Unix timestamp when limit resets | `1642784400` |
| `X-RateLimit-Reset-After` | Seconds until limit resets | `3540` |

### When Rate Limited (429 Response)

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642784400
X-RateLimit-Reset-After: 3540
Retry-After: 3540
```

**Additional Headers:**

| Header | Description |
|--------|-------------|
| `Retry-After` | Seconds to wait before retrying |
| `X-RateLimit-Type` | Type of limit hit (e.g., "user", "ai_generation") |

**Response Body:**
```json
{
  "success": false,
  "error": {
    "code": "SRV_003",
    "message": "Rate limit exceeded. Please wait 3540 seconds before making additional requests.",
    "details": {
      "limit": 1000,
      "window": "hour",
      "retry_after": 3540,
      "reset_at": "2024-01-20T15:00:00Z"
    }
  }
}
```

### API Key-Specific Headers

When using API keys, you'll see additional headers:

```http
X-API-Key-Limit: 5000
X-API-Key-Remaining: 4987
X-API-Key-Reset: 1642784400
```

---

## Handling Rate Limits

### 1. Detecting Rate Limits

**Check Response Status Code:**
```javascript
async function makeRequest(url, options) {
  const response = await fetch(url, options);

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    console.log(`Rate limited. Retry after ${retryAfter} seconds`);

    // Handle rate limit
    await handleRateLimit(retryAfter);
  }

  return response;
}
```

**Check Headers Proactively:**
```javascript
async function makeRequest(url, options) {
  const response = await fetch(url, options);

  const remaining = parseInt(response.headers.get('X-RateLimit-Remaining'));
  const limit = parseInt(response.headers.get('X-RateLimit-Limit'));

  // Warn when getting close to limit
  if (remaining < limit * 0.1) {
    console.warn(`Rate limit warning: ${remaining}/${limit} requests remaining`);
  }

  return response;
}
```

### 2. Exponential Backoff

Implement exponential backoff when rate limited:

```javascript
async function makeRequestWithBackoff(url, options, maxRetries = 3) {
  let retries = 0;

  while (retries < maxRetries) {
    try {
      const response = await fetch(url, options);

      if (response.status === 429) {
        // Get retry delay from header or calculate exponentially
        const retryAfter = response.headers.get('Retry-After');
        const delay = retryAfter
          ? parseInt(retryAfter) * 1000
          : Math.min(1000 * Math.pow(2, retries), 60000);

        console.log(`Rate limited. Waiting ${delay}ms before retry ${retries + 1}/${maxRetries}`);
        await sleep(delay);

        retries++;
        continue;
      }

      return response;
    } catch (error) {
      console.error('Request failed:', error);
      throw error;
    }
  }

  throw new Error('Max retries exceeded');
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

### 3. Request Queuing

Queue requests to stay within rate limits:

```javascript
class RateLimitedClient {
  constructor(maxRequestsPerHour = 1000) {
    this.maxRequests = maxRequestsPerHour;
    this.queue = [];
    this.requestTimes = [];
  }

  async request(url, options) {
    // Wait if at limit
    await this.waitIfNeeded();

    // Make request
    const response = await fetch(url, options);

    // Track request time
    this.requestTimes.push(Date.now());

    return response;
  }

  async waitIfNeeded() {
    const now = Date.now();
    const oneHourAgo = now - 3600000;

    // Remove requests older than 1 hour
    this.requestTimes = this.requestTimes.filter(time => time > oneHourAgo);

    // Wait if at limit
    if (this.requestTimes.length >= this.maxRequests) {
      const oldestRequest = this.requestTimes[0];
      const waitTime = oldestRequest + 3600000 - now;

      console.log(`Rate limit reached. Waiting ${waitTime}ms`);
      await sleep(waitTime);
    }
  }
}

// Usage
const client = new RateLimitedClient(1000);

async function generateText(prompt) {
  return client.request('https://api.multinotesai.com/coreapp/openai_text_to_text/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ prompt, model_id: 1 })
  });
}
```

### 4. Batch Requests

For bulk operations, batch requests to minimize API calls:

```javascript
// Instead of individual requests
for (const item of items) {
  await createContent(item); // Many API calls
}

// Batch items together
const batches = chunk(items, 50); // Create batches of 50
for (const batch of batches) {
  await createContentBatch(batch); // Single API call per batch
}
```

### 5. Caching

Cache responses to reduce API calls:

```javascript
class CachedClient {
  constructor() {
    this.cache = new Map();
    this.cacheDuration = 300000; // 5 minutes
  }

  async request(url, options) {
    const cacheKey = this.getCacheKey(url, options);

    // Check cache
    const cached = this.cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < this.cacheDuration) {
      console.log('Cache hit:', cacheKey);
      return cached.response;
    }

    // Make request
    const response = await fetch(url, options);

    // Cache response
    this.cache.set(cacheKey, {
      response: await response.clone().json(),
      timestamp: Date.now()
    });

    return response;
  }

  getCacheKey(url, options) {
    return `${options.method || 'GET'}:${url}:${JSON.stringify(options.body || {})}`;
  }

  clearCache() {
    this.cache.clear();
  }
}
```

---

## Best Practices

### 1. Monitor Your Usage

Track rate limit headers to monitor usage:

```javascript
function trackRateLimits(response) {
  const metrics = {
    limit: response.headers.get('X-RateLimit-Limit'),
    remaining: response.headers.get('X-RateLimit-Remaining'),
    reset: response.headers.get('X-RateLimit-Reset'),
    timestamp: new Date().toISOString()
  };

  // Log to monitoring service
  analytics.track('rate_limit_status', metrics);

  // Alert if usage is high
  const usagePercent = ((metrics.limit - metrics.remaining) / metrics.limit) * 100;
  if (usagePercent > 80) {
    alertTeam(`Rate limit usage at ${usagePercent.toFixed(2)}%`);
  }
}
```

### 2. Implement Circuit Breakers

Prevent cascading failures when rate limited:

```javascript
class CircuitBreaker {
  constructor(threshold = 5, timeout = 60000) {
    this.failureCount = 0;
    this.threshold = threshold;
    this.timeout = timeout;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    this.nextAttempt = Date.now();
  }

  async execute(fn) {
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttempt) {
        throw new Error('Circuit breaker is OPEN');
      }
      this.state = 'HALF_OPEN';
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;
    this.state = 'CLOSED';
  }

  onFailure() {
    this.failureCount++;
    if (this.failureCount >= this.threshold) {
      this.state = 'OPEN';
      this.nextAttempt = Date.now() + this.timeout;
      console.log(`Circuit breaker opened. Will retry at ${new Date(this.nextAttempt)}`);
    }
  }
}

// Usage
const breaker = new CircuitBreaker();

async function makeAPICall() {
  return breaker.execute(async () => {
    const response = await fetch('https://api.multinotesai.com/...');
    if (response.status === 429) {
      throw new Error('Rate limited');
    }
    return response.json();
  });
}
```

### 3. Optimize Request Patterns

**Good Practices:**
- ✅ Batch requests when possible
- ✅ Cache frequently accessed data
- ✅ Use webhooks instead of polling
- ✅ Implement pagination for large datasets
- ✅ Make requests asynchronously

**Bad Practices:**
- ❌ Polling APIs in tight loops
- ❌ Making redundant requests
- ❌ Not caching static data
- ❌ Fetching all data when only subset needed

### 4. Use Appropriate Subscription Tier

Monitor your usage patterns and upgrade if consistently hitting limits:

```javascript
// Track API usage over time
function analyzeUsagePatterns() {
  const usage = getAPIUsageMetrics(); // Your metrics

  if (usage.rateLimitHits > 10 && usage.plan === 'Free') {
    console.warn('Consider upgrading to Basic plan');
    suggestPlanUpgrade('Basic');
  }

  if (usage.averageRequestsPerHour > 4000 && usage.plan === 'Basic') {
    console.warn('Consider upgrading to Pro plan');
    suggestPlanUpgrade('Pro');
  }
}
```

### 5. Handle Gracefully in UI

Show user-friendly messages when rate limited:

```javascript
async function handleAPICall() {
  try {
    const response = await fetch(apiUrl, options);

    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After');

      showUserMessage({
        type: 'warning',
        message: `You've reached your usage limit. Please try again in ${formatDuration(retryAfter)}.`,
        action: {
          text: 'Upgrade Plan',
          onClick: () => window.location.href = '/pricing'
        }
      });

      return null;
    }

    return response.json();
  } catch (error) {
    console.error('API call failed:', error);
    showUserMessage({
      type: 'error',
      message: 'Something went wrong. Please try again later.'
    });
  }
}

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds} seconds`;
  if (seconds < 3600) return `${Math.ceil(seconds / 60)} minutes`;
  return `${Math.ceil(seconds / 3600)} hours`;
}
```

---

## Enterprise Tier Limits

Enterprise customers have customizable rate limits based on their needs.

### Custom Limits

Enterprise plans can request custom rate limits for:

- **API Requests:** Up to 1M requests/hour
- **AI Generations:** Unlimited with fair use policy
- **Concurrent Requests:** Up to 100 simultaneous
- **File Storage:** Custom storage allocation
- **Dedicated IP Whitelist:** For higher limits

### Fair Use Policy

Enterprise tier implements a fair use policy instead of hard limits:

- Normal usage patterns are unlimited
- Sustained abuse triggers soft throttling
- Coordination with account manager for capacity planning

### Dedicated Infrastructure

Enterprise customers can opt for dedicated infrastructure:

- **Dedicated API Instances:** No shared rate limits
- **Custom SLA:** 99.99% uptime guarantee
- **Priority Queue:** Faster processing times
- **Reserved Capacity:** Guaranteed resources during peak times

### Contact for Enterprise

To discuss custom rate limits:
- Email: enterprise@multinotesai.com
- Sales: sales@multinotesai.com
- Phone: +1-800-MULTINOTES

---

## Checking Your Current Limits

### API Endpoint

**Get your current rate limit status:**

```bash
curl -X GET https://api.multinotesai.com/api/v1/rate-limits/status/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "plan": "Pro",
    "limits": {
      "general": {
        "limit": 20000,
        "remaining": 18234,
        "reset_at": "2024-01-20T16:00:00Z",
        "usage_percentage": 8.83
      },
      "ai_generation": {
        "limit": 200,
        "remaining": 156,
        "reset_at": "2024-01-20T16:00:00Z",
        "usage_percentage": 22.00
      },
      "image_generation": {
        "limit": 100,
        "remaining": 89,
        "reset_at": "2024-01-20T16:00:00Z",
        "usage_percentage": 11.00
      },
      "file_upload": {
        "limit": 200,
        "remaining": 193,
        "reset_at": "2024-01-21T00:00:00Z",
        "usage_percentage": 3.50
      }
    },
    "recommendations": [
      "Your AI generation usage is moderate. You're on track for the current hour."
    ]
  }
}
```

---

## Rate Limit Increase Requests

If you consistently hit rate limits on your current plan:

### Option 1: Upgrade Plan

Upgrade to a higher tier for immediate limit increase:
- Basic → Pro: 4x increase
- Pro → Enterprise: Effectively unlimited

### Option 2: Request Temporary Increase

For one-time events or migrations:

**Endpoint:** `POST /api/v1/rate-limits/increase-request/`

```bash
curl -X POST https://api.multinotesai.com/api/v1/rate-limits/increase-request/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Data migration from legacy system",
    "requested_limit": 50000,
    "duration_hours": 24,
    "details": "Migrating 10K user accounts with associated content"
  }'
```

Requests are reviewed within 24 hours.

---

## Support

For rate limit issues:
- Email: api-support@multinotesai.com
- Dashboard: View usage in Settings > API Usage
- Documentation: https://docs.multinotesai.com/rate-limits
