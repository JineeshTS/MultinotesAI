import { useState, useEffect } from 'react';
import {
  PlusIcon,
  PlayIcon,
  XMarkIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  SparklesIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';

const BatchProcessing = () => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [activeJobs, setActiveJobs] = useState([]);
  const [jobHistory, setJobHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [models, setModels] = useState([]);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    prompts: [''],
    llm_id: '',
    batch_size: 10,
    max_concurrent: 3,
  });

  useEffect(() => {
    fetchModels();
    fetchActiveJobs();
    fetchJobHistory();

    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      fetchActiveJobs();
    }, 5000);

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

  const fetchActiveJobs = async () => {
    try {
      const response = await fetch('/api/user/batch-jobs/?status=pending,processing', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      setActiveJobs(data);
    } catch (error) {
      console.error('Failed to fetch active jobs:', error);
    }
  };

  const fetchJobHistory = async () => {
    try {
      const response = await fetch('/api/user/batch-jobs/?status=completed,failed', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      setJobHistory(data);
    } catch (error) {
      console.error('Failed to fetch job history:', error);
    }
  };

  const handleAddPrompt = () => {
    setFormData({
      ...formData,
      prompts: [...formData.prompts, ''],
    });
  };

  const handleRemovePrompt = (index) => {
    const newPrompts = formData.prompts.filter((_, i) => i !== index);
    setFormData({ ...formData, prompts: newPrompts });
  };

  const handlePromptChange = (index, value) => {
    const newPrompts = [...formData.prompts];
    newPrompts[index] = value;
    setFormData({ ...formData, prompts: newPrompts });
  };

  const handleCreateJob = async (e) => {
    e.preventDefault();

    const validPrompts = formData.prompts.filter((p) => p.trim());
    if (validPrompts.length === 0) {
      toast.error('Please add at least one prompt');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/user/batch-jobs/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          ...formData,
          prompts: validPrompts,
        }),
      });

      if (!response.ok) throw new Error('Failed to create batch job');

      toast.success('Batch job created successfully');
      setShowCreateForm(false);
      setFormData({
        name: '',
        prompts: [''],
        llm_id: formData.llm_id,
        batch_size: 10,
        max_concurrent: 3,
      });
      fetchActiveJobs();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelJob = async (jobId) => {
    try {
      const response = await fetch(`/api/user/batch-jobs/${jobId}/cancel/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Failed to cancel job');

      toast.success('Job cancelled successfully');
      fetchActiveJobs();
      fetchJobHistory();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleRetryJob = async (jobId) => {
    try {
      const response = await fetch(`/api/user/batch-jobs/${jobId}/retry/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Failed to retry job');

      toast.success('Job restarted successfully');
      fetchActiveJobs();
      fetchJobHistory();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleDownloadResults = async (jobId) => {
    try {
      const response = await fetch(`/api/user/batch-jobs/${jobId}/results/`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Failed to download results');

      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `batch-job-${jobId}-results.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Results downloaded successfully');
    } catch (error) {
      toast.error(error.message);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <ExclamationCircleIcon className="w-5 h-5 text-red-500" />;
      case 'processing':
        return <ClockIcon className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <ClockIcon className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'failed':
        return 'bg-red-100 text-red-700';
      case 'processing':
        return 'bg-blue-100 text-blue-700';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Batch Processing</h1>
          <p className="text-slate-500 mt-1">
            Process multiple prompts efficiently in batch jobs
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="btn-primary flex items-center gap-2"
        >
          <PlusIcon className="w-4 h-4" />
          Create Batch Job
        </button>
      </div>

      {/* Create Job Form */}
      {showCreateForm && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Create New Batch Job
          </h2>
          <form onSubmit={handleCreateJob} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Job Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="e.g., Product descriptions generation"
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
                    {model.name} - {model.tokens_per_request} tokens/req
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Batch Size
                </label>
                <input
                  type="number"
                  value={formData.batch_size}
                  onChange={(e) =>
                    setFormData({ ...formData, batch_size: parseInt(e.target.value) })
                  }
                  min="1"
                  max="100"
                  className="input"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Max Concurrent
                </label>
                <input
                  type="number"
                  value={formData.max_concurrent}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      max_concurrent: parseInt(e.target.value),
                    })
                  }
                  min="1"
                  max="10"
                  className="input"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Prompts
              </label>
              <div className="space-y-2">
                {formData.prompts.map((prompt, index) => (
                  <div key={index} className="flex gap-2">
                    <textarea
                      value={prompt}
                      onChange={(e) => handlePromptChange(index, e.target.value)}
                      placeholder={`Prompt ${index + 1}`}
                      rows={2}
                      className="input flex-1"
                      required
                    />
                    {formData.prompts.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemovePrompt(index)}
                        className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                      >
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={handleAddPrompt}
                className="mt-2 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                + Add Another Prompt
              </button>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary flex items-center gap-2"
              >
                <PlayIcon className="w-4 h-4" />
                {isLoading ? 'Creating...' : 'Create & Start Job'}
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

      {/* Active Jobs */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Active Jobs</h2>
        {activeJobs.length > 0 ? (
          <div className="space-y-4">
            {activeJobs.map((job) => (
              <div key={job.id} className="card p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg flex items-center justify-center">
                      <SparklesIcon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{job.name}</h3>
                      <p className="text-sm text-slate-500">
                        {job.prompts_count} prompts • {job.model_name}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        job.status
                      )}`}
                    >
                      {job.status}
                    </span>
                    {getStatusIcon(job.status)}
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-slate-600">Progress</span>
                    <span className="font-medium text-slate-900">
                      {job.completed_count || 0} / {job.total_count || 0}
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                      style={{
                        width: `${
                          ((job.completed_count || 0) / (job.total_count || 1)) * 100
                        }%`,
                      }}
                    />
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-4 mb-4 pb-4 border-b border-slate-100">
                  <div>
                    <p className="text-xs text-slate-500">Started</p>
                    <p className="text-sm font-medium text-slate-900">
                      {new Date(job.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Success</p>
                    <p className="text-sm font-medium text-green-600">
                      {job.success_count || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Failed</p>
                    <p className="text-sm font-medium text-red-600">
                      {job.failed_count || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Estimated Time</p>
                    <p className="text-sm font-medium text-slate-900">
                      {job.estimated_time || '--'}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  {job.status === 'processing' && (
                    <button
                      onClick={() => handleCancelJob(job.id)}
                      className="btn-danger flex items-center gap-2 text-sm"
                    >
                      <XMarkIcon className="w-4 h-4" />
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-8 text-center">
            <ClockIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-medium text-slate-900">No active jobs</h3>
            <p className="text-sm text-slate-500 mt-1">
              Create a new batch job to get started
            </p>
          </div>
        )}
      </div>

      {/* Job History */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Job History</h2>
        {jobHistory.length > 0 ? (
          <div className="space-y-3">
            {jobHistory.map((job) => (
              <div
                key={job.id}
                className="card p-4 flex items-center justify-between hover:shadow-md transition-shadow"
              >
                <div className="flex items-center gap-4">
                  {getStatusIcon(job.status)}
                  <div>
                    <h3 className="font-medium text-slate-900">{job.name}</h3>
                    <p className="text-sm text-slate-500">
                      {job.completed_count} / {job.total_count} completed •{' '}
                      {new Date(job.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                      job.status
                    )}`}
                  >
                    {job.status}
                  </span>
                  {job.status === 'completed' && (
                    <button
                      onClick={() => handleDownloadResults(job.id)}
                      className="btn-secondary flex items-center gap-2 text-sm"
                    >
                      <ArrowDownTrayIcon className="w-4 h-4" />
                      Download
                    </button>
                  )}
                  {job.status === 'failed' && (
                    <button
                      onClick={() => handleRetryJob(job.id)}
                      className="btn-secondary flex items-center gap-2 text-sm"
                    >
                      <ArrowPathIcon className="w-4 h-4" />
                      Retry
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-8 text-center">
            <ClockIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-medium text-slate-900">No job history</h3>
            <p className="text-sm text-slate-500 mt-1">
              Completed jobs will appear here
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BatchProcessing;
