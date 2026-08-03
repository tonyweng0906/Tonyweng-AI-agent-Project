from datetime import date

from courtmate.query_router import (
    QueryRoute,
    normalize_price_route,
    resolve_relative_date,
    resolve_relative_date_range,
)


def make_price_route() -> QueryRoute:
    return QueryRoute(
        intent="price",
        normalized_query="incorrect model guess",
        offering_type="membership",
    )


def test_water_price_route_is_normalized_deterministically():
    route = make_price_route()

    normalize_price_route(
        route=route,
        question="How much is a bottle of water?",
    )

    assert route.normalized_query == "water"
    assert route.offering_type == "retail_item"


def test_racket_price_route_is_normalized_deterministically():
    route = make_price_route()

    normalize_price_route(
        route=route,
        question="What does racquet hire cost?",
    )

    assert route.normalized_query == "racket rental"
    assert route.offering_type == "equipment_rental"


def test_next_thursday_uses_next_calendar_week():
    resolved = resolve_relative_date(
        question="What courts are available next Thursday?",
        current_date=date(2026, 8, 3),
    )

    assert resolved == date(2026, 8, 13)


def test_next_week_resolves_monday_through_sunday():
    resolved = resolve_relative_date_range(
        question="When does Coach Amy teach next week?",
        current_date=date(2026, 8, 3),
    )

    assert resolved == (
        date(2026, 8, 10),
        date(2026, 8, 16),
    )

