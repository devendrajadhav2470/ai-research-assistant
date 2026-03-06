// ==========================================
// AI Research Assistant - TypeScript Types
// ==========================================


export interface BackendStatus {
  status: string;
  service: string;
}

// --- Collections ---
export interface Collection {
  id: number;
  name: string;
  description: string;
  document_count: number;
  created_at: string;
  updated_at: string | null;
}

// --- Documents ---
export interface Document {
  id: number;
  collection_id: number;
  filename: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  status: 'processing' | 'ready' | 'error';
  error_message: string | null;
  created_at: string;
}

// --- Chat ---
export interface Citation {
  source: string;
  page_number: number;
  document_id: number;
  content_preview: string;
  relevance_score: number;
}

export interface EvaluationDimension {
  score: number;
  explanation: string;
}

export interface Evaluation {
  faithfulness: EvaluationDimension;
  relevance: EvaluationDimension;
  completeness: EvaluationDimension;
  citation_accuracy: EvaluationDimension;
  overall_score: number;
  summary: string;
  error?: boolean;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  evaluation: Evaluation | Record<string, never>;
  model_name: string | null;
  provider: string | null;
  created_at: string;
}

export interface Conversation {
  id: number;
  collection_id: number;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string | null;
  messages?: Message[];
}

// --- LLM Models ---
export interface ModelOption {
  id: string;
  name: string;
}

export type AvailableModels = Record<string, ModelOption[]>;

// --- Query ---
export interface QueryRequest {
  question: string;
  collection_id: number;
  conversation_id?: number;
  provider?: string;
  model_name?: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  conversation_id: number;
  message_id: number;
  model_info: {
    provider: string;
    model: string;
  };
}

// --- SSE Events ---
export interface SSEChunksEvent {
  type: 'chunks';
  data: Citation[];
}

export interface SSETokenEvent {
  type: 'token';
  data: string;
}

export interface SSEDoneEvent {
  type: 'done';
  data: {
    answer: string;
    citations: Citation[];
    conversation_id: number;
    model_info: {
      provider: string;
      model: string;
    };
  };
}

export interface SSEErrorEvent {
  type: 'error';
  data: string;
}

export type SSEEvent = SSEChunksEvent | SSETokenEvent | SSEDoneEvent | SSEErrorEvent;

