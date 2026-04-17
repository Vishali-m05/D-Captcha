"""
Migration script to add face_image column to users table
Run this to update your existing database
"""

import sqlite3
import shutil
from datetime import datetime

DB_PATH = "alerts.db"

# Backup the database first
backup_path = f"alerts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy(DB_PATH, backup_path)
print(f"✅ Database backed up to: {backup_path}")

# Add face_image column
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN face_image BLOB")
    conn.commit()
    print("✅ Added face_image column to users table")
except Exception as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️  face_image column already exists")
    else:
        print(f"❌ Error: {e}")

conn.close()
print("✅ Migration complete!")
