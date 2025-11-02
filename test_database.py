"""
Test script for database functionality.
This script tests the database module without requiring a Telegram bot token.
"""

from database import Database
import os

# Use a test database
test_db_path = "/tmp/test_gym_bot.db"
if os.path.exists(test_db_path):
    os.remove(test_db_path)

db = Database(test_db_path)

print("🧪 Testing Database Functionality\n")

# Test 1: Add user
print("1️⃣ Testing user creation...")
db.add_user(12345, "test_user")
print("✅ User added successfully\n")

# Test 2: Create workout program
print("2️⃣ Testing workout program creation...")
program_id = db.create_workout_program(12345, "شنبه")
print(f"✅ Program created with ID: {program_id}\n")

# Test 3: Add exercises
print("3️⃣ Testing exercise addition...")
exercises_to_add = [
    ("پرس سینه", 4, 60.0, 0),
    ("زیر بغل", 3, 50.0, 1),
    ("جلو بازو", 3, 15.0, 2),
]

for name, sets, weight, order in exercises_to_add:
    db.add_exercise(program_id, name, sets, weight, order)
    print(f"   ✅ Added: {name} - {sets} sets - {weight}kg")

print()

# Test 4: Retrieve exercises
print("4️⃣ Testing exercise retrieval...")
exercises = db.get_exercises(program_id)
print(f"✅ Retrieved {len(exercises)} exercises:")
for i, ex in enumerate(exercises, 1):
    print(f"   {i}. {ex['name']} - {ex['sets']} sets - {ex['weight']}kg")

print()

# Test 5: Get user programs
print("5️⃣ Testing program retrieval...")
programs = db.get_user_programs(12345)
print(f"✅ User has {len(programs)} program(s):")
for prog in programs:
    print(f"   - {prog['day_name']}")

print()

# Test 6: Create workout session
print("6️⃣ Testing workout session creation...")
session_id = db.create_workout_session(12345, program_id)
print(f"✅ Session created with ID: {session_id}\n")

# Test 7: Get active session
print("7️⃣ Testing active session retrieval...")
active_session = db.get_active_session(12345)
if active_session:
    print(f"✅ Active session found:")
    print(f"   Session ID: {active_session['session_id']}")
    print(f"   Program ID: {active_session['program_id']}")
    print(f"   Current exercise index: {active_session['current_exercise_index']}")
else:
    print("❌ No active session found")

print()

# Test 8: Update session exercise index
print("8️⃣ Testing session exercise index update...")
db.update_session_exercise_index(session_id, 1)
active_session = db.get_active_session(12345)
print(f"✅ Exercise index updated to: {active_session['current_exercise_index']}\n")

# Test 9: Close session
print("9️⃣ Testing session closure...")
db.close_session(session_id)
active_session = db.get_active_session(12345)
if active_session:
    print("❌ Session still active!")
else:
    print("✅ Session closed successfully\n")

print("=" * 50)
print("🎉 All database tests passed successfully!")
print("=" * 50)

# Cleanup
os.remove(test_db_path)
print("\n🧹 Test database cleaned up")
