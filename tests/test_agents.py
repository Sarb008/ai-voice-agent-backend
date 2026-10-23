
import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    test_database = tmp_path / "test_agents.db"

    app = create_app({
        "TESTING": True,
        "DATABASE": str(test_database),
    })

    with app.test_client() as test_client:
        yield test_client


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
            "system_prompt": "You are a helpful assistant.",
        },
    )

    assert response.status_code == 201

    data = response.get_json()
    assert data["message"] == "Agent created successfully"
    assert data["agent"]["name"] == "Campus Helpdesk"
    assert data["agent"]["id"]
    assert data["agent"]["created_at"]


def test_create_agent_without_name(client):
    response = client.post(
        "/agents",
        json={"system_prompt": "You are a helpful assistant."},
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
            "system_prompt": "You are a helpful assistant.",
        },
    )

    response = client.get("/agents")

    assert response.status_code == 200

    data = response.get_json()
    assert len(data["agents"]) == 1
    assert data["agents"][0]["name"] == "Campus Helpdesk"


def test_agent_persists_after_app_restart(tmp_path):
    database_path = str(tmp_path / "persistent_agents.db")

    first_app = create_app({
        "TESTING": True,
        "DATABASE": database_path,
    })

    with first_app.test_client() as client:
        response = client.post(
            "/agents",
            json={
                "name": "Persistent Agent",
                "description": "Persistence test",
                "system_prompt": "You are a test assistant.",
            },
        )

        assert response.status_code == 201
        created_id = response.get_json()["agent"]["id"]

    # Create a fresh Flask app using the same database file.
    second_app = create_app({
        "TESTING": True,
        "DATABASE": database_path,
    })

    with second_app.test_client() as client:
        response = client.get("/agents")

        assert response.status_code == 200
        saved_agents = response.get_json()["agents"]

        assert len(saved_agents) == 1
        assert saved_agents[0]["id"] == created_id
        assert saved_agents[0]["name"] == "Persistent Agent"
        
@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        (
            "name",
            "x" * 101,
            "name must be at most 100 characters",
        ),
        (
            "description",
            "x" * 501,
            "description must be at most 500 characters",
        ),
        (
            "system_prompt",
            "x" * 4001,
            "system_prompt must be at most 4000 characters",
        ),
    ],
)
def test_create_agent_rejects_oversized_fields(
    client,
    field,
    value,
    expected_error,
):
    payload = {
        "name": "Test Agent",
        "description": "Description",
        "system_prompt": "You are helpful.",
    }

    payload[field] = value

    response = client.post("/agents", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == expected_error
