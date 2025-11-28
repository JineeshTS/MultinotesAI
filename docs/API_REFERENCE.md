# MultinotesAI API Reference

## Overview

The MultinotesAI API is a RESTful API built on Django REST Framework. All endpoints return JSON responses and use standard HTTP status codes.

**Base URL:** `https://api.multinotesai.com/`

**API Version:** v1

---

## Table of Contents

- [Authentication](#authentication)
- [User Management](#user-management)
- [AI Generation](#ai-generation)
- [Documents & Folders](#documents--folders)
- [Subscriptions & Plans](#subscriptions--plans)
- [Payments](#payments)
- [Support & Tickets](#support--tickets)
- [Admin Endpoints](#admin-endpoints)

---

## Authentication

### Register User

Create a new user account.

**Endpoint:** `POST /authentication/v1/register/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "country_code": "+1",
  "referr_by_code": "REF123" // optional
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "message": "Registration successful. Please verify your email.",
  "data": {
    "user": {
      "id": 123,
      "username": "johndoe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_verified": false
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_002",
    "message": "Email already exists",
    "details": {
      "email": ["User with this email already exists."]
    }
  }
}
```

**cURL Example:**
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

---

### Login

Authenticate a user and receive JWT tokens.

**Endpoint:** `POST /authentication/v1/login/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "deviceToken": "fcm_device_token_here" // optional
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 123,
      "username": "johndoe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "user",
      "is_verified": true,
      "profile_image": "https://s3.amazonaws.com/..."
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    },
    "subscription": {
      "plan": "Pro",
      "status": "active",
      "tokens_remaining": 5000,
      "expires_at": "2024-12-31T23:59:59Z"
    }
  }
}
```

**Error Responses:**
- **401 Unauthorized:**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_001",
    "message": "Invalid email or password."
  }
}
```

- **403 Forbidden (Blocked User):**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_004",
    "message": "Your account has been blocked. Please contact support."
  }
}
```

**cURL Example:**
```bash
curl -X POST https://api.multinotesai.com/authentication/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

---

### Social Login

Login or register using social authentication (Google, Facebook, Apple).

**Endpoint:** `POST /authentication/v1/social-login/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "john@example.com",
  "username": "johndoe",
  "socialId": "google_user_id_123456",
  "socialType": 1,
  "deviceToken": "fcm_token" // optional
}
```

**Social Types:**
- `1` = Google
- `2` = Apple
- `3` = Facebook

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 123,
      "email": "john@example.com",
      "username": "johndoe",
      "socialType": 1
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
  }
}
```

**cURL Example:**
```bash
curl -X POST https://api.multinotesai.com/authentication/v1/social-login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "username": "johndoe",
    "socialId": "google_123456",
    "socialType": 1
  }'
```

---

### Email Verification

Verify user email with token sent to email.

**Endpoint:** `POST /authentication/v1/verify-email-token/`

**Request Body:**
```json
{
  "token": "email_verification_token_here"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Email verified successfully."
}
```

---

### Forgot Password

Request password reset email.

**Endpoint:** `POST /authentication/v1/forgot-password/`

**Request Body:**
```json
{
  "email": "john@example.com"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Password reset email sent successfully."
}
```

**Rate Limit:** 3 requests per hour per email

---

### Reset Password

Reset password using token from email.

**Endpoint:** `POST /authentication/v1/reset-password/`

**Request Body:**
```json
{
  "token": "password_reset_token_here",
  "new_password": "NewSecurePassword123!",
  "confirm_password": "NewSecurePassword123!"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Password reset successful. You can now login with your new password."
}
```

---

## User Management

### Get User Profile

Get details of the authenticated user.

**Endpoint:** `GET /authentication/get-user/{user_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "profile_image": "https://s3.amazonaws.com/...",
    "role": "user",
    "is_verified": true,
    "created_at": "2024-01-15T10:30:00Z",
    "subscription": {
      "plan": "Pro",
      "status": "active",
      "tokens_remaining": 5000
    }
  }
}
```

**cURL Example:**
```bash
curl -X GET https://api.multinotesai.com/authentication/get-user/123/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

---

### Update User Profile

Update user profile information.

**Endpoint:** `PUT /authentication/update-user/{user_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "bio": "AI enthusiast",
  "country": "United States"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Profile updated successfully.",
  "data": {
    "id": 123,
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "bio": "AI enthusiast",
    "country": "United States"
  }
}
```

---

### Upload Profile Image

Upload user profile image.

**Endpoint:** `POST /authentication/uploadImage/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Request Body:**
```
image: [binary file data]
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Image uploaded successfully.",
  "data": {
    "image_url": "https://s3.amazonaws.com/profile-images/user123.jpg"
  }
}
```

**cURL Example:**
```bash
curl -X POST https://api.multinotesai.com/authentication/uploadImage/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -F "image=@/path/to/image.jpg"
```

---

### Change Password

Change user password (requires current password).

**Endpoint:** `POST /authentication/change-password/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "old_password": "OldPassword123!",
  "new_password": "NewPassword456!",
  "confirm_password": "NewPassword456!"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Password changed successfully."
}
```

---

## AI Generation

### Text-to-Text Generation (OpenAI)

Generate text using OpenAI models (GPT-3.5, GPT-4).

**Endpoint:** `POST /coreapp/openai_text_to_text/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "Write a creative story about AI",
  "model_id": 1,
  "max_tokens": 500,
  "temperature": 0.7,
  "notebook_id": 5 // optional
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 789,
    "prompt": "Write a creative story about AI",
    "response": "Once upon a time, in a world powered by artificial intelligence...",
    "model": "GPT-4",
    "tokens_used": 423,
    "created_at": "2024-01-20T15:30:00Z",
    "remaining_tokens": 4577
  }
}
```

**Error Response (402 Payment Required):**
```json
{
  "success": false,
  "error": {
    "code": "SUB_001",
    "message": "Insufficient tokens. Please upgrade your subscription."
  }
}
```

**cURL Example:**
```bash
curl -X POST https://api.multinotesai.com/coreapp/openai_text_to_text/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a creative story about AI",
    "model_id": 1,
    "max_tokens": 500
  }'
```

---

### Text-to-Text Generation (Mistral)

Generate text using Mistral AI models.

**Endpoint:** `POST /coreapp/mistral_text_to_text/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "Explain quantum computing",
  "model_id": 3,
  "max_tokens": 300,
  "temperature": 0.5
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 790,
    "prompt": "Explain quantum computing",
    "response": "Quantum computing is a revolutionary approach...",
    "model": "Mistral-7B",
    "tokens_used": 245,
    "created_at": "2024-01-20T15:35:00Z"
  }
}
```

---

### Text-to-Text Generation (Llama 2)

Generate text using Meta's Llama 2 models.

**Endpoint:** `POST /coreapp/llama2_text_to_text/`

**Request/Response:** Same format as other text generation endpoints.

---

### Text-to-Text Generation (Gemini Pro)

Generate text using Google's Gemini Pro.

**Endpoint:** `POST /coreapp/gemini_pro_text_to_text/`

**Request/Response:** Same format as other text generation endpoints.

---

### Image-to-Text Generation (Gemini Vision)

Extract text or get descriptions from images using Gemini Vision.

**Endpoint:** `POST /coreapp/gemini_picture_to_text/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Request Body:**
```
image: [binary image file]
prompt: "Describe what you see in this image"
model_id: 5
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 791,
    "prompt": "Describe what you see in this image",
    "response": "The image shows a modern office space with...",
    "model": "Gemini Pro Vision",
    "image_url": "https://s3.amazonaws.com/...",
    "tokens_used": 150,
    "created_at": "2024-01-20T16:00:00Z"
  }
}
```

---

### Text-to-Image Generation

Generate images from text descriptions.

**Endpoint:** `POST /coreapp/gemini_text_to_image/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "A futuristic city at sunset with flying cars",
  "model_id": 6,
  "size": "1024x1024",
  "style": "vivid"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 792,
    "prompt": "A futuristic city at sunset with flying cars",
    "image_url": "https://s3.amazonaws.com/generated-images/img792.png",
    "model": "DALL-E 3",
    "size": "1024x1024",
    "created_at": "2024-01-20T16:10:00Z",
    "tokens_used": 1000
  }
}
```

---

### Text-to-Speech

Convert text to speech audio.

**Endpoint:** `POST /coreapp/text_to_speech_generate/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "Hello, welcome to MultinotesAI!",
  "voice": "alloy",
  "model": "tts-1",
  "speed": 1.0
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 793,
    "text": "Hello, welcome to MultinotesAI!",
    "audio_url": "https://s3.amazonaws.com/audio/speech793.mp3",
    "duration": 3.5,
    "voice": "alloy",
    "created_at": "2024-01-20T16:15:00Z"
  }
}
```

---

### Speech-to-Text

Transcribe audio to text.

**Endpoint:** `POST /coreapp/speech_to_text_generate/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Request Body:**
```
audio: [binary audio file]
language: "en" // optional
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 794,
    "text": "This is the transcribed text from the audio file.",
    "language": "en",
    "duration": 45.3,
    "created_at": "2024-01-20T16:20:00Z"
  }
}
```

