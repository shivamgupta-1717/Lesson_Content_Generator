"""Tests for SQLite Persistent Memory and Repository layer."""

from evaluation.schemas import EvaluationStatus, RejectionLogEntry
from memory.database import init_database
from memory.repository import LessonRepository


def test_sqlite_persistence_across_connections(temp_db, sample_valid_lesson, mock_llm_provider):
    """Verifies that saved runs, attempts, and logs persist reliably across new connection instances."""
    repo1 = LessonRepository(db_path=temp_db)
    run_id = "RUN_TEST_PERSIST_001"

    # 1. Record Run Start
    repo1.record_run_start(
        run_id=run_id,
        topic="Introduction to RAG",
        target_audience="12th-grade graduate from India",
    )

    # 2. Record Attempt
    from agents.evaluator import LessonEvaluatorAgent
    evaluator = LessonEvaluatorAgent(llm_provider=mock_llm_provider)
    report = evaluator.evaluate(sample_valid_lesson, "12th-grade graduate", 1)
    repo1.record_attempt(run_id=run_id, attempt_number=1, lesson=sample_valid_lesson, eval_report=report)

    # 3. Complete Run
    repo1.complete_run(run_id=run_id, final_status="PASSED", total_attempts=1)

    # 4. Simulate application restart by creating a new repository instance pointing to the same DB
    repo2 = LessonRepository(db_path=temp_db)
    retrieved = repo2.get_run_details(run_id)

    assert retrieved is not None
    assert retrieved["run_id"] == run_id
    assert retrieved["final_status"] == "PASSED"
    assert retrieved["total_attempts"] == 1
    assert len(retrieved["attempts"]) == 1
    assert retrieved["attempts"][0]["lesson_title"] == sample_valid_lesson.title


def test_rejection_log_persistence(temp_db):
    """Verifies rejection log entries are saved and retrieved accurately."""
    repo = LessonRepository(db_path=temp_db)
    run_id = "RUN_REJ_001"
    repo.record_run_start(run_id, "Introduction to RAG", "12th-grade graduate")

    log_entry = RejectionLogEntry(
        attempt_number=1,
        lesson_version_summary="Initial flawed version",
        failed_checkpoints=["CHK_ACC_01 (Factual Accuracy)"],
        failure_reasons=["Embeddings defined as passwords"],
        evaluator_evidence=["Embeddings are secret passwords..."],
        feedback_sent_to_generator="Fix embedding explanation to use numbers and semantic similarity.",
        changes_made_during_regeneration="Rewriting embeddings with roll numbers analogy.",
        final_evaluation_result=EvaluationStatus.FAIL,
    )

    repo.record_rejection_log(run_id=run_id, entry=log_entry)

    details = repo.get_run_details(run_id)
    assert len(details["rejection_logs"]) == 1
    assert "CHK_ACC_01" in details["rejection_logs"][0]["failed_checkpoints"]
    assert "secret passwords" in details["rejection_logs"][0]["evaluator_evidence"]
