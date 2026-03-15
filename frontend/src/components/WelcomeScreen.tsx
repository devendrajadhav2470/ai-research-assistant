import React from 'react';
import {
  Compass,
  Zap,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  MessageCircle,
  RefreshCw,
  FileSearch,
  ShieldAlert,
  Database,
} from 'lucide-react';

interface WelcomeScreenProps {
  collectionName: string | null;
  onPromptClick: (prompt: string) => void;
}

const featureRows = [
  {
    category: {
      icon: Compass,
      title: 'Explore',
      description: 'Learn how to use this RAG assistant for your research needs',
      color: 'bg-gray-900 text-white',
    },
    cards: [
      {
        icon: BookOpen,
        title: '"Explain"',
        description: 'Key findings from the documents',
        prompt: 'Explain the key findings discussed in these documents.',
        iconBg: 'bg-orange-100',
        iconColor: 'text-orange-500',
      },
      {
        icon: FileSearch,
        title: '"How to"',
        description: 'Summarize methodologies and approaches',
        prompt: 'How does the methodology work in these papers?',
        iconBg: 'bg-blue-100',
        iconColor: 'text-blue-500',
      },
    ],
  },
  {
    category: {
      icon: Zap,
      title: 'Capabilities',
      description: 'What this AI assistant can do for your research',
      color: 'bg-gray-900 text-white',
    },
    cards: [
      {
        icon: MessageCircle,
        title: '"Remember"',
        description: 'Maintains context across your conversation',
        prompt: 'Summarize the main topics we discussed so far.',
        iconBg: 'bg-purple-100',
        iconColor: 'text-purple-500',
      },
      {
        icon: RefreshCw,
        title: '"Allows"',
        description: 'Follow-up questions and deeper analysis',
        prompt: 'Can you elaborate on the limitations discussed?',
        iconBg: 'bg-green-100',
        iconColor: 'text-green-500',
      },
    ],
  },
  {
    category: {
      icon: AlertTriangle,
      title: 'Limitations',
      description: 'Important things to keep in mind while using',
      color: 'bg-gray-900 text-white',
    },
    cards: [
      {
        icon: ShieldAlert,
        title: '"May"',
        description: 'Occasionally generate imprecise summaries',
        prompt: 'What are the potential inaccuracies to watch for?',
        iconBg: 'bg-red-100',
        iconColor: 'text-red-500',
      },
      {
        icon: Database,
        title: '"Limited"',
        description: 'Knowledge limited to uploaded documents',
        prompt: 'Compare the results across all uploaded documents.',
        iconBg: 'bg-amber-100',
        iconColor: 'text-amber-500',
      },
    ],
  },
];

export default function WelcomeScreen({ collectionName, onPromptClick }: WelcomeScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-8 animate-fade-in">
      {/* Logo */}
      <div className="mb-2 px-5 py-2 border border-gray-200 rounded-full bg-white shadow-card">
        <span className="text-sm font-bold tracking-tight text-text-primary">CHAT A.I+</span>
      </div>

      {/* Greeting */}
      <h1 className="mt-4 text-2xl sm:text-3xl font-bold text-text-primary text-center">
        Good day! How may I assist you today?
      </h1>

      {collectionName && (
        <p className="mt-2 text-sm text-text-secondary text-center">
          Ask questions about documents in <span className="font-medium text-primary-600">"{collectionName}"</span>
        </p>
      )}

      {!collectionName && (
        <p className="mt-2 text-sm text-text-secondary text-center">
          Select or create a collection to get started.
        </p>
      )}

      {/* Feature Cards Grid */}
      <div className="mt-8 w-full max-w-4xl grid grid-cols-1 md:grid-cols-3 gap-3">
        {featureRows.map((row) => (
          <React.Fragment key={row.category.title}>
            {/* Category card */}
            <div
              className={`${row.category.color} rounded-card p-4 flex flex-col justify-between min-h-[120px]`}
            >
              <div className="flex items-center gap-2 mb-2">
                <row.category.icon size={18} />
                <span className="font-semibold text-sm">{row.category.title}</span>
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                {row.category.description}
              </p>
              <div className="flex gap-1 mt-2">
                <div className="w-1 h-6 bg-white/30 rounded-full" />
                <div className="w-1 h-4 bg-white/20 rounded-full" />
                <div className="w-1 h-5 bg-white/25 rounded-full" />
              </div>
            </div>

            {/* Prompt cards */}
            {row.cards.map((card) => (
              <button
                key={card.title}
                onClick={() => onPromptClick(card.prompt)}
                disabled={!collectionName}
                className="group bg-white rounded-card p-4 border border-gray-100 shadow-card hover:shadow-card-hover hover:border-primary-200 transition-all text-left flex flex-col justify-between min-h-[120px] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-card"
              >
                <div>
                  <div className={`inline-flex p-2 rounded-lg ${card.iconBg} mb-2`}>
                    <card.icon size={16} className={card.iconColor} />
                  </div>
                  <h3 className="font-semibold text-sm text-text-primary">{card.title}</h3>
                  <p className="text-xs text-text-secondary mt-0.5 leading-relaxed">
                    {card.description}
                  </p>
                </div>
                <div className="flex justify-end mt-2">
                  <ArrowRight
                    size={16}
                    className="text-gray-300 group-hover:text-primary-500 transition-colors"
                  />
                </div>
              </button>
            ))}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
