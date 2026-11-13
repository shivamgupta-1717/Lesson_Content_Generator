# 15–20 Minute Video Demonstration & Presentation Script

## Role & Context
- **Candidate:** GenAI Engineer – Content Systems
- **Project:** Self-Evaluating Lesson Content Generator
- **Assigned Topic:** Introduction to RAG (Retrieval-Augmented Generation)
- **Target Audience:** Indian 12th-Grade Graduate (Non-English medium background, zero AI knowledge)

---

## Time Allocation Breakdown

| Segment | Duration | Topic Covered |
| :--- | :--- | :--- |
| **Part 1** | 0:00 – 2:30 | Introduction, Problem Statement & Engineering Goals |
| **Part 2** | 2:30 – 5:30 | High-Level Architecture, State Schema & Dual-Layer Rubric |
| **Part 3** | 5:30 – 8:30 | Live Walkthrough: Clean First-Time Pass Scenario |
| **Part 4** | 8:30 – 12:30| Live Walkthrough: Deliberate-Error Injection, Evaluator Rejection & Auto-Regeneration |
| **Part 5** | 12:30 – 15:00| Persistent Memory (SQLite) & Self-Evolution Engine Walkthrough |
| **Part 6** | 15:00 – 17:30| Codebase Tour: LangGraph Workflow, Rubric Engine, and Repository |
| **Part 7** | 17:30 – 19:30| Automated Pytest Suite, Safety Guardrails & Conclusion |

---

## Detailed Script & Talking Points

### Part 1: Introduction & Problem Statement (0:00 – 2:30)
- **Visual:** Open Streamlit UI (`http://localhost:8501`) showing the clean title header and system controls.
- **Presenter:**
  > *"Hello everyone! Today, I am thrilled to present my take-home assignment for the role of GenAI Engineer – Content Systems: the **Self-Evaluating Lesson Content Generator**.*
  >
  > *Most generative AI applications in education are simple prompt wrappers—a user inputs a topic, and an LLM spits out an ungrounded, untested essay. If the explanation contains factual hallucinations, cryptic jargon, or skips essential architectural components, the learner is left confused.*
  >
  > *Our challenge was to design and implement an **autonomous agentic system** that doesn't just generate content, but acts like an editorial team: generating, independently evaluating against an uncompromising PASS/FAIL rubric, rejecting flawed drafts, executing feedback-driven regeneration with a maximum of two retries, persisting memory across sessions, and learning from failure patterns over time.*
  >
  > *Our assigned topic is **'Introduction to RAG'**, specifically tailored for a 12th-grade graduate from India with limited English vocabulary, a non-English-medium background, and zero prior knowledge of AI."*

---

### Part 2: Architecture & System Overview (2:30 – 5:30)
- **Visual:** Display `docs/architecture.md` diagram and Streamlit sidebar controls.
- **Presenter:**
  > *"Let's examine the architectural backbone of this system:*
  >
  > *1. **Orchestration:** We use **LangGraph** to model a cyclic state machine. The state schema maintains the topic, learner persona, attempt number, generated lesson, evaluation results, rejection log, and active evolution insights.*
  >
  > *2. **Dual-Layer Evaluation:** We do not rely solely on an LLM to grade its own work. We combine **Layer 1: Deterministic programmatic audits** (verifying all 18 mandatory sections, minimum content lengths, and scanning against an advanced jargon blacklist) with **Layer 2: Semantic LLM evaluation** across 6 core dimensions: Accuracy & Grounding, Beginner-Friendly Language, Teaching Through Examples, Clarity & Jargon, Topic Coverage, and Teaching Flow.*
  >
  > *3. **Pluggable LLM Layer:** We support OpenAI (GPT-4o, GPT-4o-mini), Google Gemini, Groq, Ollama, and a high-fidelity **Deterministic Mock Provider**. This guarantees that anyone reviewing this code can run the entire workflow and automated test suite instantly offline without entering an API key."*

---

### Part 3: Live Demo — Clean Passing Scenario (5:30 – 8:30)
- **Visual:** On Tab 1 ("Live Studio & Execution"), leave "Deliberate Error" unchecked. Click **"Generate & Self-Evaluate Lesson"**.
- **Presenter:**
  > *"Let us execute our first live run in standard production mode.*
  >
  > *Notice the live progress bar: it initializes the run, fetches persistent insights, invokes the Generator Agent, and immediately passes the draft to the Evaluator Agent.*
  >
  > *And look at that: **Status: PASSED on Attempt #1**!*
  >
  > *Let's navigate to Tab 2 ('Generated Lesson'):*
  > - *Notice how the lesson explains RAG using the familiar **CBSE Open-Book Exam analogy**: traditional AI is a student locked in a room trying to memorize everything, whereas RAG AI is an open-book exam where the student can consult reference books.*
  > - *Notice the culturally relatable Indian example: **Ramesh Uncle's Kirana shop in Lucknow**, where he uses his red **Bahi-Khata ledger** to look up customer credit rather than guessing from memory.*
  > - *Every technical word like 'Embeddings' and 'Vector DB' is explained immediately using student roll numbers and library book catalogs.*
  > - *All 18 required sections, terminology table, and 4 knowledge-check questions with answers and explanations are present."*

