# Admin Panel Installation Guide

## Quick Start

### 1. Install Dependencies

The admin pages require **Recharts** for data visualization. Install it by running:

```bash
cd /home/user/MultinotesAI/multinotes-frontend-main/multinotes-frontend-main
npm install recharts
```

### 2. Verify Installation

All admin page files are already created in:
```
/home/user/MultinotesAI/multinotes-frontend-main/multinotes-frontend-main/src/pages/admin/
```

Files:
- AdminDashboard.jsx (12 KB)
- UserManagement.jsx (16 KB)
- SystemHealth.jsx (15 KB)
- Analytics.jsx (17 KB)
- index.js (export file)
- README.md (documentation)
- example-routes.jsx (router examples)

### 3. Add Routes to Your Application

Option A: Add to your existing router (recommended)
```javascript
// In your App.jsx or router file
import {
  AdminDashboard,
  UserManagement,
  SystemHealth,
  Analytics
} from './pages/admin';

// Add these routes
<Route path="/admin" element={<AdminDashboard />} />
<Route path="/admin/users" element={<UserManagement />} />
<Route path="/admin/system-health" element={<SystemHealth />} />
<Route path="/admin/analytics" element={<Analytics />} />
```

Option B: Use the example routes configuration
See `example-routes.jsx` for a complete example with admin layout and protected routes.

### 4. Backend Setup

Your Django backend needs to implement these API endpoints:

```python
# urls.py
urlpatterns = [
    path('api/admin/dashboard', admin_dashboard_view),
    path('api/admin/users', admin_users_view),
    path('api/admin/users/<int:id>/block', admin_block_user_view),
    path('api/admin/system-health', admin_system_health_view),
    path('api/admin/analytics', admin_analytics_view),
]
```

Refer to `README.md` for detailed response structures for each endpoint.

### 5. Test the Pages

1. Start your development server:
   ```bash
   npm run dev
   ```

2. Navigate to:
   - http://localhost:5173/admin (Dashboard)
   - http://localhost:5173/admin/users (User Management)
   - http://localhost:5173/admin/system-health (System Health)
   - http://localhost:5173/admin/analytics (Analytics)

## Troubleshooting

### Issue: Charts not rendering
**Solution:** Make sure Recharts is installed:
```bash
npm install recharts
```

### Issue: API calls failing
**Solution:** Ensure your backend is running and the API endpoints are implemented.
Check the browser console for specific error messages.

### Issue: Routes not working
**Solution:** Verify routes are properly added to your router configuration.
Make sure React Router is set up correctly.

### Issue: Styling looks broken
**Solution:** Ensure Tailwind CSS is properly configured in your project.
The pages use standard Tailwind classes that should already be available.

## Optional Enhancements

### Add Admin Navigation
Create a sidebar or top navigation for easy switching between admin pages.
See `example-routes.jsx` for a sample admin layout.

### Add Role-Based Access Control
Implement a protected route component to restrict admin access:
```javascript
const ProtectedAdminRoute = ({ children }) => {
  const { user } = useSelector((state) => state.auth);

  if (!user?.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};
```

### Add Real-Time Updates
For System Health page, consider adding WebSocket support for real-time metrics.

### Customize Charts
Modify chart colors, tooltips, and styling to match your brand:
- Edit chart configurations in each component
- Adjust the COLORS array in Analytics.jsx
- Modify Tailwind classes for card backgrounds

## Support

For detailed documentation, see `README.md`.

For example implementations, see `example-routes.jsx`.
