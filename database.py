"""
Database module for gym reminder bot.
Handles storage and retrieval of workout programs and exercises.
"""

import sqlite3
from typing import List, Optional, Dict
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'gym.db')


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self):
        cur = self.conn.cursor()
        # users
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT
        )
        """)
        # programs
        cur.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day_name TEXT,
            created_at TEXT
        )
        """)
        # exercises
        cur.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER,
            name TEXT,
            reps INTEGER DEFAULT 0,
            sets INTEGER DEFAULT 0,
            weight REAL DEFAULT 0,
            gif TEXT,
            position INTEGER DEFAULT 0
        )
        """)
        # sessions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            program_id INTEGER,
            started_at TEXT,
            current_index INTEGER DEFAULT 0,
            closed INTEGER DEFAULT 0
        )
        """)
        # user settings
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            rest_seconds INTEGER DEFAULT 60
        )
        """)
        self.conn.commit()

    def add_user(self, user_id: int, username: Optional[str]):
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))
        self.conn.commit()

    def create_workout_program(self, user_id: int, day_name: str) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO programs (user_id, day_name, created_at) VALUES (?, ?, ?)",
                    (user_id, day_name, datetime.utcnow().isoformat()))
        self.conn.commit()
        return cur.lastrowid

    def get_program_by_user_day(self, user_id: int, day_name: str) -> Optional[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, day_name FROM programs WHERE user_id = ? AND day_name = ?",
                    (user_id, day_name))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_user_programs(self, user_id: int) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, day_name FROM programs WHERE user_id = ?", (user_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def delete_exercises(self, program_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM exercises WHERE program_id = ?", (program_id,))
        self.conn.commit()

    def add_exercise(self, program_id: int, name: str, reps: int, sets: int, weight: float = 0.0, gif: Optional[str] = None, position: int = 0):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO exercises (program_id, name, reps, sets, weight, gif, position)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (program_id, name, reps, sets, weight, gif, position))
        self.conn.commit()
        return cur.lastrowid

    def update_exercise(self, exercise_id: int, name: str, reps: int, sets: int, weight: float = 0.0, gif: Optional[str] = None):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE exercises SET name = ?, reps = ?, sets = ?, weight = ?, gif = ? WHERE id = ?
        """, (name, reps, sets, weight, gif, exercise_id))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_exercise_by_id(self, exercise_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_last_exercise(self, program_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM exercises WHERE program_id = ? ORDER BY position DESC, id DESC LIMIT 1", (program_id,))
        row = cur.fetchone()
        if not row:
            return False
        cur.execute("DELETE FROM exercises WHERE id = ?", (row['id'],))
        self.conn.commit()
        return True

    def get_exercises(self, program_id: int) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, reps, sets, weight, gif, position FROM exercises WHERE program_id = ? ORDER BY position ASC, id ASC", (program_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def create_workout_session(self, user_id: int, program_id: int) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO sessions (user_id, program_id, started_at, current_index) VALUES (?, ?, ?, ?)",
                    (user_id, program_id, datetime.utcnow().isoformat(), 0))
        self.conn.commit()
        return cur.lastrowid

    def update_session_exercise_index(self, session_id: int, index: int):
        cur = self.conn.cursor()
        cur.execute("UPDATE sessions SET current_index = ? WHERE id = ?", (index, session_id))
        self.conn.commit()

    def close_session(self, session_id: int):
        cur = self.conn.cursor()
        cur.execute("UPDATE sessions SET closed = 1 WHERE id = ?", (session_id,))
        self.conn.commit()

    def get_rest_seconds(self, user_id: int) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT rest_seconds FROM user_settings WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            return int(row['rest_seconds'])
        cur.execute("INSERT OR IGNORE INTO user_settings (user_id, rest_seconds) VALUES (?, ?)", (user_id, 60))
        self.conn.commit()
        return 60

    def set_rest_seconds(self, user_id: int, seconds: int):
        cur = self.conn.cursor()
        # SQLite upsert
        cur.execute("""
            INSERT INTO user_settings (user_id, rest_seconds) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET rest_seconds=excluded.rest_seconds
        """, (user_id, seconds))
        self.conn.commit()
