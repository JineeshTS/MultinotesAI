import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  PaperAirplaneIcon,
  StopIcon,
  SparklesIcon,
  ClipboardIcon,
  ArrowPathIcon,
  StarIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { toast } from 'react-toastify';
import {
  fetchModels,
  fetchConversation,
  sendMessage,
  setSelectedModel,
  addMessage,
  setIsGenerating,
  updateStreamingMessage,
  clearStreamingMessage,
  rateResponse,
} from '../../store/slices/chatSlice';
import chatService from '../../services/chatService';

const AIChat = () => {
  const { conversationId } = useParams();
  const dispatch = useDispatch();
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const abortControllerRef = useRef(null);

  const {
    messages,
    models,
    selectedModel,
    isGenerating,
    streamingMessage,
    isLoading,
  } = useSelector((state) => state.chat);

  const [prompt, setPrompt] = useState('');
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  useEffect(() => {
    dispatch(fetchModels());
    if (conversationId) {
      dispatch(fetchConversation(conversationId));
    }
  }, [dispatch, conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || isGenerating) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
    };

    dispatch(addMessage(userMessage));
    setPrompt('');
    dispatch(setIsGenerating(true));

    try {
      // Use streaming
      abortControllerRef.current = chatService.streamMessage(
        {
          prompt: prompt,
          llm_id: selectedModel?.id,
          conversation_id: conversationId,
        },
        // onChunk
        (chunk) => {
          dispatch(updateStreamingMessage(chunk.content || ''));
        },
        // onComplete
        () => {
          dispatch(setIsGenerating(false));
          dispatch(clearStreamingMessage());
        },
        // onError
        (error) => {
          toast.error('Failed to generate response');
          dispatch(setIsGenerating(false));
          dispatch(clearStreamingMessage());
        }
      );
    } catch (error) {
      toast.error('Failed to send message');
      dispatch(setIsGenerating(false));
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      dispatch(setIsGenerating(false));
      dispatch(clearStreamingMessage());
    }
  };

  const handleCopyMessage = (content) => {
    navigator.clipboard.writeText(content);
    toast.success('Copied to clipboard');
  };

  const handleRateMessage = (messageId, rating) => {
    dispatch(rateResponse({ responseId: messageId, rating }));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">AI Chat</h1>
          <p className="text-sm text-slate-500">
            {conversationId ? 'Continue your conversation' : 'Start a new conversation'}
          </p>
        </div>

        {/* Model Selector */}
        <div className="relative">
          <button
            onClick={() => setShowModelDropdown(!showModelDropdown)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <SparklesIcon className="w-4 h-4 text-indigo-500" />
            <span className="text-sm font-medium text-slate-700">
              {selectedModel?.name || 'Select Model'}
            </span>
            <ChevronDownIcon className="w-4 h-4 text-slate-400" />
          </button>

          {showModelDropdown && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-lg border border-slate-200 z-10">
              <div className="p-2">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      dispatch(setSelectedModel(model));
                      setShowModelDropdown(false);
                    }}
                    className={`flex items-center gap-3 w-full px-3 py-2 rounded-lg text-left transition-colors ${
                      selectedModel?.id === model.id
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg flex items-center justify-center">
                      <SparklesIcon className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{model.name}</p>
                      <p className="text-xs text-slate-500">
                        {model.tokens_per_request} tokens/req
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-6 space-y-6">
        {messages.length === 0 && !streamingMessage && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mb-4">
              <SparklesIcon className="w-8 h-8 text-indigo-600" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900">
              How can I help you today?
            </h2>
            <p className="text-slate-500 mt-2 max-w-md">
              Start a conversation by typing a message below. I can help with
              writing, coding, analysis, and more.
            </p>

            {/* Quick Prompts */}
            <div className="grid grid-cols-2 gap-3 mt-8 max-w-lg">
              {[
                'Write a blog post about AI',
                'Explain quantum computing',
                'Help me debug my code',
                'Create a marketing strategy',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setPrompt(suggestion)}
                  className="text-left px-4 py-3 bg-slate-100 rounded-lg text-sm text-slate-700 hover:bg-slate-200 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={
                message.role === 'user'
                  ? 'chat-message-user'
                  : 'chat-message-ai'
              }
            >
              {message.role === 'user' ? (
                <p className="whitespace-pre-wrap">{message.content}</p>
              ) : (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown
                    components={{
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={oneLight}
                            language={match[1]}
                            PreTag="div"
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>

                  {/* Message Actions */}
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100">
                    <button
                      onClick={() => handleCopyMessage(message.content)}
                      className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
                      title="Copy"
                    >
                      <ClipboardIcon className="w-4 h-4" />
                    </button>
                    <button
                      className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
                      title="Regenerate"
                    >
                      <ArrowPathIcon className="w-4 h-4" />
                    </button>
                    <div className="flex items-center gap-0.5 ml-auto">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() => handleRateMessage(message.id, star)}
                          className="p-0.5"
                        >
                          {message.rating >= star ? (
                            <StarIconSolid className="w-4 h-4 text-yellow-400" />
                          ) : (
                            <StarIcon className="w-4 h-4 text-slate-300 hover:text-yellow-400" />
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Streaming Message */}
        {streamingMessage && (
          <div className="flex justify-start">
            <div className="chat-message-ai">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{streamingMessage}</ReactMarkdown>
              </div>
              <div className="flex items-center gap-2 mt-2 text-indigo-600">
                <div className="w-2 h-2 bg-indigo-600 rounded-full animate-pulse" />
                <span className="text-xs">Generating...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 pt-4">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
              className="input resize-none py-3 pr-12 min-h-[48px] max-h-32"
              style={{ height: 'auto' }}
              disabled={isGenerating}
            />
            <div className="absolute right-2 bottom-2 text-xs text-slate-400">
              {prompt.length}/4000
            </div>
          </div>

          {isGenerating ? (
            <button
              type="button"
              onClick={handleStopGeneration}
              className="btn-danger flex items-center gap-2 py-3"
            >
              <StopIcon className="w-5 h-5" />
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!prompt.trim()}
              className="btn-primary flex items-center gap-2 py-3"
            >
              <PaperAirplaneIcon className="w-5 h-5" />
              Send
            </button>
          )}
        </form>

        <p className="text-xs text-slate-400 text-center mt-2">
          AI can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
};

export default AIChat;
