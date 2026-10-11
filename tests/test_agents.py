
import pytest

from app import app, agents


@pytest.fixture
def client():
    app.config["TESTING"] = True

    # Start each test with an empty agent collection.
    agents.clear()

    with app.test_client() as test_client:
        yield test_client

    agents.clear()


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_agent(client):
    response = client.post(
        "/agents",
        json={
            "name": "Campus Helpdesk",
            "description": "Answers student questions",
            "system_prompt": "You are a helpful assistant."
        }
    )

    assert response.status_code == 201

    data = response.get_json()
    assert data["message"] == "Agent created successfully"
    assert data["agent"]["name"] == "Campus Helpdesk"
    assert data["agent"]["id"]


def test_create_agent_without_name(client):
    response = client.post(
        "/agents",
        json={
            "system_prompt": "You are a helpful assistant."
        }
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "name is required and must be a non-empty string"
    )


def test_list_agents(client):
    client.post(
        "/agents",
        json={
            "name": "Campus Helpdesk",
            "description": "Answers student questions",
            "system_prompt": "You are a helpful assistant."
        }
    )

    response = client.get("/agents")

    assert response.status_code == 200
    assert len(response.get_json()["agents"]) == 1
    assert response.get_json()["agents"][0]["name"] == "Campus Helpdesk"
