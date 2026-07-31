import json
import re
from datetime import (
    date,
    datetime,
    timedelta,
)
from typing import Literal
from zoneinfo import ZoneInfo

from openai import OpenAI
from pydantic import BaseModel, Field

from courtmate.config import (
    OPENAI_API_KEY,
    OPENAI_ROUTER_MODEL,
    TIMEZONE,
)


QueryIntent = Literal[
    "conversation",
    "knowledge",
    "price",
    "availability",
    "schedule",
]

OfferingType = Literal[
    "equipment_rental",
    "court_rental",
    "private_lesson",
    "group_class",
    "drop_in",
    "membership",
]


router_client = OpenAI(
    api_key=OPENAI_API_KEY,
)

app_timezone = ZoneInfo(
    TIMEZONE
)


class QueryRoute(BaseModel):
    intent: QueryIntent = Field(
        description=(
            "The data source required "
            "to answer the question."
        )
    )

    normalized_query: str = Field(
        description=(
            "A short English search query. "
            "Translate important Chinese "
            "catalog terms into English."
        )
    )

    offering_type: OfferingType | None = Field(
        default=None,
        description=(
            "The normalized catalog category "
            "for price questions."
        ),
    )

    target_date: str | None = Field(
        default=None,
        description=(
            "Resolved local date in YYYY-MM-DD "
            "format when the question concerns "
            "a schedule or availability."
        ),
    )

    start_time: str | None = Field(
        default=None,
        description=(
            "Requested local start time in "
            "HH:MM format or null."
        ),
    )

    end_time: str | None = Field(
        default=None,
        description=(
            "Requested local end time in "
            "HH:MM format or null."
        ),
    )


def format_history(
    history: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    formatted_history = []

    for message in history or []:
        role = str(
            message.get(
                "role",
                "",
            )
        ).strip()

        content = str(
            message.get(
                "content",
                "",
            )
        ).strip()

        if (
            role in {
                "user",
                "assistant",
            }
            and content
        ):
            formatted_history.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    return formatted_history[-6:]

ENGLISH_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def start_of_week(
    current_date: date,
) -> date:
    return (
        current_date
        - timedelta(
            days=current_date.weekday()
        )
    )


def resolve_relative_date(
    question: str,
    current_date: date,
) -> date | None:
    """Resolve common English relative dates."""
    normalized = (
        question.strip().lower()
    )

    if "today" in normalized:
        return current_date

    if (
        "day after tomorrow"
        in normalized
    ):
        return (
            current_date
            + timedelta(days=2)
        )

    if "tomorrow" in normalized:
        return (
            current_date
            + timedelta(days=1)
        )

    next_week_match = re.search(
        (
            r"\bnext\s+"
            r"(monday|tuesday|wednesday|"
            r"thursday|friday|saturday|sunday)"
            r"\b"
        ),
        normalized,
    )

    if next_week_match:
        weekday = ENGLISH_WEEKDAYS[
            next_week_match.group(1)
        ]

        return (
            start_of_week(
                current_date
            )
            + timedelta(
                weeks=1,
                days=weekday,
            )
        )

    this_week_match = re.search(
        (
            r"\bthis\s+"
            r"(monday|tuesday|wednesday|"
            r"thursday|friday|saturday|sunday)"
            r"\b"
        ),
        normalized,
    )

    if this_week_match:
        weekday = ENGLISH_WEEKDAYS[
            this_week_match.group(1)
        ]

        return (
            start_of_week(
                current_date
            )
            + timedelta(
                days=weekday
            )
        )

    return None

def route_query(
    question: str,
    history: list[dict[str, str]] | None = None,
) -> QueryRoute:
    now = datetime.now(
        app_timezone
    )

    instructions = f"""
You route questions for a badminton club assistant.

Current local date and time:
{now.strftime("%Y-%m-%d %A %H:%M")}

Timezone:
{TIMEZONE}

Choose exactly one intent:

conversation:
Greetings, thanks, farewells, or casual messages.

knowledge:
Static club policies, coaching descriptions, facilities,
rules, what to bring, and other knowledge-base questions.

Price search rules:
- Produce a concise English catalog search query.
- Normalize the following concepts:
  court booking -> court rental
  one-to-one coaching -> private lesson
  one-to-two coaching -> private lesson
  one-to-three coaching -> private lesson
  beginner class -> basic group class
  advanced class -> advanced group class
  racquet hire -> racket rental
  shoe hire -> shoe rental
  mineral water -> water

availability:
Questions asking which courts or time slots are available
on a particular date.

schedule:
Questions asking what lessons, bookings, activities, or
coaches are scheduled on a particular date.

Date rules:
- Resolve relative dates using the current local date.
- "Next Thursday" means Thursday in the next calendar week.
- "This Thursday" means Thursday in the current calendar week.
- Return target_date as YYYY-MM-DD.
- If no date is supplied for availability or schedule,
  return null instead of guessing.


Use the conversation history only when needed to resolve
a follow-up question.
""".strip()

    input_data = {
        "question": question,
        "conversation_history": (
            format_history(
                history
            )
        ),
    }

    response = (
        router_client.responses.parse(
            model=OPENAI_ROUTER_MODEL,
            instructions=instructions,
            input=json.dumps(
                input_data,
                ensure_ascii=False,
            ),
            text_format=QueryRoute,
        )
    )

    route = response.output_parsed

    if route is None:
        raise RuntimeError(
            "The query router did not "
            "return structured output."
        )

    deterministic_date = (
        resolve_relative_date(
            question=question,
            current_date=now.date(),
        )
    )

    if deterministic_date is not None:
        route.target_date = (
            deterministic_date.isoformat()
        )

    return route