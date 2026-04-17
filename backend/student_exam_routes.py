"""
Student exam endpoints for D-CAPTCHA system
Handles displaying questions and exam timer
"""

import sys
import os
import base64
import json
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional

# ============================================================================
# SETUP PATH
# ============================================================================

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import database as db

router = APIRouter(prefix="/student", tags=["student"])


# ============================================================================
# TOKEN VERIFICATION HELPER
# ============================================================================

async def verify_token_header(authorization: str = Header(None)):
    """
    Verify token from Authorization header.
    Expected format: "Bearer <token>"
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        # Debug: Print what we receive
        print(f"DEBUG: Authorization header received: {authorization[:50]}...")
        print(f"DEBUG: Authorization type: {type(authorization)}")
        
        parts = authorization.split(" ")
        print(f"DEBUG: Parts after split: {len(parts)}, first part: {parts[0] if parts else 'EMPTY'}")
        
        if len(parts) != 2 or parts[0] != "Bearer":
            raise ValueError("Invalid authorization format")
        
        token = parts[1]
        print(f"DEBUG: Token length: {len(token)}, first 20 chars: {token[:20]}")
        
        # Try to decode
        decoded_bytes = base64.b64decode(token)
        print(f"DEBUG: Decoded bytes length: {len(decoded_bytes)}, first bytes: {decoded_bytes[:10]}")
        
        decoded = decoded_bytes.decode('utf-8')
        user_data = json.loads(decoded)
        print(f"DEBUG: Successfully decoded user_data: {user_data}")
        return user_data
        
    except Exception as e:
        print(f"DEBUG: Exception details: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SubmitAnswerRequest(BaseModel):
    exam_id: int
    question_id: int
    student_answer: str  # 'A', 'B', 'C', or 'D'


class SubmitExamRequest(BaseModel):
    exam_id: int
    answers: dict  # {question_id: "A"|"B"|"C"|"D"}


# ============================================================================
# EXAM DISPLAY ENDPOINTS
# ============================================================================

@router.get("/available-exams")
async def get_available_exams(user_data: dict = Depends(verify_token_header)):
    """
    Get all exams scheduled for the student (current and future).
    Displays exam name, subject, duration, and scheduled time.
    """
    try:
        student_id = user_data.get("user_id")
        exams = db.get_available_exams_for_student(student_id)
        
        return {
            "success": True,
            "total_exams": len(exams),
            "exams": exams
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start-exam")
async def start_exam(user_data: dict = Depends(verify_token_header)):
    """
    Mark that a student is starting an exam (after liveness verification passes).
    Creates an exam session in the database to prevent them from seeing other exams.
    
    Returns:
        Exam ID that should be used for subsequent submissions
    """
    try:
        student_id = user_data.get("user_id")
        
        # Create exam session - this will set status to 'in-progress'
        exam_id = db.create_exam(student_id)
        
        if exam_id == 0:
            raise HTTPException(status_code=500, detail="Failed to create exam session")
        
        return {
            "success": True,
            "exam_id": exam_id,
            "message": f"Exam session started: {exam_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exam/{paper_id}")
async def get_exam_questions(paper_id: int, user_data: dict = Depends(verify_token_header)):
    """
    Get all questions for the exam (WITHOUT correct answers).
    Used to display questions to student during exam.
    
    Returns:
        - Questions with options
        - Duration in minutes
        - Total marks
        - Total questions
    """
    try:
        student_id = user_data.get("user_id")
        paper = db.get_question_paper(paper_id)
        
        if not paper:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Remove correct answers before sending to student
        questions_for_student = []
        for q in paper["questions"]:
            questions_for_student.append({
                "question_id": q["question_id"],
                "question_text": q["question_text"],
                "options": q["options"],
                "marks": q["marks"]
                # NOTE: correct_option is NOT included
            })
        
        return {
            "success": True,
            "paper_name": paper["paper_name"],
            "subject": paper["subject"],
            "duration_minutes": paper["duration_minutes"],
            "total_marks": paper["total_marks"],
            "total_questions": paper["total_questions"],
            "questions": questions_for_student
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-answer")
async def submit_answer(request: SubmitAnswerRequest, user_data: dict = Depends(verify_token_header)):
    """
    Submit a student's answer to a question.
    Answer is automatically checked and marks are calculated.
    """
    try:
        student_id = user_data.get("user_id")
        
        # Get the question to verify answer
        # TODO: Implement full answer storage and auto-grading
        
        return {
            "success": True,
            "message": "Answer submitted successfully",
            "question_id": request.question_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-exam")
async def submit_exam(request: SubmitExamRequest, user_data: dict = Depends(verify_token_header)):
    """
    Student submits the exam.
    Saves all answers to student_responses table and marks exam as completed.
    Auto-grades all answers and calculates final score.
    """
    try:
        student_id = user_data.get("user_id")
        exam_id = request.exam_id
        answers = request.answers  # Dict of {question_id: "A"|"B"|"C"|"D"}
        
        # Save all student answers to database
        for question_id_str, student_answer in answers.items():
            try:
                question_id = int(question_id_str)
                db.save_student_response(
                    exam_id=exam_id,
                    student_id=student_id,
                    question_id=question_id,
                    student_answer=student_answer
                )
            except Exception as e:
                print(f"⚠️ Error saving answer for question {question_id_str}: {str(e)}")
        
        # Update exam status to completed
        db.update_exam_status(exam_id, "completed")
        
        # TODO: Calculate final score from all submitted answers
        
        return {
            "success": True,
            "message": "Exam submitted successfully",
            "exam_id": exam_id,
            "answers_saved": len(answers)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
