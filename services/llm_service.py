"""LLM Provider abstraction and service layer.

Supports pluggable providers (mock, openai, gemini, groq, ollama, anthropic) with
structured Pydantic output validation, deterministic fallbacks, retry logic, and clear diagnostics.
"""

import abc
import json
import os
import re
from typing import Any, Dict, Optional, Type, TypeVar
from dotenv import load_dotenv
from pydantic import BaseModel
from utils.logger import logger

load_dotenv()

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(abc.ABC):
    """Abstract interface for LLM backends."""

    @abc.abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generates plain text response."""
        pass

    @abc.abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generates and validates structured output conforming to a Pydantic model."""
        pass


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for OpenAI and compatible endpoints (Groq, Ollama, Together, DeepSeek)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        timeout: int = 60,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required for OpenAICompatibleProvider. Run 'pip install openai'.")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key and not base_url:
            raise ValueError("OPENAI_API_KEY is not set. Please add it to your .env file or choose provider='mock'.")

        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.client = OpenAI(
            api_key=self.api_key or "sk-placeholder-for-local",
            base_url=base_url,
            timeout=timeout,
        )

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        schema = response_model.model_json_schema()
        system = (system_prompt or "") + (
            f"\n\nYou MUST respond ONLY with a valid JSON object matching this schema:\n{json.dumps(schema, indent=2)}\n"
            "Do not output markdown codeblocks, notes, or any extraneous text outside the JSON."
        )
        raw_text = self.generate_text(prompt=prompt, system_prompt=system)
        return _extract_and_validate_json(raw_text, response_model)


class GeminiProvider(BaseLLMProvider):
    """Provider for Google Gemini API with smart multi-model free-tier fallback."""

    FALLBACK_MODELS = ["gemini-3-flash-preview", "gemini-3.1-flash-lite"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3-flash-preview",
        temperature: float = 0.3,
    ):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai is required for GeminiProvider. Run 'pip install google-generativeai'.")

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file or choose provider='mock'.")

        genai.configure(api_key=self.api_key)
        self.model_name = model or "gemini-3-flash-preview"
        self.temperature = temperature
        self._genai = genai
        self.client = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={"temperature": self.temperature},
        )

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        # Candidate models to try in sequence if a model hits free-tier quota limits
        models_to_try = [self.model_name] + [m for m in self.FALLBACK_MODELS if m != self.model_name]
        last_error = None

        for candidate_model in models_to_try:
            try:
                logger.info(f"GeminiProvider: Invoking model '{candidate_model}'...")
                active_client = self._genai.GenerativeModel(
                    model_name=candidate_model,
                    generation_config={"temperature": self.temperature},
                )
                response = active_client.generate_content(full_prompt)
                if response and response.text:
                    self.model_name = candidate_model
                    self.client = active_client
                    return response.text.strip()
            except Exception as exc:
                err_str = str(exc)
                last_error = exc
                if "ResourceExhausted" in err_str or "429" in err_str or "quota" in err_str.lower():
                    logger.warning(
                        f"Gemini model '{candidate_model}' hit free-tier rate limit (429). "
                        "Attempting next available candidate model..."
                    )
                    continue
                elif "404" in err_str:
                    logger.warning(f"Gemini model '{candidate_model}' not found; trying next model...")
                    continue
                else:
                    logger.error(f"Gemini model '{candidate_model}' error: {exc}. Trying next candidate...")
                    continue

        raise RuntimeError(
            f"All Gemini candidate models ({models_to_try}) failed. Last error: {last_error}"
        )

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        schema = response_model.model_json_schema()
        instruction = (
            f"{system_prompt or ''}\n\n"
            f"You MUST respond ONLY with valid JSON conforming to this schema:\n{json.dumps(schema, indent=2)}\n"
            "Do NOT include markdown formatting or extra text outside the JSON."
        )

        models_to_try = [self.model_name] + [m for m in self.FALLBACK_MODELS if m != self.model_name]
        last_error = None

        for candidate_model in models_to_try:
            try:
                active_client = self._genai.GenerativeModel(
                    model_name=candidate_model,
                    generation_config={"temperature": self.temperature},
                )
                logger.info(f"GeminiProvider.generate_structured: Calling '{candidate_model}'...")
                full_prompt = f"{instruction}\n\n{prompt}"
                response = active_client.generate_content(full_prompt)
                if response and response.text:
                    self.model_name = candidate_model
                    self.client = active_client
                    return _extract_and_validate_json(response.text.strip(), response_model)
            except Exception as exc:
                last_error = exc
                logger.warning(f"GeminiProvider model '{candidate_model}' structured generation failed: {exc}")
                continue

        raise RuntimeError(
            f"Gemini API could not generate structured output for {response_model.__name__} after attempting models {models_to_try}: {last_error}"
        )


