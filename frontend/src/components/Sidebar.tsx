import React, { useState, useEffect, useMemo, useRef } from 'react';
import clsx from 'clsx';
import {
  Plus,
  Search,
  MessageSquare,
  Trash2,
  Pencil,
  FileText,
  Settings,
  ChevronDown,
  X,
  FolderOpen,
  Sparkles,
} from 'lucide-react';
import type { Collection, Conversation, AvailableModels, ModelOption } from '../types';
import { getAvailableModels } from '../services/api';

interface SidebarProps {
  collections: Collection[];
  activeCollection: Collection | null;
  conversations: Conversation[];
  activeConversationId: number | null;
  selectedProvider: string;
  selectedModel: string;
  onSelectCollection: (collection: Collection) => void;
  onCreateCollection: (name: string, description: string) => void;
  onDeleteCollection: (id: number) => void;
  onSelectConversation: (id: number) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: number) => void;
  onEditConversation: (id: number, name: string) => void;
  onOpenDocuments: () => void;
  onModelChange: (provider: string, model: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

function groupConversationsByTime(conversations: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Previous 7 Days', items: [] },
    { label: 'Previous 30 Days', items: [] },
    { label: 'Older', items: [] },
  ];

  for (const conv of conversations) {
    const date = new Date(conv.updated_at || conv.created_at);
    if (date >= today) groups[0].items.push(conv);
    else if (date >= sevenDaysAgo) groups[1].items.push(conv);
    else if (date >= thirtyDaysAgo) groups[2].items.push(conv);
    else groups[3].items.push(conv);
  }

  return groups.filter((g) => g.items.length > 0);
}

