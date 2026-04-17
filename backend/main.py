"""
FastAPI Backend for D-CAPTCHA System
Role-based Online Exam Proctoring with Admin, Faculty, and Student roles
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import cv2
import numpy as np
import mediapipe as mp

from backend.database import (
    init_database, 
    get_all_alerts, 
    clear_alerts,
    get_alert_count,
    get_all_students,
    get_all_faculty,
    get_all_users,
    get_student_alerts,
    get_student_alert_count,
    get_all_exams,
    get_student_exams,
    create_exam,
    update_exam_status,
    store_face_image,
    get_face_image
)
from backend.monitoring import (
    start_monitoring, 
    stop_monitoring,
    is_monitoring_active
)
from backend.auth import (
    register_user,
    login_user
)
from backend.faculty_routes import router as faculty_router
from backend.student_exam_routes import router as student_exam_router

# Initialize FastAPI app
app = FastAPI(
    title="D-CAPTCHA Proctoring API",
    description="Role-based AI Exam Proctoring System - Admin, Faculty, Student",
    version="2.0.0"
)

# CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StatusResponse(BaseModel):
    status: str


class Alert(BaseModel):
    violation: str
    timestamp: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str  # "student" or "faculty"


class LoginRequest(BaseModel):
    email: str
    password: str
    role: str  # "student", "faculty", or "admin"


class LoginResponse(BaseModel):
    success: bool
    role: Optional[str] = None
    user_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None
    token: Optional[str] = None  # Add token field


class StartExamRequest(BaseModel):
    student_id: int


class MonitoringStatus(BaseModel):
    is_active: bool
    alert_count: int


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database when server starts"""
    init_database()
    print("🚀 D-CAPTCHA Backend Server Started (Role-based System)")
    print("   👤 Roles: Admin, Faculty, Student")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup when server shuts down"""
    if is_monitoring_active():
        stop_monitoring()
    print("🛑 D-CAPTCHA Backend Server Stopped")


# ============================================================================
# PUBLIC ENDPOINTS (No authentication required)
# ============================================================================

@app.get("/")
def root():
    """Root endpoint - API info"""
    return {
        "message": "D-CAPTCHA Role-based Proctoring API",
        "version": "2.0.0",
        "roles": ["admin", "faculty", "student"],
        "endpoints": {
            "auth": {
                "register": "POST /register",
                "login": "POST /login"
            },
            "exam": {
                "start": "POST /exam/start",
                "stop": "POST /exam/stop",
                "status": "GET /exam/status"
            },
            "faculty": {
                "students": "GET /faculty/students",
                "alerts": "GET /faculty/alerts/{student_id}"
            },
            "admin": {
                "users": "GET /admin/users",
                "exams": "GET /admin/exams",
                "alerts": "GET /admin/alerts"
            }
        }
    }


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/register", response_model=LoginResponse)
def register(request: RegisterRequest):
    """
    Register a new user (student or faculty).
    Admin registration is NOT allowed (admin is hardcoded).
    """
    result = register_user(
        name=request.name,
        email=request.email,
        password=request.password,
        role=request.role
    )
    
    if not result["success"]:
        return LoginResponse(success=False, message=result["message"])
    
    return LoginResponse(
        success=True,
        role=result["role"],
        user_id=result["user_id"],
        name=request.name,
        email=request.email,
        token=result.get("token"),  # Include token from auth
        message="Registration successful"
    )


@app.post("/register-face/{user_id}")
async def register_face(user_id: int, file: UploadFile = File(...)):
    """
    Register face image for a user during registration.
    Extracts face from uploaded image and stores in database.
    """
    try:
        # Read uploaded image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Initialize MediaPipe face detection
        mp_face_detection = mp.solutions.face_detection
        face_detection = mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.7
        )
        
        # Detect face
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb)
        
        if not results.detections:
            raise HTTPException(status_code=400, detail="No face detected in image")
        
        # Extract face region
        detection = results.detections[0]
        bbox = detection.location_data.relative_bounding_box
        h, w, _ = frame.shape
        x, y = int(bbox.xmin * w), int(bbox.ymin * h)
        bw, bh = int(bbox.width * w), int(bbox.height * h)
        
        face = frame[y:y+bh, x:x+bw]
        
        if face.size == 0:
            raise HTTPException(status_code=400, detail="Failed to extract face")
        
        # Encode face as JPEG
        success, face_encoded = cv2.imencode('.jpg', face)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to encode face image")
        
        face_bytes = face_encoded.tobytes()
        
        # Store in database
        if store_face_image(user_id, face_bytes):
            return {"success": True, "message": "Face registered successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store face image")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing face: {str(e)}")



@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Login user based on role (admin, faculty, or student).
    Admin credentials are hardcoded.
    """
    result = login_user(
        email=request.email,
        password=request.password,
        role=request.role
    )
    
    if not result["success"]:
        return LoginResponse(success=False, message=result["message"])
    
    return LoginResponse(
        success=True,
        role=result["role"],
        user_id=result["user_id"],
        name=result["name"],
        email=result["email"],
        token=result.get("token"),  # Include token from auth
        message="Login successful"
    )


