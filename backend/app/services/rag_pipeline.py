"""Core RAG pipeline: retrieval, prompt construction, citation generation, and streaming."""

import logging
import json
from typing import Generator, List, Dict, Any, Optional

from app.services.retriever import HybridRetriever
from app.services.llm_service import LLMService
from app.services.chat_service import ChatService
from app.services.evaluation_service import EvaluationService
from app.config import Config

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are an AI Research Assistant that answers questions based on research papers, \
policy documents, and technical documentation. You provide accurate, well-structured answers grounded in \
the provided context.

## CRITICAL: Citation Rules
- Always cite using: [Source: <filename>, Source_Page <citation_page_number>]
- The ONLY valid citation_page_number for a citation is the one in the citation_page_number attribute of the <ctx> tag.
- NEVER use page numbers found inside the text content of a chunk. Those are part of the document's own text and do NOT represent the actual page location.
- Example: If a chunk says <ctx id=1 doc="book.pdf" citation_page_number=89> and the text inside mentions "page 54", you MUST cite Page 89, NOT Page 54.

## Other Instructions
1. Answer the question based ONLY on the provided context from the retrieved documents.
2. If the context does not contain enough information to answer the question, clearly state that.
3. Include citations inline, right after the relevant claim or statement.
4. Structure your answer with clear paragraphs. Use bullet points or numbered lists when appropriate.
5. Be precise and concise. Do not add information that is not in the context.
6. If multiple sources provide relevant information, synthesize them and cite each source.


