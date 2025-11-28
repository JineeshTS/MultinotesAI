# Admin Panel Pages

Comprehensive admin panel pages for MultinotesAI React frontend.

## Files Created

1. **AdminDashboard.jsx** - Main admin dashboard
2. **UserManagement.jsx** - User management interface
3. **SystemHealth.jsx** - System monitoring dashboard
4. **Analytics.jsx** - Analytics and insights dashboard
5. **index.js** - Centralized exports

## Installation Requirements

### Install Recharts (Required)

The admin pages use Recharts for data visualization. Install it with:

```bash
npm install recharts
```

## Features

### AdminDashboard.jsx
- User statistics cards (total users, new users, active users)
- Revenue overview with area chart
- Usage metrics (prompts, tokens, generations)
- System health status indicators
- Recent activity feed
- Auto-refresh functionality

### UserManagement.jsx
- Searchable and filterable user table
- User status filters (active, blocked, premium, free)
- Block/unblock user actions
- User details modal with full information
- Pagination support
- Subscription status indicators

### SystemHealth.jsx
- Real-time service status monitoring (Database, Redis, Celery, API)
- System resource monitoring (CPU, Memory, Disk)
- API response time charts
- Error rate tracking
- Requests per minute metrics
- Auto-refresh toggle (30-second intervals)
- System uptime display

### Analytics.jsx
- Key metrics dashboard (revenue, users, churn rate)
- User retention line charts
- Revenue breakdown pie chart
- Feature usage heatmap
- Cohort analysis table with visual retention indicators
- Time range filtering (7 days, 30 days, 90 days, 1 year)
- Additional metrics (conversion rate, session duration, customer lifetime value)

## API Endpoints

The pages connect to these admin API endpoints:

```javascript
GET /api/admin/dashboard       // Dashboard data
GET /api/admin/users           // User list
POST /api/admin/users/:id/block // Block/unblock user
GET /api/admin/system-health   // System health metrics
GET /api/admin/analytics       // Analytics data
```

## Usage

### Import Components

```javascript
// Individual imports
import AdminDashboard from './pages/admin/AdminDashboard';
import UserManagement from './pages/admin/UserManagement';
import SystemHealth from './pages/admin/SystemHealth';
import Analytics from './pages/admin/Analytics';

// Or use the index
import {
  AdminDashboard,
  UserManagement,
  SystemHealth,
  Analytics
} from './pages/admin';
```

### Add Routes

Add these routes to your router configuration:

```javascript
import { AdminDashboard, UserManagement, SystemHealth, Analytics } from './pages/admin';

// In your router
<Route path="/admin" element={<AdminDashboard />} />
<Route path="/admin/users" element={<UserManagement />} />
<Route path="/admin/system-health" element={<SystemHealth />} />
<Route path="/admin/analytics" element={<Analytics />} />
```

## Styling

All pages use Tailwind CSS classes that are already configured in your project:
- Card components with `.card` class
- Button components with `.btn`, `.btn-primary` classes
- Input components with `.input` class
- Responsive grid layouts
- Custom color schemes matching your design system

## Icons

Pages use Heroicons (already installed):
- `@heroicons/react/24/outline` for line icons
- `@heroicons/react/24/solid` for filled icons

## Charts

Recharts components used:
- `LineChart` - Trend analysis
- `AreaChart` - Revenue and error rates
- `BarChart` - Feature usage and requests
- `PieChart` - Revenue breakdown

## Error Handling

All pages include:
- Loading states with spinner animations
- Error states with retry buttons
- Empty states with helpful messages
- Try-catch blocks for API calls
- User-friendly error messages

## State Management

Pages use React hooks:
- `useState` for local state
- `useEffect` for data fetching
- No Redux required (uses axios directly)

## Backend Requirements

Your Django backend should implement these endpoints with the following response structures:

### Dashboard Response
```json
{
  "stats": {
    "totalUsers": 1234,
    "newUsersToday": 45,
    "activeUsers": 890,
    "totalRevenue": 45678,
    "revenueToday": 234,
    "totalPrompts": 56789,
    "totalTokens": 123456789,
    "totalGenerations": 34567
  },
  "revenueData": [
    { "date": "2025-01-01", "revenue": 1200 }
  ],
  "activityFeed": [
    {
      "type": "user",
      "message": "New user registered",
      "timestamp": "2 hours ago"
    }
  ],
  "systemHealth": {
    "database": "healthy",
    "redis": "healthy",
    "celery": "healthy",
    "api": "healthy"
  }
}
```

### Users Response
```json
{
  "users": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "is_active": true,
      "subscription_type": "premium",
      "created_at": "2025-01-01T00:00:00Z",
      "token_balance": 10000,
      "total_prompts": 150
    }
  ]
}
```

### System Health Response
```json
{
  "services": {
    "database": {
      "status": "healthy",
      "latency": 5,
      "details": { "connections": 10 }
    },
    "redis": {
      "status": "healthy",
      "latency": 2,
      "details": { "memory_usage": "45%" }
    },
    "celery": {
      "status": "healthy",
      "latency": 3,
      "details": { "active_tasks": 5 }
    },
    "api": {
      "status": "healthy",
      "latency": 8,
      "details": { "requests_per_min": 120 }
    }
  },
  "metrics": {
    "apiResponseTime": [
      { "timestamp": "10:00", "responseTime": 45 }
    ],
    "errorRate": [
      { "timestamp": "10:00", "errorRate": 0.5 }
    ],
    "requestsPerMinute": [
      { "timestamp": "10:00", "requests": 120 }
    ]
  },
  "system": {
    "cpu_usage": 45,
    "memory_usage": 62,
    "disk_usage": 38,
    "uptime": 864000
  }
}
```

### Analytics Response
```json
{
  "metrics": {
    "totalRevenue": 45678,
    "revenueGrowth": 12.5,
    "activeUsers": 890,
    "userGrowth": 8.3,
    "avgRevPerUser": 51.32,
    "churnRate": 3.2
  },
  "userRetention": [
    {
      "week": "Week 1",
      "week1": 100,
      "week2": 85,
      "week4": 70,
      "week8": 55
    }
  ],
  "revenueBreakdown": [
    { "name": "Premium", "value": 25000 },
    { "name": "Basic", "value": 15000 },
    { "name": "Enterprise", "value": 5678 }
  ],
  "featureUsage": [
    { "feature": "AI Chat", "usage": 5000 },
    { "feature": "Templates", "usage": 3500 },
    { "feature": "Documents", "usage": 2800 }
  ],
  "cohortAnalysis": [
    {
      "month": "Jan 2025",
      "users": 250,
      "week0": 100,
      "week1": 85,
      "week2": 72,
      "week3": 65,
      "week4": 58
    }
  ]
}
```

## Notes

- All pages include proper loading states
- Error handling with retry functionality
- Responsive design for mobile/tablet/desktop
- Consistent styling with existing pages
- Production-ready code with best practices
