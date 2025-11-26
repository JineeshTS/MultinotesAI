# MultinotesAI Webhooks Documentation

## Overview

Webhooks allow you to receive real-time HTTP notifications when specific events occur in your MultinotesAI account. Instead of polling the API, webhooks push event data to your server as events happen.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Webhook Events](#webhook-events)
- [Payload Format](#payload-format)
- [Security & Verification](#security--verification)
- [Retry Policy](#retry-policy)
- [Best Practices](#best-practices)
- [Example Implementations](#example-implementations)

---

## Getting Started

### 1. Create a Webhook Endpoint

Create an HTTP endpoint on your server that can receive POST requests from MultinotesAI.

**Requirements:**
- Must be publicly accessible via HTTPS
- Must return a 2xx status code within 5 seconds
- Must validate webhook signatures

**Example endpoint:**
```
https://yourapp.com/webhooks/multinotesai
```

### 2. Register Your Webhook

**Endpoint:** `POST /api/v1/webhooks/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```bash
curl -X POST https://api.multinotesai.com/api/v1/webhooks/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourapp.com/webhooks/multinotesai",
    "events": [
      "subscription.created",
      "subscription.updated",
      "payment.succeeded",
      "ai.generation.completed"
    ],
    "description": "Production webhook endpoint"
  }'
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "wh_123456789",
    "url": "https://yourapp.com/webhooks/multinotesai",
    "events": [
      "subscription.created",
      "subscription.updated",
      "payment.succeeded",
      "ai.generation.completed"
    ],
    "secret": "whsec_AbCdEf123456789XyZ",
    "status": "active",
    "created_at": "2024-01-20T10:00:00Z"
  },
  "warning": "Store the webhook secret securely. It's used to verify webhook authenticity."
}
```

### 3. Test Your Webhook

**Endpoint:** `POST /api/v1/webhooks/{webhook_id}/test/`

```bash
curl -X POST https://api.multinotesai.com/api/v1/webhooks/wh_123456789/test/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

This sends a test event to your webhook endpoint.

---

## Webhook Events

### Subscription Events

#### subscription.created

Triggered when a new subscription is created.

**Payload:**
```json
{
  "id": "evt_abc123",
  "type": "subscription.created",
  "created_at": "2024-01-20T10:30:00Z",
  "data": {
    "object": "subscription",
    "subscription_id": 456,
    "user": {
      "id": 123,
      "email": "user@example.com",
      "name": "John Doe"
    },
    "plan": {
      "id": 3,
      "name": "Pro",
      "price": 29.99,
      "currency": "USD",
      "billing_period": "monthly"
    },
    "status": "active",
    "start_date": "2024-01-20T10:30:00Z",
    "end_date": "2024-02-20T10:30:00Z",
    "trial_end": null,
    "cancel_at_period_end": false
  }
}
```

#### subscription.updated

Triggered when a subscription is modified (upgrade, downgrade, settings change).

**Payload:**
```json
{
  "id": "evt_abc124",
  "type": "subscription.updated",
  "created_at": "2024-01-20T11:00:00Z",
  "data": {
    "object": "subscription",
    "subscription_id": 456,
    "user": {
      "id": 123,
      "email": "user@example.com"
    },
    "previous_plan": {
      "id": 2,
      "name": "Basic"
    },
    "current_plan": {
      "id": 3,
      "name": "Pro"
    },
    "status": "active",
    "changes": ["plan_id", "price"],
    "effective_date": "2024-01-20T11:00:00Z"
  }
}
```

#### subscription.cancelled

Triggered when a subscription is cancelled.

**Payload:**
```json
{
  "id": "evt_abc125",
  "type": "subscription.cancelled",
  "created_at": "2024-01-20T12:00:00Z",
  "data": {
    "object": "subscription",
    "subscription_id": 456,
    "user": {
      "id": 123,
      "email": "user@example.com"
    },
    "plan": {
      "id": 3,
      "name": "Pro"
    },
    "cancelled_at": "2024-01-20T12:00:00Z",
    "access_until": "2024-02-20T10:30:00Z",
    "cancellation_reason": "user_requested",
    "immediate": false
  }
}
```

#### subscription.expired

Triggered when a subscription expires without renewal.

**Payload:**
```json
{
  "id": "evt_abc126",
  "type": "subscription.expired",
  "created_at": "2024-02-20T10:30:00Z",
  "data": {
    "object": "subscription",
    "subscription_id": 456,
    "user": {
      "id": 123,
      "email": "user@example.com"
    },
    "plan": {
      "id": 3,
      "name": "Pro"
    },
    "expired_at": "2024-02-20T10:30:00Z",
    "reason": "payment_failed"
  }
}
```

---

### Payment Events

#### payment.succeeded

Triggered when a payment is successfully processed.

**Payload:**
```json
{
  "id": "evt_pay123",
  "type": "payment.succeeded",
  "created_at": "2024-01-20T10:35:00Z",
  "data": {
    "object": "payment",
    "payment_id": "pay_xyz789",
    "transaction_id": 1001,
    "user": {
      "id": 123,
      "email": "user@example.com"
    },
    "amount": 29.99,
    "currency": "USD",
    "payment_method": "card",
    "card_last4": "4242",
    "card_brand": "visa",
    "subscription_id": 456,
    "plan_name": "Pro",
    "status": "succeeded",
    "receipt_url": "https://multinotesai.com/receipts/txn_1001"
  }
}
```

#### payment.failed

Triggered when a payment fails.

**Payload:**
```json
{
  "id": "evt_pay124",
  "type": "payment.failed",
  "created_at": "2024-01-20T10:40:00Z",
  "data": {
    "object": "payment",
    "payment_id": "pay_xyz790",
    "user": {
      "id": 123,
      "email": "user@example.com"
    },
    "amount": 29.99,
    "currency": "USD",
    "payment_method": "card",
    "subscription_id": 456,
    "plan_name": "Pro",
    "status": "failed",
    "failure_code": "card_declined",
    "failure_message": "Your card was declined",
    "next_retry_at": "2024-01-21T10:40:00Z"
  }
}
```

#### payment.refunded

Triggered when a payment is refunded.

**Payload:**
```json
{
  "id": "evt_pay125",
  "type": "payment.refunded",
  "created_at": "2024-01-20T11:00:00Z",
  "data": {
    "object": "refund",
    "refund_id": "rfnd_abc123",
    "payment_id": "pay_xyz789",
    "user": {
      "id": 123,
      "email": "user@example.com"
    },
    "amount": 29.99,
    "currency": "USD",
    "reason": "requested_by_customer",
    "status": "succeeded",
    "refunded_at": "2024-01-20T11:00:00Z"
  }
}
```

---

### AI Generation Events

#### ai.generation.completed

Triggered when an AI generation request completes.

**Payload:**
```json
{
  "id": "evt_ai123",
  "type": "ai.generation.completed",
  "created_at": "2024-01-20T12:00:00Z",
  "data": {
    "object": "ai_generation",
    "generation_id": 5678,
    "user_id": 123,
    "model": {
      "id": 1,
      "name": "GPT-4",
      "provider": "openai"
    },
    "type": "text_to_text",
    "prompt": "Write a story about AI",
    "response_length": 423,
    "tokens_used": 423,
    "processing_time_ms": 2341,
    "status": "completed",
    "created_at": "2024-01-20T11:59:57Z",
    "completed_at": "2024-01-20T12:00:00Z"
  }
}
```

#### ai.generation.failed

Triggered when an AI generation request fails.

**Payload:**
```json
{
  "id": "evt_ai124",
  "type": "ai.generation.failed",
  "created_at": "2024-01-20T12:05:00Z",
  "data": {
    "object": "ai_generation",
    "generation_id": 5679,
    "user_id": 123,
    "model": {
      "id": 1,
      "name": "GPT-4",
      "provider": "openai"
    },
    "type": "text_to_text",
    "prompt": "Generate content...",
    "status": "failed",
    "error": {
      "code": "LLM_003",
      "message": "An error occurred during content generation",
      "details": "Rate limit exceeded on provider"
    },
    "created_at": "2024-01-20T12:04:58Z",
    "failed_at": "2024-01-20T12:05:00Z"
  }
}
```

---

### User Events

#### user.created

Triggered when a new user registers.

**Payload:**
```json
{
  "id": "evt_usr123",
  "type": "user.created",
  "created_at": "2024-01-20T09:00:00Z",
  "data": {
    "object": "user",
    "user_id": 123,
    "email": "user@example.com",
    "username": "johndoe",
    "registration_method": "email",
    "is_verified": false,
    "referral_code": "REF123",
    "referred_by": null,
    "created_at": "2024-01-20T09:00:00Z"
  }
}
```

#### user.verified

Triggered when a user verifies their email.

**Payload:**
```json
{
  "id": "evt_usr124",
  "type": "user.verified",
  "created_at": "2024-01-20T09:15:00Z",
  "data": {
    "object": "user",
    "user_id": 123,
    "email": "user@example.com",
    "verified_at": "2024-01-20T09:15:00Z",
    "verification_method": "email_link"
  }
}
```

#### user.deleted

Triggered when a user account is deleted.

**Payload:**
```json
{
  "id": "evt_usr125",
  "type": "user.deleted",
  "created_at": "2024-01-20T15:00:00Z",
  "data": {
    "object": "user",
    "user_id": 123,
    "email": "user@example.com",
    "deleted_at": "2024-01-20T15:00:00Z",
    "deletion_reason": "user_requested"
  }
}
```

---

### Content Events

#### content.created

Triggered when new content is created.

**Payload:**
```json
{
  "id": "evt_cnt123",
  "type": "content.created",
  "created_at": "2024-01-20T13:00:00Z",
  "data": {
    "object": "content",
    "content_id": 5000,
    "user_id": 123,
    "title": "My Document",
    "type": "document",
    "folder_id": 10,
    "size_bytes": 2048,
    "created_at": "2024-01-20T13:00:00Z"
  }
}
```

#### content.shared

Triggered when content is shared with another user.

**Payload:**
```json
{
  "id": "evt_cnt124",
  "type": "content.shared",
  "created_at": "2024-01-20T14:00:00Z",
  "data": {
    "object": "share",
    "share_id": 200,
    "content_id": 5000,
    "owner": {
      "id": 123,
      "email": "owner@example.com"
    },
    "shared_with": {
      "email": "colleague@example.com"
    },
    "permission": "view",
    "created_at": "2024-01-20T14:00:00Z"
  }
}
```

---

### Storage Events

#### storage.limit_warning

Triggered when user approaches storage limit (80% used).

**Payload:**
```json
{
  "id": "evt_str123",
  "type": "storage.limit_warning",
  "created_at": "2024-01-20T16:00:00Z",
  "data": {
    "object": "storage",
    "user_id": 123,
    "storage_used_gb": 8.5,
    "storage_limit_gb": 10,
    "usage_percentage": 85,
    "warning_level": "high"
  }
}
```

#### storage.limit_exceeded

Triggered when user exceeds storage limit.

**Payload:**
```json
{
  "id": "evt_str124",
  "type": "storage.limit_exceeded",
  "created_at": "2024-01-20T17:00:00Z",
  "data": {
    "object": "storage",
    "user_id": 123,
    "storage_used_gb": 10.2,
    "storage_limit_gb": 10,
    "overage_gb": 0.2,
    "action_required": "upgrade_plan_or_delete_content"
  }
}
```

---

## Payload Format

All webhook payloads follow a consistent structure:

```json
{
  "id": "evt_unique_id",
  "type": "event.type",
  "created_at": "2024-01-20T10:00:00Z",
  "api_version": "v1",
  "livemode": true,
  "data": {
    "object": "object_type",
    // Event-specific data
  }
}
```

**Common Fields:**

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique event identifier |
| type | string | Event type (e.g., "payment.succeeded") |
| created_at | string | ISO 8601 timestamp |
| api_version | string | API version when event was created |
| livemode | boolean | True for production, false for test mode |
| data | object | Event-specific payload |

---

## Security & Verification

### Webhook Signatures

Every webhook request includes an `X-Webhook-Signature` header that you must verify to ensure the request came from MultinotesAI.

**Signature Calculation:**
```
HMAC-SHA256(payload, webhook_secret)
```

### Verification Steps

1. Extract the signature from the `X-Webhook-Signature` header
2. Compute the expected signature using your webhook secret
3. Compare the signatures using a constant-time comparison
4. Only process the webhook if signatures match

### Example Implementations

#### Node.js / Express

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
const WEBHOOK_SECRET = process.env.MULTINOTESAI_WEBHOOK_SECRET;

// Use raw body parser for webhook verification
app.post('/webhooks/multinotesai',
  express.raw({ type: 'application/json' }),
  (req, res) => {
    const signature = req.headers['x-webhook-signature'];
    const payload = req.body;

    // Verify signature
    if (!verifyWebhookSignature(payload, signature, WEBHOOK_SECRET)) {
      console.error('Invalid webhook signature');
      return res.status(400).send('Invalid signature');
    }

    // Parse the verified payload
    const event = JSON.parse(payload.toString());

    // Process the event
    handleWebhookEvent(event);

    // Return 200 to acknowledge receipt
    res.status(200).json({ received: true });
  }
);

function verifyWebhookSignature(payload, receivedSignature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  // Use timingSafeEqual to prevent timing attacks
  return crypto.timingSafeEqual(
    Buffer.from(receivedSignature),
    Buffer.from(expectedSignature)
  );
}

function handleWebhookEvent(event) {
  console.log('Received event:', event.type);

  switch (event.type) {
    case 'payment.succeeded':
      handlePaymentSucceeded(event.data);
      break;

    case 'subscription.created':
      handleSubscriptionCreated(event.data);
      break;

    case 'ai.generation.completed':
      handleAIGenerationCompleted(event.data);
      break;

    default:
      console.log('Unhandled event type:', event.type);
  }
}

function handlePaymentSucceeded(data) {
  console.log('Payment succeeded:', data.payment_id);
  // Send confirmation email, update database, etc.
}

function handleSubscriptionCreated(data) {
  console.log('New subscription:', data.subscription_id);
  // Grant access, send welcome email, etc.
}

function handleAIGenerationCompleted(data) {
  console.log('AI generation completed:', data.generation_id);
  // Notify user, save results, etc.
}

app.listen(3000, () => {
  console.log('Webhook server listening on port 3000');
});
```

#### Python / Flask

```python
import os
import hmac
import hashlib
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_SECRET = os.getenv('MULTINOTESAI_WEBHOOK_SECRET')

@app.route('/webhooks/multinotesai', methods=['POST'])
def webhook():
    # Get signature from header
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data()

    # Verify signature
    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        app.logger.error('Invalid webhook signature')
        return jsonify({'error': 'Invalid signature'}), 400

    # Parse verified payload
    event = json.loads(payload)

    # Process event
    handle_webhook_event(event)

    # Acknowledge receipt
    return jsonify({'received': True}), 200


def verify_webhook_signature(payload, received_signature, secret):
    """Verify webhook signature using HMAC-SHA256."""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison
    return hmac.compare_digest(expected_signature, received_signature)


def handle_webhook_event(event):
    """Handle different webhook events."""
    event_type = event['type']
    data = event['data']

    handlers = {
        'payment.succeeded': handle_payment_succeeded,
        'subscription.created': handle_subscription_created,
        'ai.generation.completed': handle_ai_generation_completed,
    }

    handler = handlers.get(event_type)
    if handler:
        handler(data)
    else:
        app.logger.info(f'Unhandled event type: {event_type}')


def handle_payment_succeeded(data):
    """Handle successful payment."""
    payment_id = data['payment_id']
    print(f'Payment succeeded: {payment_id}')
    # Send confirmation email, update database, etc.


def handle_subscription_created(data):
    """Handle new subscription."""
    subscription_id = data['subscription_id']
    print(f'New subscription: {subscription_id}')
    # Grant access, send welcome email, etc.


def handle_ai_generation_completed(data):
    """Handle completed AI generation."""
    generation_id = data['generation_id']
    print(f'AI generation completed: {generation_id}')
    # Notify user, save results, etc.


if __name__ == '__main__':
    app.run(port=3000)
```

#### PHP

```php
<?php

$webhookSecret = getenv('MULTINOTESAI_WEBHOOK_SECRET');

// Get raw POST body
$payload = file_get_contents('php://input');
$signature = $_SERVER['HTTP_X_WEBHOOK_SIGNATURE'] ?? '';

// Verify signature
if (!verifyWebhookSignature($payload, $signature, $webhookSecret)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid signature']);
    exit;
}

// Parse payload
$event = json_decode($payload, true);

// Handle event
handleWebhookEvent($event);

// Acknowledge receipt
http_response_code(200);
echo json_encode(['received' => true]);

function verifyWebhookSignature($payload, $receivedSignature, $secret) {
    $expectedSignature = hash_hmac('sha256', $payload, $secret);
    return hash_equals($expectedSignature, $receivedSignature);
}

function handleWebhookEvent($event) {
    $eventType = $event['type'];
    $data = $event['data'];

    switch ($eventType) {
        case 'payment.succeeded':
            handlePaymentSucceeded($data);
            break;

        case 'subscription.created':
            handleSubscriptionCreated($data);
            break;

        case 'ai.generation.completed':
            handleAIGenerationCompleted($data);
            break;

        default:
            error_log("Unhandled event type: $eventType");
    }
}

function handlePaymentSucceeded($data) {
    $paymentId = $data['payment_id'];
    error_log("Payment succeeded: $paymentId");
    // Send confirmation email, update database, etc.
}

function handleSubscriptionCreated($data) {
    $subscriptionId = $data['subscription_id'];
    error_log("New subscription: $subscriptionId");
    // Grant access, send welcome email, etc.
}

function handleAIGenerationCompleted($data) {
    $generationId = $data['generation_id'];
    error_log("AI generation completed: $generationId");
    // Notify user, save results, etc.
}
```

---

## Retry Policy

### Automatic Retries

If your endpoint fails to respond or returns a non-2xx status code, MultinotesAI will automatically retry the webhook delivery.

**Retry Schedule:**
- 1st retry: After 5 seconds
- 2nd retry: After 30 seconds
- 3rd retry: After 2 minutes
- 4th retry: After 10 minutes
- 5th retry: After 1 hour
- 6th retry: After 6 hours
- 7th retry: After 24 hours

After 7 failed attempts, the webhook is marked as failed and no further retries are attempted.

### Retry Headers

Retried webhooks include these additional headers:

```
X-Webhook-Delivery-Attempt: 3
X-Webhook-First-Attempt: 2024-01-20T10:00:00Z
X-Webhook-Previous-Attempt: 2024-01-20T10:02:00Z
```

### Idempotency

Your webhook handler should be **idempotent** - processing the same webhook multiple times should have the same effect as processing it once.

**Best Practice:**
```javascript
// Store processed event IDs to prevent duplicate processing
const processedEvents = new Set();

function handleWebhookEvent(event) {
  // Check if already processed
  if (processedEvents.has(event.id)) {
    console.log('Event already processed:', event.id);
    return;
  }

  // Process the event
  processEvent(event);

  // Mark as processed
  processedEvents.add(event.id);

  // In production, store in database instead of memory
  // await db.webhookEvents.create({ event_id: event.id, processed_at: new Date() });
}
```

---

## Best Practices

### 1. Respond Quickly

Your webhook endpoint must respond within **5 seconds** to avoid timeouts.

**Good Practice:**
```javascript
app.post('/webhooks/multinotesai', async (req, res) => {
  // Verify signature
  if (!verifySignature(req)) {
    return res.status(400).send('Invalid signature');
  }

  // Immediately acknowledge receipt
  res.status(200).json({ received: true });

  // Process webhook asynchronously
  const event = JSON.parse(req.body);
  setImmediate(() => {
    handleWebhookEvent(event);
  });
});
```

### 2. Use a Queue for Processing

For complex processing, queue webhooks for asynchronous handling:

```javascript
const queue = require('bull');
const webhookQueue = new queue('webhooks');

app.post('/webhooks/multinotesai', async (req, res) => {
  if (!verifySignature(req)) {
    return res.status(400).send('Invalid signature');
  }

  // Add to queue
  await webhookQueue.add(JSON.parse(req.body));

  // Acknowledge immediately
  res.status(200).json({ received: true });
});

// Process webhooks from queue
webhookQueue.process(async (job) => {
  await handleWebhookEvent(job.data);
});
```

### 3. Log All Webhooks

Keep a log of all received webhooks for debugging and auditing:

```javascript
function logWebhook(event, status) {
  console.log({
    event_id: event.id,
    event_type: event.type,
    timestamp: event.created_at,
    status: status,
    logged_at: new Date().toISOString()
  });

  // In production, log to database or logging service
}
```

### 4. Handle Errors Gracefully

```javascript
async function handleWebhookEvent(event) {
  try {
    // Process event
    await processEvent(event);
    logWebhook(event, 'success');
  } catch (error) {
    console.error('Error processing webhook:', error);
    logWebhook(event, 'error');

    // Alert monitoring service
    alertMonitoring({
      error: error.message,
      event_id: event.id,
      event_type: event.type
    });
  }
}
```

### 5. Test Webhooks Thoroughly

Use the test endpoint to verify your webhook handler:

```bash
# Test your webhook
curl -X POST https://api.multinotesai.com/api/v1/webhooks/wh_123456789/test/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Managing Webhooks

### List All Webhooks

```bash
curl -X GET https://api.multinotesai.com/api/v1/webhooks/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Webhook Details

```bash
curl -X GET https://api.multinotesai.com/api/v1/webhooks/wh_123456789/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Webhook

```bash
curl -X PUT https://api.multinotesai.com/api/v1/webhooks/wh_123456789/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": ["payment.succeeded", "subscription.created"],
    "status": "active"
  }'
```

### Delete Webhook

```bash
curl -X DELETE https://api.multinotesai.com/api/v1/webhooks/wh_123456789/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### View Webhook Logs

```bash
curl -X GET https://api.multinotesai.com/api/v1/webhooks/wh_123456789/deliveries/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "count": 45,
  "results": [
    {
      "id": "del_abc123",
      "event_type": "payment.succeeded",
      "status": "success",
      "response_code": 200,
      "attempts": 1,
      "created_at": "2024-01-20T10:30:00Z",
      "completed_at": "2024-01-20T10:30:01Z"
    }
  ]
}
```

---

## Troubleshooting

### Common Issues

#### Issue: Webhook not receiving events

**Solutions:**
- Verify webhook URL is publicly accessible via HTTPS
- Check firewall rules allow incoming requests from MultinotesAI IPs
- Ensure webhook is active and subscribed to correct events
- Check webhook logs for delivery attempts

#### Issue: Signature verification fails

**Solutions:**
- Verify you're using the correct webhook secret
- Ensure you're hashing the raw request body
- Check for automatic JSON parsing middleware
- Verify HMAC calculation matches the example code

#### Issue: Timeouts

**Solutions:**
- Process webhooks asynchronously
- Return 200 response immediately
- Use a queue for complex processing
- Optimize database queries

---

## Support

For webhook issues:
- Email: webhooks-support@multinotesai.com
- Documentation: https://docs.multinotesai.com/webhooks
- Test webhook deliveries: Dashboard > Settings > Webhooks
