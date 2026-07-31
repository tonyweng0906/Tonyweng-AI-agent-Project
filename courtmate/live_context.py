import json
from datetime import (
    date,
    time,
)
from typing import Any

from courtmate.operations import (
    find_available_courts,
    get_daily_schedule,
    search_prices,
)
from courtmate.query_router import (
    QueryRoute,
)


def parse_date(
    value: str | None,
) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(
            value
        )

    except ValueError:
        return None


def parse_time(
    value: str | None,
) -> time | None:
    if not value:
        return None

    try:
        return time.fromisoformat(
            value
        )

    except ValueError:
        return None


def compact_schedule(
    schedule: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    compact_rows = []

    for row in schedule:
        # Available slots are handled by the
        # availability search.
        if (
            row.get("slot_status")
            == "available"
        ):
            continue

        compact_rows.append(
            {
                "court": row.get(
                    "court_name"
                ),
                "start_at": row.get(
                    "start_at"
                ),
                "end_at": row.get(
                    "end_at"
                ),
                "activity": row.get(
                    "activity_name"
                ),
                "offering": row.get(
                    "offering_name"
                ),
                "coach": row.get(
                    "coach_name"
                ),
                "status": row.get(
                    "slot_status"
                ),
            }
        )

    return compact_rows


def build_live_context(
    route: QueryRoute,
) -> tuple[str, list[dict[str, str]]]:
    if route.intent == "price":
        results = search_prices(
            query=route.normalized_query,
            offering_type=(
                route.offering_type
            ),
        )

        context = {
            "source": (
                "current_price_catalog"
            ),
            "query": (
                route.normalized_query
            ),
            "results": results,
        }

        sources = [
            {
                "id": "current-price-catalog",
                "title": (
                    "Current price catalog"
                ),
                "category": "live_price",
            }
        ]

        return (
            json.dumps(
                context,
                ensure_ascii=False,
                indent=2,
            ),
            sources,
        )

    if route.intent == "availability":
        target_date = parse_date(
            route.target_date
        )

        if target_date is None:
            return (
                json.dumps(
                    {
                        "source": (
                            "live_court_schedule"
                        ),
                        "error": (
                            "A specific date is "
                            "required before court "
                            "availability can be "
                            "checked."
                        ),
                    },
                    ensure_ascii=False,
                ),
                [],
            )

        results = find_available_courts(
            target_date=target_date,
            start_time=parse_time(
                route.start_time
            ),
            end_time=parse_time(
                route.end_time
            ),
        )

        context = {
            "source": (
                "live_court_schedule"
            ),
            "target_date": (
                target_date.isoformat()
            ),
            "results": results,
        }

        sources = [
            {
                "id": "live-court-schedule",
                "title": (
                    "Live court schedule"
                ),
                "category": (
                    "live_availability"
                ),
            }
        ]

        return (
            json.dumps(
                context,
                ensure_ascii=False,
                indent=2,
            ),
            sources,
        )

    if route.intent == "schedule":
        target_date = parse_date(
            route.target_date
        )

        if target_date is None:
            return (
                json.dumps(
                    {
                        "source": (
                            "live_court_schedule"
                        ),
                        "error": (
                            "A specific date is "
                            "required before the "
                            "schedule can be checked."
                        ),
                    },
                    ensure_ascii=False,
                ),
                [],
            )

        schedule = get_daily_schedule(
            target_date=target_date
        )

        context = {
            "source": (
                "live_court_schedule"
            ),
            "target_date": (
                target_date.isoformat()
            ),
            "scheduled_activities": (
                compact_schedule(
                    schedule
                )
            ),
        }

        sources = [
            {
                "id": "live-court-schedule",
                "title": (
                    "Live court schedule"
                ),
                "category": "live_schedule",
            }
        ]

        return (
            json.dumps(
                context,
                ensure_ascii=False,
                indent=2,
            ),
            sources,
        )

    return (
        (
            "No live operational data was "
            "requested for this message."
        ),
        [],
    )