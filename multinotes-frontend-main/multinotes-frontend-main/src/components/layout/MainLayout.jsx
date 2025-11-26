import { Outlet } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import Sidebar from './Sidebar';
import Header from './Header';
import CommandPalette from '../common/CommandPalette';
import NotificationPanel from '../common/NotificationPanel';

const MainLayout = () => {
  const dispatch = useDispatch();
  const { sidebarOpen, sidebarCollapsed, commandPaletteOpen } = useSelector(
    (state) => state.ui
  );

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} isCollapsed={sidebarCollapsed} />

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />

        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Command Palette Modal */}
      {commandPaletteOpen && <CommandPalette />}

      {/* Notification Panel */}
      <NotificationPanel />
    </div>
  );
};

export default MainLayout;
