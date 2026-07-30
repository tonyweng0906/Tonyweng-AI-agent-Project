import uuid

from flask import Flask, jsonify, request

from courtmate import db
from courtmate.rag import rag


app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    try:
        database_ready = (
            db.check_database_connection()
        )

    except Exception:
        database_ready = False

    status_code = (
        200 if database_ready else 503
    )

    return (
        jsonify(
            {
                "status": (
                    "ok"
                    if database_ready
                    else "degraded"
                ),
                "service": "courtmate-ai",
                "database": (
                    "connected"
                    if database_ready
                    else "unavailable"
                ),
            }
        ),
        status_code,
    )

@app.route("/question", methods=["POST"])
def handle_question():
    data = request.get_json(
        silent=True,
    ) or {}

    question = str(
        data.get("question", "")
    ).strip()

    raw_history = data.get("history", [])
    history: list[dict[str, str]] = []

    if isinstance(raw_history, list):
        for message in raw_history[-8:]:
            if not isinstance(message, dict):
                continue

            role = str(
                message.get("role", "")
            ).strip()

            content = str(
                message.get("content", "")
            ).strip()

            if role not in {"user", "assistant"}:
                continue

            if not content:
                continue

            history.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    if not question:
        return (
            jsonify(
                {
                    "error": (
                        "The 'question' field is required."
                    )
                }
            ),
            400,
        )

    conversation_id = str(uuid.uuid4())

    try:
        answer_data = rag(
            question=question,
            history=history,
        )

        db.save_conversation(
            conversation_id=conversation_id,
            question=question,
            answer_data=answer_data,
        )

    except Exception:
        app.logger.exception(
            "Question processing failed."
        )

        return (
            jsonify(
                {
                    "conversation_id": (
                        conversation_id
                    ),
                    "error": (
                        "Unable to process the question."
                    ),
                }
            ),
            500,
        )

    return (
        jsonify(
            {
                "conversation_id": (
                    conversation_id
                ),
                "question": question,
                **answer_data,
            }
        ),
        200,
    )

@app.route("/feedback", methods=["POST"])
def handle_feedback():
    data = request.get_json(
        silent=True,
    ) or {}

    conversation_id = str(
        data.get("conversation_id", "")
    ).strip()

    feedback = data.get("feedback")
    comment = data.get("comment")

    if not conversation_id:
        return (
            jsonify(
                {
                    "error": (
                        "conversation_id is required."
                    )
                }
            ),
            400,
        )

    if feedback not in {-1, 1}:
        return (
            jsonify(
                {
                    "error": (
                        "feedback must be 1 or -1."
                    )
                }
            ),
            400,
        )

    try:
        db.save_feedback(
            conversation_id=conversation_id,
            feedback=feedback,
            comment=comment,
        )

    except Exception:
        app.logger.exception(
            "Feedback could not be saved."
        )

        return (
            jsonify(
                {
                    "error": (
                        "Unable to save feedback."
                    )
                }
            ),
            500,
        )

    return (
        jsonify(
            {
                "message": "Feedback received.",
                "conversation_id": (
                    conversation_id
                ),
                "feedback": feedback,
            }
        ),
        201,
    )

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
    )