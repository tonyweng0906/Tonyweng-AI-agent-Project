import time

import psycopg2

from courtmate.db import init_db


MAX_RETRIES = 15
RETRY_SECONDS = 2


def main() -> None:
    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            init_db()
            print(
                "Database initialized successfully."
            )
            return

        except psycopg2.OperationalError as exc:
            print(
                f"Database unavailable "
                f"(attempt {attempt}/{MAX_RETRIES}): "
                f"{exc}"
            )
            time.sleep(RETRY_SECONDS)

    raise RuntimeError(
        "Unable to initialize database."
    )


if __name__ == "__main__":
    main()