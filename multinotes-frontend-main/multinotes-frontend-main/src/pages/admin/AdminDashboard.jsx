import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  UsersIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  ServerIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import api from '../../services/api';

const AdminDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState({
    stats: {
      totalUsers: 0,
      newUsersToday: 0,
      activeUsers: 0,
      totalRevenue: 0,
      revenueToday: 0,
      totalPrompts: 0,
      totalTokens: 0,
      totalGenerations: 0,
    },
    revenueData: [],
    activityFeed: [],
    systemHealth: {
      database: 'healthy',
      redis: 'healthy',
      celery: 'healthy',
      api: 'healthy',
    },
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/admin/dashboard');
      setDashboardData(response.data);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err.response?.data?.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const statsCards = [
    {
      name: 'Total Users',
      value: dashboardData.stats.totalUsers.toLocaleString(),
      change: `+${dashboardData.stats.newUsersToday} today`,
      changeType: 'positive',
      icon: UsersIcon,
      color: 'bg-blue-500',
      link: '/admin/users',
    },
    {
      name: 'Active Users',
      value: dashboardData.stats.activeUsers.toLocaleString(),
      change: 'Last 24 hours',
      changeType: 'neutral',
      icon: ArrowTrendingUpIcon,
      color: 'bg-green-500',
      link: '/admin/users',
    },
    {
      name: 'Total Revenue',
      value: `$${dashboardData.stats.totalRevenue.toLocaleString()}`,
      change: `+$${dashboardData.stats.revenueToday} today`,
      changeType: 'positive',
      icon: CurrencyDollarIcon,
      color: 'bg-purple-500',
      link: '/admin/analytics',
    },
    {
      name: 'Total Prompts',
      value: dashboardData.stats.totalPrompts.toLocaleString(),
      change: 'All time',
      changeType: 'neutral',
      icon: ChartBarIcon,
      color: 'bg-indigo-500',
      link: '/admin/analytics',
    },
  ];

  const usageMetrics = [
    {
      label: 'Total Prompts',
      value: dashboardData.stats.totalPrompts.toLocaleString(),
      icon: ChartBarIcon,
      color: 'text-blue-600',
    },
    {
      label: 'Total Tokens',
      value: (dashboardData.stats.totalTokens / 1000000).toFixed(2) + 'M',
      icon: ServerIcon,
      color: 'text-purple-600',
    },
    {
      label: 'Total Generations',
      value: dashboardData.stats.totalGenerations.toLocaleString(),
      icon: ArrowTrendingUpIcon,
      color: 'text-green-600',
    },
  ];

  const getHealthStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'critical':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getHealthStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="w-5 h-5" />;
      case 'warning':
      case 'critical':
        return <ExclamationTriangleIcon className="w-5 h-5" />;
      default:
        return <ServerIcon className="w-5 h-5" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <ExclamationTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">Error Loading Dashboard</h3>
          <p className="text-slate-600 mb-4">{error}</p>
          <button onClick={fetchDashboardData} className="btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin Dashboard</h1>
          <p className="text-slate-600 mt-1">Overview of your system performance and metrics</p>
        </div>
        <button
          onClick={fetchDashboardData}
          className="btn bg-white border border-slate-300 hover:bg-slate-50"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsCards.map((stat) => (
          <Link
            key={stat.name}
            to={stat.link}
            className="card p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-500">{stat.name}</p>
                <p className="mt-2 text-3xl font-bold text-slate-900">{stat.value}</p>
                <p
                  className={`mt-2 text-sm flex items-center ${
                    stat.changeType === 'positive'
                      ? 'text-green-600'
                      : stat.changeType === 'negative'
                      ? 'text-red-600'
                      : 'text-slate-500'
                  }`}
                >
                  {stat.changeType === 'positive' && (
                    <ArrowTrendingUpIcon className="w-4 h-4 mr-1" />
                  )}
                  {stat.changeType === 'negative' && (
                    <ArrowTrendingDownIcon className="w-4 h-4 mr-1" />
                  )}
                  {stat.change}
                </p>
              </div>
              <div className={`w-12 h-12 ${stat.color} rounded-xl flex items-center justify-center`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Revenue Chart */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-slate-900">Revenue Overview</h2>
          <select className="input py-2 px-3 text-sm">
            <option>Last 7 days</option>
            <option>Last 30 days</option>
            <option>Last 90 days</option>
          </select>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={dashboardData.revenueData}>
            <defs>
              <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="date" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '0.5rem',
              }}
            />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke="#8b5cf6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorRevenue)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Usage Metrics */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-6">Usage Metrics</h2>
          <div className="space-y-4">
            {usageMetrics.map((metric) => (
              <div key={metric.label} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <metric.icon className={`w-6 h-6 ${metric.color}`} />
                  <span className="font-medium text-slate-700">{metric.label}</span>
                </div>
                <span className="text-2xl font-bold text-slate-900">{metric.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* System Health */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-slate-900">System Health</h2>
            <Link to="/admin/system-health" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
              View Details
            </Link>
          </div>
          <div className="space-y-3">
            {Object.entries(dashboardData.systemHealth).map(([service, status]) => (
              <div key={service} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  {getHealthStatusIcon(status)}
                  <span className="font-medium text-slate-700 capitalize">{service}</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getHealthStatusColor(status)}`}>
                  {status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity Feed */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-6">Recent Activity</h2>
        {dashboardData.activityFeed && dashboardData.activityFeed.length > 0 ? (
          <div className="space-y-4">
            {dashboardData.activityFeed.map((activity, index) => (
              <div key={index} className="flex items-start space-x-4 pb-4 border-b border-slate-200 last:border-0">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  activity.type === 'user' ? 'bg-blue-100' :
                  activity.type === 'revenue' ? 'bg-green-100' :
                  activity.type === 'system' ? 'bg-yellow-100' :
                  'bg-gray-100'
                }`}>
                  {activity.type === 'user' && <UsersIcon className="w-5 h-5 text-blue-600" />}
                  {activity.type === 'revenue' && <CurrencyDollarIcon className="w-5 h-5 text-green-600" />}
                  {activity.type === 'system' && <ServerIcon className="w-5 h-5 text-yellow-600" />}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-900">{activity.message}</p>
                  <div className="flex items-center mt-1 text-xs text-slate-500">
                    <ClockIcon className="w-3 h-3 mr-1" />
                    {activity.timestamp}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500">
            <ClockIcon className="w-12 h-12 mx-auto mb-2 text-slate-300" />
            <p>No recent activity</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
