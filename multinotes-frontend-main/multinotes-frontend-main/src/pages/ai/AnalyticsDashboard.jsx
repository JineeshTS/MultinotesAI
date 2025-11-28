import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import {
  ArrowDownTrayIcon,
  CalendarIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  SparklesIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';

const AnalyticsDashboard = () => {
  const [dateRange, setDateRange] = useState('7d');
  const [isLoading, setIsLoading] = useState(true);
  const [analytics, setAnalytics] = useState({
    tokenUsage: [],
    costBreakdown: [],
    generationHistory: [],
    usagePatterns: [],
    summary: {
      totalTokens: 0,
      totalCost: 0,
      totalGenerations: 0,
      avgResponseTime: 0,
    },
  });

  const dateRangeOptions = [
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' },
    { value: '90d', label: 'Last 90 Days' },
    { value: 'all', label: 'All Time' },
  ];

  const COLORS = [
    '#6366f1',
    '#8b5cf6',
    '#ec4899',
    '#f59e0b',
    '#10b981',
    '#06b6d4',
  ];

  useEffect(() => {
    fetchAnalytics();
  }, [dateRange]);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/user/analytics/?range=${dateRange}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (!response.ok) throw new Error('Failed to fetch analytics');

      const data = await response.json();
      setAnalytics(data);
    } catch (error) {
      toast.error('Failed to load analytics');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const exportReport = async () => {
    try {
      const response = await fetch(
        `/api/user/analytics/export/?range=${dateRange}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (!response.ok) throw new Error('Failed to export report');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics-report-${dateRange}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Report exported successfully');
    } catch (error) {
      toast.error(error.message);
    }
  };

  const formatNumber = (num) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="skeleton h-8 w-48 mb-2" />
            <div className="skeleton h-4 w-64" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-6">
              <div className="skeleton h-12 w-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Analytics Dashboard
          </h1>
          <p className="text-slate-500 mt-1">
            Track your AI usage, costs, and performance
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="input"
          >
            {dateRangeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button
            onClick={exportReport}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
              <SparklesIcon className="w-6 h-6 text-indigo-600" />
            </div>
          </div>
          <p className="text-sm text-slate-500 mb-1">Total Tokens</p>
          <p className="text-2xl font-bold text-slate-900">
            {formatNumber(analytics.summary.totalTokens)}
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <CurrencyDollarIcon className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <p className="text-sm text-slate-500 mb-1">Total Cost</p>
          <p className="text-2xl font-bold text-slate-900">
            {formatCurrency(analytics.summary.totalCost)}
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
              <ChartBarIcon className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <p className="text-sm text-slate-500 mb-1">Generations</p>
          <p className="text-2xl font-bold text-slate-900">
            {formatNumber(analytics.summary.totalGenerations)}
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center">
              <ClockIcon className="w-6 h-6 text-orange-600" />
            </div>
          </div>
          <p className="text-sm text-slate-500 mb-1">Avg Response Time</p>
          <p className="text-2xl font-bold text-slate-900">
            {analytics.summary.avgResponseTime}s
          </p>
        </div>
      </div>

      {/* Token Usage Over Time */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Token Usage Over Time
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={analytics.tokenUsage}>
            <defs>
              <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              stroke="#64748b"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              stroke="#64748b"
              style={{ fontSize: '12px' }}
              tickFormatter={formatNumber}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
              }}
              formatter={(value) => [formatNumber(value), 'Tokens']}
            />
            <Area
              type="monotone"
              dataKey="tokens"
              stroke="#6366f1"
              fillOpacity={1}
              fill="url(#colorTokens)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Cost Breakdown & Usage Patterns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Breakdown by Model */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Cost Breakdown by Model
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={analytics.costBreakdown}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
                outerRadius={100}
                fill="#8884d8"
                dataKey="cost"
              >
                {analytics.costBreakdown.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => formatCurrency(value)}
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>

          {/* Legend */}
          <div className="mt-4 space-y-2">
            {analytics.costBreakdown.map((item, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-sm text-slate-700">{item.name}</span>
                </div>
                <span className="text-sm font-medium text-slate-900">
                  {formatCurrency(item.cost)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Usage Patterns (Hourly) */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Usage Patterns (by Hour)
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analytics.usagePatterns}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="hour"
                stroke="#64748b"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke="#64748b"
                style={{ fontSize: '12px' }}
                tickFormatter={formatNumber}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                }}
                formatter={(value) => [formatNumber(value), 'Requests']}
              />
              <Bar dataKey="requests" fill="#6366f1" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Generation History */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Generation History
        </h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Date & Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Model
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Tokens
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {analytics.generationHistory.length > 0 ? (
                analytics.generationHistory.map((item, index) => (
                  <tr key={index} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                      {new Date(item.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg flex items-center justify-center">
                          <SparklesIcon className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-sm text-slate-900">
                          {item.model}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                      {formatNumber(item.tokens)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                      {formatCurrency(item.cost)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                      {item.duration}s
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          item.status === 'success'
                            ? 'bg-green-100 text-green-800'
                            : item.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan="6"
                    className="px-6 py-8 text-center text-sm text-slate-500"
                  >
                    No generation history available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {analytics.generationHistory.length > 10 && (
          <div className="mt-4 text-center">
            <button className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
              Load more
            </button>
          </div>
        )}
      </div>

      {/* Quick Insights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-5">
          <h3 className="text-sm font-medium text-slate-700 mb-2">
            Most Used Model
          </h3>
          <p className="text-xl font-semibold text-slate-900">
            {analytics.costBreakdown[0]?.name || 'N/A'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {analytics.costBreakdown[0]?.percentage || 0}% of total usage
          </p>
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-medium text-slate-700 mb-2">
            Peak Usage Hour
          </h3>
          <p className="text-xl font-semibold text-slate-900">
            {analytics.usagePatterns.reduce(
              (max, item) => (item.requests > max.requests ? item : max),
              analytics.usagePatterns[0] || { hour: 'N/A' }
            ).hour}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Most active time of day
          </p>
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-medium text-slate-700 mb-2">
            Cost Efficiency
          </h3>
          <p className="text-xl font-semibold text-slate-900">
            {analytics.summary.totalGenerations > 0
              ? formatCurrency(
                  analytics.summary.totalCost /
                    analytics.summary.totalGenerations
                )
              : '$0.00'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Average cost per generation
          </p>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
