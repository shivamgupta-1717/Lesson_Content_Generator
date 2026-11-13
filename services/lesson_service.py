"""High-level Orchestration Service for Lesson Generation and Evaluation.

Provides a clean facade for UI and automated testing to execute workflows,
stream live stage transitions, and manage persistent memory.
"""

from typing import Any, Callable, Dict, List, Optional
from memory.database import init_database
from memory.evolution import SelfEvolutionEngine
from memory.repository import LessonRepository
from services.llm_service import BaseLLMProvider, get_llm_provider
from utils.logger import logger
from workflow.graph import create_lesson_graph
from workflow.nodes import WorkflowNodeController
from workflow.state import LessonState


class LessonContentService:
    """Service facade coordinating the LangGraph workflow, repository, and evolution engine."""

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        db_path: Optional[str] = None,
    ):
        self.db_path = db_path
        init_database(db_path=db_path)
        self.llm_provider = llm_provider or get_llm_provider()
        self.repository = LessonRepository(db_path=db_path)
        self.evolution_engine = SelfEvolutionEngine(db_path=db_path)

    def run_lesson_workflow(
        self,
        topic: str = "Introduction to RAG (Retrieval-Augmented Generation)",
        target_audience: str = "12th-grade graduate from India with limited English vocabulary and no prior AI knowledge",
        max_retries: int = 2,
        deliberate_error_mode: Optional[str] = None,
        step_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Executes the complete self-evaluating generation and evaluation workflow.

        Args:
            topic: Topic string.
            target_audience: Student persona description.
            max_retries: Retry threshold (default 2).
            deliberate_error_mode: Demo/testing flag for controlled error injection.
            step_callback: Optional callable hook invoked at each state transition.

        Returns:
            Dict[str, Any]: Final workflow state containing lesson, evaluation, and rejection trail.
        """
        logger.info(f"LessonContentService: Executing workflow for topic='{topic}'")

        controller = WorkflowNodeController(
            repository=self.repository,
            evolution_engine=self.evolution_engine,
        )
        # Ensure generator and evaluator share configured LLM provider
        controller.generator.llm_provider = self.llm_provider
        controller.evaluator.llm_provider = self.llm_provider

        graph = create_lesson_graph(controller=controller)

        initial_state: LessonState = {
            "topic": topic,
            "target_audience": target_audience,
            "max_retries": max_retries,
            "error_injection_mode": deliberate_error_mode,
        }

        # If step_callback is provided, we can stream through nodes
        if step_callback:
            final_state = dict(initial_state)
            for event in graph.stream(initial_state):
                for node_name, node_output in event.items():
                    logger.info(f"Step Event [{node_name}]: {node_output.get('status_message', '')}")
                    final_state.update(node_output)
                    step_callback(node_name, node_output)
            return final_state
        else:
            return graph.invoke(initial_state)

    def get_past_runs(self) -> List[Dict[str, Any]]:
        """Retrieves list of past runs."""
        return self.repository.get_all_runs()

    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a specific past run."""
        return self.repository.get_run_details(run_id)

    def get_evolution_insights(self) -> List[Dict[str, Any]]:
        """Retrieves persistent learned guidelines."""
        return self.evolution_engine.get_all_insights()

    def get_rubric_proposals(self) -> List[Dict[str, Any]]:
        """Retrieves rubric enhancement proposals."""
        return self.evolution_engine.get_all_rubric_proposals()

    def submit_rubric_proposal(self, change: str, rationale: str) -> str:
        """Submits a new reviewable proposal to evolve the rubric without unvetted changes."""
        return self.evolution_engine.propose_rubric_enhancement(change, rationale)
