import re

from datetime import (
    date,
    datetime,
    time,
    timedelta,
)
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from psycopg2.extras import RealDictCursor

from courtmate.config import TIMEZONE
from courtmate.db import get_db_connection


APP_TIMEZONE = ZoneInfo(TIMEZONE)


def serialize_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert database values into JSON-compatible values."""
    serialized_rows = []

    for row in rows:
        serialized_row = {}

        for key, value in row.items():
            if isinstance(value, datetime):
                serialized_row[key] = (
                    value.astimezone(
                        APP_TIMEZONE
                    ).isoformat()
                )

            elif isinstance(value, date):
                serialized_row[key] = (
                    value.isoformat()
                )

            elif isinstance(value, Decimal):
                serialized_row[key] = (
                    float(value)
                )

            else:
                serialized_row[key] = value

        serialized_rows.append(
            serialized_row
        )

    return serialized_rows


PRICE_SEARCH_STOPWORDS = {
    "a",
    "an",
    "are",
    "can",
    "cost",
    "costs",
    "do",
    "does",
    "fee",
    "fees",
    "for",
    "how",
    "i",
    "is",
    "much",
    "of",
    "please",
    "price",
    "prices",
    "rate",
    "rates",
    "the",
    "what",
}


def extract_price_search_terms(
    query: str,
) -> list[str]:
    """Return meaningful lowercase terms for catalog search."""
    terms = [
        term
        for term in re.findall(
            r"[a-z0-9]+",
            query.lower(),
        )
        if term not in PRICE_SEARCH_STOPWORDS
    ]

    return list(
        dict.fromkeys(terms)
    )


def search_prices(
    query: str = "",
    offering_type: str | None = None,
) -> list[dict[str, Any]]:
    """Search the current price catalog."""
    conditions = [
        "o.active = TRUE",
        "p.active = TRUE",
        "p.effective_from <= CURRENT_DATE",
        (
            "("
            "p.effective_to IS NULL "
            "OR p.effective_to >= CURRENT_DATE"
            ")"
        ),
    ]

    parameters: list[Any] = []

    cleaned_query = query.strip()

    search_terms = (
        extract_price_search_terms(
            cleaned_query
        )
    )

    for search_term in search_terms:
        search_pattern = (
            f"%{search_term}%"
        )

        conditions.append(
            """
            (
                o.name ILIKE %s
                OR o.description ILIKE %s
                OR o.offering_type ILIKE %s
                OR p.price_name ILIKE %s
            )
            """
        )

        parameters.extend(
            [
                search_pattern,
                search_pattern,
                search_pattern,
                search_pattern,
            ]
        )

    if offering_type:
        conditions.append(
            "o.offering_type = %s"
        )
        parameters.append(
            offering_type
        )

    where_clause = " AND ".join(
        conditions
    )

    connection = get_db_connection()

    try:
        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                f"""
                SELECT
                    o.id AS offering_id,
                    o.offering_type,
                    o.name,
                    o.description,
                    o.duration_minutes,
                    o.capacity,
                    c.name AS coach_name,
                    p.price_name,
                    p.amount,
                    p.currency,
                    p.billing_unit,
                    p.effective_from,
                    p.effective_to
                FROM offerings o
                JOIN prices p
                    ON p.offering_id = o.id
                LEFT JOIN coaches c
                    ON c.id = o.coach_id
                WHERE {where_clause}
                ORDER BY
                    o.offering_type,
                    o.name,
                    p.amount
                """,
                parameters,
            )

            rows = cursor.fetchall()

        return serialize_rows(
            list(rows)
        )

    finally:
        connection.close()


def find_available_courts(
    target_date: date,
    start_time: time | None = None,
    end_time: time | None = None,
) -> list[dict[str, Any]]:
    """
    Return available courts grouped by 60-minute time slot.
    """
    if start_time is None:
        start_time = time(
            hour=10
        )

    if end_time is None:
        end_time = time(
            hour=22
        )

    local_start = datetime.combine(
        target_date,
        start_time,
        tzinfo=APP_TIMEZONE,
    )

    local_end = datetime.combine(
        target_date,
        end_time,
        tzinfo=APP_TIMEZONE,
    )

    if local_end <= local_start:
        raise ValueError(
            "end_time must be later "
            "than start_time."
        )

    connection = get_db_connection()

    try:
        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    cs.start_at,
                    cs.end_at,
                    ARRAY_AGG(
                        c.name
                        ORDER BY c.name
                    ) AS available_courts,
                    COUNT(*) AS available_count
                FROM court_schedule cs
                JOIN courts c
                    ON c.id = cs.court_id
                WHERE
                    c.active = TRUE
                    AND cs.slot_status =
                        'available'
                    AND cs.start_at >= %s
                    AND cs.end_at <= %s
                GROUP BY
                    cs.start_at,
                    cs.end_at
                ORDER BY
                    cs.start_at
                """,
                (
                    local_start,
                    local_end,
                ),
            )

            rows = cursor.fetchall()

        return serialize_rows(
            list(rows)
        )

    finally:
        connection.close()

