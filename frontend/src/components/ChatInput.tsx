import React, { useState, useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';

interface ChatInputProps {
  collectionName: string | null;
  isStreaming: boolean;
  onSendMessage: (message: string) => void;
  onStopStreaming: () => void;
  initialValue?: string;
}

export default function ChatInput({
  collectionName,
  isStreaming,
  onSendMessage,
  onStopStreaming,
  initialValue,
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialValue !== undefined) {
      setInput(initialValue);
      textareaRef.current?.focus();
    }
  }, [initialValue]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (trimmed && !isStreaming) {
      onSendMessage(trimmed);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-gray-100 bg-white/80 backdrop-blur-sm px-4 sm:px-6 py-3">
      <div className="max-w-3xl mx-auto">
        <div className="relative flex items-end gap-2 bg-white border border-gray-200 rounded-2xl px-4 py-2 shadow-card focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              collectionName
                ? "What's in your mind?..."
                : 'Select a collection first...'
            }
            disabled={!collectionName || isStreaming}
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-text-primary placeholder:text-gray-400 focus:outline-none disabled:cursor-not-allowed py-1.5 max-h-40"
          />

          {isStreaming ? (
            <button
              onClick={onStopStreaming}
              className="flex-shrink-0 w-9 h-9 flex items-center justify-center bg-red-500 hover:bg-red-600 text-white rounded-xl transition-colors"
              title="Stop generating"
            >
              <Square size={14} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || !collectionName}
              className="flex-shrink-0 w-9 h-9 flex items-center justify-center bg-primary-500 hover:bg-primary-600 text-white rounded-xl transition-colors disabled:bg-gray-200 disabled:cursor-not-allowed"
              title="Send message"
            >
              <Send size={14} />
            </button>
          )}
        </div>

        <p className="text-center text-[11px] text-gray-400 mt-2">
          Answers are generated from your uploaded documents using RAG.
        </p>
      </div>
    </div>
  );
}
