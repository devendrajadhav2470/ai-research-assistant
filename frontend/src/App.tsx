import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import CollectionSidebar from './components/CollectionSidebar';
import ChatInterface from './components/ChatInterface';
import DocumentUpload from './components/DocumentUpload';
import { useCollections } from './hooks/useCollections';
import { useDocuments } from './hooks/useDocuments';
import { useChat } from './hooks/useChat';
import { evaluateMessage } from './services/api';

export default function App() {
  // Model selection
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');

  // Document upload modal
  const [showDocuments, setShowDocuments] = useState(false);

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
    error: chatError,
    fetchConversations,
    loadConversation,
    startNewConversation,
    sendMessage,
    stopStreaming,
    removeConversation,
  } = useChat(activeCollection?.id ?? null);

  // Fetch conversations when collection changes
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
        // Error handled silently
      } finally {
        setEvaluatingId(null);
      }
    },
    [selectedProvider, selectedModel, activeConversation, loadConversation],
  );

  return (
    <div className="h-screen flex flex-col">
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
          onOpenDocuments={() => setShowDocuments(true)}
        />

        <ChatInterface
          messages={messages}
          streamingContent={streamingContent}
          streamingCitations={streamingCitations}
          isStreaming={isStreaming}
          loading={chatLoading}
          error={chatError}
          collectionName={activeCollection?.name ?? null}
          onSendMessage={handleSendMessage}
          onStopStreaming={stopStreaming}
          onEvaluate={handleEvaluate}
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

