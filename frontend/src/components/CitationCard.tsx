import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import type { Citation } from '../types';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export default function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={14} className="text-indigo-500 flex-shrink-0" />
          <span className="text-xs font-medium text-gray-700 truncate">
            [{index + 1}] {citation.source}
          </span>
          <span className="text-xs text-gray-400 flex-shrink-0">
            Page {citation.page_number}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {citation.relevance_score > 0 && (
            <span className="text-xs px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded font-medium">
              {(citation.relevance_score * 100).toFixed(0)}%
            </span>
          )}
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 py-2 border-t border-gray-100 bg-gray-50">
          <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap">
            {citation.content_preview}
          </p>
        </div>
      )}
    </div>
  );
}

