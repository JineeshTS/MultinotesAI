import { useState, useEffect, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  ChatBubbleLeftRightIcon,
  FolderIcon,
  DocumentTextIcon,
  CreditCardIcon,
  Cog6ToothIcon,
  SparklesIcon,
  RectangleStackIcon,
} from '@heroicons/react/24/outline';
import { setCommandPaletteOpen } from '../../store/slices/uiSlice';

const CommandPalette = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const commands = [
    { id: 'new-chat', name: 'New Chat', icon: ChatBubbleLeftRightIcon, action: () => navigate('/ai/chat'), category: 'Actions' },
    { id: 'templates', name: 'Browse Templates', icon: RectangleStackIcon, action: () => navigate('/ai/templates'), category: 'Navigation' },
    { id: 'compare', name: 'Compare Models', icon: SparklesIcon, action: () => navigate('/ai/compare'), category: 'Actions' },
    { id: 'documents', name: 'My Documents', icon: FolderIcon, action: () => navigate('/documents'), category: 'Navigation' },
    { id: 'tokens', name: 'View Tokens', icon: CreditCardIcon, action: () => navigate('/tokens'), category: 'Navigation' },
    { id: 'settings', name: 'Settings', icon: Cog6ToothIcon, action: () => navigate('/settings'), category: 'Navigation' },
  ];

  const filteredCommands = commands.filter((command) =>
    command.name.toLowerCase().includes(query.toLowerCase())
  );

  const groupedCommands = filteredCommands.reduce((groups, command) => {
    const category = command.category;
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(command);
    return groups;
  }, {});

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        dispatch(setCommandPaletteOpen(false));
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredCommands.length - 1 ? prev + 1 : prev
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
          dispatch(setCommandPaletteOpen(false));
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [dispatch, filteredCommands, selectedIndex]);

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleCommandClick = (command) => {
    command.action();
    dispatch(setCommandPaletteOpen(false));
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm"
        onClick={() => dispatch(setCommandPaletteOpen(false))}
      />

      {/* Dialog */}
      <div className="relative min-h-screen flex items-start justify-center pt-[15vh] px-4">
        <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 border-b border-slate-200">
            <MagnifyingGlassIcon className="w-5 h-5 text-slate-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or search..."
              className="flex-1 py-4 text-sm text-slate-900 placeholder-slate-400 bg-transparent border-0 focus:outline-none focus:ring-0"
            />
            <kbd className="px-2 py-1 text-xs font-medium text-slate-400 bg-slate-100 rounded">
              ESC
            </kbd>
          </div>

          {/* Commands List */}
          <div className="max-h-80 overflow-y-auto p-2">
            {Object.entries(groupedCommands).map(([category, commands]) => (
              <div key={category}>
                <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {category}
                </div>
                {commands.map((command, index) => {
                  const globalIndex = filteredCommands.indexOf(command);
                  return (
                    <button
                      key={command.id}
                      onClick={() => handleCommandClick(command)}
                      className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-left transition-colors ${
                        globalIndex === selectedIndex
                          ? 'bg-indigo-50 text-indigo-700'
                          : 'text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <command.icon className="w-5 h-5 flex-shrink-0" />
                      <span className="text-sm font-medium">{command.name}</span>
                    </button>
                  );
                })}
              </div>
            ))}

            {filteredCommands.length === 0 && (
              <div className="px-3 py-8 text-center text-slate-500">
                <p className="text-sm">No commands found</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50 text-xs text-slate-500">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">↑</kbd>
                <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">↓</kbd>
                <span>to navigate</span>
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">↵</kbd>
                <span>to select</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