---

### Dynamic AI Generator

Universal endpoint for AI generation across different models.

**Endpoint:** `POST /coreapp/dynamic_llm_generator/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "Summarize this article",
  "model_id": 2,
  "generation_type": "text",
  "parameters": {
    "max_tokens": 200,
    "temperature": 0.5
  }
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 795,
    "response": "The article discusses...",
    "model": "GPT-3.5-Turbo",
    "tokens_used": 150
  }
}
```

---

## Documents & Folders

### Create Folder

Create a new folder for organizing content.

**Endpoint:** `POST /coreapp/create_folder/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "My Projects",
  "parent_id": null,
  "color": "#FF5733",
  "icon": "folder"
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 10,
    "name": "My Projects",
    "parent_id": null,
    "color": "#FF5733",
    "icon": "folder",
    "created_at": "2024-01-20T17:00:00Z",
    "item_count": 0
  }
}
```

---

### Get Folders

Get all folders for the authenticated user.

**Endpoint:** `GET /coreapp/get_folders/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `parent_id` (optional): Filter by parent folder
- `page` (optional): Page number for pagination
- `limit` (optional): Items per page (default: 20)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "count": 15,
    "next": "https://api.multinotesai.com/coreapp/get_folders/?page=2",
    "previous": null,
    "results": [
      {
        "id": 10,
        "name": "My Projects",
        "parent_id": null,
        "color": "#FF5733",
        "icon": "folder",
        "item_count": 5,
        "created_at": "2024-01-20T17:00:00Z",
        "updated_at": "2024-01-20T17:00:00Z"
      }
    ]
  }
}
```

