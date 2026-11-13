"""LangGraph Agentic Workflow compilation for the Self-Evaluating Lesson Generator.

Wires together Generator, Evaluator, conditional routing, feedback loops, and persistence.
"""

from typing import Optional
from langgraph.graph import END, START, StateGraph
from workflow.nodes import WorkflowNodeController
from workflow.state import LessonState


def create_lesson_graph(controller: Optional[WorkflowNodeController] = None):
    """Constructs and compiles the full LangGraph state machine workflow.

    Args:
        controller: Optional custom WorkflowNodeController instance.

    Returns:
        CompiledStateGraph: Executable LangGraph workflow.
    """
    node_controller = controller or WorkflowNodeController()

    builder = StateGraph(LessonState)

    # 1. Add Nodes
    builder.add_node("initialize_run", node_controller.initialize_run_node)
    builder.add_node("generate_lesson", node_controller.generate_lesson_node)
    builder.add_node("evaluate_lesson", node_controller.evaluate_lesson_node)
    builder.add_node("prepare_regeneration", node_controller.prepare_regeneration_node)
    builder.add_node("finalize_success", node_controller.finalize_success_node)
    builder.add_node("finalize_exhausted", node_controller.finalize_exhausted_node)

    # 2. Add Standard Flow Edges
    builder.add_edge(START, "initialize_run")
    builder.add_edge("initialize_run", "generate_lesson")
    builder.add_edge("generate_lesson", "evaluate_lesson")

    # 3. Add Conditional Decision Branching
    builder.add_conditional_edges(
        "evaluate_lesson",
        node_controller.decision_router,
        {
            "finalize_success": "finalize_success",
            "prepare_regeneration": "prepare_regeneration",
            "finalize_exhausted": "finalize_exhausted",
        },
    )

    # 4. Add Regeneration Loop Back to Generator
    builder.add_edge("prepare_regeneration", "generate_lesson")

    # 5. Add Terminal Edges
    builder.add_edge("finalize_success", END)
    builder.add_edge("finalize_exhausted", END)

    return builder.compile()
