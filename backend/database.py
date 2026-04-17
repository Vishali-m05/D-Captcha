"""
Database module for D-CAPTCHA system
Handles SQLite database operations for logging violations and user management
"""

import sqlite3
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Database path
DB_PATH = "alerts.db"

# Thread lock for thread-safe database access
db_lock = threading.Lock()


def init_database():
    """
    Initialize SQLite database and create all required tables.
    This function is called when the backend starts.
    
    Tables created:
    - users: Store faculty and student information
    - alerts: Store violation logs with student reference
    - exams: Store exam sessions and their status
    """
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create users table (Admin NOT stored here - hardcoded)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'faculty')),
                face_image BLOB
            )
        """)
        
        # Create alerts table with student_id reference
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
        
        # Create question_papers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faculty_id INTEGER NOT NULL,
                paper_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                total_marks INTEGER NOT NULL,
                duration_minutes INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (faculty_id) REFERENCES users(id)
            )
        """)
        
        # Create questions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL CHECK(correct_option IN ('A', 'B', 'C', 'D')),
                marks INTEGER NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES question_papers(id)
            )
        """)
        
        # Create exam_assignments table (for scheduled exams)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                class_id INTEGER,
                scheduled_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES question_papers(id)
            )
        """)
        
        # Create student_responses table (for storing student answers)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                student_answer TEXT,
                is_correct BOOLEAN,
                marks_obtained INTEGER,
                FOREIGN KEY (exam_id) REFERENCES exams(id),
                FOREIGN KEY (student_id) REFERENCES users(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    print(f"✅ Database initialized: {DB_PATH}")
    print("   ✅ users table")
    print("   ✅ alerts table")
    print("   ✅ exams table")
    print("   ✅ question_papers table")
    print("   ✅ questions table")
    print("   ✅ exam_assignments table")
    print("   ✅ student_responses table")


def log_alert(violation: str, student_id: Optional[int] = None):
    """
    Log a violation alert to the database.
    This function is called from the monitoring thread when a violation is detected.
    
    Args:
        violation: Description of the violation (e.g., "Mobile Phone Detected")
        student_id: ID of the student being monitored (optional for backward compatibility)
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Insert violation with current timestamp and student_id
            cursor.execute(
                "INSERT INTO alerts (student_id, violation, timestamp) VALUES (?, ?, ?)",
                (student_id, violation, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            conn.commit()
            conn.close()
            
            print(f"⚠️  Violation logged: {violation} (Student ID: {student_id})")
            
        except Exception as e:
            print(f"❌ Error logging alert: {e}")


def get_all_alerts() -> List[Dict]:
    """
    Retrieve all violation alerts from the database.
    Used by the GET /alerts endpoint.
    
    Returns:
        List of dictionaries containing violation and timestamp
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Fetch all alerts ordered by timestamp (newest first)
            cursor.execute(
                "SELECT violation, timestamp FROM alerts ORDER BY timestamp DESC"
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries
            alerts = [
                {
                    "violation": row[0],
                    "timestamp": row[1]
                }
                for row in rows
            ]
            
            return alerts
            
        except Exception as e:
            print(f"❌ Error fetching alerts: {e}")
            return []


def clear_alerts():
    """
    Clear all alerts from the database.
    Useful for starting a fresh exam session.
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM alerts")
            
            conn.commit()
            conn.close()
            
            print("🗑️  All alerts cleared")
            
        except Exception as e:
            print(f"❌ Error clearing alerts: {e}")


def get_alert_count() -> int:
    """
    Get the total number of alerts in the database.
    
    Returns:
        Total count of alerts
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM alerts")
            count = cursor.fetchone()[0]
            
            conn.close()
            
            return count
            
        except Exception as e:
            print(f"❌ Error getting alert count: {e}")
            return 0


# ============================================================================
# USER MANAGEMENT FUNCTIONS
# ============================================================================

def create_user(name: str, email: str, password: str, role: str) -> Dict:
    """
    Create a new user (student or faculty).
    Admin is NOT stored in database - hardcoded in auth.py
    
    Args:
        name: User's full name
        email: User's email (must be unique)
        password: Plain text password (college project - no encryption)
        role: "student" or "faculty"
    
    Returns:
        Dictionary with success status and user_id or error message
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return {"success": False, "message": "Email already registered"}
            
            # Insert new user
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name, email, password, role)
            )
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ User created: {name} ({role}) - ID: {user_id}")
            
            return {"success": True, "user_id": user_id, "role": role}
            
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return {"success": False, "message": str(e)}


def get_user_by_email(email: str) -> Optional[Dict]:
    """
    Get user details by email.
    
    Args:
        email: User's email
    
    Returns:
        User dictionary or None if not found
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, email, password, role FROM users WHERE email = ?",
                (email,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "password": row[3],
                    "role": row[4]
                }
            return None
            
        except Exception as e:
            print(f"❌ Error fetching user: {e}")
            return None


def get_all_students() -> List[Dict]:
    """
    Get all students for faculty/admin dashboard.
    
    Returns:
        List of student dictionaries
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, email FROM users WHERE role = 'student' ORDER BY name"
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            students = [
                {
                    "id": row[0],
                    "name": row[1],
                    "email": row[2]
                }
                for row in rows
            ]
            
            return students
            
        except Exception as e:
            print(f"❌ Error fetching students: {e}")
            return []


def get_all_faculty() -> List[Dict]:
    """
    Get all faculty for admin dashboard.
    
    Returns:
        List of faculty dictionaries
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, email FROM users WHERE role = 'faculty' ORDER BY name"
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            faculty = [
                {
                    "id": row[0],
                    "name": row[1],
                    "email": row[2]
                }
                for row in rows
            ]
            
            return faculty
            
        except Exception as e:
            print(f"❌ Error fetching faculty: {e}")
            return []


def get_all_users() -> List[Dict]:
    """
    Get all users (students and faculty) for admin dashboard.
    
    Returns:
        List of user dictionaries
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, email, role FROM users ORDER BY role, name"
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            users = [
                {
                    "id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "role": row[3]
                }
                for row in rows
            ]
            
            return users
            
        except Exception as e:
            print(f"❌ Error fetching users: {e}")
            return []


# ============================================================================
# EXAM MANAGEMENT FUNCTIONS
# ============================================================================

def create_exam(student_id: int) -> int:
    """
    Create a new exam session for a student.
    
    Args:
        student_id: ID of the student taking the exam
    
    Returns:
        Exam ID
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO exams (student_id, status, start_time) VALUES (?, 'in-progress', ?)",
                (student_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            exam_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"📝 Exam started: Student ID {student_id}, Exam ID {exam_id}")
            
            return exam_id
            
        except Exception as e:
            print(f"❌ Error creating exam: {e}")
            return 0


def has_student_started_paper(student_id: int, paper_id: int) -> bool:
    """
    Check if a student has already started a paper (has an in-progress exam).
    
    Args:
        student_id: ID of the student
        paper_id: ID of the paper
    
    Returns:
        True if student has an in-progress exam for this paper, False otherwise
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if there's any in-progress exam for this student
            # A student can only do one exam at a time
            cursor.execute("""
                SELECT COUNT(*) FROM exams
                WHERE student_id = ? AND status = 'in-progress'
            """, (student_id,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            print(f"❌ Error checking exam status: {e}")
            return False


def _has_student_started_paper_unlocked(cursor, student_id: int) -> bool:
    """
    Internal version - check if student has in-progress exam WITHOUT acquiring lock.
    Must be called from within an existing db_lock context.
    
    Args:
        cursor: SQLite cursor (already locked)
        student_id: ID of the student
    
    Returns:
        True if student has a VALID in-progress exam, False otherwise
        (Auto-completes expired exams)
    """
    try:
        # Check if there's any in-progress exam for this student
        # A student can only do one exam at a time
        cursor.execute("""
            SELECT id, start_time FROM exams
            WHERE student_id = ? AND status = 'in-progress'
        """, (student_id,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return False
        
        # Check if any are expired (older than 2 hours)
        now = datetime.now()
        for exam_id, start_time_str in rows:
            try:
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                elapsed = (now - start_time).total_seconds()
                
                # If exam started more than 2 hours ago, mark it as completed
                if elapsed > 7200:  # 2 hours
                    print(f"   ⚠️ Auto-completing expired in-progress exam (started {elapsed/60:.0f} min ago)")
                    cursor.execute(
                        "UPDATE exams SET status = 'completed' WHERE id = ?",
                        (exam_id,)
                    )
                else:
                    # Still valid in-progress exam
                    return True
            except Exception as e:
                print(f"   ⚠️ Error checking exam expiry: {e}")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error checking exam status (unlocked): {e}")
        return False


def update_exam_status(exam_id: int, status: str):
    """
    Update exam status (completed or terminated).
    
    Args:
        exam_id: ID of the exam
        status: "completed" or "terminated"
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE exams SET status = ?, end_time = ? WHERE id = ?",
                (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), exam_id)
            )
            
            conn.commit()
            conn.close()
            
            print(f"✅ Exam {exam_id} status updated: {status}")
            
        except Exception as e:
            print(f"❌ Error updating exam status: {e}")


