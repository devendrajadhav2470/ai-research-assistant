import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, Bot, Loader2, BookOpen } from 'lucide-react';
import type { Message, Citation } from '../types';
import MessageBubble from './MessageBubble';
import CitationCard from './CitationCard';
import ReactMarkdown from 'react-markdown';

interface ChatInterfaceProps {
  messages: Message[];
  streamingContent: string;
  streamingCitations: Citation[];
  isStreaming: boolean;
  loading: boolean;
  error: string | null;
  collectionName: string | null;
  onSendMessage: (message: string) => void;
  onStopStreaming: () => void;
  onEvaluate: (messageId: number) => void;
  evaluatingId: number | null;
}

export default function ChatInterface({
  messages,
  streamingContent,
  streamingCitations,
  isStreaming,
  loading,
  error,
  collectionName,
  onSendMessage,
  onStopStreaming,
  onEvaluate,
  evaluatingId,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (trimmed && !isStreaming) {
      onSendMessage(trimmed);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-gray-50 h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="bg-indigo-100 p-4 rounded-full mb-4">
              <BookOpen size={40} className="text-indigo-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">
              AI Research Assistant
            </h2>
            <p className="text-gray-500 max-w-md text-sm">
              {collectionName
                ? `Ask questions about documents in "${collectionName}". Upload PDFs first, then ask anything.`
                : 'Select or create a collection to get started.'}
            </p>
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg">
              {[
                'What are the key findings of this paper?',
                'Summarize the methodology used.',
                'What are the limitations discussed?',
                'Compare the results across the documents.',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                    textareaRef.current?.focus();
                  }}
                  className="text-left px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-6 max-w-4xl mx-auto">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onEvaluate={onEvaluate}
              isEvaluating={evaluatingId === msg.id}
            />
          ))}

          {/* Streaming Response */}
          {isStreaming && (
            <div className="flex gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gray-700">
                <Bot size={16} className="text-white" />
              </div>
              <div className="flex-1 max-w-[80%]">
                {streamingCitations.length > 0 && !streamingContent && (
                  <div className="mb-3 space-y-1.5">
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                      Retrieved Sources
                    </p>
                    {streamingCitations.map((citation, idx) => (
                      <CitationCard key={idx} citation={citation} index={idx} />
                    ))}
                  </div>
                )}
                <div className="inline-block bg-white border border-gray-200 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm">
                  {streamingContent ? (
                    <div className="prose prose-sm max-w-none text-sm">
                      <ReactMarkdown>{streamingContent}</ReactMarkdown>
                      <span className="inline-block w-2 h-4 bg-indigo-500 animate-pulse ml-0.5" />
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 size={16} className="animate-spin" />
                      Searching documents...
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <div ref={messagesEndRef} />
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-6 mb-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-white px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                collectionName
                  ? `Ask a question about "${collectionName}"...`
                  : 'Select a collection first...'
              }
              disabled={!collectionName || isStreaming}
              rows={1}
              className="w-full resize-none rounded-xl border border-gray-300 px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed max-h-32"
            />
          </div>
          {isStreaming ? (
            <button
              onClick={onStopStreaming}
              className="flex-shrink-0 p-3 bg-red-600 hover:bg-red-700 text-white rounded-xl transition-colors"
              title="Stop generating"
            >
              <Square size={18} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || !collectionName}
              className="flex-shrink-0 p-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              title="Send message"
            >
              <Send size={18} />
            </button>
          )}
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">
          Answers are generated from your uploaded documents using RAG.
        </p>
      </div>
    </div>
  );
}

