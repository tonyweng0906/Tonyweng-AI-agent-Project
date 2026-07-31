import json
from time import perf_counter
from typing import Any

from openai import OpenAI

from courtmate.config import (
    OPENAI_API_KEY,
    OPENAI_JUDGE_MODEL,
    OPENAI_MODEL,
)

from courtmate.hybrid_search import (
    HybridSearch,
)

from courtmate.rerank import (
    RERANK_CANDIDATE_COUNT,
    RERANK_ENABLED,
    RERANK_MODEL,
    rerank_documents,
)

openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
)

retriever = HybridSearch()

PROMPT_TEMPLATE = """
You are Badminton Mate, a friendly assistant for a badminton club.

First determine whether the user is having a general conversation
or asking for factual badminton club information.

GENERAL CONVERSATION:
- Respond naturally to greetings, thanks, farewells, and questions
  about who you are.
- General conversation does not require knowledge-base support.
- Do not include sources for general conversation.

BADMINTON CLUB QUESTIONS:
- Answer factual club questions using only the provided CONTEXT.
- Give the direct answer in the first sentence.
- Include the necessary details found in the context.
- Do not invent prices, schedules, availability, policies,
  coach qualifications, membership terms, or booking status.
- Static knowledge-base information must not be presented as
  live availability.
- If the context contains partial information, answer the supported
  part first, then clearly explain what information is missing.
- Do not discard useful context just because it does not answer every
  part of the question.
- Distinguish booking duration or policy from exact start times and
  live availability.
- Use the following fallback only when the context contains no useful
  information:
  "I don't have enough information in the club knowledge base
  to answer that."
PARTIAL ANSWER RULE:
- Before using the insufficient-information fallback, identify every
  fact in the context that is relevant to any part of the question.
- Always provide supported partial information before explaining what
  is unavailable.
- A time-slot duration is different from an exact start time.
- If the context says bookings use 60-minute time slots, you must
  mention the 60-minute duration even when exact start times or live
  availability are unavailable.

Example:
User question:
Are there any specific time slots available for court bookings?

Context information:
Court bookings use 60-minute time slots. Exact start times and live
availability are not stored in the knowledge base.

Correct answer:
Court bookings use 60-minute time slots. However, the knowledge base
does not contain exact start times or live court availability, so
please confirm those details with the club.
- When useful, ask one short follow-up question.
- Finish with a short source list using document titles.

CONVERSATION HISTORY:
{conversation_history}

USER QUESTION:
{question}

CONTEXT:
{context}
""".strip()

EVALUATION_PROMPT_TEMPLATE = """
You are evaluating an answer produced by Badminton Mate,
a badminton club retrieval-augmented generation system.

Evaluate whether the GENERATED ANSWER appropriately responds
to the USER QUESTION.

Important:
- The assistant only has access to a static club knowledge base.
- The knowledge base may not contain live availability,
  exact start times, or current booking status.
- If the requested information is unavailable, an answer that
  clearly explains this limitation without inventing facts is
  a correct and relevant answer.
- Do not penalize the answer merely because live or unavailable
  information cannot be provided.
- If partial information is available, the answer should provide
  that supported information before explaining what is missing.

Use exactly one of these labels:

RELEVANT:
The answer directly and appropriately responds to the question.
It provides all supported information available and does not invent
unsupported facts. A clear explanation that requested live or exact
information is unavailable should be classified as RELEVANT when that
is the most accurate answer possible.

PARTLY_RELEVANT:
The answer contains useful supported information but misses another
important fact that was available, is unnecessarily vague, or does
not clearly explain the limitation.

NON_RELEVANT:
The answer does not address the question, contradicts available
information, or makes major unsupported claims.

Return valid JSON only:

{{
  "relevance": "RELEVANT | PARTLY_RELEVANT | NON_RELEVANT",
  "explanation": "Brief explanation"
}}

USER QUESTION:
{question}

GENERATED ANSWER:
{answer}
""".strip()

DOCUMENT_TEMPLATE = """
Document ID: {id}
Category: {category}
Title: {title}
Content: {content}
Coach: {coach_name}
Skill level: {skill_level}
Location: {location}
""".strip()

def format_conversation_history(
    history: list[dict[str, str]] | None,
) -> str:
    """Format recent messages for the LLM prompt."""
    if not history:
        return "No previous conversation."

    formatted_messages = []

    for message in history[-8:]:
        role = message.get("role", "")
        content = message.get("content", "").strip()

        if role not in {"user", "assistant"}:
            continue

        if not content:
            continue

        speaker = (
            "User"
            if role == "user"
            else "Badminton Mate"
        )

        formatted_messages.append(
            f"{speaker}: {content}"
        )

    if not formatted_messages:
        return "No previous conversation."

    return "\n".join(formatted_messages)


