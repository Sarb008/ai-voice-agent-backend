
from flask import Flask, request
from uuid import uuid4

app = Flask(__name__)

# Temporary in-memory storage for our agents
agents = {}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/agents")
def create_agent():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "Request body must be a JSON object"}, 400

    name = data.get("name")
    description = data.get("description", "")
    system_prompt = data.get("system_prompt")

    if not isinstance(name, str) or not name.strip():
        return {"error": "name is required and must be a non-empty string"}, 400

    if not isinstance(description, str):
        return {"error": "description must be a string"}, 400

    if not isinstance(system_prompt, str) or not system_prompt.strip():
        return {"error": "system_prompt is required and must be a non-empty string"}, 400

    agent_id = str(uuid4())

    agent = {
        "id": agent_id,
        "name": name.strip(),
        "description": description.strip(),
        "system_prompt": system_prompt.strip()
    }

    agents[agent_id] = agent

    return {"message": "Agent created successfully", "agent": agent}, 201


@app.get("/agents")
def list_agents():
    return {"agents": list(agents.values())}


if __name__ == "__main__":
    app.run(debug=True)
