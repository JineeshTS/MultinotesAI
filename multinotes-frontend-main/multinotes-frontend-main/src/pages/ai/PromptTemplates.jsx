import { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  HeartIcon,
  SparklesIcon,
  ArrowTrendingUpIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';
import { HeartIcon as HeartIconSolid } from '@heroicons/react/24/solid';
import {
  fetchTemplates,
  fetchCategories,
  fetchTrending,
  toggleFavorite,
  setSelectedCategory,
  setSearchQuery,
} from '../../store/slices/templatesSlice';

const PromptTemplates = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const {
    templates,
    categories,
    trending,
    selectedCategory,
    searchQuery,
    isLoading,
  } = useSelector((state) => state.templates);

  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    dispatch(fetchTemplates());
    dispatch(fetchCategories());
    dispatch(fetchTrending());
  }, [dispatch]);

  useEffect(() => {
    dispatch(
      fetchTemplates({
        category: selectedCategory,
        search: searchQuery,
      })
    );
  }, [dispatch, selectedCategory, searchQuery]);

  const handleUseTemplate = (template) => {
    navigate('/ai/chat', { state: { template } });
  };

  const handleToggleFavorite = (e, templateId) => {
    e.stopPropagation();
    dispatch(toggleFavorite(templateId));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Prompt Templates</h1>
          <p className="text-slate-500 mt-1">
            Discover and use pre-built prompts for common tasks
          </p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <PlusIcon className="w-4 h-4" />
          Create Template
        </button>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => dispatch(setSearchQuery(e.target.value))}
            placeholder="Search templates..."
            className="input pl-10"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="btn-secondary flex items-center gap-2"
        >
          <FunnelIcon className="w-4 h-4" />
          Filters
        </button>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => dispatch(setSelectedCategory(null))}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
            !selectedCategory
              ? 'bg-indigo-600 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          All
        </button>
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => dispatch(setSelectedCategory(category.id))}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              selectedCategory === category.id
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {category.name}
          </button>
        ))}
      </div>

      {/* Trending Section */}
      {!searchQuery && !selectedCategory && trending.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <ArrowTrendingUpIcon className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-semibold text-slate-900">Trending</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {trending.slice(0, 3).map((template) => (
              <div
                key={template.id}
                onClick={() => handleUseTemplate(template)}
                className="card p-4 cursor-pointer hover:shadow-md transition-shadow group"
              >
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 bg-gradient-to-br from-orange-400 to-pink-500 rounded-xl flex items-center justify-center">
                    <SparklesIcon className="w-5 h-5 text-white" />
                  </div>
                  <button
                    onClick={(e) => handleToggleFavorite(e, template.id)}
                    className="p-1 hover:bg-slate-100 rounded"
                  >
                    {template.is_favorite ? (
                      <HeartIconSolid className="w-5 h-5 text-red-500" />
                    ) : (
                      <HeartIcon className="w-5 h-5 text-slate-400" />
                    )}
                  </button>
                </div>
                <h3 className="font-semibold text-slate-900 mt-3 group-hover:text-indigo-600 transition-colors">
                  {template.title}
                </h3>
                <p className="text-sm text-slate-500 mt-1 line-clamp-2">
                  {template.description}
                </p>
                <div className="flex items-center gap-2 mt-3">
                  <span className="badge-info">{template.category}</span>
                  <span className="text-xs text-slate-400">
                    {template.usage_count} uses
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Templates Grid */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          {selectedCategory ? 'Filtered Templates' : 'All Templates'}
        </h2>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="card p-4">
                <div className="skeleton h-10 w-10 rounded-xl mb-4" />
                <div className="skeleton h-5 w-3/4 mb-2" />
                <div className="skeleton h-4 w-full mb-1" />
                <div className="skeleton h-4 w-2/3" />
              </div>
            ))}
          </div>
        ) : templates.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((template) => (
              <div
                key={template.id}
                onClick={() => handleUseTemplate(template)}
                className="card p-4 cursor-pointer hover:shadow-md transition-shadow group"
              >
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center">
                    <SparklesIcon className="w-5 h-5 text-white" />
                  </div>
                  <button
                    onClick={(e) => handleToggleFavorite(e, template.id)}
                    className="p-1 hover:bg-slate-100 rounded"
                  >
                    {template.is_favorite ? (
                      <HeartIconSolid className="w-5 h-5 text-red-500" />
                    ) : (
                      <HeartIcon className="w-5 h-5 text-slate-400" />
                    )}
                  </button>
                </div>
                <h3 className="font-semibold text-slate-900 mt-3 group-hover:text-indigo-600 transition-colors">
                  {template.title}
                </h3>
                <p className="text-sm text-slate-500 mt-1 line-clamp-2">
                  {template.description}
                </p>

                {/* Variables Preview */}
                {template.variables && template.variables.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {template.variables.slice(0, 3).map((variable) => (
                      <span
                        key={variable}
                        className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded"
                      >
                        {'{' + variable + '}'}
                      </span>
                    ))}
                    {template.variables.length > 3 && (
                      <span className="text-xs text-slate-400">
                        +{template.variables.length - 3} more
                      </span>
                    )}
                  </div>
                )}

                <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100">
                  <span className="badge-info">{template.category}</span>
                  <span className="text-xs text-slate-400">
                    {template.usage_count} uses
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-8 text-center">
            <SparklesIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-medium text-slate-900">No templates found</h3>
            <p className="text-sm text-slate-500 mt-1">
              Try adjusting your search or filters
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PromptTemplates;
