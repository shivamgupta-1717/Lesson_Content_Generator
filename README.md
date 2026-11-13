# Self-Evaluating Lesson Content Generator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Pydantic v2](https://img.shields.io/badge/validation-Pydantic%20v2-green.svg)](https://docs.pydantic.dev/)
[![Streamlit](https://img.shields.io/badge/frontend-Streamlit-red.svg)](https://streamlit.io/)
[![Tests Passing](https://img.shields.io/badge/tests-20%20passed-brightgreen.svg)](https://github.com/)

An enterprise-grade, agentic content generation and automated pedagogical auditing system. Built for the **GenAI Engineer – Content Systems** take-home assignment, this system demonstrates autonomous generation, independent strict PASS/FAIL evaluation, feedback-based regeneration with guaranteed termination, persistent SQLite memory, and self-evolution mechanisms.

---

## 1. Project Overview & Objective

### 1.1. Core Mission
Basic LLM chatbots generate ungrounded content with high hallucination rates and zero quality guarantees. This project implements a **self-correcting content engine** that:
1. Generates complete, standalone educational lessons tailored to specific learner personas.
2. Independently evaluates generated lessons against a strict **PASS/FAIL rubric** across 6 pedagogical dimensions.
3. Conditionally routes feedback back to the generator for **targeted regeneration** if any mandatory checkpoint fails (maximum 2 retries).
4. Persists execution histories, evaluation outcomes, and rejection logs in **SQLite**.
5. Employs a **controlled self-evolution engine** that learns from failure patterns across runs without compromising evaluation standards.

### 1.2. Assigned Educational Topic & Target Learner
- **Assigned Topic:** *"Introduction to RAG (Retrieval-Augmented Generation)"*
- **Target Learner Profile:** A 12th-grade graduate from India who:
  - Has a limited English vocabulary.
  - Comes from a non-English-medium educational background (Hindi, Tamil, Marathi, Bengali, Telugu, etc.).
  - Has zero prior knowledge of Computer Science, AI, or RAG.
  - Requires simple explanations, short sentences, immediate jargon definitions, and culturally relatable Indian analogies (such as a local Kirana storekeeper's *Bahi-Khata* ledger book and the CBSE *Open-Book Exam*).

---

## 2. Key Features

- **Cyclic Agentic Loop:** Implemented using **LangGraph** (`StateGraph`) with conditional decision branching and a maximum 2-retry termination guarantee.
- **Dual-Layer Evaluation Rubric:**
  - *Layer 1 (Deterministic):* Programmatic verification of all 18 mandatory sections, minimum content lengths, glossary completeness, and regex detection of forbidden machine learning jargon.
  - *Layer 2 (Semantic LLM):* Deep auditing of conceptual correctness, grounding, Indian student accessibility, and absence of hallucinations.
- **Zero-Tolerance Strict Verdicts:** Every checkpoint receives either `PASS` or `FAIL`. No partial credit.
- **Transparent Rejection Trail:** Stores attempt-by-attempt snapshots, exact failure reasons, evaluator quote citations, feedback delivered, and targeted adjustments.
- **Pluggable Multi-Provider LLM Layer:** Out-of-the-box support for:
  - **Deterministic Mock Provider:** 100% deterministic, instant, zero-API-key execution (ideal for local testing and CI/CD).
  - **OpenAI:** `gpt-4o-mini`, `gpt-4o`.
  - **Google Gemini:** `gemini-1.5-flash`, `gemini-1.5-pro`.
  - **Groq:** `llama-3.3-70b-versatile`.
  - **Local Ollama:** `llama3.1`.
- **Persistent SQLite Memory:** Preserves runs, attempts, evaluations, and rejection logs across application reboots in `data/lesson_generator.db`.
- **Controlled Self-Evolution:** Derives proactive generation guidelines from recurring failure patterns while freezing core rubric criteria to prevent standards from being weakened.
- **Modern Streamlit Dashboard:** Interactive 6-tab interface with live workflow streaming, detailed evaluation cards, rejection timelines, memory inspection, and Markdown/JSON export.
- **Deliberate-Error Demo Mode:** Built-in simulation toggle to showcase evaluator rejection and auto-correction live in under 30 seconds.

---

## 3. High-Level Architecture & Workflow

### 3.1. System Architecture
```
┌────────────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend (app.py)                     │
│    [Input Studio]   [Lesson Viewer]   [Audit Cards]   [Rejection Trail]│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                         LessonContentService
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      LangGraph Orchestration Machine                   │
│                                                                        │
│   ┌────────────────┐       ┌─────────────────┐       ┌───────────────┐ │
│   │ initialize_run │ ───>  │ generate_lesson │ ───>  │evaluate_lesson│ │
│   └────────────────┘       └────────▲────────┘       └───────┬───────┘ │
│                                     │                        │         │
│                                     │ Feedback Loop          ▼         │
│                           ┌─────────┴──────────┐   ┌─────────────────┐ │
│                           │prepare_regeneration│<──┤ decision_router │ │
│                           └────────────────────┘   └────────┬────────┘ │
│                                                             │          │
│                              All Checkpoints Pass           │ Exhausted│
│                       ┌─────────────────────────────────────┴────────┐ │
│                       ▼                                              ▼ │
│              ┌──────────────────┐                           ┌────────┴┐│
│              │ finalize_success │                           │ finalize││
│              │  (Status: PASS)  │                           │exhausted││
│              └──────────────────┘                           └─────────┘│
└───────────────────▲─────────────────────────────────────────────▲──────┘
                    │                                             │
                    ▼                                             ▼
       ┌────────────────────────┐                    ┌──────────────────┐
       │ Persistent Memory (DB) │                    │ Pluggable LLM    │
       │ SQLite: runs, attempts,│                    │ OpenAI, Gemini,  │
       │ rejections, insights   │                    │ Groq, Ollama, Mock│
       └────────────────────────┘                    └──────────────────┘
```

---

## 4. Tech Stack & Justifications

| Technology | Role | Justification |
| :--- | :--- | :--- |
| **Python 3.10+** | Core Language | Industry-standard language for AI engineering, typing, and asynchronous workflows. |
| **LangGraph** | Workflow Orchestration | Cyclic state graphs natively support conditional retries and feedback loops unlike linear DAG engines. |
| **Pydantic v2** | Data Contracts & Validation | Guarantees strict type safety, automatic JSON schema serialization, and rigorous runtime validation. |
| **SQLite3** | Persistent Memory | Zero-configuration serverless database that persists runs, attempts, and insights across reboots. |
| **Streamlit** | Interactive Frontend | Fast, reactive Python web dashboard supporting real-time event streaming and artifact downloads. |
| **Pytest** | Testing Framework | Automated testing covering unit checks, deliberate errors, retry exhaustion, and end-to-end flows. |
| **python-dotenv** | Configuration | Clean environment variable isolation ensuring API keys are never hardcoded. |

---

## 5. Project Directory Structure

```
self-evaluating-lesson-generator/
│
├── app.py                         # Streamlit interactive dashboard
├── requirements.txt               # Application dependencies
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules
├── README.md                      # Comprehensive project documentation
│
├── agents/                        # Autonomous Agent definitions
│   ├── __init__.py
│   ├── generator.py               # Lesson Generator Agent (18 sections, Indian analogies)
│   └── evaluator.py               # Independent Lesson Evaluator Agent
│
├── workflow/                      # LangGraph Orchestration
│   ├── __init__.py
│   ├── state.py                   # Typed state schema (LessonState)
│   ├── nodes.py                   # Generation, evaluation, router, and regeneration nodes
│   └── graph.py                   # Compiled state machine graph
│
├── evaluation/                    # Rubric and Schemas
│   ├── __init__.py
│   ├── schemas.py                 # Pydantic models (LessonContent, EvaluationReport, RejectionLog)
│   └── rubric.py                  # Dual-layer deterministic + semantic rubric engine
│
├── memory/                        # SQLite Memory & Evolution
│   ├── __init__.py
│   ├── database.py                # Database connection and schema initialization
│   ├── repository.py              # CRUD repository for runs, attempts, and rejection logs
│   └── evolution.py               # Self-Evolution engine & rubric proposal governance
│
├── prompts/                       # Modular prompt engineering
│   ├── __init__.py
│   ├── generator_prompt.py        # Learner-specific prompts & feedback revision logic
│   └── evaluator_prompt.py        # Strict PASS/FAIL auditing criteria & evidence prompt
│
├── services/                      # Orchestration & LLM service layer
│   ├── __init__.py
│   ├── llm_service.py             # Multi-provider adapter (OpenAI, Gemini, Groq, Ollama, Mock)
│   └── lesson_service.py          # High-level service facade for UI and automated testing
│
├── utils/                         # Utilities
│   ├── __init__.py
│   ├── logger.py                  # Formatted logging setup
│   └── exporters.py               # Markdown and JSON export utilities
│
├── tests/                         # Pytest test suite (20 automated tests)
│   ├── __init__.py
│   ├── conftest.py                # Test fixtures and isolated in-memory DB setups
│   ├── test_generator.py          # Generator unit tests
│   ├── test_evaluator.py          # Evaluator and rubric tests
│   ├── test_memory.py             # SQLite persistence tests across connections
│   ├── test_evolution.py          # Self-evolution and rubric proposal tests
│   ├── test_workflow.py           # Conditional routing and decision node tests
│   └── test_end_to_end.py         # End-to-end integration and deliberate error tests
│
├── docs/                          # Detailed Technical Documentation
│   ├── architecture.md            # System architecture and component breakdown
│   ├── workflow.md                # LangGraph state machine & feedback loop details
│   ├── evaluation_rubric.md       # Complete 6-dimension rubric catalog
│   ├── design_decisions.md        # Engineering trade-offs and safety mechanisms
│   └── video_demo_script.md       # 15–20 minute video presentation script
│
├── data/                          # SQLite persistent database storage
│   └── lesson_generator.db
│
└── outputs/                       # Generated artifacts & sample lessons
    ├── sample_rag_lesson.md       # Production-ready passing RAG lesson
    ├── sample_full_audit_report.md# Comprehensive run audit document
    └── sample_rejection_audit_trail.json # Raw rejection log JSON
```

---

## 6. Installation & Quickstart

### 6.1. Prerequisites
- Python 3.10 or higher.
- Git.

### 6.2. Clone & Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/shivamgupta-1717/Lesson_Content_Generator.git
cd Lesson_Content_Generator

# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Or on Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 6.3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` to configure your preferred provider. By default, `LLM_PROVIDER=mock` is set so you can run the entire application **immediately without an API key**:
```env
# Default provider (instant, deterministic, offline, zero-key)
LLM_PROVIDER=mock

# Or configure OpenAI:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# LLM_MODEL=gpt-4o-mini

# Or configure Google Gemini:
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=AIzaSy...
# LLM_MODEL=gemini-1.5-flash
```

---

## 7. Running the Application

### 7.1. Launch Streamlit UI
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 7.2. Running Programmatically via CLI
You can also run the agentic workflow programmatically from Python:
```python
from services.lesson_service import LessonContentService

service = LessonContentService()
result = service.run_lesson_workflow(
    topic="Introduction to RAG (Retrieval-Augmented Generation)",
    target_audience="A 12th-grade graduate from India with limited English vocabulary",
)

print(f"Final Status: {result['final_status']}")
print(f"Total Attempts: {result['current_attempt']}")
print(f"Markdown Length: {len(result['final_lesson_markdown'])} chars")
```

---

## 8. Demonstration of Deliberate Error & Regeneration

To demonstrate that the system does not simply give a rubber-stamp pass:
1. Open the Streamlit dashboard (`app.py`).
2. In the sidebar, check **"Enable Deliberate Error Injection"**.
3. Select **"Flawed Embeddings"** (or another deliberate flaw).
4. Click **"Generate & Self-Evaluate Lesson"**.
5. **Observe the result:**
   - **Attempt 1:** The generator produces the deliberate flaw (*"Embeddings are secret passwords that do not capture meaning"*).
   - **Evaluator Audit:** Catches the flaw at `CHK_ACC_01 (Factual Accuracy)`, records direct quoted evidence, and issues a strict `FAIL`.
   - **Rejection Log:** Records the failure, evidence, and creates targeted feedback.
   - **Regeneration Loop:** LangGraph routes back to generator with explicit correction instructions.
   - **Attempt 2:** The generator replaces the flawed explanation with the intuitive roll-number analogy.
   - **Re-Audit:** Evaluator passes all 10 checkpoints.
   - **Final Status:** `PASSED` on Attempt #2 with full rejection audit trail visible in Tab 4.

---

## 9. Automated Testing & Verification

The project includes **20 automated tests** across all modules.

Run the test suite:
```bash
python -m pytest tests/ -v
```

### Actual Test Execution Output:
```
tests/test_end_to_end.py::test_end_to_end_clean_pass_on_first_attempt PASSED       [  5%]
tests/test_end_to_end.py::test_end_to_end_deliberate_error_regeneration_and_pass PASSED [ 10%]
tests/test_end_to_end.py::test_end_to_end_max_retries_exhaustion PASSED                [ 15%]
tests/test_evaluator.py::test_evaluator_passes_compliant_lesson PASSED                 [ 20%]
tests/test_evaluator.py::test_evaluator_catches_flawed_embeddings PASSED               [ 25%]
tests/test_evaluator.py::test_evaluator_catches_missing_vector_db PASSED               [ 30%]
tests/test_evaluator.py::test_deterministic_rubric_detects_unexplained_advanced_jargon PASSED [ 35%]
tests/test_evaluator.py::test_deterministic_rubric_detects_empty_glossary PASSED       [ 40%]
tests/test_evolution.py::test_evolution_engine_seeds_initial_insights PASSED          [ 45%]
tests/test_evolution.py::test_evolution_engine_learns_from_evaluation_failures PASSED [ 50%]
tests/test_evolution.py::test_rubric_proposal_governance PASSED                        [ 55%]
tests/test_generator.py::test_generator_produces_all_mandatory_fields PASSED          [ 60%]
tests/test_generator.py::test_generator_markdown_serialization PASSED                  [ 65%]
tests/test_generator.py::test_generator_applies_deliberate_errors PASSED               [ 70%]
tests/test_generator.py::test_generator_resolves_error_when_given_feedback PASSED    [ 75%]
tests/test_memory.py::test_sqlite_persistence_across_connections PASSED                [ 80%]
tests/test_memory.py::test_rejection_log_persistence PASSED                            [ 85%]
tests/test_workflow.py::test_decision_router_routes_to_success_when_all_pass PASSED   [ 90%]
tests/test_workflow.py::test_decision_router_routes_to_regeneration_when_failed_and_retries_remain PASSED [ 95%]
tests/test_workflow.py::test_decision_router_routes_to_exhausted_when_retries_depleted PASSED [100%]

============================= 20 passed in 0.62s ==============================
```

---

## 10. Sample Final Generated RAG Lesson

A complete, production-grade generated lesson is preserved in [`outputs/sample_rag_lesson.md`](outputs/sample_rag_lesson.md).

Key pedagogical highlights from the lesson:
- **Analogy:** CBSE Open-Book Exam (Traditional AI = student forced to memorize everything; RAG AI = student permitted to open textbook).
- **Relatable Indian Example:** Ramesh Uncle running a busy Kirana store in Lucknow, consulting his red *Bahi-Khata* ledger book rather than guessing customer balances.
- **Immediate Definitions:** Technical terms like *Embeddings*, *Vector Database*, and *Context Injection* are demystified using student roll numbers and library shelf catalogs.
- **Glossary Table:** Tabulates technical terms with plain-English everyday equivalents.
- **Knowledge-Check:** 4 formative questions with explanations.

---

## 11. Known Limitations & Future Scope

- **Audio/Multimodal Lesson Delivery:** Future iterations can integrate text-to-speech (TTS) to generate audio explanations in regional Indian languages (Hindi, Tamil, Marathi).
- **Interactive Quiz Sandbox:** Expanding the knowledge-check section into an interactive Streamlit quiz widget with instant scoring.
- **Vectorized Historical Memory:** Utilizing an embedding-based vector database (like Chroma or FAISS) for historical memory retrieval when analyzing thousands of runs across hundreds of educational topics.

---

## 12. GitHub Publishing Instructions

To publish this codebase to your personal GitHub repository:

```bash
# Initialize git repository
git init

# Add all project files
git add .

# Create initial commit
git commit -m "feat: complete self-evaluating lesson content generator with LangGraph, SQLite, and Streamlit"

# Create a new repository on GitHub: https://github.com/new (e.g. 'self-evaluating-lesson-generator')
# Link your local repo to GitHub:
git remote add origin https://github.com/shivamgupta-1717/Lesson_Content_Generator.git
git branch -M main
git push -u origin main
```
