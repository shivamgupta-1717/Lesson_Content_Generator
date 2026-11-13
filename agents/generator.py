"""Lesson Generator Agent.

Responsible for generating comprehensive, beginner-friendly lessons tailored for
Indian 12th-grade learners. Fully supports feedback-driven regeneration and deliberate
error injection for demonstration and automated testing.
"""

from typing import List, Optional
from evaluation.schemas import LessonContent
from prompts.generator_prompt import GENERATOR_SYSTEM_PROMPT, build_generator_prompt
from services.llm_service import BaseLLMProvider, get_llm_provider
from utils.logger import logger


class LessonGeneratorAgent:
    """Agent that creates structured, pedagogical educational lessons."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider or get_llm_provider()

    def generate(
        self,
        topic: str,
        target_audience: str,
        feedback: Optional[str] = None,
        evolution_insights: Optional[List[str]] = None,
        deliberate_error_mode: Optional[str] = None,
    ) -> LessonContent:
        """Generates a complete educational lesson.

        Args:
            topic: The educational topic (e.g. 'Introduction to RAG').
            target_audience: Learner persona description.
            feedback: Evaluator feedback from previous failed attempt, if any.
            evolution_insights: Historical learned rules to guide generation.
            deliberate_error_mode: Flag to inject flawed content for demonstration.

        Returns:
            LessonContent: Validated Pydantic structured lesson.
        """
        is_regeneration = feedback is not None and len(feedback.strip()) > 0
        logger.info(
            f"LessonGeneratorAgent: Starting generation for topic='{topic}' "
            f"(Regeneration={is_regeneration}, ErrorMode={deliberate_error_mode})"
        )

        # If LLM provider is DeterministicMockLLMProvider, inform it of the error mode
        if hasattr(self.llm_provider, "set_error_mode"):
            self.llm_provider.set_error_mode(deliberate_error_mode)

        prompt = build_generator_prompt(
            topic=topic,
            target_audience=target_audience,
            feedback=feedback,
            evolution_insights=evolution_insights,
            deliberate_error_mode=deliberate_error_mode,
        )

        lesson = self.llm_provider.generate_structured(
            prompt=prompt,
            response_model=LessonContent,
            system_prompt=GENERATOR_SYSTEM_PROMPT,
        )

        # Handle deliberate error injection for real LLM providers if requested
        if deliberate_error_mode and not is_regeneration:
            lesson = self._apply_deliberate_error(lesson, deliberate_error_mode)

        logger.info(f"LessonGeneratorAgent: Successfully produced lesson '{lesson.title}'")
        return lesson

    def _apply_deliberate_error(
        self, lesson: LessonContent, error_mode: str
    ) -> LessonContent:
        """Injects a deliberate error into a real LLM generation for demonstration/test purposes."""
        logger.warning(f"Applying deliberate error mode: '{error_mode}' to generated lesson.")

        if error_mode == "flawed_embeddings":
            lesson.embedding_explanation = (
                "Embeddings are secret passwords that encrypt text so nobody can read it. "
                "Embeddings do not capture any meaning at all, they just count how many letters exist in a word."
            )
        elif error_mode == "missing_vector_db":
            lesson.vector_database_explanation = "Vector databases are not important and we will skip them today."
        elif error_mode == "jargon_overload":
            lesson.what_is_rag = (
                "RAG utilizes approximate nearest neighbors on latent high-dimensional non-Euclidean manifolds "
                "orchestrated via dot-product cosine affinity matrices without explanatory semantics."
            )
        elif error_mode == "flawed_workflow":
            lesson.step_by_step_workflow = "Step 1: The AI guesses the answer. Step 2: It retrieves nothing. Step 3: Done."

        return lesson