# ============================================================================
# D-CAPTCHA LIVENESS VERIFICATION ENDPOINTS
# ============================================================================

@app.post("/dcaptcha/reset")
def reset_dcaptcha_session():
    """Reset D-CAPTCHA verification session"""
    from backend.dcaptcha_processor import reset_verification_state
    reset_verification_state()
    return {"message": "Session reset"}


@app.post("/dcaptcha/verify-blink")
async def verify_blink(file: UploadFile = File(...)):
    """
    Process frame for blink detection.
    Frontend sends continuous frames, backend processes and returns verification status.
    """
    from backend.dcaptcha_processor import process_blink_frame
    
    try:
        contents = await file.read()
        result = process_blink_frame(contents)
        return result
    except Exception as e:
        return {"verified": False, "message": f"Error: {str(e)}", "blink_count": 0}


@app.post("/dcaptcha/verify-head-movement")
async def verify_head_movement(file: UploadFile = File(...)):
    """
    Process frame for head movement detection (LEFT then RIGHT).
    Frontend sends continuous frames, backend processes and returns verification status.
    """
    from backend.dcaptcha_processor import process_head_movement_frame
    
    try:
        contents = await file.read()
        result = process_head_movement_frame(contents)
        return result
    except Exception as e:
        return {
            "verified": False,
            "message": f"Error: {str(e)}",
            "direction": "LEFT",
            "left_done": False,
            "right_done": False
        }


@app.get("/dcaptcha/state")
def get_dcaptcha_state():
    """Get current D-CAPTCHA verification state"""
    from backend.dcaptcha_processor import get_verification_state
    return get_verification_state()


@app.post("/dcaptcha/verify-speech-audio")
async def verify_speech_audio(
    phrase: str,
    file: UploadFile = File(...)
):
    """
    Verify speech from audio blob uploaded by frontend.
    """
    import speech_recognition as sr
    from difflib import SequenceMatcher
    import io
    from backend.dcaptcha_processor import verification_state
    
    try:
        # Read audio file
        audio_bytes = await file.read()
        
        # Recognize speech
        recognizer = sr.Recognizer()
        
        # Convert bytes to AudioFile
        from io import BytesIO
        import speech_recognition as sr
        
        # Save to temp file because AudioFile needs path or file-like object
        # Note: raw bytes might need conversion to WAV depending on frontend
        # Assuming frontend sends WAV blob
        audio_file = BytesIO(audio_bytes)
        
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            
        print(f"🎤 Recognized: {text}")
        print(f"📝 Expected: {phrase}")
        
        # Compare
        similarity = SequenceMatcher(None, text.lower(), phrase.lower()).ratio()
        passed = similarity >= 0.70
        
        # Update state
        if passed:
            verification_state["speech_verified"] = True
            verification_state["speech_message"] = "Voice verified! ✓"
        else:
            verification_state["speech_verified"] = False
            verification_state["speech_message"] = f"Expected: '{phrase}', Heard: '{text}'"
            
        return {
            "passed": passed,
            "text": text,
            "similarity": similarity,
            "message": verification_state["speech_message"]
        }
        
    except sr.UnknownValueError:
        return {"passed": False, "message": "Could not understand audio", "text": ""}
    except Exception as e:
        print(f"❌ Speech error: {e}")
        return {"passed": False, "message": f"Error: {str(e)}", "text": ""}


# ============================================================================
# EXAM ENDPOINTS (Student)
# ============================================================================

@app.get("/exam/get-verification-phrase")
def get_verification_phrase():
    """
    Get a random phrase for speech verification.
    Called before exam starts.
    """
    from backend.liveness_verification import get_random_phrase
    phrase = get_random_phrase()
    return {"phrase": phrase}


@app.post("/exam/verify-speech")
def verify_speech_endpoint(phrase: str, recognized_text: str):
    """
    Verify speech recognition result.
    Returns similarity score and whether it passed 70% threshold.
    """
    from difflib import SequenceMatcher
    
    similarity = SequenceMatcher(None, recognized_text.lower(), phrase.lower()).ratio()
    passed = similarity >= 0.70
    
    return {
        "passed": passed,
        "similarity": similarity,
        "threshold": 0.70,
        "message": "Verification passed!" if passed else "Please try again - similarity too low"
    }


@app.post("/exam/start")
def start_exam(request: StartExamRequest):
    """
    Start exam monitoring for a student.
    Creates exam record and launches ML monitoring.
    NOTE: Liveness verification should be completed in frontend before calling this.
    """
    # Create exam record
    exam_id = create_exam(request.student_id)
    
    if exam_id == 0:
        raise HTTPException(status_code=500, detail="Failed to create exam")
    
    # Start monitoring with student_id
    success = start_monitoring(student_id=request.student_id)
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Monitoring is already running"
        )
    
    return {
        "status": "Exam started",
        "exam_id": exam_id,
        "student_id": request.student_id
    }


