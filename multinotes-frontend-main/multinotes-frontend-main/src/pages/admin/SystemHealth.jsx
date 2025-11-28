import { useEffect, useState } from 'react';
import {
  ServerIcon,
  CircleStackIcon,
  CpuChipIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ChartBarIcon,
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

const SystemHealth = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [healthData, setHealthData] = useState({
    services: {
      database: { status: 'unknown', latency: 0, details: {} },
      redis: { status: 'unknown', latency: 0, details: {} },
      celery: { status: 'unknown', latency: 0, details: {} },
      api: { status: 'unknown', latency: 0, details: {} },
    },
    metrics: {
      apiResponseTime: [],
      errorRate: [],
      requestsPerMinute: [],
    },
    system: {
      cpu_usage: 0,
      memory_usage: 0,
      disk_usage: 0,
      uptime: 0,
    },
  });

  const [autoRefresh, setAutoRefresh] = useState(false);

  useEffect(() => {
    fetchHealthData();
  }, []);

  useEffect(() => {
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchHealthData, 30000); // Refresh every 30 seconds
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const fetchHealthData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/admin/system-health');
      setHealthData(response.data);
    } catch (err) {
      console.error('Error fetching health data:', err);
      setError(err.response?.data?.message || 'Failed to load system health data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
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

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="w-6 h-6" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-6 h-6" />;
      case 'critical':
        return <XCircleIcon className="w-6 h-6" />;
      default:
        return <ServerIcon className="w-6 h-6" />;
    }
  };

  const getServiceIcon = (service) => {
    switch (service) {
      case 'database':
        return <CircleStackIcon className="w-8 h-8" />;
      case 'redis':
        return <CpuChipIcon className="w-8 h-8" />;
      case 'celery':
        return <ClockIcon className="w-8 h-8" />;
      case 'api':
        return <ServerIcon className="w-8 h-8" />;
      default:
        return <ServerIcon className="w-8 h-8" />;
    }
  };

  const formatUptime = (seconds) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  if (loading && !healthData.services.database.status) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error && !healthData.services.database.status) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <XCircleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">Error Loading System Health</h3>
          <p className="text-slate-600 mb-4">{error}</p>
          <button onClick={fetchHealthData} className="btn-primary">
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
          <h1 className="text-2xl font-bold text-slate-900">System Health</h1>
          <p className="text-slate-600 mt-1">Monitor system services and performance metrics</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`btn ${
              autoRefresh
                ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                : 'bg-white border border-slate-300 hover:bg-slate-50'
            }`}
          >
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
            {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
          </button>
          <button
            onClick={fetchHealthData}
            disabled={loading}
            className="btn bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-50"
          >
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Service Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Object.entries(healthData.services).map(([service, data]) => (
          <div key={service} className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="text-slate-600">{getServiceIcon(service)}</div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(data.status)}`}>
                {getStatusIcon(data.status)}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 capitalize mb-2">{service}</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Status:</span>
                <span className="font-medium text-slate-900 capitalize">{data.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Latency:</span>
                <span className="font-medium text-slate-900">{data.latency || 0}ms</span>
              </div>
              {data.details && Object.keys(data.details).length > 0 && (
                <div className="pt-2 border-t border-slate-200">
                  {Object.entries(data.details).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-slate-500 capitalize">{key.replace(/_/g, ' ')}:</span>
                      <span className="font-medium text-slate-700">{value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* System Resources */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <h3 className="text-sm font-medium text-slate-500 mb-4">CPU Usage</h3>
          <div className="flex items-end justify-between">
            <div>
              <p className="text-3xl font-bold text-slate-900">{healthData.system.cpu_usage}%</p>
              <p className="text-sm text-slate-500 mt-1">Current utilization</p>
            </div>
            <div className="w-20 h-20 relative">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="40"
                  cy="40"
                  r="32"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="8"
                />
                <circle
                  cx="40"
                  cy="40"
                  r="32"
                  fill="none"
                  stroke="#6366f1"
                  strokeWidth="8"
                  strokeDasharray={`${(healthData.system.cpu_usage / 100) * 200} 200`}
                  strokeLinecap="round"
                />
              </svg>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-sm font-medium text-slate-500 mb-4">Memory Usage</h3>
          <div className="flex items-end justify-between">
            <div>
              <p className="text-3xl font-bold text-slate-900">{healthData.system.memory_usage}%</p>
              <p className="text-sm text-slate-500 mt-1">Current utilization</p>
            </div>
            <div className="w-20 h-20 relative">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="40"
                  cy="40"
                  r="32"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="8"
                />
                <circle
                  cx="40"
                  cy="40"
                  r="32"
                  fill="none"
                  stroke="#8b5cf6"
                  strokeWidth="8"
                  strokeDasharray={`${(healthData.system.memory_usage / 100) * 200} 200`}
                  strokeLinecap="round"
                />
              </svg>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-sm font-medium text-slate-500 mb-4">Disk Usage</h3>
          <div className="flex items-end justify-between">
            <div>
              <p className="text-3xl font-bold text-slate-900">{healthData.system.disk_usage}%</p>
              <p className="text-sm text-slate-500 mt-1">Current utilization</p>
            </div>
            <div className="w-20 h-20 relative">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="40"
                  cy="40"
                  r="32"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="8"
                />
                <circle
                  cx="40"
                  cy="40"
                  r="32"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="8"
                  strokeDasharray={`${(healthData.system.disk_usage / 100) * 200} 200`}
                  strokeLinecap="round"
                />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* API Response Time */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-6">API Response Time</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={healthData.metrics.apiResponseTime}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="timestamp" stroke="#64748b" />
            <YAxis stroke="#64748b" label={{ value: 'ms', angle: -90, position: 'insideLeft' }} />
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
              dataKey="responseTime"
              stroke="#6366f1"
              strokeWidth={2}
              name="Response Time (ms)"
              dot={{ fill: '#6366f1' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Error Rate */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-6">Error Rate</h2>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={healthData.metrics.errorRate}>
              <defs>
                <linearGradient id="colorErrors" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="timestamp" stroke="#64748b" />
              <YAxis stroke="#64748b" label={{ value: '%', angle: -90, position: 'insideLeft' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                }}
              />
              <Area
                type="monotone"
                dataKey="errorRate"
                stroke="#ef4444"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorErrors)"
                name="Error Rate (%)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Requests Per Minute */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-6">Requests Per Minute</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={healthData.metrics.requestsPerMinute}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="timestamp" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                }}
              />
              <Bar dataKey="requests" fill="#8b5cf6" name="Requests/min" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* System Uptime */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">System Uptime</h2>
            <p className="text-3xl font-bold text-indigo-600 mt-2">
              {formatUptime(healthData.system.uptime || 0)}
            </p>
          </div>
          <ClockIcon className="w-16 h-16 text-slate-300" />
        </div>
      </div>
    </div>
  );
};

export default SystemHealth;
