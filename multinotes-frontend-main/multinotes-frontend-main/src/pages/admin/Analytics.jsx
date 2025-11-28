import { useEffect, useState } from 'react';
import {
  ChartBarIcon,
  CurrencyDollarIcon,
  UsersIcon,
  SparklesIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
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
} from 'recharts';
import api from '../../services/api';

const Analytics = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('30days');
  const [analyticsData, setAnalyticsData] = useState({
    userRetention: [],
    revenueBreakdown: [],
    featureUsage: [],
    cohortAnalysis: [],
    metrics: {
      totalRevenue: 0,
      revenueGrowth: 0,
      activeUsers: 0,
      userGrowth: 0,
      avgRevPerUser: 0,
      churnRate: 0,
    },
  });

  useEffect(() => {
    fetchAnalyticsData();
  }, [timeRange]);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/admin/analytics', {
        params: { timeRange },
      });
      setAnalyticsData(response.data);
    } catch (err) {
      console.error('Error fetching analytics data:', err);
      setError(err.response?.data?.message || 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];

  const metricCards = [
    {
      name: 'Total Revenue',
      value: `$${analyticsData.metrics.totalRevenue.toLocaleString()}`,
      change: analyticsData.metrics.revenueGrowth,
      changeType: analyticsData.metrics.revenueGrowth >= 0 ? 'positive' : 'negative',
      icon: CurrencyDollarIcon,
      color: 'bg-green-500',
    },
    {
      name: 'Active Users',
      value: analyticsData.metrics.activeUsers.toLocaleString(),
      change: analyticsData.metrics.userGrowth,
      changeType: analyticsData.metrics.userGrowth >= 0 ? 'positive' : 'negative',
      icon: UsersIcon,
      color: 'bg-blue-500',
    },
    {
      name: 'Avg Revenue/User',
      value: `$${analyticsData.metrics.avgRevPerUser.toFixed(2)}`,
      change: '+12.5%',
      changeType: 'positive',
      icon: ChartBarIcon,
      color: 'bg-purple-500',
    },
    {
      name: 'Churn Rate',
      value: `${analyticsData.metrics.churnRate.toFixed(1)}%`,
      change: '-2.1%',
      changeType: 'positive',
      icon: ArrowTrendingUpIcon,
      color: 'bg-orange-500',
    },
  ];

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
          <ChartBarIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">Error Loading Analytics</h3>
          <p className="text-slate-600 mb-4">{error}</p>
          <button onClick={fetchAnalyticsData} className="btn-primary">
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
          <h1 className="text-2xl font-bold text-slate-900">Analytics Dashboard</h1>
          <p className="text-slate-600 mt-1">Detailed insights into user behavior and revenue</p>
        </div>
        <div className="flex items-center gap-3">
          <CalendarIcon className="w-5 h-5 text-slate-400" />
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="input py-2 px-4"
          >
            <option value="7days">Last 7 days</option>
            <option value="30days">Last 30 days</option>
            <option value="90days">Last 90 days</option>
            <option value="1year">Last year</option>
          </select>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metricCards.map((metric) => (
          <div key={metric.name} className="card p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-500">{metric.name}</p>
                <p className="mt-2 text-3xl font-bold text-slate-900">{metric.value}</p>
                <p
                  className={`mt-2 text-sm flex items-center ${
                    metric.changeType === 'positive' ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {metric.changeType === 'positive' ? (
                    <ArrowTrendingUpIcon className="w-4 h-4 mr-1" />
                  ) : (
                    <ArrowTrendingDownIcon className="w-4 h-4 mr-1" />
                  )}
                  {metric.change}% vs last period
                </p>
              </div>
              <div className={`w-12 h-12 ${metric.color} rounded-xl flex items-center justify-center`}>
                <metric.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* User Retention Chart */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-6">User Retention</h2>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={analyticsData.userRetention}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="week" stroke="#64748b" />
            <YAxis stroke="#64748b" label={{ value: '%', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '0.5rem',
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="week1"
              stroke="#6366f1"
              strokeWidth={2}
              name="Week 1"
              dot={{ fill: '#6366f1' }}
            />
            <Line
              type="monotone"
              dataKey="week2"
              stroke="#8b5cf6"
              strokeWidth={2}
              name="Week 2"
              dot={{ fill: '#8b5cf6' }}
            />
            <Line
              type="monotone"
              dataKey="week4"
              stroke="#ec4899"
              strokeWidth={2}
              name="Week 4"
              dot={{ fill: '#ec4899' }}
            />
            <Line
              type="monotone"
              dataKey="week8"
              stroke="#f59e0b"
              strokeWidth={2}
              name="Week 8"
              dot={{ fill: '#f59e0b' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Breakdown */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-6">Revenue Breakdown</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={analyticsData.revenueBreakdown}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {analyticsData.revenueBreakdown.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {analyticsData.revenueBreakdown.map((item, index) => (
              <div key={item.name} className="flex items-center space-x-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                ></div>
                <span className="text-sm text-slate-600">
                  {item.name}: ${item.value.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Usage */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-6">Feature Usage Heatmap</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analyticsData.featureUsage} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis type="number" stroke="#64748b" />
              <YAxis dataKey="feature" type="category" stroke="#64748b" width={100} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                }}
              />
              <Bar dataKey="usage" fill="#8b5cf6" name="Usage Count" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cohort Analysis Table */}
      <div className="card overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Cohort Analysis</h2>
          <p className="text-sm text-slate-600 mt-1">User retention by signup cohort</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Cohort
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Users
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Week 0
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Week 1
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Week 2
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Week 3
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Week 4
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {analyticsData.cohortAnalysis && analyticsData.cohortAnalysis.length > 0 ? (
                analyticsData.cohortAnalysis.map((cohort, index) => (
                  <tr key={index} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                      {cohort.month}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-slate-900">
                      {cohort.users}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <span
                        className="inline-flex px-3 py-1 rounded-full font-medium"
                        style={{
                          backgroundColor: `rgba(99, 102, 241, ${cohort.week0 / 100})`,
                          color: cohort.week0 > 50 ? '#fff' : '#000',
                        }}
                      >
                        {cohort.week0}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <span
                        className="inline-flex px-3 py-1 rounded-full font-medium"
                        style={{
                          backgroundColor: `rgba(99, 102, 241, ${cohort.week1 / 100})`,
                          color: cohort.week1 > 50 ? '#fff' : '#000',
                        }}
                      >
                        {cohort.week1}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <span
                        className="inline-flex px-3 py-1 rounded-full font-medium"
                        style={{
                          backgroundColor: `rgba(99, 102, 241, ${cohort.week2 / 100})`,
                          color: cohort.week2 > 50 ? '#fff' : '#000',
                        }}
                      >
                        {cohort.week2}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <span
                        className="inline-flex px-3 py-1 rounded-full font-medium"
                        style={{
                          backgroundColor: `rgba(99, 102, 241, ${cohort.week3 / 100})`,
                          color: cohort.week3 > 50 ? '#fff' : '#000',
                        }}
                      >
                        {cohort.week3}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <span
                        className="inline-flex px-3 py-1 rounded-full font-medium"
                        style={{
                          backgroundColor: `rgba(99, 102, 241, ${cohort.week4 / 100})`,
                          color: cohort.week4 > 50 ? '#fff' : '#000',
                        }}
                      >
                        {cohort.week4}%
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="7" className="px-6 py-8 text-center text-slate-500">
                    No cohort data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-slate-500">Conversion Rate</h3>
            <SparklesIcon className="w-5 h-5 text-indigo-600" />
          </div>
          <p className="text-3xl font-bold text-slate-900">24.5%</p>
          <p className="text-sm text-green-600 mt-2">+3.2% from last period</p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-slate-500">Avg Session Duration</h3>
            <ChartBarIcon className="w-5 h-5 text-purple-600" />
          </div>
          <p className="text-3xl font-bold text-slate-900">12m 34s</p>
          <p className="text-sm text-green-600 mt-2">+1m 15s from last period</p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-slate-500">Customer Lifetime Value</h3>
            <CurrencyDollarIcon className="w-5 h-5 text-green-600" />
          </div>
          <p className="text-3xl font-bold text-slate-900">$487</p>
          <p className="text-sm text-green-600 mt-2">+$52 from last period</p>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
