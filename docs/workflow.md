# LangGraph Workflow & Regeneration Loop

## 1. Overview

The core workflow engine coordinates content generation, evaluation, conditional branching, rejection tracking, and feedback loop management using **LangGraph** (`StateGraph`).

---

## 2. Workflow Graph Topology

```mermaid
stateDiagram-v2
    [*] --> initialize_run
    initialize_run --> generate_lesson
    generate_lesson --> evaluate_lesson
    
    state evaluate_lesson {
        Deterministic_Checks
        --> Semantic_LLM_Audit
        --> Combine_Audit_Report
    }

    evaluate_lesson --> decision_router
    
    decision_router --> finalize_success : 100% Checkpoints PASS
    decision_router --> prepare_regeneration : Checkpoints FAIL & Attempts < 3
    decision_router --> finalize_exhausted : Checkpoints FAIL & Attempts >= 3
    
    prepare_regeneration --> generate_lesson : Feedback Injected Loop
    
    finalize_success --> [*] : Terminate (PASSED)
    finalize_exhausted --> [*] : Terminate (FAILED)
```

---

## 3. Detailed Step Breakdown

### Step 1: `initialize_run`
- **Objective:** Initializes execution context and retrieves persistent insights.
- **Operations:**
  - Generates a unique UUID `run_id`.
  - Queries `evolution_insights` table in SQLite for active pedagogical rules for the topic.
  - Inserts initial record in `runs` table with status `IN_PROGRESS`.
  - Sets `current_attempt = 1`.

### Step 2: `generate_lesson`
- **Objective:** Invokes the Generator Agent.
- **Operations:**
  - Injects `topic`, `target_audience`, `insights_applied`, and any previous attempt's `feedback_prompt`.
  - Prompts LLM to produce structured JSON matching `LessonContent` schema (all 18 mandatory sections).
  - Handles deliberate error injection if demo mode is enabled on Attempt 1.

### Step 3: `evaluate_lesson`
- **Objective:** Independent audit by the Evaluator Agent and Rubric Engine.
- **Operations:**
  - Runs **Layer 1: Deterministic Checks** (presence of all 18 sections, minimum content lengths, forbidden jargon detection, glossary completeness, question count).
  - Runs **Layer 2: Semantic LLM Checks** (conceptual correctness, Indian learner accessibility, analogy validity, absence of hallucinations).
  - Merges into strict binary report (`is_passed = True` only if $0$ mandatory checkpoints fail).
  - Saves attempt record in `attempts` table.

### Step 4: `decision_router`
- **Objective:** Conditional decision node.
- **Rules:**
  1. If `eval_report.is_passed == True` $\rightarrow$ transition to `finalize_success`.
  2. If `eval_report.is_passed == False` and `current_attempt < (1 + max_retries)` $\rightarrow$ transition to `prepare_regeneration`.
  3. If `eval_report.is_passed == False` and `current_attempt >= (1 + max_retries)` $\rightarrow$ transition to `finalize_exhausted`.

### Step 5: `prepare_regeneration` (The Feedback Loop)
- **Objective:** Packages specific failure evidence for targeted revision.
- **Operations:**
  - Extracts failed checkpoints, reasons, evidence citations, and required actions.
  - Formulates structured feedback prompt:
    ```markdown
    CRITICAL: The previous lesson failed the strict evaluation rubric:
    - Checkpoint [CHK_ACC_01] 'Factual Accuracy':
      * Failure Reason: Embeddings were misdefined as passwords without meaning.
      * Evidence: "Embeddings are secret passwords that encrypt text..."
      * Required Action: Explain embeddings accurately as numbers capturing semantic meaning.
    ```
  - Appends to `rejection_log` and persists entry into `rejection_logs` table.
  - Increments `current_attempt`.
  - Loops back to `generate_lesson`.

### Step 6a: `finalize_success`
- **Objective:** Stamping successful outcome.
- **Operations:**
  - Sets `final_status = "PASSED"`.
  - Updates `runs` table in SQLite.
  - Increments application counter of used insights in `evolution_insights`.
  - Transitions to LangGraph `END`.

### Step 6b: `finalize_exhausted`
- **Objective:** Controlled termination when retry limit is exhausted.
- **Operations:**
  - Sets `final_status = "FAILED"`. Never falsely marks as passed!
  - Appends final termination rejection log.
  - Updates `runs` table with status `FAILED`.
  - Triggers failure pattern registration in `SelfEvolutionEngine` to learn for subsequent runs.
  - Transitions to LangGraph `END`.
