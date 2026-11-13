"""Workflow State schema for LangGraph agentic orchestration.

Maintains all context across generation, evaluation, conditional routing,
regeneration loops, rejection logs, and finalization.
"""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from evaluation.schemas import EvaluationReport, LessonContent, RejectionLogEntry


class LessonState(TypedDict, total=False):
    """The central state graph schema passed between LangGraph nodes."""

    run_id: str
    topic: str
    target_audience: str
    current_attempt: int
    max_retries: int
    generated_lesson: Optional[LessonContent]
    evaluation_result: Optional[EvaluationReport]
    failed_checkpoints: List[str]
    feedback_history: List[str]
    rejection_log: List[RejectionLogEntry]
    insights_applied: List[str]
    error_injection_mode: Optional[str]
    final_status: str  # "IN_PROGRESS", "PASSED", "FAILED"
    final_lesson_markdown: Optional[str]
    status_message: str
