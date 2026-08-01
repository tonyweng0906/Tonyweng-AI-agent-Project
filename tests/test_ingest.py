import json

import pytest

from courtmate.ingest import (
    DEFAULT_BOOST,
    load_boost,
    load_documents,
)


VALID_CSV = """id,category,title,content,coach_name,skill_level,location
faq-001,faq,Racket rental,Rackets are available at the front desk,,,Main Club
coach-001,coach,Coach Amy,Coach Amy teaches beginners,Coach Amy,beginner,Main Club
"""


def test_load_documents_from_valid_csv(
    tmp_path,
):
    csv_path = (
        tmp_path / "knowledge_base.csv"
    )
    csv_path.write_text(
        VALID_CSV,
        encoding="utf-8",
    )

    documents = load_documents(csv_path)

    assert len(documents) == 2
    assert documents[0]["id"] == "faq-001"
    assert documents[0]["title"] == "Racket rental"
    assert documents[1]["coach_name"] == "Coach Amy"


def test_load_documents_rejects_missing_file(
    tmp_path,
):
    missing_path = (
        tmp_path / "missing.csv"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Knowledge-base file not found",
    ):
        load_documents(missing_path)


def test_load_documents_rejects_missing_columns(
    tmp_path,
):
    csv_path = (
        tmp_path / "invalid.csv"
    )
    csv_path.write_text(
        "id,title\nfaq-001,Racket rental\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="missing columns",
    ):
        load_documents(csv_path)


def test_load_documents_rejects_duplicate_ids(
    tmp_path,
):
    csv_path = (
        tmp_path / "duplicates.csv"
    )
    csv_path.write_text(
        (
            "id,category,title,content,"
            "coach_name,skill_level,location\n"
            "faq-001,faq,First,First document,,,\n"
            "faq-001,faq,Second,Second document,,,\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="document IDs must be unique",
    ):
        load_documents(csv_path)


def test_load_boost_uses_default_when_file_missing(
    tmp_path,
):
    missing_path = (
        tmp_path / "missing-boost.json"
    )

    boost = load_boost(missing_path)

    assert boost == DEFAULT_BOOST
    assert boost is not DEFAULT_BOOST


def test_load_boost_reads_json_configuration(
    tmp_path,
):
    boost_path = (
        tmp_path / "boost.json"
    )
    boost_path.write_text(
        json.dumps(
            {
                "title": 3,
                "content": 1.5,
            }
        ),
        encoding="utf-8",
    )

    boost = load_boost(boost_path)

    assert boost == {
        "title": 3.0,
        "content": 1.5,
    }