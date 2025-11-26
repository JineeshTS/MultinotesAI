import { Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';

// Layout
import MainLayout from './components/layout/MainLayout';
import AuthLayout from './components/layout/AuthLayout';

// Auth Pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';
import VerifyEmail from './pages/auth/VerifyEmail';

// Dashboard Pages
import Dashboard from './pages/dashboard/Dashboard';
import TokenDashboard from './pages/dashboard/TokenDashboard';

// AI Pages
import AIChat from './pages/ai/AIChat';
import PromptTemplates from './pages/ai/PromptTemplates';
import ModelComparison from './pages/ai/ModelComparison';

// Document Pages
import Documents from './pages/documents/Documents';
import FolderView from './pages/documents/FolderView';
import SharedWithMe from './pages/documents/SharedWithMe';

// Settings Pages
import Settings from './pages/settings/Settings';
import Profile from './pages/settings/Profile';
import Subscription from './pages/settings/Subscription';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useSelector((state) => state.auth);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Public Route Component (redirects to dashboard if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated } = useSelector((state) => state.auth);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function App() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
        <Route path="/forgot-password" element={<PublicRoute><ForgotPassword /></PublicRoute>} />
        <Route path="/reset-password/:token" element={<PublicRoute><ResetPassword /></PublicRoute>} />
        <Route path="/verify-email/:token" element={<VerifyEmail />} />
      </Route>

      {/* Protected Routes */}
      <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tokens" element={<TokenDashboard />} />

        {/* AI Routes */}
        <Route path="/ai/chat" element={<AIChat />} />
        <Route path="/ai/chat/:conversationId" element={<AIChat />} />
        <Route path="/ai/templates" element={<PromptTemplates />} />
        <Route path="/ai/compare" element={<ModelComparison />} />

        {/* Document Routes */}
        <Route path="/documents" element={<Documents />} />
        <Route path="/documents/folder/:folderId" element={<FolderView />} />
        <Route path="/documents/shared" element={<SharedWithMe />} />

        {/* Settings Routes */}
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/profile" element={<Profile />} />
        <Route path="/settings/subscription" element={<Subscription />} />
      </Route>

      {/* Redirect root to dashboard or login */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 404 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
