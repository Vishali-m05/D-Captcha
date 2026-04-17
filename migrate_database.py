"""
Database Migration Script
Recreates database with proper schema including student_id column
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "alerts.db"

print("🔧 Database Migration Script")
print("=" * 50)

# Backup old database if it exists
if os.path.exists(DB_PATH):
    backup_path = f"alerts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    print(f"📦 Backing up old database to: {backup_path}")
    os.rename(DB_PATH, backup_path)
    print("✅ Backup created")
else:
    print("ℹ️  No existing database found")

# Create new database with proper schema
print("\n🔨 Creating new database with proper schema...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create users table
print("   Creating users table...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'faculty'))
    )
""")

# Create alerts table WITH student_id
print("   Creating alerts table (with student_id)...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        violation TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id)
    )
""")

# Create exams table
print("   Creating exams table...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('in-progress', 'completed', 'terminated')),
        start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        end_time DATETIME,
        FOREIGN KEY (student_id) REFERENCES users(id)
    )
""")

conn.commit()
conn.close()

print("\n✅ Database migration complete!")
print(f"   Database: {DB_PATH}")
print("\n📋 Tables created:")
print("   ✅ users (id, name, email, password, role)")
print("   ✅ alerts (id, student_id, violation, timestamp)")
print("   ✅ exams (id, student_id, status, start_time, end_time)")
print("\n🚀 You can now start the backend server!")
print("   uvicorn backend.main:app --reload")