---

### Get Single Folder

Get details of a specific folder.

**Endpoint:** `GET /coreapp/get_folder/{folder_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 10,
    "name": "My Projects",
    "parent_id": null,
    "color": "#FF5733",
    "icon": "folder",
    "items": [
      {
        "id": 1,
        "name": "Project Plan.txt",
        "type": "document",
        "size": 1024,
        "created_at": "2024-01-20T17:05:00Z"
      }
    ],
    "created_at": "2024-01-20T17:00:00Z"
  }
}
```

---

### Update Folder

Update folder details.

**Endpoint:** `PUT /coreapp/update_folder/{folder_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Updated Project Name",
  "color": "#00FF00",
  "icon": "star"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Folder updated successfully.",
  "data": {
    "id": 10,
    "name": "Updated Project Name",
    "color": "#00FF00",
    "icon": "star"
  }
}
```

---

### Delete Folder

Delete a folder (moves to trash or permanently deletes).

**Endpoint:** `DELETE /coreapp/delete_folder/{folder_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `permanent` (optional): Set to `true` for permanent deletion

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Folder deleted successfully."
}
```

---

### Create Document/Content

Create a new document or content item.

**Endpoint:** `POST /coreapp/create_content/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Meeting Notes",
  "content": "Notes from the quarterly meeting...",
  "folder_id": 10,
  "type": "document",
  "tags": ["meeting", "q1"]
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 50,
    "title": "Meeting Notes",
    "content": "Notes from the quarterly meeting...",
    "folder_id": 10,
    "type": "document",
    "tags": ["meeting", "q1"],
    "created_at": "2024-01-20T18:00:00Z"
  }
}
```

