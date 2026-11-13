"""Unit tests for the Lesson Evaluator Agent and Rubric Engine."""

import pytest
from agents.evaluator import LessonEvaluatorAgent
from evaluation.rubric import RubricEngine
from evaluation.schemas import EvaluationStatus, LessonContent
from services.llm_service import DeterministicMockLLMProvider


def test_evaluator_passes_compliant_lesson(sample_valid_lesson):
    """Verifies that a well-formed lesson passes all rubric checkpoints."""
    provider = DeterministicMockLLMProvider()
    evaluator = LessonEvaluatorAgent(llm_provider=provider)

    report = evaluator.evaluate(
        lesson=sample_valid_lesson,
        target_audience="12th-grade graduate from India",
        attempt_number=1,
    )

    assert report.is_passed is True
    assert report.failed_checkpoints == 0
    assert report.passed_checkpoints == report.total_checkpoints
    assert len(report.checkpoints) >= 6


def test_evaluator_catches_flawed_embeddings(sample_valid_lesson):
    """Deliberate-Error Test Case: Verifies evaluator catches and rejects flawed embeddings explanation."""
    provider = DeterministicMockLLMProvider(deliberate_error_mode="flawed_embeddings")
    evaluator = LessonEvaluatorAgent(llm_provider=provider)

    # Corrupt embedding explanation
    sample_valid_lesson.embedding_explanation = (
        "Embeddings are secret passwords that encrypt text so nobody can read it. "
        "Embeddings do not capture any meaning at all."
    )

    report = evaluator.evaluate(
        lesson=sample_valid_lesson,
        target_audience="12th-grade graduate from India",
        attempt_number=1,
    )

    assert report.is_passed is False
    assert report.failed_checkpoints > 0

    acc_fail = next((c for c in report.checkpoints if c.checkpoint_id == "CHK_ACC_01"), None)
    assert acc_fail is not None
    assert acc_fail.status == EvaluationStatus.FAIL
    assert len(acc_fail.evidence) > 0
    assert len(acc_fail.suggested_improvement) > 0


def test_evaluator_catches_missing_vector_db(sample_valid_lesson):
    """Deliberate-Error Test Case: Verifies evaluator catches omission of vector database section."""
    provider = DeterministicMockLLMProvider(deliberate_error_mode="missing_vector_db")
    evaluator = LessonEvaluatorAgent(llm_provider=provider)

    sample_valid_lesson.vector_database_explanation = "Vector databases are not important and we will skip them today."

    report = evaluator.evaluate(
        lesson=sample_valid_lesson,
        target_audience="12th-grade graduate from India",
        attempt_number=1,
    )

    assert report.is_passed is False
    cov_fail = next((c for c in report.checkpoints if c.checkpoint_id == "CHK_COV_01"), None)
    assert cov_fail is not None
    assert cov_fail.status == EvaluationStatus.FAIL


def test_deterministic_rubric_detects_unexplained_advanced_jargon(sample_valid_lesson):
    """Verifies that the deterministic check flags forbidden high-level machine learning jargon."""
    engine = RubricEngine()

    sample_valid_lesson.introduction += " Note that we optimize cross-entropy loss along the high-dimensional manifold."

    results = engine.evaluate_deterministic(sample_valid_lesson)
    jarg_chk = next((c for c in results if c.checkpoint_id == "CHK_JARG_03"), None)

    assert jarg_chk is not None
    assert jarg_chk.status == EvaluationStatus.FAIL
    assert "high-dimensional manifold" in jarg_chk.evidence


def test_deterministic_rubric_detects_empty_glossary(sample_valid_lesson):
    """Verifies that having an insufficient glossary fails the deterministic check."""
    engine = RubricEngine()
    sample_valid_lesson.key_terminology = {"RAG": "Retrieval Augmented Generation"}  # Less than 4

    results = engine.evaluate_deterministic(sample_valid_lesson)
    term_chk = next((c for c in results if c.checkpoint_id == "CHK_JARG_02"), None)

    assert term_chk is not None
    assert term_chk.status == EvaluationStatus.FAIL
