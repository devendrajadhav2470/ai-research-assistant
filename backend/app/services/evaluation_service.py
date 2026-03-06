"""LLM-as-Judge evaluation service for RAG answer quality assessment."""

import json
import logging
from typing import Dict, Any, List, Optional

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

EVALUATION_SYSTEM_PROMPT = """You are an expert evaluator assessing the quality of AI-generated answers 
based on retrieved context from research papers and documents.

You must evaluate the answer on four dimensions and return a JSON object with scores and explanations.

## Evaluation Dimensions

1. **Faithfulness** (1-5): Is every claim in the answer supported by the provided context? 
   - 5: All claims are directly supported by the context
   - 3: Most claims are supported, some minor unsupported statements
   - 1: Many claims are not supported or contradict the context

2. **Relevance** (1-5): Does the answer directly address the user's question?
   - 5: Perfectly addresses the question with focused, relevant information
   - 3: Partially addresses the question, some tangential information
   - 1: Does not address the question or is completely off-topic

3. **Completeness** (1-5): Does the answer cover all important aspects of the question?
   - 5: Comprehensive coverage of all aspects
   - 3: Covers main points but misses some important aspects
   - 1: Very incomplete, misses most key points

4. **Citation Accuracy** (1-5): Are the citations correct and properly referencing the source content?
   - 5: All citations accurately reference the correct sources
   - 3: Most citations are correct, some minor errors
   - 1: Citations are mostly incorrect or missing

## Output Format
Return ONLY a valid JSON object (no markdown, no explanation outside JSON):
{
    "faithfulness": {"score": <1-5>, "explanation": "<brief explanation>"},
    "relevance": {"score": <1-5>, "explanation": "<brief explanation>"},
    "completeness": {"score": <1-5>, "explanation": "<brief explanation>"},
    "citation_accuracy": {"score": <1-5>, "explanation": "<brief explanation>"},
    "overall_score": <average of all scores as float>,
    "summary": "<one sentence overall assessment>"
}"""


EVALUATION_USER_PROMPT_TEMPLATE = """## Question
{question}

## Retrieved Context
{context}

## Generated Answer
{answer}

Please evaluate the generated answer based on the question and retrieved context."""


class EvaluationService:
    """Evaluates RAG answer quality using LLM-as-a-Judge."""

    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or LLMService()

    def evaluate(
        self,
        question: str,
        answer: str,
        context_chunks: List[Dict[str, Any]],
        provider: str = None,
        model_name: str = None,
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of a RAG-generated answer.

        Args:
            question: The user's original question.
            answer: The generated answer to evaluate.
            context_chunks: The retrieved chunks used to generate the answer.
            provider: LLM provider for evaluation (defaults to configured default).
            model_name: Model to use for evaluation.

        Returns:
            Evaluation dict with scores for each dimension.
        """
        # Format context for evaluation
        context_text = self._format_context(context_chunks)

        # Build evaluation prompt
        eval_prompt = EVALUATION_USER_PROMPT_TEMPLATE.format(
            question=question,
            context=context_text,
            answer=answer,
        )

        messages = [
            {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": eval_prompt},
        ]

        print("evaluation_service messages:")
        try:
            response = self.llm_service.generate(
                messages=messages,
                provider=provider,
                model_name=model_name,
                temperature=0.0,  # Deterministic for evaluation
            )
            print("evaluation_service response: ")
            evaluation = self._parse_evaluation_response(response)
            logger.info(
                f"Evaluation complete. Overall score: {evaluation.get('overall_score', 'N/A')}"
            )
            return evaluation

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return self._default_evaluation(str(e))

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format context chunks into a readable string for evaluation."""
        if not chunks:
            return "No context provided."

        formatted = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "Unknown")
            page = chunk.get("page_number", "?")
            content = chunk.get("content", "")
            formatted.append(
                f"[Source {i}: {source}, Page {page}]\n{content}"
            )
        return "\n\n".join(formatted)

    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM's evaluation response into a structured dict."""
        try:
            # Try to extract JSON from the response
            response = response.strip()

            # Handle case where response is wrapped in markdown code blocks
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith("```") and not in_block:
                        in_block = True
                        continue
                    elif line.startswith("```") and in_block:
                        break
                    elif in_block:
                        json_lines.append(line)
                response = "\n".join(json_lines)

            evaluation = json.loads(response)

            # Validate required fields
            required = ["faithfulness", "relevance", "completeness", "citation_accuracy"]
            for field in required:
                if field not in evaluation:
                    evaluation[field] = {"score": 0, "explanation": "Not evaluated"}

            # Calculate overall score if missing
            if "overall_score" not in evaluation:
                scores = [
                    evaluation[f].get("score", 0) for f in required
                    if isinstance(evaluation[f], dict)
                ]
                evaluation["overall_score"] = (
                    sum(scores) / len(scores) if scores else 0
                )

            return evaluation

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse evaluation response: {e}")
            return self._default_evaluation(f"Parse error: {e}")

    @staticmethod
    def _default_evaluation(error_msg: str = "") -> Dict[str, Any]:
        """Return a default evaluation when the process fails."""
        return {
            "faithfulness": {"score": 0, "explanation": "Evaluation failed"},
            "relevance": {"score": 0, "explanation": "Evaluation failed"},
            "completeness": {"score": 0, "explanation": "Evaluation failed"},
            "citation_accuracy": {"score": 0, "explanation": "Evaluation failed"},
            "overall_score": 0,
            "summary": f"Evaluation could not be completed. {error_msg}",
            "error": True,
        }

