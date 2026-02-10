import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';
import type { Message, Citation, Evaluation } from '../types';
import CitationCard from './CitationCard';
import EvaluationBadge from './EvaluationBadge';

interface MessageBubbleProps {
  message: Message;
  onEvaluate: (messageId: number) => void;
  isEvaluating?: boolean;
}

export default function MessageBubble({ message, onEvaluate, isEvaluating }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-indigo-600' : 'bg-gray-700'
        }`}
      >
        {isUser ? (
          <User size={16} className="text-white" />
        ) : (
          <Bot size={16} className="text-white" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block text-left rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-indigo-600 text-white rounded-tr-md'
              : 'bg-white border border-gray-200 text-gray-800 rounded-tl-md shadow-sm'
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none text-sm">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-2 space-y-1.5 max-w-[80%]">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Sources
            </p>
            {message.citations.map((citation, idx) => (
              <CitationCard key={idx} citation={citation} index={idx} />
            ))}
          </div>
        )}

        {/* Evaluation */}
        {!isUser && (
          <EvaluationBadge
            evaluation={message.evaluation}
            messageId={message.id}
            onEvaluate={onEvaluate}
            isEvaluating={isEvaluating}
          />
        )}

        {/* Metadata */}
        {!isUser && message.model_name && (
          <p className="mt-1 text-xs text-gray-400">
            {message.provider}/{message.model_name}
          </p>
        )}
      </div>
    </div>
  );
}

