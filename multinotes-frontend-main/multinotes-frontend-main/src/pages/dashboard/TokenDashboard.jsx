import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import {
  CreditCardIcon,
  ArrowTrendingUpIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import {
  fetchTokenBalance,
  fetchDailyUsage,
  fetchUsageBreakdown,
} from '../../store/slices/tokenSlice';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const TokenDashboard = () => {
  const dispatch = useDispatch();
  const { balance, usedTokens, totalTokens, dailyUsage, usageBreakdown, isLoading } =
    useSelector((state) => state.tokens);
  const [timeRange, setTimeRange] = useState(30);

  useEffect(() => {
    dispatch(fetchTokenBalance());
    dispatch(fetchDailyUsage(timeRange));
    dispatch(fetchUsageBreakdown());
  }, [dispatch, timeRange]);

  const usagePercentage = totalTokens > 0 ? (usedTokens / totalTokens) * 100 : 0;
  const isLowBalance = balance < 1000;

  // Chart data for daily usage
  const dailyChartData = {
    labels: dailyUsage?.map((d) => d.date) || [],
    datasets: [
      {
        label: 'Tokens Used',
        data: dailyUsage?.map((d) => d.tokens) || [],
        fill: true,
        borderColor: 'rgb(99, 102, 241)',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
      },
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
      },
    },
  };

  // Usage breakdown by model
  const breakdownChartData = {
    labels: usageBreakdown?.map((b) => b.model) || ['GPT-4', 'Claude', 'Gemini'],
    datasets: [
      {
        data: usageBreakdown?.map((b) => b.tokens) || [40, 35, 25],
        backgroundColor: [
          'rgba(99, 102, 241, 0.8)',
          'rgba(168, 85, 247, 0.8)',
          'rgba(236, 72, 153, 0.8)',
          'rgba(34, 197, 94, 0.8)',
        ],
        borderWidth: 0,
      },
    ],
  };

  const optimizationTips = [
    {
      title: 'Use efficient prompts',
      description: 'Shorter, focused prompts consume fewer tokens',
    },
    {
      title: 'Choose the right model',
      description: 'Smaller models work great for simple tasks',
    },
    {
      title: 'Leverage templates',
      description: 'Pre-built templates are optimized for token usage',
    },
  ];

  const tokenEstimates = [
    { operation: 'Simple question', tokens: '50-100' },
    { operation: 'Content generation', tokens: '200-500' },
    { operation: 'Document analysis', tokens: '300-800' },
    { operation: 'Code generation', tokens: '400-1000' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Token Dashboard</h1>
          <p className="text-slate-500 mt-1">
            Monitor your token usage and manage your balance
          </p>
        </div>
        <button
          onClick={() => dispatch(fetchTokenBalance())}
          className="btn-secondary flex items-center gap-2"
        >
          <ArrowPathIcon className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Low Balance Warning */}
      {isLowBalance && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-start gap-3">
          <ExclamationTriangleIcon className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-yellow-800">Low Token Balance</h3>
            <p className="text-sm text-yellow-700 mt-1">
              You have less than 1,000 tokens remaining. Consider upgrading your plan
              to continue using AI features.
            </p>
            <Link
              to="/settings/subscription"
              className="inline-block mt-2 text-sm font-medium text-yellow-800 hover:text-yellow-900"
            >
              Upgrade Plan &rarr;
            </Link>
          </div>
        </div>
      )}

      {/* Token Balance Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-sm font-medium text-slate-500">Token Balance</p>
              <p className="text-4xl font-bold text-slate-900 mt-1">
                {balance?.toLocaleString() || 0}
              </p>
            </div>
            <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center">
              <CreditCardIcon className="w-8 h-8 text-indigo-600" />
            </div>
          </div>

          {/* Usage Progress Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500">Usage this period</span>
              <span className="font-medium text-slate-900">
                {usedTokens?.toLocaleString()} / {totalTokens?.toLocaleString()}
              </span>
            </div>
            <div className="token-meter">
              <div
                className="token-meter-fill bg-gradient-to-r from-indigo-500 to-purple-500"
                style={{ width: `${Math.min(usagePercentage, 100)}%` }}
              />
            </div>
            <p className="text-xs text-slate-400">
              {usagePercentage.toFixed(1)}% of your plan used
            </p>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-200">
            <div>
              <p className="text-sm text-slate-500">Daily Average</p>
              <p className="text-xl font-bold text-slate-900">
                {Math.round(usedTokens / 30).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-500">Estimated Days Left</p>
              <p className="text-xl font-bold text-slate-900">
                {Math.round(balance / (usedTokens / 30)) || '∞'}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-500">Plan</p>
              <p className="text-xl font-bold text-indigo-600">Pro</p>
            </div>
          </div>
        </div>

        {/* Usage Breakdown */}
        <div className="card p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Usage by Model</h3>
          <div className="h-48">
            <Doughnut
              data={breakdownChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'bottom',
                    labels: {
                      usePointStyle: true,
                      padding: 20,
                    },
                  },
                },
                cutout: '65%',
              }}
            />
          </div>
        </div>
      </div>

      {/* Usage Chart */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-semibold text-slate-900">Token Usage Over Time</h3>
          <div className="flex items-center gap-2">
            {[7, 14, 30].map((days) => (
              <button
                key={days}
                onClick={() => setTimeRange(days)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  timeRange === days
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-slate-500 hover:bg-slate-100'
                }`}
              >
                {days}D
              </button>
            ))}
          </div>
        </div>
        <div className="h-64">
          <Line data={dailyChartData} options={chartOptions} />
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Token Estimates */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <ChartBarIcon className="w-5 h-5 text-slate-400" />
            <h3 className="font-semibold text-slate-900">Token Estimates</h3>
          </div>
          <div className="space-y-3">
            {tokenEstimates.map((estimate) => (
              <div
                key={estimate.operation}
                className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
              >
                <span className="text-slate-600">{estimate.operation}</span>
                <span className="font-medium text-slate-900">
                  {estimate.tokens} tokens
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Optimization Tips */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <LightBulbIcon className="w-5 h-5 text-yellow-500" />
            <h3 className="font-semibold text-slate-900">Optimization Tips</h3>
          </div>
          <div className="space-y-4">
            {optimizationTips.map((tip, index) => (
              <div key={index} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-xs font-medium">
                  {index + 1}
                </span>
                <div>
                  <p className="font-medium text-slate-900">{tip.title}</p>
                  <p className="text-sm text-slate-500">{tip.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Upgrade CTA */}
      <div className="card bg-gradient-to-r from-indigo-600 to-purple-600 p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold">Need more tokens?</h3>
            <p className="text-indigo-100 mt-1">
              Upgrade your plan to get more tokens and unlock premium features.
            </p>
          </div>
          <Link
            to="/settings/subscription"
            className="btn bg-white text-indigo-600 hover:bg-indigo-50 flex-shrink-0"
          >
            Upgrade Plan
          </Link>
        </div>
      </div>
    </div>
  );
};

export default TokenDashboard;
