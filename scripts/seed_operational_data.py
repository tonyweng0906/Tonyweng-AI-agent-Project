from datetime import (
    date,
    datetime,
    time,
    timedelta,
)
from random import Random
from zoneinfo import ZoneInfo

from psycopg2.extras import execute_values

from courtmate.config import TIMEZONE
from courtmate.db import get_db_connection


SCHEDULE_DAYS = 28
EFFECTIVE_FROM = date(2026, 1, 1)

timezone = ZoneInfo(TIMEZONE)


COACHES = [
    (
        "coach-lily",
        "Coach Lily Chen",
        (
            "Beginner-friendly coach focused on "
            "fundamentals and junior development."
        ),
        "Fundamentals, footwork, junior training",
        "beginner and intermediate",
    ),
    (
        "coach-daniel",
        "Coach Daniel Wong",
        (
            "Coach focused on singles strategy, "
            "movement and match preparation."
        ),
        "Singles strategy, movement, match preparation",
        "intermediate and advanced",
    ),
    (
        "coach-amy",
        "Coach Amy",
        (
            "Coach focused on beginner fundamentals, "
            "footwork and junior training."
        ),
        "Fundamentals, footwork, junior training",
        "beginner and intermediate",
    ),
    (
        "coach-david",
        "Coach David",
        (
            "Coach focused on intermediate and advanced "
            "singles strategy, movement and match preparation."
        ),
        "Singles strategy, movement, match preparation",
        "intermediate and advanced",
    ),
]

COACH_NAMES = {
    coach_id: coach_name
    for (
        coach_id,
        coach_name,
        _,
        _,
        _,
    ) in COACHES
}

OFFERINGS = [
    (
        "court-rental",
        "court_rental",
        "Court rental",
        "One badminton court for 60 minutes.",
        None,
        60,
        4,
    ),
    (
        "private-one",
        "private_lesson",
        "One-to-one private lesson",
        "A 60-minute private lesson for one player.",
        None,
        60,
        1,
    ),
    (
        "private-two",
        "private_lesson",
        "One-to-two private lesson",
        "A 60-minute private lesson for two players.",
        None,
        60,
        2,
    ),
    (
        "private-three",
        "private_lesson",
        "One-to-three private lesson",
        "A 60-minute private lesson for three players.",
        None,
        60,
        3,
    ),
    (
        "group-basic",
        "group_class",
        "Basic group class",
        (
            "Weekday beginner group training. "
            "Morning sessions run from 9 AM to 12 PM."
        ),
        None,
        180,
        16,
    ),
    (
        "group-advanced",
        "group_class",
        "Advanced group class",
        (
            "Weekday advanced group training. "
            "Afternoon sessions run from 1 PM to 4 PM."
        ),
        None,
        180,
        12,
    ),
    (
        "soft-drink",
        "retail_item",
        "Soft drink",
        "One bottled soft drink.",
        None,
        None,
        None,
    ),
    (
        "water",
        "retail_item",
        "Bottled water",
        "One bottle of mineral water.",
        None,
        None,
        None,
    ),
    (
        "racket-rental",
        "equipment_rental",
        "Badminton racket rental",
        "Badminton racket rental for one hour.",
        None,
        60,
        None,
    ),
    (
        "shoe-rental",
        "equipment_rental",
        "Badminton shoe rental",
        "Badminton shoe rental for one hour.",
        None,
        60,
        None,
    ),
]


PRICES = [
    (
        "court-rental",
        "hourly",
        35.00,
        "CAD",
        "per_hour",
    ),
    (
        "private-one",
        "one_player",
        80.00,
        "CAD",
        "per_hour",
    ),
    (
        "private-two",
        "two_players",
        100.00,
        "CAD",
        "per_hour",
    ),
    (
        "private-three",
        "three_players",
        120.00,
        "CAD",
        "per_hour",
    ),
    (
        "group-basic",
        "single_class",
        65.00,
        "CAD",
        "per_person",
    ),
    (
        "group-basic",
        "weekly_package",
        250.00,
        "CAD",
        "per_week",
    ),
    (
        "group-advanced",
        "single_class",
        70.00,
        "CAD",
        "per_person",
    ),
    (
        "group-advanced",
        "weekly_package",
        280.00,
        "CAD",
        "per_week",
    ),
    (
        "soft-drink",
        "standard",
        3.00,
        "CAD",
        "per_item",
    ),
    (
        "water",
        "standard",
        2.00,
        "CAD",
        "per_item",
    ),
    (
        "racket-rental",
        "hourly",
        5.00,
        "CAD",
        "per_hour",
    ),
    (
        "shoe-rental",
        "hourly",
        5.00,
        "CAD",
        "per_hour",
    ),
]


COURTS = [
    (
        f"court-{number:02d}",
        f"Court {number}",
        "Main Club",
        f"Badminton Court {number}",
    )
    for number in range(1, 9)
]


PRIVATE_OPTIONS = [
    (
        "private-one",
        "One-to-one private lesson",
        1,
    ),
    (
        "private-two",
        "One-to-two private lesson",
        2,
    ),
    (
        "private-three",
        "One-to-three private lesson",
        3,
    ),
]