---

### Get Content

Get a specific content item.

**Endpoint:** `GET /coreapp/get_content/{content_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 50,
    "title": "Meeting Notes",
    "content": "Notes from the quarterly meeting...",
    "folder_id": 10,
    "type": "document",
    "tags": ["meeting", "q1"],
    "size": 2048,
    "created_at": "2024-01-20T18:00:00Z",
    "updated_at": "2024-01-20T18:00:00Z"
  }
}
```

---

### Update Content

Update content item.

**Endpoint:** `PUT /coreapp/update_content/{content_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Updated Meeting Notes",
  "content": "Updated notes...",
  "tags": ["meeting", "q1", "important"]
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Content updated successfully."
}
```

---

### Delete Content

Delete a content item.

**Endpoint:** `DELETE /coreapp/delete_content/{content_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Content deleted successfully."
}
```

---

### Share Content

Share content with other users.

**Endpoint:** `POST /coreapp/create_share_content/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "content_id": 50,
  "share_with_email": "colleague@example.com",
  "permission": "view",
  "message": "Check out these notes"
}
```

**Permissions:**
- `view`: Read-only access
- `edit`: Can modify content
- `admin`: Full control

**Success Response (201 Created):**
```json
{
  "success": true,
  "message": "Content shared successfully.",
  "data": {
    "share_id": 100,
    "content_id": 50,
    "shared_with": "colleague@example.com",
    "permission": "view",
    "created_at": "2024-01-20T19:00:00Z"
  }
}
```

---

## Subscriptions & Plans

### Get Available Plans

Get all available subscription plans.

**Endpoint:** `GET /planandsubscription/get-plans/`

**Headers:**
```
Content-Type: application/json
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Free",
      "price": 0,
      "currency": "USD",
      "billing_period": "monthly",
      "features": {
        "tokens": 1000,
        "storage_gb": 1,
        "ai_models": ["GPT-3.5"],
        "max_uploads_per_day": 10
      },
      "is_active": true
    },
    {
      "id": 2,
      "name": "Basic",
      "price": 9.99,
      "currency": "USD",
      "billing_period": "monthly",
      "features": {
        "tokens": 10000,
        "storage_gb": 10,
        "ai_models": ["GPT-3.5", "Mistral"],
        "max_uploads_per_day": 50
      },
      "is_active": true
    },
    {
      "id": 3,
      "name": "Pro",
      "price": 29.99,
      "currency": "USD",
      "billing_period": "monthly",
      "features": {
        "tokens": 50000,
        "storage_gb": 100,
        "ai_models": ["GPT-4", "GPT-3.5", "Mistral", "Llama 2", "Gemini Pro"],
        "max_uploads_per_day": 200,
        "priority_support": true
      },
      "is_active": true
    },
    {
      "id": 4,
      "name": "Enterprise",
      "price": 99.99,
      "currency": "USD",
      "billing_period": "monthly",
      "features": {
        "tokens": -1,
        "storage_gb": 1000,
        "ai_models": "all",
        "max_uploads_per_day": -1,
        "priority_support": true,
        "dedicated_support": true,
        "custom_models": true
      },
      "is_active": true
    }
  ]
}
```

---

### Get User Subscription

Get current user's subscription details.

**Endpoint:** `GET /planandsubscription/get-subscription/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 456,
    "plan": {
      "id": 3,
      "name": "Pro",
      "price": 29.99,
      "billing_period": "monthly"
    },
    "status": "active",
    "tokens_remaining": 45000,
    "storage_used_gb": 12.5,
    "storage_limit_gb": 100,
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-02-01T00:00:00Z",
    "auto_renew": true,
    "next_billing_date": "2024-02-01T00:00:00Z"
  }
}
```

---

### Create Subscription

Subscribe to a plan.

