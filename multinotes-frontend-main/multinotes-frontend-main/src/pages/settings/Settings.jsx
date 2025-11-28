import { NavLink, Outlet } from 'react-router-dom';
import {
  UserCircleIcon,
  CreditCardIcon,
  BellIcon,
  ShieldCheckIcon,
  PaintBrushIcon,
} from '@heroicons/react/24/outline';

const Settings = () => {
  const navigation = [
    { name: 'Profile', href: '/settings/profile', icon: UserCircleIcon },
    { name: 'Subscription', href: '/settings/subscription', icon: CreditCardIcon },
    { name: 'Notifications', href: '/settings/notifications', icon: BellIcon },
    { name: 'Security', href: '/settings/security', icon: ShieldCheckIcon },
    { name: 'Appearance', href: '/settings/appearance', icon: PaintBrushIcon },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 mt-1">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Navigation */}
        <nav className="lg:w-64 flex-shrink-0">
          <div className="card p-2 lg:sticky lg:top-6">
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`
                }
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </NavLink>
            ))}
          </div>
        </nav>

        {/* Content */}
        <div className="flex-1">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default Settings;
