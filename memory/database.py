"""SQLite Database initialization and schema management for persistent memory.

Ensures real cross-session persistence across application restarts.
"""

import os
import sqlite3
from typing import Optional
from utils.logger import logger

DEFAULT_DB_PATH = os.path.join("data", "lesson_generator.db")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates a thread-safe connection to the SQLite database.

    Args:
        db_path: Optional custom path to SQLite database.

    Returns:
        sqlite3.Connection: Database connection with row factory enabled.
    """
    path = db_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: Optional[str] = None) -> None:
    """Initializes tables for runs, attempts, rejection logs, and self-evolution insights."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Runs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            target_audience TEXT NOT NULL,
            final_status TEXT NOT NULL,
            total_attempts INTEGER NOT NULL,
            prompt_version TEXT DEFAULT 'v1.0',
            rubric_version TEXT DEFAULT 'v1.0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # 2. Attempts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            attempt_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            lesson_title TEXT,
            lesson_json TEXT NOT NULL,
            lesson_markdown TEXT NOT NULL,
            eval_report_json TEXT NOT NULL,
            is_passed BOOLEAN NOT NULL,
            failed_checkpoints_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
    """)

    # 3. Rejection Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rejection_logs (
            log_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            failed_checkpoints TEXT NOT NULL,
            failure_reasons TEXT NOT NULL,
            evaluator_evidence TEXT NOT NULL,
            feedback_sent TEXT NOT NULL,
            changes_made TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
    """)

    # 4. Evolution Insights Table (Learned from failures across runs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evolution_insights (
            insight_id TEXT PRIMARY KEY,
            topic_category TEXT NOT NULL,
            recurring_issue TEXT NOT NULL,
            guideline_rule TEXT NOT NULL,
            prompt_version TEXT DEFAULT 'v1.0',
            rubric_version TEXT DEFAULT 'v1.0',
            applied_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. Rubric Proposals Table (Audit log for reviewable rubric evolution without unapproved changes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rubric_proposals (
            proposal_id TEXT PRIMARY KEY,
            rubric_version TEXT NOT NULL,
            proposed_checkpoint_change TEXT NOT NULL,
            rationale TEXT NOT NULL,
            status TEXT DEFAULT 'REVIEW_REQUIRED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully with persistent tables.")
