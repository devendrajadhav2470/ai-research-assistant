import React, { useState } from 'react';
import clsx from 'clsx';
import { Shield, ChevronDown, Loader2 } from 'lucide-react';
import type { Evaluation } from '../types';

interface EvaluationBadgeProps {
  evaluation: Evaluation | Record<string, never>;
  messageId: number;
  onEvaluate: (messageId: number) => void;
  isEvaluating?: boolean;
}

function getScoreColor(score: number) {
  if (score >= 4) return { text: 'text-emerald-600', bg: 'bg-emerald-50' };
  if (score >= 3) return { text: 'text-amber-600', bg: 'bg-amber-50' };
  return { text: 'text-red-500', bg: 'bg-red-50' };
}

function getOverallBg(score: number): string {
  if (score >= 4) return 'bg-emerald-500';
  if (score >= 3) return 'bg-amber-500';
  return 'bg-red-500';
}

export default function EvaluationBadge({
  evaluation,
  messageId,
  onEvaluate,
  isEvaluating,
}: EvaluationBadgeProps) {
  const [expanded, setExpanded] = useState(false);

  const hasEvaluation =
    evaluation &&
    'overall_score' in evaluation &&
    typeof evaluation.overall_score === 'number';

  if (!hasEvaluation) {
    return (
      <button
        onClick={() => onEvaluate(messageId)}
        disabled={isEvaluating}
        className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-text-secondary hover:text-primary-600 hover:bg-primary-50 rounded-xl border border-gray-200 transition-colors disabled:opacity-50"
      >
        {isEvaluating ? (
          <>
            <Loader2 size={12} className="animate-spin" />
            Evaluating...
          </>
        ) : (
          <>
            <Shield size={12} />
            Evaluate Quality
          </>
        )}
      </button>
    );
  }

  const eval_ = evaluation as Evaluation;
  const dimensions = [
    { key: 'faithfulness', label: 'Faithfulness' },
    { key: 'relevance', label: 'Relevance' },
    { key: 'completeness', label: 'Completeness' },
    { key: 'citation_accuracy', label: 'Citations' },
  ] as const;

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 flex-wrap"
      >
        <span
          className={clsx(
            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-white text-[11px] font-semibold',
            getOverallBg(eval_.overall_score)
          )}
        >
          <Shield size={10} />
          {eval_.overall_score.toFixed(1)}/5
        </span>
        {dimensions.map((dim) => {
          const d = eval_[dim.key];
          if (!d) return null;
          const colors = getScoreColor(d.score);
          return (
            <span
              key={dim.key}
              className={clsx(
                'px-2 py-0.5 rounded-full text-[10px] font-semibold',
                colors.text,
                colors.bg
              )}
            >
              {dim.label}: {d.score}
            </span>
          );
        })}
        <ChevronDown
          size={14}
          className={clsx(
            'text-gray-400 transition-transform',
            expanded && 'rotate-180'
          )}
        />
      </button>

      {expanded && (
        <div className="mt-2 p-3 bg-gray-50 rounded-xl border border-gray-100 space-y-2.5 animate-fade-in">
          {eval_.summary && (
            <p className="text-xs text-text-secondary italic leading-relaxed">{eval_.summary}</p>
          )}
          {dimensions.map((dim) => {
            const d = eval_[dim.key];
            if (!d) return null;
            const colors = getScoreColor(d.score);
            return (
              <div key={dim.key} className="flex items-start gap-2">
                <span
                  className={clsx(
                    'text-[10px] font-bold px-1.5 py-0.5 rounded-md flex-shrink-0',
                    colors.text,
                    colors.bg
                  )}
                >
                  {d.score}/5
                </span>
                <div>
                  <span className="text-xs font-semibold text-text-primary">{dim.label}: </span>
                  <span className="text-xs text-text-secondary">{d.explanation}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
