"""Repository layer for persisting and retrieving runs, evaluation history, and rejection logs."""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from evaluation.schemas import (
    CheckpointResult,
    EvaluationReport,
    LessonContent,
    RejectionLogEntry,
    SelfEvolutionInsight,
)
from memory.database import get_db_connection
from utils.logger import logger


class LessonRepository:
    """Manages SQLite persistence for agent runs, attempts, and rejection history."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    def record_run_start(
        self,
        run_id: str,
        topic: str,
        target_audience: str,
        prompt_version: str = "v1.0",
        rubric_version: str = "v1.0",
    ) -> None:
        """Records the initial creation of a new workflow run."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO runs (run_id, topic, target_audience, final_status, total_attempts, prompt_version, rubric_version, created_at)
            VALUES (?, ?, ?, 'IN_PROGRESS', 0, ?, ?, ?)
            """,
            (run_id, topic, target_audience, prompt_version, rubric_version, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()

    def record_attempt(
        self,
        run_id: str,
        attempt_number: int,
        lesson: LessonContent,
        eval_report: EvaluationReport,
    ) -> None:
        """Persists a single generation and evaluation attempt."""
        conn = self._conn()
        cursor = conn.cursor()
        attempt_id = str(uuid.uuid4())

        failed_checkpoints = [
            f"{c.checkpoint_id}: {c.checkpoint_name}"
            for c in eval_report.get_failed_checkpoints()
        ]

        cursor.execute(
            """
            INSERT INTO attempts (
                attempt_id, run_id, attempt_number, lesson_title, lesson_json, lesson_markdown,
                eval_report_json, is_passed, failed_checkpoints_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                run_id,
                attempt_number,
                lesson.title,
                lesson.model_dump_json(),
                lesson.to_markdown(),
                eval_report.model_dump_json(),
                1 if eval_report.is_passed else 0,
                json.dumps(failed_checkpoints),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def record_rejection_log(self, run_id: str, entry: RejectionLogEntry) -> None:
        """Saves a rejection log entry for a failed generation attempt."""
        conn = self._conn()
        cursor = conn.cursor()
        log_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO rejection_logs (
                log_id, run_id, attempt_number, failed_checkpoints, failure_reasons,
                evaluator_evidence, feedback_sent, changes_made, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                run_id,
                entry.attempt_number,
                json.dumps(entry.failed_checkpoints),
                json.dumps(entry.failure_reasons),
                json.dumps(entry.evaluator_evidence),
                entry.feedback_sent_to_generator,
                entry.changes_made_during_regeneration,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def complete_run(self, run_id: str, final_status: str, total_attempts: int) -> None:
        """Updates run status to PASSED or FAILED and stamps completion time."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE runs
            SET final_status = ?, total_attempts = ?, completed_at = ?
            WHERE run_id = ?
            """,
            (final_status, total_attempts, datetime.utcnow().isoformat(), run_id),
        )
        conn.commit()
        conn.close()

    def get_all_runs(self) -> List[Dict[str, Any]]:
        """Retrieves list of all past runs with metadata."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs ORDER BY created_at DESC")
        rows = cursor.fetchall()
        runs = [dict(row) for row in rows]
        conn.close()
        return runs

    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Fetches complete run record including attempts and rejection history."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        run_row = cursor.fetchone()
        if not run_row:
            conn.close()
            return None

        result = dict(run_row)

        cursor.execute("SELECT * FROM attempts WHERE run_id = ? ORDER BY attempt_number ASC", (run_id,))
        result["attempts"] = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM rejection_logs WHERE run_id = ? ORDER BY attempt_number ASC", (run_id,))
        result["rejection_logs"] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return result

    def get_historical_failures_for_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Finds failed checkpoints and reasons from past runs matching the topic keyword."""
        conn = self._conn()
        cursor = conn.cursor()
        keyword = f"%{topic.split()[0]}%" if topic else "%RAG%"
        cursor.execute(
            """
            SELECT a.run_id, a.attempt_number, a.failed_checkpoints_json, a.created_at
            FROM attempts a
            JOIN runs r ON a.run_id = r.run_id
            WHERE r.topic LIKE ? AND a.is_passed = 0
            ORDER BY a.created_at DESC LIMIT 10
            """,
            (keyword,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
