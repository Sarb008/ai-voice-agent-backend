from llm_provider import generate_reply
from pathlib import Path
from uuid import uuid4
import time

from flask import Flask, request, render_template

from database import (
    init_db,
    create_agent,
    get_all_agents,
    create_conversation,
    get_conversation,
    create_message,
    get_messages,
    get_message_by_idempotency_key,
    consume_rate_limit,
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BASE_DIR / "agents.db"


def create_app(test_config=None):
    app = Flask(__name__)

    app.config["DATABASE"] = str(DEFAULT_DATABASE)

    if test_config is not None:
        app.config.update(test_config)

    init_db(app.config["DATABASE"])
    
    app.config.setdefault("AI_RATE_LIMIT", 10)
    app.config.setdefault("AI_RATE_WINDOW_SECONDS", 3600)
    
    @app.get("/")
    def index():
        return render_template("index.html")

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
            
        name = name.strip()
        description = description.strip()
        system_prompt = system_prompt.strip()

        if len(name) > 100:
            return {
                "error": "name must be at most 100 characters"
            }, 400

        if len(description) > 500:
            return {
                "error": "description must be at most 500 characters"
            }, 400

        if len(system_prompt) > 4000:
            return {
                "error": "system_prompt must be at most 4000 characters"
            }, 400

        agent = {
            "id": str(uuid4()),
            "name": name,
            "description": description,
            "system_prompt": system_prompt,
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

        db_path = app.config["DATABASE"]
        content = content.strip()
        
        if len(content) > 4000:
            return {
                "error": "content must be at most 4000 characters"
            }, 400

        # Idempotency keys are supported for user messages.
        idempotency_key = request.headers.get("Idempotency-Key")

        if idempotency_key is not None:
            idempotency_key = idempotency_key.strip()

            if not idempotency_key:
                return {
                    "error": "Idempotency-Key must not be empty"
                }, 400

            if len(idempotency_key) > 200:
                return {
                    "error": "Idempotency-Key must be at most 200 characters"
                }, 400

            if role != "user":
                return {
                    "error": "Idempotency-Key is supported only for user messages"
                }, 400

            existing_message = get_message_by_idempotency_key(
                db_path,
                idempotency_key,
                "user",
            )

            if existing_message is not None:
                if (
                    existing_message["conversation_id"] != conversation_id
                    or existing_message["content"] != content
                ):
                    return {
                        "error": (
                            "Idempotency-Key was already used "
                            "for a different request"
                        )
                    }, 409

                # A previous request may have saved the user message
                # but failed before saving the assistant response.
                history = get_messages(db_path, conversation_id)
                assistant_message = next(
                    (
                        message
                        for message in history
                        if message["role"] == "assistant"
                        and message.get("idempotency_key") == idempotency_key
                    ),
                    None,
                )

                if assistant_message is not None:
                    return {
                        "message": "Request already processed",
                        "data": existing_message,
                        "assistant_message": assistant_message,
                    }, 200

                saved_message = existing_message

            else:
                saved_message = None
        else:
            saved_message = None

        # Save a new message only if this request has not already
        # saved one under its idempotency key.
        if saved_message is None:
            user_message = {
                "id": str(uuid4()),
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "idempotency_key": idempotency_key,
            }

            try:
                saved_message = create_message(db_path, user_message)
            except Exception:
                # Another request may have inserted the same key
                # between our lookup and insert.
                if idempotency_key is None:
                    raise

                existing_message = get_message_by_idempotency_key(
                    db_path,
                    idempotency_key,
                    "user",
                )

                if existing_message is None:
                    raise

                if (
                    existing_message["conversation_id"] != conversation_id
                    or existing_message["content"] != content
                ):
                    return {
                        "error": (
                            "Idempotency-Key was already used "
                            "for a different request"
                        )
                    }, 409

                saved_message = existing_message

                history = get_messages(db_path, conversation_id)
                assistant_message = next(
                    (
                        message
                        for message in history
                        if message["role"] == "assistant"
                        and message.get("idempotency_key") == idempotency_key
                    ),
                    None,
                )

                if assistant_message is not None:
                    return {
                        "message": "Request already processed",
                        "data": saved_message,
                        "assistant_message": assistant_message,
                    }, 200

        # Manually submitted assistant messages remain supported
        # when no idempotency key is supplied.
        if role == "assistant":
            return {
                "message": "Message created successfully",
                "data": saved_message,
            }, 201

        agents = get_all_agents(db_path)
        agent = next(
            (
                item for item in agents
                if item["id"] == conversation["agent_id"]
            ),
            None,
        )

        if agent is None:
            app.logger.error(
                "Agent %s not found for conversation %s",
                conversation["agent_id"],
                conversation_id,
            )
            return {"error": "Conversation agent not found"}, 500
        
        forwarded_for = request.headers.get("X-Forwarded-For")

        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.remote_addr or "unknown"

        allowed, retry_after = consume_rate_limit(
            db_path,
            client_ip,
            app.config["AI_RATE_LIMIT"],
            app.config["AI_RATE_WINDOW_SECONDS"],
            int(time.time()),
        )

        if not allowed:
            return {
                "error": "AI request rate limit exceeded",
                "retry_after_seconds": retry_after,
            }, 429

        history = get_messages(db_path, conversation_id)

        try:
            reply = generate_reply(agent["system_prompt"], history)
        except Exception:
            app.logger.exception(
                "AI response generation failed for conversation %s",
                conversation_id,
            )
            return {
                "error": (
                    "AI response generation failed. "
                    "Your message was saved; please retry with the same "
                    "Idempotency-Key."
                )
            }, 502

        assistant_message = {
            "id": str(uuid4()),
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": reply,
            "idempotency_key": idempotency_key,
        }

        saved_assistant_message = create_message(
            db_path,
            assistant_message,
        )

        return {
            "message": "AI response generated successfully",
            "data": saved_message,
            "assistant_message": saved_assistant_message,
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