**Endpoint:** `POST /planandsubscription/create-subscription/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "plan_id": 3,
  "billing_period": "monthly",
  "payment_method": "razorpay",
  "coupon_code": "SAVE20" // optional
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "message": "Subscription created. Please complete payment.",
  "data": {
    "subscription_id": 456,
    "plan": "Pro",
    "amount": 23.99,
    "original_amount": 29.99,
    "discount": 6.00,
    "payment_order_id": "order_xyz123",
    "status": "pending"
  }
}
```

---

### Update Subscription

Update subscription settings (upgrade/downgrade).

**Endpoint:** `PUT /planandsubscription/update-subscription/{subscription_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "plan_id": 4,
  "auto_renew": true
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Subscription updated successfully.",
  "data": {
    "subscription_id": 456,
    "new_plan": "Enterprise",
    "effective_date": "2024-02-01T00:00:00Z",
    "prorated_amount": 70.00
  }
}
```

---

### Cancel Subscription

Cancel current subscription.

**Endpoint:** `DELETE /planandsubscription/delete-subscription/{subscription_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `immediate` (optional): Cancel immediately (default: false, cancels at period end)

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Subscription cancelled. Access will continue until 2024-02-01.",
  "data": {
    "subscription_id": 456,
    "status": "cancelled",
    "access_until": "2024-02-01T00:00:00Z"
  }
}
```

---

## Payments

### Create Razorpay Order

Create a payment order for subscription.

**Endpoint:** `POST /planandsubscription/payment/create-order/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "plan_id": 3,
  "billing_period": "monthly",
  "coupon_code": "SAVE20" // optional
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "order_id": "order_MnO3pQrStUvWxYz",
    "amount": 2399,
    "currency": "INR",
    "plan_name": "Pro",
    "razorpay_key_id": "rzp_test_xxxxxx",
    "user": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890"
    }
  }
}
```

**cURL Example:**
```bash
curl -X POST https://api.multinotesai.com/planandsubscription/payment/create-order/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": 3,
    "billing_period": "monthly"
  }'
```

---

### Verify Razorpay Payment

Verify payment after successful transaction.

**Endpoint:** `POST /planandsubscription/payment/verify/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "razorpay_order_id": "order_MnO3pQrStUvWxYz",
  "razorpay_payment_id": "pay_AbCdEfGhIjKlMn",
  "razorpay_signature": "signature_hash_here"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Payment verified successfully. Subscription activated.",
  "data": {
    "subscription_id": 456,
    "plan": "Pro",
    "status": "active",
    "transaction_id": 789,
    "payment_id": "pay_AbCdEfGhIjKlMn"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "PAY_006",
    "message": "Payment verification failed. Invalid signature."
  }
}
```

---

### Get Payment Status

Check status of a payment order.

**Endpoint:** `GET /planandsubscription/payment/status/{order_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "order_id": "order_MnO3pQrStUvWxYz",
    "status": "paid",
    "amount": 2399,
    "currency": "INR",
    "payment_id": "pay_AbCdEfGhIjKlMn",
    "method": "card",
    "created_at": "2024-01-20T20:00:00Z",
    "paid_at": "2024-01-20T20:05:00Z"
  }
}
```

---

### Validate Coupon

Validate a coupon code before applying.

**Endpoint:** `POST /planandsubscription/payment/validate-coupon/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "coupon_code": "SAVE20",
  "plan_id": 3
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "coupon_code": "SAVE20",
    "is_valid": true,
    "discount_type": "percentage",
    "discount_value": 20,
    "max_discount": 10.00,
    "original_price": 29.99,
    "discounted_price": 23.99,
    "savings": 6.00,
    "expires_at": "2024-12-31T23:59:59Z"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "PAY_004",
    "message": "Coupon has expired."
  }
}
```

---

### Request Refund

Request a refund for a payment.

**Endpoint:** `POST /planandsubscription/payment/refund/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "payment_id": "pay_AbCdEfGhIjKlMn",
  "amount": 2399,
  "reason": "Not satisfied with service"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Refund initiated successfully.",
  "data": {
    "refund_id": "rfnd_XyZ123",
    "payment_id": "pay_AbCdEfGhIjKlMn",
    "amount": 2399,
    "status": "processing",
    "estimated_completion": "3-5 business days"
  }
}
```