def local_datetime(
    schedule_date: date,
    hour: int,
) -> datetime:
    return datetime.combine(
        schedule_date,
        time(hour=hour),
        tzinfo=timezone,
    )


def create_schedule_rows() -> list[tuple]:
    rows = []

    coach_busy_slots: set[
        tuple[str, datetime]
    ] = set()

    today = datetime.now(
        timezone
    ).date()

    for day_offset in range(
        SCHEDULE_DAYS
    ):
        schedule_date = (
            today
            + timedelta(days=day_offset)
        )

        weekday = (
            schedule_date.weekday()
        )

        # Basic weekday class starts at 9 AM,
        # one hour before normal public booking hours.
        if weekday < 5:
            start_at = local_datetime(
                schedule_date,
                9,
            )

            rows.append(
                (
                    "court-01",
                    "group-basic",
                    "coach-lily",
                    "Basic group class",
                    start_at,
                    start_at
                    + timedelta(hours=1),
                    "scheduled",
                    16,
                    12,
                    "Simulated weekday class",
                    "simulation",
                )
            )

        for court_number in range(
            1,
            9,
        ):
            court_id = (
                f"court-{court_number:02d}"
            )

            for hour in range(
                10,
                22,
                
            ):
                start_at = local_datetime(
                    schedule_date,
                    hour,
                )
                end_at = (
                    start_at
                    + timedelta(hours=1)
                )
                # Coach Amy teaches a regular beginner class
                # every Tuesday and Thursday from 6 PM to 7 PM.
                if (
                    weekday in {1, 3}
                    and court_number == 3
                    and hour == 18
                ):
                    rows.append(
                        (
                            court_id,
                            "group-basic",
                            "coach-amy",
                            "Beginner skills class with Coach Amy",
                            start_at,
                            end_at,
                            "scheduled",
                            16,
                            10,
                            "Simulated recurring class",
                            "simulation",
                        )
                    )

                    coach_busy_slots.add(
                        (
                            "coach-amy",
                            start_at,
                        )
                    )

                    continue
                # Court 1: weekday basic class,
                # 9 AM to 12 PM.
                if (
                    weekday < 5
                    and court_number == 1
                    and hour in {10, 11}
                ):
                    rows.append(
                        (
                            court_id,
                            "group-basic",
                            "coach-lily",
                            "Basic group class",
                            start_at,
                            end_at,
                            "scheduled",
                            16,
                            12,
                            "Simulated weekday class",
                            "simulation",
                        )
                    )

                    coach_busy_slots.add(
                        (
                            "coach-lily",
                            start_at,
                        )
                    )
                    
                    continue

                # Court 2: weekday advanced class,
                # 1 PM to 4 PM.
                if (
                    weekday < 5
                    and court_number == 2
                    and hour in {13, 14, 15}
                ):
                    rows.append(
                        (
                            court_id,
                            "group-advanced",
                            "coach-daniel",
                            "Advanced group class",
                            start_at,
                            end_at,
                            "scheduled",
                            12,
                            9,
                            "Simulated weekday class",
                            "simulation",
                        )
                    )

                    coach_busy_slots.add(
                        (
                            "coach-daniel",
                            start_at,
                        )
                    )
                    continue

                random_generator = Random(
                    (
                        f"{schedule_date.isoformat()}"
                        f"-{court_id}-{hour}"
                    )
                )

                random_value = (
                    random_generator.random()
                )

                # Simulate a limited number of private lessons.
                if random_value < 0.03:
                    available_coaches = [
                        coach_id
                        for coach_id in COACH_NAMES
                        if (
                            coach_id,
                            start_at,
                        ) not in coach_busy_slots
                    ]

                    if available_coaches:
                        (
                            offering_id,
                            lesson_name,
                            capacity,
                        ) = random_generator.choice(
                            PRIVATE_OPTIONS
                        )

                        coach_id = random_generator.choice(
                            available_coaches
                        )

                        coach_name = COACH_NAMES[
                            coach_id
                        ]

                        rows.append(
                            (
                                court_id,
                                offering_id,
                                coach_id,
                                (
                                    f"{lesson_name} "
                                    f"with {coach_name}"
                                ),
                                start_at,
                                end_at,
                                "scheduled",
                                capacity,
                                capacity,
                                "Simulated private lesson",
                                "simulation",
                            )
                        )

                        coach_busy_slots.add(
                            (
                                coach_id,
                                start_at,
                            )
                        )

                        continue
                # Simulate existing court bookings.
                if random_value < 0.28:
                    rows.append(
                        (
                            court_id,
                            "court-rental",
                            None,
                            "Existing court booking",
                            start_at,
                            end_at,
                            "scheduled",
                            1,
                            1,
                            "Simulated court booking",
                            "simulation",
                        )
                    )
                    continue

                # Otherwise the court is available.
                rows.append(
                    (
                        court_id,
                        None,
                        None,
                        "Available",
                        start_at,
                        end_at,
                        "available",
                        1,
                        0,
                        "",
                        "simulation",
                    )
                )

    return rows


