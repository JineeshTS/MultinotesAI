import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  Bars3Icon,
  MagnifyingGlassIcon,
  BellIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';
import {
  toggleSidebar,
  toggleCommandPalette,
  toggleNotificationPanel,
} from '../../store/slices/uiSlice';

const Header = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector((state) => state.auth);

  const handleNewChat = () => {
    navigate('/ai/chat');
  };

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b border-slate-200 bg-white px-6">
      {/* Mobile Menu Toggle */}
      <button
        onClick={() => dispatch(toggleSidebar())}
        className="lg:hidden p-2 rounded-lg hover:bg-slate-100"
      >
        <Bars3Icon className="w-5 h-5 text-slate-600" />
      </button>

      {/* Search Bar */}
      <div className="flex-1 max-w-xl">
        <button
          onClick={() => dispatch(toggleCommandPalette())}
          className="flex items-center w-full gap-3 px-4 py-2 text-left text-slate-500 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
        >
          <MagnifyingGlassIcon className="w-5 h-5" />
          <span className="flex-1 text-sm">Search or type a command...</span>
          <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-slate-400 bg-slate-200 rounded">
            <span>⌘</span>
            <span>K</span>
          </kbd>
        </button>
      </div>

      {/* Right Side Actions */}
      <div className="flex items-center gap-2">
        {/* New Chat Button */}
        <button
          onClick={handleNewChat}
          className="btn-primary flex items-center gap-2"
        >
          <PlusIcon className="w-4 h-4" />
          <span className="hidden sm:inline">New Chat</span>
        </button>

        {/* Notifications */}
        <button
          onClick={() => dispatch(toggleNotificationPanel())}
          className="relative p-2 rounded-lg hover:bg-slate-100 text-slate-600"
        >
          <BellIcon className="w-5 h-5" />
          {/* Notification Badge */}
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* User Avatar */}
        <button className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-100">
          <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
            <span className="text-indigo-600 font-medium text-sm">
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </span>
          </div>
        </button>
      </div>
    </header>
  );
};

export default Header;
