# Strict PASS/FAIL Evaluation Rubric Specification

## 1. Rubric Architecture & Principles

The evaluation system operates under **zero-tolerance binary auditing**:
- **No Partial Credit:** Every mandatory checkpoint receives either `PASS` or `FAIL`.
- **Dual-Layer Validation:** Combines deterministic programmatic heuristics with deep semantic LLM evaluation.
- **Empirical Evidence:** Every checkpoint requires concrete excerpted evidence from the generated text.
- **Strict Passing Condition:** The lesson passes overall **if and only if 100% of mandatory checkpoints pass**. A single failure triggers regeneration.

---

## 2. Rubric Dimensions & Checkpoint Catalog

| Dimension | Checkpoint ID | Checkpoint Title | Evaluation Method | Mandatory? | Passing Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A. Accuracy & Grounding** | `CHK_ACC_01` | Factual Accuracy of Core Concepts | Semantic LLM | Yes | Retrieval, Augmentation, Generation, Embeddings, and Vector DBs are factually accurate without misconceptions. |
| **A. Accuracy & Grounding** | `CHK_ACC_02` | No Hallucinated Claims or Citations | Semantic LLM | Yes | Zero fabricated benchmarks, fake historical facts, or unsupported scientific citations. |
| **B. Beginner-Friendly Language** | `CHK_LANG_01`| Appropriate Vocabulary for 12th Grader | Semantic LLM | Yes | Vocabulary is simple, sentences are short and conversational, tailored to a non-English-medium Indian student. |
| **C. Teaching Through Examples** | `CHK_EX_01` | Relatable Everyday Examples | Semantic LLM | Yes | Includes practical Indian cultural scenario (Kirana store Bahi-Khata ledger) and intuitive open-book exam analogy. |
| **D. Clarity & Jargon** | `CHK_JARG_01`| Immediate Technical Term Explanation | Semantic LLM | Yes | All technical terms are explained immediately in plain language upon first appearance. |
| **D. Clarity & Jargon** | `CHK_JARG_02`| Glossary of Key Technical Terms | Deterministic | Yes | Glossary table defines at least 4 key terms with clear plain-English meanings. |
| **D. Clarity & Jargon** | `CHK_JARG_03`| Avoidance of Advanced Jargon | Deterministic | Yes | Zero occurrences of advanced terms from the blacklist (`manifold`, `eigenvalues`, `cross-entropy`, etc.). |
| **E. Topic Coverage** | `CHK_COV_01` | Complete Topic Coverage & Mandatory Sections | Deterministic + Semantic | Yes | All 18 mandatory syllabus sections are present with substantial, non-placeholder content. |
| **F. Teaching Flow** | `CHK_FLOW_01` | Logical Pedagogical Progression | Semantic LLM | Yes | Structure moves progressively: Problem $\rightarrow$ Concept $\rightarrow$ Analogy $\rightarrow$ Workflow $\rightarrow$ Summary $\rightarrow$ Quiz. |
| **F. Teaching Flow** | `CHK_FLOW_02` | Formative Knowledge-Check Assessment | Deterministic | Yes | At least 3 questions with answers and clear conceptual explanations are provided. |

---

## 3. Mandatory 18 Syllabus Sections

To satisfy `CHK_COV_01`, the lesson must contain all 18 sections:
1. Lesson Title
2. Learning Objectives
3. Introduction
4. What is RAG?
5. Why is RAG Needed?
6. How RAG Works
7. Retrieval Process
8. Embedding Explanation
9. Vector Database Explanation
10. Context Injection
11. Generation Process
12. Real-Life Example (Kirana Store Bahi-Khata)
13. Step-by-Step Workflow
14. Simple Practical Analogy (Open-Book Exam)
15. Key Terminology with Simple Meanings
16. Advantages and Limitations
17. Summary & Key Takeaways
18. Knowledge-Check Questions with Answers

---

## 4. Failure Handling & Regeneration Contract

When a checkpoint receives `FAIL`:
1. The Evaluator Agent extracts the offending text segment into `evidence`.
2. A detailed `reason` is recorded explaining why the student would be confused or misled.
3. An actionable `suggested_improvement` directive is formulated.
4. The system aggregates all failures into `RejectionLogEntry` and delivers it to the Generator Agent.
5. In the subsequent attempt, the Generator Agent is constrained to resolve those specific failures without regressing previously passed sections.
