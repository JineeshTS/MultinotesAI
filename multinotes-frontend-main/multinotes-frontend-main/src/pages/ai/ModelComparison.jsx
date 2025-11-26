import { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  SparklesIcon,
  PaperAirplaneIcon,
  ClockIcon,
  CreditCardIcon,
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import { fetchModels } from '../../store/slices/chatSlice';
import chatService from '../../services/chatService';
import { toast } from 'react-toastify';

const ModelComparison = () => {
  const dispatch = useDispatch();
  const { models } = useSelector((state) => state.chat);

  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState([]);
  const [results, setResults] = useState({});
  const [isComparing, setIsComparing] = useState(false);

  useEffect(() => {
    dispatch(fetchModels());
  }, [dispatch]);

  useEffect(() => {
    // Pre-select first 3 models
    if (models.length > 0 && selectedModels.length === 0) {
      setSelectedModels(models.slice(0, 3).map((m) => m.id));
    }
  }, [models, selectedModels.length]);

  const toggleModel = (modelId) => {
    if (selectedModels.includes(modelId)) {
      setSelectedModels(selectedModels.filter((id) => id !== modelId));
    } else if (selectedModels.length < 4) {
      setSelectedModels([...selectedModels, modelId]);
    } else {
      toast.warning('You can compare up to 4 models at once');
    }
  };

  const handleCompare = async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }
    if (selectedModels.length < 2) {
      toast.error('Please select at least 2 models to compare');
      return;
    }

    setIsComparing(true);
    setResults({});

    try {
      const response = await chatService.compareModels({
        prompt,
        model_ids: selectedModels,
      });

      setResults(response.results || {});
    } catch (error) {
      toast.error('Failed to compare models');
    } finally {
      setIsComparing(false);
    }
  };

  const getModelById = (id) => models.find((m) => m.id === id);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Compare AI Models</h1>
        <p className="text-slate-500 mt-1">
          Run the same prompt on multiple models to compare their responses
        </p>
      </div>

      {/* Model Selection */}
      <div className="card p-6">
        <h2 className="font-semibold text-slate-900 mb-4">
          Select Models to Compare (2-4)
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {models.map((model) => (
            <button
              key={model.id}
              onClick={() => toggleModel(model.id)}
              className={`p-4 rounded-xl border-2 transition-all text-left ${
                selectedModels.includes(model.id)
                  ? 'border-indigo-500 bg-indigo-50'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    selectedModels.includes(model.id)
                      ? 'bg-indigo-500'
                      : 'bg-slate-100'
                  }`}
                >
                  <SparklesIcon
                    className={`w-5 h-5 ${
                      selectedModels.includes(model.id)
                        ? 'text-white'
                        : 'text-slate-500'
                    }`}
                  />
                </div>
                <div>
                  <p className="font-medium text-slate-900">{model.name}</p>
                  <p className="text-xs text-slate-500">
                    {model.tokens_per_request} tokens
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Prompt Input */}
      <div className="card p-6">
        <h2 className="font-semibold text-slate-900 mb-4">Your Prompt</h2>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter a prompt to compare across models..."
          rows={4}
          className="input resize-none"
        />
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-slate-500">
            {selectedModels.length} model{selectedModels.length !== 1 ? 's' : ''}{' '}
            selected
          </p>
          <button
            onClick={handleCompare}
            disabled={isComparing || selectedModels.length < 2 || !prompt.trim()}
            className="btn-primary flex items-center gap-2"
          >
            {isComparing ? (
              <>
                <svg className="animate-spin h-4 w-4\" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Comparing...
              </>
            ) : (
              <>
                <PaperAirplaneIcon className="w-4 h-4" />
                Compare Models
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {Object.keys(results).length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-900 mb-4">Comparison Results</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {selectedModels.map((modelId) => {
              const model = getModelById(modelId);
              const result = results[modelId];

              return (
                <div key={modelId} className="card overflow-hidden">
                  {/* Model Header */}
                  <div className="flex items-center justify-between p-4 bg-slate-50 border-b border-slate-200">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-indigo-500 rounded-lg flex items-center justify-center">
                        <SparklesIcon className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-900">
                          {model?.name || 'Unknown Model'}
                        </p>
                        <p className="text-xs text-slate-500">
                          {model?.provider || 'Provider'}
                        </p>
                      </div>
                    </div>

                    {result && (
                      <div className="flex items-center gap-4 text-sm text-slate-500">
                        <div className="flex items-center gap-1">
                          <ClockIcon className="w-4 h-4" />
                          <span>{result.processing_time}s</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <CreditCardIcon className="w-4 h-4" />
                          <span>{result.tokens_used} tokens</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Response Content */}
                  <div className="p-4 max-h-96 overflow-y-auto">
                    {result ? (
                      result.error ? (
                        <div className="text-red-500">{result.error}</div>
                      ) : (
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>{result.response}</ReactMarkdown>
                        </div>
                      )
                    ) : isComparing ? (
                      <div className="flex items-center gap-2 text-slate-500">
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                            fill="none"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          />
                        </svg>
                        Generating response...
                      </div>
                    ) : (
                      <p className="text-slate-400">No response yet</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelComparison;
