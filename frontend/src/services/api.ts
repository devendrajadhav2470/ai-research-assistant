/**
 * API client for the AI Research Assistant backend.
 */
import axios from 'axios';
import type {
  Collection,
  Document,
  Conversation,
  Message,
  QueryResponse,
  AvailableModels,
  Evaluation,
  BackendStatus,
} from '../types';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function getBackendStatus(): Promise<BackendStatus> {
  const { data } = await api.get('/health');
  return data;
}
// ==================== Collections ====================

export async function getCollections(): Promise<Collection[]> {
  const { data } = await api.get('/collections');
  return data;
}

export async function createCollection(name: string, description: string = ''): Promise<Collection> {
  const { data } = await api.post('/collections', { name, description });
  return data;
}

export async function updateCollection(id: number, updates: Partial<Collection>): Promise<Collection> {
  const { data } = await api.put(`/collections/${id}`, updates);
  return data;
}

export async function deleteCollection(id: number): Promise<void> {
  await api.delete(`/collections/${id}`);
}

// ==================== Documents ====================

export async function getDocuments(collectionId: number): Promise<Document[]> {
  const { data } = await api.get(`/documents/collection/${collectionId}`);
  return data;
}

export async function uploadDocument(collectionId: number, file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post(`/documents/upload/${collectionId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function deleteDocument(documentId: number): Promise<void> {
  await api.delete(`/documents/${documentId}`);
}

// ==================== Chat ====================

export async function getConversations(collectionId: number): Promise<Conversation[]> {
  const { data } = await api.get(`/chat/conversations/collection/${collectionId}`);
  return data;
}

export async function createConversation(collectionId: number, title?: string): Promise<Conversation> {
  const { data } = await api.post('/chat/conversations', {
    collection_id: collectionId,
    title: title || 'New Conversation',
  });
  return data;
}

export async function getConversation(conversationId: number): Promise<{conversation: Conversation; hasOlder: boolean}> {
  const { data } = await api.get(`/chat/conversations/${conversationId}`);
  const {hasOlder, ...conversation} = data;
  return {
    conversation,
    hasOlder: hasOlder 
  };
}

export async function getConversationMessages(conversationId: number, limit: number, beforeId?: number | null): Promise<{messages: Message[]; hasOlder: boolean}> {
  const url = beforeId != null
  ? `/chat/conversations/${conversationId}?limit=${limit}&before_id=${beforeId}`
  : `/chat/conversations/${conversationId}?limit=${limit}`;
  const { data } = await api.get(url);
  return {
    messages: data.messages ?? [],
    hasOlder: data.hasOlder === true,
  };
}

export async function updateConversation(conversationId: number, updates: Partial<Conversation>): Promise<Conversation> {
  const { data } = await api.patch(`/chat/conversations/${conversationId}`, updates);
  return data;
}

export async function deleteConversation(conversationId: number): Promise<void> {
  await api.delete(`/chat/conversations/${conversationId}`);
}

export async function queryRAG(
  question: string,
  collectionId: number,
  conversationId?: number,
  provider?: string,
  modelName?: string,
): Promise<QueryResponse> {
  const { data } = await api.post('/chat/query', {
    question,
    collection_id: collectionId,
    conversation_id: conversationId,
    provider,
    model_name: modelName,
  });
  return data;
}

/**
 * Stream a RAG query response using Server-Sent Events.
 */
export function queryRAGStream(
  question: string,
  collectionId: number,
  conversationId?: number,
  provider?: string,
  modelName?: string,
  callbacks?: {
    onChunks?: (citations: any[]) => void;
    onToken?: (token: string) => void;
    onDone?: (data: any) => void;
    onError?: (error: string) => void;
  },
): AbortController {
  const controller = new AbortController();

  fetch(`${API_BASE}/chat/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      collection_id: collectionId,
      conversation_id: conversationId,
      provider,
      model_name: modelName,
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json();
        callbacks?.onError?.(err.error || 'Request failed');
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const data = JSON.parse(jsonStr);
              switch (eventType) {
                case 'chunks':
                  callbacks?.onChunks?.(data);
                  break;
                case 'token':
                  callbacks?.onToken?.(data);
                  break;
                case 'done':
                  callbacks?.onDone?.(data);
                  break;
                case 'error':
                  callbacks?.onError?.(data);
                  break;
              }
            } catch {
              // Token data might be a plain string
              if (eventType === 'token') {
                callbacks?.onToken?.(jsonStr);
              }
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        callbacks?.onError?.(err.message);
      }
    });

  return controller;
}

// ==================== Models ====================

export async function getAvailableModels(): Promise<AvailableModels> {
  const { data } = await api.get('/chat/models');
  return data;
}

// ==================== Evaluation ====================

export async function evaluateMessage(
  messageId: number,
  provider?: string,
  modelName?: string,
): Promise<{ message_id: number; evaluation: Evaluation }> {
  const { data } = await api.post(`/evaluation/evaluate/${messageId}`, {
    provider,
    model_name: modelName,
  });
  return data;
}

export async function getMessageEvaluation(
  messageId: number,
): Promise<{ message_id: number; evaluation: Evaluation }> {
  const { data } = await api.get(`/evaluation/message/${messageId}`);
  return data;
}

