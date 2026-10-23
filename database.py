
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
        
        connection.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_key TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_rate_limit_events_client_time
            ON rate_limit_events (client_key, created_at)
        """)
        
                # Add idempotency support to existing databases.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(messages)"
            ).fetchall()
        }

        if "idempotency_key" not in columns:
            connection.execute(
                "ALTER TABLE messages ADD COLUMN idempotency_key TEXT"
            )

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_messages_idempotency_key_role
            ON messages (idempotency_key, role)
            WHERE idempotency_key IS NOT NULL
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
            INSERT INTO messages (
                id,
                conversation_id,
                role,
                content,
                idempotency_key
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                message["id"],
                message["conversation_id"],
                message["role"],
                message["content"],
                message.get("idempotency_key"),
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
        
def get_message_by_idempotency_key(
    db_path,
    idempotency_key,
    role,
):
    """Find an existing message associated with a request key."""
    connection = get_db_connection(db_path)

    try:
        row = connection.execute(
            """
            SELECT *
            FROM messages
            WHERE idempotency_key = ?
              AND role = ?
            """,
            (idempotency_key, role),
        ).fetchone()

        return dict(row) if row is not None else None
    finally:
        connection.close()
        
def consume_rate_limit(db_path, client_key, limit, window_seconds, now):
    """
    Consume one rate-limit slot.

    Returns (allowed, retry_after_seconds).
    """
    connection = get_db_connection(db_path)

    try:
        window_start = now - window_seconds

        connection.execute(
            """
            DELETE FROM rate_limit_events
            WHERE created_at <= ?
            """,
            (window_start,),
        )

        rows = connection.execute(
            """
            SELECT created_at
            FROM rate_limit_events
            WHERE client_key = ?
              AND created_at > ?
            ORDER BY created_at ASC
            """,
            (client_key, window_start),
        ).fetchall()

        if len(rows) >= limit:
            oldest = rows[0]["created_at"]
            retry_after = max(
                1,
                window_seconds - (now - oldest),
            )

            connection.commit()
            return False, retry_after

        connection.execute(
            """
            INSERT INTO rate_limit_events (
                client_key,
                created_at
            )
            VALUES (?, ?)
            """,
            (client_key, now),
        )

        connection.commit()
        return True, 0

    finally:
        connection.close()
