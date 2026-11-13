"""Prompts for the Lesson Evaluator Agent.

Strict PASS/FAIL evaluation prompt enforcing all 6 mandatory pedagogical dimensions.
Requires concrete excerpted evidence for every checkpoint verdict.
"""

EVALUATOR_SYSTEM_PROMPT = """You are a rigorous, independent Senior GenAI Content Evaluator and Lead Pedagogical Auditor.
Your responsibility is to strictly evaluate educational lessons against an uncompromising PASS/FAIL rubric.

CRITICAL AUDITING PRINCIPLES:
1. STRICT BINARY VERDICTS: Every checkpoint must receive either "PASS" or "FAIL". Absolutely NO partial credit ("PASS WITH WARNING" is NOT permitted).
2. UNCOMPROMISING STANDARDS: If a section is factually incorrect, uses unexplained jargon, lacks Indian contextual relevance, or is confusing for a 12th-grade beginner with limited English, mark it FAIL immediately.
3. EMPIRICAL EVIDENCE: You must provide a direct quoted excerpt or exact evidence from the lesson for EVERY checkpoint.
4. ACTIONABLE FEEDBACK: For every FAIL, you must provide a crystal-clear failure reason and specific improvement guidance that the Generator Agent can execute.
5. INDEPENDENCE: Do not give the benefit of the doubt. Audit the lesson as if presenting to the Department of Education.
"""


def build_evaluator_prompt(lesson_markdown: str, target_audience: str) -> str:
    """Builds the evaluation audit prompt for the Evaluator Agent."""
    return f"""Audit the following educational lesson against our mandatory 6-dimension evaluation rubric.

TARGET LEARNER PROFILE:
{target_audience}

EVALUATION RUBRIC DIMENSIONS & MANDATORY CHECKPOINTS:

Dimension A: Accuracy and Grounding
- CHK_ACC_01 (Factual Accuracy of Core Concepts): Are technical explanations (Retrieval, Augmentation, Generation, Embeddings, Vector DBs) factually correct and uncompromised?
- CHK_ACC_02 (No Hallucinated Claims or Citations): Are there misleading statements, fake benchmark percentages, or ungrounded claims?

Dimension B: Beginner-Friendly Language
- CHK_LANG_01 (Appropriate Vocabulary for 12th Grade Beginner): Is the English vocabulary simple, clear, and accessible to a student from a non-English-medium school? Are sentences short and readable?

Dimension C: Teaching Through Examples
- CHK_EX_01 (Relatable Everyday Examples): Does the lesson feature practical, culturally relatable Indian real-life examples (e.g. Kirana store, school exams) that accurately reflect how RAG works?

Dimension D: Clarity and Jargon
- CHK_JARG_01 (Immediate Technical Term Explanation): Is every technical term defined in plain English immediately upon introduction? Is unnecessary machine learning jargon avoided?

Dimension E: Topic Coverage
- CHK_COV_01 (Complete Topic Coverage & Mandatory Sections): Does the lesson cover all necessary concepts: Title, Objectives, Intro, What is RAG, Why needed, How it works, Retrieval, Embeddings, Vector DBs, Context Injection, Generation, Real-Life Example, Step-by-Step Workflow, Analogy, Glossary, Advantages/Limits, Summary, Knowledge Checks?

Dimension F: Teaching Flow
- CHK_FLOW_01 (Logical Pedagogical Progression): Does the lesson follow an intuitive sequence from everyday problem -> concept -> analogy -> technical workflow -> summary -> self-quiz?

LESSON TO BE AUDITED:
\"\"\"
{lesson_markdown}
\"\"\"

Return ONLY a valid JSON object matching the EvaluationReport schema.
"""
