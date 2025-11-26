import { useState, useEffect } from 'react';
import {
  PlusIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  ClockIcon,
  CalendarIcon,
  SparklesIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';

const ScheduledGenerations = () => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [activeSchedules, setActiveSchedules] = useState([]);
  const [scheduleHistory, setScheduleHistory] = useState([]);
  const [models, setModels] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCronHelper, setShowCronHelper] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    prompt: '',
    llm_id: '',
    schedule_type: 'simple',
    cron_expression: '0 9 * * *',
    simple_schedule: {
      frequency: 'daily',
      time: '09:00',
      day_of_week: '',
      day_of_month: '',
    },
    enabled: true,
  });

  const frequencyOptions = [
    { value: 'hourly', label: 'Hourly' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'monthly', label: 'Monthly' },
  ];

  const cronPresets = [
    { label: 'Every hour', value: '0 * * * *' },
    { label: 'Every day at 9 AM', value: '0 9 * * *' },
    { label: 'Every Monday at 9 AM', value: '0 9 * * 1' },
    { label: 'First day of month at 9 AM', value: '0 9 1 * *' },
    { label: 'Every weekday at 9 AM', value: '0 9 * * 1-5' },
  ];

  useEffect(() => {
    fetchModels();
    fetchActiveSchedules();
    fetchScheduleHistory();

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchActiveSchedules();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/llm-models/', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      setModels(data);
      if (data.length > 0) {
        setFormData((prev) => ({ ...prev, llm_id: data[0].id }));
      }
    } catch (error) {
      toast.error('Failed to fetch models');
    }
  };

  const fetchActiveSchedules = async () => {
    try {
      const response = await fetch('/api/user/scheduled-generations/', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      setActiveSchedules(data.filter((s) => s.enabled || s.status === 'active'));
    } catch (error) {
      console.error('Failed to fetch schedules:', error);
    }
  };

  const fetchScheduleHistory = async () => {
    try {
      const response = await fetch('/api/user/scheduled-generations/history/', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      setScheduleHistory(data);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    }
  };

  const buildCronExpression = () => {
    const { frequency, time, day_of_week, day_of_month } = formData.simple_schedule;
    const [hour, minute] = time.split(':');

    switch (frequency) {
      case 'hourly':
        return `0 * * * *`;
      case 'daily':
        return `${minute} ${hour} * * *`;
      case 'weekly':
        return `${minute} ${hour} * * ${day_of_week}`;
      case 'monthly':
        return `${minute} ${hour} ${day_of_month} * *`;
      default:
        return '0 9 * * *';
    }
  };

  const handleCreateSchedule = async (e) => {
    e.preventDefault();

    const cronExpression =
      formData.schedule_type === 'simple'
        ? buildCronExpression()
        : formData.cron_expression;

    setIsLoading(true);
    try {
      const response = await fetch('/api/user/scheduled-generations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          name: formData.name,
          prompt: formData.prompt,
          llm_id: formData.llm_id,
          cron_expression: cronExpression,
          enabled: formData.enabled,
        }),
      });

      if (!response.ok) throw new Error('Failed to create schedule');

      toast.success('Schedule created successfully');
      setShowCreateForm(false);
      setFormData({
        name: '',
        prompt: '',
        llm_id: formData.llm_id,
        schedule_type: 'simple',
        cron_expression: '0 9 * * *',
        simple_schedule: {
          frequency: 'daily',
          time: '09:00',
          day_of_week: '',
          day_of_month: '',
        },
        enabled: true,
      });
      fetchActiveSchedules();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePauseSchedule = async (scheduleId) => {
    try {
      const response = await fetch(
        `/api/user/scheduled-generations/${scheduleId}/pause/`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (!response.ok) throw new Error('Failed to pause schedule');

      toast.success('Schedule paused');
      fetchActiveSchedules();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleResumeSchedule = async (scheduleId) => {
    try {
      const response = await fetch(
        `/api/user/scheduled-generations/${scheduleId}/resume/`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (!response.ok) throw new Error('Failed to resume schedule');

      toast.success('Schedule resumed');
      fetchActiveSchedules();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleDeleteSchedule = async (scheduleId) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;

    try {
      const response = await fetch(`/api/user/scheduled-generations/${scheduleId}/`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Failed to delete schedule');

      toast.success('Schedule deleted');
      fetchActiveSchedules();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const formatNextRun = (nextRun) => {
    if (!nextRun) return 'Not scheduled';
    const date = new Date(nextRun);
    const now = new Date();
    const diff = date - now;

    if (diff < 0) return 'Overdue';

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours < 1) return `in ${minutes}m`;
    if (hours < 24) return `in ${hours}h ${minutes}m`;
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Scheduled Generations
          </h1>
          <p className="text-slate-500 mt-1">
            Automate AI content generation with scheduled tasks
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="btn-primary flex items-center gap-2"
        >
          <PlusIcon className="w-4 h-4" />
          Create Schedule
        </button>
      </div>

      {/* Create Schedule Form */}
      {showCreateForm && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Create New Schedule
          </h2>
          <form onSubmit={handleCreateSchedule} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Schedule Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="e.g., Daily market summary"
                className="input"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Prompt
              </label>
              <textarea
                value={formData.prompt}
                onChange={(e) =>
                  setFormData({ ...formData, prompt: e.target.value })
                }
                placeholder="Enter your prompt here..."
                rows={4}
                className="input"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Model
              </label>
              <select
                value={formData.llm_id}
                onChange={(e) =>
                  setFormData({ ...formData, llm_id: e.target.value })
                }
                className="input"
                required
              >
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Schedule Type Toggle */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Schedule Type
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() =>
                    setFormData({ ...formData, schedule_type: 'simple' })
                  }
                  className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                    formData.schedule_type === 'simple'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Simple
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setFormData({ ...formData, schedule_type: 'advanced' })
                  }
                  className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                    formData.schedule_type === 'advanced'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Advanced (Cron)
                </button>
              </div>
            </div>

            {/* Simple Schedule */}
            {formData.schedule_type === 'simple' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Frequency
                  </label>
                  <select
                    value={formData.simple_schedule.frequency}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        simple_schedule: {
                          ...formData.simple_schedule,
                          frequency: e.target.value,
                        },
                      })
                    }
                    className="input"
                  >
                    {frequencyOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                {formData.simple_schedule.frequency !== 'hourly' && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Time
                    </label>
                    <input
                      type="time"
                      value={formData.simple_schedule.time}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          simple_schedule: {
                            ...formData.simple_schedule,
                            time: e.target.value,
                          },
                        })
                      }
                      className="input"
                    />
                  </div>
                )}

                {formData.simple_schedule.frequency === 'weekly' && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Day of Week
                    </label>
                    <select
                      value={formData.simple_schedule.day_of_week}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          simple_schedule: {
                            ...formData.simple_schedule,
                            day_of_week: e.target.value,
                          },
                        })
                      }
                      className="input"
                      required
                    >
                      <option value="">Select day</option>
                      <option value="1">Monday</option>
                      <option value="2">Tuesday</option>
                      <option value="3">Wednesday</option>
                      <option value="4">Thursday</option>
                      <option value="5">Friday</option>
                      <option value="6">Saturday</option>
                      <option value="0">Sunday</option>
                    </select>
                  </div>
                )}

                {formData.simple_schedule.frequency === 'monthly' && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Day of Month
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="31"
                      value={formData.simple_schedule.day_of_month}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          simple_schedule: {
                            ...formData.simple_schedule,
                            day_of_month: e.target.value,
                          },
                        })
                      }
                      placeholder="1-31"
                      className="input"
                      required
                    />
                  </div>
                )}
              </div>
            )}

            {/* Advanced Cron Expression */}
            {formData.schedule_type === 'advanced' && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium text-slate-700">
                    Cron Expression
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowCronHelper(!showCronHelper)}
                    className="text-sm text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                  >
                    <InformationCircleIcon className="w-4 h-4" />
                    Help
                  </button>
                </div>
                <input
                  type="text"
                  value={formData.cron_expression}
                  onChange={(e) =>
                    setFormData({ ...formData, cron_expression: e.target.value })
                  }
                  placeholder="0 9 * * *"
                  className="input font-mono"
                  required
                />

                {showCronHelper && (
                  <div className="mt-3 p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="text-sm text-slate-700 mb-3">
                      Cron format: <code className="text-indigo-600">minute hour day month weekday</code>
                    </p>
                    <div className="space-y-2">
                      <p className="text-xs text-slate-600">Quick presets:</p>
                      {cronPresets.map((preset) => (
                        <button
                          key={preset.value}
                          type="button"
                          onClick={() =>
                            setFormData({
                              ...formData,
                              cron_expression: preset.value,
                            })
                          }
                          className="block w-full text-left px-3 py-2 text-sm bg-white hover:bg-indigo-50 border border-slate-200 rounded"
                        >
                          <span className="font-medium text-slate-900">
                            {preset.label}
                          </span>
                          <span className="text-slate-500 ml-2 font-mono text-xs">
                            {preset.value}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={(e) =>
                  setFormData({ ...formData, enabled: e.target.checked })
                }
                className="w-4 h-4 text-indigo-600 rounded"
              />
              <label htmlFor="enabled" className="text-sm text-slate-700">
                Enable schedule immediately
              </label>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary flex items-center gap-2"
              >
                <CalendarIcon className="w-4 h-4" />
                {isLoading ? 'Creating...' : 'Create Schedule'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Active Schedules */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Active Schedules
        </h2>
        {activeSchedules.length > 0 ? (
          <div className="space-y-4">
            {activeSchedules.map((schedule) => (
              <div key={schedule.id} className="card p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-500 rounded-lg flex items-center justify-center">
                      <CalendarIcon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        {schedule.name}
                      </h3>
                      <p className="text-sm text-slate-500 mt-1">
                        {schedule.model_name}
                      </p>
                      <p className="text-sm text-slate-600 mt-2 line-clamp-2">
                        {schedule.prompt}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {schedule.enabled ? (
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                        Active
                      </span>
                    ) : (
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                        Paused
                      </span>
                    )}
                  </div>
                </div>

                {/* Schedule Info */}
                <div className="grid grid-cols-3 gap-4 mb-4 pb-4 border-b border-slate-100">
                  <div>
                    <p className="text-xs text-slate-500">Cron Expression</p>
                    <p className="text-sm font-mono font-medium text-slate-900">
                      {schedule.cron_expression}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Next Run</p>
                    <p className="text-sm font-medium text-indigo-600">
                      {formatNextRun(schedule.next_run)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Total Runs</p>
                    <p className="text-sm font-medium text-slate-900">
                      {schedule.run_count || 0}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  {schedule.enabled ? (
                    <button
                      onClick={() => handlePauseSchedule(schedule.id)}
                      className="btn-secondary flex items-center gap-2 text-sm"
                    >
                      <PauseIcon className="w-4 h-4" />
                      Pause
                    </button>
                  ) : (
                    <button
                      onClick={() => handleResumeSchedule(schedule.id)}
                      className="btn-primary flex items-center gap-2 text-sm"
                    >
                      <PlayIcon className="w-4 h-4" />
                      Resume
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteSchedule(schedule.id)}
                    className="btn-danger flex items-center gap-2 text-sm"
                  >
                    <TrashIcon className="w-4 h-4" />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-8 text-center">
            <CalendarIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-medium text-slate-900">No active schedules</h3>
            <p className="text-sm text-slate-500 mt-1">
              Create a schedule to automate your AI generations
            </p>
          </div>
        )}
      </div>

      {/* Schedule History */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Recent Runs
        </h2>
        {scheduleHistory.length > 0 ? (
          <div className="space-y-2">
            {scheduleHistory.slice(0, 10).map((run) => (
              <div
                key={run.id}
                className="card p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  {run.status === 'success' ? (
                    <CheckCircleIcon className="w-5 h-5 text-green-500" />
                  ) : (
                    <XCircleIcon className="w-5 h-5 text-red-500" />
                  )}
                  <div>
                    <h3 className="font-medium text-slate-900 text-sm">
                      {run.schedule_name}
                    </h3>
                    <p className="text-xs text-slate-500">
                      {new Date(run.executed_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-xs text-slate-500">Duration</p>
                    <p className="text-sm font-medium text-slate-900">
                      {run.duration}s
                    </p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      run.status === 'success'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {run.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-8 text-center">
            <ClockIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-medium text-slate-900">No run history</h3>
            <p className="text-sm text-slate-500 mt-1">
              Schedule runs will appear here
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ScheduledGenerations;
