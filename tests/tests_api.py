from app import app


def test_health_endpoint():
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_question_requires_question():
    client = app.test_client()

    response = client.post(
        "/question",
        json={},
    )

    assert response.status_code == 400


def test_question_rejects_blank_question():
    client = app.test_client()

    response = client.post(
        "/question",
        json={"question": "   "},
    )

    assert response.status_code == 400

def test_feedback_rejects_invalid_value():
    client = app.test_client()

    response = client.post(
        "/feedback",
        json={
            "conversation_id": "test-id",
            "feedback": 0,
        },
    )

    assert response.status_code == 400