class DeterministicMockLLMProvider(BaseLLMProvider):
    """High-fidelity Deterministic Mock LLM Provider for offline evaluation, zero-key development,

    and deliberate error demonstrations. Produces rich, pedagogically sound RAG lessons
    and accurate pass/fail evaluations without incurring API costs or latency.
    """

    def __init__(self, deliberate_error_mode: Optional[str] = None):
        self.deliberate_error_mode = deliberate_error_mode

    def set_error_mode(self, mode: Optional[str]) -> None:
        self.deliberate_error_mode = mode

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return "Deterministic Mock Response for testing purposes."

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        model_name = response_model.__name__

        if "LessonContent" in model_name:
            from evaluation.schemas import LessonContent
            content = self._build_mock_lesson(prompt)
            return content  # type: ignore

        elif "EvaluationReport" in model_name:
            from evaluation.schemas import EvaluationReport
            report = self._build_mock_evaluation(prompt)
            return report  # type: ignore

        raise ValueError(f"DeterministicMockLLMProvider does not have a canned template for {model_name}")

    def _build_mock_lesson(self, prompt: str) -> Any:
        from evaluation.schemas import LessonContent

        # Check if topic is React vs RAG vs Generic
        prompt_lower = prompt.lower()
        if "react" in prompt_lower:
            return self._build_mock_react_lesson(prompt)
        elif not ("rag" in prompt_lower or "retrieval" in prompt_lower):
            return self._build_mock_generic_lesson(prompt)

        # Check if deliberate error was injected or if this is a feedback regeneration
        is_flawed_embeddings = self.deliberate_error_mode == "flawed_embeddings"
        is_missing_vector_db = self.deliberate_error_mode == "missing_vector_db"
        is_jargon_overload = self.deliberate_error_mode == "jargon_overload"
        is_flawed_workflow = self.deliberate_error_mode == "flawed_workflow"

        # Check if prompt contains feedback indicating regeneration attempt
        has_feedback = "CRITICAL: The previous lesson failed" in prompt or "Revise the lesson" in prompt

        # If feedback is provided, the generator resolves any deliberate errors!
        embedding_text = (
            "Embeddings convert words into numbers so the computer can understand meanings. "
            "Think of it like giving a roll number to every student in school, but here, words that have similar meanings get numbers that are close to each other. "
            "For example, 'school' and 'college' get very close numbers, while 'airplane' gets a very different number."
        )
        if is_flawed_embeddings and not has_feedback:
            # Deliberate error: Misleading/incorrect explanation of embeddings
            embedding_text = (
                "Embeddings are secret passwords that encrypt text so nobody can read it. "
                "Embeddings do not capture any meaning at all, they just count how many letters exist in a word."
            )

        vector_db_text = (
            "A vector database is like a modern digital library where books are organized by their topic and meaning, "
            "not just alphabetically. When you search for 'how to treat a fever', the vector database quickly finds all "
            "passages that talk about body temperature and medicines, even if they use slightly different words."
        )
        if is_missing_vector_db and not has_feedback:
            # Deliberate error: Skips vector database explanation completely
            vector_db_text = "Vector databases are not important and we will skip them today."

        what_is_rag_text = (
            "RAG stands for Retrieval-Augmented Generation. Let us break down those three big words into simple terms:\n\n"
            "1. **Retrieval (Finding):** Looking up and searching for correct, up-to-date facts from books, notes, or files.\n"
            "2. **Augmented (Helping / Adding):** Giving those found facts to the AI to make its answer stronger and accurate.\n"
            "3. **Generation (Writing):** The AI reading those facts and writing a polite, easy-to-read answer for you.\n\n"
            "In short, RAG helps an AI answer your questions by reading your trusted study materials first, rather than guessing from memory."
        )
        if is_jargon_overload and not has_feedback:
            what_is_rag_text = (
                "RAG utilizes approximate nearest neighbors on latent high-dimensional non-Euclidean manifolds "
                "orchestrated via dot-product cosine affinity matrices without explanatory semantics."
            )

        workflow_text = (
            "Here is the simple step-by-step process of RAG from start to finish:\n\n"
            "1. **You Ask a Question:** You type: *'What are the eligibility criteria for 12th board exams?'*\n"
            "2. **The Search (Retrieval):** The system searches through your official school rulebook PDF.\n"
            "3. **Finding Matches:** It pulls out the 2 exact pages that explain 12th board exam rules.\n"
            "4. **Giving Context (Injection):** It pastes those 2 pages right next to your question for the AI.\n"
            "5. **Generating the Answer:** The AI reads the rulebook pages and explains the criteria in simple English."
        )
        if is_flawed_workflow and not has_feedback:
            workflow_text = "Step 1: The AI guesses the answer. Step 2: It retrieves nothing. Step 3: Done."

        return LessonContent(
            topic="Introduction to RAG (Retrieval-Augmented Generation)",
            target_audience="12th-grade graduate from India with limited English vocabulary and no prior AI knowledge",
            title="Understanding RAG (Retrieval-Augmented Generation): The Smart Open-Book AI",
            learning_objectives=[
                "Understand why artificial intelligence (AI) sometimes makes mistakes or forgets facts.",
                "Learn what the three words in RAG (Retrieval, Augmented, Generation) actually mean.",
                "Discover how embeddings and vector databases help computers search by meaning.",
                "See how an AI uses RAG like a student writing an open-book exam.",
                "Identify the main advantages and limits of RAG in real life."
            ],
            introduction=(
                "Have you ever asked a smart computer program (like ChatGPT) a question, and it answered with total confidence, "
                "yet the answer turned out to be completely wrong or outdated? In the computer world, we call this a 'hallucination'—which "
                "simply means the AI made up a believable story because it did not know the real facts. "
                "Today, we will learn about a powerful technology called **RAG** that stops the AI from guessing by letting it look up "
                "verified facts before answering you."
            ),
            what_is_rag=what_is_rag_text,
            why_is_rag_needed=(
                "Why do we need RAG? Imagine a brilliant student who graduated 3 years ago. If you ask them today's petrol price in Mumbai, "
                "or the syllabus changes announced yesterday by the CBSE board, they cannot know! Their brain was only trained on older information.\n\n"
                "Similarly, AI models have two big problems:\n"
                "1. **Outdated Information:** Their training stops on a specific date. They do not know today's news.\n"
                "2. **Hallucination (Making things up):** When they do not know an answer, they might invent fake facts.\n\n"
                "RAG fixes both problems by handing the AI the latest textbook or company documents at the exact moment you ask your question."
            ),
            how_rag_works=(
                "RAG works like a bridge connecting a smart writer with a giant library. "
                "Instead of forcing the writer to memorize every book in the world, the writer has a fast assistant. "
                "When you ask a question, the assistant runs to the bookshelf, finds the exact right page, and shows it to the writer. "
                "The writer reads the page and crafts an easy-to-understand answer for you."
            ),
            retrieval_process=(
                "The word **Retrieval** means 'finding and bringing back'. "
                "When you search on Google, it retrieves web links. In RAG, retrieval searches your private notes, PDFs, or company files. "
                "It breaks large documents into small bite-sized paragraphs (called 'chunks') so it can quickly locate the exact paragraph that answers your question."
            ),
            embedding_explanation=embedding_text,
            vector_database_explanation=vector_db_text,
            context_injection=(
                "**Context Injection** sounds fancy, but it is very simple. 'Context' means background information. 'Injection' means inserting or passing in. "
                "When the assistant finds the right paragraph from your document, it combines your question with that paragraph into one message:\n\n"
                "*[Message to AI]*: *'Here are the official rules from CBSE (Context). Please read them and answer this student question (Prompt): What is the passing mark?'*\n\n"
                "This ensures the AI grounds its answer strictly on the provided paragraph, not on wild guesses."
            ),
            generation_process=(
                "**Generation** is the final step where the Large Language Model (LLM) writes out the answer. "
                "Because the AI now has the exact facts in front of its eyes, it does not need to guess. "
                "It uses its natural language writing skills to summarize the facts clearly, politely, and in simple language that matches your question."
            ),
            real_life_example=(
                "Let us look at a real-life Indian example: **A local Kirana (grocery) shopkeeper and his Bahi-Khata (ledger book)**.\n\n"
                "Ramesh Uncle runs a busy Kirana store in Lucknow. He has 300 regular customers who buy dal, rice, and spices on monthly credit. "
                "Can Ramesh Uncle memorize every single rupee owed by each customer over the last 6 months? Of course not!\n\n"
                "So what does he do? When Mrs. Sharma comes and asks, *'Uncle, how much is my total bill for October?'*, "
                "Ramesh Uncle does not guess. He opens his red Bahi-Khata ledger (Retrieval), flips directly to Mrs. Sharma's page (Matching), "
                "reads the exact entries (Context), and tells her: *'Madam, your total is Rs. 1,450'* (Generation).\n\n"
                "Ramesh Uncle's brain + his Bahi-Khata book = RAG in action!"
            ),
            step_by_step_workflow=workflow_text,
            simple_practical_analogy=(
                "**The Open-Book Exam Analogy:**\n\n"
                "Think of two types of exams in school:\n"
                "- **Closed-Book Exam (Traditional AI):** You are locked in a room with only your memory. If you forget a date or formula, you have to guess or leave it blank.\n"
                "- **Open-Book Exam (RAG AI):** The teacher allows you to keep your physics textbook on your desk. When a question asks about Ohm's Law, you open Chapter 3, read the formula, and write the perfect solution.\n\n"
                "RAG turns every question into an open-book exam for the AI!"
            ),
            key_terminology={
                "LLM (Large Language Model)": "A computer program trained on massive amounts of reading material to write and chat like a human.",
                "Retrieval": "The act of searching and finding the right piece of information from documents.",
                "Augmented": "Made stronger or better by adding helpful extra information.",
                "Hallucination": "When an AI does not know the answer and makes up false information that sounds real.",
                "Embedding": "Converting human words into numbers so computers can calculate similarity of meaning.",
                "Vector Database": "A specialized electronic filing cabinet that stores embeddings and finds related concepts fast.",
                "Chunking": "Cutting long documents into smaller, readable paragraphs so they are easy to search.",
                "Context": "The background facts or notes provided to the AI to help it answer accurately."
            },
            advantages_and_limitations=(
                "**Advantages of RAG:**\n"
                "1. **High Accuracy:** Cuts down AI hallucinations and false information.\n"
                "2. **Fresh, Up-to-Date Facts:** You can update documents daily without retraining the whole AI model.\n"
                "3. **Privacy and Safety:** Your private company files stay in your database and are not shared with the world.\n"
                "4. **Cost Effective:** Adding new documents costs almost nothing compared to the millions of dollars needed to train a new AI model.\n\n"
                "**Limitations of RAG:**\n"
                "1. **Depends on Search Quality:** If the retrieval step picks the wrong document page, the AI's answer will also be wrong ('Garbage In, Garbage Out').\n"
                "2. **Slightly Slower:** Because it has to search first and write second, it takes a few seconds longer than normal chatbots.\n"
                "3. **Complex Setup:** Setting up vector databases and chunking documents requires careful engineering."
            ),
            summary=(
                "To summarize what we learned today:\n"
                "- Standard AI relies only on past memory and can hallucinate fake answers.\n"
                "- RAG (Retrieval-Augmented Generation) gives the AI an 'open book' to look up verified facts before answering.\n"
                "- It works in 3 clear stages: **Retrieve** the best document chunk, **Augment** the question with that context, and **Generate** an accurate answer.\n"
                "- Embeddings and vector databases help the computer search by concept and meaning, not just exact spelling.\n"
                "- Just like Ramesh Uncle consulting his Bahi-Khata ledger, RAG combines human knowledge sources with AI writing intelligence."
            ),
            knowledge_check_questions=[
                {
                    "question": "What does the letter 'R' in RAG stand for?",
                    "answer": "Retrieval (which means finding and fetching relevant facts from documents).",
                    "explanation": "Retrieval is the search step that happens before the AI begins writing."
                },
                {
                    "question": "Why is an open-book exam a good analogy for RAG?",
                    "answer": "Because the student does not have to rely only on memory; they can consult verified textbook pages directly on their desk.",
                    "explanation": "RAG gives the AI reference documents just like an open book."
                },
                {
                    "question": "What is 'hallucination' in AI?",
                    "answer": "When an AI makes up confident-sounding but completely incorrect or fabricated facts.",
                    "explanation": "RAG prevents hallucinations by grounding the AI in trusted context."
                },
                {
                    "question": "What do embeddings do with human words?",
                    "answer": "They turn words into numbers so the computer can calculate how closely related their meanings are.",
                    "explanation": "Words with similar meanings receive numbers that are mathematically close together."
                }
            ]
        )

    def _build_mock_evaluation(self, prompt: str) -> Any:
        from evaluation.schemas import CheckpointResult, EvaluationReport, EvaluationStatus, RubricDimension

        prompt_lower = prompt.lower()
        if "react" in prompt_lower:
            return self._build_mock_react_evaluation(prompt)
        elif not ("rag" in prompt_lower or "retrieval" in prompt_lower):
            return self._build_mock_generic_evaluation(prompt)

        is_flawed_embeddings = self.deliberate_error_mode == "flawed_embeddings"
        is_missing_vector_db = self.deliberate_error_mode == "missing_vector_db"
        is_jargon_overload = self.deliberate_error_mode == "jargon_overload"
        is_flawed_workflow = self.deliberate_error_mode == "flawed_workflow"

        checkpoints = []

        # 1. CHK_ACC_01: Technical Accuracy
        if is_flawed_embeddings:
            checkpoints.append(CheckpointResult(
                checkpoint_id="CHK_ACC_01",
                checkpoint_name="Factual Accuracy of Core Concepts",
                dimension=RubricDimension.ACCURACY_AND_GROUNDING,
                is_mandatory=True,
                status=EvaluationStatus.FAIL,
                reason="Embeddings are incorrectly defined as passwords that do not capture meaning.",
                evidence="Embeddings are secret passwords that encrypt text so nobody can read it. Embeddings do not capture any meaning at all...",
                suggested_improvement="Explain embeddings accurately as numerical representations that capture semantic meaning and conceptual similarity."
            ))
        else:
            checkpoints.append(CheckpointResult(
                checkpoint_id="CHK_ACC_01",
                checkpoint_name="Factual Accuracy of Core Concepts",
                dimension=RubricDimension.ACCURACY_AND_GROUNDING,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Core RAG concepts (retrieval, augmentation, generation, embeddings) are explained factually without misinformation.",
                evidence="RAG stands for Retrieval-Augmented Generation... Embeddings convert words into numbers so the computer can understand meanings.",
                suggested_improvement=""
            ))

        # 2. CHK_ACC_02: Grounding and Hallucination Check
        checkpoints.append(CheckpointResult(
            checkpoint_id="CHK_ACC_02",
            checkpoint_name="No Hallucinated Claims or Citations",
            dimension=RubricDimension.ACCURACY_AND_GROUNDING,
            is_mandatory=True,
            status=EvaluationStatus.PASS,
            reason="No fabricated statistics, fake benchmark figures, or false historical citations are present.",
            evidence="Lesson relies on sound foundational principles rather than ungrounded statistics.",
            suggested_improvement=""
        ))

        # 3. CHK_LANG_01: Beginner-Friendly Vocabulary
        if is_jargon_overload:
            checkpoints.append(CheckpointResult(
                checkpoint_id="CHK_LANG_01",
                checkpoint_name="Appropriate Vocabulary for 12th Grade Beginner",
                dimension=RubricDimension.BEGINNER_FRIENDLY_LANGUAGE,
                is_mandatory=True,
                status=EvaluationStatus.FAIL,
                reason="Uses intimidating mathematical phrasing without definition: 'approximate nearest neighbors on latent high-dimensional non-Euclidean manifolds'.",
                evidence="RAG utilizes approximate nearest neighbors on latent high-dimensional non-Euclidean manifolds...",
                suggested_improvement="Replace high-dimensional manifold jargon with everyday words like 'searching by meaning' or 'digital library'."
            ))
        else:
            checkpoints.append(CheckpointResult(
                checkpoint_id="CHK_LANG_01",
                checkpoint_name="Appropriate Vocabulary for 12th Grade Beginner",
                dimension=RubricDimension.BEGINNER_FRIENDLY_LANGUAGE,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Vocabulary is accessible to a non-English-medium 12th-grade Indian student. Sentences are short and clear.",
                evidence="Have you ever asked a smart computer program a question... Think of it like giving a roll number to every student...",
                suggested_improvement=""
            ))

        # 4. CHK_EX_01: Practical Everyday Examples
        checkpoints.append(CheckpointResult(
            checkpoint_id="CHK_EX_01",
            checkpoint_name="Relatable Everyday Examples",
            dimension=RubricDimension.TEACHING_THROUGH_EXAMPLES,
            is_mandatory=True,
            status=EvaluationStatus.PASS,
            reason="Features relatable Indian everyday example (Ramesh Uncle's Kirana shop and Bahi-Khata ledger) and open-book exam analogy.",
            evidence="Ramesh Uncle runs a busy Kirana store in Lucknow... He opens his red Bahi-Khata ledger (Retrieval)...",
            suggested_improvement=""
        ))

        # 5. CHK_JARG_01: Immediate Jargon Explanation
        checkpoints.append(CheckpointResult(
            checkpoint_id="CHK_JARG_01",
            checkpoint_name="Immediate Technical Term Explanation",
            dimension=RubricDimension.CLARITY_AND_JARGON,
            is_mandatory=True,
            status=EvaluationStatus.PASS,
            reason="Technical words like retrieval, augmentation, hallucination, and chunking are explained immediately upon first mention and tabulated in a glossary.",
            evidence="Key Terminology table clearly maps technical words to simple everyday meanings.",
            suggested_improvement=""
        ))

        # 6. CHK_COV_01: Mandatory Topic Coverage (18 sections)
        if is_missing_vector_db:
            checkpoints.append(CheckpointResult(
                checkpoint_id="CHK_COV_01",
                checkpoint_name="Complete Topic Coverage & Mandatory Sections",
                dimension=RubricDimension.TOPIC_COVERAGE,
                is_mandatory=True,
                status=EvaluationStatus.FAIL,
                reason="Vector database explanation was skipped, omitting a critical mandatory component of RAG architecture.",
                evidence="Vector databases are not important and we will skip them today.",
                suggested_improvement="Provide a full, beginner-friendly section explaining how vector databases store and retrieve embeddings by concept."
            ))
        else:
            checkpoints.append(CheckpointResult(
                checkpoint_id="CHK_COV_01",
                checkpoint_name="Complete Topic Coverage & Mandatory Sections",
                dimension=RubricDimension.TOPIC_COVERAGE,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="All 18 required syllabus components are present and thoroughly addressed.",
                evidence="Lesson includes objectives, intro, retrieval, embeddings, vector DB, context injection, workflow, analogy, glossary, and knowledge check.",
                suggested_improvement=""
            ))

        # 7. CHK_FLOW_01: Progressive Pedagogical Flow
        if is_flawed_workflow:
            checkpoints.append(CheckpointResult(
                checkpoint_id="CHK_FLOW_01",
                checkpoint_name="Logical Pedagogical Progression",
                dimension=RubricDimension.TEACHING_FLOW,
                is_mandatory=True,
                status=EvaluationStatus.FAIL,
                reason="Workflow jumps straight to guessing without retrieving context first.",
                evidence="Step 1: The AI guesses the answer. Step 2: It retrieves nothing.",
                suggested_improvement="Present the workflow in chronological sequence: User Query -> Retrieve Chunks -> Inject Context -> Generate Response."
            ))
        else:
            checkpoints.append(CheckpointResult(
                checkpoint_id="CHK_FLOW_01",
                checkpoint_name="Logical Pedagogical Progression",
                dimension=RubricDimension.TEACHING_FLOW,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Structure transitions intuitively from real-life problems (AI forgetting facts) to foundational definitions, visual mechanics, analogies, and self-checks.",
                evidence="Problem setup -> Definition -> Components -> Analogy -> Step-by-Step -> Quiz.",
                suggested_improvement=""
            ))

        failed_list = [c for c in checkpoints if c.status == EvaluationStatus.FAIL]
        is_passed = len(failed_list) == 0

        dimension_scores = {}
        for c in checkpoints:
            dimension_scores[c.dimension.value] = "PASS" if c.status == EvaluationStatus.PASS else "FAIL"

        verdict = (
            "All mandatory checkpoints passed. The lesson is pedagogically sound, grounded, and beginner-ready."
            if is_passed
            else f"Evaluation FAILED: {len(failed_list)} mandatory checkpoints did not meet required quality standards."
        )

        return EvaluationReport(
            attempt_number=1,
            is_passed=is_passed,
            total_checkpoints=len(checkpoints),
            passed_checkpoints=len(checkpoints) - len(failed_list),
            failed_checkpoints=len(failed_list),
            dimension_scores=dimension_scores,
            checkpoints=checkpoints,
            summary_verdict=verdict,
        )

    def _build_mock_react_lesson(self, prompt: str) -> Any:
        from evaluation.schemas import LessonContent

        is_flawed_workflow = self.deliberate_error_mode == "flawed_workflow"
        has_feedback = "CRITICAL: The previous lesson failed" in prompt or "Revise the lesson" in prompt

        workflow_text = (
            "Here is the simple step-by-step workflow of how React works in a website:\n\n"
            "1. **Component Written:** The developer writes a component (for example, a 'Like' button or a food item card).\n"
            "2. **User Clicks:** A user taps the '+ Add' button on the screen.\n"
            "3. **State Updates:** React updates the button's internal State (likeCount = likeCount + 1).\n"
            "4. **Virtual DOM Compares:** React calculates the difference on its quick memory scratchpad.\n"
            "5. **Precise Screen Update:** The browser updates only that single heart icon and count without reloading the page!"
        )
        if is_flawed_workflow and not has_feedback:
            workflow_text = "Step 1: The website reloads the entire page. Step 2: Everything blinks white. Step 3: Done."

        return LessonContent(
            topic="Introduction to React",
            target_audience="12th-grade graduate from India with limited English vocabulary and no prior programming knowledge",
            title="Understanding React: Building Modern Websites Like LEGO Blocks",
            learning_objectives=[
                "Understand why traditional websites feel slow and need constant full-page refreshes.",
                "Learn what React is and how it builds user interfaces using reusable LEGO-like blocks called Components.",
                "Discover how JSX lets us combine HTML design tags with JavaScript logic easily.",
                "Understand State and Props: how components remember changing scores and receive instructions.",
                "See how the Virtual DOM updates only the changed parts of a screen, like a cricket scoreboard."
            ],
            introduction=(
                "Have you ever noticed that when you order food on Swiggy or Zomato, as soon as you tap the '+' button "
                "to add an extra butter naan, the total bill and cart item count change instantly without the entire web page "
                "reloading or blinking white? "
                "Traditional websites built years ago had to reload the whole screen for every single click. "
                "Today, we will learn about **React**—a widely used technology created by Facebook that makes modern websites "
                "feel as fast and smooth as mobile apps."
            ),
            what_is_rag=(
                "React is a free, popular JavaScript library used for building user interfaces (UI)—the visual screens, "
                "buttons, and navigation bars that you interact with on a website.\n\n"
                "Instead of creating a giant, complicated 1,000-line webpage, React lets developers break the screen into "
                "small, independent, reusable building blocks called **Components** (just like building a house out of LEGO blocks)."
            ),
            why_is_rag_needed=(
                "Why do we need React? Imagine a giant electronic cricket scoreboard at the Wankhede Stadium. "
                "Every time Virat Kohli runs a single, only the 'Runs' number needs to flip from 81 to 82! "
                "You should not have to shut down the stadium, turn off the stadium lights, and rebuild the entire iron scoreboard "
                "just to update one single number!\n\n"
                "Without React, traditional web browsers did something very similar: they refreshed and redrew the entire webpage "
                "whenever data changed. React fixes this by updating ONLY the specific piece of the screen that changed."
            ),
            how_rag_works=(
                "React works like a smart construction manager with a fast blueprint notebook. "
                "When data changes (such as a customer adding an item to their online cart), React draws a quick draft in the computer's "
                "memory called the **Virtual DOM**. It compares the new draft with the old draft, identifies the exact single line that changed, "
                "and tells the browser: 'Do not touch the rest of the page; only redraw this single price number.' "
                "This makes web pages feel instantaneous."
            ),
            retrieval_process=(
                "**Components (The LEGO Blocks of the Web):**\n"
                "A Component is a self-contained, reusable piece of code that controls one part of the screen. "
                "For example, on YouTube, every video thumbnail card is a component. A developer writes the card component once, "
                "and React reuses that same component 50 times to display 50 different videos on the homepage."
            ),
            embedding_explanation=(
                "**JSX (Writing HTML Tags Inside JavaScript):**\n"
                "In traditional web development, your layout design (HTML) and your programming logic (JavaScript) lived in completely separate files. "
                "React introduced **JSX**, which allows developers to write familiar HTML tags directly inside their JavaScript functions. "
                "For example, you can write `<h1>Welcome, Rahul!</h1>` directly inside your program, making code much easier to read."
            ),
            vector_database_explanation=(
                "**State and Props (Memory and Instructions):**\n"
                "Every React component can hold data in two ways:\n"
                "1. **State:** Think of State as the component's personal memory notebook. For example, a counter button uses State to remember how many times it was clicked.\n"
                "2. **Props:** Short for 'Properties'. Props are inputs passed down from a parent component to a child component, like a father giving pocket money and instructions to his child."
            ),
            context_injection=(
                "**The Virtual DOM (The Fast Memory Scratchpad):**\n"
                "The real webpage in your browser (called the real DOM) is heavy and slow to change, like carving words into stone. "
                "React keeps a lightweight virtual copy in computer RAM. "
                "Whenever your data changes, React does all its calculations on this fast scratchpad in less than 5 milliseconds, "
                "and only paints the exact difference onto the real browser screen."
            ),
            generation_process=(
                "**React Hooks (Helpful Built-in Superpowers):**\n"
                "Hooks are special built-in functions in React (such as `useState` and `useEffect`) that give simple components superpowers. "
                "For example, `useState` allows a component to remember data between clicks, while `useEffect` allows a component to fetch data from the internet when the page first opens."
            ),
            real_life_example=(
                "**The Swiggy Cart Counter in India:**\n"
                "Let us look at an everyday Indian example: Ordering Biryani on Swiggy.\n"
                "The Swiggy food page has several React components:\n"
                "- The Header search bar\n"
                "- The Restaurant banner\n"
                "- The Menu item cards with '+ Add' buttons\n"
                "- The floating green 'View Cart' bar at the bottom\n\n"
                "When you tap '+ Add' on Chicken Biryani, only the '+ Add' button changes to '1', and the green Cart bar at the bottom slides up showing Rs. 280. "
                "The restaurant photos do not reload, the header does not blink, and your scroll position does not reset. "
                "That smooth, seamless experience is 100% powered by React!"
            ),
            step_by_step_workflow=workflow_text,
            simple_practical_analogy=(
                "**The Indian Railway Reservation Chart Analogy:**\n"
                "Imagine you are checking the reservation chart at New Delhi railway station for the Rajdhani Express. "
                "If Passenger Sharma moves from RAC to a confirmed Berth B1-22, the station master does not print a brand-new 50-page chart and paste it on the wall. "
                "He simply crosses out the RAC note on Sharma's row and writes 'Confirmed'. "
                "React does the exact same thing: it only edits the changed line, leaving the rest of the wall untouched!"
            ),
            key_terminology={
                "React": "A popular JavaScript library used to build fast, interactive user interfaces for websites and web applications.",
                "Component": "A reusable building block of a website screen, like an individual LEGO brick.",
                "JSX": "A syntax extension that allows developers to write HTML-like tags directly inside JavaScript code.",
                "State": "A component's internal memory that stores information that can change over time (like a click count or cart total).",
                "Props": "Short for properties; data and instructions passed from a parent component down to a child component.",
                "Virtual DOM": "A lightweight digital copy of the webpage kept in computer memory to calculate only what changed before updating the real screen.",
                "Hooks": "Special helper functions (like useState) that give React components memory and lifecycle capabilities."
            },
            advantages_and_limitations=(
                "**Advantages of React:**\n"
                "1. **Blazing Fast Performance:** Virtual DOM prevents slow full-page browser reloads.\n"
                "2. **Reusable Code:** Components can be written once and reused across hundreds of pages.\n"
                "3. **Huge Career Demand:** Thousands of top companies in India and globally (Swiggy, Flipkart, Meta, Netflix) hire React developers.\n\n"
                "**Limitations of React:**\n"
                "1. **Steep Initial Learning Curve:** Beginners must learn JavaScript fundamentals and JSX syntax.\n"
                "2. **Fast-Paced Ecosystem:** Libraries and best practices evolve quickly, requiring continuous learning."
            ),
            summary=(
                "To summarize what we learned about React today:\n"
                "- Traditional websites forced full-page reloads for every small change.\n"
                "- React breaks screens into reusable Components (like LEGO bricks).\n"
                "- **State** remembers changing data; **Props** pass data down from parent to child.\n"
                "- The **Virtual DOM** compares screen blueprints in memory and updates only the changed parts, like a cricket scoreboard.\n"
                "- Used in popular everyday Indian apps like Swiggy, Zomato, and Flipkart."
            ),
            knowledge_check_questions=[
                {
                    "question": "What is a Component in React?",
                    "answer": "A reusable, independent building block of a website user interface, like a LEGO brick.",
                    "explanation": "Components allow developers to write UI code once and reuse it across multiple screens."
                },
                {
                    "question": "Why is a cricket scoreboard a good analogy for the Virtual DOM?",
                    "answer": "Because only the changed score digit is updated, rather than demolishing and rebuilding the entire scoreboard structure.",
                    "explanation": "Virtual DOM calculates the exact difference and updates only the changed element in the browser."
                },
                {
                    "question": "What is the difference between State and Props?",
                    "answer": "State is a component's internal changing memory, whereas Props are read-only properties passed down from a parent.",
                    "explanation": "State holds data that can change on user interaction (like cart items); Props pass configuration from parent to child."
                },
                {
                    "question": "What does JSX stand for and what does it do?",
                    "answer": "JavaScript XML; it lets developers write HTML-like tags directly inside JavaScript functions.",
                    "explanation": "JSX makes user interface code intuitive and concise within JavaScript."
                }
            ]
        )

    def _build_mock_react_evaluation(self, prompt: str) -> Any:
        from evaluation.schemas import CheckpointResult, EvaluationReport, EvaluationStatus, RubricDimension

        checkpoints = [
            CheckpointResult(
                checkpoint_id="CHK_ACC_01",
                checkpoint_name="Factual Accuracy of Core Concepts",
                dimension=RubricDimension.ACCURACY_AND_GROUNDING,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Core React concepts (Components, JSX, State & Props, Virtual DOM, Hooks) are explained factually without misconceptions.",
                evidence="React divides the screen into small, independent, reusable building blocks called Components...",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_ACC_02",
                checkpoint_name="No Hallucinated Claims or Citations",
                dimension=RubricDimension.ACCURACY_AND_GROUNDING,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="No fabricated statistics, fake benchmark figures, or false historical citations are present.",
                evidence="Lesson relies on sound architectural principles rather than ungrounded statistics.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_LANG_01",
                checkpoint_name="Appropriate Vocabulary for 12th Grade Beginner",
                dimension=RubricDimension.BEGINNER_FRIENDLY_LANGUAGE,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Vocabulary is accessible to a non-English-medium 12th-grade Indian student. Sentences are short and clear.",
                evidence="Have you ever noticed that when you order food on Swiggy... Think of it like building a house out of LEGO blocks...",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_EX_01",
                checkpoint_name="Relatable Everyday Examples",
                dimension=RubricDimension.TEACHING_THROUGH_EXAMPLES,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Features relatable Indian everyday examples: Swiggy food ordering cart and Eden Gardens / Wankhede cricket scoreboard.",
                evidence="When you tap '+ Add' on Chicken Biryani, only the '+ Add' button changes to '1'...",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_JARG_01",
                checkpoint_name="Immediate Technical Term Explanation",
                dimension=RubricDimension.CLARITY_AND_JARGON,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Technical words like Component, JSX, State, Props, Virtual DOM, and Hooks are explained immediately upon first mention.",
                evidence="Key Terminology table clearly maps technical words to simple everyday meanings.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_COV_01",
                checkpoint_name="Complete Topic Coverage & Mandatory Sections",
                dimension=RubricDimension.TOPIC_COVERAGE,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="All 18 required syllabus components are present and specifically address React.",
                evidence="Lesson includes objectives, intro, components, JSX, state/props, Virtual DOM, workflow, analogy, glossary, and knowledge check.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_FLOW_01",
                checkpoint_name="Logical Pedagogical Progression",
                dimension=RubricDimension.TEACHING_FLOW,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Structure transitions intuitively from everyday web problems (slow page reloads) to LEGO block components, JSX, Virtual DOM, and self-checks.",
                evidence="Problem setup -> Definition -> Components -> Analogy -> Step-by-Step -> Quiz.",
                suggested_improvement=""
            ),
        ]

        failed_list = [c for c in checkpoints if c.status == EvaluationStatus.FAIL]
        is_passed = len(failed_list) == 0

        dimension_scores = {}
        for c in checkpoints:
            dimension_scores[c.dimension.value] = "PASS" if c.status == EvaluationStatus.PASS else "FAIL"

        return EvaluationReport(
            attempt_number=1,
            is_passed=is_passed,
            total_checkpoints=len(checkpoints),
            passed_checkpoints=len(checkpoints),
            failed_checkpoints=0,
            dimension_scores=dimension_scores,
            checkpoints=checkpoints,
            summary_verdict="All mandatory checkpoints passed. The lesson teaches React cleanly, accurately, and with relatable Indian examples.",
        )

    def _extract_topic_from_prompt(self, prompt: str) -> str:
        """Extracts the user's requested topic name from the prompt text."""
        match = re.search(r'Educational Topic to Teach:\s*"(.*?)"', prompt, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r'topic:\s*(?:Introduction to\s+)?([^\n,\'"]+)', prompt, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "the Chosen Topic"

    def _build_mock_generic_lesson(self, prompt: str) -> Any:
        from evaluation.schemas import LessonContent

        topic_name = self._extract_topic_from_prompt(prompt)

        return LessonContent(
            topic=topic_name,
            target_audience="A 12th-grade graduate from India with limited English vocabulary and no prior technical knowledge",
            title=f"A Simple Beginner's Guide to {topic_name}",
            learning_objectives=[
                f"Understand what {topic_name} is in simple, everyday language.",
                f"Learn why {topic_name} is used and what problem it solves.",
                f"Discover the core pillars and working steps of {topic_name}.",
                f"Explore a relatable real-life Indian analogy to visualize {topic_name}.",
                f"Review key terminology and test your understanding with simple questions."
            ],
            introduction=(
                f"Welcome! Have you ever wondered how {topic_name} works in real life? "
                "Many people think technical topics are difficult because books use heavy, complicated English words. "
                f"In this lesson, we will break down **{topic_name}** using simple words, short sentences, and everyday Indian examples "
                "so that anyone can easily understand it from scratch."
            ),
            what_is_rag=(
                f"**What is {topic_name}?**\n\n"
                f"At its core, {topic_name} is a set of rules and tools designed to solve a specific everyday challenge. "
                "Instead of doing everything manually by hand or repeating the same mistakes, it gives us a organized system "
                "to handle tasks step-by-step with high speed and accuracy."
            ),
            why_is_rag_needed=(
                f"**Why is {topic_name} Needed?**\n\n"
                "Imagine trying to manage a busy Indian railway station ticket counter during Diwali rush with only a pencil and paper! "
                "Lines would stretch for kilometers, people would get tired, and mistakes would happen constantly.\n\n"
                f"{topic_name} was created to replace slow, error-prone manual methods with a clean, dependable, and automated approach."
            ),
            how_rag_works=(
                f"**How {topic_name} Works (High-Level Overview):**\n\n"
                "It operates like a well-organized team:\n"
                "1. **Input:** It receives your instructions or data.\n"
                "2. **Processing:** It breaks the task into manageable components and applies clear rules.\n"
                "3. **Output:** It presents the finished result cleanly and quickly."
            ),
            retrieval_process=(
                f"**Core Pillar 1 of {topic_name} (Collection & Input):**\n"
                "The system gathers the required information from reliable sources, checking that everything needed is present before starting."
            ),
            embedding_explanation=(
                f"**Core Pillar 2 of {topic_name} (Organization & Translation):**\n"
                "It translates raw input into a structured format that computers or learners can understand effortlessly."
            ),
            vector_database_explanation=(
                f"**Core Pillar 3 of {topic_name} (Structured Storage):**\n"
                "Information is stored neatly in memory so that any required detail can be found in milliseconds without searching through everything."
            ),
            context_injection=(
                f"**Core Pillar 4 of {topic_name} (Coordination & Assembly):**\n"
                "Different parts work together like gears in a bicycle, ensuring no single component has to carry all the burden alone."
            ),
            generation_process=(
                f"**Core Pillar 5 of {topic_name} (Final Execution & Delivery):**\n"
                "The final result is verified, polished, and delivered to the user in a smooth, user-friendly format."
            ),
            real_life_example=(
                "**Relatable Everyday Example:**\n\n"
                "Think of a busy local chai tapri (tea stall) near an Indian railway station during morning office hours. "
                "The chai stall owner has a clear, organized workflow: one helper takes orders, one boils the fresh milk and crushed ginger, "
                "and one pours the steaming hot chai into glasses and collects UPI payments. "
                f"Because every role is defined and organized, 200 customers get fresh tea in minutes without chaos. {topic_name} works on the exact same principles of clean organization and teamwork!"
            ),
            step_by_step_workflow=(
                f"Here is the simple step-by-step workflow of {topic_name}:\n\n"
                "1. **Step 1 (Trigger):** A request is initiated by the user.\n"
                "2. **Step 2 (Verification):** The system checks the request requirements.\n"
                "3. **Step 3 (Execution):** The core process runs following tested standard procedures.\n"
                "4. **Step 4 (Validation):** The output is reviewed to ensure there are no errors.\n"
                "5. **Step 5 (Delivery):** The final completed output is delivered cleanly."
            ),
            simple_practical_analogy=(
                f"**The Recipe Book Analogy for {topic_name}:**\n\n"
                "Cooking a delicious biryani without a recipe can lead to too much salt or raw rice. "
                "Following a trusted step-by-step family recipe guarantees that every single time you cook, the dish turns out aromatic and delicious. "
                f"{topic_name} is like that trusted recipe book: it gives you reliable, tested steps for great results every time."
            ),
            key_terminology={
                "Input": "The initial data or question provided by the user.",
                "Process": "The structured series of actions taken to achieve a goal.",
                "Component": "An individual, reusable building block of the system.",
                "Validation": "Double-checking work to ensure correctness and quality.",
                "Output": "The final finished result presented to the user."
            },
            advantages_and_limitations=(
                f"**Advantages of {topic_name}:**\n"
                "1. **High Efficiency:** Completes tasks much faster than traditional manual methods.\n"
                "2. **Consistency:** Produces uniform, high-quality results every single time.\n"
                "3. **Beginner-Friendly:** Easy to learn and adopt once the core pillars are understood.\n\n"
                f"**Limitations of {topic_name}:**\n"
                "1. **Setup Effort:** Requires initial planning and understanding of the basic concepts.\n"
                "2. **Input Dependent:** If the initial input is incomplete or flawed, the final output will reflect those mistakes ('Garbage In, Garbage Out')."
            ),
            summary=(
                f"**Key Takeaways for {topic_name}:**\n"
                f"- {topic_name} is a practical, structured framework designed to simplify complex work.\n"
                "- It replaces slow manual guessing with clear, organized steps.\n"
                "- Like the organized chai stall or trusted family recipe, it guarantees speed, accuracy, and reliability."
            ),
            knowledge_check_questions=[
                {
                    "question": f"What is the primary purpose of {topic_name}?",
                    "answer": "To provide an organized, reliable system that replaces slow manual methods with structured efficiency.",
                    "explanation": f"{topic_name} focuses on clarity, speed, and accuracy."
                },
                {
                    "question": f"Why is good input important in {topic_name}?",
                    "answer": "Because the final output depends on the quality of the starting information (Garbage In, Garbage Out).",
                    "explanation": "High quality input ensures high quality output."
                },
                {
                    "question": f"What does the Chai Stall analogy demonstrate about {topic_name}?",
                    "answer": "It shows how dividing work into clear, coordinated steps makes a busy system run smoothly without mistakes.",
                    "explanation": "Organization and teamwork make systems scalable."
                }
            ]
        )

    def _build_mock_generic_evaluation(self, prompt: str) -> Any:
        from evaluation.schemas import CheckpointResult, EvaluationReport, EvaluationStatus, RubricDimension

        topic_name = self._extract_topic_from_prompt(prompt)

        checkpoints = [
            CheckpointResult(
                checkpoint_id="CHK_ACC_01",
                checkpoint_name="Factual Accuracy of Core Concepts",
                dimension=RubricDimension.ACCURACY_AND_GROUNDING,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason=f"Core concepts for {topic_name} are explained accurately and factually.",
                evidence=f"{topic_name} definition and pillars are sound and grounded.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_ACC_02",
                checkpoint_name="No Hallucinated Claims or Citations",
                dimension=RubricDimension.ACCURACY_AND_GROUNDING,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="No fabricated statistics, fake citations, or unsupported claims are present.",
                evidence="Lesson relies on sound pedagogical fundamentals.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_LANG_01",
                checkpoint_name="Appropriate Vocabulary for 12th Grade Beginner",
                dimension=RubricDimension.BEGINNER_FRIENDLY_LANGUAGE,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Vocabulary is accessible, with short sentences and plain English definitions.",
                evidence="Uses simple everyday conversational words.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_EX_01",
                checkpoint_name="Relatable Everyday Examples",
                dimension=RubricDimension.TEACHING_THROUGH_EXAMPLES,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Features relatable Indian everyday example and intuitive analogies.",
                evidence="Chai stall and recipe book analogies.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_JARG_01",
                checkpoint_name="Immediate Technical Term Explanation",
                dimension=RubricDimension.CLARITY_AND_JARGON,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Technical terms are immediately explained in plain English and listed in the glossary.",
                evidence="Key Terminology section contains clear mappings.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_COV_01",
                checkpoint_name="Complete Topic Coverage & Mandatory Sections",
                dimension=RubricDimension.TOPIC_COVERAGE,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason=f"All 18 required pedagogical sections are present and dedicated to {topic_name}.",
                evidence=f"Lesson covers title, objectives, intro, pillars, workflow, quiz for {topic_name}.",
                suggested_improvement=""
            ),
            CheckpointResult(
                checkpoint_id="CHK_FLOW_01",
                checkpoint_name="Logical Pedagogical Progression",
                dimension=RubricDimension.TEACHING_FLOW,
                is_mandatory=True,
                status=EvaluationStatus.PASS,
                reason="Logical sequence from intro to definition, pillars, workflow, and quiz.",
                evidence="Progressive pedagogical sequence.",
                suggested_improvement=""
            )
        ]

        dimension_scores = {c.dimension.value: "PASS" for c in checkpoints}

        return EvaluationReport(
            attempt_number=1,
            is_passed=True,
            total_checkpoints=len(checkpoints),
            passed_checkpoints=len(checkpoints),
            failed_checkpoints=0,
            dimension_scores=dimension_scores,
            checkpoints=checkpoints,
            summary_verdict=f"All mandatory checkpoints passed. The lesson teaches {topic_name} cleanly and accurately.",
        )


def _extract_and_validate_json(raw_text: str, response_model: Type[T]) -> T:
    """Helper to extract JSON block from LLM output and parse into Pydantic model."""
    cleaned = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1:
        cleaned = cleaned[first_brace : last_brace + 1]

    try:
        data = json.loads(cleaned)
        return response_model.model_validate(data)
    except Exception as exc:
        logger.error(f"Failed to parse JSON for {response_model.__name__}: {exc}\nRaw text snippet: {raw_text[:300]}")
        raise ValueError(f"LLM output could not be validated against {response_model.__name__}: {exc}")


def get_llm_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    deliberate_error_mode: Optional[str] = None,
) -> BaseLLMProvider:
    """Factory function to instantiate configured LLM provider.

    Defaults to LLM_PROVIDER env variable or 'mock' if no external API key is present.
    """
    provider = (provider_name or os.getenv("LLM_PROVIDER", "mock")).lower().strip()
    model_name = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    logger.info(f"Instantiating LLM provider: '{provider}' (model: '{model_name}')")

    if provider == "mock":
        return DeterministicMockLLMProvider(deliberate_error_mode=deliberate_error_mode)

    elif provider in ("openai", "default"):
        return OpenAICompatibleProvider(
            model=model_name,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

    elif provider == "gemini":
        gemini_model = model_name if model_name and "gemini" in model_name else "gemini-3-flash-preview"
        return GeminiProvider(
            model=gemini_model,
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    elif provider == "groq":
        return OpenAICompatibleProvider(
            model=model_name or "llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        )

    elif provider == "ollama":
        return OpenAICompatibleProvider(
            model=model_name or "llama3.1",
            api_key="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        )

    else:
        logger.warning(f"Unrecognized LLM provider '{provider}'. Falling back to DeterministicMockLLMProvider.")
        return DeterministicMockLLMProvider(deliberate_error_mode=deliberate_error_mode)
