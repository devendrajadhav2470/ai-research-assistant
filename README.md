<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

# AI Research Assistant

A full-stack **Retrieval-Augmented Generation (RAG)** application that lets you upload research papers, technical documents, and PDFs, then ask questions and get accurate, cited answers powered by LLMs.

Built with a **hybrid retrieval pipeline** (semantic search + keyword search + reranking), **multi-provider LLM support** (OpenAI, Anthropic, Groq), **real-time streaming**, and **LLM-as-Judge evaluation** — all wrapped in a modern chat UI.

---

## Features

### Intelligent Document Q&A
- Upload PDFs and ask natural-language questions grounded in your documents
- Answers include **inline citations** with source filename and page number
- Conversation history for multi-turn follow-up questions

### Advanced Hybrid Retrieval
- **FAISS vector search** with SentenceTransformer embeddings (`all-MiniLM-L6-v2`)
- **BM25 keyword search** for lexical matching
- **Reciprocal Rank Fusion (RRF)** to merge results from both retrieval methods
- **Cross-encoder reranking** (`ms-marco-MiniLM-L-6-v2`) for precision

### Multi-Provider LLM Support
| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o Mini, GPT-4 Turbo |
| **Anthropic** | Claude Sonnet 4, Claude 3.5 Haiku |
| **Groq** | Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B |

Switch models on the fly from the UI — only providers with configured API keys are shown.

### Real-Time Streaming
- Server-Sent Events (SSE) deliver tokens as they're generated
- Retrieved source citations appear before the answer starts streaming
- Stop generation mid-stream with a single click

### RAG Quality Evaluation
- **LLM-as-Judge** evaluates every answer across four dimensions:
  - **Faithfulness** — Are claims supported by the context?
  - **Relevance** — Does the answer address the question?
  - **Completeness** — Are all important aspects covered?
  - **Citation Accuracy** — Do citations correctly reference sources?
- Per-dimension scores (1–5) with explanations and an overall score

### Collection-Based Organization
- Group documents into **collections** (e.g., per project, topic, or paper)
- Each collection has its own FAISS index and conversation threads
- Upload, view, and manage documents per collection

### Observability
- Optional **Langfuse** integration for tracing LLM calls and retrieval performance

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  Vite + TypeScript + Tailwind CSS                       │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐             │
│  │  Chat   │  │ Document │  │ Collection │             │
│  │Interface│  │  Upload  │  │  Sidebar   │             │
│  └────┬────┘  └────┬─────┘  └─────┬──────┘             │
└───────┼─────────────┼──────────────┼────────────────────┘
        │  SSE Stream │   REST API   │
        ▼             ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                   Backend (Flask)                        │
│                                                         │
│  ┌──────────────────────────────────────┐               │
│  │           RAG Pipeline               │               │
│  │  ┌──────────┐    ┌───────────────┐   │               │
│  │  │ Hybrid   │───▶│ LLM Service   │   │               │
│  │  │ Retriever│    │ (LangChain)   │   │               │
│  │  └──┬───┬───┘    └───────────────┘   │               │
│  │     │   │                            │               │
│  │     ▼   ▼                            │               │
│  │  ┌────┐ ┌─────┐  ┌──────────────┐   │               │
│  │  │FAISS│ │BM25 │  │  Evaluation  │   │               │
│  │  │Index│ │Index│  │  (LLM Judge) │   │               │
│  │  └────┘ └─────┘  └──────────────┘   │               │
│  └──────────────────────────────────────┘               │
│                                                         │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────┐    │
│  │  Document    │  │  Embedding │  │  SQLite DB   │    │
│  │  Processor   │  │  Service   │  │  (metadata)  │    │
│  │  (PyPDF)     │  │ (MiniLM)   │  └──────────────┘    │
│  └──────────────┘  └────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- At least one LLM API key (OpenAI, Anthropic, or Groq)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ai-research-assistant.git
cd ai-research-assistant
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# LLM Providers (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...

# Defaults
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4o-mini

# Embedding & Retrieval
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
RERANKER_MODEL_NAME=cross-encoder/ms-marco-MiniLM-L-6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=20
TOP_K_RERANK=5

# Observability (optional)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Download NLTK tokenizer data
python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

# Run the Flask server
flask --app app:create_app run --port 5000
```

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### Docker (Alternative)

Spin up both services with Docker Compose:

```bash
docker compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000

---

## Usage

1. **Create a Collection** — Click `+ New Collection` in the sidebar and give it a name.
2. **Upload Documents** — Open the documents panel and drag-and-drop PDF files. They'll be parsed, chunked, embedded, and indexed automatically.
3. **Ask Questions** — Type a question in the chat. The system retrieves relevant chunks, streams an LLM-generated answer with inline citations, and shows source cards.
4. **Evaluate Answers** — Click the evaluate button on any assistant message to get an LLM-as-Judge quality assessment with scores for faithfulness, relevance, completeness, and citation accuracy.
5. **Switch Models** — Use the model selector in the header to switch between providers and models on the fly.

