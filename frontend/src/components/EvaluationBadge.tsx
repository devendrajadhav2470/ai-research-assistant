import React, { useState } from 'react';
import { Shield, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import type { Evaluation } from '../types';

interface EvaluationBadgeProps {
  evaluation: Evaluation | Record<string, never>;
  messageId: number;
  onEvaluate: (messageId: number) => void;
  isEvaluating?: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 4) return 'text-green-600 bg-green-50';
  if (score >= 3) return 'text-amber-600 bg-amber-50';
  return 'text-red-600 bg-red-50';
}

function getOverallColor(score: number): string {
  if (score >= 4) return 'bg-green-500';
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
        className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-full border border-gray-200 transition-colors disabled:opacity-50"
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
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs"
      >
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-white font-medium ${getOverallColor(
            eval_.overall_score
          )}`}
        >
          <Shield size={12} />
          Quality: {eval_.overall_score.toFixed(1)}/5
        </div>
        {dimensions.map((dim) => {
          const d = eval_[dim.key];
          if (!d) return null;
          return (
            <span
              key={dim.key}
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${getScoreColor(d.score)}`}
            >
              {dim.label}: {d.score}/5
            </span>
          );
        })}
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {expanded && (
        <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
          {eval_.summary && (
            <p className="text-xs text-gray-600 italic">{eval_.summary}</p>
          )}
          {dimensions.map((dim) => {
            const d = eval_[dim.key];
            if (!d) return null;
            return (
              <div key={dim.key} className="flex items-start gap-2">
                <span
                  className={`text-xs font-bold px-1.5 py-0.5 rounded ${getScoreColor(
                    d.score
                  )} flex-shrink-0`}
                >
                  {d.score}/5
                </span>
                <div>
                  <span className="text-xs font-medium text-gray-700">{dim.label}:</span>{' '}
                  <span className="text-xs text-gray-600">{d.explanation}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

