"""Export utilities for generating downloadable files in Markdown and JSON formats."""

import json
from typing import Any, Dict, List
from evaluation.schemas import EvaluationReport, LessonContent, RejectionLogEntry


def export_lesson_markdown(lesson: LessonContent) -> str:
    """Exports a structured LessonContent to a clean Markdown document."""
    return lesson.to_markdown()


def export_rejection_log_json(rejection_logs: List[RejectionLogEntry]) -> str:
    """Serializes the list of rejection log entries to formatted JSON."""
    data = [entry.model_dump() for entry in rejection_logs]
    return json.dumps(data, indent=2)


def export_full_run_report_markdown(
    topic: str,
    target_audience: str,
    final_status: str,
    attempts_count: int,
    lesson: LessonContent,
    eval_report: EvaluationReport,
    rejection_logs: List[RejectionLogEntry],
) -> str:
    """Creates a comprehensive audit report document containing the lesson, evaluation, and rejection trail."""
    lines: List[str] = [
        f"# AGENTIC LESSON GENERATION AUDIT REPORT",
        f"**Topic:** {topic}",
        f"**Target Audience:** {target_audience}",
        f"**Final Status:** {final_status}",
        f"**Total Attempts:** {attempts_count}",
        f"**Overall Evaluation:** {'PASSED' if eval_report.is_passed else 'FAILED'}",
        "\n---\n",
        "## EVALUATION SUMMARY",
        f"- Total Checkpoints: {eval_report.total_checkpoints}",
        f"- Passed Checkpoints: {eval_report.passed_checkpoints}",
        f"- Failed Checkpoints: {eval_report.failed_checkpoints}",
        f"- Summary Verdict: {eval_report.summary_verdict}\n",
        "### Checkpoint Breakdown",
        "| ID | Name | Dimension | Status | Reason |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for chk in eval_report.checkpoints:
        status_icon = "PASS" if chk.status == "PASS" else "**FAIL**"
        lines.append(f"| {chk.checkpoint_id} | {chk.checkpoint_name} | {chk.dimension.value} | {status_icon} | {chk.reason} |")

    lines.append("\n---\n")
    lines.append("## REJECTION & REGENERATION LOGS")

    if not rejection_logs:
        lines.append("No rejections occurred. Lesson passed on the first attempt!")
    else:
        for entry in rejection_logs:
            lines.append(f"### Attempt #{entry.attempt_number} (Status: {entry.final_evaluation_result.value})")
            lines.append(f"**Version Summary:** {entry.lesson_version_summary}")
            lines.append("**Failed Checkpoints:**")
            for fc in entry.failed_checkpoints:
                lines.append(f"- {fc}")
            lines.append("\n**Feedback Sent to Generator:**")
            lines.append(f"```\n{entry.feedback_sent_to_generator}\n```")
            if entry.changes_made_during_regeneration:
                lines.append(f"\n**Changes Made in Follow-Up Attempt:**\n{entry.changes_made_during_regeneration}")
            lines.append("\n")

    lines.append("\n---\n")
    lines.append("## FINAL GENERATED LESSON")
    lines.append(lesson.to_markdown())

    return "\n".join(lines)