---

### Part 4: Live Demo — Deliberate-Error Rejection & Auto-Regeneration (8:30 – 12:30)
- **Visual:** In the Sidebar, check **"Enable Deliberate Error Injection"** and select **"Flawed Embeddings"**. Click **"Generate & Self-Evaluate Lesson"**.
- **Presenter:**
  > *"Now, let's demonstrate the core intelligence of this system: **catching errors, rejecting drafts, and auto-regenerating using targeted feedback**.*
  >
  > *I have activated the deliberate error flag, which simulates a flawed generator that claims 'Embeddings are secret passwords that encrypt text without meaning'.*
  >
  > *Watch the workflow progress: Attempt 1 is generated $\rightarrow$ The Evaluator audits it $\rightarrow$ **Evaluator rejects the draft!** $\rightarrow$ Conditional Router detects retries remain $\rightarrow$ Feedback is formatted $\rightarrow$ Attempt 2 is generated with corrective instructions $\rightarrow$ Evaluator re-audits $\rightarrow$ **PASSED on Attempt #2!**"*
- **Visual:** Switch to Tab 3 ("Evaluator Audit Dashboard") and Tab 4 ("Rejection & Regeneration Trail").
- **Presenter:**
  > *"Look at Tab 4: Here is our **Rejection Log**. For Attempt #1, it shows:*
  > - *Failed Checkpoint: `CHK_ACC_01 (Factual Accuracy of Core Concepts)`*
  > - *Exact Evaluator Evidence: 'Embeddings are secret passwords that encrypt text so nobody can read it...'*
  > - *Feedback Sent to Generator: 'Explain embeddings accurately as numerical representations that capture semantic meaning.'*
  >
  > *The generator received this exact feedback, corrected the embedding explanation in Attempt #2 using the roll-number analogy, and passed all 10 checkpoints. This proves that our feedback loop is real, targeted, and self-correcting."*

---

### Part 5: Persistent SQLite Memory & Self-Evolution (12:30 – 15:00)
- **Visual:** Open Tab 5 ("Persistent Memory & Evolution").
- **Presenter:**
  > *"Next, let's explore **Memory and Self-Evolution**.*
  >
  > *All runs and rejection logs are stored in a local SQLite database (`data/lesson_generator.db`). Here on the dashboard, you can see historical runs with their run IDs, status, attempts count, and prompt versions.*
  >
  > *Below that is our **Self-Evolution Engine**:*
  > - *The system analyzes failure patterns across historical runs.*
  > - *When it notices recurring issues (e.g. students struggling with abstract vector spaces), it synthesizes proactive guidelines, such as 'Always introduce embeddings using student roll numbers'.*
  > - *These active guidelines are automatically injected into future generator prompts.*
  > - *Crucially, we enforce a strict **safety boundary**: the system NEVER allows automatic weakening of the evaluation rubric. If a rubric change is needed, it is submitted to the `rubric_proposals` table for human review. This prevents the agent from lowering standards to cheat a 100% pass rate."*

---

### Part 6: Codebase Walkthrough (15:00 – 17:30)
- **Visual:** Switch to IDE / Terminal showing directory tree:
  - `agents/generator.py` and `agents/evaluator.py`
  - `workflow/graph.py` and `workflow/nodes.py`
  - `evaluation/rubric.py` and `evaluation/schemas.py`
  - `memory/database.py`, `memory/repository.py`, `memory/evolution.py`
  - `services/lesson_service.py`
- **Presenter:**
  > *"Let's take a quick look at the code organization:*
  > - *Every component follows single-responsibility principles.*
  > - *`workflow/graph.py` compiles the LangGraph state machine with clear conditional edges.*
  > - *`evaluation/rubric.py` cleanly separates deterministic programmatic checks from semantic LLM audits.*
  > - *All data contracts are strictly enforced using Pydantic v2 schemas.*
  > - *`services/llm_service.py` provides an extensible adapter pattern for OpenAI, Gemini, Groq, Ollama, and our deterministic mock provider."*

---

### Part 7: Automated Testing & Wrap-Up (17:30 – 19:30)
- **Visual:** Open terminal and run `python -m pytest tests/ -v`. Show all 20 tests passing.
- **Presenter:**
  > *"Finally, let's run our automated test suite.*
  >
  > *`pytest` runs 20 comprehensive unit, integration, deliberate-error, and retry-exhaustion tests in less than a second:*
  > - *Generator tests verify all 18 sections and prompt responsiveness.*
  > - *Evaluator tests verify deterministic jargon detection, missing section detection, and accurate evidence citation.*
  > - *Workflow tests verify routing bounds and ensure the retry limit terminates at max 2 retries without infinite loops.*
  > - *End-to-end tests verify clean passes, deliberate error regenerations, and max-retry exhaustion.*
  >
  > *In summary, this project represents a complete, reliable, and production-style GenAI content system. Thank you for your time and consideration!"*
