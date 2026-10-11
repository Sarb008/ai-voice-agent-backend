from unittest.mock import patch
import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    database_path = str(tmp_path / "test_conversations.db")

    app = create_app({
        "TESTING": True,
        "DATABASE": database_path,
    })

    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def agent_id(client):
    response = client.post(
        "/agents",
        json={
            "name": "Campus Helpdesk",
            "description": "Answers student questions",
            "system_prompt": "You are a helpful assistant.",
        },
    )

    assert response.status_code == 201
    return response.get_json()["agent"]["id"]


def test_create_conversation(client, agent_id):
    response = client.post(
        f"/agents/{agent_id}/conversations"
    )

    assert response.status_code == 201

    data = response.get_json()
    conversation = data["conversation"]

    assert data["message"] == "Conversation created successfully"
    assert conversation["agent_id"] == agent_id
    assert conversation["status"] == "active"
    assert conversation["id"]
    assert conversation["created_at"]


def test_create_conversation_for_missing_agent(client):
    response = client.post(
        "/agents/nonexistent-agent/conversations"
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Agent not found"


def test_get_conversation(client, agent_id):
    create_response = client.post(
        f"/agents/{agent_id}/conversations"
    )
    conversation_id = create_response.get_json()["conversation"]["id"]

    response = client.get(f"/conversations/{conversation_id}")

    assert response.status_code == 200

    conversation = response.get_json()["conversation"]
    assert conversation["id"] == conversation_id
    assert conversation["agent_id"] == agent_id


def test_get_missing_conversation(client):
    response = client.get("/conversations/nonexistent-conversation")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Conversation not found"



def test_create_message(client, agent_id):
    conversation_response = client.post(
        f"/agents/{agent_id}/conversations"
    )
    conversation_id = conversation_response.get_json()["conversation"]["id"]

    with patch(
        "app.generate_reply",
        return_value="Hello! How can I help you?",
    ) as mock_generate:
        response = client.post(
            f"/conversations/{conversation_id}/messages",
            json={
                "role": "user",
                "content": "Hello, can you help me?",
            },
        )

    assert response.status_code == 201

    data = response.get_json()
    user_message = data["data"]
    assistant_message = data["assistant_message"]

    assert data["message"] == "AI response generated successfully"

    assert user_message["conversation_id"] == conversation_id
    assert user_message["role"] == "user"
    assert user_message["content"] == "Hello, can you help me?"
    assert user_message["id"]

    assert assistant_message["conversation_id"] == conversation_id
    assert assistant_message["role"] == "assistant"
    assert assistant_message["content"] == "Hello! How can I help you?"
    assert assistant_message["id"]

    mock_generate.assert_called_once_with(
        "You are a helpful assistant.",
        [
            {
                "id": user_message["id"],
                "conversation_id": conversation_id,
                "role": "user",
                "content": "Hello, can you help me?",
                "created_at": user_message["created_at"],
            }
        ],
    )


def test_create_message_with_invalid_role(client, agent_id):
    conversation_response = client.post(
        f"/agents/{agent_id}/conversations"
    )
    conversation_id = conversation_response.get_json()["conversation"]["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={
            "role": "system",
            "content": "Invalid role",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "role must be 'user' or 'assistant'"


def test_create_message_with_empty_content(client, agent_id):
    conversation_response = client.post(
        f"/agents/{agent_id}/conversations"
    )
    conversation_id = conversation_response.get_json()["conversation"]["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={
            "role": "user",
            "content": "   ",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "content must be a non-empty string"



def test_list_messages(client, agent_id):
    conversation_response = client.post(
        f"/agents/{agent_id}/conversations"
    )
    conversation_id = conversation_response.get_json()["conversation"]["id"]

    with patch(
        "app.generate_reply",
        return_value="Hi! How can I help?",
    ):
        response = client.post(
            f"/conversations/{conversation_id}/messages",
            json={
                "role": "user",
                "content": "Hello",
            },
        )

    assert response.status_code == 201

    response = client.get(
        f"/conversations/{conversation_id}/messages"
    )

    assert response.status_code == 200

    messages = response.get_json()["messages"]

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi! How can I help?"


def test_ai_failure_preserves_user_message(client, agent_id):
    conversation_response = client.post(
        f"/agents/{agent_id}/conversations"
    )
    conversation_id = conversation_response.get_json()["conversation"]["id"]

    with patch(
        "app.generate_reply",
        side_effect=RuntimeError("Simulated provider failure"),
    ):
        response = client.post(
            f"/conversations/{conversation_id}/messages",
            json={
                "role": "user",
                "content": "Can you help me?",
            },
        )

    assert response.status_code == 502
    assert "AI response generation failed" in response.get_json()["error"]

    history_response = client.get(
        f"/conversations/{conversation_id}/messages"
    )

    assert history_response.status_code == 200

    messages = history_response.get_json()["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Can you help me?"
