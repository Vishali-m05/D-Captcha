"""
Faculty routes for D-CAPTCHA system
Handles question paper creation, management, and exam scheduling
"""

import sys
import os
import base64
import json
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional

# ============================================================================
# FIX PATH IMPORTS
# ============================================================================

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import database as db

router = APIRouter(prefix="/faculty", tags=["faculty"])


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

class CreateQuestionPaperRequest(BaseModel):
    paper_name: str
    subject: str
    total_marks: int
    duration_minutes: int


class AddQuestionRequest(BaseModel):
    paper_id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str  # 'A', 'B', 'C', or 'D'
    marks: int


class UpdateQuestionRequest(BaseModel):
    question_id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    marks: int


class AssignExamRequest(BaseModel):
    paper_id: int
    class_id: int  # Can be extended for multiple classes
    scheduled_date: str  # Format: "YYYY-MM-DD"
    start_time: str  # Format: "HH:MM"


# ============================================================================
# QUESTION PAPER ENDPOINTS
# ============================================================================

@router.post("/create-question-paper")
async def create_question_paper(request: CreateQuestionPaperRequest, user_data: dict = Depends(verify_token_header)):
    """
    Faculty creates a new question paper.
    Token must contain faculty_id.
    """
    try:
        faculty_id = user_data.get("user_id")
        
        paper_id = db.create_question_paper(
            faculty_id=faculty_id,
            paper_name=request.paper_name,
            subject=request.subject,
            total_marks=request.total_marks,
            duration_minutes=request.duration_minutes
        )
        
        if paper_id == 0:
            raise HTTPException(status_code=400, detail="Failed to create question paper")
        
        return {
            "success": True,
            "message": f"Question paper '{request.paper_name}' created successfully",
            "paper_id": paper_id,
            "duration_minutes": request.duration_minutes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-question")
async def add_question(request: AddQuestionRequest, user_data: dict = Depends(verify_token_header)):
    """
    Faculty adds a multiple choice question to a paper.
    """
    try:
        question_id = db.add_question(
            paper_id=request.paper_id,
            question_text=request.question_text,
            option_a=request.option_a,
            option_b=request.option_b,
            option_c=request.option_c,
            option_d=request.option_d,
            correct_option=request.correct_option,
            marks=request.marks
        )
        
        if question_id == 0:
            raise HTTPException(status_code=400, detail="Failed to add question")
        
        return {
            "success": True,
            "message": "Question added successfully",
            "question_id": question_id,
            "marks": request.marks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/question-papers")
async def get_faculty_papers(user_data: dict = Depends(verify_token_header)):
    """
    Get all question papers created by the faculty.
    """
    try:
        faculty_id = user_data.get("user_id")
        papers = db.get_faculty_question_papers(faculty_id)
        
        return {
            "success": True,
            "total_papers": len(papers),
            "papers": papers
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/question-paper/{paper_id}")
async def get_question_paper(paper_id: int, user_data: dict = Depends(verify_token_header)):
    """
    Get complete question paper with all questions.
    Excludes correct answers for student preview.
    """
    try:
        paper = db.get_question_paper(paper_id)
        
        if not paper:
            raise HTTPException(status_code=404, detail="Question paper not found")
        
        return {
            "success": True,
            "paper": paper
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update-question")
async def update_question(request: UpdateQuestionRequest, user_data: dict = Depends(verify_token_header)):
    """
    Faculty updates an existing question.
    """
    try:
        success = db.update_question(
            question_id=request.question_id,
            question_text=request.question_text,
            option_a=request.option_a,
            option_b=request.option_b,
            option_c=request.option_c,
            option_d=request.option_d,
            correct_option=request.correct_option,
            marks=request.marks
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update question")
        
        return {
            "success": True,
            "message": "Question updated successfully",
            "question_id": request.question_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/question/{question_id}")
async def delete_question(question_id: int, user_data: dict = Depends(verify_token_header)):
    """
    Faculty deletes a question from a paper.
    """
    try:
        success = db.delete_question(question_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete question")
        
        return {
            "success": True,
            "message": "Question deleted successfully",
            "question_id": question_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/question-paper/{paper_id}")
async def delete_question_paper(paper_id: int, user_data: dict = Depends(verify_token_header)):
    """
    Faculty deletes entire question paper and all questions.
    """
    try:
        success = db.delete_question_paper(paper_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete question paper")
        
        return {
            "success": True,
            "message": "Question paper deleted successfully",
            "paper_id": paper_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EXAM SCHEDULING ENDPOINTS
# ============================================================================

@router.post("/assign-exam")
async def assign_exam(request: AssignExamRequest, user_data: dict = Depends(verify_token_header)):
    """
    Faculty schedules/assigns a question paper for a specific date and time.
    """
    try:
        assignment_id = db.assign_question_paper(
            paper_id=request.paper_id,
            class_id=request.class_id,
            scheduled_date=request.scheduled_date,
            start_time=request.start_time
        )
        
        if assignment_id == 0:
            raise HTTPException(status_code=400, detail="Failed to assign exam")
        
        return {
            "success": True,
            "message": f"Exam scheduled for {request.scheduled_date} at {request.start_time}",
            "assignment_id": assignment_id,
            "paper_id": request.paper_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
