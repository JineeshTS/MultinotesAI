import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import {
  ChatBubbleLeftRightIcon,
  FolderIcon,
  SparklesIcon,
  RocketLaunchIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { fetchTokenBalance } from '../../store/slices/tokenSlice';
import { fetchConversations } from '../../store/slices/chatSlice';

const Dashboard = () => {
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);
  const { balance, usedTokens } = useSelector((state) => state.tokens);
  const { conversations } = useSelector((state) => state.chat);

  useEffect(() => {
    dispatch(fetchTokenBalance());
    dispatch(fetchConversations());
  }, [dispatch]);

  const quickActions = [
    {
      name: 'New Chat',
      description: 'Start a conversation with AI',
      href: '/ai/chat',
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-indigo-500',
    },
    {
      name: 'Browse Templates',
      description: 'Explore prompt templates',
      href: '/ai/templates',
      icon: SparklesIcon,
      color: 'bg-purple-500',
    },
    {
      name: 'My Documents',
      description: 'View and manage files',
      href: '/documents',
      icon: FolderIcon,
      color: 'bg-blue-500',
    },
    {
      name: 'Compare Models',
      description: 'Compare AI responses',
      href: '/ai/compare',
      icon: RocketLaunchIcon,
      color: 'bg-pink-500',
    },
  ];

  const stats = [
    {
      name: 'Token Balance',
      value: balance?.toLocaleString() || 0,
      change: '+2,500 this month',
      changeType: 'positive',
    },
    {
      name: 'Tokens Used',
      value: usedTokens?.toLocaleString() || 0,
      change: 'Last 30 days',
      changeType: 'neutral',
    },
    {
      name: 'Conversations',
      value: conversations?.length || 0,
      change: 'Total',
      changeType: 'neutral',
    },
    {
      name: 'Documents',
      value: '12',
      change: '3 shared with you',
      changeType: 'neutral',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 text-white">
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.name?.split(' ')[0] || 'User'}!
        </h1>
        <p className="mt-2 text-indigo-100 max-w-2xl">
          Ready to create something amazing? Start a new conversation with AI or
          explore our template library to get inspired.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/ai/chat" className="btn bg-white text-indigo-600 hover:bg-indigo-50">
            Start New Chat
          </Link>
          <Link to="/ai/templates" className="btn bg-white/20 text-white hover:bg-white/30">
            Browse Templates
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.name} className="card p-6">
            <p className="text-sm font-medium text-slate-500">{stat.name}</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{stat.value}</p>
            <p
              className={`mt-2 text-sm ${
                stat.changeType === 'positive'
                  ? 'text-green-600'
                  : stat.changeType === 'negative'
                  ? 'text-red-600'
                  : 'text-slate-500'
              }`}
            >
              {stat.change}
            </p>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action) => (
            <Link
              key={action.name}
              to={action.href}
              className="card p-6 hover:shadow-md transition-shadow group"
            >
              <div
                className={`w-12 h-12 ${action.color} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}
              >
                <action.icon className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-semibold text-slate-900">{action.name}</h3>
              <p className="text-sm text-slate-500 mt-1">{action.description}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent Conversations */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">
            Recent Conversations
          </h2>
          <Link
            to="/ai/chat"
            className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
          >
            View all
          </Link>
        </div>

        {conversations && conversations.length > 0 ? (
          <div className="card divide-y divide-slate-200">
            {conversations.slice(0, 5).map((conversation) => (
              <Link
                key={conversation.id}
                to={`/ai/chat/${conversation.id}`}
                className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
              >
                <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <ChatBubbleLeftRightIcon className="w-5 h-5 text-indigo-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 truncate">
                    {conversation.title || 'Untitled Conversation'}
                  </p>
                  <p className="text-sm text-slate-500 truncate">
                    {conversation.last_message || 'No messages yet'}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <ClockIcon className="w-4 h-4" />
                  <span>{conversation.updated_at || 'Just now'}</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="card p-8 text-center">
            <ChatBubbleLeftRightIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-medium text-slate-900">No conversations yet</h3>
            <p className="text-sm text-slate-500 mt-1">
              Start your first AI conversation to see it here
            </p>
            <Link to="/ai/chat" className="btn-primary mt-4 inline-block">
              Start Chatting
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
