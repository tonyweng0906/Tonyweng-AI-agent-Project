import json
from pathlib import Path
from typing import Literal

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field

from datetime import datetime
from zoneinfo import ZoneInfo


from courtmate.live_context import build_live_context
from courtmate.query_router import route_query
from courtmate.rag import rag

from courtmate.config import (
    OPENAI_API_KEY,
    OPENAI_JUDGE_MODEL,
    TIMEZONE,
)

GROUND_TRUTH_PATH = Path(
    "data/ground-truth-operational.json"
)
RESULTS_PATH = Path(
    "data/evaluation/operational-rag-evaluation-results.csv"
)


class OperationalJudgment(BaseModel):
    score: Literal["good", "bad"] = Field(
        description=(
            "Whether the answer is correct and fully grounded "
            "in the authoritative operational context."
        )
    )
    reasoning: str


JUDGE_INSTRUCTIONS = """
You evaluate Badminton Mate answers that use live PostgreSQL data.

The OPERATIONAL CONTEXT is the authoritative ground truth for this run.
The intent tells you what kind of operational question the user asked.

Important rules:

1. The database has already filtered price records by active status and
   effective date. Prices returned in OPERATIONAL CONTEXT are current.
   Do not reject a price because its effective_from date is earlier than
   the evaluation date.

2. Numeric formats are equivalent:
   2, 2.0, and 2.00 represent the same value.

3. For intent "price":
   - verify the item, amount, currency, and billing unit when relevant;
   - do not require a coach unless the question asks about a coach.

4. For intent "schedule":
   - the user is asking about existing scheduled activities;
   - listing those activities is correct;
   - do not confuse scheduled activities with available booking times;
   - an answer is especially clear when it says these are not available
     booking slots;
   - a heading may show the complete requested date range;
   - only table rows or explicitly listed activities count as activity dates;
   - dates with no scheduled activities may be omitted.

5. For intent "availability":
   - the answer must list courts and times that are available for booking.

6. Treat route_checks as deterministic evidence.
   Do not invent a failed requirement when its route check is true.

- EVALUATION_DATE is the exact current date for this evaluation.
Never substitute your own current date or model knowledge cutoff.

- CALENDAR_FACTS is calculated by Python and is authoritative.
Do not claim a weekday/date combination is wrong when it agrees
with CALENDAR_FACTS.

- When every route_check is true, only mark the answer bad when you
can identify a specific factual contradiction or missing answer.
Do not invent missing requirements.

Mark the answer good when it directly answers the question and its factual
claims are supported by OPERATIONAL CONTEXT.

Mark it bad when deterministic routing checks failed, required information
is missing, or the answer contradicts OPERATIONAL CONTEXT.
""".strip()


judge_client = OpenAI(api_key=OPENAI_API_KEY)


def load_cases() -> list[dict]:
    with GROUND_TRUTH_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def evaluate_answer(
    question: str,
    intent: str,
    context: str,
    answer: str,
    route_checks: dict[str, bool],
) -> OperationalJudgment:
    context_data = json.loads(context)
    evaluation_date = datetime.now(
        ZoneInfo(TIMEZONE)
    ).date().isoformat()

    calendar_facts: dict[str, str] = {}

    for activity in context_data.get(
        "scheduled_activities",
        [],
    ):
        start_at = activity.get("start_at")

        if not start_at:
            continue

        activity_date = datetime.fromisoformat(
            start_at
        ).date()

        calendar_facts[
            activity_date.isoformat()
        ] = activity_date.strftime("%A")

    response = judge_client.responses.parse(
        model=OPENAI_JUDGE_MODEL,
        instructions=JUDGE_INSTRUCTIONS,
        input=json.dumps(
            {
                "question": question,
                "intent": intent,
                "route_checks": route_checks,
                "evaluation_date": evaluation_date,
                "calendar_facts": calendar_facts,
                "operational_context": context_data,
                "generated_answer": answer,
            },
            ensure_ascii=False,
        ),
        text_format=OperationalJudgment,
        temperature=0,
    )

    if response.output_parsed is None:
        raise RuntimeError(
            "The operational judge returned no structured result."
        )

    return response.output_parsed