---

## API Reference

### Collections

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/collections` | List all collections |
| `POST` | `/api/collections` | Create a collection |
| `PUT` | `/api/collections/:id` | Update a collection |
| `DELETE` | `/api/collections/:id` | Delete a collection |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/documents/collection/:id` | List documents in a collection |
| `POST` | `/api/documents/upload/:collection_id` | Upload a PDF (multipart) |
| `DELETE` | `/api/documents/:id` | Delete a document |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/chat/conversations/:collection_id` | List conversations |
| `POST` | `/api/chat/conversations` | Create a conversation |
| `GET` | `/api/chat/conversations/:id` | Get conversation with messages |
| `DELETE` | `/api/chat/conversations/:id` | Delete a conversation |
| `POST` | `/api/chat/query` | Query (non-streaming) |
| `POST` | `/api/chat/query/stream` | Query (SSE streaming) |
| `GET` | `/api/chat/models` | List available LLM models |

### Evaluation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/evaluation/evaluate/:message_id` | Evaluate a message |
| `GET` | `/api/evaluation/message/:message_id` | Get evaluation for a message |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |

---

## Project Structure

```
ai-research-assistant/
├── backend/
│   ├── app/
│   │   ├── __init__.py            # Flask app factory
│   │   ├── config.py              # Environment-based configuration
│   │   ├── extensions.py          # Flask extensions (SQLAlchemy, CORS)
│   │   ├── api/
│   │   │   ├── chat.py            # Chat & query endpoints (SSE streaming)
│   │   │   ├── collections.py     # Collection CRUD
│   │   │   ├── documents.py       # Document upload & management
│   │   │   └── evaluation.py      # LLM-as-Judge evaluation
│   │   ├── models/
│   │   │   ├── chat.py            # Conversation & Message models
│   │   │   └── document.py        # Collection, Document, Chunk models
│   │   ├── services/
│   │   │   ├── rag_pipeline.py    # Core RAG orchestration
│   │   │   ├── retriever.py       # Hybrid retriever (FAISS + BM25 + RRF + reranking)
│   │   │   ├── llm_service.py     # Multi-provider LLM service (LangChain)
│   │   │   ├── embedding_service.py # SentenceTransformer embeddings
│   │   │   ├── vector_store.py    # FAISS index management
│   │   │   ├── bm25_index.py      # BM25 keyword index
│   │   │   ├── document_processor.py # PDF parsing & chunking
│   │   │   ├── chat_service.py    # Chat history management
│   │   │   └── evaluation_service.py # LLM-as-Judge evaluation
│   │   └── utils/
│   │       └── observability.py   # Langfuse tracing integration
│   ├── tests/                     # Backend test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Main application component
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx   # Chat UI with streaming
│   │   │   ├── MessageBubble.tsx   # Message rendering with markdown
│   │   │   ├── CitationCard.tsx    # Source citation display
│   │   │   ├── CollectionSidebar.tsx # Collection & conversation nav
│   │   │   ├── DocumentUpload.tsx  # Drag-and-drop PDF upload
│   │   │   ├── EvaluationBadge.tsx # Quality score display
│   │   │   └── Header.tsx          # Model selector header
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── services/api.ts         # API client with SSE support
│   │   └── types/index.ts          # TypeScript type definitions
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
└── docker-compose.yml
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS |
| **Backend** | Flask 3.1, Python 3.11 |
| **LLM Orchestration** | LangChain (OpenAI, Anthropic, Groq) |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) |
| **Vector Store** | FAISS (with cosine similarity) |
| **Keyword Search** | BM25 (`rank-bm25`) |
| **Reranking** | Cross-encoder (`ms-marco-MiniLM-L-6-v2`) |
| **Document Parsing** | PyPDF |
| **Database** | SQLite + SQLAlchemy |
| **Streaming** | Server-Sent Events (SSE) |
| **Observability** | Langfuse |
| **Deployment** | Docker + Docker Compose + Nginx |

---

## Configuration Reference

All settings are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GROQ_API_KEY` | — | Groq API key |
| `DEFAULT_LLM_PROVIDER` | `openai` | Default LLM provider |
| `DEFAULT_MODEL_NAME` | `gpt-4o-mini` | Default model |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | SentenceTransformer model for embeddings |
| `RERANKER_MODEL_NAME` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model for reranking |
| `CHUNK_SIZE` | `1000` | Max characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |
| `TOP_K_RETRIEVAL` | `20` | Candidates retrieved from each search method |
| `TOP_K_RERANK` | `5` | Final results after reranking |
| `CHAT_HISTORY_WINDOW` | `10` | Number of past messages included as context |
| `LANGFUSE_PUBLIC_KEY` | — | Langfuse public key (optional) |
| `LANGFUSE_SECRET_KEY` | — | Langfuse secret key (optional) |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse host URL |

---

## License

This project is open source and available under the [MIT License](LICENSE).