---

## Support & Tickets

### Create Support Ticket

Create a new support ticket.

**Endpoint:** `POST /ticketandcategory/create-ticket/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "subject": "Cannot access AI generation",
  "description": "I'm getting an error when trying to generate text",
  "category_id": 2,
  "priority": "high",
  "attachments": [
    "https://s3.amazonaws.com/screenshot1.png"
  ]
}
```

**Priority Levels:**
- `low`
- `medium`
- `high`
- `urgent`

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 1001,
    "ticket_number": "TKT-001001",
    "subject": "Cannot access AI generation",
    "description": "I'm getting an error when trying to generate text",
    "category": "Technical Support",
    "priority": "high",
    "status": "open",
    "created_at": "2024-01-20T21:00:00Z"
  }
}
```

---

### Get User Tickets

Get all tickets for the authenticated user.

**Endpoint:** `GET /ticketandcategory/get-tickets/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `status` (optional): Filter by status (open, in_progress, resolved, closed)
- `priority` (optional): Filter by priority
- `page` (optional): Page number

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "count": 5,
    "results": [
      {
        "id": 1001,
        "ticket_number": "TKT-001001",
        "subject": "Cannot access AI generation",
        "status": "in_progress",
        "priority": "high",
        "created_at": "2024-01-20T21:00:00Z",
        "updated_at": "2024-01-20T21:30:00Z",
        "unread_messages": 2
      }
    ]
  }
}
```

---

### Get Single Ticket

Get details of a specific ticket with messages.

**Endpoint:** `GET /ticketandcategory/get-ticket/{ticket_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1001,
    "ticket_number": "TKT-001001",
    "subject": "Cannot access AI generation",
    "description": "I'm getting an error when trying to generate text",
    "category": "Technical Support",
    "priority": "high",
    "status": "in_progress",
    "messages": [
      {
        "id": 1,
        "sender": "support",
        "message": "We're looking into this issue. Can you provide more details?",
        "created_at": "2024-01-20T21:15:00Z"
      },
      {
        "id": 2,
        "sender": "user",
        "message": "Sure, here are the details...",
        "created_at": "2024-01-20T21:20:00Z"
      }
    ],
    "created_at": "2024-01-20T21:00:00Z",
    "updated_at": "2024-01-20T21:30:00Z"
  }
}
```

---

### Add Message to Ticket

Reply to a support ticket.

**Endpoint:** `POST /ticketandcategory/add-chat-ticket/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "ticket_id": 1001,
  "message": "Here are the additional details you requested..."
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 3,
    "ticket_id": 1001,
    "sender": "user",
    "message": "Here are the additional details you requested...",
    "created_at": "2024-01-20T21:35:00Z"
  }
}
```

---

### Update Ticket

Update ticket details (e.g., close ticket).

**Endpoint:** `PUT /ticketandcategory/update-ticket/{ticket_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "status": "closed",
  "rating": 5,
  "feedback": "Issue resolved quickly. Great support!"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Ticket updated successfully."
}
```

---

### Contact Us

Submit a contact form (for non-authenticated users or general inquiries).

**Endpoint:** `POST /ticketandcategory/contactus/`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "subject": "Business Inquiry",
  "message": "I'm interested in enterprise solutions..."
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "message": "Your message has been sent. We'll get back to you within 24 hours."
}
```

---

## Admin Endpoints

### Admin Dashboard Stats

Get comprehensive dashboard statistics.

**Endpoint:** `GET /coreapp/admin_dashboard_count/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Permissions Required:** Admin/Staff

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "users": {
      "total": 10547,
      "active": 8234,
      "new_this_month": 432,
      "verified": 9876
    },
    "subscriptions": {
      "total_active": 5432,
      "free": 5115,
      "basic": 234,
      "pro": 78,
      "enterprise": 5
    },
    "revenue": {
      "total": 125430.50,
      "this_month": 15234.00,
      "last_month": 14567.00,
      "growth_percentage": 4.58
    },
    "ai_usage": {
      "total_requests": 1234567,
      "this_month": 145678,
      "tokens_used": 9876543210,
      "most_used_model": "GPT-3.5"
    },
    "storage": {
      "total_used_gb": 5432.1,
      "total_files": 98765
    },
    "support": {
      "open_tickets": 23,
      "in_progress": 15,
      "resolved_today": 45
    }
  }
}
```

