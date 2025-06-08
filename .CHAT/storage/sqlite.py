import sqlite3
import json
from datetime import datetime

class SQLiteStorage:
    def __init__(self, db_path="history.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    user_id INTEGER,
                    query TEXT,
                    result TEXT,
                    timestamp DATETIME
                )
            """)
            conn.commit()

    def add_history(self, user_id: int, query: str, result: dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Count existing records
            cursor.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", (user_id,))
            count = cursor.fetchone()[0]
            
            # Delete oldest if limit reached
            if count >= 100:
                cursor.execute("""
                    DELETE FROM history
                    WHERE user_id = ? AND timestamp = (
                        SELECT MIN(timestamp) FROM history WHERE user_id = ?
                    )
                """, (user_id, user_id))
            
            # Insert new record
            cursor.execute("""
                INSERT INTO history (user_id, query, result, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, query, json.dumps(result), datetime.now()))
            conn.commit()

    def get_history(self, user_id: int, limit: int = 10):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT query, result, timestamp
                FROM history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            return [
                (row[0], json.loads(row[1]), datetime.fromisoformat(row[2]))
                for row in cursor.fetchall()
            ]

    def clear_old_records(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Delete records older than 30 days
            cursor.execute("""
                DELETE FROM history
                WHERE timestamp < datetime('now', '-30 days')
            """)
            conn.commit()