
from pathlib import Path
from uuid import uuid4

from flask import Flask, request

from database import (
    init_db,
    create_agent,
    get_all_agents,
    create_conversation,
    get_conversation,
    create_message,
    get_messages,
)


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
    
    
    @app.post("/agents/<agent_id>/conversations")
    def create_conversation_endpoint(agent_id):
        data = request.get_json(silent=True)

        if data is not None and not isinstance(data, dict):
            return {"error": "Request body must be a JSON object"}, 400

        agent_exists = any(
            agent["id"] == agent_id
            for agent in get_all_agents(app.config["DATABASE"])
        )

        if not agent_exists:
            return {"error": "Agent not found"}, 404

        conversation = {
            "id": str(uuid4()),
            "agent_id": agent_id,
            "status": "active",
        }

        saved_conversation = create_conversation(
            app.config["DATABASE"],
            conversation,
        )

        return {
            "message": "Conversation created successfully",
            "conversation": saved_conversation,
        }, 201

    @app.get("/conversations/<conversation_id>")
    def get_conversation_endpoint(conversation_id):
        conversation = get_conversation(
            app.config["DATABASE"],
            conversation_id,
        )

        if conversation is None:
            return {"error": "Conversation not found"}, 404

        return {"conversation": conversation}, 200

    
    @app.post("/conversations/<conversation_id>/messages")
    def create_message_endpoint(conversation_id):
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return {"error": "Request body must be a JSON object"}, 400

        role = data.get("role")
        content = data.get("content")

        if role not in ("user", "assistant"):
            return {
                "error": "role must be 'user' or 'assistant'"
            }, 400

        if not isinstance(content, str) or not content.strip():
            return {
                "error": "content must be a non-empty string"
            }, 400

        conversation = get_conversation(
            app.config["DATABASE"],
            conversation_id,
        )

        if conversation is None:
            return {"error": "Conversation not found"}, 404

        message = {
            "id": str(uuid4()),
            "conversation_id": conversation_id,
            "role": role,
            "content": content.strip(),
        }

        saved_message = create_message(
            app.config["DATABASE"],
            message,
        )

        return {
            "message": "Message created successfully",
            "data": saved_message,
        }, 201

    @app.get("/conversations/<conversation_id>/messages")
    def list_messages_endpoint(conversation_id):
        conversation = get_conversation(
            app.config["DATABASE"],
            conversation_id,
        )

        if conversation is None:
            return {"error": "Conversation not found"}, 404

        messages = get_messages(
            app.config["DATABASE"],
            conversation_id,
        )

        return {"messages": messages}, 200


    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
