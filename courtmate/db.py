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