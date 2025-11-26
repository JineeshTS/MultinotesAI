import { useDispatch, useSelector } from 'react-redux';
import { XMarkIcon, BellIcon, CheckCircleIcon, ExclamationCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { toggleNotificationPanel } from '../../store/slices/uiSlice';
import classNames from 'classnames';

const NotificationPanel = () => {
  const dispatch = useDispatch();
  const { notificationPanelOpen } = useSelector((state) => state.ui);

  // Mock notifications - in a real app, these would come from Redux/API
  const notifications = [
    {
      id: 1,
      type: 'success',
      title: 'Generation Complete',
      message: 'Your AI response has been generated successfully.',
      time: '2 min ago',
      read: false,
    },
    {
      id: 2,
      type: 'info',
      title: 'New Template Available',
      message: 'Check out the new marketing templates in the library.',
      time: '1 hour ago',
      read: false,
    },
    {
      id: 3,
      type: 'warning',
      title: 'Low Token Balance',
      message: 'You have 500 tokens remaining. Consider upgrading your plan.',
      time: '3 hours ago',
      read: true,
    },
  ];

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'warning':
        return <ExclamationCircleIcon className="w-5 h-5 text-yellow-500" />;
      case 'error':
        return <ExclamationCircleIcon className="w-5 h-5 text-red-500" />;
      default:
        return <InformationCircleIcon className="w-5 h-5 text-blue-500" />;
    }
  };

  if (!notificationPanelOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={() => dispatch(toggleNotificationPanel())}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 z-50 h-full w-full max-w-sm bg-white shadow-xl border-l border-slate-200 animate-slide-left">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <BellIcon className="w-5 h-5 text-slate-600" />
            <h2 className="text-lg font-semibold text-slate-900">Notifications</h2>
          </div>
          <button
            onClick={() => dispatch(toggleNotificationPanel())}
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-slate-100">
          <button className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            Mark all as read
          </button>
          <button className="text-sm text-slate-500 hover:text-slate-700">
            Clear all
          </button>
        </div>

        {/* Notifications List */}
        <div className="overflow-y-auto h-[calc(100vh-130px)]">
          {notifications.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={classNames(
                    'px-6 py-4 hover:bg-slate-50 cursor-pointer transition-colors',
                    !notification.read && 'bg-indigo-50/50'
                  )}
                >
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {getIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-slate-900">
                          {notification.title}
                        </p>
                        {!notification.read && (
                          <span className="w-2 h-2 bg-indigo-600 rounded-full" />
                        )}
                      </div>
                      <p className="text-sm text-slate-600 mt-1">
                        {notification.message}
                      </p>
                      <p className="text-xs text-slate-400 mt-2">
                        {notification.time}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 px-6">
              <BellIcon className="w-12 h-12 text-slate-300 mb-4" />
              <p className="text-slate-500 text-center">
                No notifications yet
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default NotificationPanel;
