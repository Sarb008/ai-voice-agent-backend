# AgentForge — AI Agent Backend

AgentForge is a deployed Python/Flask application for creating configurable AI agents, managing persistent conversations, and generating context-aware responses using Google's Gemini API.

The project focuses on backend engineering concerns around AI-powered applications, including REST API design, persistent conversation state, idempotent request handling, input validation, rate limiting, provider-failure handling, automated testing, and production deployment.

A lightweight browser interface is included so the backend can be tested without installing or configuring a local client.

## Live Demo

**Public demo:** https://ai-voice-agent-backend-27ag.onrender.com/

The application is hosted on Render's free tier, so the service may take a short time to wake after inactivity. Gemini responses can also occasionally be affected by upstream model availability or API quota limits.

## Features

- **Configurable AI agents:** Create agents with custom names, descriptions, and system prompts.
- **Persistent conversations:** Create conversations associated with individual agents and store their history in SQLite.
- **Context-aware Gemini responses:** Send previous conversation messages and agent instructions to Gemini for multi-turn responses.
- **Recruiter-friendly browser demo:** Create agents and chat with them directly through a lightweight web interface.
- **Per-agent session restoration:** Restore the selected agent and its conversation when returning to or refreshing the browser demo.
- **Idempotent message handling:** Use `Idempotency-Key` headers to prevent duplicate message storage and repeated AI generation for completed requests.
- **Failure recovery:** Preserve user messages when AI generation fails so requests can safely be retried with the same idempotency key.
- **Transient provider retries:** Retry temporary Gemini `503 Service Unavailable` failures with bounded exponential backoff.
- **API input validation:** Enforce validation and size limits for agent configuration and message content.
- **Request rate limiting:** Apply per-client AI-generation limits backed by SQLite to protect the public demo from excessive usage.
- **Automated testing:** Test API behavior, validation, persistence, AI-provider failures, idempotency, and rate limiting with pytest.
- **Environment-based configuration:** Keep Gemini credentials and model configuration outside source control.
- **Production deployment:** Serve the Flask application with Gunicorn and deploy it publicly on Render.

## Tech Stack

- Python
- Flask
- SQLite
- Google GenAI SDK
- Google Gemini API
- pytest
- Gunicorn
- python-dotenv
- HTML, CSS, and JavaScript
- Render

## Project Structure

```text
ai-voice-agent-backend/
|-- app.py
|-- database.py
|-- llm_provider.py
|-- requirements.txt
|-- templates/
|   `-- index.html
|-- tests/
|   |-- test_agents.py
|   `-- test_conversations.py
|-- .env
|-- .gitignore
|-- agents.db
`-- README.md
```

`app.py` contains the Flask application and API routes, `database.py` handles SQLite persistence and rate-limit storage, and `llm_provider.py` contains the Gemini integration and transient-provider retry logic.

The local `.env` and `agents.db` files are excluded from version control.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Open the AgentForge browser demo |
| `GET` | `/health` | Check API health |
| `POST` | `/agents` | Create an AI agent |
| `GET` | `/agents` | List available agents |
| `POST` | `/agents/<agent_id>/conversations` | Create a conversation for an agent |
| `GET` | `/conversations/<conversation_id>` | Retrieve conversation details |
| `POST` | `/conversations/<conversation_id>/messages` | Save a message and generate an AI response |
| `GET` | `/conversations/<conversation_id>/messages` | Retrieve conversation history |

## Example Workflow

### 1. Create an agent

```http
POST /agents
Content-Type: application/json
```

```json
{
  "name": "Campus Helpdesk",
  "description": "Helps students with common campus questions.",
  "system_prompt": "You are a helpful campus assistant. Give clear and practical answers."
}
```

### 2. Create a conversation

```http
POST /agents/<agent_id>/conversations
```

### 3. Send a message

```http
POST /conversations/<conversation_id>/messages
Content-Type: application/json
Idempotency-Key: request-001
```

```json
{
  "role": "user",
  "content": "Give me three practical tips for preparing for a database lab exam."
}
```

For a user message, AgentForge:

1. validates the request;
2. checks idempotency state;
3. persists the user message;
4. loads the agent and conversation history;
5. applies the AI-generation rate limit;
6. sends the conversation context and system prompt to Gemini;
7. retries temporary Gemini `503` failures with bounded backoff;
8. persists the generated assistant response; and
9. returns both messages to the client.

## Idempotent Retries

The message endpoint accepts an optional `Idempotency-Key` header for user messages.

If a completed request is repeated with the same key and payload, AgentForge returns the previously stored result rather than generating another AI response.

If the same key is reused with different message content or for another conversation, the API returns `409 Conflict`.

If AI generation fails after the user message has been stored, the client can retry with the same key. AgentForge reuses the existing user message and attempts response generation again rather than inserting a duplicate.

The implementation is designed for ordinary request retries. It does not claim distributed exactly-once AI execution under simultaneous concurrent requests.

## Reliability and Abuse Protection

The public demo includes several safeguards:

- maximum lengths for agent names, descriptions, system prompts, and messages;
- per-client rate limiting for AI-generation requests;
- idempotency protection against duplicate completed requests;
- persistence of user messages across provider failures;
- bounded retries for temporary Gemini `503` responses;
- explicit error handling for AI-provider failures; and
- a Gunicorn request timeout appropriate for slower external AI calls.

The current rate limiter uses SQLite because the deployed demo runs as a small single-service application. A horizontally scaled production system would typically move shared rate-limit state to infrastructure such as Redis.

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/Sarb008/ai-voice-agent-backend.git
cd ai-voice-agent-backend
```

### 2. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure Gemini

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key
GEMINI_MODEL=your_gemini_model
```

Never commit the real API key.

### 5. Start the development server

```powershell
python app.py
```

Open the local address printed by Flask to use the AgentForge browser interface.

## Running Tests

```powershell
python -m pytest -q
```

The current automated suite contains **23 passing tests** covering agent and conversation operations, validation, persistent message history, mocked AI responses, provider failures, idempotent retries, conflicting idempotency keys, recovery after failed AI generation, message-size limits, and rate-limit behavior.

## Deployment

The public demo is deployed on Render and served using Gunicorn.

Production start command:

```text
gunicorn --timeout 120 app:app
```

Secrets such as `GEMINI_API_KEY` and model configuration are supplied through deployment environment variables rather than committed to the repository.

Because the current demo uses SQLite on a free hosted instance, stored demo data should not be treated as durable production data and may be reset when the service filesystem is recreated.

## Security Notes

- API credentials are loaded from environment variables.
- `.env` and local SQLite database files are excluded from Git.
- User-controlled text is validated and size-limited by the backend.
- The public AI endpoint is rate-limited.
- Generated Markdown in the browser interface is sanitized before rendering.
- Authentication and authorization are intentionally outside the scope of the current public portfolio demo.

## Current Status

AgentForge is a functional deployed portfolio project with persistent AI-agent conversations, Gemini integration, idempotent request handling, provider-failure recovery, API validation, rate limiting, automated testing, and a browser-based demonstration interface.

The project is intentionally scoped as a backend-focused AI application rather than a full production multi-user platform.

## Future Improvements

- Add authentication and per-user agent ownership.
- Replace SQLite with PostgreSQL for durable hosted persistence.
- Use Redis-backed distributed rate limiting for horizontally scaled deployments.
- Add structured logging, request tracing, and operational metrics.
- Add API documentation and broader integration testing.