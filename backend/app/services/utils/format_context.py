from typing import List, Dict, Any

def format_context(chunks: List[Dict[str, Any]]) -> str:
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