from courtmate.source_selection import select_source_ids


def test_source_selection_rejects_unknown_ids_and_duplicates():
    selected = select_source_ids(
        requested_source_ids=[
            "faq-002",
            "invented-id",
            "faq-002",
            "course-001",
        ],
        allowed_source_ids=[
            "faq-002",
            "course-001",
        ],
    )

    assert selected == [
        "faq-002",
        "course-001",
    ]


def test_source_selection_does_not_force_an_irrelevant_fallback():
    selected = select_source_ids(
        requested_source_ids=[],
        allowed_source_ids=["faq-001"],
    )

    assert selected == []

