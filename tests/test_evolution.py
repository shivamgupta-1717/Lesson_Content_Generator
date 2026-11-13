"""Tests for the Self-Evolution Engine and controlled rubric governance."""

from evaluation.schemas import CheckpointResult, EvaluationReport, EvaluationStatus, RubricDimension
from memory.evolution import SelfEvolutionEngine


def test_evolution_engine_seeds_initial_insights(temp_db):
    """Verifies that the evolution engine initializes with standard seed insights."""
    engine = SelfEvolutionEngine(db_path=temp_db)
    insights = engine.get_all_insights()

    assert len(insights) >= 3
    rag_insights = [ins for ins in insights if ins["topic_category"] == "RAG"]
    assert len(rag_insights) >= 3


def test_evolution_engine_learns_from_evaluation_failures(temp_db):
    """Verifies that recurring evaluation failures are analyzed and synthesized into new insights."""
    engine = SelfEvolutionEngine(db_path=temp_db)
    initial_count = len(engine.get_all_insights())

    # Create a failing evaluation report with a new failure pattern
    failed_checkpoint = CheckpointResult(
        checkpoint_id="CHK_TEST_01",
        checkpoint_name="Novel Conceptual Check",
        dimension=RubricDimension.ACCURACY_AND_GROUNDING,
        is_mandatory=True,
        status=EvaluationStatus.FAIL,
        reason="The explanation of chunking lacked overlap considerations.",
        evidence="Chunking was described as cutting papers blindly.",
        suggested_improvement="Always mention chunk overlap to preserve context across boundaries.",
    )

    eval_report = EvaluationReport(
        attempt_number=1,
        is_passed=False,
        total_checkpoints=1,
        passed_checkpoints=0,
        failed_checkpoints=1,
        checkpoints=[failed_checkpoint],
        summary_verdict="Evaluation failed on chunking.",
    )

    engine.analyze_and_record_failures(
        run_id="RUN_LEARN_001",
        eval_report=eval_report,
        topic="RAG Chunking Strategies",
    )

    updated_insights = engine.get_all_insights()
    assert len(updated_insights) == initial_count + 1

    new_insight = next((ins for ins in updated_insights if "Novel Conceptual Check" in ins["recurring_issue"]), None)
    assert new_insight is not None
    assert "chunk overlap" in new_insight["guideline_rule"].lower()


def test_rubric_proposal_governance(temp_db):
    """Verifies that rubric changes require structured proposals rather than uncontrolled automatic mutations."""
    engine = SelfEvolutionEngine(db_path=temp_db)

    proposal_id = engine.propose_rubric_enhancement(
        proposed_change="Add mandatory checkpoint for code snippet verification in technical lessons.",
        rationale="Prevents untested pseudo-code from reaching advanced students.",
    )

    assert proposal_id.startswith("RUB_PROP_")
    proposals = engine.get_all_rubric_proposals()
    assert len(proposals) == 1
    assert proposals[0]["status"] == "REVIEW_REQUIRED"
    assert "code snippet" in proposals[0]["proposed_checkpoint_change"]
