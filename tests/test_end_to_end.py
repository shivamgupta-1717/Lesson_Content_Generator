"""End-to-End integration tests for the Self-Evaluating Lesson Content Generator."""

import pytest
from evaluation.schemas import EvaluationReport, EvaluationStatus
from services.lesson_service import LessonContentService
from services.llm_service import DeterministicMockLLMProvider


def test_end_to_end_clean_pass_on_first_attempt(temp_db):
    """Scenario 1: Full workflow execution where lesson passes on Attempt 1 without regeneration."""
    provider = DeterministicMockLLMProvider()
    service = LessonContentService(llm_provider=provider, db_path=temp_db)

    result = service.run_lesson_workflow(
        topic="Introduction to RAG (Retrieval-Augmented Generation)",
        target_audience="12th-grade graduate from India with limited English",
        max_retries=2,
    )

    assert result["final_status"] == "PASSED"
    assert result["current_attempt"] == 1
    assert len(result["rejection_log"]) == 0
    assert result["evaluation_result"].is_passed is True
    assert result["evaluation_result"].failed_checkpoints == 0
    assert len(result["final_lesson_markdown"]) > 500


def test_end_to_end_deliberate_error_regeneration_and_pass(temp_db):
    """Scenario 2 (Deliberate-Error Demonstration):

    - Attempt 1 introduces a deliberate flaw (flawed embeddings).
    - Evaluator catches the flaw and rejects the lesson.
    - System records rejection and feeds targeted failure evidence back to generator.
    - Generator fixes the flaw on Attempt 2.
    - Evaluator passes the regenerated lesson.
    - Final status is PASSED with complete rejection audit trail!
    """
    provider = DeterministicMockLLMProvider(deliberate_error_mode="flawed_embeddings")
    service = LessonContentService(llm_provider=provider, db_path=temp_db)

    result = service.run_lesson_workflow(
        topic="Introduction to RAG (Retrieval-Augmented Generation)",
        target_audience="12th-grade graduate from India with limited English",
        max_retries=2,
        deliberate_error_mode="flawed_embeddings",
    )

    assert result["final_status"] == "PASSED"
    assert result["current_attempt"] == 2
    assert len(result["rejection_log"]) == 1

    rejection = result["rejection_log"][0]
    assert rejection.attempt_number == 1
    assert any("CHK_ACC_01" in fc for fc in rejection.failed_checkpoints)
    assert "secret passwords" in str(rejection.evaluator_evidence)
    assert len(rejection.feedback_sent_to_generator) > 20

    # Verify attempt 2 lesson resolved the error
    assert "secret passwords" not in result["generated_lesson"].embedding_explanation.lower()


class PersistentFailingMockLLM(DeterministicMockLLMProvider):
    """Adversarial mock provider that perpetually produces failing evaluations to test retry exhaustion."""

    def _build_mock_evaluation(self, prompt: str):
        report = super()._build_mock_evaluation(prompt)
        # Force a failure
        for chk in report.checkpoints:
            if chk.checkpoint_id == "CHK_ACC_01":
                chk.status = EvaluationStatus.FAIL
                chk.reason = "Persistent ungrounded claim that refuses to resolve."
        report.is_passed = False
        report.failed_checkpoints = 1
        report.passed_checkpoints = report.total_checkpoints - 1
        return report


def test_end_to_end_max_retries_exhaustion(temp_db):
    """Scenario 3: Max Retries Exhaustion:

    Verifies that when a lesson repeatedly fails, the loop strictly terminates at max_retries = 2
    (3 attempts total) and marks the run as FAILED without infinite loops or false passes.
    """
    provider = PersistentFailingMockLLM()
    service = LessonContentService(llm_provider=provider, db_path=temp_db)

    result = service.run_lesson_workflow(
        topic="Introduction to RAG",
        target_audience="12th-grade graduate",
        max_retries=2,
    )

    assert result["final_status"] == "FAILED"
    # Total attempts = 1 initial + 2 retries = 3
    assert result["current_attempt"] == 3
    # 2 intermediate rejections + 1 final exhausted rejection log entry = 3
    assert len(result["rejection_log"]) == 3
    assert result["evaluation_result"].is_passed is False
