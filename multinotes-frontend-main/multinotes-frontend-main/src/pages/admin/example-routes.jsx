/**
 * Example Router Configuration for Admin Pages
 *
 * Add these routes to your main router configuration.
 * This file is for reference only - integrate these routes into your existing router.
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import {
  AdminDashboard,
  UserManagement,
  SystemHealth,
  Analytics,
} from './pages/admin';

// Example Admin Layout Component (you may already have one)
const AdminLayout = ({ children }) => {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Admin Navigation */}
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-slate-900">Admin Panel</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <a
                  href="/admin"
                  className="border-indigo-500 text-slate-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Dashboard
                </a>
                <a
                  href="/admin/users"
                  className="border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Users
                </a>
                <a
                  href="/admin/system-health"
                  className="border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  System Health
                </a>
                <a
                  href="/admin/analytics"
                  className="border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Analytics
                </a>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Admin Content */}
      <main className="max-w-7xl mx-auto">
        {children}
      </main>
    </div>
  );
};

// Example protected route component
const ProtectedAdminRoute = ({ children }) => {
  const { user } = useSelector((state) => state.auth);

  // Check if user is admin
  if (!user?.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// Example admin routes configuration
export const AdminRoutes = () => {
  return (
    <Routes>
      <Route
        path="/admin/*"
        element={
          <ProtectedAdminRoute>
            <AdminLayout>
              <Routes>
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={<UserManagement />} />
                <Route path="system-health" element={<SystemHealth />} />
                <Route path="analytics" element={<Analytics />} />
              </Routes>
            </AdminLayout>
          </ProtectedAdminRoute>
        }
      />
    </Routes>
  );
};

// Alternative: Flat route structure (integrate into your main App.jsx router)
export const AdminRoutesFlat = [
  {
    path: '/admin',
    element: (
      <ProtectedAdminRoute>
        <AdminLayout>
          <AdminDashboard />
        </AdminLayout>
      </ProtectedAdminRoute>
    ),
  },
  {
    path: '/admin/users',
    element: (
      <ProtectedAdminRoute>
        <AdminLayout>
          <UserManagement />
        </AdminLayout>
      </ProtectedAdminRoute>
    ),
  },
  {
    path: '/admin/system-health',
    element: (
      <ProtectedAdminRoute>
        <AdminLayout>
          <SystemHealth />
        </AdminLayout>
      </ProtectedAdminRoute>
    ),
  },
  {
    path: '/admin/analytics',
    element: (
      <ProtectedAdminRoute>
        <AdminLayout>
          <Analytics />
        </AdminLayout>
      </ProtectedAdminRoute>
    ),
  },
];

/**
 * Usage in App.jsx:
 *
 * import { AdminRoutes } from './pages/admin/example-routes';
 *
 * function App() {
 *   return (
 *     <Router>
 *       <Routes>
 *         <Route path="/" element={<Home />} />
 *         <Route path="/dashboard" element={<Dashboard />} />
 *         // ... other routes
 *       </Routes>
 *       <AdminRoutes />
 *     </Router>
 *   );
 * }
 */
