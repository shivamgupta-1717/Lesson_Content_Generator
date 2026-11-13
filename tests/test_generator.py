"""Unit tests for the Lesson Generator Agent."""

import pytest
from agents.generator import LessonGeneratorAgent
from evaluation.schemas import LessonContent
from services.llm_service import DeterministicMockLLMProvider


def test_generator_produces_all_mandatory_fields(mock_llm_provider):
    """Verifies that the Generator Agent outputs a complete lesson conforming to all 18 sections."""
    agent = LessonGeneratorAgent(llm_provider=mock_llm_provider)
    lesson = agent.generate(
        topic="Introduction to RAG",
        target_audience="12th-grade graduate from India",
    )

    assert isinstance(lesson, LessonContent)
    assert len(lesson.title) > 5
    assert len(lesson.learning_objectives) >= 3
    assert len(lesson.introduction) > 30
    assert len(lesson.what_is_rag) > 30
    assert len(lesson.why_is_rag_needed) > 30
    assert len(lesson.how_rag_works) > 30
    assert len(lesson.retrieval_process) > 30
    assert len(lesson.embedding_explanation) > 30
    assert len(lesson.vector_database_explanation) > 30
    assert len(lesson.context_injection) > 30
    assert len(lesson.generation_process) > 30
    assert len(lesson.real_life_example) > 30
    assert len(lesson.step_by_step_workflow) > 30
    assert len(lesson.simple_practical_analogy) > 30
    assert len(lesson.key_terminology) >= 4
    assert len(lesson.advantages_and_limitations) > 30
    assert len(lesson.summary) > 30
    assert len(lesson.knowledge_check_questions) >= 3


def test_generator_markdown_serialization(sample_valid_lesson):
    """Verifies that the generated lesson properly renders to clean Markdown with headers."""
    md = sample_valid_lesson.to_markdown()
    assert "# Understanding RAG" in md or "# " in md
    assert "Learning Objectives" in md
    assert "Key Terminology" in md
    assert "Knowledge-Check Questions" in md
    assert "Real-Life" in md


def test_generator_applies_deliberate_errors():
    """Verifies that the generator correctly introduces flawed content when demo error mode is set."""
    provider = DeterministicMockLLMProvider()
    agent = LessonGeneratorAgent(llm_provider=provider)

    # 1. Flawed Embeddings
    flawed_lesson = agent.generate(
        topic="Introduction to RAG",
        target_audience="12th-grade graduate from India",
        deliberate_error_mode="flawed_embeddings",
    )
    assert "secret passwords" in flawed_lesson.embedding_explanation.lower()

    # 2. Missing Vector DB
    skipped_db_lesson = agent.generate(
        topic="Introduction to RAG",
        target_audience="12th-grade graduate from India",
        deliberate_error_mode="missing_vector_db",
    )
    assert "skip them today" in skipped_db_lesson.vector_database_explanation.lower()


def test_generator_resolves_error_when_given_feedback():
    """Verifies that when specific failure feedback is provided, the generator corrects the error."""
    provider = DeterministicMockLLMProvider(deliberate_error_mode="flawed_embeddings")
    agent = LessonGeneratorAgent(llm_provider=provider)

    # With feedback passed, the generator should correct the embedding explanation
    regenerated_lesson = agent.generate(
        topic="Introduction to RAG",
        target_audience="12th-grade graduate from India",
        feedback="CRITICAL: The previous lesson failed checkpoint CHK_ACC_01 because embeddings were misdefined as passwords.",
        deliberate_error_mode="flawed_embeddings",
    )

    assert "secret passwords" not in regenerated_lesson.embedding_explanation.lower()
    assert "numbers" in regenerated_lesson.embedding_explanation.lower()
