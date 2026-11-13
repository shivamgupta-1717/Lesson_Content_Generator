"""Data models and schemas for Lesson Generation, Evaluation, and Rejection Tracking.

Built with Pydantic v2 for robust validation, serialization, and typing integrity.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class EvaluationStatus(str, Enum):
    """Evaluation status for checkpoints and overall evaluation."""
    PASS = "PASS"
    FAIL = "FAIL"


class RubricDimension(str, Enum):
    """The 6 mandatory evaluation rubric dimensions."""
    ACCURACY_AND_GROUNDING = "A. Accuracy and Grounding"
    BEGINNER_FRIENDLY_LANGUAGE = "B. Beginner-Friendly Language"
    TEACHING_THROUGH_EXAMPLES = "C. Teaching Through Examples"
    CLARITY_AND_JARGON = "D. Clarity and Jargon"
    TOPIC_COVERAGE = "E. Topic Coverage"
    TEACHING_FLOW = "F. Teaching Flow"


class LessonSection(BaseModel):
    """An individual section within a generated lesson."""
    section_number: int = Field(..., description="Section index from 1 to 18")
    title: str = Field(..., description="Section header title")
    content: str = Field(..., description="Detailed markdown content of the section")


class LessonContent(BaseModel):
    """Structured representation of a generated educational lesson."""
    topic: str = Field(..., description="Educational topic name")
    target_audience: str = Field(..., description="Target learner profile")
    title: str = Field(..., description="Overall lesson title")
    learning_objectives: List[str] = Field(default_factory=list, description="Clear, bulleted learning goals")
    introduction: str = Field(..., description="Introductory opening")
    what_is_rag: str = Field(..., description="Definition and foundational meaning")
    why_is_rag_needed: str = Field(..., description="Problem statement and motivation")
    how_rag_works: str = Field(..., description="High-level mechanics overview")
    retrieval_process: str = Field(..., description="How information is fetched from external storage")
    embedding_explanation: str = Field(..., description="Simple explanation of embeddings/vectors")
    vector_database_explanation: str = Field(..., description="Simple explanation of vector databases")
    context_injection: str = Field(..., description="How retrieved context is supplied to the prompt")
    generation_process: str = Field(..., description="How the LLM produces the final response")
    real_life_example: str = Field(..., description="Relatable Indian real-life scenario")
    step_by_step_workflow: str = Field(..., description="Step 1 to N sequence of operations")
    simple_practical_analogy: str = Field(..., description="Intuitive everyday analogy (e.g. open book exam)")
    key_terminology: Dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary mapping technical terms to simple plain-English meanings"
    )
    advantages_and_limitations: str = Field(..., description="Benefits and boundary limitations")
    summary: str = Field(..., description="Wrap-up recap of core concepts")
    knowledge_check_questions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Questions with explanations and correct answers"
    )

    def to_markdown(self) -> str:
        """Serializes the entire structured lesson into clean, beautifully formatted Markdown."""
        md_lines: List[str] = [
            f"# {self.title}\n",
            f"> **Topic:** {self.topic}  ",
            f"> **Target Learner:** {self.target_audience}\n",
            "---\n",
            "## 1. Learning Objectives\n",
        ]
        for obj in self.learning_objectives:
            md_lines.append(f"- {obj}")
        md_lines.append("\n---\n")

        topic_clean = self.topic.strip()
        is_rag = "rag" in topic_clean.lower() or "retrieval" in topic_clean.lower()
        is_react = "react" in topic_clean.lower()

        sec_3 = f"3. What is {topic_clean}?" if not is_rag else "3. What is RAG (Retrieval-Augmented Generation)?"
        sec_4 = f"4. Why is {topic_clean} Needed?" if not is_rag else "4. Why is RAG Needed?"
        sec_5 = f"5. How {topic_clean} Works (High-Level Overview)" if not is_rag else "5. How RAG Works (High-Level Overview)"

        if is_react:
            sec_6 = "6. Components (Reusable LEGO UI Bricks)"
            sec_7 = "7. JSX (Writing HTML Tags Inside JavaScript)"
            sec_8 = "8. State and Props (Memory and Instructions)"
            sec_9 = "9. The Virtual DOM (The Fast Memory Scratchpad)"
            sec_10 = "10. Component Lifecycle & Hooks"
        elif is_rag:
            sec_6 = "6. The Retrieval Process (Finding Information)"
            sec_7 = "7. Embeddings Explained Simply"
            sec_8 = "8. Vector Databases (The Smart Library)"
            sec_9 = "9. Context Injection (Passing Clues to the AI)"
            sec_10 = "10. The Generation Process (Crafting the Answer)"
        else:
            sec_6 = f"6. Core Pillar 1 of {topic_clean}"
            sec_7 = f"7. Core Pillar 2 of {topic_clean}"
            sec_8 = f"8. Core Pillar 3 of {topic_clean}"
            sec_9 = f"9. Core Pillar 4 of {topic_clean}"
            sec_10 = f"10. Core Pillar 5 of {topic_clean}"

        sections = [
            ("2. Introduction", self.introduction),
            (sec_3, self.what_is_rag),
            (sec_4, self.why_is_rag_needed),
            (sec_5, self.how_rag_works),
            (sec_6, self.retrieval_process),
            (sec_7, self.embedding_explanation),
            (sec_8, self.vector_database_explanation),
            (sec_9, self.context_injection),
            (sec_10, self.generation_process),
            ("11. Real-Life Indian Everyday Example", self.real_life_example),
            ("12. Step-by-Step Workflow", self.step_by_step_workflow),
            ("13. Simple Practical Analogy", self.simple_practical_analogy),
        ]

        for sec_title, content in sections:
            md_lines.append(f"## {sec_title}\n\n{content}\n\n---\n")

        # Key Terminology
        md_lines.append("## 14. Key Terminology (Words with Simple Meanings)\n")
        md_lines.append("| Technical Word | Simple Everyday Meaning |")
        md_lines.append("| :--- | :--- |")
        for term, meaning in self.key_terminology.items():
            md_lines.append(f"| **{term}** | {meaning} |")
        md_lines.append("\n---\n")

        md_lines.append(f"## 15. Advantages and Limitations\n\n{self.advantages_and_limitations}\n\n---\n")
        md_lines.append(f"## 16. Summary & Key Takeaways\n\n{self.summary}\n\n---\n")

        # Knowledge Check
        md_lines.append("## 17. Knowledge-Check Questions\n")
        for i, qa in enumerate(self.knowledge_check_questions, 1):
            q = qa.get("question", "")
            a = qa.get("answer", "")
            exp = qa.get("explanation", "")
            options = qa.get("options")
            md_lines.append(f"**Q{i}: {q}**")
            if isinstance(options, dict):
                for opt_k, opt_v in options.items():
                    md_lines.append(f"- ({opt_k}) {opt_v}")
            elif isinstance(options, list):
                for opt in options:
                    md_lines.append(f"- {opt}")
            if a:
                md_lines.append(f"- *Answer:* {a}")
            if exp:
                md_lines.append(f"- *Why:* {exp}")
            md_lines.append("")

        return "\n".join(md_lines)


class CheckpointResult(BaseModel):
    """Evaluation result for an individual rubric checkpoint. Strict PASS or FAIL."""
    checkpoint_id: str = Field(..., description="Unique checkpoint ID, e.g., CHK_ACC_01")
    checkpoint_name: str = Field(..., description="Human-readable title of the checkpoint")
    dimension: RubricDimension = Field(..., description="Rubric dimension category")
    is_mandatory: bool = Field(default=True, description="Whether passing is strictly mandatory")
    status: EvaluationStatus = Field(..., description="Strict PASS or FAIL outcome")
    reason: str = Field(..., description="Clear explanation for the PASS/FAIL outcome")
    evidence: str = Field(..., description="Exact quoted excerpt or concrete evidence from the lesson")
    suggested_improvement: str = Field(
        default="",
        description="Actionable guidance to fix the checkpoint if status is FAIL"
    )

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> str:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if "PASS" in v_upper:
                return "PASS"
            if "FAIL" in v_upper:
                return "FAIL"
        return v

    @field_validator("dimension", mode="before")
    @classmethod
    def normalize_dimension(cls, v: Any) -> str:
        if isinstance(v, str):
            v_upper = v.upper()
            if "ACCURACY" in v_upper or "GROUNDING" in v_upper:
                return RubricDimension.ACCURACY_AND_GROUNDING.value
            if "BEGINNER" in v_upper or "LANGUAGE" in v_upper:
                return RubricDimension.BEGINNER_FRIENDLY_LANGUAGE.value
            if "EXAMPLE" in v_upper:
                return RubricDimension.TEACHING_THROUGH_EXAMPLES.value
            if "JARGON" in v_upper or "CLARITY" in v_upper:
                return RubricDimension.CLARITY_AND_JARGON.value
            if "COVERAGE" in v_upper:
                return RubricDimension.TOPIC_COVERAGE.value
            if "FLOW" in v_upper:
                return RubricDimension.TEACHING_FLOW.value
        return v


class EvaluationReport(BaseModel):
    """Comprehensive evaluation report aggregated across all checkpoints."""
    attempt_number: int = Field(default=1, description="Current attempt number (1, 2, or 3)")
    is_passed: bool = Field(..., description="True ONLY if 100% of mandatory checkpoints pass")
    total_checkpoints: int = Field(..., description="Total evaluated checkpoints count")
    passed_checkpoints: int = Field(..., description="Count of passed checkpoints")
    failed_checkpoints: int = Field(..., description="Count of failed checkpoints")
    dimension_scores: Dict[str, str] = Field(
        default_factory=dict,
        description="Pass/Fail status by rubric dimension"
    )
    checkpoints: List[CheckpointResult] = Field(
        default_factory=list,
        description="List of individual checkpoint evaluations"
    )
    summary_verdict: str = Field(..., description="High-level narrative verdict")

    @field_validator("is_passed", mode="before")
    @classmethod
    def normalize_is_passed(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in ("true", "pass", "passed", "1")
        return bool(v)

    def get_failed_checkpoints(self) -> List[CheckpointResult]:
        """Returns all checkpoints that resulted in FAIL."""
        return [chk for chk in self.checkpoints if chk.status == EvaluationStatus.FAIL]

    def get_feedback_prompt(self) -> str:
        """Formats actionable feedback for the generator agent."""
        failed = self.get_failed_checkpoints()
        if not failed:
            return "All evaluation checkpoints passed successfully."

        feedback_lines = [
            "CRITICAL: The previous lesson failed the strict evaluation rubric on the following checkpoints.",
            "You MUST specifically revise and address these exact shortcomings without weakening other sections:\n"
        ]
        for chk in failed:
            feedback_lines.append(f"- Checkpoint [{chk.checkpoint_id}] '{chk.checkpoint_name}' (Dimension: {chk.dimension.value}):")
            feedback_lines.append(f"  * Failure Reason: {chk.reason}")
            feedback_lines.append(f"  * Evaluator Evidence: \"{chk.evidence}\"")
            feedback_lines.append(f"  * Required Action: {chk.suggested_improvement}\n")

        return "\n".join(feedback_lines)


class RejectionLogEntry(BaseModel):
    """Detailed record for every failed attempt during generation and evaluation."""
    attempt_number: int = Field(..., description="Attempt number that failed")
    lesson_version_summary: str = Field(..., description="Brief summary of the lesson in this attempt")
    failed_checkpoints: List[str] = Field(default_factory=list, description="IDs and names of failed checkpoints")
    failure_reasons: List[str] = Field(default_factory=list, description="Detailed failure reasons")
    evaluator_evidence: List[str] = Field(default_factory=list, description="Direct citations/quotes")
    feedback_sent_to_generator: str = Field(..., description="Exact feedback instructions passed to generator")
    changes_made_during_regeneration: str = Field(
        default="",
        description="Summary of targeted changes applied in subsequent attempt"
    )
    final_evaluation_result: EvaluationStatus = Field(..., description="Status after this attempt: FAIL")


class SelfEvolutionInsight(BaseModel):
    """Learned pattern from historical failures used to evolve future prompts."""
    insight_id: str = Field(..., description="Unique ID for insight, e.g. INS_001")
    topic_category: str = Field(default="RAG", description="Category or topic")
    recurring_issue: str = Field(..., description="Observed failure trend across multiple runs")
    guideline_rule: str = Field(..., description="Proactive prompt directive to prevent this failure")
    prompt_version: str = Field(default="v1.0", description="Prompt version tracking")
    applied_count: int = Field(default=0, description="How many runs have utilized this insight")
    created_at: str = Field(..., description="ISO 8601 timestamp")
