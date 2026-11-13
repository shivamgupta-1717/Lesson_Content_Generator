"""Lesson Evaluator Agent.

Performs independent pedagogical and technical audits against the strict 6-dimension rubric.
Combines deterministic programmatic validation with semantic LLM evaluation to ensure
uncompromising quality and zero ungrounded hallucinations.
"""

from typing import Optional
from evaluation.rubric import RubricEngine
from evaluation.schemas import EvaluationReport, LessonContent
from prompts.evaluator_prompt import EVALUATOR_SYSTEM_PROMPT, build_evaluator_prompt
from services.llm_service import BaseLLMProvider, get_llm_provider
from utils.logger import logger


class LessonEvaluatorAgent:
    """Agent that performs independent, strict PASS/FAIL evaluation of educational lessons."""

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        rubric_engine: Optional[RubricEngine] = None,
    ):
        self.llm_provider = llm_provider or get_llm_provider()
        self.rubric_engine = rubric_engine or RubricEngine()

    def evaluate(
        self,
        lesson: LessonContent,
        target_audience: Optional[str] = None,
        attempt_number: int = 1,
    ) -> EvaluationReport:
        """Audits the lesson and produces an EvaluationReport.

        Args:
            lesson: The generated lesson to audit.
            target_audience: Target student persona.
            attempt_number: Current generation attempt index (1, 2, or 3).

        Returns:
            EvaluationReport: Comprehensive strict pass/fail audit.
        """
        audience = target_audience or lesson.target_audience or "12th-grade graduate from India"
        logger.info(
            f"LessonEvaluatorAgent: Starting evaluation for attempt #{attempt_number} "
            f"of lesson '{lesson.title}' (Topic='{lesson.topic}')"
        )

        # 1. Run deterministic checks first (section completeness, jargon scan, glossary check)
        deterministic_results = self.rubric_engine.evaluate_deterministic(lesson)
        det_failures = [c for c in deterministic_results if c.status == "FAIL"]
        logger.info(
            f"Deterministic evaluation complete: {len(deterministic_results)} checks run, "
            f"{len(det_failures)} failures."
        )

        # 2. Run LLM semantic evaluation for conceptual accuracy, grounding, analogies, and tone
        lesson_md = lesson.to_markdown()
        prompt = build_evaluator_prompt(
            lesson_markdown=lesson_md,
            target_audience=audience,
            topic=lesson.topic,
        )

        semantic_report = self.llm_provider.generate_structured(
            prompt=prompt,
            response_model=EvaluationReport,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
        )

        # 3. Combine deterministic and semantic audits into the final strict report
        final_report = self.rubric_engine.combine_evaluations(
            attempt_number=attempt_number,
            deterministic_results=deterministic_results,
            semantic_report=semantic_report,
        )

        logger.info(
            f"LessonEvaluatorAgent: Audit completed. Verdict: {'PASSED' if final_report.is_passed else 'FAILED'} "
            f"({final_report.passed_checkpoints}/{final_report.total_checkpoints} checkpoints passed)"
        )
        return final_report
