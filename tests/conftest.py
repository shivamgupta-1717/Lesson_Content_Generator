"""Pytest test configuration and fixtures."""

import os
import sys
import tempfile
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.schemas import LessonContent
from memory.database import init_database
from memory.evolution import SelfEvolutionEngine
from memory.repository import LessonRepository
from services.llm_service import DeterministicMockLLMProvider


@pytest.fixture
def temp_db():
    """Provides a fresh temporary SQLite database path for isolated test execution."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_database(db_path=path)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


@pytest.fixture
def repository(temp_db):
    """Provides a LessonRepository pointing to the isolated test database."""
    return LessonRepository(db_path=temp_db)


@pytest.fixture
def evolution_engine(temp_db):
    """Provides a SelfEvolutionEngine pointing to the isolated test database."""
    return SelfEvolutionEngine(db_path=temp_db)


@pytest.fixture
def mock_llm_provider():
    """Provides a clean DeterministicMockLLMProvider."""
    return DeterministicMockLLMProvider()


@pytest.fixture
def sample_valid_lesson(mock_llm_provider) -> LessonContent:
    """Returns a valid, high-quality LessonContent."""
    return mock_llm_provider.generate_structured(
        prompt="Generate lesson on Introduction to RAG",
        response_model=LessonContent,
    )
