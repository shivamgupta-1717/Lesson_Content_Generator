"""Services package for LLM provider access and lesson orchestration."""

from services.llm_service import (
    BaseLLMProvider,
    DeterministicMockLLMProvider,
    GeminiProvider,
    OpenAICompatibleProvider,
    get_llm_provider,
)

__all__ = [
    "BaseLLMProvider",
    "DeterministicMockLLMProvider",
    "GeminiProvider",
    "OpenAICompatibleProvider",
    "get_llm_provider",
    "LessonContentService",
]


def __getattr__(name: str):
    if name == "LessonContentService":
        from services.lesson_service import LessonContentService
        return LessonContentService
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
