
from pathlib import Path
from uuid import uuid4

from flask import Flask, request

from database import init_db, create_agent, get_all_agents


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BASE_DIR / "agents.db"


def create_app(test_config=None):
    app = Flask(__name__)

    app.config["DATABASE"] = str(DEFAULT_DATABASE)

    if test_config is not None:
        app.config.update(test_config)

    init_db(app.config["DATABASE"])

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    @app.post("/agents")
    def create_agent_endpoint():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return {"error": "Request body must be a JSON object"}, 400

        name = data.get("name")
        description = data.get("description", "")
        system_prompt = data.get("system_prompt")

        if not isinstance(name, str) or not name.strip():
            return {
                "error": "name is required and must be a non-empty string"
            }, 400

        if not isinstance(description, str):
            return {"error": "description must be a string"}, 400

        if (
            not isinstance(system_prompt, str)
            or not system_prompt.strip()
        ):
            return {
                "error": "system_prompt is required and must be a non-empty string"
            }, 400

        agent = {
            "id": str(uuid4()),
            "name": name.strip(),
            "description": description.strip(),
            "system_prompt": system_prompt.strip(),
        }

        saved_agent = create_agent(app.config["DATABASE"], agent)

        return {
            "message": "Agent created successfully",
            "agent": saved_agent,
        }, 201

    @app.get("/agents")
    def list_agents():
        saved_agents = get_all_agents(app.config["DATABASE"])
        return {"agents": saved_agents}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
