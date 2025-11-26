import { NavLink, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  HomeIcon,
  ChatBubbleLeftRightIcon,
  FolderIcon,
  DocumentTextIcon,
  SparklesIcon,
  CreditCardIcon,
  Cog6ToothIcon,
  ArrowLeftOnRectangleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  RectangleStackIcon,
  UsersIcon,
  ChartBarIcon,
  CalendarIcon,
  QueueListIcon,
  LinkIcon,
  ShieldCheckIcon,
  ServerIcon,
  ChartPieIcon,
} from '@heroicons/react/24/outline';
import { toggleSidebarCollapsed } from '../../store/slices/uiSlice';
import { logout } from '../../store/slices/authSlice';
import classNames from 'classnames';

const Sidebar = ({ isOpen, isCollapsed, isAdmin = false }) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector((state) => state.auth);
  const { balance } = useSelector((state) => state.tokens);

  // Regular user navigation
  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
    { name: 'AI Chat', href: '/ai/chat', icon: ChatBubbleLeftRightIcon },
    { name: 'Templates', href: '/ai/templates', icon: RectangleStackIcon },
    { name: 'Compare Models', href: '/ai/compare', icon: SparklesIcon },
    { name: 'Batch Processing', href: '/ai/batch', icon: QueueListIcon },
    { name: 'Scheduled Jobs', href: '/ai/schedule', icon: CalendarIcon },
    { name: 'Prompt Chaining', href: '/ai/chain', icon: LinkIcon },
    { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
    { name: 'Documents', href: '/documents', icon: FolderIcon },
    { name: 'Shared with Me', href: '/documents/shared', icon: UsersIcon },
    { name: 'Tokens', href: '/tokens', icon: CreditCardIcon },
  ];

  // Admin navigation
  const adminNavigation = [
    { name: 'Admin Dashboard', href: '/admin', icon: ShieldCheckIcon },
    { name: 'User Management', href: '/admin/users', icon: UsersIcon },
    { name: 'System Health', href: '/admin/system', icon: ServerIcon },
    { name: 'Analytics', href: '/admin/analytics', icon: ChartPieIcon },
  ];

  // Choose navigation based on admin status
  const currentNavigation = isAdmin ? adminNavigation : navigation;

  const bottomNavigation = [
    { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
  ];

  const handleLogout = async () => {
    await dispatch(logout());
    navigate('/login');
  };

  if (!isOpen) return null;

  return (
    <div
      className={classNames(
        'flex flex-col bg-white border-r border-slate-200 transition-all duration-300',
        isCollapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-slate-200">
        {!isCollapsed && (
          <div className="flex items-center gap-3">
            <div className={classNames(
              "w-8 h-8 rounded-lg flex items-center justify-center",
              isAdmin ? "bg-red-600" : "bg-indigo-600"
            )}>
              <span className="text-white font-bold text-sm">M</span>
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-slate-900">Multinotes.ai</span>
              {isAdmin && (
                <span className="text-xs text-red-600 font-medium">Admin Panel</span>
              )}
            </div>
          </div>
        )}
        {isCollapsed && (
          <div className={classNames(
            "w-8 h-8 rounded-lg flex items-center justify-center mx-auto",
            isAdmin ? "bg-red-600" : "bg-indigo-600"
          )}>
            <span className="text-white font-bold text-sm">M</span>
          </div>
        )}
        <button
          onClick={() => dispatch(toggleSidebarCollapsed())}
          className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600"
        >
          {isCollapsed ? (
            <ChevronRightIcon className="w-5 h-5" />
          ) : (
            <ChevronLeftIcon className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Token Balance */}
      {!isCollapsed && (
        <div className="p-4 border-b border-slate-200">
          <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-4 text-white">
            <div className="text-xs font-medium text-indigo-100">Token Balance</div>
            <div className="text-2xl font-bold mt-1">
              {balance?.toLocaleString() || 0}
            </div>
            <div className="mt-2">
              <NavLink
                to="/tokens"
                className="text-xs text-indigo-100 hover:text-white underline"
              >
                View Details &rarr;
              </NavLink>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {currentNavigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              classNames(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                isCollapsed && 'justify-center'
              )
            }
            title={isCollapsed ? item.name : undefined}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span>{item.name}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Bottom Navigation */}
      <div className="p-4 border-t border-slate-200 space-y-1">
        {/* Admin/User View Switcher for Admin Users */}
        {user?.role === 'admin' && (
          <NavLink
            to={isAdmin ? '/dashboard' : '/admin'}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-indigo-600 hover:bg-indigo-50 transition-colors justify-center"
            title={isCollapsed ? (isAdmin ? 'User View' : 'Admin Panel') : undefined}
          >
            <ShieldCheckIcon className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span>{isAdmin ? 'Switch to User View' : 'Admin Panel'}</span>}
          </NavLink>
        )}

        {bottomNavigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              classNames(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                isCollapsed && 'justify-center'
              )
            }
            title={isCollapsed ? item.name : undefined}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span>{item.name}</span>}
          </NavLink>
        ))}

        {/* User Profile */}
        <div
          className={classNames(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg',
            isCollapsed && 'justify-center'
          )}
        >
          <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
            <span className="text-indigo-600 font-medium text-sm">
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </span>
          </div>
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-900 truncate">
                {user?.name || 'User'}
              </div>
              <div className="text-xs text-slate-500 truncate">
                {user?.email || 'user@example.com'}
              </div>
            </div>
          )}
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className={classNames(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 w-full transition-colors',
            isCollapsed && 'justify-center'
          )}
          title={isCollapsed ? 'Logout' : undefined}
        >
          <ArrowLeftOnRectangleIcon className="w-5 h-5 flex-shrink-0" />
          {!isCollapsed && <span>Logout</span>}
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
