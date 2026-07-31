from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import RealDictCursor

from courtmate.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    TIMEZONE,
)

APP_TIMEZONE = ZoneInfo("America/Toronto")


def current_timestamp() -> datetime:
    return datetime.now(APP_TIMEZONE)

timezone = ZoneInfo(TIMEZONE)

def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=10,
    )

def init_db() -> None:
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    sources JSONB NOT NULL DEFAULT '[]',
                    model_used TEXT NOT NULL,
                    judge_model TEXT NOT NULL,
                    response_time DOUBLE PRECISION NOT NULL,
                    relevance TEXT NOT NULL,
                    relevance_explanation TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    eval_prompt_tokens INTEGER NOT NULL,
                    eval_completion_tokens INTEGER NOT NULL,
                    eval_total_tokens INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id BIGSERIAL PRIMARY KEY,
                    conversation_id UUID NOT NULL
                        REFERENCES conversations(id)
                        ON DELETE CASCADE,
                    feedback SMALLINT NOT NULL
                        CHECK (feedback IN (-1, 1)),
                    comment TEXT,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS coaches (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    specialties TEXT NOT NULL DEFAULT '',
                    skill_level TEXT NOT NULL DEFAULT '',
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS offerings (
                    id TEXT PRIMARY KEY,
                    offering_type TEXT NOT NULL
                        CHECK (
                            offering_type IN (
                                'equipment_rental',
                                'court_rental',
                                'private_lesson',
                                'group_class',
                                'drop_in',
                                'membership'
                            )
                        ),
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    coach_id TEXT
                        REFERENCES coaches(id)
                        ON DELETE SET NULL,
                    duration_minutes INTEGER
                        CHECK (
                            duration_minutes IS NULL
                            OR duration_minutes > 0
                        ),
                    capacity INTEGER
                        CHECK (
                            capacity IS NULL
                            OR capacity > 0
                        ),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS prices (
                    id BIGSERIAL PRIMARY KEY,
                    offering_id TEXT NOT NULL
                        REFERENCES offerings(id)
                        ON DELETE CASCADE,
                    price_name TEXT NOT NULL DEFAULT 'standard',
                    amount NUMERIC(10, 2) NOT NULL
                        CHECK (amount >= 0),
                    currency CHAR(3) NOT NULL DEFAULT 'CAD',
                    billing_unit TEXT NOT NULL,
                    effective_from DATE NOT NULL
                        DEFAULT CURRENT_DATE,
                    effective_to DATE,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    CHECK (
                        effective_to IS NULL
                        OR effective_to >= effective_from
                    ),
                    CONSTRAINT prices_billing_unit_check_v2
                        CHECK (
                            billing_unit IN (
                                'per_item',
                                'per_hour',
                                'per_session',
                                'per_person',
                                'per_week',
                                'per_month'
                            )
                        ),
                    CONSTRAINT prices_catalog_unique
                        UNIQUE (
                            offering_id,
                            price_name,
                            effective_from
                        )
                )
                """
            )

            cursor.execute(
                """
                ALTER TABLE prices
                ADD COLUMN IF NOT EXISTS
                price_name TEXT NOT NULL
                DEFAULT 'standard'
                """
            )

            cursor.execute(
                """
                ALTER TABLE prices
                DROP CONSTRAINT IF EXISTS
                prices_billing_unit_check
                """
            )

            cursor.execute(
                """
                ALTER TABLE prices
                DROP CONSTRAINT IF EXISTS
                prices_offering_id_effective_from_key
                """
            )

            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'prices_billing_unit_check_v2'
                    ) THEN
                        ALTER TABLE prices
                        ADD CONSTRAINT
                        prices_billing_unit_check_v2
                        CHECK (
                            billing_unit IN (
                                'per_item',
                                'per_hour',
                                'per_session',
                                'per_person',
                                'per_week',
                                'per_month'
                            )
                        );
                    END IF;
                END
                $$
                """
            )

            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'prices_catalog_unique'
                    ) THEN
                        ALTER TABLE prices
                        ADD CONSTRAINT
                        prices_catalog_unique
                        UNIQUE (
                            offering_id,
                            price_name,
                            effective_from
                        );
                    END IF;
                END
                $$
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS courts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    location TEXT NOT NULL DEFAULT 'Main Club',
                    description TEXT NOT NULL DEFAULT '',
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS court_schedule (
                    id BIGSERIAL PRIMARY KEY,
                    court_id TEXT NOT NULL
                        REFERENCES courts(id)
                        ON DELETE CASCADE,
                    offering_id TEXT
                        REFERENCES offerings(id)
                        ON DELETE SET NULL,
                    coach_id TEXT
                        REFERENCES coaches(id)
                        ON DELETE SET NULL,
                    activity_name TEXT NOT NULL
                        DEFAULT 'Available',
                    start_at TIMESTAMPTZ NOT NULL,
                    end_at TIMESTAMPTZ NOT NULL,
                    slot_status TEXT NOT NULL
                        DEFAULT 'available'
                        CHECK (
                            slot_status IN (
                                'available',
                                'scheduled',
                                'blocked',
                                'maintenance'
                            )
                        ),
                    capacity INTEGER
                        CHECK (
                            capacity IS NULL
                            OR capacity > 0
                        ),
                    booked_count INTEGER NOT NULL DEFAULT 0
                        CHECK (booked_count >= 0),
                    notes TEXT NOT NULL DEFAULT '',

                    source TEXT NOT NULL DEFAULT 'manual',

                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    CHECK (end_at > start_at),
                    CHECK (
                        capacity IS NULL
                        OR booked_count <= capacity
                    ),
                    UNIQUE (
                        court_id,
                        start_at,
                        end_at
                    )
                )
                """
            )

            cursor.execute(
                """
                ALTER TABLE court_schedule
                ADD COLUMN IF NOT EXISTS
                source TEXT NOT NULL
                DEFAULT 'manual'
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_offerings_type
                ON offerings(offering_type)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_prices_current
                ON prices(offering_id, active)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_court_schedule_start
                ON court_schedule(start_at)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_court_schedule_court_start
                ON court_schedule(court_id, start_at)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_court_schedule_available
                ON court_schedule(start_at, court_id)
                WHERE slot_status = 'available'
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_conversations_created_at
                ON conversations(created_at)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_conversations_relevance
                ON conversations(relevance)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_feedback_conversation_id
                ON feedback(conversation_id)
                """
            )

        connection.commit()

    finally:
        connection.close()

import json


def save_conversation(
    conversation_id: str,
    question: str,
    answer_data: dict[str, Any],
    timestamp: datetime | None = None,
) -> None:
    if timestamp is None:
        timestamp = datetime.now(timezone)

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (
                    id,
                    question,
                    answer,
                    sources,
                    model_used,
                    judge_model,
                    response_time,
                    relevance,
                    relevance_explanation,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    eval_prompt_tokens,
                    eval_completion_tokens,
                    eval_total_tokens,
                    created_at
                )
                VALUES (
                    %s, %s, %s, %s::jsonb,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    conversation_id,
                    question,
                    answer_data["answer"],
                    json.dumps(
                        answer_data["sources"]
                    ),
                    answer_data["model_used"],
                    answer_data["judge_model"],
                    answer_data["response_time"],
                    answer_data["relevance"],
                    answer_data[
                        "relevance_explanation"
                    ],
                    answer_data["prompt_tokens"],
                    answer_data[
                        "completion_tokens"
                    ],
                    answer_data["total_tokens"],
                    answer_data[
                        "eval_prompt_tokens"
                    ],
                    answer_data[
                        "eval_completion_tokens"
                    ],
                    answer_data[
                        "eval_total_tokens"
                    ],
                    timestamp,
                ),
            )

        connection.commit()

    finally:
        connection.close()

def save_feedback(
    conversation_id: str,
    feedback: int,
    comment: str | None = None,
    timestamp: datetime | None = None,
) -> None:
    if feedback not in {-1, 1}:
        raise ValueError(
            "Feedback must be 1 or -1."
        )

    if timestamp is None:
        timestamp = datetime.now(timezone)

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feedback (
                    conversation_id,
                    feedback,
                    comment,
                    created_at
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    conversation_id,
                    feedback,
                    comment,
                    timestamp,
                ),
            )

        connection.commit()

    finally:
        connection.close()


def check_database_connection() -> bool:
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        return result == (1,)

    finally:
        connection.close()