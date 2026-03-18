import React, { useState, useEffect, useCallback } from 'react';
import { Menu } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import DocumentUpload from './components/DocumentUpload';
import { useCollections } from './hooks/useCollections';
import { useDocuments } from './hooks/useDocuments';
import { useChat } from './hooks/useChat';
import { evaluateMessage, getBackendStatus } from './services/api';
import BackendUnhealthyBanner from './components/BackendUnhealthyBanner';
import { BackendStatus } from './types';

export default function App() {
  const [selectedProvider, setSelectedProvider] = useState('groq');
  const [selectedModel, setSelectedModel] = useState('llama-3.3-70b-versatile');
  const [showDocuments, setShowDocuments] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({
    status: 'unhealthy',
    service: 'backend',
  });
  const [evaluatingId, setEvaluatingId] = useState<number | null>(null);

  const {
    collections,
    activeCollection,
    setActiveCollection,
    createCollection,
    removeCollection,
  } = useCollections();

  const {
    documents,
    uploading,
    uploadProgress,
    error: docError,
    fetchDocuments,
    uploadDocument,
    removeDocument,
  } = useDocuments(activeCollection?.id ?? null);

  const {
    conversations,
    activeConversation,
    messages,
    streamingContent,
    streamingCitations,
    isStreaming,
    loading: chatLoading,
    loadingMessages,
    hasMoreMessages,
    error: chatError,
    fetchConversations,
    loadConversation,
    loadConversationMessages,
    startNewConversation,
    sendMessage,
    stopStreaming,
    removeConversation,
    updateConversationTitle,
  } = useChat(activeCollection?.id ?? null);

  useEffect(() => {
    getBackendStatus().then((status) => setBackendStatus(status));
  }, []);

  useEffect(() => {
    if (activeCollection) {
      fetchConversations();
      startNewConversation();
    }
  }, [activeCollection?.id]);

  const handleModelChange = useCallback((provider: string, model: string) => {
    setSelectedProvider(provider);
    setSelectedModel(model);
  }, []);

  const handleSendMessage = useCallback(
    (question: string) => {
      sendMessage(question, selectedProvider, selectedModel);
    },
    [sendMessage, selectedProvider, selectedModel]
  );

  const handleEvaluate = useCallback(
    async (messageId: number) => {
      try {
        setEvaluatingId(messageId);
        await evaluateMessage(messageId, selectedProvider, selectedModel);
        if (activeConversation) {
          loadConversation(activeConversation.id);
        }
      } catch {
        console.error('Error evaluating message');
      } finally {
        setEvaluatingId(null);
      }
    },
    [selectedProvider, selectedModel, activeConversation, loadConversation]
  );

  return (
    <div className="h-screen flex flex-col bg-page overflow-hidden">
      <BackendUnhealthyBanner status={backendStatus} />

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          collections={collections}
          activeCollection={activeCollection}
          conversations={conversations}
          activeConversationId={activeConversation?.id ?? null}
          selectedProvider={selectedProvider}
          selectedModel={selectedModel}
          onSelectCollection={setActiveCollection}
          onCreateCollection={createCollection}
          onDeleteCollection={removeCollection}
          onSelectConversation={loadConversation}
          onNewConversation={startNewConversation}
          onDeleteConversation={removeConversation}
          onEditConversation={updateConversationTitle}
          onOpenDocuments={() => setShowDocuments(true)}
          onModelChange={handleModelChange}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main content */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Mobile top bar */}
          <div className="lg:hidden flex items-center gap-3 px-4 py-2.5 bg-white border-b border-border">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
            >
              <Menu size={20} className="text-text-primary" />
            </button>
            <span className="text-sm font-bold text-text-primary">CHAT A.I+</span>
          </div>

          <ChatInterface
            messages={messages}
            streamingContent={streamingContent}
            streamingCitations={streamingCitations}
            isStreaming={isStreaming}
            loading={chatLoading}
            loadingMessages={loadingMessages}
            hasMoreMessages={hasMoreMessages}
            error={chatError}
            collectionName={activeCollection?.name ?? null}
            onSendMessage={handleSendMessage}
            onStopStreaming={stopStreaming}
            onEvaluate={handleEvaluate}
            onLoadMoreMessages={loadConversationMessages}
            evaluatingId={evaluatingId}
          />
        </main>
      </div>

      {/* Document Upload Modal */}
      {showDocuments && activeCollection && (
        <DocumentUpload
          collectionName={activeCollection.name}
          documents={documents}
          uploading={uploading}
          uploadProgress={uploadProgress}
          error={docError}
          onUpload={uploadDocument}
          onDelete={removeDocument}
          onClose={() => setShowDocuments(false)}
          onRefresh={fetchDocuments}
        />
      )}
    </div>
  );
}