---

### Get All Users (Admin)

Get paginated list of all users.

**Endpoint:** `GET /authentication/get-users/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Permissions Required:** Admin/Staff

**Query Parameters:**
- `page` (optional): Page number
- `limit` (optional): Items per page
- `search` (optional): Search by name/email
- `role` (optional): Filter by role
- `status` (optional): Filter by status (active, blocked, deleted)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "count": 10547,
    "next": "https://api.multinotesai.com/authentication/get-users/?page=2",
    "previous": null,
    "results": [
      {
        "id": 123,
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "user",
        "is_verified": true,
        "is_blocked": false,
        "subscription": "Pro",
        "created_at": "2024-01-15T10:30:00Z",
        "last_login": "2024-01-20T09:15:00Z"
      }
    ]
  }
}
```

---

### Delete User (Admin)

Delete a user account.

**Endpoint:** `DELETE /authentication/delete-user/{user_id}/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Permissions Required:** Admin

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "User deleted successfully."
}
```

---

### Get Latest Users

Get recently registered users.

**Endpoint:** `GET /coreapp/latest_user/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Permissions Required:** Admin/Staff

**Query Parameters:**
- `limit` (optional): Number of users to return (default: 10)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 10547,
      "username": "newuser123",
      "email": "newuser@example.com",
      "subscription": "Free",
      "created_at": "2024-01-20T22:00:00Z"
    }
  ]
}
```

---

### Get Latest Transactions

Get recent payment transactions.

**Endpoint:** `GET /coreapp/latest_transaction/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Permissions Required:** Admin/Staff

**Query Parameters:**
- `limit` (optional): Number of transactions (default: 10)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 5678,
      "user": "john@example.com",
      "plan": "Pro",
      "amount": 29.99,
      "currency": "USD",
      "status": "success",
      "payment_method": "card",
      "created_at": "2024-01-20T21:45:00Z"
    }
  ]
}
```

---

### Token Usage Statistics

Get daily token usage statistics.

**Endpoint:** `GET /coreapp/per_day_used_token/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Permissions Required:** Admin/Staff

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `days` (optional): Number of days (default: 30)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2024-01-01",
      "end": "2024-01-30"
    },
    "total_tokens": 9876543,
    "daily_usage": [
      {
        "date": "2024-01-20",
        "tokens": 345678,
        "requests": 5432,
        "unique_users": 234
      }
    ],
    "top_models": [
      {
        "model": "GPT-3.5",
        "tokens": 5432109,
        "percentage": 55.0
      },
      {
        "model": "GPT-4",
        "tokens": 3456789,
        "percentage": 35.0
      }
    ]
  }
}
```

---

## Response Format

All API responses follow a standard format:

### Success Response
```json
{
  "success": true,
  "message": "Optional success message",
  "data": {
    // Response data
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {} // Optional additional details
  }
}
```

---

## HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required or invalid token
- `402 Payment Required` - Subscription upgrade needed
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `413 Payload Too Large` - File size exceeds limit
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

---

## Pagination

List endpoints support pagination with the following query parameters:

- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)

Response format:
```json
{
  "count": 100,
  "next": "https://api.multinotesai.com/endpoint/?page=3",
  "previous": "https://api.multinotesai.com/endpoint/?page=1",
  "results": []
}
```

---

## Rate Limiting Headers

Every API response includes rate limit headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642780800
```

See [RATE_LIMITS.md](RATE_LIMITS.md) for detailed information.

---

## API Versioning

The API uses URL-based versioning:

- Current version: `v1`
- Example: `/authentication/v1/login/`

When breaking changes are introduced, a new version will be released while maintaining support for previous versions.

---

## Support

For API support, contact:
- Email: api-support@multinotesai.com
- Documentation: https://docs.multinotesai.com
- Developer Portal: https://developers.multinotesai.com
