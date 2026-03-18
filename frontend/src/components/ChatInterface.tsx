import React, { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { Loader2, Sparkles } from 'lucide-react';
import type { Message, Citation } from '../types';
import MessageBubble from './MessageBubble';
import CitationCard from './CitationCard';
import WelcomeScreen from './WelcomeScreen';
import ChatInput from './ChatInput';
import ReactMarkdown from 'react-markdown';

interface ChatInterfaceProps {
  messages: Message[];
  streamingContent: string;
  streamingCitations: Citation[];
  isStreaming: boolean;
  loading: boolean;
  loadingMessages: boolean;
  hasMoreMessages: boolean;
  error: string | null;
  collectionName: string | null;
  onSendMessage: (message: string) => void;
  onStopStreaming: () => void;
  onEvaluate: (messageId: number) => void;
  onLoadMoreMessages: () => void;
  evaluatingId: number | null;
}

export default function ChatInterface({
  messages,
  streamingContent,
  streamingCitations,
  isStreaming,
  loading,
  loadingMessages,
  hasMoreMessages,
  error,
  collectionName,
  onSendMessage,
  onStopStreaming,
  onEvaluate,
  onLoadMoreMessages,
  evaluatingId,
}: ChatInterfaceProps) {
  const [promptValue, setPromptValue] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const didPrependRef = useRef(false);

  const pendingPrependRef = useRef<{
    prevScrollHeight: number;
    prevScrollTop: number;
  } | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (didPrependRef.current) {
      didPrependRef.current = false;
      return;
    }
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Prevent scroll jump on prepend
  useLayoutEffect(() => {
    const container = containerRef.current;
    const pending = pendingPrependRef.current;
    if (!container || !pending) return;

    const newScrollHeight = container.scrollHeight;
    const heightDiff = newScrollHeight - pending.prevScrollHeight;
    container.scrollTop = pending.prevScrollTop + heightDiff;
    pendingPrependRef.current = null;
  }, [messages.length]);

  function onScroll() {
    if (loadingMessages || !hasMoreMessages) return;
    const el = containerRef.current;
    if (!el) return;
    if (el.scrollTop < 80) {
      pendingPrependRef.current = {
        prevScrollHeight: el.scrollHeight,
        prevScrollTop: el.scrollTop,
      };
      didPrependRef.current = true;
      void onLoadMoreMessages();
    }
  }

  const handlePromptClick = (prompt: string) => {
    setPromptValue(prompt);
  };

  const handleSendMessage = (message: string) => {
    setPromptValue(undefined);
    onSendMessage(message);
  };

  const showWelcome = messages.length === 0 && !isStreaming;

  return (
    <div className="flex-1 flex flex-col bg-page h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto" ref={containerRef} onScroll={onScroll}>
        {showWelcome ? (
          <WelcomeScreen collectionName={collectionName} onPromptClick={handlePromptClick} />
        ) : (
          <div className="px-4 sm:px-6 py-6">
            <div className="max-w-3xl mx-auto space-y-5">
              {loadingMessages && hasMoreMessages && (
                <div className="flex justify-center py-3">
                  <div className="flex items-center gap-2 text-xs text-text-secondary bg-white px-4 py-2 rounded-full shadow-card">
                    <Loader2 size={14} className="animate-spin" />
                    Loading older messages...
                  </div>
                </div>
              )}

              {!hasMoreMessages && messages.length > 0 && (
                <div className="flex justify-center py-2">
                  <span className="text-[11px] text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                    Beginning of conversation
                  </span>
                </div>
              )}

              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onEvaluate={onEvaluate}
                  isEvaluating={evaluatingId === msg.id}
                  onResend={onSendMessage}
                />
              ))}

              {/* Streaming Response */}
              {isStreaming && (
                <div className="flex gap-3 animate-fade-in">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-primary-500">
                    <Sparkles size={14} className="text-white" />
                  </div>
                  <div className="flex-1 max-w-[85%]">
                    {streamingCitations.length > 0 && !streamingContent && (
                      <div className="mb-3 space-y-1.5">
                        <p className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
                          Retrieved Sources
                        </p>
                        {streamingCitations.map((citation, idx) => (
                          <CitationCard key={idx} citation={citation} index={idx} />
                        ))}
                      </div>
                    )}
                    <div className="bg-white border border-gray-100 rounded-bubble rounded-tl-lg px-4 py-3 shadow-card">
                      {streamingContent ? (
                        <div className="prose prose-sm max-w-none text-sm text-text-primary">
                          <ReactMarkdown>{streamingContent}</ReactMarkdown>
                          <span className="inline-block w-1.5 h-4 bg-primary-500 rounded-sm typing-cursor ml-0.5 align-text-bottom" />
                        </div>
                      ) : (
                        <div className="flex items-center gap-2.5 text-sm text-text-secondary">
                          <Loader2 size={14} className="animate-spin text-primary-500" />
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
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-4 sm:mx-6 mb-2 px-4 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600 animate-fade-in">
          {error}
        </div>
      )}

      {/* Input Area */}
      <ChatInput
        collectionName={collectionName}
        isStreaming={isStreaming}
        onSendMessage={handleSendMessage}
        onStopStreaming={onStopStreaming}
        initialValue={promptValue}
      />
    </div>
  );
}