export default function Sidebar({
  collections,
  activeCollection,
  conversations,
  activeConversationId,
  selectedProvider,
  selectedModel,
  onSelectCollection,
  onCreateCollection,
  onDeleteCollection,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onEditConversation,
  onOpenDocuments,
  onModelChange,
  isOpen,
  onClose,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showNewCollection, setShowNewCollection] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [showCollectionDropdown, setShowCollectionDropdown] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [models, setModels] = useState<AvailableModels>({});

  const collectionDropdownRef = useRef<HTMLDivElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getAvailableModels().then(setModels).catch(() => setModels({}));
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (collectionDropdownRef.current && !collectionDropdownRef.current.contains(e.target as Node)) {
        setShowCollectionDropdown(false);
      }
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setShowSettings(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const q = searchQuery.toLowerCase();
    return conversations.filter((c) => c.title.toLowerCase().includes(q));
  }, [conversations, searchQuery]);

  const grouped = useMemo(() => groupConversationsByTime(filteredConversations), [filteredConversations]);

  const allModels = useMemo(
    () =>
      Object.entries(models).flatMap(([provider, list]) =>
        list.map((m: ModelOption) => ({ ...m, provider }))
      ),
    [models]
  );

  const currentModel = allModels.find(
    (m) => m.provider === selectedProvider && m.id === selectedModel
  );

  const handleCreateCollection = () => {
    const name = newCollectionName.trim();
    if (name) {
      onCreateCollection(name, '');
      setNewCollectionName('');
      setShowNewCollection(false);
    }
  };

  const commitEdit = (convId: number) => {
    const trimmed = editingTitle.trim();
    if (trimmed) {
      onEditConversation(convId, trimmed);
    }
    setEditingId(null);
    setEditingTitle('');
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 sidebar-overlay z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          'fixed lg:static inset-y-0 left-0 z-50 w-[280px] bg-white border-r border-border flex flex-col h-full shadow-sidebar transition-transform duration-250 ease-out',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Brand + Close */}
        <div className="px-5 pt-5 pb-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-primary-500 flex items-center justify-center">
              <Sparkles size={18} className="text-white" />
            </div>
            <span className="text-[15px] font-bold tracking-tight text-text-primary">
              CHAT A.I+
            </span>
          </div>
          <button onClick={onClose} className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100">
            <X size={18} className="text-text-secondary" />
          </button>
        </div>

        {/* New Chat Button + Search */}
        <div className="px-4 pb-3 space-y-2.5">
          <button
            onClick={() => {
              onNewConversation();
              onClose();
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-500 hover:bg-primary-600 text-white rounded-xl text-sm font-semibold transition-colors"
          >
            <Plus size={16} />
            New chat
          </button>

          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-xl placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-400 transition-all"
            />
          </div>
        </div>

        {/* Collection Selector */}
        <div className="px-4 pb-2" ref={collectionDropdownRef}>
          <div className="relative">
            <button
              onClick={() => setShowCollectionDropdown(!showCollectionDropdown)}
              className="w-full flex items-center justify-between px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-xl hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FolderOpen size={14} className="text-primary-500 flex-shrink-0" />
                <span className="truncate text-text-primary font-medium">
                  {activeCollection?.name || 'Select Collection'}
                </span>
              </div>
              <ChevronDown
                size={14}
                className={clsx(
                  'text-gray-400 flex-shrink-0 transition-transform',
                  showCollectionDropdown && 'rotate-180'
                )}
              />
            </button>

            {showCollectionDropdown && (
              <div className="absolute left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-card-hover z-20 py-1 max-h-60 overflow-y-auto animate-slide-in-up">
                {collections.map((col) => (
                  <div
                    key={col.id}
                    className="group flex items-center justify-between"
                  >
                    <button
                      onClick={() => {
                        onSelectCollection(col);
                        setShowCollectionDropdown(false);
                      }}
                      className={clsx(
                        'flex-1 text-left px-3 py-2 text-sm transition-colors',
                        activeCollection?.id === col.id
                          ? 'text-primary-600 bg-primary-50 font-medium'
                          : 'text-text-primary hover:bg-gray-50'
                      )}
                    >
                      <span className="truncate block">{col.name}</span>
                      <span className="text-xs text-text-secondary">
                        {col.document_count} doc{col.document_count !== 1 ? 's' : ''}
                      </span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteCollection(col.id);
                      }}
                      className="p-1.5 mr-1 opacity-0 group-hover:opacity-100 hover:bg-red-50 rounded-lg transition-all"
                    >
                      <Trash2 size={12} className="text-red-400" />
                    </button>
                  </div>
                ))}

                {collections.length === 0 && (
                  <p className="px-3 py-2 text-xs text-text-secondary">No collections yet.</p>
                )}

                <div className="border-t border-gray-100 mt-1 pt-1">
                  {showNewCollection ? (
                    <div className="px-3 py-2 space-y-2">
                      <input
                        type="text"
                        value={newCollectionName}
                        onChange={(e) => setNewCollectionName(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleCreateCollection()}
                        placeholder="Collection name"
                        className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-200"
                        autoFocus
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={handleCreateCollection}
                          className="flex-1 px-3 py-1.5 bg-primary-500 text-white text-xs font-medium rounded-lg hover:bg-primary-600 transition-colors"
                        >
                          Create
                        </button>
                        <button
                          onClick={() => {
                            setShowNewCollection(false);
                            setNewCollectionName('');
                          }}
                          className="px-3 py-1.5 bg-gray-100 text-text-secondary text-xs rounded-lg hover:bg-gray-200 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowNewCollection(true)}
                      className="w-full text-left px-3 py-2 text-sm text-primary-500 hover:bg-primary-50 font-medium transition-colors"
                    >
                      + New Collection
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-3 pb-2">
          {activeCollection && (
            <div className="mb-1 px-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                Your conversations
              </span>
            </div>
          )}

          {grouped.map((group) => (
            <div key={group.label} className="mb-3">
              <p className="px-2 py-1 text-[11px] font-medium text-text-secondary uppercase tracking-wide">
                {group.label}
              </p>
              <div className="space-y-0.5">
                {group.items.map((conv) => (
                  <div
                    key={conv.id}
                    onClick={() => {
                      if (editingId !== conv.id) {
                        onSelectConversation(conv.id);
                        onClose();
                      }
                    }}
                    className={clsx(
                      'group flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer text-sm transition-all',
                      activeConversationId === conv.id
                        ? 'bg-primary-50 text-primary-700 font-medium'
                        : 'text-text-primary hover:bg-gray-50'
                    )}
                  >
                    <MessageSquare
                      size={14}
                      className={clsx(
                        'flex-shrink-0',
                        activeConversationId === conv.id ? 'text-primary-500' : 'text-gray-400'
                      )}
                    />

                    {editingId === conv.id ? (
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        autoFocus
                        onClick={(e) => e.stopPropagation()}
                        onBlur={() => commitEdit(conv.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            commitEdit(conv.id);
                          } else if (e.key === 'Escape') {
                            setEditingId(null);
                            setEditingTitle('');
                          }
                        }}
                        className="flex-1 min-w-0 px-2 py-0.5 text-sm rounded-lg border border-primary-300 bg-white focus:outline-none focus:ring-1 focus:ring-primary-400"
                      />
                    ) : (
                      <span className="truncate flex-1">{conv.title}</span>
                    )}

                    {editingId !== conv.id && (
                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingTitle(conv.title);
                            setEditingId(conv.id);
                          }}
                          className="p-1 rounded-md hover:bg-gray-200 transition-colors"
                        >
                          <Pencil size={12} className="text-gray-500" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteConversation(conv.id);
                          }}
                          className="p-1 rounded-md hover:bg-red-50 transition-colors"
                        >
                          <Trash2 size={12} className="text-red-400" />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          {activeCollection && conversations.length === 0 && (
            <p className="px-3 py-4 text-xs text-text-secondary text-center">
              No conversations yet. Start a new chat!
            </p>
          )}

          {!activeCollection && (
            <p className="px-3 py-4 text-xs text-text-secondary text-center">
              Select a collection to view conversations.
            </p>
          )}
        </div>

        {/* Bottom actions */}
        <div className="border-t border-border px-4 py-3 space-y-2">
          {activeCollection && (
            <button
              onClick={onOpenDocuments}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-text-primary hover:bg-gray-50 rounded-xl transition-colors"
            >
              <FileText size={16} className="text-text-secondary" />
              Manage Documents
            </button>
          )}

          {/* Settings / Model selector */}
          <div className="relative" ref={settingsRef}>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-text-primary hover:bg-gray-50 rounded-xl transition-colors"
            >
              <Settings size={16} className="text-text-secondary" />
              <span className="flex-1 text-left">Settings</span>
              {currentModel && (
                <span className="text-[11px] text-text-secondary bg-gray-100 px-2 py-0.5 rounded-full truncate max-w-[120px]">
                  {currentModel.name}
                </span>
              )}
            </button>

            {showSettings && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-xl shadow-card-hover z-30 py-2 max-h-80 overflow-y-auto animate-slide-in-up">
                <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Model
                </p>
                {Object.entries(models).map(([provider, modelList]) => (
                  <div key={provider}>
                    <p className="px-3 pt-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                      {provider}
                    </p>
                    {modelList.map((m: ModelOption) => (
                      <button
                        key={`${provider}-${m.id}`}
                        onClick={() => {
                          onModelChange(provider, m.id);
                          setShowSettings(false);
                        }}
                        className={clsx(
                          'w-full text-left px-4 py-1.5 text-sm transition-colors',
                          selectedProvider === provider && selectedModel === m.id
                            ? 'text-primary-600 bg-primary-50 font-medium'
                            : 'text-text-primary hover:bg-gray-50'
                        )}
                      >
                        {m.name}
                      </button>
                    ))}
                  </div>
                ))}
                {allModels.length === 0 && (
                  <p className="px-4 py-2 text-sm text-text-secondary">
                    No API keys configured.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