@app.post("/exam/stop")
def stop_exam(student_id: int, status: str = "completed"):
    """
    Stop exam monitoring.
    Updates exam status (completed or terminated).
    
    Args:
        student_id: ID of the student
        status: "completed" or "terminated"
    """
    # Get current exam for student
    exams = get_student_exams(student_id)
    if exams and exams[0]["status"] == "in-progress":
        exam_id = exams[0]["exam_id"]
        update_exam_status(exam_id, status)
    
    # Stop monitoring
    success = stop_monitoring()
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Monitoring is not running"
        )
    
    return {
        "status": f"Exam {status}",
        "student_id": student_id
    }


@app.get("/exam/status")
def get_exam_status(student_id: Optional[int] = None):
    """
    Get current exam monitoring status.
    If student_id provided, returns their alert count and termination status.
    """
    from backend.monitoring import is_exam_terminated, get_termination_reason
    
    status = {
        "is_active": is_monitoring_active(),
        "alert_count": get_alert_count(),
        "terminated": is_exam_terminated(),
        "termination_reason": get_termination_reason()
    }
    
    if student_id:
        status["student_alert_count"] = get_student_alert_count(student_id)
        status["max_violations"] = 5  # VIOLATION_LIMIT
    
    return status


@app.get("/exam/frame")
def get_exam_frame():
    """
    Get the latest monitoring frame.
    Used for streaming video to frontend during exam.
    """
    from backend.monitoring import get_latest_frame
    from fastapi.responses import Response
    
    frame_bytes = get_latest_frame()
    
    if frame_bytes:
        return Response(content=frame_bytes, media_type="image/jpeg")
    else:
        # Return a placeholder or 404
        return Response(status_code=404)


def get_video_stream():
    """
    Generator function for MJPEG video stream.
    Yields frames from the monitoring system.
    """
    from backend.monitoring import get_latest_frame
    import time
    
    while True:
        frame_bytes = get_latest_frame()
        
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            # If no frame available yet, send a small placeholder or wait
            pass
            
        time.sleep(0.05)  # 20 FPS cap to save resources


@app.get("/exam/video_feed")
def video_feed():
    """
    Stream video feed using MJPEG.
    Browser can render this directly in an <img> tag.
    """
    from fastapi.responses import StreamingResponse
    return StreamingResponse(get_video_stream(), media_type="multipart/x-mixed-replace;boundary=frame")




@app.get("/student/alerts/{student_id}")
def get_student_alerts_endpoint(student_id: int):
    """
    Get alerts for a specific student (for testing/debug).
    In production, students should not see their own alerts.
    """
    alerts = get_student_alerts(student_id)
    return {"student_id": student_id, "alerts": alerts}


# ============================================================================
# FACULTY ENDPOINTS
# ============================================================================

@app.get("/faculty/students")
def get_students():
    """
    Get list of all students.
    Used by faculty to view students.
    """
    students = get_all_students()
    return {"students": students}


@app.get("/faculty/alerts/{student_id}")
def get_faculty_student_alerts(student_id: int):
    """
    Get violation alerts for a specific student.
    Used by faculty to review student violations.
    """
    alerts = get_student_alerts(student_id)
    alert_count = len(alerts)
    
    # Get student exam history
    exams = get_student_exams(student_id)
    
    return {
        "student_id": student_id,
        "total_violations": alert_count,
        "alerts": alerts,
        "exams": exams
    }


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.get("/admin/users")
def get_admin_users():
    """
    Get all users (students and faculty).
    Used by admin dashboard.
    """
    users = get_all_users()
    students = get_all_students()
    faculty = get_all_faculty()
    
    return {
        "total_users": len(users),
        "total_students": len(students),
        "total_faculty": len(faculty),
        "users": users
    }


@app.get("/admin/exams")
def get_admin_exams():
    """
    Get all exam records.
    Used by admin to view exam statistics.
    """
    exams = get_all_exams()
    
    # Calculate statistics
    total_exams = len(exams)
    completed = len([e for e in exams if e["status"] == "completed"])
    terminated = len([e for e in exams if e["status"] == "terminated"])
    in_progress = len([e for e in exams if e["status"] == "in-progress"])
    
    return {
        "total_exams": total_exams,
        "completed": completed,
        "terminated": terminated,
        "in_progress": in_progress,
        "exams": exams
    }


@app.get("/admin/alerts")
def get_admin_alerts():
    """
    Get all violation alerts across all students.
    Used by admin to view overall violations.
    """
    all_alerts = get_all_alerts()
    total_count = get_alert_count()
    
    return {
        "total_violations": total_count,
        "alerts": all_alerts
    }


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================
@app.get("/alerts", response_model=List[Alert])
def get_alerts():
    """
    Retrieve all logged violation alerts from the database.
    Returns list of violations with timestamps.
    """
    alerts = get_all_alerts()
    return alerts


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/alerts")
def get_all_alerts_endpoint():
    """
    Get all alerts (for debugging/testing).
    In production, use role-specific endpoints.
    """
    alerts = get_all_alerts()
    return {"alerts": alerts}


@app.delete("/alerts")
def delete_all_alerts():
    """
    Clear all alerts from the database.
    Useful for testing/debugging.
    """
    clear_alerts()
    return {"status": "All alerts cleared"}


# Include the new routers
app.include_router(faculty_router)
app.include_router(student_exam_router)


# Run the server (for development)
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
