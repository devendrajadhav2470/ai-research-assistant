import React, { useEffect, useState } from 'react';
import { BookOpen, ChevronDown } from 'lucide-react';
import type { AvailableModels, ModelOption } from '../types';
import { getAvailableModels } from '../services/api';

interface HeaderProps {
  selectedProvider: string;
  selectedModel: string;
  onModelChange: (provider: string, model: string) => void;
}

export default function Header({ selectedProvider, selectedModel, onModelChange }: HeaderProps) {
  const [models, setModels] = useState<AvailableModels>({});
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    getAvailableModels()
      .then(setModels)
      .catch(() => setModels({}));
  }, []);

  const allModels = Object.entries(models).flatMap(([provider, modelList]) =>
    modelList.map((m: ModelOption) => ({ ...m, provider }))
  );

  const currentModel = allModels.find(
    (m) => m.provider === selectedProvider && m.id === selectedModel
  );

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="bg-indigo-600 text-white p-2 rounded-lg">
          <BookOpen size={22} />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">AI Research Assistant</h1>
          <p className="text-xs text-gray-500">RAG-powered document Q&A</p>
        </div>
      </div>

      <div className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700 transition-colors"
        >
          <span className="text-xs text-gray-400 uppercase">{selectedProvider}</span>
          <span>{currentModel?.name || selectedModel}</span>
          <ChevronDown size={14} />
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50 py-1">
            {Object.entries(models).map(([provider, modelList]) => (
              <div key={provider}>
                <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase bg-gray-50">
                  {provider}
                </div>
                {modelList.map((m: ModelOption) => (
                  <button
                    key={`${provider}-${m.id}`}
                    onClick={() => {
                      onModelChange(provider, m.id);
                      setDropdownOpen(false);
                    }}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-indigo-50 transition-colors ${
                      selectedProvider === provider && selectedModel === m.id
                        ? 'text-indigo-600 bg-indigo-50 font-medium'
                        : 'text-gray-700'
                    }`}
                  >
                    {m.name}
                  </button>
                ))}
              </div>
            ))}
            {allModels.length === 0 && (
              <div className="px-4 py-3 text-sm text-gray-500">
                No API keys configured. Add keys to .env file.
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

