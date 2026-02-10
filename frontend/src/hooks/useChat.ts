import { useState, useCallback, useRef } from 'react';
import type { Message, Citation, Conversation } from '../types';
import * as api from '../services/api';

export function useChat(collectionId: number | null) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchConversations = useCallback(async () => {
    if (!collectionId) return;
    try {
      const data = await api.getConversations(collectionId);
      setConversations(data);
    } catch (err: any) {
      setError(err.message);
    }
  }, [collectionId]);

  const loadConversation = useCallback(async (conversationId: number) => {
    try {
      setLoading(true);
      const data = await api.getConversation(conversationId);
      setActiveConversation(data);
      setMessages(data.messages || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const startNewConversation = useCallback(() => {
    setActiveConversation(null);
    setMessages([]);
    setStreamingContent('');
    setStreamingCitations([]);
    setError(null);
  }, []);

  const sendMessage = useCallback(
    async (
      question: string,
      provider?: string,
      modelName?: string,
    ) => {
      if (!collectionId) return;

      setError(null);
      setIsStreaming(true);
      setStreamingContent('');
      setStreamingCitations([]);

      // Add user message to UI immediately
      const userMessage: Message = {
        id: Date.now(),
        conversation_id: activeConversation?.id || 0,
        role: 'user',
        content: question,
        citations: [],
        evaluation: {},
        model_name: null,
        provider: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Stream the response
      const controller = api.queryRAGStream(
        question,
        collectionId,
        activeConversation?.id,
        provider,
        modelName,
        {
          onChunks: (citations) => {
            setStreamingCitations(citations);
          },
          onToken: (token) => {
            setStreamingContent((prev) => prev + token);
          },
          onDone: (data) => {
            const assistantMessage: Message = {
              id: Date.now() + 1,
              conversation_id: data.conversation_id,
              role: 'assistant',
              content: data.answer,
              citations: data.citations || [],
              evaluation: {},
              model_name: data.model_info?.model || null,
              provider: data.model_info?.provider || null,
              created_at: new Date().toISOString(),
            };

            setMessages((prev) => [...prev, assistantMessage]);
            setStreamingContent('');
            setStreamingCitations([]);
            setIsStreaming(false);

            // Update active conversation
            if (!activeConversation) {
              setActiveConversation({
                id: data.conversation_id,
                collection_id: collectionId,
                title: question.slice(0, 100),
                message_count: 2,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              });
            }

            // Refresh conversation list
            fetchConversations();
          },
          onError: (errMsg) => {
            setError(errMsg);
            setIsStreaming(false);
            setStreamingContent('');
          },
        },
      );

      abortControllerRef.current = controller;
    },
    [collectionId, activeConversation, fetchConversations],
  );

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
    if (streamingContent) {
      const partialMessage: Message = {
        id: Date.now(),
        conversation_id: activeConversation?.id || 0,
        role: 'assistant',
        content: streamingContent + '\n\n*[Response stopped by user]*',
        citations: streamingCitations,
        evaluation: {},
        model_name: null,
        provider: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, partialMessage]);
      setStreamingContent('');
      setStreamingCitations([]);
    }
  }, [streamingContent, streamingCitations, activeConversation]);

  const removeConversation = useCallback(async (conversationId: number) => {
    try {
      await api.deleteConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      if (activeConversation?.id === conversationId) {
        startNewConversation();
      }
    } catch (err: any) {
      setError(err.message);
    }
  }, [activeConversation, startNewConversation]);

  return {
    conversations,
    activeConversation,
    messages,
    streamingContent,
    streamingCitations,
    isStreaming,
    loading,
    error,
    fetchConversations,
    loadConversation,
    startNewConversation,
    sendMessage,
    stopStreaming,
    removeConversation,
    setActiveConversation,
  };
}