def save_student_response(exam_id: int, student_id: int, question_id: int, student_answer: str) -> bool:
    """
    Save a student's answer to a question.
    
    Args:
        exam_id: ID of the exam
        student_id: ID of the student
        question_id: ID of the question
        student_answer: The selected answer ('A', 'B', 'C', or 'D')
    
    Returns:
        True if successful, False otherwise
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get the question to check correct answer
            cursor.execute("SELECT correct_option FROM questions WHERE id = ?", (question_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"⚠️ Question {question_id} not found")
                conn.close()
                return False
            
            correct_answer = result[0]
            is_correct = (student_answer == correct_answer)
            
            # Insert student response
            cursor.execute("""
                INSERT INTO student_responses 
                (exam_id, student_id, question_id, student_answer, is_correct)
                VALUES (?, ?, ?, ?, ?)
            """, (exam_id, student_id, question_id, student_answer, is_correct))
            
            conn.commit()
            conn.close()
            
            status = "✅ Correct" if is_correct else "❌ Incorrect"
            print(f"📝 Response saved for Q{question_id}: {student_answer} {status}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving student response: {e}")
            return False


def get_student_alerts(student_id: int) -> List[Dict]:
    """
    Get all alerts for a specific student.
    Used by faculty to review student violations.
    
    Args:
        student_id: ID of the student
    
    Returns:
        List of alert dictionaries
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT violation, timestamp FROM alerts WHERE student_id = ? ORDER BY timestamp DESC",
                (student_id,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            alerts = [
                {
                    "violation": row[0],
                    "timestamp": row[1]
                }
                for row in rows
            ]
            
            return alerts
            
        except Exception as e:
            print(f"❌ Error fetching student alerts: {e}")
            return []


def get_student_alert_count(student_id: int) -> int:
    """
    Get the number of violations for a specific student.
    Used to determine if exam should be terminated.
    
    Args:
        student_id: ID of the student
    
    Returns:
        Count of alerts
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT COUNT(*) FROM alerts WHERE student_id = ?",
                (student_id,)
            )
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
            
        except Exception as e:
            print(f"❌ Error getting student alert count: {e}")
            return 0


def get_all_exams() -> List[Dict]:
    """
    Get all exam records for admin dashboard.
    
    Returns:
        List of exam dictionaries with student info
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.id, e.student_id, u.name, e.status, e.start_time, e.end_time
                FROM exams e
                JOIN users u ON e.student_id = u.id
                ORDER BY e.start_time DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            exams = [
                {
                    "exam_id": row[0],
                    "student_id": row[1],
                    "student_name": row[2],
                    "status": row[3],
                    "start_time": row[4],
                    "end_time": row[5]
                }
                for row in rows
            ]
            
            return exams
            
        except Exception as e:
            print(f"❌ Error fetching exams: {e}")
            return []


def get_student_exams(student_id: int) -> List[Dict]:
    """
    Get exam history for a specific student.
    
    Args:
        student_id: ID of the student
    
    Returns:
        List of exam dictionaries
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, status, start_time, end_time FROM exams WHERE student_id = ? ORDER BY start_time DESC",
                (student_id,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            exams = [
                {
                    "exam_id": row[0],
                    "status": row[1],
                    "start_time": row[2],
                    "end_time": row[3]
                }
                for row in rows
            ]
            
            return exams
            
        except Exception as e:
            print(f"❌ Error fetching student exams: {e}")
            return []


# ============================================================================
# FACE IMAGE MANAGEMENT FUNCTIONS
# ============================================================================

def store_face_image(user_id: int, face_image_bytes: bytes) -> bool:
    """
    Store face image for a user in the database.
    
    Args:
        user_id: ID of the user
        face_image_bytes: Face image as bytes (JPEG format)
    
    Returns:
        True if successful, False otherwise
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE users SET face_image = ? WHERE id = ?",
                (face_image_bytes, user_id)
            )
            
            conn.commit()
            conn.close()
            
            print(f"✅ Face image stored for user ID: {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error storing face image: {e}")
            return False


