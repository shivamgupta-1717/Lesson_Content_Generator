"""Tests for LangGraph agentic workflow routing and state transitions."""

import pytest
from evaluation.schemas import CheckpointResult, EvaluationReport, EvaluationStatus, LessonContent, RubricDimension
from workflow.nodes import WorkflowNodeController
from workflow.state import LessonState


def test_decision_router_routes_to_success_when_all_pass():
    """Verifies that router branches to 'finalize_success' when all checkpoints pass."""
    controller = WorkflowNodeController()

    report = EvaluationReport(
        attempt_number=1,
        is_passed=True,
        total_checkpoints=6,
        passed_checkpoints=6,
        failed_checkpoints=0,
        summary_verdict="All passed",
    )

    state: LessonState = {
        "current_attempt": 1,
        "max_retries": 2,
        "evaluation_result": report,
    }

    route = controller.decision_router(state)
    assert route == "finalize_success"


def test_decision_router_routes_to_regeneration_when_failed_and_retries_remain():
    """Verifies router branches to 'prepare_regeneration' when checkpoints fail and attempts < 1 + max_retries."""
    controller = WorkflowNodeController()

    report = EvaluationReport(
        attempt_number=1,
        is_passed=False,
        total_checkpoints=6,
        passed_checkpoints=5,
        failed_checkpoints=1,
        summary_verdict="Failed",
    )

    # Attempt 1 failed, max_retries = 2 (allowed: 1, 2, 3)
    state: LessonState = {
        "current_attempt": 1,
        "max_retries": 2,
        "evaluation_result": report,
    }

    route = controller.decision_router(state)
    assert route == "prepare_regeneration"


def test_decision_router_routes_to_exhausted_when_retries_depleted():
    """Verifies router branches to 'finalize_exhausted' when retries are exhausted."""
    controller = WorkflowNodeController()

    report = EvaluationReport(
        attempt_number=3,
        is_passed=False,
        total_checkpoints=6,
        passed_checkpoints=5,
        failed_checkpoints=1,
        summary_verdict="Failed",
    )

    # Attempt 3 failed with max_retries = 2 (total allowed attempts = 3)
    state: LessonState = {
        "current_attempt": 3,
        "max_retries": 2,
        "evaluation_result": report,
    }

    route = controller.decision_router(state)
    assert route == "finalize_exhausted"
