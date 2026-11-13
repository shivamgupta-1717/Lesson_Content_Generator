"""Prompts for the Lesson Generator Agent.

Specially engineered for non-English-medium 12th-grade Indian graduates,
supporting feedback-based regeneration, targeted modifications, and dynamic self-evolution insights.
"""

from typing import List, Optional

GENERATOR_SYSTEM_PROMPT = """You are an empathetic, world-class Senior Educational Content Engineer and Teacher.
Your mission is to write an exceptionally clear, engaging, standalone educational lesson for a student in India who:
- Has just graduated from 12th grade (Secondary School).
- Comes from a non-English-medium school background (Hindi, Tamil, Marathi, Bengali, Telugu, etc.) and has a limited English vocabulary.
- Has zero prior knowledge of Computer Science, Artificial Intelligence, or Machine Learning.
- Needs simple everyday words, short sentences, and familiar cultural analogies (such as a local Kirana shopkeeper's Bahi-Khata ledger, an open-book exam, or a library).

PEDAGOGICAL & WRITING RULES:
1. Explain every technical term IMMEDIATELY the first time it is introduced in plain, conversational English.
2. Never assume prior AI knowledge. Break down acronyms (e.g., RAG = Retrieval-Augmented Generation) word-by-word.
3. Use concrete real-life examples and intuitive analogies before presenting any technical workflow.
4. Strictly avoid high-level academic jargon (e.g. "latent vector space", "high-dimensional manifolds", "backpropagation").
5. Do not invent fake statistics, fake scientific studies, or false citations.
6. Make the lesson completely standalone. A student reading this lesson should not need to search Google to understand it.
7. Return your response ONLY as a structured JSON object matching the requested schema.
"""


def build_generator_prompt(
    topic: str,
    target_audience: str,
    feedback: Optional[str] = None,
    evolution_insights: Optional[List[str]] = None,
    deliberate_error_mode: Optional[str] = None,
) -> str:
    """Builds the comprehensive user prompt for lesson generation or feedback-based regeneration."""
    prompt_lines = [
        f"Generate a comprehensive, beginner-friendly lesson on the topic: '{topic}'",
        f"Target Learner Profile: {target_audience}\n",
        "The lesson MUST cover all 18 mandatory sections in structured detail:",
        "1. Lesson Title (engaging and friendly)",
        "2. Learning Objectives (3-5 clear bullet points)",
        "3. Introduction (hook the student with a relatable scenario of AI making mistakes)",
        "4. What is RAG? (break down Retrieval, Augmented, and Generation in simple terms)",
        "5. Why is RAG Needed? (explain outdated knowledge and AI hallucinations)",
        "6. How RAG Works (high-level visual mechanics overview)",
        "7. Retrieval Process (how documents are searched and chunked)",
        "8. Embedding Explanation (explain turning words into numbers using intuitive analogies)",
        "9. Vector Database Explanation (explain storing concepts like a smart electronic library)",
        "10. Context Injection (explain passing the retrieved book pages to the AI)",
        "11. Generation Process (explain the AI writing the answer based on the facts)",
        "12. Real-Life Example (relatable Indian scenario, e.g. Kirana store ledger/Bahi-Khata)",
        "13. Step-by-Step Workflow (clear sequence of steps 1 through 5)",
        "14. Simple Practical Analogy (e.g. Open-Book Exam vs Closed-Book Exam)",
        "15. Key Terminology (glossary of at least 6 technical terms with simple meanings)",
        "16. Advantages and Limitations (honest benefits and boundaries)",
        "17. Summary & Key Takeaways (recap of key ideas)",
        "18. Knowledge-Check Questions (at least 3-4 questions with answers and explanations)\n",
    ]

    # Incorporate persistent self-evolution insights if available
    if evolution_insights:
        prompt_lines.append("### SYSTEM SELF-IMPROVEMENT INSIGHTS (From Historical Evaluations):")
        prompt_lines.append("Pay close attention to these learned guidelines from past evaluation patterns:")
        for insight in evolution_insights:
            prompt_lines.append(f"- {insight}")
        prompt_lines.append("")

    # If this is a regeneration attempt, append specific failure feedback
    if feedback:
        prompt_lines.append("### CRITICAL REVISION INSTRUCTIONS:")
        prompt_lines.append("Your previous attempt was evaluated and REJECTED against the strict evaluation rubric.")
        prompt_lines.append("You MUST specifically fix the issues listed in the evaluator feedback below.")
        prompt_lines.append("DO NOT degrade or remove sections that previously satisfied the rubric:")
        prompt_lines.append(f"\n{feedback}\n")

    if deliberate_error_mode:
        prompt_lines.append(f"### [DEMO/TEST FLAG ACTIVE]: {deliberate_error_mode}")

    return "\n".join(prompt_lines)
