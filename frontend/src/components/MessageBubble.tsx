import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import clsx from 'clsx';
import {
  User,
  Sparkles,
  Copy,
  Check,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import type { Message } from '../types';
import CitationCard from './CitationCard';
import EvaluationBadge from './EvaluationBadge';

interface MessageBubbleProps {
  message: Message;
  onEvaluate: (messageId: number) => void;
  isEvaluating?: boolean;
  onResend?: (content: string) => void;
}

export default function MessageBubble({
  message,
  onEvaluate,
  isEvaluating,
  onResend,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState<'up' | 'down' | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard not available
    }
  };

  const handleRegenerate = () => {
    if (!onResend) return;
    onResend(message.content);
  };

  return (
    <div
      className={clsx(
        'flex gap-3 animate-fade-in',
        isUser ? 'flex-row-reverse' : ''
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser ? 'bg-primary-500' : 'bg-gray-800'
        )}
      >
        {isUser ? (
          <User size={14} className="text-white" />
        ) : (
          <Sparkles size={14} className="text-white" />
        )}
      </div>

      {/* Content */}
      <div className={clsx('flex-1 max-w-[85%]', isUser ? 'text-right' : '')}>
        {/* Role label */}
        {!isUser && (
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className="text-xs font-semibold text-text-primary">CHAT A.I +</span>
            <span className="inline-flex items-center gap-0.5 text-[10px] text-primary-600 bg-primary-50 px-1.5 py-0.5 rounded-full font-medium">
              <Sparkles size={8} />
              AI
            </span>
          </div>
        )}

        {/* Message bubble */}
        <div
          className={clsx(
            'inline-block text-left px-4 py-3 text-sm leading-relaxed',
            isUser
              ? 'bg-primary-500 text-white rounded-bubble rounded-tr-lg'
              : 'bg-white border border-gray-100 text-text-primary rounded-bubble rounded-tl-lg shadow-card'
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Actions bar for assistant messages */}
        {!isUser && (
          <div className="flex items-center gap-1 mt-2 flex-wrap">
            <ActionButton
              icon={copied ? Check : Copy}
              label={copied ? 'Copied' : 'Copy'}
              onClick={handleCopy}
              active={copied}
            />
            <ActionButton
              icon={RefreshCw}
              label="Regenerate"
              onClick={handleRegenerate}
            />
            <div className="w-px h-4 bg-gray-200 mx-1" />
            <ActionButton
              icon={ThumbsUp}
              label=""
              onClick={() => setLiked(liked === 'up' ? null : 'up')}
              active={liked === 'up'}
            />
            <ActionButton
              icon={ThumbsDown}
              label=""
              onClick={() => setLiked(liked === 'down' ? null : 'down')}
              active={liked === 'down'}
            />

            {/* Model info */}
            {message.model_name && (
              <>
                <div className="w-px h-4 bg-gray-200 mx-1" />
                <span className="text-[10px] text-gray-400 px-1">
                  {message.provider}/{message.model_name}
                </span>
              </>
            )}
          </div>
        )}

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-3 space-y-1.5">
            <p className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
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
      </div>
    </div>
  );
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  active,
}: {
  icon: React.ElementType;
  label: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium transition-colors',
        active
          ? 'text-primary-600 bg-primary-50'
          : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50'
      )}
    >
      <Icon size={12} />
      {label && <span>{label}</span>}
    </button>
  );
}
