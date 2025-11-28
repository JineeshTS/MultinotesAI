import { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import {
  PlusIcon,
  PlayIcon,
  BookmarkIcon,
  TrashIcon,
  Bars3Icon,
  PencilIcon,
  ArrowRightIcon,
  SparklesIcon,
  DocumentDuplicateIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';

const PromptChaining = () => {
  const [chain, setChain] = useState({
    name: '',
    steps: [],
  });
  const [models, setModels] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResults, setExecutionResults] = useState([]);
  const [expandedSteps, setExpandedSteps] = useState(new Set());
  const [expandedResults, setExpandedResults] = useState(new Set());
  const [showTemplates, setShowTemplates] = useState(false);

  useEffect(() => {
    fetchModels();
    fetchTemplates();
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
    } catch (error) {
      toast.error('Failed to fetch models');
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/user/prompt-chains/', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      setTemplates(data);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
    }
  };

  const addStep = () => {
    const newStep = {
      id: `step-${Date.now()}`,
      name: `Step ${chain.steps.length + 1}`,
      prompt: '',
      llm_id: models[0]?.id || '',
      variables: [],
      use_previous_output: chain.steps.length > 0,
    };
    setChain({
      ...chain,
      steps: [...chain.steps, newStep],
    });
    setExpandedSteps(new Set([...expandedSteps, newStep.id]));
  };

  const removeStep = (stepId) => {
    setChain({
      ...chain,
      steps: chain.steps.filter((step) => step.id !== stepId),
    });
    const newExpanded = new Set(expandedSteps);
    newExpanded.delete(stepId);
    setExpandedSteps(newExpanded);
  };

  const duplicateStep = (stepIndex) => {
    const stepToDuplicate = chain.steps[stepIndex];
    const newStep = {
      ...stepToDuplicate,
      id: `step-${Date.now()}`,
      name: `${stepToDuplicate.name} (Copy)`,
    };
    const newSteps = [...chain.steps];
    newSteps.splice(stepIndex + 1, 0, newStep);
    setChain({ ...chain, steps: newSteps });
  };

  const updateStep = (stepId, field, value) => {
    setChain({
      ...chain,
      steps: chain.steps.map((step) =>
        step.id === stepId ? { ...step, [field]: value } : step
      ),
    });
  };

  const addVariable = (stepId) => {
    const variableName = prompt('Enter variable name (e.g., topic, style):');
    if (!variableName) return;

    setChain({
      ...chain,
      steps: chain.steps.map((step) =>
        step.id === stepId
          ? {
              ...step,
              variables: [...(step.variables || []), variableName],
            }
          : step
      ),
    });
  };

  const removeVariable = (stepId, variableIndex) => {
    setChain({
      ...chain,
      steps: chain.steps.map((step) =>
        step.id === stepId
          ? {
              ...step,
              variables: step.variables.filter((_, i) => i !== variableIndex),
            }
          : step
      ),
    });
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;

    const newSteps = Array.from(chain.steps);
    const [reorderedStep] = newSteps.splice(result.source.index, 1);
    newSteps.splice(result.destination.index, 0, reorderedStep);

    setChain({ ...chain, steps: newSteps });
  };

  const toggleStepExpanded = (stepId) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId);
    } else {
      newExpanded.add(stepId);
    }
    setExpandedSteps(newExpanded);
  };

  const toggleResultExpanded = (index) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedResults(newExpanded);
  };

  const executeChain = async () => {
    if (!chain.name.trim()) {
      toast.error('Please enter a chain name');
      return;
    }

    if (chain.steps.length === 0) {
      toast.error('Please add at least one step');
      return;
    }

    setIsExecuting(true);
    setExecutionResults([]);

    try {
      const response = await fetch('/api/user/prompt-chains/execute/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          name: chain.name,
          steps: chain.steps,
        }),
      });

      if (!response.ok) throw new Error('Failed to execute chain');

      const data = await response.json();
      setExecutionResults(data.results || []);
      toast.success('Chain executed successfully');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsExecuting(false);
    }
  };

  const saveAsTemplate = async () => {
    if (!chain.name.trim()) {
      toast.error('Please enter a chain name');
      return;
    }

    if (chain.steps.length === 0) {
      toast.error('Please add at least one step');
      return;
    }

    try {
      const response = await fetch('/api/user/prompt-chains/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          name: chain.name,
          steps: chain.steps,
        }),
      });

      if (!response.ok) throw new Error('Failed to save template');

      toast.success('Chain saved as template');
      fetchTemplates();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const loadTemplate = (template) => {
    setChain({
      name: `${template.name} (Copy)`,
      steps: template.steps.map((step) => ({
        ...step,
        id: `step-${Date.now()}-${Math.random()}`,
      })),
    });
    setShowTemplates(false);
    toast.success('Template loaded');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Prompt Chaining</h1>
          <p className="text-slate-500 mt-1">
            Build complex AI workflows with sequential prompts
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="btn-secondary flex items-center gap-2"
          >
            <BookmarkIcon className="w-4 h-4" />
            Templates
          </button>
        </div>
      </div>

      {/* Templates Sidebar */}
      {showTemplates && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Saved Templates
          </h2>
          {templates.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className="p-4 border border-slate-200 rounded-lg hover:border-indigo-300 cursor-pointer transition-colors"
                  onClick={() => loadTemplate(template)}
                >
                  <h3 className="font-medium text-slate-900">{template.name}</h3>
                  <p className="text-sm text-slate-500 mt-1">
                    {template.steps.length} steps
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No saved templates yet</p>
          )}
        </div>
      )}

      {/* Chain Builder */}
      <div className="card p-6">
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Chain Name
          </label>
          <input
            type="text"
            value={chain.name}
            onChange={(e) => setChain({ ...chain, name: e.target.value })}
            placeholder="e.g., Blog post generation workflow"
            className="input"
          />
        </div>

        {/* Steps */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Steps</h2>
            <button
              onClick={addStep}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <PlusIcon className="w-4 h-4" />
              Add Step
            </button>
          </div>

          {chain.steps.length > 0 ? (
            <DragDropContext onDragEnd={handleDragEnd}>
              <Droppable droppableId="steps">
                {(provided) => (
                  <div
                    {...provided.droppableProps}
                    ref={provided.innerRef}
                    className="space-y-4"
                  >
                    {chain.steps.map((step, index) => (
                      <Draggable key={step.id} draggableId={step.id} index={index}>
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            className={`border-2 rounded-lg transition-all ${
                              snapshot.isDragging
                                ? 'border-indigo-400 shadow-lg'
                                : 'border-slate-200'
                            }`}
                          >
                            {/* Step Header */}
                            <div className="flex items-center justify-between p-4 bg-slate-50">
                              <div className="flex items-center gap-3">
                                <div
                                  {...provided.dragHandleProps}
                                  className="cursor-grab active:cursor-grabbing"
                                >
                                  <Bars3Icon className="w-5 h-5 text-slate-400" />
                                </div>
                                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-semibold text-sm">
                                  {index + 1}
                                </div>
                                <input
                                  type="text"
                                  value={step.name}
                                  onChange={(e) =>
                                    updateStep(step.id, 'name', e.target.value)
                                  }
                                  className="font-medium text-slate-900 bg-transparent border-none focus:outline-none focus:ring-0"
                                  placeholder="Step name"
                                />
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => duplicateStep(index)}
                                  className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
                                  title="Duplicate"
                                >
                                  <DocumentDuplicateIcon className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => toggleStepExpanded(step.id)}
                                  className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
                                >
                                  {expandedSteps.has(step.id) ? (
                                    <ChevronUpIcon className="w-4 h-4" />
                                  ) : (
                                    <ChevronDownIcon className="w-4 h-4" />
                                  )}
                                </button>
                                <button
                                  onClick={() => removeStep(step.id)}
                                  className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded"
                                  title="Delete"
                                >
                                  <TrashIcon className="w-4 h-4" />
                                </button>
                              </div>
                            </div>

                            {/* Step Content */}
                            {expandedSteps.has(step.id) && (
                              <div className="p-4 space-y-4">
                                <div>
                                  <label className="block text-sm font-medium text-slate-700 mb-1">
                                    Model
                                  </label>
                                  <select
                                    value={step.llm_id}
                                    onChange={(e) =>
                                      updateStep(step.id, 'llm_id', e.target.value)
                                    }
                                    className="input"
                                  >
                                    {models.map((model) => (
                                      <option key={model.id} value={model.id}>
                                        {model.name}
                                      </option>
                                    ))}
                                  </select>
                                </div>

                                <div>
                                  <label className="block text-sm font-medium text-slate-700 mb-1">
                                    Prompt
                                  </label>
                                  <textarea
                                    value={step.prompt}
                                    onChange={(e) =>
                                      updateStep(step.id, 'prompt', e.target.value)
                                    }
                                    placeholder="Enter your prompt here. Use {{variable}} for variables and {{previous}} for previous step output."
                                    rows={4}
                                    className="input"
                                  />
                                </div>

                                {index > 0 && (
                                  <div className="flex items-center gap-2">
                                    <input
                                      type="checkbox"
                                      id={`use-previous-${step.id}`}
                                      checked={step.use_previous_output}
                                      onChange={(e) =>
                                        updateStep(
                                          step.id,
                                          'use_previous_output',
                                          e.target.checked
                                        )
                                      }
                                      className="w-4 h-4 text-indigo-600 rounded"
                                    />
                                    <label
                                      htmlFor={`use-previous-${step.id}`}
                                      className="text-sm text-slate-700"
                                    >
                                      Use previous step output in this prompt
                                    </label>
                                  </div>
                                )}

                                {/* Variables */}
                                <div>
                                  <div className="flex items-center justify-between mb-2">
                                    <label className="block text-sm font-medium text-slate-700">
                                      Variables
                                    </label>
                                    <button
                                      onClick={() => addVariable(step.id)}
                                      className="text-sm text-indigo-600 hover:text-indigo-700"
                                    >
                                      + Add Variable
                                    </button>
                                  </div>
                                  {step.variables && step.variables.length > 0 && (
                                    <div className="flex flex-wrap gap-2">
                                      {step.variables.map((variable, vIndex) => (
                                        <div
                                          key={vIndex}
                                          className="flex items-center gap-1 px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-sm"
                                        >
                                          <span>{'{{' + variable + '}}'}</span>
                                          <button
                                            onClick={() =>
                                              removeVariable(step.id, vIndex)
                                            }
                                            className="ml-1 text-indigo-400 hover:text-indigo-600"
                                          >
                                            ×
                                          </button>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* Arrow to next step */}
                            {index < chain.steps.length - 1 && (
                              <div className="flex justify-center py-2">
                                <ArrowRightIcon className="w-5 h-5 text-slate-400 rotate-90" />
                              </div>
                            )}
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </DragDropContext>
          ) : (
            <div className="card p-8 text-center">
              <SparklesIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="font-medium text-slate-900">No steps yet</h3>
              <p className="text-sm text-slate-500 mt-1">
                Click "Add Step" to start building your chain
              </p>
            </div>
          )}
        </div>

        {/* Actions */}
        {chain.steps.length > 0 && (
          <div className="flex gap-3 pt-4 border-t border-slate-200">
            <button
              onClick={executeChain}
              disabled={isExecuting}
              className="btn-primary flex items-center gap-2"
            >
              <PlayIcon className="w-4 h-4" />
              {isExecuting ? 'Executing...' : 'Execute Chain'}
            </button>
            <button
              onClick={saveAsTemplate}
              className="btn-secondary flex items-center gap-2"
            >
              <BookmarkIcon className="w-4 h-4" />
              Save as Template
            </button>
          </div>
        )}
      </div>

      {/* Execution Results */}
      {executionResults.length > 0 && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Execution Results
          </h2>
          <div className="space-y-4">
            {executionResults.map((result, index) => (
              <div
                key={index}
                className="border border-slate-200 rounded-lg overflow-hidden"
              >
                <button
                  onClick={() => toggleResultExpanded(index)}
                  className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-semibold text-sm">
                      {index + 1}
                    </div>
                    <span className="font-medium text-slate-900">
                      {result.step_name || `Step ${index + 1}`}
                    </span>
                  </div>
                  {expandedResults.has(index) ? (
                    <ChevronUpIcon className="w-5 h-5 text-slate-400" />
                  ) : (
                    <ChevronDownIcon className="w-5 h-5 text-slate-400" />
                  )}
                </button>

                {expandedResults.has(index) && (
                  <div className="p-4 bg-white">
                    <div className="mb-3">
                      <p className="text-xs font-medium text-slate-500 mb-1">
                        Prompt
                      </p>
                      <p className="text-sm text-slate-700 bg-slate-50 p-3 rounded">
                        {result.prompt}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-slate-500 mb-1">
                        Output
                      </p>
                      <div className="text-sm text-slate-900 bg-slate-50 p-3 rounded whitespace-pre-wrap">
                        {result.output}
                      </div>
                    </div>
                    {result.tokens && (
                      <p className="text-xs text-slate-500 mt-2">
                        Tokens used: {result.tokens}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PromptChaining;
