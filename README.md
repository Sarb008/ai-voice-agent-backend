# AI Voice Agent Backend

A Python REST API for creating AI agents, managing conversations, and generating contextual responses using Google's Gemini API. Conversation data is persisted in SQLite, and automated tests verify the API's core functionality.

## Features

- **Agent management:** Create and list AI agents with configurable system instructions.
- **Conversation management:** Create conversations associated with specific agents.
- **AI-powered responses:** Generate contextual replies using Google Gemini.
- **Conversation history:** Persist user and assistant messages in SQLite.
- **REST API:** JSON-based endpoints built with Flask.
- **Automated testing:** Validate API behavior and error handling using pytest.
- **Configuration and secrets:** Load API credentials from environment variables rather than hardcoding them in source files.

## Tech Stack

- Python
- Flask
- SQLite
- Google GenAI SDK
- Google Gemini API
- pytest
- python-dotenv

## Project Structure

```text
ai-voice-agent-backend/
├── app.py                # Flask application and API routes
├── database.py           # SQLite database operations
├── llm_provider.py       # Gemini integration
├── tests/
│   ├── test_agents.py
│   └── test_conversations.py
├── .env                  # Local environment variables (not committed)
├── .gitignore
├── agents.db             # Local SQLite database (not committed)
└── README.md
```

## Prerequisites

- Python 3.14.7 (the version used during development)
- A Google AI Studio API key with access to the configured Gemini model
- Git

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Sarb008/ai-voice-agent-backend.git
cd ai-voice-agent-backend
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the project's dependencies:

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key
GEMINI_MODEL=gemini-3.8-flash
```

Replace the API key placeholder with your own key. Never commit your real API key.

### 5. Start the server

```powershell
python app.py
```

The Flask development server runs locally. Use the address printed in the terminal to access the API.

## API Endpoints

All request and response bodies use JSON.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check whether the API is running |
| POST | `/agents` | Create an AI agent |
| GET | `/agents` | List available agents |
| POST | `/agents/<agent_id>/conversations` | Create a conversation for an agent |
| GET | `/conversations/<conversation_id>` | Retrieve conversation details |
| POST | `/conversations/<conversation_id>/messages` | Save a message and generate a Gemini reply for user messages |
| GET | `/conversations/<conversation_id>/messages` | Retrieve conversation history |

### Example workflow

#### 1. Check the API

```http
GET /health
```

#### 2. Create an agent

```http
POST /agents
Content-Type: application/json
```

```json
{
  "name": "Campus Helpdesk",
  "description": "An assistant that helps students with common campus questions.",
  "system_prompt": "You are a helpful campus helpdesk assistant. Give clear, practical answers to student questions."
}
```

Save the returned agent ID.

#### 3. Create a conversation

```http
POST /agents/<agent_id>/conversations
Content-Type: application/json
```

Replace `<agent_id>` with the ID returned when creating the agent. Save the returned conversation ID.

#### 4. Send a message

```http
POST /conversations/<conversation_id>/messages
Content-Type: application/json
```

```json
{
  "role": "user",
  "content": "Give me three practical tips for preparing for a database lab exam."
}
```

The API saves the user's message, sends the conversation context and agent instructions to Gemini, saves the generated assistant reply, and returns both messages.

#### 5. Retrieve conversation history

```http
GET /conversations/<conversation_id>/messages
```

The response contains the messages stored for that conversation.

## Running Tests

Run the automated test suite from the project root:

```powershell
python -m pytest -q
```

The tests cover agent and conversation operations, input validation, message history, mocked AI responses, and AI-provider failure handling.

## Security Notes

- Keep `.env` and `agents.db` out of version control.
- Never expose API keys in source code, commits, screenshots, or public logs.
- The Flask development server is intended for local development, not production deployment.
- Before production use, add appropriate authentication, authorization, rate limiting, and production-grade server configuration.

## Current Status

The backend supports persistent agent and conversation management, Gemini-generated responses, multi-turn message history, and automated tests.

## Future Improvements

- Add authentication and per-user agent ownership.
- Improve retry and recovery behavior when the AI provider fails.
- Add structured logging and request tracing.
- Introduce API schemas and more comprehensive integration tests.
- Add deployment configuration and operational monitoring.
