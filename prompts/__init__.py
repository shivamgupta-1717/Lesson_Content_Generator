"""Prompt templates for generator and evaluator agents."""

from prompts.generator_prompt import GENERATOR_SYSTEM_PROMPT, build_generator_prompt
from prompts.evaluator_prompt import EVALUATOR_SYSTEM_PROMPT, build_evaluator_prompt

__all__ = [
    "GENERATOR_SYSTEM_PROMPT",
    "build_generator_prompt",
    "EVALUATOR_SYSTEM_PROMPT",
    "build_evaluator_prompt",
]
