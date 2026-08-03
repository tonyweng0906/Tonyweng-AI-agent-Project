import pytest

import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        app_module.db,
        "check_database_connection",
        lambda: True,
    )

    app_module.app.config.update(
        TESTING=True,
    )

    return app_module.app.test_client()


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.json["database"] == "connected"


def test_question_requires_question(client):
    response = client.post(
        "/question",
        json={},
    )

    assert response.status_code == 400


def test_question_rejects_blank_question(client):
    response = client.post(
        "/question",
        json={"question": "   "},
    )

    assert response.status_code == 400


def test_question_rejects_excessive_length(client):
    response = client.post(
        "/question",
        json={
            "question": "x" * (
                app_module.MAX_QUESTION_LENGTH + 1
            )
        },
    )

    assert response.status_code == 400
    assert "character limit" in response.json["error"]


def test_feedback_rejects_invalid_value(client):
    response = client.post(
        "/feedback",
        json={
            "conversation_id": "test-id",
            "feedback": 0,
        },
    )

    assert response.status_code == 400

def test_question_returns_answer_and_saves_conversation(
    client,
    monkeypatch,
):
    saved_conversation = {}

    def fake_run_rag(
        question: str,
        history: list[dict[str, str]],
    ):
        assert question == "What should I bring?"
        assert history == []

        return {
            "answer": "Bring court shoes, water, and a racket.",
            "sources": [
                {
                    "id": "faq-002",
                    "title": "What to bring",
                    "category": "faq",
                }
            ],
        }

    def fake_save_conversation(**kwargs):
        saved_conversation.update(kwargs)

    monkeypatch.setattr(
        app_module,
        "run_rag",
        fake_run_rag,
    )

    monkeypatch.setattr(
        app_module.db,
        "save_conversation",
        fake_save_conversation,
    )

    response = client.post(
        "/question",
        json={
            "question": "What should I bring?",
            "history": [],
        },
    )

    assert response.status_code == 200
    assert response.json["answer"] == (
        "Bring court shoes, water, and a racket."
    )
    assert response.json["question"] == (
        "What should I bring?"
    )
    assert response.json["conversation_id"]

    assert saved_conversation["question"] == (
        "What should I bring?"
    )
    assert saved_conversation["answer_data"]["answer"] == (
        "Bring court shoes, water, and a racket."
    )

