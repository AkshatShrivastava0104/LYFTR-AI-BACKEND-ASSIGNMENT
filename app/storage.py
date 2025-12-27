import os
import sqlite3
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

        # ✅ ensure parent directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    from_msisdn TEXT NOT NULL,
                    to_msisdn TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    text TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_from_msisdn ON messages(from_msisdn)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ts ON messages(ts)
            """)
            conn.commit()

    def insert_message(self, message_id: str, from_msisdn: str, to_msisdn: str,
                       ts: str, text: Optional[str]) -> bool:
        try:
            with self.get_connection() as conn:
                created_at = datetime.utcnow().isoformat() + 'Z'
                conn.execute("""
                    INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (message_id, from_msisdn, to_msisdn, ts, text, created_at))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_messages(self, limit: int = 50, offset: int = 0, from_filter: Optional[str] = None,
                     since: Optional[str] = None, q: Optional[str] = None):
        with self.get_connection() as conn:
            where_clauses = []
            params = []

            if from_filter:
                where_clauses.append("from_msisdn = ?")
                params.append(from_filter)

            if since:
                where_clauses.append("ts >= ?")
                params.append(since)

            if q:
                where_clauses.append("text LIKE ?")
                params.append(f"%{q}%")

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            count_query = f"SELECT COUNT(*) as total FROM messages WHERE {where_sql}"
            total = conn.execute(count_query, params).fetchone()['total']

            data_query = f"""
                SELECT message_id, from_msisdn, to_msisdn, ts, text
                FROM messages
                WHERE {where_sql}
                ORDER BY ts ASC, message_id ASC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            rows = conn.execute(data_query, params).fetchall()

            messages = [{
                'message_id': row['message_id'],
                'from': row['from_msisdn'],
                'to': row['to_msisdn'],
                'ts': row['ts'],
                'text': row['text']
            } for row in rows]

            return {
                'data': messages,
                'total': total,
                'limit': limit,
                'offset': offset
            }

    def get_stats(self):
        with self.get_connection() as conn:
            total_query = "SELECT COUNT(*) as total FROM messages"
            total_messages = conn.execute(total_query).fetchone()['total']

            senders_query = "SELECT COUNT(DISTINCT from_msisdn) as count FROM messages"
            senders_count = conn.execute(senders_query).fetchone()['count']

            per_sender_query = """
                SELECT from_msisdn, COUNT(*) as count
                FROM messages
                GROUP BY from_msisdn
                ORDER BY count DESC
                LIMIT 10
            """
            per_sender = conn.execute(per_sender_query).fetchall()
            messages_per_sender = [{'from': row['from_msisdn'], 'count': row['count']}
                                   for row in per_sender]

            ts_query = "SELECT MIN(ts) as first_ts, MAX(ts) as last_ts FROM messages"
            ts_result = conn.execute(ts_query).fetchone()

            return {
                'total_messages': total_messages,
                'senders_count': senders_count,
                'messages_per_sender': messages_per_sender,
                'first_message_ts': ts_result['first_ts'],
                'last_message_ts': ts_result['last_ts']
            }

    def is_healthy(self) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False
