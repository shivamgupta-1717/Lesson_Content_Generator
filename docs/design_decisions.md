# Technical Design Decisions & Engineering Trade-offs

## 1. Why LangGraph for Workflow Orchestration?

- **Cyclic Feedback Capabilities:** Traditional DAG engines (like standard Airflow or linear LangChain chains) struggle with iterative feedback loops that require conditional re-entry into prior states. LangGraph models stateful cycles natively with explicit conditional branching (`add_conditional_edges`).
- **Typed State Management:** `LessonState` provides a strictly typed dictionary (`TypedDict`) ensuring all nodes receive a predictable, immutable-friendly context across transitions.
- **Observability & Streaming:** LangGraph's event stream allows the Streamlit UI to subscribe to step transitions in real time without polling.

---

## 2. Dual-Layer Evaluation Architecture

- **The Problem with LLM-Only Grading:** Pure LLM evaluators are susceptible to "self-grading bias" (tendency to rate everything 8/10 or overlook missing structural sections) and non-deterministic schema violations.
- **The Solution:** We implemented a two-tier evaluation strategy:
  1. *Deterministic Layer (Python code):* Verifies mandatory field counts, minimum string lengths, glossary dictionary size, question counts, and performs regex scanning against a forbidden machine-learning jargon blacklist.
  2. *Semantic Layer (LLM auditor):* Evaluates nuanced readability, tone for an Indian 12th-grader, analogy accuracy, and factual grounding.
  If a deterministic check fails, it immediately overrides the outcome to `FAIL` regardless of semantic scores.

---

## 3. Pluggable LLM Provider & Deterministic Mock Provider

- **Zero-Key Out-of-the-Box Execution:** Hiring managers and reviewers running the project locally should not be blocked if they do not have a paid OpenAI or Gemini API key.
- **The Deterministic Mock LLM Provider:**
  - Provides rich, pedagogically verified canned responses for RAG lessons and evaluations.
  - Dynamically simulates deliberate errors (flawed embeddings, missing vector DB, jargon overload, flawed workflow) and faithfully mimics feedback-driven regeneration.
  - Enables **100% test pass rate in CI/CD environments** with zero external network dependencies or API costs.
- **Multi-Provider Flexibility:** For production runs, users can select OpenAI (`gpt-4o-mini`, `gpt-4o`), Google Gemini (`gemini-1.5-flash`), Groq, or Ollama without changing a single line of application code.

---

## 4. SQLite Persistent Memory Design

- **Thread-Safe File Persistence:** SQLite requires zero daemon configuration, stores cleanly in `data/lesson_generator.db`, and persists across system reboots.
- **Normalized Schema:**
  - `runs`: High-level run metadata and status.
  - `attempts`: Attempt-level snapshots of lessons and evaluations.
  - `rejection_logs`: Transparent audit log of failures, evidence, and feedback.
  - `evolution_insights`: Persistent guidelines learned from historical failures.
  - `rubric_proposals`: Versioned governance table for proposed rubric modifications.

---

## 5. Controlled Self-Evolution Safety Guardrails

- **The Danger of Uncontrolled Self-Evolution:** In autonomous systems, allowing an agent to rewrite its own rubric inevitably leads to "rubric softening" (the agent lowers the passing threshold to artificially report a 100% pass rate).
- **The Safety Solution:**
  1. *Generator Prompt Evolution:* Safe to evolve automatically. The `SelfEvolutionEngine` analyzes recurring failure patterns and creates proactive guidelines (e.g. "Always introduce embeddings with roll numbers") that are injected into future generator prompts.
  2. *Rubric Standards Frozen:* The core evaluation rubric is strictly frozen. Any proposed rubric modification is written to the `rubric_proposals` table with status `REVIEW_REQUIRED`, ensuring changes must be explicitly reviewed and vetted.
