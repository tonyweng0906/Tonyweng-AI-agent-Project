import json
from time import perf_counter
from typing import Any

from openai import OpenAI

from courtmate.config import (
    OPENAI_API_KEY,
    OPENAI_JUDGE_MODEL,
    OPENAI_MODEL,
)
from courtmate.ingest import (
    load_boost,
    load_index,
)


openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
)

index = load_index()
boost = load_boost()

PROMPT_TEMPLATE = """
You are CourtMate, an assistant for a badminton club.

Answer the USER QUESTION using only the provided CONTEXT.

Instructions:
1. Give the direct answer in the first sentence.
2. Include all necessary details found in the context.
3. Do not invent prices, schedules, availability, policies,
   coach qualifications, or booking status.
4. Static knowledge-base information must not be presented as
   live availability.
5. If the context does not contain enough information, say:
   "I don't have enough information in the club knowledge base
   to answer that."
6. Keep the answer concise and customer-friendly.
7. Finish with a short source list using document titles.

USER QUESTION:
{question}

CONTEXT:
{context}
""".strip()

EVALUATION_PROMPT_TEMPLATE = """
You are evaluating an answer produced by a badminton club
retrieval-augmented generation system.

Evaluate how well the GENERATED ANSWER responds to the USER QUESTION.

Use exactly one of these labels:

RELEVANT:
The answer directly answers the question, is sufficiently complete,
and does not make unsupported claims.

PARTLY_RELEVANT:
The answer contains useful information but is incomplete, vague,
indirect, or contains a minor unsupported detail.

NON_RELEVANT:
The answer fails to answer the question, contains major unsupported
claims, or is substantially incorrect.

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

def search(
    query: str,
    num_results: int = 5,
) -> list[dict[str, Any]]:
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    return index.search(
        query=query.strip(),
        filter_dict={},
        boost_dict=boost,
        num_results=num_results,
    )

def build_prompt(
    question: str,
    search_results: list[dict[str, Any]],
) -> str:
    context_entries = [
        DOCUMENT_TEMPLATE.format(**document)
        for document in search_results
    ]

    context = "\n\n".join(context_entries)

    return PROMPT_TEMPLATE.format(
        question=question,
        context=context,
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
) -> dict[str, Any]:
    started_at = perf_counter()

    search_results = search(
        query=question,
        num_results=num_results,
    )

    prompt = build_prompt(
        question=question,
        search_results=search_results,
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

