"""
Database module for gym reminder bot.
Handles storage and retrieval of workout programs and exercises.
"""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "gym_bot.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Workout programs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_programs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    day_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, day_name)
                )
            """)
            
            # Exercises table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    program_id INTEGER NOT NULL,
                    exercise_name TEXT NOT NULL,
                    sets INTEGER NOT NULL,
                    weight REAL,
                    order_index INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (program_id) REFERENCES workout_programs (id) ON DELETE CASCADE
                )
            """)
            
            # Workout sessions table (to track active sessions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    program_id INTEGER NOT NULL,
                    current_exercise_index INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (program_id) REFERENCES workout_programs (id)
                )
            """)
            
            conn.commit()

    def add_user(self, user_id: int, username: str = None):
        """Add or update user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, username)
                VALUES (?, ?)
            """, (user_id, username))
            conn.commit()

    def create_workout_program(self, user_id: int, day_name: str) -> int:
        """Create a new workout program for a specific day."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO workout_programs (user_id, day_name)
                VALUES (?, ?)
            """, (user_id, day_name))
            conn.commit()
            
            # Get the program ID
            cursor.execute("""
                SELECT id FROM workout_programs
                WHERE user_id = ? AND day_name = ?
            """, (user_id, day_name))
            
            result = cursor.fetchone()
            return result[0] if result else None

    def add_exercise(self, program_id: int, exercise_name: str, sets: int, weight: float, order_index: int):
        """Add an exercise to a workout program."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO exercises (program_id, exercise_name, sets, weight, order_index)
                VALUES (?, ?, ?, ?, ?)
            """, (program_id, exercise_name, sets, weight, order_index))
            conn.commit()

    def get_workout_program(self, user_id: int, day_name: str) -> Optional[int]:
        """Get workout program ID for a user and day."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM workout_programs
                WHERE user_id = ? AND day_name = ?
            """, (user_id, day_name))
            
            result = cursor.fetchone()
            return result[0] if result else None

    def get_exercises(self, program_id: int) -> List[Dict]:
        """Get all exercises for a workout program."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, exercise_name, sets, weight, order_index
                FROM exercises
                WHERE program_id = ?
                ORDER BY order_index
            """, (program_id,))
            
            exercises = []
            for row in cursor.fetchall():
                exercises.append({
                    'id': row[0],
                    'name': row[1],
                    'sets': row[2],
                    'weight': row[3],
                    'order_index': row[4]
                })
            
            return exercises

    def delete_exercises(self, program_id: int):
        """Delete all exercises from a workout program."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM exercises WHERE program_id = ?
            """, (program_id,))
            conn.commit()

    def get_user_programs(self, user_id: int) -> List[Dict]:
        """Get all workout programs for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, day_name FROM workout_programs
                WHERE user_id = ?
                ORDER BY day_name
            """, (user_id,))
            
            programs = []
            for row in cursor.fetchall():
                programs.append({
                    'id': row[0],
                    'day_name': row[1]
                })
            
            return programs

    def create_workout_session(self, user_id: int, program_id: int) -> int:
        """Create a new workout session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Close any existing active sessions for this user
            cursor.execute("""
                UPDATE workout_sessions
                SET is_active = 0
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            # Create new session
            cursor.execute("""
                INSERT INTO workout_sessions (user_id, program_id, current_exercise_index)
                VALUES (?, ?, 0)
            """, (user_id, program_id))
            
            conn.commit()
            return cursor.lastrowid

    def get_active_session(self, user_id: int) -> Optional[Dict]:
        """Get active workout session for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, program_id, current_exercise_index
                FROM workout_sessions
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'session_id': result[0],
                    'program_id': result[1],
                    'current_exercise_index': result[2]
                }
            return None

    def update_session_exercise_index(self, session_id: int, exercise_index: int):
        """Update the current exercise index for a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workout_sessions
                SET current_exercise_index = ?
                WHERE id = ?
            """, (exercise_index, session_id))
            conn.commit()

    def close_session(self, session_id: int):
        """Close a workout session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workout_sessions
                SET is_active = 0
                WHERE id = ?
            """, (session_id,))
            conn.commit()