def get_schedule_range(
    start_date: date,
    end_date: date,
    coach_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return scheduled activities within a local date range."""
    if end_date < start_date:
        raise ValueError(
            "end_date cannot be earlier than start_date."
        )

    local_start = datetime.combine(
        start_date,
        time.min,
        tzinfo=APP_TIMEZONE,
    )

    local_end = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        tzinfo=APP_TIMEZONE,
    )

    conditions = [
        "cs.start_at >= %s",
        "cs.start_at < %s",
        "cs.slot_status != 'available'",
    ]

    parameters: list[Any] = [
        local_start,
        local_end,
    ]

    cleaned_coach_name = (
        coach_name.strip()
        if coach_name
        else ""
    )

    if cleaned_coach_name:
        conditions.append(
            "coach.name ILIKE %s"
        )
        parameters.append(
            f"%{cleaned_coach_name}%"
        )

    where_clause = " AND ".join(
        conditions
    )

    connection = get_db_connection()

    try:
        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                f"""
                SELECT
                    c.id AS court_id,
                    c.name AS court_name,
                    cs.start_at,
                    cs.end_at,
                    cs.activity_name,
                    cs.slot_status,
                    o.offering_type,
                    o.name AS offering_name,
                    coach.name AS coach_name,
                    cs.capacity,
                    cs.booked_count,
                    cs.notes,
                    cs.source
                FROM court_schedule cs
                JOIN courts c
                    ON c.id = cs.court_id
                LEFT JOIN offerings o
                    ON o.id = cs.offering_id
                LEFT JOIN coaches coach
                    ON coach.id = cs.coach_id
                WHERE {where_clause}
                ORDER BY
                    cs.start_at,
                    c.name
                """,
                parameters,
            )

            rows = cursor.fetchall()

        return serialize_rows(
            list(rows)
        )

    finally:
        connection.close()
        
def get_daily_schedule(
    target_date: date,
) -> list[dict[str, Any]]:
    """Return every court activity for one local date."""
    local_start = datetime.combine(
        target_date,
        time.min,
        tzinfo=APP_TIMEZONE,
    )

    local_end = (
        local_start
        + timedelta(days=1)
    )

    connection = get_db_connection()

    try:
        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    c.id AS court_id,
                    c.name AS court_name,
                    cs.start_at,
                    cs.end_at,
                    cs.activity_name,
                    cs.slot_status,
                    o.offering_type,
                    o.name AS offering_name,
                    coach.name AS coach_name,
                    cs.capacity,
                    cs.booked_count,
                    cs.notes,
                    cs.source
                FROM court_schedule cs
                JOIN courts c
                    ON c.id = cs.court_id
                LEFT JOIN offerings o
                    ON o.id = cs.offering_id
                LEFT JOIN coaches coach
                    ON coach.id = cs.coach_id
                WHERE
                    cs.start_at >= %s
                    AND cs.start_at < %s
                ORDER BY
                    cs.start_at,
                    c.name
                """,
                (
                    local_start,
                    local_end,
                ),
            )

            rows = cursor.fetchall()

        return serialize_rows(
            list(rows)
        )

    finally:
        connection.close()


def next_occurrence_of_weekday(
    weekday: int,
    from_date: date | None = None,
) -> date:
    """
    Return the next occurrence of a weekday.

    Monday is 0 and Sunday is 6.
    """
    if weekday < 0 or weekday > 6:
        raise ValueError(
            "weekday must be between 0 and 6."
        )

    if from_date is None:
        from_date = datetime.now(
            APP_TIMEZONE
        ).date()

    days_ahead = (
        weekday
        - from_date.weekday()
    ) % 7

    if days_ahead == 0:
        days_ahead = 7

    return (
        from_date
        + timedelta(days=days_ahead)
    )