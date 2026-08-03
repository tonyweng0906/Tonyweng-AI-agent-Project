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

from courtmate.live_context import (
    build_live_context,
)
from courtmate.query_router import (
    route_query,
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

BOOKING CAPABILITY:
- You can check court availability but cannot create, reserve,
  hold, modify, or cancel a booking.
- Never imply that a booking has been or can be completed.
- After presenting availability, ask which options the user wants
  to review or advise them to contact the club to complete booking.

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

LIVE OPERATIONAL DATA:
- For current prices, court availability, and schedules, treat the
  LIVE OPERATIONAL DATA as the authoritative source.
- Never replace live operational data with static knowledge-base data.
- Do not invent missing prices, courts, dates, time slots, coaches,
  bookings, or availability.
- If a date is required but missing, ask the user for a date.
- Clearly include the resolved calendar date in schedule and
  availability answers.
- When several courts are available at the same time, group them by
  time slot.
- Use "Current price catalog" or "Live court schedule" as the source
  when live operational data is used.

SCHEDULE ANSWER RULES:
- Treat every returned schedule row as an existing scheduled
  activity, not as an available booking time.
- Never imply that a scheduled private lesson or class is available
  to join or book.
- For a coach schedule question, include only activities belonging
  to the requested coach.
- Sort schedule entries chronologically.
- Include the date, start time, end time, activity name, and court
  for every listed schedule entry.
- Do not omit the court name when it is present in the live data.
- Use a compact Markdown table when more than three schedule entries
  are returned.
- Use these table columns:
  Date | Time | Activity | Court
- Do not create a separate heading for every date.
- The live schedule context contains result_count.
- If you mention the number of activities, copy result_count exactly.
- Never calculate or estimate the number of schedule entries yourself.
- Do not state a total unless result_count is present.
- If no matching activities are returned, clearly say that no
  scheduled activities were found for the requested coach and date
  range.
- Do not describe an empty result as a knowledge-base limitation.
- End with:
  "Source: Live court schedule"
- Do not offer to create or complete a booking.
- A safe follow-up is:
  "Would you like me to check whether other courts are available
  during any of these time slots?"
  Schedule format example:

Here is Coach Amy's schedule from August 3 to August 9, 2026.

| Date | Time | Activity | Court |
|---|---|---|---|
| Mon, Aug 3 | 10:00-11:00 AM | Private lesson | Court 2 |
| Tue, Aug 4 | 6:00-7:00 PM | Beginner skills class | Court 3 |
| Thu, Aug 6 | 6:00-7:00 PM | Beginner skills class | Court 3 |

These are existing scheduled activities and should not be treated
as available booking times.

Source: Live court schedule

CONVERSATION HISTORY:
{conversation_history}

USER QUESTION:
{question}

LIVE OPERATIONAL DATA:
{operational_context}

STATIC KNOWLEDGE-BASE CONTEXT:
{context}

""".strip()

EVALUATION_PROMPT_TEMPLATE = """
You are evaluating an answer produced by Badminton Mate.

The application can use two kinds of data:

1. Static knowledge-base documents for policies and club information.
2. Live PostgreSQL operational data for prices, schedules,
   court availability, coaches, and current activities.

QUERY INTENT:
{query_intent}

LIVE OPERATIONAL DATA USED:
{uses_live_data}

Evaluation rules:

- Any stated totals, dates, times, coach names, and court names must
  be internally consistent with the generated answer.
- If the answer states an activity count that does not match the
  number of listed activities, label it PARTLY_RELEVANT.
- If LIVE OPERATIONAL DATA USED is true, treat the answer as being
  based on a current PostgreSQL query.
- Do not reject an availability, schedule, or price answer merely
  because it contains current operational information.
- For an availability question, a list of dates, time slots, and
  available courts is a valid direct answer.
- For a price question, current catalog prices from PostgreSQL are
  authoritative.
- For a schedule question, scheduled activities from PostgreSQL are
  authoritative.
- The answer must directly address the user's question.
- The answer must not invent information that was not returned by
  the selected data source.
- If requested information is unavailable, clearly explaining that
  limitation is an appropriate answer.

Use exactly one label:

RELEVANT:
The answer directly and appropriately responds using the selected
data source.

PARTLY_RELEVANT:
The answer contains useful information but omits an important
available detail or is unnecessarily vague.

NON_RELEVANT:
The answer does not address the question, contradicts the selected
data source, or makes major unsupported claims.

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
    operational_context: str = (
        "No live operational data was requested."
    ),
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
        conversation_history=(
            conversation_history
        ),
        operational_context=(
            operational_context
        ),
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
    query_intent: str = "knowledge",
    uses_live_data: bool = False,
) -> tuple[dict[str, str], dict[str, int]]:
    prompt = (
        EVALUATION_PROMPT_TEMPLATE.format(
            question=question,
            answer=answer,
            query_intent=query_intent,
            uses_live_data=str(
                uses_live_data
            ).lower(),
        )
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
    route = route_query(
        question=question,
        history=history,
    )

    (
        operational_context,
        operational_sources,
    ) = build_live_context(
        route
    )

    search_results = []

    if route.intent == "knowledge":
        retrieval_query = (
            build_retrieval_query(
                question=question,
                history=history,
            )
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
            search_results = (
                rerank_documents(
                    question=(
                        retrieval_query
                    ),
                    documents=(
                        search_results
                    ),
                    model=RERANK_MODEL,
                )
            )

        search_results = (
            search_results[
                :num_results
            ]
        )

    prompt = build_prompt(
        question=question,
        search_results=search_results,
        history=history,
        operational_context=(
            operational_context
        ),
    )

    answer, generation_tokens = llm(
        prompt=prompt,
        model=model,
    )

    relevance_result, evaluation_tokens = (
        evaluate_relevance(
            question=question,
            answer=answer,
            query_intent=route.intent,
            uses_live_data=bool(
                operational_sources
            ),
        )
    )

    response_time = (
        perf_counter() - started_at
    )

    return {
        "answer": answer,
        "sources": (
            operational_sources
            + [
                {
                    "id": document["id"],
                    "title": document["title"],
                    "category": document[
                        "category"
                    ],
                }
                for document in search_results
            ]
        ),
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
        "query_intent": route.intent,
        "resolved_date": (
            route.target_date
        ),
        "resolved_end_date": (
            route.target_end_date
        ),
    }

