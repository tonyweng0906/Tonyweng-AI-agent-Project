import json
from pathlib import Path
from typing import Literal

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field

from courtmate.config import (
    OPENAI_API_KEY,
    OPENAI_JUDGE_MODEL,
)
from courtmate.live_context import build_live_context
from courtmate.query_router import route_query
from courtmate.rag import rag


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
Mark the answer good only when it directly answers the question and every
price, date, time, coach, court, and availability claim is supported by that
context. Mark it bad when routing checks failed, required values are missing,
the answer contradicts the context, or scheduled activities are described as
available booking times.
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
    context: str,
    answer: str,
    route_checks: dict[str, bool],
) -> OperationalJudgment:
    response = judge_client.responses.parse(
        model=OPENAI_JUDGE_MODEL,
        instructions=JUDGE_INSTRUCTIONS,
        input=json.dumps(
            {
                "question": question,
                "route_checks": route_checks,
                "operational_context": json.loads(context),
                "generated_answer": answer,
            },
            ensure_ascii=False,
        ),
        text_format=OperationalJudgment,
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
            context=context,
            answer=str(answer_data["answer"]),
            route_checks=route_checks,
        )

        if not all(route_checks.values()):
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
                "score": judgment.score,
                "reasoning": judgment.reasoning,
            }
        )

        print(
            f"[{index}/{len(cases)}] "
            f"{judgment.score}: {question}"
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
    print()
    print(
        f"Good operational answers: {good_count}/{len(dataframe)}"
    )
    print(f"Saved results to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()