def seed_data() -> None:
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # Seed-managed catalog rows are reactivated below. Rows that
            # were removed from this file remain available for audit but
            # no longer appear in operational searches.
            cursor.execute(
                """
                UPDATE coaches
                SET active = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE source = 'seed'
                """
            )

            cursor.execute(
                """
                UPDATE offerings
                SET active = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE source = 'seed'
                """
            )

            cursor.execute(
                """
                UPDATE prices
                SET active = FALSE
                WHERE source = 'seed'
                """
            )

            coach_rows = [
                (*coach, True, "seed")
                for coach in COACHES
            ]

            execute_values(
                cursor,
                """
                INSERT INTO coaches (
                    id,
                    name,
                    description,
                    specialties,
                    skill_level,
                    active,
                    source
                )
                VALUES %s
                ON CONFLICT (id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    description =
                        EXCLUDED.description,
                    specialties =
                        EXCLUDED.specialties,
                    skill_level =
                        EXCLUDED.skill_level,
                    active = EXCLUDED.active,
                    source = EXCLUDED.source,
                    updated_at =
                        CURRENT_TIMESTAMP
                """,
                coach_rows,
            )

            offering_rows = [
                (*offering, True, "seed")
                for offering in OFFERINGS
            ]

            execute_values(
                cursor,
                """
                INSERT INTO offerings (
                    id,
                    offering_type,
                    name,
                    description,
                    coach_id,
                    duration_minutes,
                    capacity,
                    active,
                    source
                )
                VALUES %s
                ON CONFLICT (id)
                DO UPDATE SET
                    offering_type =
                        EXCLUDED.offering_type,
                    name = EXCLUDED.name,
                    description =
                        EXCLUDED.description,
                    coach_id =
                        EXCLUDED.coach_id,
                    duration_minutes =
                        EXCLUDED.duration_minutes,
                    capacity =
                        EXCLUDED.capacity,
                    active = EXCLUDED.active,
                    source = EXCLUDED.source,
                    updated_at =
                        CURRENT_TIMESTAMP
                """,
                offering_rows,
            )

            price_rows = [
                (
                    offering_id,
                    price_name,
                    amount,
                    currency,
                    billing_unit,
                    EFFECTIVE_FROM,
                    True,
                    "seed",
                )
                for (
                    offering_id,
                    price_name,
                    amount,
                    currency,
                    billing_unit,
                ) in PRICES
            ]

            execute_values(
                cursor,
                """
                INSERT INTO prices (
                    offering_id,
                    price_name,
                    amount,
                    currency,
                    billing_unit,
                    effective_from,
                    active,
                    source
                )
                VALUES %s
                ON CONFLICT (
                    offering_id,
                    price_name,
                    effective_from
                )
                DO UPDATE SET
                    amount = EXCLUDED.amount,
                    currency = EXCLUDED.currency,
                    billing_unit =
                        EXCLUDED.billing_unit,
                    active = EXCLUDED.active,
                    source = EXCLUDED.source
                """,
                price_rows,
            )

            execute_values(
                cursor,
                """
                INSERT INTO courts (
                    id,
                    name,
                    location,
                    description
                )
                VALUES %s
                ON CONFLICT (id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    location = EXCLUDED.location,
                    description =
                        EXCLUDED.description,
                    updated_at =
                        CURRENT_TIMESTAMP
                """,
                COURTS,
            )

            schedule_rows = (
                create_schedule_rows()
            )

            # Rebuild only simulated rows. Manual bookings and staff-created
            # schedule entries keep their source and are never removed here.
            cursor.execute(
                """
                DELETE FROM court_schedule
                WHERE source = 'simulation'
                """
            )

            execute_values(
                cursor,
                """
                INSERT INTO court_schedule (
                    court_id,
                    offering_id,
                    coach_id,
                    activity_name,
                    start_at,
                    end_at,
                    slot_status,
                    capacity,
                    booked_count,
                    notes,
                    source
                )
                VALUES %s
                ON CONFLICT (
                    court_id,
                    start_at,
                    end_at
                )
                DO UPDATE SET
                    offering_id = EXCLUDED.offering_id,
                    coach_id = EXCLUDED.coach_id,
                    activity_name = EXCLUDED.activity_name,
                    slot_status = EXCLUDED.slot_status,
                    capacity = EXCLUDED.capacity,
                    booked_count = EXCLUDED.booked_count,
                    notes = EXCLUDED.notes,
                    source = EXCLUDED.source,
                    updated_at = CURRENT_TIMESTAMP
                WHERE court_schedule.source = 'simulation'
                """,
                schedule_rows,
                page_size=500,
            )

        connection.commit()

    finally:
        connection.close()

    print(
        "Operational data seeded successfully."
    )
    print(
        f"Courts: {len(COURTS)}"
    )
    print(
        f"Offerings: {len(OFFERINGS)}"
    )
    print(
        f"Prices: {len(PRICES)}"
    )
    print(
        f"Generated schedule days: "
        f"{SCHEDULE_DAYS}"
    )


if __name__ == "__main__":
    seed_data()

