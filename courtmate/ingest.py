import json
from pathlib import Path
from typing import Any

import pandas as pd
from minsearch import Index

from courtmate.config import BOOST_PATH, DATA_PATH


TEXT_FIELDS = [
    "category",
    "title",
    "content",
    "coach_name",
    "skill_level",
    "location",
]

KEYWORD_FIELDS = ["id"]

DEFAULT_BOOST = {
    "category": 1.2,
    "title": 2.0,
    "content": 1.0,
    "coach_name": 1.5,
    "skill_level": 1.0,
    "location": 0.5,
}


def load_documents(
    data_path: Path = DATA_PATH,
) -> list[dict[str, Any]]:
    if not data_path.exists():
        raise FileNotFoundError(
            f"Knowledge-base file not found: {data_path}"
        )

    df = pd.read_csv(data_path).fillna("")

    required_columns = {
        "id",
        "category",
        "title",
        "content",
        "coach_name",
        "skill_level",
        "location",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Knowledge-base CSV is missing columns: "
            f"{sorted(missing_columns)}"
        )

    if not df["id"].is_unique:
        raise ValueError(
            "Knowledge-base document IDs must be unique."
        )

    return df.to_dict(orient="records")


def load_boost(
    boost_path: Path = BOOST_PATH,
) -> dict[str, float]:
    if not boost_path.exists():
        return DEFAULT_BOOST.copy()

    with open(
        boost_path,
        "r",
        encoding="utf-8",
    ) as file:
        boost = json.load(file)

    return {
        field: float(value)
        for field, value in boost.items()
    }


def load_index(
    data_path: Path = DATA_PATH,
) -> Index:
    documents = load_documents(data_path)

    index = Index(
        text_fields=TEXT_FIELDS,
        keyword_fields=KEYWORD_FIELDS,
    )

    index.fit(documents)
    print(
        f"Knowledge base loaded: "
        f"{len(documents)} documents"
    )
    return index

