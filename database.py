
import sqlite3



def get_db_connection(db_path):
    """Open a connection to the SQLite database."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection



def init_db(db_path):
    """Create the agents table if it does not exist."""
    connection = get_db_connection(db_path)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                system_prompt TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id)
                    REFERENCES agents(id)
                    ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL
                    CHECK (length(trim(content)) > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
        """)

        connection.commit()
    finally:
        connection.close()


def create_agent(db_path, agent):
    """Save an agent in the database and return its stored data."""
    connection = get_db_connection(db_path)

    try:
        connection.execute(
            """
            INSERT INTO agents (id, name, description, system_prompt)
            VALUES (?, ?, ?, ?)
            """,
            (
                agent["id"],
                agent["name"],
                agent["description"],
                agent["system_prompt"],
            ),
        )

        connection.commit()

        row = connection.execute(
            "SELECT * FROM agents WHERE id = ?",
            (agent["id"],),
        ).fetchone()

        return dict(row)
    finally:
        connection.close()


def get_all_agents(db_path):
    """Retrieve all agents from the database."""
    connection = get_db_connection(db_path)

    try:
        rows = connection.execute(
            "SELECT * FROM agents ORDER BY rowid"
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()



def create_conversation(db_path, conversation):
    """Create a conversation for an existing agent."""
    connection = get_db_connection(db_path)

    try:
        connection.execute(
            """
            INSERT INTO conversations (id, agent_id, status)
            VALUES (?, ?, ?)
            """,
            (
                conversation["id"],
                conversation["agent_id"],
                conversation["status"],
            ),
        )
        connection.commit()

        row = connection.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation["id"],),
        ).fetchone()

        return dict(row)
    finally:
        connection.close()


def get_conversation(db_path, conversation_id):
    """Retrieve a conversation by its ID."""
    connection = get_db_connection(db_path)

    try:
        row = connection.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()

        return dict(row) if row is not None else None
    finally:
        connection.close()


def create_message(db_path, message):
    """Save a message and return its stored data."""
    connection = get_db_connection(db_path)

    try:
        connection.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (?, ?, ?, ?)
            """,
            (
                message["id"],
                message["conversation_id"],
                message["role"],
                message["content"],
            ),
        )

        connection.commit()

        row = connection.execute(
            "SELECT * FROM messages WHERE id = ?",
            (message["id"],),
        ).fetchone()

        return dict(row)
    finally:
        connection.close()


def get_messages(db_path, conversation_id):
    """Retrieve a conversation's messages in chronological order."""
    connection = get_db_connection(db_path)

    try:
        rows = connection.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at, rowid
            """,
            (conversation_id,),
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()
