import React, { useState, useEffect } from 'react';
import {
  FolderPlus,
  Trash2,
  MessageSquarePlus,
  MessageSquare,
  ChevronRight,
  Library,
  FileText,
  Pencil
} from 'lucide-react';
import type { Collection, Conversation, Document } from '../types';
import * as api from '../services/api';

interface CollectionSidebarProps {
  collections: Collection[];
  activeCollection: Collection | null;
  conversations: Conversation[];
  activeConversationId: number | null;
  onSelectCollection: (collection: Collection) => void;
  onCreateCollection: (name: string, description: string) => void;
  onDeleteCollection: (id: number) => void;
  onSelectConversation: (id: number) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: number) => void;
  onEditConversation: (id: number, name: string) => void;
  onOpenDocuments: () => void;
}

export default function CollectionSidebar({
  collections,
  activeCollection,
  conversations,
  activeConversationId,
  onSelectCollection,
  onCreateCollection, 
  onDeleteCollection,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onEditConversation,
  onOpenDocuments,
}: CollectionSidebarProps) {
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [expandedCollections, setExpandedCollections] = useState<Set<number>>(new Set());
  const [collectionDocs, setCollectionDocs] = useState<Record<number, Document[]>>({});
  const [editingConversationId, setEditingConversationId] = useState<number | null>(null);
  const [editingConversationTitle, setEditingConversationTitle] = useState<string>("");

  const handleCreate = () => {
    if (newName.trim()) {
      onCreateCollection(newName.trim(), newDesc.trim());
      setNewName('');
      setNewDesc('');
      setShowNewForm(false);
    }
  };

  const toggleExpand = async (col: Collection) => {
    const isCurrentlyExpanded = expandedCollections.has(col.id);
    const next = new Set(expandedCollections);

    if (isCurrentlyExpanded) {
      next.delete(col.id);
    } else {
      next.add(col.id);
      // Fetch documents for this collection if not already cached
      if (!collectionDocs[col.id]) {
        try {
          const docs = await api.getDocuments(col.id);
          setCollectionDocs((prev) => ({ ...prev, [col.id]: docs }));
        } catch {
          setCollectionDocs((prev) => ({ ...prev, [col.id]: [] }));
        }
      }
    }
    setExpandedCollections(next);
    onSelectCollection(col);
  };

  // Refresh cached docs when activeCollection changes (e.g. after upload)
  useEffect(() => {
    if (activeCollection && expandedCollections.has(activeCollection.id)) {
      api.getDocuments(activeCollection.id).then((docs) => {
        setCollectionDocs((prev) => ({ ...prev, [activeCollection.id]: docs }));
      }).catch(() => {});
    }
  }, [activeCollection, collections]);

  return (
    <aside className="w-72 bg-gray-900 text-gray-100 flex flex-col h-full">
      {/* Collections Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Library size={16} />
            <span className="text-sm font-semibold uppercase tracking-wide text-gray-400">
              Collections
            </span>
          </div>
          <button
            onClick={() => setShowNewForm(!showNewForm)}
            className="p-1.5 hover:bg-gray-700 rounded-md transition-colors"
            title="New Collection"
          >
            <FolderPlus size={16} />
          </button>
        </div>

        {showNewForm && (
          <div className="space-y-2 mb-2">
            <input
              type="text"
              placeholder="Collection name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              className="w-full px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              autoFocus
            />
            <input
              type="text"
              placeholder="Description (optional)"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              className="w-full px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            />
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                className="flex-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 rounded text-sm font-medium transition-colors"
              >
                Create
              </button>
              <button
                onClick={() => setShowNewForm(false)}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Collection List */}
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {collections.map((col) => {
            const isExpanded = expandedCollections.has(col.id);
            const docs = collectionDocs[col.id] || [];

            return (
              <div key={col.id}>
                <div
                  onClick={() => toggleExpand(col)}
                  className={`group flex items-center justify-between px-3 py-2 rounded-md cursor-pointer text-sm transition-colors ${
                    activeCollection?.id === col.id
                      ? 'bg-indigo-600 text-white'
                      : 'hover:bg-gray-800 text-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <ChevronRight
                      size={14}
                      className={`flex-shrink-0 transition-transform duration-200 ${
                        isExpanded ? 'rotate-90' : ''
                      }`}
                    />
                    <span className="truncate">{col.name}</span>
                    <span className="text-xs opacity-60">({col.document_count})</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteCollection(col.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-600 rounded transition-all"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>

                {/* Expanded document list */}
                {isExpanded && (
                  <div className="ml-5 mt-1 mb-1 space-y-0.5">
                    {docs.length > 0 ? (
                      docs.map((doc) => (
                        <div
                          key={doc.id}
                          className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 rounded hover:bg-gray-800 transition-colors"
                        >
                          <FileText size={12} className="flex-shrink-0 text-gray-500" />
                          <span className="truncate">{doc.filename}</span>
                          <span
                            className={`ml-auto text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 ${
                              doc.status === 'ready'
                                ? 'bg-green-900/40 text-green-400'
                                : doc.status === 'processing'
                                ? 'bg-yellow-900/40 text-yellow-400'
                                : 'bg-red-900/40 text-red-400'
                            }`}
                          >
                            {doc.status}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="px-3 py-1.5 text-xs text-gray-500 italic">
                        No documents yet.
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {collections.length === 0 && (
            <p className="text-xs text-gray-500 px-3 py-2">
              No collections yet. Create one to get started.
            </p>
          )}
        </div>
      </div>

      {/* Active Collection Actions */}
      {activeCollection && (
        <div className="p-4 border-b border-gray-700">
          <button
            onClick={onOpenDocuments}
            className="w-full flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-md text-sm transition-colors mb-2"
          >
            <FileText size={14} />
            <span>Manage Documents</span>
          </button>
          <button
            onClick={onNewConversation}
            className="w-full flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-md text-sm font-medium transition-colors"
          >
            <MessageSquarePlus size={14} />
            <span>New Chat</span>
          </button>
        </div>
      )}

      {/* Conversations */}
      {activeCollection && (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare size={14} className="text-gray-400" />
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">
              Conversations
            </span>
          </div>
          <div className="space-y-1">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={`group flex items-center justify-between px-3 py-2 rounded-md cursor-pointer text-sm transition-colors ${
                  activeConversationId === conv.id
                    ? 'bg-gray-700 text-white'
                    : 'hover:bg-gray-800 text-gray-400'
                }`}
              >
                { editingConversationId ===  conv.id ?
                  <input
                    type="text"
                    value={editingConversationTitle}
                    onChange={(e)=>setEditingConversationTitle(e.target.value)}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                    onBlur={(e) => {
                      if(editingConversationTitle.trim() === ''){
                        setEditingConversationId(null);
                      }
                      else{
                      onEditConversation(conv.id, editingConversationTitle);
                      setEditingConversationId(null);
                      setEditingConversationTitle('');
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        if(editingConversationTitle.trim() === ''){
                          setEditingConversationId(null);
                        }
                        else{
                        onEditConversation(conv.id, editingConversationTitle);
                        setEditingConversationId(null);
                        setEditingConversationTitle('');
                        }
                      } else if (e.key === "Escape") {
                        e.preventDefault();
                        setEditingConversationId(null);
                        setEditingConversationTitle('');
                      }
                    }}
                    className="flex-1 px-2 py-1 rounded bg-gray-800 text-white"
                  />:
                <span className="truncate flex-1">{conv.title}</span>
              }

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingConversationTitle(conv.title);
                    setEditingConversationId(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-600 rounded transition-all"
                >
                  <Pencil size={12} />
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-600 rounded transition-all"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
            {conversations.length === 0 && (
              <p className="text-xs text-gray-500">No conversations yet.</p>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}

