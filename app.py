"""Self-Evaluating Lesson Content Generator - Interactive Streamlit Dashboard.

A production-style GenAI agentic application featuring LangGraph orchestration,
strict PASS/FAIL evaluation rubric, persistent SQLite memory, self-evolution engine,
and controlled deliberate-error demo modes.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from evaluation.schemas import (
    CheckpointResult,
    EvaluationReport,
    EvaluationStatus,
    LessonContent,
    RejectionLogEntry,
)
from services.lesson_service import LessonContentService
from services.llm_service import (
    DeterministicMockLLMProvider,
    GeminiProvider,
    OpenAICompatibleProvider,
    get_llm_provider,
)
from utils.exporters import (
    export_full_run_report_markdown,
    export_lesson_markdown,
    export_rejection_log_json,
)

# Page Configuration
st.set_page_config(
    page_title="Self-Evaluating Lesson Content Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .status-card {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 5px solid;
    }
    .status-pass {
        background-color: #ECFDF5;
        border-color: #10B981;
        color: #065F46;
    }
    .status-fail {
        background-color: #FEF2F2;
        border-color: #EF4444;
        color: #991B1B;
    }
    .status-progress {
        background-color: #EFF6FF;
        border-color: #3B82F6;
        color: #1E40AF;
    }
    .badge-pass {
        background-color: #10B981;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-fail {
        background-color: #EF4444;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .metric-container {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_configured_service(provider_type: str, model_name: str, api_key: str, error_mode: Optional[str]) -> LessonContentService:
    """Instantiates the lesson service based on sidebar parameters."""
    if provider_type == "mock":
        provider = DeterministicMockLLMProvider(deliberate_error_mode=error_mode)
    elif provider_type == "openai":
        provider = OpenAICompatibleProvider(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model=model_name or "gpt-4o-mini",
        )
    elif provider_type == "gemini":
        provider = GeminiProvider(
            api_key=api_key or os.getenv("GEMINI_API_KEY"),
            model=model_name or "gemini-1.5-flash",
        )
    elif provider_type == "groq":
        provider = OpenAICompatibleProvider(
            api_key=api_key or os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            model=model_name or "llama-3.3-70b-versatile",
        )
    elif provider_type == "ollama":
        provider = OpenAICompatibleProvider(
            api_key="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            model=model_name or "llama3.1",
        )
    else:
        provider = DeterministicMockLLMProvider(deliberate_error_mode=error_mode)

    return LessonContentService(llm_provider=provider)


# ==========================================
# SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=64)
    st.title("System Controls")
    st.caption("GenAI Engineer Take-Home Assignment")

    st.subheader("1. LLM Provider")
    provider_option = st.selectbox(
        "Select Provider",
        options=["mock", "openai", "gemini", "groq", "ollama"],
        index=0,
        help=(
            "Use 'mock' for 100% deterministic, instant, zero-key testing and offline demo. "
            "Select 'openai' or 'gemini' to execute with real foundation models."
        ),
    )

    api_key_input = ""
    model_input = ""
    if provider_option != "mock":
        default_model = "gpt-4o-mini" if provider_option == "openai" else "gemini-1.5-flash"
        if provider_option == "groq":
            default_model = "llama-3.3-70b-versatile"
        elif provider_option == "ollama":
            default_model = "llama3.1"

        model_input = st.text_input("Model Name", value=default_model)
        if provider_option != "ollama":
            api_key_input = st.text_input(
                f"{provider_option.upper()} API Key",
                type="password",
                help=f"Leave empty to read from {provider_option.upper()}_API_KEY environment variable.",
            )

    st.divider()

    st.subheader("2. Workflow Rules")
    max_retries = st.slider("Max Regeneration Attempts", min_value=1, max_value=3, value=2)

    st.divider()

    st.subheader("3. Video Demo / Test Mode")
    demo_mode_active = st.checkbox("Enable Deliberate Error Injection", value=False)
    selected_error_mode = None

    if demo_mode_active:
        st.warning("Demo Mode: Deliberate error will be introduced on Attempt 1 to demonstrate evaluator rejection & auto-regeneration.")
        selected_error_mode = st.selectbox(
            "Select Deliberate Flaw",
            options=[
                ("flawed_embeddings", "Flawed Embeddings (Defined as passwords without meaning)"),
                ("missing_vector_db", "Missing Vector Database (Section intentionally skipped)"),
                ("jargon_overload", "Jargon Overload (Complex mathematical manifold terms)"),
                ("flawed_workflow", "Flawed Workflow (Non-sequential guessing logic)"),
            ],
            format_func=lambda x: x[1],
        )[0]
    else:
        st.success("Production Mode: Generates high-quality compliant content.")

    st.divider()
    st.markdown("**Version Tracking:**")
    st.caption("Prompt Version: `v1.2` | Rubric Version: `v1.0`")


# Initialize Session State
if "workflow_state" not in st.session_state:
    st.session_state.workflow_state = None
if "run_in_progress" not in st.session_state:
    st.session_state.run_in_progress = False


# Instantiate Service
service = get_configured_service(
    provider_type=provider_option,
    model_name=model_input,
    api_key=api_key_input,
    error_mode=selected_error_mode,
)

# Header Section
st.markdown('<div class="main-header">🎓 Self-Evaluating Lesson Content Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Production-grade agentic content generation with independent PASS/FAIL evaluation, '
    'feedback-driven regeneration loop, SQLite memory, and self-evolution.</div>',
    unsafe_allow_html=True,
)


# Tabs Navigation
tab_studio, tab_lesson, tab_eval, tab_rejections, tab_memory, tab_export = st.tabs([
    "🚀 Live Studio & Execution",
    "📖 Generated Lesson",
    "⚖️ Evaluator Audit Dashboard",
    "🔁 Rejection & Regeneration Trail",
    "🧠 Persistent Memory & Evolution",
    "💾 Export & Downloads",
])


# ==========================================
# TAB 1: STUDIO & EXECUTION
# ==========================================
with tab_studio:
    st.subheader("Educational Requirements")

    col_input1, col_input2 = st.columns([1.2, 1])

    with col_input1:
        topic_input = st.text_input(
            "Educational Topic",
            value="Introduction to RAG (Retrieval-Augmented Generation)",
            help="Topic assigned for evaluation.",
        )

    with col_input2:
        audience_input = st.text_area(
            "Target Learner Persona",
            value=(
                "A 12th-grade graduate from India with limited English vocabulary, "
                "from a non-English-medium background, with zero prior knowledge of AI or RAG."
            ),
            height=68,
        )

    run_btn = st.button("⚡ Generate & Self-Evaluate Lesson", type="primary", use_container_width=True)

    if run_btn:
        st.session_state.run_in_progress = True
        progress_bar = st.progress(0, text="Initializing LangGraph agentic workflow...")
        status_container = st.empty()

        def stream_callback(node_name: str, output: Dict[str, Any]):
            msg = output.get("status_message", f"Executing {node_name}...")
            if node_name == "initialize_run":
                progress_bar.progress(15, text=f"[1/5] {msg}")
            elif node_name == "generate_lesson":
                progress_bar.progress(40, text=f"[2/5] {msg}")
            elif node_name == "evaluate_lesson":
                progress_bar.progress(70, text=f"[3/5] {msg}")
            elif node_name == "prepare_regeneration":
                progress_bar.progress(85, text=f"[REGENERATING] {msg}")
            elif "finalize" in node_name:
                progress_bar.progress(100, text=f"[COMPLETE] {msg}")

        try:
            with st.spinner("Agentic workflow is executing..."):
                final_state = service.run_lesson_workflow(
                    topic=topic_input,
                    target_audience=audience_input,
                    max_retries=max_retries,
                    deliberate_error_mode=selected_error_mode,
                    step_callback=stream_callback,
                )
                st.session_state.workflow_state = final_state
                st.session_state.run_in_progress = False
                st.success("Workflow completed successfully!")
        except Exception as exc:
            st.session_state.run_in_progress = False
            st.error(f"Workflow execution failed: {exc}")

    # Display Current State Metrics
    state = st.session_state.workflow_state
    if state:
        st.divider()
        st.subheader("Current Execution Summary")

        final_status = state.get("final_status", "UNKNOWN")
        current_attempt = state.get("current_attempt", 1)
        eval_result: Optional[EvaluationReport] = state.get("evaluation_result")
        rejection_logs: List[RejectionLogEntry] = state.get("rejection_log", [])

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            st.markdown(
                f"""
                <div class="metric-container">
                    <span style="font-size:0.85rem; color:#6B7280;">Final Status</span><br/>
                    <strong style="font-size:1.3rem; color:{'#10B981' if final_status == 'PASSED' else '#EF4444'};">
                        {final_status}
                    </strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_m2:
            st.markdown(
                f"""
                <div class="metric-container">
                    <span style="font-size:0.85rem; color:#6B7280;">Total Attempts</span><br/>
                    <strong style="font-size:1.3rem; color:#1E3A8A;">{current_attempt}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_m3:
            passed_chk = eval_result.passed_checkpoints if eval_result else 0
            total_chk = eval_result.total_checkpoints if eval_result else 0
            st.markdown(
                f"""
                <div class="metric-container">
                    <span style="font-size:0.85rem; color:#6B7280;">Checkpoints Passed</span><br/>
                    <strong style="font-size:1.3rem; color:#1E3A8A;">{passed_chk} / {total_chk}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_m4:
            st.markdown(
                f"""
                <div class="metric-container">
                    <span style="font-size:0.85rem; color:#6B7280;">Rejections Recorded</span><br/>
                    <strong style="font-size:1.3rem; color:#D97706;">{len(rejection_logs)}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if final_status == "PASSED":
            st.markdown(
                f"""
                <div class="status-card status-pass">
                    <strong>PASS CONFIRMATION:</strong> The lesson successfully passed 100% of the mandatory checkpoints on attempt #{current_attempt}.
                    It meets all grounding, pedagogical clarity, Indian learner appropriateness, and structural criteria.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="status-card status-fail">
                    <strong>FAILURE TERMINATION:</strong> The lesson failed mandatory evaluation checkpoints after exhausting {current_attempt} attempt(s).
                    See Evaluator Audit and Rejection Trail tabs for specific evidence and failure reasons.
                </div>
                """,
                unsafe_allow_html=True,
            )


# ==========================================
# TAB 2: GENERATED LESSON
# ==========================================
with tab_lesson:
    if not st.session_state.workflow_state:
        st.info("No lesson generated yet. Go to 'Live Studio & Execution' tab and click 'Generate & Self-Evaluate Lesson'.")
    else:
        lesson: Optional[LessonContent] = st.session_state.workflow_state.get("generated_lesson")
        if lesson:
            st.header(lesson.title)
            st.caption(f"Topic: {lesson.topic} | Target: {lesson.target_audience}")

            # Highlight Boxes
            col_hl1, col_hl2 = st.columns(2)
            with col_hl1:
                st.info(f"**Practical Indian Example:**\n\n{lesson.real_life_example[:260]}...")
            with col_hl2:
                st.success(f"**Everyday Analogy:**\n\n{lesson.simple_practical_analogy[:260]}...")

            st.divider()

            # Render Full Markdown Content
            st.markdown(lesson.to_markdown())


# ==========================================
# TAB 3: EVALUATOR AUDIT DASHBOARD
# ==========================================
with tab_eval:
    if not st.session_state.workflow_state:
        st.info("No evaluation data available. Run the workflow first.")
    else:
        eval_report: Optional[EvaluationReport] = st.session_state.workflow_state.get("evaluation_result")
        if eval_report:
            st.subheader(f"Evaluation Audit Report (Attempt #{eval_report.attempt_number})")
            st.markdown(f"**Verdict:** {eval_report.summary_verdict}")

            # Dimension Score Pills
            st.write("**Dimension Status Breakdown:**")
            dim_cols = st.columns(len(eval_report.dimension_scores))
            for col, (dim, status) in zip(dim_cols, eval_report.dimension_scores.items()):
                with col:
                    badge_class = "badge-pass" if status == "PASS" else "badge-fail"
                    short_dim = dim.split(".")[1].strip() if "." in dim else dim
                    st.markdown(
                        f"<div style='text-align:center;'><small>{short_dim}</small><br/>"
                        f"<span class='{badge_class}'>{status}</span></div>",
                        unsafe_allow_html=True,
                    )

            st.divider()

            # Checkpoint Filter
            filter_choice = st.radio(
                "Filter Checkpoints:",
                options=["All Checkpoints", "Failed Only", "Passed Only"],
                horizontal=True,
            )

            for chk in eval_report.checkpoints:
                if filter_choice == "Failed Only" and chk.status != EvaluationStatus.FAIL:
                    continue
                if filter_choice == "Passed Only" and chk.status != EvaluationStatus.PASS:
                    continue

                badge = (
                    '<span class="badge-pass">PASS</span>'
                    if chk.status == EvaluationStatus.PASS
                    else '<span class="badge-fail">FAIL</span>'
                )

                with st.expander(f"[{chk.checkpoint_id}] {chk.checkpoint_name} — {chk.dimension.value}", expanded=(chk.status == EvaluationStatus.FAIL)):
                    st.markdown(f"**Status:** {badge}", unsafe_allow_html=True)
                    st.markdown(f"**Mandatory:** {'Yes' if chk.is_mandatory else 'No'}")
                    st.markdown(f"**Reason:** {chk.reason}")

                    st.markdown("**Evaluator Evidence / Quote:**")
                    st.code(chk.evidence, language="markdown")

                    if chk.suggested_improvement:
                        st.warning(f"**Required Improvement:** {chk.suggested_improvement}")


# ==========================================
# TAB 4: REJECTION & REGENERATION TRAIL
# ==========================================
with tab_rejections:
    if not st.session_state.workflow_state:
        st.info("No rejection trail available yet. Run the workflow first.")
    else:
        rejections: List[RejectionLogEntry] = st.session_state.workflow_state.get("rejection_log", [])

        if not rejections:
            st.success("🎉 No rejections recorded! The lesson passed all evaluation checkpoints on the very first attempt.")
        else:
            st.subheader(f"Rejection & Regeneration Audit Trail ({len(rejections)} Recorded)")
            st.markdown(
                "This log transparently documents every failed attempt, the exact evidence captured by the evaluator, "
                "the targeted feedback delivered back to the generator, and the specific corrections made."
            )

            for entry in rejections:
                st.markdown(f"### ❌ Attempt #{entry.attempt_number} (Evaluator Rejected)")
                st.caption(f"Summary: {entry.lesson_version_summary}")

                col_rej1, col_rej2 = st.columns([1, 1.2])

                with col_rej1:
                    st.markdown("**Failed Checkpoints:**")
                    for fc in entry.failed_checkpoints:
                        st.markdown(f"- 🔴 `{fc}`")

                    st.markdown("**Failure Reasons:**")
                    for r in entry.failure_reasons:
                        st.markdown(f"- {r}")

                with col_rej2:
                    st.markdown("**Feedback Sent to Generator Agent:**")
                    st.info(entry.feedback_sent_to_generator)

                    st.markdown("**Changes Made in Follow-Up Attempt:**")
                    st.write(entry.changes_made_during_regeneration or "Targeted fix applied during next iteration.")

                st.divider()


# ==========================================
# TAB 5: PERSISTENT MEMORY & EVOLUTION
# ==========================================
with tab_memory:
    st.subheader("Persistent SQLite Memory & Historical Runs")

    past_runs = service.get_past_runs()

    if not past_runs:
        st.info("No previous runs recorded in the database yet.")
    else:
        st.markdown(f"**Total Historical Runs Stored:** `{len(past_runs)}`")
        runs_table = []
        for r in past_runs[:10]:
            runs_table.append({
                "Run ID": r["run_id"][:8] + "...",
                "Topic": r["topic"],
                "Final Status": r["final_status"],
                "Total Attempts": r["total_attempts"],
                "Prompt Ver": r["prompt_version"],
                "Rubric Ver": r["rubric_version"],
                "Date": r["created_at"][:19],
            })
        st.dataframe(runs_table, use_container_width=True)

    st.divider()

    st.subheader("🧬 Self-Evolution Insights (Learned Guidelines)")
    st.caption("Active guidelines derived from historical failures and pre-emptively fed into future generation prompts.")

    insights = service.get_evolution_insights()
    for ins in insights:
        with st.expander(f"[{ins['insight_id']}] Topic: {ins['topic_category']} (Applied {ins['applied_count']} times)"):
            st.markdown(f"**Recurring Issue Identified:** {ins['recurring_issue']}")
            st.markdown(f"**Proactive Guideline Rule:**")
            st.success(ins['guideline_rule'])
            st.caption(f"Created: {ins['created_at'][:19]} | Prompt Version: {ins['prompt_version']}")

    st.divider()

    st.subheader("🛡️ Controlled Rubric Evolution Proposals")
    st.caption(
        "To prevent gaming and quality degradation, the core rubric is FROZEN. "
        "Any rubric modification must be submitted as a reviewable proposal."
    )

    with st.form("propose_rubric_form"):
        prop_change = st.text_input("Proposed Rubric Modification / New Checkpoint")
        prop_rationale = st.text_area("Justification & Pedagogical Rationale")
        submit_prop = st.form_submit_button("Submit Rubric Proposal for Review")

        if submit_prop:
            if prop_change and prop_rationale:
                prop_id = service.submit_rubric_proposal(prop_change, prop_rationale)
                st.success(f"Proposal `{prop_id}` submitted successfully with status: REVIEW_REQUIRED.")
            else:
                st.error("Please fill in both the proposed modification and rationale.")

    proposals = service.get_rubric_proposals()
    if proposals:
        st.write("**Submitted Proposals:**")
        st.dataframe(proposals, use_container_width=True)


# ==========================================
# TAB 6: EXPORT & DOWNLOADS
# ==========================================
with tab_export:
    st.subheader("Download Artifacts")
    if not st.session_state.workflow_state:
        st.info("Run the workflow first to generate downloadable artifacts.")
    else:
        state = st.session_state.workflow_state
        lesson: Optional[LessonContent] = state.get("generated_lesson")
        eval_report: Optional[EvaluationReport] = state.get("evaluation_result")
        rejections: List[RejectionLogEntry] = state.get("rejection_log", [])
        final_status = state.get("final_status", "UNKNOWN")

        if lesson and eval_report:
            lesson_md = export_lesson_markdown(lesson)
            rejection_json = export_rejection_log_json(rejections)
            full_audit_md = export_full_run_report_markdown(
                topic=state.get("topic", "Introduction to RAG"),
                target_audience=state.get("target_audience", "12th-grade graduate"),
                final_status=final_status,
                attempts_count=state.get("current_attempt", 1),
                lesson=lesson,
                eval_report=eval_report,
                rejection_logs=rejections,
            )

            col_d1, col_d2, col_d3 = st.columns(3)

            with col_d1:
                st.download_button(
                    label="📄 Download Lesson (.md)",
                    data=lesson_md,
                    file_name="RAG_Lesson_Final.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            with col_d2:
                st.download_button(
                    label="🔁 Download Rejection Log (.json)",
                    data=rejection_json,
                    file_name="rejection_log.json",
                    mime="application/json",
                    use_container_width=True,
                )

            with col_d3:
                st.download_button(
                    label="📊 Download Full Audit Report (.md)",
                    data=full_audit_md,
                    file_name="complete_audit_report.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            st.divider()
            st.subheader("Preview Full Audit Report")
            st.text_area("Audit Report Preview", value=full_audit_md, height=400)
