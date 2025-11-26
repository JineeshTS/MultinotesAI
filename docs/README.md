# MultinotesAI API Documentation

Welcome to the MultinotesAI API documentation! This directory contains comprehensive guides for integrating with and using the MultinotesAI API.

## Documentation Overview

### API Documentation

1. **[API_REFERENCE.md](./API_REFERENCE.md)** - Complete API endpoint reference
   - All available endpoints with examples
   - Request/response formats
   - Authentication methods
   - cURL examples for every endpoint
   - Pagination and filtering
   - Admin endpoints

2. **[AUTHENTICATION.md](./AUTHENTICATION.md)** - Authentication & security guide
   - JWT token flow and management
   - Token refresh mechanism
   - Social authentication (Google, Facebook, Apple)
   - API key authentication for programmatic access
   - Security best practices
   - Session management

3. **[WEBHOOKS.md](./WEBHOOKS.md)** - Webhook integration guide
   - Available webhook events
   - Payload format for each event type
   - Signature verification for security
   - Retry policy and idempotency
   - Example implementations in Node.js, Python, PHP

4. **[RATE_LIMITS.md](./RATE_LIMITS.md)** - Rate limiting documentation
   - Rate limits per endpoint and subscription tier
   - Rate limit headers
   - Best practices for handling limits
   - Request queuing and throttling
   - Enterprise tier limits

5. **[ERRORS.md](./ERRORS.md)** - Error handling guide
   - Standard error response format
   - Complete list of error codes
   - Troubleshooting common errors
   - Error handling best practices
   - HTTP status codes reference

## Quick Start

### 1. Authentication

Register a new account:

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

Login to get JWT tokens:

```bash
curl -X POST https://api.multinotesai.com/authentication/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

### 2. Make Authenticated Requests

Use the access token in the Authorization header:

```bash
curl -X GET https://api.multinotesai.com/authentication/get-user/123/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Generate AI Content

```bash
curl -X POST https://api.multinotesai.com/coreapp/openai_text_to_text/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a creative story about AI",
    "model_id": 1,
    "max_tokens": 500
  }'
```

## API Base URL

**Production:** `https://api.multinotesai.com/`

## Response Format

All API responses follow a standard format:

**Success:**
```json
{
  "success": true,
  "data": {
    // Response data
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  }
}
```

## Rate Limits

Check rate limit headers in every response:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642780800
```

See [RATE_LIMITS.md](./RATE_LIMITS.md) for complete rate limiting documentation.

## Subscription Tiers

| Plan | Price | Requests/Hour | AI Generations/Hour | Storage |
|------|-------|---------------|---------------------|---------|
| Free | $0 | 1,000 | 10 | 1 GB |
| Basic | $9.99 | 5,000 | 50 | 10 GB |
| Pro | $29.99 | 20,000 | 200 | 100 GB |
| Enterprise | $99.99 | Unlimited | 1,000 | 1 TB |

## SDK & Libraries

### JavaScript/TypeScript

```bash
npm install @multinotesai/sdk
```

```javascript
import { MultinotesAI } from '@multinotesai/sdk';

const client = new MultinotesAI({
  apiKey: 'YOUR_API_KEY'
});

const result = await client.generateText({
  prompt: 'Write a story',
  model: 'gpt-4'
});
```

### Python

```bash
pip install multinotesai
```

```python
from multinotesai import Client

client = Client(api_key='YOUR_API_KEY')

result = client.generate_text(
    prompt='Write a story',
    model='gpt-4'
)
```

## Support & Resources

- **Email:** api-support@multinotesai.com
- **Documentation:** https://docs.multinotesai.com
- **Developer Portal:** https://developers.multinotesai.com
- **Status Page:** https://status.multinotesai.com
- **Community Forum:** https://community.multinotesai.com

## Changelog

See [CHANGELOG.md](../CHANGELOG.md) for API version history and updates.

## Contributing

Found an issue in the documentation? Please submit an issue or pull request on GitHub.

## License

Copyright © 2024 MultinotesAI. All rights reserved.
