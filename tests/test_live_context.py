import json

from courtmate import live_context
from courtmate.query_router import QueryRoute


def test_price_context_uses_operational_catalog(monkeypatch):
    monkeypatch.setattr(
        live_context,
        "search_prices",
        lambda **_kwargs: [
            {
                "name": "Bottled water",
                "amount": "2.00",
                "currency": "CAD",
            }
        ],
    )

    route = QueryRoute(
        intent="price",
        normalized_query="water",
        offering_type="retail_item",
    )

    raw_context, sources = live_context.build_live_context(route)
    context = json.loads(raw_context)

    assert context["source"] == "current_price_catalog"
    assert context["results"][0]["amount"] == "2.00"
    assert sources[0]["id"] == "current-price-catalog"


def test_schedule_context_filters_available_rows(monkeypatch):
    captured = {}

    def fake_schedule(**kwargs):
        captured.update(kwargs)
        return [
            {
                "court_name": "Court 1",
                "start_at": "2026-08-10T10:00:00-04:00",
                "end_at": "2026-08-10T11:00:00-04:00",
                "activity_name": "Available",
                "offering_name": None,
                "coach_name": None,
                "slot_status": "available",
            },
            {
                "court_name": "Court 2",
                "start_at": "2026-08-10T11:00:00-04:00",
                "end_at": "2026-08-10T12:00:00-04:00",
                "activity_name": "Private lesson",
                "offering_name": "One-to-one private lesson",
                "coach_name": "Coach Amy",
                "slot_status": "scheduled",
            },
        ]

    monkeypatch.setattr(
        live_context,
        "get_schedule_range",
        fake_schedule,
    )

    route = QueryRoute(
        intent="schedule",
        normalized_query="Coach Amy classes",
        coach_name="Coach Amy",
        target_date="2026-08-10",
        target_end_date="2026-08-16",
    )

    raw_context, sources = live_context.build_live_context(route)
    context = json.loads(raw_context)

    assert captured["coach_name"] == "Coach Amy"
    assert context["result_count"] == 1
    assert context["scheduled_activities"][0]["coach"] == "Coach Amy"
    assert sources[0]["category"] == "live_schedule"


def test_availability_requires_a_date():
    route = QueryRoute(
        intent="availability",
        normalized_query="available courts",
    )

    raw_context, sources = live_context.build_live_context(route)
    context = json.loads(raw_context)

    assert "specific date" in context["error"]
    assert sources == []

