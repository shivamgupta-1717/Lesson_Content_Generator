"""Prompts for the Lesson Generator Agent.

Dynamically adapts to ANY educational topic (React, RAG, Python, etc.) while tailoring
pedagogy for non-English-medium 12th-grade Indian graduates, supporting feedback-based
regeneration, targeted modifications, and persistent self-evolution insights.
"""

from typing import List, Optional

GENERATOR_SYSTEM_PROMPT = """You are an empathetic, world-class Senior Educational Content Engineer and Teacher.
Your mission is to write an exceptionally clear, engaging, standalone educational lesson for a student in India who:
- Has just graduated from 12th grade (Secondary School).
- Comes from a non-English-medium school background (Hindi, Tamil, Marathi, Bengali, Telugu, etc.) and has a limited English vocabulary.
- Has zero prior knowledge of Computer Science or the requested topic.
- Needs simple everyday words, short sentences, and familiar cultural analogies (such as cricket scoreboards, Swiggy food ordering, a local Kirana store, train booking, etc.).

PEDAGOGICAL & WRITING RULES:
1. DEDICATE THE CONTENT 100% TO THE REQUESTED TOPIC. If the user asks for "React", teach React! If they ask for "RAG", teach RAG! Never replace the user's requested topic with an unrelated topic.
2. Explain every technical term IMMEDIATELY the first time it is introduced in plain, conversational English.
3. Never assume prior programming or tech knowledge. Break down names, concepts, and acronyms word-by-word.
4. Use concrete real-life Indian examples and intuitive practical analogies before presenting any technical workflow.
5. Strictly avoid intimidating academic or mathematical jargon without immediate plain-English explanations.
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
    """Builds the comprehensive user prompt for lesson generation tailored to ANY topic."""
    topic_clean = topic.strip()
    is_rag = "rag" in topic_clean.lower() or "retrieval" in topic_clean.lower()
    is_react = "react" in topic_clean.lower()

    if is_react:
        p1 = "Components (reusable UI building blocks like LEGO bricks)"
        p2 = "JSX (writing HTML-like tags inside JavaScript)"
        p3 = "State and Props (storing changing data vs passing data down)"
        p4 = "Virtual DOM (a smart memory scratchpad that updates only what changed)"
        p5 = "Component Lifecycle & Hooks (functions like useState to control behavior)"
        example_hint = "e.g., Live Cricket Scoreboard or Swiggy food cart updating the total bill without reloading the whole web page"
        analogy_hint = "e.g., Building a house with reusable LEGO blocks instead of carving each room from scratch every time"
    elif is_rag:
        p1 = "The Retrieval Process (how documents are searched and chunked)"
        p2 = "Embedding Explanation (turning human words into numbers by meaning)"
        p3 = "Vector Database Explanation (storing concepts like a smart electronic library)"
        p4 = "Context Injection (passing the retrieved facts into the prompt for the AI)"
        p5 = "Generation Process (the AI reading facts and writing a grounded answer)"
        example_hint = "e.g., A local Kirana shopkeeper (Ramesh Uncle) using his red Bahi-Khata ledger book"
        analogy_hint = "e.g., An Open-Book Exam where you can read textbook pages on your desk vs Closed-Book Exam"
    else:
        p1 = f"Core Technical Pillar 1 of {topic_clean}"
        p2 = f"Core Technical Pillar 2 of {topic_clean}"
        p3 = f"Core Technical Pillar 3 of {topic_clean}"
        p4 = f"Core Technical Pillar 4 of {topic_clean}"
        p5 = f"Core Technical Pillar 5 of {topic_clean}"
        example_hint = f"e.g., Relatable everyday Indian scenario demonstrating {topic_clean} in action"
        analogy_hint = f"e.g., Intuitive everyday analogy to understand {topic_clean}"

    prompt_lines = [
        f"Generate a comprehensive, beginner-friendly lesson on the exact topic: '{topic_clean}'",
        f"Target Learner Profile: {target_audience}\n",
        f"CRITICAL: All explanations, examples, glossary, and questions MUST BE SPECIFICALLY ABOUT '{topic_clean}'.",
        "The lesson MUST cover all 18 mandatory sections in structured detail:",
        f"1. Lesson Title (engaging and friendly, specifically about {topic_clean})",
        "2. Learning Objectives (3-5 clear bullet points)",
        f"3. Introduction (hook the student with a relatable scenario showing why we need {topic_clean})",
        f"4. What is {topic_clean}? (clear plain-English definition breaking down the name and purpose)",
        f"5. Why is {topic_clean} Needed? (the exact problem it solves in everyday life / computing)",
        f"6. How {topic_clean} Works (high-level visual mechanics overview)",
        f"7. Core Concept 1: {p1}",
        f"8. Core Concept 2: {p2}",
        f"9. Core Concept 3: {p3}",
        f"10. Core Concept 4: {p4}",
        f"11. Core Concept 5: {p5}",
        f"12. Real-Life Example ({example_hint})",
        f"13. Step-by-Step Workflow (clear sequence of steps 1 through 5 for {topic_clean})",
        f"14. Simple Practical Analogy ({analogy_hint})",
        f"15. Key Terminology (glossary of at least 6 technical terms of {topic_clean} with simple meanings)",
        f"16. Advantages and Limitations (honest benefits and boundaries of {topic_clean})",
        f"17. Summary & Key Takeaways (recap of key ideas)",
        f"18. Knowledge-Check Questions (at least 3-4 questions specifically about {topic_clean} with answers and explanations)\n",
    ]

    # Incorporate persistent self-evolution insights if available
    if evolution_insights:
        prompt_lines.append("### SYSTEM SELF-IMPROVEMENT INSIGHTS (From Historical Evaluations):")
        for insight in evolution_insights:
            prompt_lines.append(f"- {insight}")
        prompt_lines.append("")

    # If this is a regeneration attempt, append specific failure feedback
    if feedback:
        prompt_lines.append("### CRITICAL REVISION INSTRUCTIONS:")
        prompt_lines.append("Your previous attempt was evaluated and REJECTED against the strict evaluation rubric.")
        prompt_lines.append("You MUST specifically fix the issues listed in the evaluator feedback below.")
        prompt_lines.append(f"\n{feedback}\n")

    if deliberate_error_mode:
        prompt_lines.append(f"### [DEMO/TEST FLAG ACTIVE]: {deliberate_error_mode}")

    return "\n".join(prompt_lines)
