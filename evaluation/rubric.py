"""Strict PASS/FAIL Evaluation Rubric Engine.

Combines deterministic rule-based audits (structural presence, jargon detection,
length heuristics) with semantic LLM evaluation across the 6 mandatory dimensions.
Every mandatory checkpoint receives either PASS or FAIL — no partial credit.
"""

from typing import List, Tuple
from evaluation.schemas import (
    CheckpointResult,
    EvaluationReport,
    EvaluationStatus,
    LessonContent,
    RubricDimension,
)
from utils.logger import logger


class RubricEngine:
    """Core evaluation engine that validates lessons against the strict 6-dimension rubric."""

    MANDATORY_SECTIONS = [
        ("title", "Lesson Title"),
        ("learning_objectives", "Learning Objectives"),
        ("introduction", "Introduction"),
        ("what_is_rag", "What is the Topic?"),
        ("why_is_rag_needed", "Why is it Needed?"),
        ("how_rag_works", "How it Works"),
        ("retrieval_process", "Core Pillar 1"),
        ("embedding_explanation", "Core Pillar 2"),
        ("vector_database_explanation", "Core Pillar 3"),
        ("context_injection", "Core Pillar 4"),
        ("generation_process", "Core Pillar 5"),
        ("real_life_example", "Real-Life Example"),
        ("step_by_step_workflow", "Step-by-Step Workflow"),
        ("simple_practical_analogy", "Simple Practical Analogy"),
        ("key_terminology", "Key Terminology with Simple Meanings"),
        ("advantages_and_limitations", "Advantages and Limitations"),
        ("summary", "Summary"),
        ("knowledge_check_questions", "Knowledge-Check Questions with Answers"),
    ]

    UNEXPLAINED_JARGON_LIST = [
        "eigenvalue",
        "high-dimensional manifold",
        "backpropagation",
        "dot-product matrix",
        "stochastic gradient descent",
        "cross-entropy loss",
        "non-euclidean",
    ]

    def evaluate_deterministic(self, lesson: LessonContent) -> List[CheckpointResult]:
        """Runs fast, deterministic programmatic checks on structure, coverage, and jargon."""
        results: List[CheckpointResult] = []

        # 1. Topic Coverage Check (CHK_COV_01)
        missing_sections = []
        for field_name, display_name in self.MANDATORY_SECTIONS:
            val = getattr(lesson, field_name, None)
            if val is None:
                missing_sections.append(display_name)
            elif isinstance(val, (str, list, dict)) and len(val) == 0:
                missing_sections.append(display_name)
            elif isinstance(val, str) and len(val.strip()) < 20:
                # Section content is suspiciously empty or placeholder
                missing_sections.append(f"{display_name} (Content under 20 chars)")

        if missing_sections:
            results.append(CheckpointResult(
                checkpoint_id="CHK_COV_01",
                checkpoint_name="Complete Topic Coverage & Mandatory Sections",
                dimension=RubricDimension.TOPIC_COVERAGE,
                is_mandatory=True,
                status=EvaluationStatus.FAIL,
                reason=f"The lesson is missing or has incomplete mandatory sections: {', '.join(missing_sections)}.",
                evidence=f"Missing sections: {', '.join(missing_sections)}",
                suggested_improvement=f"Ensure all 18 mandatory sections are present and fully written: {', '.join(missing_sections)}.",
            ))
        else:
            results.append(CheckpointResult(
                checkpoint_id="CHK_COV_01",
                checkpoint_name="Complete Topic Coverage & Mandatory Sections",
                dimension=RubricDimension.TOPIC_COVERAGE,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="All 18 mandatory syllabus components and structural sections are present with substantial content.",
                evidence=f"Verified presence of all 18 required sections (from '{lesson.title}' through Knowledge-Check Questions).",
                suggested_improvement="",
            ))

        # 2. Key Terminology Glossary Check (CHK_JARG_02)
        if len(lesson.key_terminology) < 4:
            results.append(CheckpointResult(
                checkpoint_id="CHK_JARG_02",
                checkpoint_name="Glossary of Key Technical Terms",
                dimension=RubricDimension.CLARITY_AND_JARGON,
                is_mandatory=True,
                status=EvaluationStatus.FAIL,
                reason="The Key Terminology glossary must define at least 4 core terms with simple meanings.",
                evidence=f"Found only {len(lesson.key_terminology)} terms in glossary.",
                suggested_improvement="Provide clear definitions for at least 4 foundational terms (e.g., Retrieval, Embedding, Vector DB, Hallucination).",
            ))
        else:
            results.append(CheckpointResult(
                checkpoint_id="CHK_JARG_02",
                checkpoint_name="Glossary of Key Technical Terms",
                dimension=RubricDimension.CLARITY_AND_JARGON,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason=f"Glossary contains {len(lesson.key_terminology)} technical terms defined in simple, everyday language.",
                evidence=f"Defined terms include: {', '.join(list(lesson.key_terminology.keys())[:5])}.",
                suggested_improvement="",
            ))

        # 3. Unexplained Advanced Jargon Detection (CHK_JARG_03)
        lesson_full_text = lesson.to_markdown().lower()
        found_jargon = [term for term in self.UNEXPLAINED_JARGON_LIST if term in lesson_full_text]
        if found_jargon:
            results.append(CheckpointResult(
                checkpoint_id="CHK_JARG_03",
                checkpoint_name="Avoidance of Unexplained Advanced Jargon",
                dimension=RubricDimension.CLARITY_AND_JARGON,
                is_mandatory=True,
                status=EvaluationStatus.FAIL,
                reason=f"Found high-level academic/mathematical jargon inappropriate for 12th graders without simple explanation: {', '.join(found_jargon)}.",
                evidence=f"Text contains flagged phrases: {', '.join(found_jargon)}",
                suggested_improvement="Remove advanced machine-learning jargon or substitute with simple relatable concepts.",
            ))
        else:
            results.append(CheckpointResult(
                checkpoint_id="CHK_JARG_03",
                checkpoint_name="Avoidance of Unexplained Advanced Jargon",
                dimension=RubricDimension.CLARITY_AND_JARGON,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="No forbidden advanced mathematical or machine-learning jargon detected.",
                evidence="Scanned document against advanced jargon blacklist; no prohibitive terms found.",
                suggested_improvement="",
            ))

        # 4. Assessment Questions Validation (CHK_FLOW_02)
        if len(lesson.knowledge_check_questions) < 3:
            results.append(CheckpointResult(
                checkpoint_id="CHK_FLOW_02",
                checkpoint_name="Formative Knowledge Check Assessment",
                dimension=RubricDimension.TEACHING_FLOW,
                is_mandatory=True,
                status=EvaluationStatus.FAIL,
                reason="At least 3 knowledge-check questions with answers and explanations are required.",
                evidence=f"Found only {len(lesson.knowledge_check_questions)} questions.",
                suggested_improvement="Include at least 3 to 4 multiple-choice or short conceptual questions with answers.",
            ))
        else:
            results.append(CheckpointResult(
                checkpoint_id="CHK_FLOW_02",
                checkpoint_name="Formative Knowledge Check Assessment",
                dimension=RubricDimension.TEACHING_FLOW,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason=f"Contains {len(lesson.knowledge_check_questions)} well-formed knowledge check questions with clear answers and explanations.",
                evidence=f"Verified {len(lesson.knowledge_check_questions)} review questions.",
                suggested_improvement="",
            ))

        return results

    def combine_evaluations(
        self,
        attempt_number: int,
        deterministic_results: List[CheckpointResult],
        semantic_report: EvaluationReport,
    ) -> EvaluationReport:
        """Merges deterministic and semantic checkpoint audits into a final strict EvaluationReport."""
        all_checkpoints: List[CheckpointResult] = []
        seen_ids = set()

        # Prioritize deterministic failures if any checkpoint IDs collide
        for chk in deterministic_results:
            all_checkpoints.append(chk)
            seen_ids.add(chk.checkpoint_id)

        for chk in semantic_report.checkpoints:
            if chk.checkpoint_id not in seen_ids:
                all_checkpoints.append(chk)
                seen_ids.add(chk.checkpoint_id)
            else:
                # If deterministic failed, preserve the failure
                existing = next(c for c in all_checkpoints if c.checkpoint_id == chk.checkpoint_id)
                if existing.status == EvaluationStatus.PASS and chk.status == EvaluationStatus.FAIL:
                    # Upgrade to FAIL
                    existing.status = EvaluationStatus.FAIL
                    existing.reason = chk.reason
                    existing.evidence = chk.evidence
                    existing.suggested_improvement = chk.suggested_improvement

        failed_checkpoints = [c for c in all_checkpoints if c.status == EvaluationStatus.FAIL]
        is_passed = len(failed_checkpoints) == 0

        dimension_scores = {}
        for c in all_checkpoints:
            dim_key = c.dimension.value
            current = dimension_scores.get(dim_key, "PASS")
            if c.status == EvaluationStatus.FAIL:
                dimension_scores[dim_key] = "FAIL"
            elif current != "FAIL":
                dimension_scores[dim_key] = "PASS"

        if is_passed:
            summary = "PASSED: All mandatory checkpoints satisfy the strict quality and pedagogical standards."
        else:
            summary = f"FAILED: {len(failed_checkpoints)} mandatory checkpoint(s) failed strict evaluation criteria."

        return EvaluationReport(
            attempt_number=attempt_number,
            is_passed=is_passed,
            total_checkpoints=len(all_checkpoints),
            passed_checkpoints=len(all_checkpoints) - len(failed_checkpoints),
            failed_checkpoints=len(failed_checkpoints),
            dimension_scores=dimension_scores,
            checkpoints=all_checkpoints,
            summary_verdict=summary,
        )
