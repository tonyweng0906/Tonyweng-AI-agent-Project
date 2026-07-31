import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = Path(
    os.getenv(
        "DATA_PATH",
        PROJECT_ROOT / "data" / "knowledge_base.csv",
    )
)

BOOST_PATH = Path(
    os.getenv(
        "BOOST_PATH",
        PROJECT_ROOT / "data" / "best-minsearch-boost.json",
    )
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini",
)

OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small",
)

RETRIEVAL_CONFIG_PATH = Path(
    os.getenv(
        "RETRIEVAL_CONFIG_PATH",
        PROJECT_ROOT
        / "data"
        / "best-retrieval-config.json",
    )
)

OPENAI_JUDGE_MODEL = os.getenv(
    "OPENAI_JUDGE_MODEL",
    OPENAI_MODEL,
)

POSTGRES_HOST = os.getenv(
    "POSTGRES_HOST",
    "localhost",
)

POSTGRES_PORT = int(
    os.getenv(
        "POSTGRES_PORT",
        "5432",
    )
)

POSTGRES_DB = os.getenv(
    "POSTGRES_DB",
    "courtmate",
)

POSTGRES_USER = os.getenv(
    "POSTGRES_USER",
    "courtmate",
)

POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD",
    "courtmate",
)

TIMEZONE = os.getenv(
    "TZ",
    "America/Toronto",
)

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing."
    )