def get_face_image(user_id: int) -> Optional[bytes]:
    """
    Retrieve face image for a user from the database.
    
    Args:
        user_id: ID of the user
    
    Returns:
        Face image as bytes or None if not found
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT face_image FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result and result[0]:
                return result[0]
            return None
            
        except Exception as e:
            print(f"❌ Error retrieving face image: {e}")
            return None


# ============================================================================
# QUESTION PAPER & EXAM CONFIGURATION FUNCTIONS
# ============================================================================

def create_question_paper(faculty_id: int, paper_name: str, subject: str, total_marks: int, duration_minutes: int) -> int:
    """
    Create a new question paper with metadata.
    
    Args:
        faculty_id: ID of the faculty creating the paper
        paper_name: Name of the question paper (e.g., "Midterm Exam 2026")
        subject: Subject/Course name
        total_marks: Total marks for the exam
        duration_minutes: Duration of exam in minutes
    
    Returns:
        Question paper ID or 0 if failed
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO question_papers (faculty_id, paper_name, subject, total_marks, duration_minutes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (faculty_id, paper_name, subject, total_marks, duration_minutes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            paper_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Question paper created: {paper_name} (ID: {paper_id}) - Duration: {duration_minutes} min")
            return paper_id
            
        except Exception as e:
            print(f"❌ Error creating question paper: {e}")
            return 0


def add_question(paper_id: int, question_text: str, option_a: str, option_b: str, option_c: str, option_d: str, correct_option: str, marks: int) -> int:
    """
    Add a multiple choice question to a question paper.
    
    Args:
        paper_id: ID of the question paper
        question_text: The question text
        option_a, option_b, option_c, option_d: Answer options
        correct_option: Correct answer ('A', 'B', 'C', or 'D')
        marks: Marks for this question
    
    Returns:
        Question ID or 0 if failed
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Validate correct_option
            if correct_option not in ['A', 'B', 'C', 'D']:
                raise ValueError("Correct option must be A, B, C, or D")
            
            cursor.execute("""
                INSERT INTO questions (paper_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (paper_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks))
            
            question_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Question added: ID {question_id} to Paper ID {paper_id}")
            return question_id
            
        except Exception as e:
            print(f"❌ Error adding question: {e}")
            return 0


def get_question_paper(paper_id: int) -> Optional[Dict]:
    """
    Get question paper details with all questions.
    
    Args:
        paper_id: ID of the question paper
    
    Returns:
        Dictionary with paper info and questions list
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get paper details
            cursor.execute("""
                SELECT id, faculty_id, paper_name, subject, total_marks, duration_minutes, created_at
                FROM question_papers WHERE id = ?
            """, (paper_id,))
            
            paper_row = cursor.fetchone()
            if not paper_row:
                conn.close()
                return None
            
            # Get all questions for this paper
            cursor.execute("""
                SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option, marks
                FROM questions WHERE paper_id = ? ORDER BY id ASC
            """, (paper_id,))
            
            question_rows = cursor.fetchall()
            conn.close()
            
            questions = [
                {
                    "question_id": row[0],
                    "question_text": row[1],
                    "options": {
                        "A": row[2],
                        "B": row[3],
                        "C": row[4],
                        "D": row[5]
                    },
                    "correct_option": row[6],
                    "marks": row[7]
                }
                for row in question_rows
            ]
            
            return {
                "paper_id": paper_row[0],
                "faculty_id": paper_row[1],
                "paper_name": paper_row[2],
                "subject": paper_row[3],
                "total_marks": paper_row[4],
                "duration_minutes": paper_row[5],
                "created_at": paper_row[6],
                "total_questions": len(questions),
                "questions": questions
            }
            
        except Exception as e:
            print(f"❌ Error fetching question paper: {e}")
            return None


def get_faculty_question_papers(faculty_id: int) -> List[Dict]:
    """
    Get all question papers created by a faculty.
    
    Args:
        faculty_id: ID of the faculty
    
    Returns:
        List of question paper dictionaries
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, paper_name, subject, total_marks, duration_minutes, created_at,
                       (SELECT COUNT(*) FROM questions WHERE paper_id = question_papers.id) as total_questions
                FROM question_papers WHERE faculty_id = ? ORDER BY created_at DESC
            """, (faculty_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            papers = [
                {
                    "paper_id": row[0],
                    "paper_name": row[1],
                    "subject": row[2],
                    "total_marks": row[3],
                    "duration_minutes": row[4],
                    "created_at": row[5],
                    "total_questions": row[6]
                }
                for row in rows
            ]
            
            return papers
            
        except Exception as e:
            print(f"❌ Error fetching faculty papers: {e}")
            return []


def assign_question_paper(paper_id: int, class_id: int, scheduled_date: str, start_time: str) -> int:
    """
    Assign a question paper to a class at a scheduled date/time.
    
    Args:
        paper_id: ID of the question paper
        class_id: ID of the class (placeholder - can be extended)
        scheduled_date: Date in format "YYYY-MM-DD"
        start_time: Time in format "HH:MM"
    
    Returns:
        Assignment ID or 0 if failed
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO exam_assignments (paper_id, class_id, scheduled_date, start_time, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (paper_id, class_id, scheduled_date, start_time, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            assignment_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Question paper assigned: Paper ID {paper_id} on {scheduled_date} at {start_time}")
            return assignment_id
            
        except Exception as e:
            print(f"❌ Error assigning question paper: {e}")
            return 0


def get_available_exams_for_student(student_id: int) -> List[Dict]:
    """
    Get exams scheduled for a student that haven't expired and haven't been completed.
    
    Filters:
    1. Only shows exams with scheduled_date >= today
    2. Only shows exams where current time is BEFORE exam end time (scheduled_date + start_time + duration_minutes)
    3. Excludes exams that the student has already completed/submitted
    
    Args:
        student_id: ID of the student
    
    Returns:
        List of available exam dictionaries
    """
    print(f"\n{'='*80}")
    print(f"🔍 GETTING AVAILABLE EXAMS for student_id={student_id}")
    print(f"{'='*80}")
    
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # First, let's see ALL exams in the database for debugging
            cursor.execute("""
                SELECT ea.id, qp.id, qp.paper_name, qp.subject, qp.duration_minutes, qp.total_marks,
                       ea.scheduled_date, ea.start_time
                FROM exam_assignments ea
                JOIN question_papers qp ON ea.paper_id = qp.id
                ORDER BY ea.scheduled_date ASC, ea.start_time ASC
            """)
            
            all_rows = cursor.fetchall()
            print(f"\n📊 DEBUG: Total exams in database: {len(all_rows)}")
            for row in all_rows:
                print(f"   - {row[2]}: {row[6]} {row[7]}")
            
            # Get current datetime for comparison
            now = datetime.now()
            print(f"⏰ DEBUG: Current datetime: {now} (timezone: {now.tzinfo})")
            print(f"📅 DEBUG: Current date: {now.date()}")
            
            # Now filter by date >= today
            cursor.execute("""
                SELECT ea.id, qp.id, qp.paper_name, qp.subject, qp.duration_minutes, qp.total_marks,
                       ea.scheduled_date, ea.start_time
                FROM exam_assignments ea
                JOIN question_papers qp ON ea.paper_id = qp.id
                WHERE ea.scheduled_date >= date('now')
                ORDER BY ea.scheduled_date ASC, ea.start_time ASC
            """)
            
            rows = cursor.fetchall()
            print(f"📋 DEBUG: Exams after date filter (>= today): {len(rows)}")
            for row in rows:
                print(f"   - {row[2]}: {row[6]} {row[7]}")
            
            # Filter exams based on time and completion status
            available_exams = []
            for row in rows:
                assignment_id = row[0]
                paper_id = row[1]
                paper_name = row[2]
                subject = row[3]
                duration_minutes = row[4]
                total_marks = row[5]
                scheduled_date = row[6]
                start_time = row[7]
                
                try:
                    # Parse scheduled date and time - handle multiple time formats
                    try:
                        # Try standard HH:MM format first
                        scheduled_dt = datetime.strptime(f"{scheduled_date} {start_time}", "%Y-%m-%d %H:%M")
                    except ValueError:
                        try:
                            # Try HH:MM:SS format
                            scheduled_dt = datetime.strptime(f"{scheduled_date} {start_time}", "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            # Try ISO format with microseconds
                            time_part = start_time.split('.')[0] if '.' in start_time else start_time
                            scheduled_dt = datetime.strptime(f"{scheduled_date} {time_part}", "%Y-%m-%d %H:%M:%S")
                    
                    visibility_start_dt = scheduled_dt - timedelta(minutes=5)  # Show 5 min before exam
                    exam_end_dt = scheduled_dt + timedelta(minutes=duration_minutes)
                    
                    print(f"\n🔍 DEBUG: Checking exam '{paper_name}'")
                    print(f"   Stored: {scheduled_date} {start_time}")
                    print(f"   Parsed scheduled_dt: {scheduled_dt}")
                    print(f"   Visibility starts: {visibility_start_dt}")
                    print(f"   Exam ends: {exam_end_dt}")
                    print(f"   Now: {now}")
                    print(f"   now < visibility_start: {now < visibility_start_dt}")
                    print(f"   now > exam_end: {now > exam_end_dt}")
                    
                    # ✅ CHECK 1: Current time is within visibility window (5 min before to end time)
                    if now < visibility_start_dt:
                        print(f"   ⏱️  SKIPPED: Not yet available")
                        continue  # Exam not yet available
                    
                    if now > exam_end_dt:
                        print(f"   ⏭️  SKIPPED: Duration expired")
                        continue  # Skip this exam - it has expired
                    
                    print(f"   ✅ Passed time checks")
                    
                    try:
                        # ✅ CHECK 2: Check if student has already completed this paper
                        cursor.execute("""
                            SELECT COUNT(*) FROM student_responses
                            WHERE student_id = ? AND question_id IN (
                                SELECT id FROM questions WHERE paper_id = ?
                            )
                        """, (student_id, paper_id))
                        
                        completed_count = cursor.fetchone()[0]
                        print(f"   Checking completion: completed_count={completed_count}")
                        if completed_count > 0:
                            print(f"   ✅ SKIPPED: Student already submitted")
                            continue  # Skip - student already completed this exam
                        
                        print(f"   ✅ AVAILABLE - Adding to list")
                        
                        # This exam is available - include scheduled_dt for frontend timer calculation
                        available_exams.append({
                            "assignment_id": assignment_id,
                            "paper_id": paper_id,
                            "paper_name": paper_name,
                            "subject": subject,
                            "duration_minutes": duration_minutes,
                            "total_marks": total_marks,
                            "scheduled_date": scheduled_date,
                            "start_time": start_time,
                            "scheduled_datetime": scheduled_dt.strftime("%Y-%m-%d %H:%M:%S")
                        })
                    
                    except Exception as check_error:
                        print(f"   ❌ ERROR during checks: {type(check_error).__name__}: {str(check_error)}")
                        import traceback
                        traceback.print_exc()
                        continue
                    
                except ValueError as ve:
                    # Skip exams with invalid date/time format
                    print(f"⚠️  Skipping exam: Invalid date/time format ({scheduled_date} {start_time}) - {str(ve)}")
                    continue
            
            print(f"\n✅ DEBUG SUMMARY: Found {len(available_exams)} available exams for student {student_id}")
            conn.close()
            return available_exams
            
        except Exception as e:
            print(f"❌ Error fetching available exams: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return []


def update_question(question_id: int, question_text: str, option_a: str, option_b: str, option_c: str, option_d: str, correct_option: str, marks: int) -> bool:
    """
    Update an existing question in a paper.
    
    Args:
        question_id: ID of the question to update
        question_text, option_a, option_b, option_c, option_d: Updated content
        correct_option: Correct answer
        marks: Marks for this question
    
    Returns:
        True if successful, False otherwise
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE questions
                SET question_text = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, 
                    correct_option = ?, marks = ?
                WHERE id = ?
            """, (question_text, option_a, option_b, option_c, option_d, correct_option, marks, question_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Question {question_id} updated")
            return True
            
        except Exception as e:
            print(f"❌ Error updating question: {e}")
            return False


def delete_question(question_id: int) -> bool:
    """
    Delete a question from a paper.
    
    Args:
        question_id: ID of the question to delete
    
    Returns:
        True if successful, False otherwise
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Question {question_id} deleted")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting question: {e}")
            return False


def delete_question_paper(paper_id: int) -> bool:
    """
    Delete entire question paper and its questions.
    
    Args:
        paper_id: ID of the question paper
    
    Returns:
        True if successful, False otherwise
    """
    with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Delete all questions first
            cursor.execute("DELETE FROM questions WHERE paper_id = ?", (paper_id,))
            
            # Delete the paper
            cursor.execute("DELETE FROM question_papers WHERE id = ?", (paper_id,))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Question paper {paper_id} and all its questions deleted")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting question paper: {e}")
            return False