def main() -> None:
    cases = load_cases()
    rows = []

    for index, case in enumerate(cases, start=1):
        question = str(case["question"])
        route = route_query(question)
        context, context_sources = build_live_context(route)
        answer_data = rag(question)

        expected_source_id = str(
            case["expected_source_id"]
        )
        context_source_ids = {
            str(source["id"])
            for source in context_sources
        }
        answer_source_ids = {
            str(source["id"])
            for source in answer_data.get("sources", [])
        }

        route_checks = {
            "intent": (
                route.intent
                == case["expected_intent"]
            ),
            "offering_type": (
                case.get("expected_offering_type") is None
                or route.offering_type
                == case["expected_offering_type"]
            ),
            "coach_name": (
                case.get("expected_coach_name") is None
                or route.coach_name
                == case["expected_coach_name"]
            ),
            "context_source": (
                expected_source_id in context_source_ids
            ),
            "answer_source": (
                expected_source_id in answer_source_ids
            ),
            "required_context_values": all(
                str(value).lower() in context.lower()
                for value in case.get(
                    "required_context_values",
                    [],
                )
            ),
        }

        judgment = evaluate_answer(
            question=question,
            intent=route.intent,
            context=context,
            answer=str(answer_data["answer"]),
            route_checks=route_checks,
        )
        deterministic_passed = all(
            route_checks.values()
        )

        deterministic_score = (
            "good"
            if deterministic_passed
            else "bad"
        )

        if not deterministic_passed:
            judgment.score = "bad"
            failed_checks = [
                name
                for name, passed in route_checks.items()
                if not passed
            ]
            judgment.reasoning = (
                "Deterministic checks failed: "
                + ", ".join(failed_checks)
                + ". "
                + judgment.reasoning
            )
        judge_score = judgment.score

        if deterministic_score == "bad":
            final_score = "bad"
        elif judge_score == "good":
            final_score = "good"
        else:
            final_score = "needs_review"

        rows.append(
            {
                "question": question,
                "expected_intent": case["expected_intent"],
                "actual_intent": route.intent,
                "expected_offering_type": case.get(
                    "expected_offering_type"
                ),
                "actual_offering_type": route.offering_type,
                "expected_coach_name": case.get(
                    "expected_coach_name"
                ),
                "actual_coach_name": route.coach_name,
                "resolved_date": route.target_date,
                "resolved_end_date": route.target_end_date,
                "route_checks": json.dumps(route_checks),
                "answer": answer_data["answer"],
                "deterministic_score": deterministic_score,
                "judge_score": judge_score,
                "score": final_score,
                "reasoning": judgment.reasoning,
            }
        )

        print(
            f"[{index}/{len(cases)}] "
            f"{final_score}: {question}"
        )

    RESULTS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    dataframe = pd.DataFrame(rows)
    dataframe.to_csv(RESULTS_PATH, index=False)

    good_count = int(
        (dataframe["score"] == "good").sum()
    )

    bad_count = int(
        (dataframe["score"] == "bad").sum()
    )

    review_count = int(
        (
            dataframe["score"]
            == "needs_review"
        ).sum()
    )

    deterministic_good_count = int(
        (
            dataframe["deterministic_score"]
            == "good"
        ).sum()
    )

    judge_good_count = int(
        (
            dataframe["judge_score"]
            == "good"
        ).sum()
    )

    print()
    print(
        "Deterministic operational checks: "
        f"{deterministic_good_count}/{len(dataframe)}"
    )
    print(
        "LLM judge good answers: "
        f"{judge_good_count}/{len(dataframe)}"
    )
    print(f"Final good: {good_count}")
    print(f"Final bad: {bad_count}")
    print(f"Needs review: {review_count}")
    print(f"Saved results to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()

