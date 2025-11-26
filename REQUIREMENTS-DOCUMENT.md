# Software Requirements Document (SRD)
# MultinotesAI - AI-Powered Multi-LLM SaaS Platform

**Document Version**: 1.0
**Date**: November 24, 2025
**Project Name**: MultinotesAI
**Document Type**: Software Requirements Specification

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [User Roles & Permissions](#3-user-roles--permissions)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [External Interfaces](#6-external-interfaces)
7. [Data Requirements](#7-data-requirements)
8. [Security Requirements](#8-security-requirements)
9. [Payment Integration](#9-payment-integration)
10. [Deployment Requirements](#10-deployment-requirements)

---

## 1. Introduction

### 1.1 Purpose
This document specifies the software requirements for MultinotesAI, a comprehensive AI-powered SaaS platform that provides users access to multiple Large Language Models (LLMs) for various content generation tasks including text, images, audio, video analysis, and code generation.

### 1.2 Scope
MultinotesAI is a subscription-based platform offering:
- Multi-LLM access (Together AI, Google Gemini, OpenAI)
- Token-based usage system
- Cloud storage for generated content
- Enterprise/cluster management
- Comprehensive admin dashboard

### 1.3 Definitions & Acronyms

| Term | Definition |
|------|------------|
| LLM | Large Language Model |
| Token | Unit of AI usage measurement |
| Cluster | Enterprise organization grouping |
| SSE | Server-Sent Events (for streaming responses) |
| JWT | JSON Web Token (authentication) |

### 1.4 Target Audience
- Individual users seeking AI-powered content generation
- Enterprise organizations requiring multi-user AI access
- Developers integrating AI capabilities
- Content creators and professionals

---

## 2. System Overview

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Web Browser   │  │   Mobile App    │  │   API Clients   │ │
│  │   (React SPA)   │  │    (Future)     │  │                 │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
└───────────┼────────────────────┼────────────────────┼───────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Django REST API                          ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  ││
│  │  │   Auth   │ │  Core    │ │  Plans   │ │    Admin     │  ││
│  │  │  Module  │ │  App     │ │ & Subs   │ │    Panel     │  ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  Celery Workers  │  │ Django Channels  │                    │
│  │  (Async Tasks)   │  │   (WebSocket)    │                    │
│  └──────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  MySQL   │  │  Redis   │  │ AWS S3   │  │  LLM APIs    │   │
│  │ Database │  │  Cache   │  │ Storage  │  │ (External)   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, Tailwind CSS, Redux Toolkit |
| Backend | Django 5.0, Django REST Framework |
| Database | MySQL 8.0+ |
| Cache/Queue | Redis |
| Task Queue | Celery |
| Real-time | Django Channels |
| Storage | AWS S3 |
| Payment | Razorpay |
| Authentication | JWT (SimpleJWT) |

---

## 3. User Roles & Permissions

### 3.1 Role Hierarchy

```
Super Admin (is_superuser)
    │
    ├── Admin
    │   └── Full platform management
    │
    ├── Sub Admin
    │   └── Limited admin capabilities
    │
    ├── Enterprise Admin (Cluster Owner)
    │   ├── Enterprise Sub Admin
    │   └── Enterprise User
    │
    └── Regular User
        └── Standard platform access
```

### 3.2 Role Definitions

| Role | Code | Description | Permissions |
|------|------|-------------|-------------|
| **Super Admin** | `admin` + `is_superuser` | Platform owner | Full system access |
| **Admin** | `admin` | Platform administrator | User management, analytics, settings |
| **Sub Admin** | `sub_admin` | Assistant administrator | Limited admin features |
| **Enterprise Admin** | `enterprise_admin` | Cluster owner | Manage cluster users, shared subscription |
| **Enterprise Sub Admin** | `enterprise_sub_admin` | Cluster assistant | Limited cluster management |
| **Enterprise User** | `enterprise_user` | Cluster member | Use shared cluster resources |
| **User** | `user` | Regular user | Personal account features |

### 3.3 Permission Matrix

| Feature | Super Admin | Admin | Sub Admin | Enterprise Admin | Enterprise User | User |
|---------|:-----------:|:-----:|:---------:|:----------------:|:---------------:|:----:|
| Manage All Users | ✓ | ✓ | ✓ | - | - | - |
| Manage Cluster Users | ✓ | ✓ | - | ✓ | - | - |
| View Analytics | ✓ | ✓ | ✓ | ✓ | - | - |
| Manage Plans | ✓ | ✓ | - | - | - | - |
| Manage LLM Models | ✓ | ✓ | - | - | - | - |
| Manage Categories | ✓ | ✓ | ✓ | - | - | - |
| Manage Coupons | ✓ | ✓ | - | - | - | - |
| Use AI Generation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Manage Own Content | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Share Content | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Purchase Subscription | ✓ | - | - | ✓ | - | ✓ |

---

## 4. Functional Requirements

### 4.1 Authentication & User Management

#### FR-AUTH-001: User Registration
**Description**: Users can register using email/password or social login
**Priority**: P0 (Critical)

| Field | Type | Required | Validation |
|-------|------|:--------:|------------|
| username | String | Yes | Unique, max 250 chars |
| email | Email | Yes | Valid email, unique |
| password | String | Yes | Min 8 chars, complexity rules |
| name | String | No | Max 250 chars |
| phone_number | String | No | Unique if provided |
| referr_by_code | String | No | Valid referral code |

**Business Rules**:
- Email verification required before login
- Automatic trial subscription creation on registration
- Free storage plan assigned on registration
- Referral bonus applied if valid code provided
- Cluster auto-assignment based on email domain

#### FR-AUTH-002: Social Login
**Description**: Users can authenticate via Google or Facebook
**Priority**: P0

**Supported Providers**:
| Provider | socialType Code |
|----------|:---------------:|
| Google | 2 |
| Facebook | 3 |

**Flow**:
1. User initiates social login
2. OAuth redirect to provider
3. Callback with social ID and profile data
4. Create or link account
5. Issue JWT tokens

#### FR-AUTH-003: Email Verification
**Description**: Email verification via JWT token link
**Priority**: P0

**Process**:
1. Generate JWT token with user_id
2. Send email with verification link
3. User clicks link
4. Token validated and user verified
5. Account activated

#### FR-AUTH-004: Password Management
**Description**: Password change and reset functionality
**Priority**: P0

| Feature | Endpoint | Authentication |
|---------|----------|----------------|
| Change Password | `/api/auth/change-password/` | Required |
| Forgot Password | `/api/auth/forgot-password/` | Not Required |
| Reset Password | `/api/auth/reset-password/` | Token-based |
| Generate Password (Social) | `/api/auth/generate-password/` | Required |

#### FR-AUTH-005: User Profile Management
**Description**: Users can update profile information
**Priority**: P1

**Editable Fields**:
- username, name, email
- phone_number, country_code
- profile_image (AWS S3)
- gender, city, state, country, zipcode
- deviceToken (for push notifications)

#### FR-AUTH-006: User Blocking
**Description**: Admins can block/unblock users
**Priority**: P1

**Effects of Blocking**:
- Login prevented
- API access denied
- Active sessions invalidated

---

### 4.2 AI Generation Features

#### FR-AI-001: Text-to-Text Generation
**Description**: Generate text responses from text prompts
**Priority**: P0

**Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| prompt | String | Yes | User's text prompt |
| model | String | Yes | LLM model name |
| category | Integer | Yes | Category ID |
| promptWriter | Boolean | No | Enable prompt enhancement |
| chatbot | Boolean | No | Enable conversation mode |
| groupId | Integer | No | Conversation group ID |

**Supported Providers**:
- Together AI (source=2)
- Google Gemini (source=3)
- OpenAI (source=4)

**Response**: Server-Sent Events (SSE) stream

#### FR-AI-002: Image-to-Text Generation
**Description**: Analyze images and generate text descriptions
**Priority**: P1

**Supported Formats**: PNG, JPEG, JPG, WebP, HEIC, HEIF

**Request Parameters**:
| Parameter | Type | Required |
|-----------|------|:--------:|
| file | File | Yes |
| prompt | String | No |
| model | String | Yes |
| category | Integer | Yes |

**Provider**: Google Gemini (source=3)

#### FR-AI-003: Text-to-Image Generation
**Description**: Generate images from text descriptions
**Priority**: P1

**Request Parameters**:
| Parameter | Type | Required | Default |
|-----------|------|:--------:|---------|
| prompt | String | Yes | - |
| model | String | Yes | - |
| category | Integer | Yes | - |
| width | Integer | No | 1024 |
| height | Integer | No | 1024 |

**Providers**: Together AI (source=2), OpenAI (source=4)

**Output**: Base64 encoded PNG uploaded to S3

#### FR-AI-004: Text-to-Speech Generation
**Description**: Convert text to audio speech
**Priority**: P1

**Request Parameters**:
| Parameter | Type | Required |
|-----------|------|:--------:|
| prompt | String | Yes |
| model | String | Yes |
| category | Integer | Yes |
| voice | String | Yes |

**Provider**: OpenAI (source=4)

**Output**: MP3 file uploaded to S3

#### FR-AI-005: Speech-to-Text Generation
**Description**: Transcribe audio to text
**Priority**: P1

**Supported Formats**: MP3, WAV, AIFF, AAC, OGG, FLAC

**Providers**: OpenAI (source=4), Google Gemini (source=3)

#### FR-AI-006: Video-to-Text Analysis
**Description**: Analyze video content and generate descriptions
**Priority**: P2

**Supported Formats**: MP4, MPEG, MOV, AVI, FLV, MPG, WebM, WMV, 3GPP

**Provider**: Google Gemini (source=3)

#### FR-AI-007: Code Generation
**Description**: Generate code from natural language descriptions
**Priority**: P1

**Providers**: Together AI (source=2), Google Gemini (source=3)

**Response**: SSE stream with code formatting

#### FR-AI-008: Conversation Management
**Description**: Maintain conversation context across multiple prompts
**Priority**: P1

**Features**:
- Automatic group creation for chatbot mode
- Conversation history storage
- Group naming from first prompt (first 4 words)
- LLM and category association per group

---

### 4.3 Content Management

#### FR-CONTENT-001: Folder Management
**Description**: Hierarchical folder structure for organizing content
**Priority**: P1

**Features**:
| Feature | Description |
|---------|-------------|
| Create Folder | Create folders with titles |
| Nested Folders | Support parent-child relationships |
| List Folders | Get folder tree for user |
| Update Folder | Rename folders |
| Delete Folder | Soft delete (is_delete flag) |
| Move Content | Move items between folders |

**Data Model**:
```
Folder
├── id
├── title
├── user (FK → CustomUser)
├── parent_folder (FK → self, nullable)
├── is_active
├── is_delete
├── created_at
└── updated_at
```

#### FR-CONTENT-002: Document Management
**Description**: Store and manage AI-generated documents
**Priority**: P1

**Document Types**:
- Text responses
- Generated images
- Generated audio
- Code snippets

**Features**:
- Save to folder
- Title and content storage
- Size tracking
- LLM model association
- Response ID linking

#### FR-CONTENT-003: User Content (File) Management
**Description**: User-uploaded files for AI processing
**Priority**: P1

**Features**:
- File upload to AWS S3
- File size tracking
- Folder organization
- Self-upload flag for user files
- File description support

#### FR-CONTENT-004: Notebook Feature
**Description**: Create notebooks to collect prompts and content
**Priority**: P2

**Features**:
- Unique label per notebook
- Rich text content
- Link multiple prompts
- Folder organization
- Open/closed state tracking

#### FR-CONTENT-005: Content Sharing
**Description**: Share content with other users
**Priority**: P1

**Shareable Items**:
- Files (UserContent)
- Folders
- Documents

**Access Levels**:
| Level | Code | Permissions |
|-------|------|-------------|
| View Only | `can_view` | Read access |
| Edit | `can_edit` | Read + write access |

**Data Model**:
```
Share
├── file (FK → UserContent, nullable)
├── folder (FK → Folder, nullable)
├── document (FK → Document, nullable)
├── owner (FK → CustomUser)
├── share_to_user (FK → CustomUser)
├── content_type (file/folder/document)
├── access_type (can_view/can_edit)
├── main_folder (FK → Folder, nullable)
└── is_active, is_delete, timestamps
```

---

### 4.4 Subscription & Payment Management

#### FR-SUB-001: Subscription Plans
**Description**: Define and manage subscription plans
**Priority**: P0

**Plan Types**:
| Type | Code | Description |
|------|------|-------------|
| Token Plan | `token` | AI generation tokens |
| Storage Plan | `storage` | Cloud storage space |

**Plan Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| plan_name | String | Display name |
| description | Text | Plan details |
| amount | Float | Price |
| duration | Integer | Days valid |
| totalToken | Integer | Text tokens included |
| fileToken | Integer | File tokens included |
| storage_size | BigInteger | Bytes (for storage plans) |
| feature | Text | Feature list (JSON) |
| discount | Integer | Discount percentage |
| is_free | Boolean | Trial/free plan flag |
| is_for_cluster | Boolean | Enterprise plan flag |

#### FR-SUB-002: User Subscriptions
**Description**: Manage user subscription lifecycle
**Priority**: P0

**Subscription States**:
| Status | Description |
|--------|-------------|
| `trial` | Free trial period |
| `active` | Paid and valid |
| `expire` | Subscription ended |

**Token Tracking**:
- `balanceToken` - Available text tokens
- `usedToken` - Consumed text tokens
- `expireToken` - Expired unused tokens
- `fileToken` - Available file tokens
- `usedFileToken` - Consumed file tokens

**Subscription Flow**:
```
Registration → Trial Subscription → Payment → Active Subscription
                                          ↓
                               Expiry → Renewal/Expire
```

#### FR-SUB-003: Storage Usage Tracking
**Description**: Track user cloud storage consumption
**Priority**: P1

**Tracked Metrics**:
- `total_storage_used` (bytes)
- `storage_limit` (bytes)
- Plan association
- Subscription status

#### FR-SUB-004: Payment Processing (Razorpay)
**Description**: Process payments via Razorpay
**Priority**: P0

**Payment Flow**:
1. User selects plan
2. Create Razorpay order
3. User completes payment on Razorpay
4. Webhook/callback verification
5. Subscription activation
6. Transaction recording

**Transaction Record**:
| Field | Type | Description |
|-------|------|-------------|
| transactionId | String | Razorpay payment ID |
| amount | Float | Payment amount |
| plan_name | String | Purchased plan |
| duration | Integer | Subscription days |
| tokenCount | Integer | Tokens included |
| payment_status | Enum | paid/failure/pending |
| payment_method | String | Card/UPI/NetBanking |

#### FR-SUB-005: Coupon System
**Description**: Apply discount coupons to purchases
**Priority**: P2

**Coupon Types**:
| Type | Description |
|------|-------------|
| `percentage` | Percentage discount |
| `fixed` | Fixed amount discount |

**Coupon Attributes**:
- coupon_code (unique)
- discount_value
- min_order_amount
- max_discount_amount
- bonus_token (extra tokens on use)
- start_date / end_date
- is_active

**Validation Rules**:
- Date range check
- Minimum order amount
- Maximum discount cap
- Single use per user (optional)

---

### 4.5 Enterprise/Cluster Management

#### FR-CLUSTER-001: Cluster Creation
**Description**: Create enterprise organizations
**Priority**: P1

**Cluster Attributes**:
| Field | Description |
|-------|-------------|
| cluster_name | Organization name |
| org_name | Legal organization name |
| email | Primary contact email |
| domain | Email domain for auto-assignment |
| plan | Token subscription plan |
| storage_plan | Storage subscription plan |

**Creation Flow**:
1. Admin creates cluster with plans
2. Cluster owner account created
3. Verification email sent
4. Shared subscriptions created

#### FR-CLUSTER-002: Domain-Based Auto-Assignment
**Description**: Auto-assign users to clusters by email domain
**Priority**: P1

**Process**:
1. User registers with email
2. System extracts domain from email
3. Match against cluster domains
4. If match found:
   - Assign user to cluster
   - Set role to `enterprise_user`
   - Use cluster's shared subscription

#### FR-CLUSTER-003: Cluster User Management
**Description**: Manage users within a cluster
**Priority**: P1

**Features**:
- View cluster members
- Promote user to enterprise_sub_admin
- Demote sub_admin to user
- Remove user from cluster
- View shared token usage

#### FR-CLUSTER-004: Shared Resource Management
**Description**: Cluster members share subscription resources
**Priority**: P1

**Shared Resources**:
- Token balance (text + file)
- Storage quota
- Subscription validity

---

### 4.6 LLM Model Management

#### FR-LLM-001: LLM Model Configuration
**Description**: Configure AI models available in platform
**Priority**: P0

**Model Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| name | String | Display name |
| description | Text | Model description |
| api_key | String | Provider API key |
| model_string | String | Provider model identifier |
| source | Integer | 2=Together, 3=Gemini, 4=OpenAI |
| capabilities | String | Capability description |
| powered_by | Text | Provider info |
| test_status | Enum | connected/disconnected |

**Capability Flags**:
- `text` - Text generation
- `code` - Code generation
- `image_to_text` - Image analysis
- `video_to_text` - Video analysis
- `text_to_image` - Image generation
- `text_to_audio` - Speech synthesis
- `audio_to_text` - Transcription

#### FR-LLM-002: Model Testing
**Description**: Test LLM connectivity and functionality
**Priority**: P1

**Test Process**:
1. Admin initiates test
2. Send sample request to provider
3. Update `test_status` based on result
4. Only `connected` models available to users

#### FR-LLM-003: User LLM Preferences
**Description**: Users can enable/disable available models
**Priority**: P2

**Features**:
- Personal model enable/disable
- Per-user model preferences
- Quick access to favorites

#### FR-LLM-004: Model Ratings
**Description**: Users can rate and review models
**Priority**: P2

**Rating System**:
- 1-5 star rating
- Text review (optional)
- Average rating calculation

---

### 4.7 Category Management

#### FR-CAT-001: Main Categories
**Description**: Top-level feature categories
**Priority**: P1

**Attributes**:
- name, description
- status (active/inactive)
- alias_name
- can_delete flag

**Default Main Categories** (non-deletable):
- Content Generation
- Code Generation
- Image Generation
- Audio/Speech
- Analysis

#### FR-CAT-002: Sub-Categories
**Description**: Specific use-case categories under main categories
**Priority**: P1

**Attributes**:
- mainCategory (FK)
- name, description
- alias_name (auto-generated)
- llm_models (compatible models)
- route (frontend routing)
- status (active/inactive)

---

### 4.8 Support & Communication

#### FR-SUPPORT-001: Support Tickets
**Description**: User support ticket system
**Priority**: P1

**Ticket Attributes**:
| Field | Type | Values |
|-------|------|--------|
| ticket_title | String | - |
| description | Text | - |
| ticket_type | Enum | support, feedback |
| status | Enum | open, in-progress, closed |
| priority | Enum | low, medium, high |
| image | String | S3 attachment |

**Ticket Lifecycle**:
```
Open → In-Progress → Closed
         ↑
    (Reopen possible)
```

#### FR-SUPPORT-002: Ticket Responses
**Description**: Threaded conversation on tickets
**Priority**: P1

**Features**:
- User and admin messages
- Image attachments
- Timestamp tracking
- Read status

#### FR-SUPPORT-003: Notifications
**Description**: In-app notification system
**Priority**: P1

**Notification Types**:
| Type Code | Description |
|:---------:|-------------|
| 2 | New ticket |
| 3 | Ticket response |

**Attributes**:
- title, description
- sender (user/admin)
- ticket reference
- read status (isMarkRead)

#### FR-SUPPORT-004: FAQ Management
**Description**: Frequently asked questions
**Priority**: P2

**Features**:
- Question/answer pairs
- Custom ordering
- Active/inactive status
- Admin management

#### FR-SUPPORT-005: Contact Us
**Description**: Public contact form
**Priority**: P2

**Form Fields**:
- name, email (required)
- mobile, country_code (optional)
- subject, message
- Admin comment field
- Status tracking (open/closed)

---

### 4.9 Referral System

#### FR-REF-001: Referral Program
**Description**: User referral reward system
**Priority**: P2

**Referral Flow**:
1. User A shares referral code
2. User B registers with code
3. Referral record created
4. Rewards distributed on conditions

**Reward Types** (configurable):
| Setting | Description |
|---------|-------------|
| isToken | Award bonus tokens |
| isStorage | Award bonus storage |
| isFirstPayment | Award on first payment |

**Reward Distribution**:
- `refer_by_token` - Tokens to referrer
- `refer_to_token` - Tokens to new user
- `storage` - Storage bonus (if enabled)

#### FR-REF-002: Referral Code Generation
**Description**: Auto-generate unique referral codes
**Priority**: P2

**Code Format**: 12-character alphanumeric (uppercase + digits)

**Generation**: On user creation (non-cluster users only)

---

### 4.10 Admin Dashboard

#### FR-ADMIN-001: User Management
**Description**: Admin user administration
**Priority**: P0

**Features**:
- List all users with filters
- Search by username/email
- Filter by status (free/paid/expire)
- Filter by role
- Block/unblock users
- Delete users (soft delete)
- Edit user details
- Manually adjust tokens/storage

#### FR-ADMIN-002: Analytics Dashboard
**Description**: Platform analytics and metrics
**Priority**: P1

**Metrics to Display**:
- Total users (by status)
- Active subscriptions
- Revenue (daily/weekly/monthly)
- Token consumption
- Storage usage
- Popular LLM models
- Category usage

#### FR-ADMIN-003: LLM Management
**Description**: Configure LLM models
**Priority**: P0

**Features**:
- Add/edit/delete models
- Configure API keys
- Set capabilities
- Test connectivity
- Enable/disable models

#### FR-ADMIN-004: Plan Management
**Description**: Manage subscription plans
**Priority**: P0

**Features**:
- Create token/storage plans
- Set pricing and duration
- Configure token allocations
- Set as free/trial plan
- Activate/deactivate plans

#### FR-ADMIN-005: Transaction Reports
**Description**: Payment and transaction reporting
**Priority**: P1

**Features**:
- Transaction history
- Filter by date range
- Filter by status
- Export capabilities
- Revenue summaries

---

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

| Requirement | Specification |
|-------------|---------------|
| API Response Time | < 500ms for non-AI endpoints |
| AI Streaming Start | < 2 seconds to first token |
| Concurrent Users | Support 1000+ simultaneous users |
| Database Queries | < 100ms for indexed queries |
| File Upload | Support up to 250MB files |
| Page Load Time | < 3 seconds (frontend) |

### 5.2 Scalability Requirements

| Aspect | Requirement |
|--------|-------------|
| Horizontal Scaling | Support multiple application instances |
| Database | Connection pooling, read replicas support |
| Task Queue | Distributed Celery workers |
| Storage | CDN integration for static assets |
| Caching | Redis cluster support |

### 5.3 Availability Requirements

| Metric | Target |
|--------|--------|
| Uptime | 99.5% |
| Planned Maintenance | < 4 hours/month |
| Recovery Time | < 1 hour |
| Backup Frequency | Daily (database), real-time (files) |

### 5.4 Usability Requirements

- Mobile-responsive design (320px - 1920px+)
- WCAG 2.1 AA accessibility compliance
- Multi-browser support (Chrome, Firefox, Safari, Edge)
- Intuitive navigation with < 3 clicks to any feature
- Loading indicators for all async operations
- Error messages in user-friendly language

### 5.5 Reliability Requirements

- Graceful degradation if LLM provider unavailable
- Automatic retry for failed API calls (exponential backoff)
- Data consistency with database transactions
- Idempotent API operations where applicable

---

## 6. External Interfaces

### 6.1 LLM Provider APIs

#### Together AI
- **Base URL**: `https://api.together.xyz`
- **Authentication**: Bearer token
- **Features**: Text generation, code, image generation
- **Rate Limits**: Per API key limits

#### Google Gemini
- **Base URL**: `https://generativelanguage.googleapis.com`
- **Authentication**: API key
- **Features**: Text, vision, audio, video analysis
- **Rate Limits**: Requests per minute

#### OpenAI
- **Base URL**: `https://api.openai.com`
- **Authentication**: Bearer token
- **Features**: Text, images, audio (TTS/STT)
- **Rate Limits**: Tokens per minute

### 6.2 Payment Gateway (Razorpay)

**Integration Type**: Server-side + Client-side SDK

**Required APIs**:
| API | Purpose |
|-----|---------|
| Create Order | Generate payment order |
| Verify Payment | Validate payment signature |
| Fetch Payment | Get payment details |
| Refund | Process refunds |
| Webhook | Async payment notifications |

**Webhook Events**:
- `payment.captured` - Successful payment
- `payment.failed` - Failed payment
- `refund.processed` - Refund completed

### 6.3 AWS S3

**Operations**:
| Operation | Use Case |
|-----------|----------|
| PutObject | Upload files (images, audio, documents) |
| GetObject | Retrieve files |
| DeleteObject | Remove files |
| GeneratePresignedUrl | Temporary access URLs |

**Bucket Structure**:
```
multinote/
├── user/           # Profile images
├── texttoimage/    # Generated images
├── textToSpeech/   # Generated audio
├── speechToText/   # Uploaded audio
└── documents/      # User documents
```

### 6.4 Email Service (SMTP)

**Email Types**:
| Type | Trigger |
|------|---------|
| Verification | User registration |
| Password Reset | Forgot password request |
| OTP | Role change verification |
| Subscription | Plan purchase/expiry |

---

## 7. Data Requirements

### 7.1 Data Entities Summary

| Entity | Description | Relationships |
|--------|-------------|---------------|
| CustomUser | User accounts | → Roles, Cluster, Subscription |
| Cluster | Enterprise organizations | → Users, Plans |
| Subscription | User subscriptions | → User, Plan |
| StorageUsage | Storage tracking | → User, Plan |
| LLM | AI model configs | → Prompts, Responses |
| Prompt | User prompts | → User, Category, Group |
| PromptResponse | AI responses | → Prompt, LLM |
| Folder | Content organization | → User, Parent Folder |
| Document | Saved documents | → User, Folder, Category |
| Share | Content sharing | → Owner, Recipient, Content |
| Ticket | Support tickets | → User, Responses |
| Category | Feature categories | → Main Category |

### 7.2 Data Retention

| Data Type | Retention Period |
|-----------|------------------|
| User accounts | Until deletion request |
| Prompts/Responses | 2 years |
| Transactions | 7 years (compliance) |
| Audit logs | 1 year |
| Deleted content | 30 days (soft delete) |

### 7.3 Data Backup

| Backup Type | Frequency | Retention |
|-------------|-----------|-----------|
| Full database | Daily | 30 days |
| Incremental | Every 6 hours | 7 days |
| Transaction logs | Continuous | 7 days |
| S3 objects | Versioning enabled | 90 days |

---

## 8. Security Requirements

### 8.1 Authentication Security

| Requirement | Implementation |
|-------------|----------------|
| Password Hashing | Django's PBKDF2 with SHA256 |
| Token Security | JWT with HS256, 15-day expiry |
| Session Management | Token rotation on refresh |
| Brute Force Protection | Rate limiting, account lockout |
| Social Auth | OAuth 2.0 with state verification |

### 8.2 Authorization Security

| Requirement | Implementation |
|-------------|----------------|
| Role-Based Access | Django permissions + custom roles |
| Resource Ownership | User ID verification on all operations |
| API Authorization | JWT required for protected endpoints |
| Admin Verification | OTP for sensitive operations |

### 8.3 Data Security

| Requirement | Implementation |
|-------------|----------------|
| Data in Transit | TLS 1.2+ (HTTPS) |
| Data at Rest | S3 server-side encryption |
| API Key Storage | Environment variables, encrypted in DB |
| PII Protection | Access logging, data minimization |
| SQL Injection | Django ORM parameterized queries |
| XSS Prevention | Content sanitization, CSP headers |

### 8.4 Infrastructure Security

| Requirement | Implementation |
|-------------|----------------|
| Firewall | UFW with whitelist rules |
| SSH Security | Key-only auth, no root login |
| Intrusion Detection | fail2ban |
| Security Updates | Automatic OS updates |
| Secret Management | Environment variables |

### 8.5 Compliance

| Standard | Applicability |
|----------|---------------|
| GDPR | EU user data handling |
| Data Retention | Transaction records (7 years) |
| User Rights | Data export, deletion requests |

---

## 9. Payment Integration (Razorpay)

### 9.1 Razorpay Configuration

**Required Credentials**:
- `RAZORPAY_KEY_ID` - Public key
- `RAZORPAY_KEY_SECRET` - Secret key
- `RAZORPAY_WEBHOOK_SECRET` - Webhook signature verification

### 9.2 Payment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     PAYMENT FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

User                    Frontend                  Backend                 Razorpay
  │                        │                         │                       │
  │ Select Plan            │                         │                       │
  │───────────────────────>│                         │                       │
  │                        │ POST /api/payment/order │                       │
  │                        │────────────────────────>│                       │
  │                        │                         │ Create Order          │
  │                        │                         │──────────────────────>│
  │                        │                         │<──────────────────────│
  │                        │                         │ order_id, amount      │
  │                        │<────────────────────────│                       │
  │                        │                         │                       │
  │                        │ Open Razorpay Checkout  │                       │
  │<───────────────────────│                         │                       │
  │                        │                         │                       │
  │ Complete Payment       │                         │                       │
  │───────────────────────────────────────────────────────────────────────>│
  │                        │                         │                       │
  │<──────────────────────────────────────────────────────────────────────│
  │ Payment Response       │                         │                       │
  │                        │                         │                       │
  │───────────────────────>│                         │                       │
  │                        │ POST /api/payment/verify│                       │
  │                        │────────────────────────>│                       │
  │                        │                         │ Verify Signature      │
  │                        │                         │                       │
  │                        │                         │ Create Subscription   │
  │                        │                         │                       │
  │                        │<────────────────────────│                       │
  │                        │ Success + Subscription  │                       │
  │<───────────────────────│                         │                       │
  │                        │                         │                       │
```

### 9.3 API Endpoints (Payment)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/payment/create-order/` | POST | Create Razorpay order |
| `/api/payment/verify/` | POST | Verify payment signature |
| `/api/payment/webhook/` | POST | Handle Razorpay webhooks |
| `/api/payment/refund/` | POST | Process refund |

### 9.4 Order Creation Request

```json
{
  "plan_id": 1,
  "coupon_code": "SAVE20"  // optional
}
```

### 9.5 Order Creation Response

```json
{
  "order_id": "order_ABC123",
  "amount": 99900,  // in paise
  "currency": "INR",
  "key_id": "rzp_live_xxxxx",
  "plan_name": "Pro Plan",
  "description": "Monthly subscription"
}
```

### 9.6 Payment Verification Request

```json
{
  "razorpay_order_id": "order_ABC123",
  "razorpay_payment_id": "pay_XYZ789",
  "razorpay_signature": "signature_hash"
}
```

### 9.7 Webhook Handling

**Webhook URL**: `https://api.yourdomain.com/api/payment/webhook/`

**Signature Verification**:
```python
import razorpay
client = razorpay.Client(auth=(key_id, key_secret))
client.utility.verify_webhook_signature(
    request.body,
    request.headers['X-Razorpay-Signature'],
    webhook_secret
)
```

### 9.8 Supported Payment Methods

| Method | Support |
|--------|---------|
| Credit/Debit Cards | Yes |
| UPI | Yes |
| Net Banking | Yes |
| Wallets | Yes |
| EMI | Optional |

---

## 10. Deployment Requirements

### 10.1 Server Requirements (Hostinger VPS)

**Minimum Specifications**:
| Resource | Requirement |
|----------|-------------|
| CPU | 2 vCPU |
| RAM | 4 GB |
| Storage | 80 GB SSD |
| Bandwidth | 4 TB/month |
| OS | Ubuntu 22.04 LTS |

**Recommended Specifications**:
| Resource | Requirement |
|----------|-------------|
| CPU | 4 vCPU |
| RAM | 8 GB |
| Storage | 160 GB SSD |
| Bandwidth | Unlimited |

### 10.2 Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| MySQL | 8.0+ | Database |
| Redis | 6.0+ | Cache & message broker |
| Nginx | 1.18+ | Web server |
| Supervisor | 4.0+ | Process management |
| Certbot | Latest | SSL certificates |

### 10.3 Domain & SSL

| Requirement | Specification |
|-------------|---------------|
| Domain | Valid domain pointing to VPS |
| SSL Certificate | Let's Encrypt (auto-renewal) |
| HTTPS | Required for all traffic |
| HSTS | Enabled (31536000 seconds) |

### 10.4 Environment Variables

```bash
# Django
DEBUG=False
SECRET_KEY=<256-bit-secure-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=multinotesai
DB_USER=dbuser
DB_PASSWORD=<secure-password>
DB_HOST=localhost
DB_PORT=3306

# AWS S3
AWS_ACCESS_KEY_ID=<aws-key>
AWS_SECRET_ACCESS_KEY=<aws-secret>
AWS_BUCKET=multinotes-bucket
AWS_DEFAULT_REGION=ap-south-1

# Razorpay
RAZORPAY_KEY_ID=rzp_live_xxxxx
RAZORPAY_KEY_SECRET=<secret>
RAZORPAY_WEBHOOK_SECRET=<webhook-secret>

# Email
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=<smtp-password>

# OAuth
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-secret>
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

# LLM APIs
TOGETHER_API_KEY=<together-key>
GEMINI_API_KEY=<gemini-key>
OPENAI_API_KEY=<openai-key>
```

### 10.5 Process Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         NGINX                                    │
│                    (Reverse Proxy)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Static    │  │   API       │  │      WebSocket          │ │
│  │   Files     │  │   Proxy     │  │       Proxy             │ │
│  │   /static/  │  │   /api/     │  │       /ws/              │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
    ┌──────────┐    ┌───────────┐        ┌───────────┐
    │  Files   │    │ Gunicorn  │        │  Daphne   │
    │  (Disk)  │    │ (WSGI)    │        │  (ASGI)   │
    └──────────┘    │ Workers:4 │        │ Workers:2 │
                    └───────────┘        └───────────┘
                          │
                          ▼
                    ┌───────────┐
                    │  Celery   │
                    │  Workers  │
                    │  (4)      │
                    └───────────┘
                          │
                          ▼
                    ┌───────────┐
                    │  Celery   │
                    │   Beat    │
                    │ (Scheduler)│
                    └───────────┘
```

### 10.6 Supervisor Configuration

**Gunicorn (WSGI)**:
```ini
[program:gunicorn]
command=/path/to/venv/bin/gunicorn backend.wsgi:application -w 4 -b 127.0.0.1:8000
directory=/path/to/project
user=deploy
autostart=true
autorestart=true
```

**Daphne (ASGI)**:
```ini
[program:daphne]
command=/path/to/venv/bin/daphne -b 127.0.0.1 -p 8001 backend.asgi:application
directory=/path/to/project
user=deploy
autostart=true
autorestart=true
```

**Celery Worker**:
```ini
[program:celery_worker]
command=/path/to/venv/bin/celery -A backend worker -l info
directory=/path/to/project
user=deploy
autostart=true
autorestart=true
```

**Celery Beat**:
```ini
[program:celery_beat]
command=/path/to/venv/bin/celery -A backend beat -l info
directory=/path/to/project
user=deploy
autostart=true
autorestart=true
```

---

## Appendix A: API Endpoint Reference

### Authentication APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | User registration |
| POST | `/api/auth/login/` | Email/password login |
| POST | `/api/auth/social-login/` | Social authentication |
| POST | `/api/auth/verify-email/` | Email verification |
| POST | `/api/auth/resend-verification/` | Resend verification |
| POST | `/api/auth/forgot-password/` | Request password reset |
| POST | `/api/auth/reset-password/` | Reset password |
| POST | `/api/auth/change-password/` | Change password |
| GET | `/api/auth/user/<id>/` | Get user profile |
| PATCH | `/api/auth/user/<id>/` | Update user profile |
| POST | `/api/auth/upload-image/` | Upload profile image |
| GET | `/api/auth/image-url/` | Get image URL |

### AI Generation APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/user/generate/` | Dynamic LLM generation |
| POST | `/api/user/text-generate/` | Text-to-text |
| POST | `/api/user/file-generate/` | File-based generation |
| POST | `/api/user/gemini/text/` | Gemini text |
| POST | `/api/user/gemini/image/` | Gemini image analysis |
| POST | `/api/user/openai/text/` | OpenAI text |
| POST | `/api/user/tts/` | Text-to-speech |
| POST | `/api/user/stt/` | Speech-to-text |

### Content Management APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/user/folders/` | List/Create folders |
| GET/PATCH/DELETE | `/api/user/folders/<id>/` | Folder operations |
| GET/POST | `/api/user/documents/` | List/Create documents |
| GET/PATCH/DELETE | `/api/user/documents/<id>/` | Document operations |
| GET/POST | `/api/user/content/` | User content |
| POST | `/api/user/share/` | Share content |
| GET | `/api/user/shared-with-me/` | Shared content |

### Subscription APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/plan/` | List plans |
| GET | `/api/subscription/` | User subscription |
| POST | `/api/subscription/create/` | Create subscription |
| GET | `/api/transaction/` | Transaction history |

### Admin APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users/` | List users |
| GET/PATCH | `/api/admin/users/<id>/` | User management |
| GET/POST | `/api/admin/llm/` | LLM management |
| GET/POST | `/api/admin/plans/` | Plan management |
| GET/POST | `/api/admin/categories/` | Category management |
| GET | `/api/admin/analytics/` | Dashboard analytics |

---

## Appendix B: Error Codes

| Code | HTTP Status | Description |
|------|:-----------:|-------------|
| AUTH_001 | 400 | Invalid credentials |
| AUTH_002 | 400 | Email already exists |
| AUTH_003 | 400 | Username already exists |
| AUTH_004 | 401 | User blocked |
| AUTH_005 | 406 | User not verified |
| AUTH_006 | 400 | Invalid/expired token |
| SUB_001 | 402 | Insufficient tokens |
| SUB_002 | 402 | Subscription expired |
| SUB_003 | 402 | Storage limit exceeded |
| LLM_001 | 400 | Model not found |
| LLM_002 | 400 | Model not connected |
| LLM_003 | 500 | Generation error |
| PAY_001 | 400 | Invalid payment |
| PAY_002 | 400 | Payment failed |
| PAY_003 | 400 | Invalid coupon |

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| Token | Unit measuring AI model usage (input + output) |
| File Token | Tokens for file-based operations (image, audio, video) |
| Cluster | Enterprise organization with shared resources |
| SSE | Server-Sent Events for streaming AI responses |
| Prompt | User input to AI model |
| Response | AI model output |
| Group | Conversation thread for multi-turn interactions |

---

**Document End**

*This document should be reviewed and updated as requirements evolve.*