def build_retrieval_query(
    question: str,
    history: list[dict[str, str]] | None,
) -> str:
    """
    Add recent user messages to the retrieval query.

    This helps resolve follow-ups such as:
    "Does she teach juniors?"
    """
    previous_user_messages = []

    for message in history or []:
        if message.get("role") != "user":
            continue

        content = message.get("content", "").strip()

        if content:
            previous_user_messages.append(content)

    query_parts = previous_user_messages[-2:]
    query_parts.append(question)

    return " ".join(query_parts)

def search(
    query: str,
    num_results: int = 5,
) -> list[dict[str, Any]]:
    if not query or not query.strip():
        raise ValueError(
            "Query cannot be empty."
        )

    return retriever.search(
        query=query.strip(),
        num_results=num_results,
    )

def build_prompt(
    question: str,
    search_results: list[dict[str, Any]],
    history: list[dict[str, str]] | None = None,
) -> str:
    context_entries = [
        DOCUMENT_TEMPLATE.format(**document)
        for document in search_results
    ]

    context = "\n\n".join(context_entries)

    if not context:
        context = "No relevant knowledge-base documents were found."

    conversation_history = (
        format_conversation_history(history)
    )

    return PROMPT_TEMPLATE.format(
        question=question,
        context=context,
        conversation_history=conversation_history,
    )

def llm(
    prompt: str,
    model: str,
) -> tuple[str, dict[str, int]]:
    response = openai_client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    usage = response.usage

    token_stats = {
        "prompt_tokens": (
            usage.input_tokens
            if usage
            else 0
        ),
        "completion_tokens": (
            usage.output_tokens
            if usage
            else 0
        ),
        "total_tokens": (
            usage.total_tokens
            if usage
            else 0
        ),
    }

    return (
        response.output_text.strip(),
        token_stats,
    )

VALID_RELEVANCE_LABELS = {
    "RELEVANT",
    "PARTLY_RELEVANT",
    "NON_RELEVANT",
}


def clean_json_text(text: str) -> str:
    text = text.strip()

    if text.startswith("```json"):
        text = text[len("```json"):]

    if text.startswith("```"):
        text = text[len("```"):]

    if text.endswith("```"):
        text = text[:-len("```")]

    return text.strip()


def evaluate_relevance(
    question: str,
    answer: str,
) -> tuple[dict[str, str], dict[str, int]]:
    prompt = EVALUATION_PROMPT_TEMPLATE.format(
        question=question,
        answer=answer,
    )

    raw_evaluation, token_stats = llm(
        prompt=prompt,
        model=OPENAI_JUDGE_MODEL,
    )

    try:
        parsed = json.loads(
            clean_json_text(raw_evaluation)
        )

        relevance = str(
            parsed.get("relevance", "UNKNOWN")
        ).strip().upper()

        explanation = str(
            parsed.get("explanation", "")
        ).strip()

        if relevance not in VALID_RELEVANCE_LABELS:
            relevance = "UNKNOWN"

        return (
            {
                "relevance": relevance,
                "explanation": explanation,
            },
            token_stats,
        )

    except json.JSONDecodeError:
        return (
            {
                "relevance": "UNKNOWN",
                "explanation": (
                    "Judge response could not be parsed."
                ),
            },
            token_stats,
        )

    
def rag(
    question: str,
    model: str = OPENAI_MODEL,
    num_results: int = 5,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()

    retrieval_query = build_retrieval_query(
    question=question,
    history=history,
    )

    retrieval_count = (
    max(
        num_results,
        RERANK_CANDIDATE_COUNT,
    )
    if RERANK_ENABLED
    else num_results
)

    search_results = search(
        query=retrieval_query,
        num_results=retrieval_count,
    )

    if RERANK_ENABLED:
        search_results = rerank_documents(
            question=retrieval_query,
            documents=search_results,
            model=RERANK_MODEL,
        )

    search_results = search_results[
        :num_results
    ]

    prompt = build_prompt(
        question=question,
        search_results=search_results,
        history=history,
    )

    answer, generation_tokens = llm(
        prompt=prompt,
        model=model,
    )

    relevance_result, evaluation_tokens = (
        evaluate_relevance(
            question=question,
            answer=answer,
        )
    )

    response_time = (
        perf_counter() - started_at
    )

    return {
        "answer": answer,
        "sources": [
            {
                "id": document["id"],
                "title": document["title"],
                "category": document["category"],
            }
            for document in search_results
        ],
        "model_used": model,
        "judge_model": OPENAI_JUDGE_MODEL,
        "response_time": response_time,
        "relevance": relevance_result[
            "relevance"
        ],
        "relevance_explanation": (
            relevance_result["explanation"]
        ),
        "prompt_tokens": generation_tokens[
            "prompt_tokens"
        ],
        "completion_tokens": generation_tokens[
            "completion_tokens"
        ],
        "total_tokens": generation_tokens[
            "total_tokens"
        ],
        "eval_prompt_tokens": evaluation_tokens[
            "prompt_tokens"
        ],
        "eval_completion_tokens": (
            evaluation_tokens[
                "completion_tokens"
            ]
        ),
        "eval_total_tokens": evaluation_tokens[
            "total_tokens"
        ],
    }

