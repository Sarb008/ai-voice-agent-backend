
import sqlite3


def get_db_connection(db_path):
    """Open a connection to the SQLite database."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
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
