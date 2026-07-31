import json

from courtmate.operations import (
    find_available_courts,
    get_daily_schedule,
    next_occurrence_of_weekday,
    search_prices,
)


def print_section(
    title: str,
    value: object,
) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)
    print(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )
    )


def main() -> None:
    # Monday=0, Thursday=3.
    next_thursday = (
        next_occurrence_of_weekday(
            3
        )
    )

    print_section(
        "Private lesson prices",
        search_prices(
            offering_type=(
                "private_lesson"
            )
        ),
    )

    print_section(
        "Group class prices",
        search_prices(
            offering_type=(
                "group_class"
            )
        ),
    )

    print_section(
        (
            "Available courts next "
            f"Thursday: {next_thursday}"
        ),
        find_available_courts(
            target_date=next_thursday
        ),
    )

    schedule = get_daily_schedule(
        target_date=next_thursday
    )

    print_section(
        (
            "First 20 schedule rows "
            f"for {next_thursday}"
        ),
        schedule[:20],
    )


if __name__ == "__main__":
    main()