import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import CollectionSidebar from './components/CollectionSidebar';
import ChatInterface from './components/ChatInterface';
import DocumentUpload from './components/DocumentUpload';
import { useCollections } from './hooks/useCollections';
import { useDocuments } from './hooks/useDocuments';
import { useChat } from './hooks/useChat';
import { evaluateMessage, getBackendStatus } from './services/api';
import BackendUnhealthyBanner from './components/BackendUnhealthyBanner';
import { BackendStatus } from './types';

export default function App() {
  // Model selection
  const [selectedProvider, setSelectedProvider] = useState('groq');
  const [selectedModel, setSelectedModel] = useState('llama-3.3-70b-versatile');

  // Document upload modal
  const [showDocuments, setShowDocuments] = useState(false);

  // Backend status
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ status: 'unhealthy', service: 'backend' });

  // Evaluation state
  const [evaluatingId, setEvaluatingId] = useState<number | null>(null);

  // Collections
  const {
    collections,
    activeCollection,
    setActiveCollection,
    createCollection,
    removeCollection,
  } = useCollections();

  // Documents
  const {
    documents,
    uploading,
    uploadProgress,
    error: docError,
    fetchDocuments,
    uploadDocument,
    removeDocument,
  } = useDocuments(activeCollection?.id ?? null);

  // Chat
  const {
    conversations,
    activeConversation,
    messages,
    streamingContent,
    streamingCitations,
    isStreaming,
    loading: chatLoading,
    loadingMessages: loadingMessages,
    hasMoreMessages: hasMoreMessages,
    error: chatError,
    fetchConversations,
    loadConversation,
    loadConversationMessages,
    startNewConversation,
    sendMessage,
    stopStreaming,
    removeConversation,
    updateConversationTitle
  } = useChat(activeCollection?.id ?? null);

  // Fetch conversations when collection changes



  useEffect(() => {
    getBackendStatus().then((status) => {
      setBackendStatus(status);
    });
  }, []);
  useEffect(() => {
    if (activeCollection) {
      fetchConversations();
      startNewConversation();
    }
  }, [activeCollection?.id]);

  // Handle model change
  const handleModelChange = useCallback((provider: string, model: string) => {
    setSelectedProvider(provider);
    setSelectedModel(model);
  }, []);

  // Handle send message with model selection
  const handleSendMessage = useCallback(
    (question: string) => {
      sendMessage(question, selectedProvider, selectedModel);
    },
    [sendMessage, selectedProvider, selectedModel],
  );

  // Handle evaluate message
  const handleEvaluate = useCallback(
    async (messageId: number) => {
      try {
        setEvaluatingId(messageId);
        await evaluateMessage(messageId, selectedProvider, selectedModel);
        // Reload conversation to get updated evaluation
        if (activeConversation) {
          loadConversation(activeConversation.id);
        }
      } catch {
        console.error("Error evaluating message");
      } finally {
        setEvaluatingId(null);
      }
    },
    [selectedProvider, selectedModel, activeConversation, loadConversation],
  );

  return (
    <div className="h-screen flex flex-col">
      <BackendUnhealthyBanner status={backendStatus} />
      <Header
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        onModelChange={handleModelChange}
      />

      <div className="flex-1 flex overflow-hidden">
        <CollectionSidebar
          collections={collections}
          activeCollection={activeCollection}
          conversations={conversations}
          activeConversationId={activeConversation?.id ?? null}
          onSelectCollection={setActiveCollection}
          onCreateCollection={createCollection}
          onDeleteCollection={removeCollection}
          onSelectConversation={loadConversation}
          onNewConversation={startNewConversation}
          onDeleteConversation={removeConversation}
          onEditConversation={updateConversationTitle}
          onOpenDocuments={() => setShowDocuments(true)}
        />

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

