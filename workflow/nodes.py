"""LangGraph Workflow Nodes and Conditional Decision Logic.

Implements generation, evaluation, failure collection, regeneration preparation,
rejection logging, and state finalization.
"""

import uuid
from typing import Any, Dict, List, Literal, Optional
from agents.evaluator import LessonEvaluatorAgent
from agents.generator import LessonGeneratorAgent
from evaluation.schemas import EvaluationStatus, RejectionLogEntry
from memory.evolution import SelfEvolutionEngine
from memory.repository import LessonRepository
from utils.logger import logger
from workflow.state import LessonState


class WorkflowNodeController:
    """Encapsulates node execution logic and state transitions for the LangGraph workflow."""

    def __init__(
        self,
        generator_agent: Optional[LessonGeneratorAgent] = None,
        evaluator_agent: Optional[LessonEvaluatorAgent] = None,
        repository: Optional[LessonRepository] = None,
        evolution_engine: Optional[SelfEvolutionEngine] = None,
    ):
        self.generator = generator_agent or LessonGeneratorAgent()
        self.evaluator = evaluator_agent or LessonEvaluatorAgent()
        self.repository = repository or LessonRepository()
        self.evolution_engine = evolution_engine or SelfEvolutionEngine()

    def initialize_run_node(self, state: LessonState) -> Dict[str, Any]:
        """Node 1: Initializes the run, retrieves persistent insights, and sets up state."""
        run_id = state.get("run_id") or str(uuid.uuid4())
        topic = state.get("topic", "Introduction to RAG (Retrieval-Augmented Generation)")
        target_audience = state.get(
            "target_audience",
            "12th-grade graduate from India with limited English vocabulary and no prior AI knowledge",
        )
        max_retries = state.get("max_retries", 2)
        error_mode = state.get("error_injection_mode")

        logger.info(f"[Node: initialize_run] RunID: {run_id} | Topic: {topic}")

        # Retrieve active evolution insights from persistent SQLite memory
        active_insights = self.evolution_engine.get_active_insights_for_prompt(topic)

        # Record run start in persistent SQLite repository
        self.repository.record_run_start(
            run_id=run_id,
            topic=topic,
            target_audience=target_audience,
            prompt_version=self.evolution_engine.prompt_version,
            rubric_version=self.evolution_engine.rubric_version,
        )

        return {
            "run_id": run_id,
            "topic": topic,
            "target_audience": target_audience,
            "current_attempt": 1,
            "max_retries": max_retries,
            "insights_applied": active_insights,
            "feedback_history": [],
            "rejection_log": [],
            "final_status": "IN_PROGRESS",
            "status_message": "Run initialized. Active memory insights retrieved.",
            "error_injection_mode": error_mode,
        }

    def generate_lesson_node(self, state: LessonState) -> Dict[str, Any]:
        """Node 2: Invokes the Lesson Generator Agent with feedback and evolution insights."""
        topic = state["topic"]
        target_audience = state["target_audience"]
        current_attempt = state.get("current_attempt", 1)
        insights = state.get("insights_applied", [])
        error_mode = state.get("error_injection_mode")

        # Get latest feedback if this is a regeneration attempt
        feedback_list = state.get("feedback_history", [])
        latest_feedback = feedback_list[-1] if feedback_list else None

        logger.info(
            f"[Node: generate_lesson] Attempt #{current_attempt} "
            f"(HasFeedback={latest_feedback is not None}, ErrorMode={error_mode})"
        )

        lesson = self.generator.generate(
            topic=topic,
            target_audience=target_audience,
            feedback=latest_feedback,
            evolution_insights=insights,
            deliberate_error_mode=error_mode if current_attempt == 1 else None,
        )

        return {
            "generated_lesson": lesson,
            "status_message": f"Generated attempt #{current_attempt}: '{lesson.title}'",
        }

    def evaluate_lesson_node(self, state: LessonState) -> Dict[str, Any]:
        """Node 3: Invokes the Lesson Evaluator Agent for independent PASS/FAIL auditing."""
        lesson = state["generated_lesson"]
        target_audience = state["target_audience"]
        current_attempt = state.get("current_attempt", 1)
        run_id = state["run_id"]

        logger.info(f"[Node: evaluate_lesson] Auditing attempt #{current_attempt}")

        eval_report = self.evaluator.evaluate(
            lesson=lesson,
            target_audience=target_audience,
            attempt_number=current_attempt,
        )

        # Persist this attempt in SQLite
        self.repository.record_attempt(
            run_id=run_id,
            attempt_number=current_attempt,
            lesson=lesson,
            eval_report=eval_report,
        )

        failed_checkpoints = [
            f"{c.checkpoint_id}: {c.checkpoint_name}"
            for c in eval_report.get_failed_checkpoints()
        ]

        return {
            "evaluation_result": eval_report,
            "failed_checkpoints": failed_checkpoints,
            "status_message": (
                f"Evaluation complete for attempt #{current_attempt}: "
                f"{'PASSED' if eval_report.is_passed else 'FAILED'} "
                f"({eval_report.passed_checkpoints}/{eval_report.total_checkpoints} passed)"
            ),
        }

    def decision_router(self, state: LessonState) -> Literal["finalize_success", "prepare_regeneration", "finalize_exhausted"]:
        """Conditional Router: Determines whether to finalize, regenerate, or terminate."""
        eval_report = state.get("evaluation_result")
        current_attempt = state.get("current_attempt", 1)
        max_retries = state.get("max_retries", 2)

        if eval_report and eval_report.is_passed:
            logger.info("Conditional Router: ALL checkpoints PASSED -> Routing to finalize_success")
            return "finalize_success"

        # Check retry limit: total attempts allowed = 1 initial + max_retries
        total_allowed_attempts = 1 + max_retries
        if current_attempt < total_allowed_attempts:
            logger.info(
                f"Conditional Router: Evaluation FAILED. Current attempt {current_attempt} < {total_allowed_attempts} "
                "-> Routing to prepare_regeneration"
            )
            return "prepare_regeneration"

        logger.warning(
            f"Conditional Router: Maximum regeneration attempts ({max_retries}) exhausted. "
            "-> Routing to finalize_exhausted"
        )
        return "finalize_exhausted"

    def prepare_regeneration_node(self, state: LessonState) -> Dict[str, Any]:
        """Node 4: Formats failure reasons, builds RejectionLogEntry, and queues next attempt."""
        eval_report = state["evaluation_result"]
        lesson = state["generated_lesson"]
        current_attempt = state.get("current_attempt", 1)
        run_id = state["run_id"]
        rejection_logs = list(state.get("rejection_log", []))
        feedback_history = list(state.get("feedback_history", []))

        feedback_prompt = eval_report.get_feedback_prompt()
        feedback_history.append(feedback_prompt)

        failed = eval_report.get_failed_checkpoints()
        log_entry = RejectionLogEntry(
            attempt_number=current_attempt,
            lesson_version_summary=f"Version #{current_attempt}: {lesson.title}",
            failed_checkpoints=[f"{c.checkpoint_id} ({c.checkpoint_name})" for c in failed],
            failure_reasons=[c.reason for c in failed],
            evaluator_evidence=[c.evidence for c in failed],
            feedback_sent_to_generator=feedback_prompt,
            changes_made_during_regeneration=f"Regenerating to specifically resolve: {', '.join([c.checkpoint_id for c in failed])}",
            final_evaluation_result=EvaluationStatus.FAIL,
        )
        rejection_logs.append(log_entry)

        # Persist rejection log to SQLite
        self.repository.record_rejection_log(run_id=run_id, entry=log_entry)

        next_attempt = current_attempt + 1
        logger.info(f"[Node: prepare_regeneration] Advancing to attempt #{next_attempt}")

        return {
            "current_attempt": next_attempt,
            "feedback_history": feedback_history,
            "rejection_log": rejection_logs,
            "status_message": f"Attempt #{current_attempt} rejected. Queuing regeneration #{next_attempt} with targeted feedback.",
        }

    def finalize_success_node(self, state: LessonState) -> Dict[str, Any]:
        """Node 5: Finalizes successful run, stamps PASS in database, and records metrics."""
        run_id = state["run_id"]
        topic = state["topic"]
        lesson = state["generated_lesson"]
        current_attempt = state.get("current_attempt", 1)

        logger.info(f"[Node: finalize_success] Run {run_id} PASSED after {current_attempt} attempt(s)!")

        # Update SQLite run status to PASSED
        self.repository.complete_run(
            run_id=run_id,
            final_status="PASSED",
            total_attempts=current_attempt,
        )

        # Increment usage metric of active insights
        self.evolution_engine.increment_insight_usage(topic)

        final_md = lesson.to_markdown()

        return {
            "final_status": "PASSED",
            "final_lesson_markdown": final_md,
            "status_message": f"Workflow completed successfully! Lesson PASSED on attempt #{current_attempt}.",
        }

    def finalize_exhausted_node(self, state: LessonState) -> Dict[str, Any]:
        """Node 6: Finalizes run after exhausting retry limit. Never falsely marks as passed!"""
        run_id = state["run_id"]
        topic = state["topic"]
        lesson = state["generated_lesson"]
        current_attempt = state.get("current_attempt", 1)
        eval_report = state["evaluation_result"]
        rejection_logs = list(state.get("rejection_log", []))

        logger.warning(
            f"[Node: finalize_exhausted] Run {run_id} FAILED after exhausting {current_attempt} attempt(s)."
        )

        # Add final rejection log entry
        failed = eval_report.get_failed_checkpoints()
        final_log = RejectionLogEntry(
            attempt_number=current_attempt,
            lesson_version_summary=f"Final Version #{current_attempt}: {lesson.title}",
            failed_checkpoints=[f"{c.checkpoint_id} ({c.checkpoint_name})" for c in failed],
            failure_reasons=[c.reason for c in failed],
            evaluator_evidence=[c.evidence for c in failed],
            feedback_sent_to_generator="Maximum retries reached. Workflow terminated with FAIL status.",
            changes_made_during_regeneration="None (Retry limit reached).",
            final_evaluation_result=EvaluationStatus.FAIL,
        )
        rejection_logs.append(final_log)
        self.repository.record_rejection_log(run_id=run_id, entry=final_log)

        # Update SQLite run status to FAILED
        self.repository.complete_run(
            run_id=run_id,
            final_status="FAILED",
            total_attempts=current_attempt,
        )

        # Register failed patterns into self-evolution engine to learn for future runs
        self.evolution_engine.analyze_and_record_failures(
            run_id=run_id,
            eval_report=eval_report,
            topic=topic,
        )

        final_md = lesson.to_markdown()

        return {
            "final_status": "FAILED",
            "final_lesson_markdown": final_md,
            "rejection_log": rejection_logs,
            "status_message": f"Workflow terminated: Lesson FAILED after maximum attempts ({current_attempt}).",
        }
