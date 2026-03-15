import React, { useState } from 'react';
import clsx from 'clsx';
import { FileText, ChevronDown } from 'lucide-react';
import type { Citation } from '../types';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export default function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-100 rounded-xl overflow-hidden bg-white shadow-card transition-shadow hover:shadow-card-hover">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-gray-50/50 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex-shrink-0 w-6 h-6 rounded-lg bg-primary-50 flex items-center justify-center">
            <FileText size={12} className="text-primary-500" />
          </div>
          <span className="text-xs font-medium text-text-primary truncate">
            [{index + 1}] {citation.source}
          </span>
          <span className="text-[11px] text-text-secondary flex-shrink-0">
            p.{citation.page_number}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {citation.relevance_score > 0 && (
            <span className="text-[10px] px-2 py-0.5 bg-primary-50 text-primary-600 rounded-full font-semibold">
              {(citation.relevance_score * 100).toFixed(0)}%
            </span>
          )}
          <ChevronDown
            size={14}
            className={clsx(
              'text-gray-400 transition-transform duration-200',
              expanded && 'rotate-180'
            )}
          />
        </div>
      </button>

      {expanded && (
        <div className="px-3 py-2.5 border-t border-gray-50 bg-gray-50/50 animate-fade-in">
          <p className="text-xs text-text-secondary leading-relaxed whitespace-pre-wrap">
            {citation.content_preview}
          </p>
        </div>
      )}
    </div>
  );
}
