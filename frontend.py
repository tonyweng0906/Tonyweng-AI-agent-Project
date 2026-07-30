import os
from typing import Any

import requests
import streamlit as st


API_URL = os.getenv(
    "BADMINTON_MATE_API_URL",
    os.getenv("COURTMATE_API_URL", "http://localhost:5000"),
)


st.set_page_config(
    page_title="Badminton Mate",
    page_icon="🏸",
    layout="centered",
)


def initialize_session() -> None:
    """Initialize values that must survive Streamlit reruns."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_conversation_id" not in st.session_state:
        st.session_state.last_conversation_id = None

    if "feedback_sent" not in st.session_state:
        st.session_state.feedback_sent = False


def check_api() -> bool:
    """Check whether the Flask API is reachable."""
    try:
        response = requests.get(
            f"{API_URL}/health",
            timeout=5,
        )
        return response.ok
    except requests.RequestException:
        return False


def extract_answer(data: dict[str, Any]) -> str:
    """Extract the assistant answer from the API response."""
    for key in ("answer", "response", "result", "message"):
        value = data.get(key)

        if isinstance(value, str) and value.strip():
            return value

    return "The server responded, but no answer was found."


def extract_conversation_id(data: dict[str, Any]) -> Any:
    """Extract the database conversation ID from the API response."""
    for key in ("conversation_id", "id"):
        value = data.get(key)

        if value is not None:
            return value

    return None


def ask_question(
    question: str,
    history: list[dict[str, str]],
) -> tuple[str, Any]:
    """Send a question and recent conversation history to the API."""
    response = requests.post(
        f"{API_URL}/question",
        json={
            "question": question,
            "history": history[-8:],
        },
        timeout=120,
    )

    response.raise_for_status()
    data = response.json()

    return extract_answer(data), extract_conversation_id(data)


def send_feedback(conversation_id: Any, score: int) -> None:
    """Send thumbs-up or thumbs-down feedback."""
    response = requests.post(
        f"{API_URL}/feedback",
        json={
            "conversation_id": conversation_id,
            "feedback": score,
        },
        timeout=10,
    )

    response.raise_for_status()


initialize_session()


st.title("🏸 Badminton Mate")
st.caption(
    "Your badminton club assistant for programs, coaching, "
    "facilities, schedules, policies, and membership information."
)


with st.sidebar:
    st.subheader("System status")

    if check_api():
        st.success("Badminton Mate API connected")
    else:
        st.error("Badminton Mate API unavailable")

    st.divider()

    st.markdown(
        """
        **How to ask a good question**

        You can ask about:

        - badminton programs;
        - coaching and skill levels;
        - court locations;
        - club policies;
        - membership information;
        - schedules and pricing in the knowledge base.
        """
    )

    st.info(
        "Schedule and availability information may not be live. "
        "Please confirm current availability with the club."
    )

    if st.button(
        "Clear conversation",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.session_state.last_conversation_id = None
        st.session_state.feedback_sent = False
        st.rerun()


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


question = st.chat_input(
    "Ask about badminton programs, coaching, courts, or club policies"
)


if question:
    conversation_history = (
        st.session_state.messages.copy()
    )

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(
            "Badminton Mate is checking the club knowledge base..."
        ):
            try:
                answer, conversation_id = ask_question(
                    question=question,
                    history=conversation_history,
                )

                st.markdown(answer)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

                st.session_state.last_conversation_id = (
                    conversation_id
                )
                st.session_state.feedback_sent = False

            except requests.ConnectionError:
                st.error(
                    "I could not connect to the Badminton Mate API. "
                    "Make sure the app container is running."
                )

            except requests.Timeout:
                st.error(
                    "The request took too long. Please try again."
                )

            except requests.HTTPError as error:
                status_code = error.response.status_code
                response_text = error.response.text

                st.error(
                    f"API request failed with status "
                    f"{status_code}.\n\n{response_text}"
                )

            except ValueError:
                st.error(
                    "The API returned a response that was not valid JSON."
                )


conversation_id = st.session_state.last_conversation_id


if (
    conversation_id is not None
    and not st.session_state.feedback_sent
):
    st.caption("Was this answer helpful?")

    positive_column, negative_column, _ = st.columns(
        [1, 1, 5]
    )

    with positive_column:
        if st.button("👍", help="Helpful"):
            try:
                send_feedback(conversation_id, 1)
                st.session_state.feedback_sent = True
                st.success("Thanks for your feedback.")
                st.rerun()

            except requests.RequestException as error:
                st.error(
                    f"Could not save feedback: {error}"
                )

    with negative_column:
        if st.button("👎", help="Not helpful"):
            try:
                send_feedback(conversation_id, -1)
                st.session_state.feedback_sent = True
                st.info(
                    "Thanks. Your feedback was recorded."
                )
                st.rerun()

            except requests.RequestException as error:
                st.error(
                    f"Could not save feedback: {error}"
                )


elif st.session_state.feedback_sent:
    st.caption("✓ Feedback submitted")
