"""
Clear all data from the database
Run this to start fresh with face registration
"""

import sqlite3
import os

DB_PATH = "alerts.db"

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Delete all data from all tables
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM exams")
    cursor.execute("DELETE FROM users")
    
    conn.commit()
    conn.close()
    
    print("✅ All data cleared from database!")
    print("   - Users: 0")
    print("   - Exams: 0")
    print("   - Alerts: 0")
else:
    print("❌ Database file not found")