## Context from Retrieved Documents
{context}"""

RAG_USER_PROMPT_TEMPLATE = """{question}"""


class RAGPipeline:
    """Orchestrates the full RAG flow: retrieve, augment, generate."""

    def __init__(
        self,
        retriever: HybridRetriever = None,
        llm_service: LLMService = None,
        chat_service: ChatService = None,
        evaluation_service: EvaluationService = None,
    ):
        self.retriever = retriever or HybridRetriever()
        self.llm_service = llm_service or LLMService()
        self.chat_service = chat_service or ChatService()
        self.evaluation_service = evaluation_service or EvaluationService(self.llm_service)

    def query(
        self,
        collection_id: int,
        question: str,
        conversation_id: int = None,
        provider: str = None,
        model_name: str = None,
        top_k: int = None,
    ) -> Dict[str, Any]:
        """
        Execute the full RAG pipeline (non-streaming).

        Args:
            collection_id: Collection to search.
            question: User's question.
            conversation_id: Optional conversation for chat history.
            provider: LLM provider to use.
            model_name: Model to use.
            top_k: Number of chunks to retrieve.

        Returns:
            Dict with 'answer', 'citations', 'chunks', 'model_info'.
        """
        # Step 1: Retrieve relevant chunks
        chunks = self.retriever.retrieve(
            collection_id=collection_id,
            query=question,
            top_k=top_k,
        )

        # Step 2: Build messages with context and chat history
        messages = self._build_messages(
            question=question,
            chunks=chunks,
            conversation_id=conversation_id,
        )

        # Step 3: Generate answer
        answer = self.llm_service.generate(
            messages=messages,
            provider=provider,
            model_name=model_name,
        )

        # Step 4: Extract citations
        citations = self._extract_citations(chunks)

        return {
            "answer": answer,
            "citations": citations,
            "chunks": chunks,
            "model_info": {
                "provider": provider or Config.DEFAULT_LLM_PROVIDER,
                "model": model_name or Config.DEFAULT_MODEL_NAME,
            },
        }

    def query_stream(
        self,
        collection_id: int,
        question: str,
        conversation_id: int = None,
        provider: str = None,
        model_name: str = None,
        top_k: int = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Execute the RAG pipeline with streaming response.

        Yields SSE-formatted events:
        - {"type": "chunks", "data": [...]} - retrieved context chunks
        - {"type": "token", "data": "..."} - individual tokens
        - {"type": "citations", "data": [...]} - source citations
        - {"type": "done", "data": {"answer": "..."}} - completion signal
        - {"type": "error", "data": "..."} - error message
        """
        try:
            # Step 1: Retrieve relevant chunks
            chunks = self.retriever.retrieve(
                collection_id=collection_id,
                query=question,
                top_k=top_k,
            )

            # Yield retrieved chunks
            citations = self._extract_citations(chunks)
            yield {
                "type": "chunks",
                "data": citations,
            }

            # Step 2: Build messages
            messages = self._build_messages(
                question=question,
                chunks=chunks,
                conversation_id=conversation_id,
            )

            # Step 3: Stream answer tokens
            full_answer = []
            for token in self.llm_service.generate_stream(
                messages=messages,
                provider=provider,
                model_name=model_name,
            ):
                full_answer.append(token)
                yield {
                    "type": "token",
                    "data": token,
                }

            # Step 4: Final response
            complete_answer = "".join(full_answer)
            yield {
                "type": "done",
                "data": {
                    "answer": complete_answer,
                    "citations": citations,
                    "model_info": {
                        "provider": provider or Config.DEFAULT_LLM_PROVIDER,
                        "model": model_name or Config.DEFAULT_MODEL_NAME,
                    },
                },
            }

        except Exception as e:
            logger.error(f"RAG pipeline error: {e}")
            yield {
                "type": "error",
                "data": str(e),
            }

    def evaluate_response(
        self,
        question: str,
        answer: str,
        chunks: List[Dict[str, Any]],
        provider: str = None,
        model_name: str = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a RAG response quality using LLM-as-Judge.

        Returns evaluation scores dict.
        """
        return self.evaluation_service.evaluate(
            question=question,
            answer=answer,
            context_chunks=chunks,
            provider=provider,
            model_name=model_name,
        )

    def _build_messages(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        conversation_id: int = None,
    ) -> List[Dict[str, str]]:
        """Build the message list for the LLM with context and chat history."""
        # Format context from chunks
        context = self._format_context(chunks)
        print(context)
        # System prompt with context
        system_prompt = RAG_SYSTEM_PROMPT.format(context=context)

        messages = [{"role": "system", "content": system_prompt}]

        # Add chat history if conversation exists
        if conversation_id:
            history = self.chat_service.get_chat_history(conversation_id)
            messages.extend(history)
        
        # Add current question if not already present in the chat history 

        if messages[-1]["role"] == "user" and messages[-1]["content"] == question:
            # this means the user message exists in the chat_history, I only need to change its format
            messages[-1]["content"] = RAG_USER_PROMPT_TEMPLATE.format(question=question)

        else:
            messages.append({
                "role": "user",
                "content": RAG_USER_PROMPT_TEMPLATE.format(question=question)
            })
            
        return messages

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into a context string for the LLM prompt."""
        if not chunks:
            return "No relevant context found."

        formatted = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "Unknown")
            page = chunk.get("page_number", "?")
            content = chunk.get("content", "")
            score_info = ""
            if "rerank_score" in chunk:
                score_info = f" (relevance: {chunk['rerank_score']:.3f})"

            formatted.append(
                f"<ctx id={i} doc='{source}' citation_page_number={page} {score_info}>\n{content}\n</ctx>"
            )

        return "\n\n---\n\n".join(formatted)

    def _extract_citations(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract citation information from retrieved chunks."""
        citations = []
        seen = set()

        for chunk in chunks:
            source = chunk.get("source", "Unknown")
            page = chunk.get("page_number", "?")
            doc_id = chunk.get("document_id", "")
            key = f"{source}_{page}"

            if key not in seen:
                seen.add(key)
                
                content_preview = chunk.get("content", "")[:201]
                if len(content_preview) > 200 :
                    content_preview = content_preview + "..."
                else:
                    content_preview = content_preview[:-1]

                citations.append({
                    "source": source,
                    "page_number": page,
                    "document_id": doc_id,
                    "content_preview": content_preview,
                    "relevance_score": round(chunk.get("rerank_score", 0), 3),
                })

        return citations

