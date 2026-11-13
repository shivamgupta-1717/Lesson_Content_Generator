"""Controlled Self-Evolution Mechanism.

Analyzes historical evaluation failures across runs, tracks recurring quality issues,
evolves generator instructions via versioned prompt guidelines, and preserves strict,
unweakened rubric standards through reviewable change proposals.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from evaluation.schemas import EvaluationReport, SelfEvolutionInsight
from memory.database import get_db_connection, init_database
from utils.logger import logger

CURRENT_PROMPT_VERSION = "v1.2"
CURRENT_RUBRIC_VERSION = "v1.0"

DEFAULT_SEED_INSIGHTS = [
    {
        "insight_id": "INS_RAG_001",
        "topic_category": "RAG",
        "recurring_issue": "Embeddings were previously explained as mathematical vectors without intuitive grounding.",
        "guideline_rule": (
            "Always introduce embeddings by comparing them to student roll numbers or library book numbers: "
            "words with similar meanings receive numbers that are physically close together."
        ),
        "prompt_version": "v1.1",
        "applied_count": 5,
    },
    {
        "insight_id": "INS_RAG_002",
        "topic_category": "RAG",
        "recurring_issue": "Non-English-medium students struggle with abstract AI retrieval definitions.",
        "guideline_rule": (
            "Ground the retrieval concept in an everyday Indian cultural context, specifically a local Kirana "
            "store owner (Ramesh Uncle) looking up a credit balance in his red Bahi-Khata ledger."
        ),
        "prompt_version": "v1.1",
        "applied_count": 4,
    },
    {
        "insight_id": "INS_RAG_003",
        "topic_category": "RAG",
        "recurring_issue": "Technical terms (context injection, hallucination) were used before being defined.",
        "guideline_rule": (
            "Never use the term 'Context Injection' without immediately breaking it down into 'Context = background notes' "
            "and 'Injection = passing into the prompt'."
        ),
        "prompt_version": "v1.2",
        "applied_count": 3,
    },
]


class SelfEvolutionEngine:
    """Orchestrates continuous self-improvement across runs while preserving rubric integrity."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        init_database(db_path=db_path)
        self.prompt_version = CURRENT_PROMPT_VERSION
        self.rubric_version = CURRENT_RUBRIC_VERSION
        self._seed_initial_insights()

    def _conn(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    def _seed_initial_insights(self) -> None:
        """Seeds standard pedagogical insights if the evolution table is empty."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM evolution_insights")
        count = cursor.fetchone()["cnt"]

        if count == 0:
            for item in DEFAULT_SEED_INSIGHTS:
                cursor.execute(
                    """
                    INSERT INTO evolution_insights (
                        insight_id, topic_category, recurring_issue, guideline_rule,
                        prompt_version, rubric_version, applied_count, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        item["insight_id"],
                        item["topic_category"],
                        item["recurring_issue"],
                        item["guideline_rule"],
                        item["prompt_version"],
                        self.rubric_version,
                        item["applied_count"],
                        datetime.utcnow().isoformat(),
                    ),
                )
            conn.commit()
            logger.info("Seeded initial Self-Evolution Insights.")
        conn.close()

    def get_active_insights_for_prompt(self, topic: str) -> List[str]:
        """Fetches active improvement directives relevant to the target topic."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT guideline_rule FROM evolution_insights
            WHERE is_active = 1
            ORDER BY applied_count DESC
            LIMIT 5
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return [row["guideline_rule"] for row in rows]

    def increment_insight_usage(self, topic: str) -> None:
        """Increments the application count of active insights used in a run."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE evolution_insights SET applied_count = applied_count + 1 WHERE is_active = 1")
        conn.commit()
        conn.close()

    def analyze_and_record_failures(self, run_id: str, eval_report: EvaluationReport, topic: str) -> None:
        """Analyzes failed checkpoints from a run to detect and register new recurring quality patterns."""
        failed_checkpoints = eval_report.get_failed_checkpoints()
        if not failed_checkpoints:
            logger.info(f"SelfEvolutionEngine: Run {run_id} passed cleanly; no new failure patterns recorded.")
            return

        conn = self._conn()
        cursor = conn.cursor()

        for chk in failed_checkpoints:
            # Check if this failure type already has an insight
            cursor.execute(
                "SELECT insight_id, applied_count FROM evolution_insights WHERE recurring_issue LIKE ?",
                (f"%{chk.checkpoint_name}%",),
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "UPDATE evolution_insights SET applied_count = applied_count + 1 WHERE insight_id = ?",
                    (existing["insight_id"],),
                )
            else:
                new_id = f"INS_DYN_{uuid.uuid4().hex[:6].upper()}"
                directive = (
                    f"PREVENTIVE RULE for '{chk.checkpoint_name}': {chk.suggested_improvement} "
                    f"Ensure compliance with Dimension '{chk.dimension.value}'."
                )
                cursor.execute(
                    """
                    INSERT INTO evolution_insights (
                        insight_id, topic_category, recurring_issue, guideline_rule,
                        prompt_version, rubric_version, applied_count, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
                    """,
                    (
                        new_id,
                        topic[:20],
                        f"Check '{chk.checkpoint_name}' failed with reason: {chk.reason}",
                        directive,
                        self.prompt_version,
                        self.rubric_version,
                        datetime.utcnow().isoformat(),
                    ),
                )
                logger.info(f"SelfEvolutionEngine: Registered new learned insight {new_id}")

        conn.commit()
        conn.close()

    def propose_rubric_enhancement(self, proposed_change: str, rationale: str) -> str:
        """Submits a versioned proposal for rubric evolution without unilaterally weakening standards."""
        conn = self._conn()
        cursor = conn.cursor()
        proposal_id = f"RUB_PROP_{uuid.uuid4().hex[:6].upper()}"

        cursor.execute(
            """
            INSERT INTO rubric_proposals (proposal_id, rubric_version, proposed_checkpoint_change, rationale, status, created_at)
            VALUES (?, ?, ?, ?, 'REVIEW_REQUIRED', ?)
            """,
            (proposal_id, self.rubric_version, proposed_change, rationale, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
        logger.info(f"SelfEvolutionEngine: Submitted rubric proposal {proposal_id} for review.")
        return proposal_id

    def get_all_insights(self) -> List[Dict[str, Any]]:
        """Returns all persistent insights with usage metrics."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evolution_insights ORDER BY applied_count DESC, created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_rubric_proposals(self) -> List[Dict[str, Any]]:
        """Returns all submitted rubric proposals."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rubric_proposals ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
