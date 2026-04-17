"""
D-CAPTCHA Liveness Verification Module
Processes continuous video frames for blink, head movement detection
"""

import cv2
import numpy as np
import mediapipe as mp
import math
from typing import Dict, Optional

# Initialize MediaPipe Face Mesh once
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Global state for verification session
verification_state = {
    "blink_count": 0,
    "blink_flag": False,
    "blink_verified": False,
    "head_center_x": None,
    "head_direction": "LEFT",  # LEFT -> RIGHT -> DONE
    "head_left_done": False,
    "head_right_done": False,
    "speech_verified": False,
    "speech_message": None
}


def distance(p1, p2):
    """Calculate Euclidean distance between two landmarks"""
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def reset_verification_state():
    """Reset state for new verification session"""
    global verification_state
    verification_state = {
        "blink_count": 0,
        "blink_flag": False,
        "blink_verified": False,
        "head_center_x": None,
        "head_direction": "LEFT",
        "head_left_done": False,
        "head_right_done": False,
        "speech_verified": False,
        "speech_message": None
    }


def process_blink_frame(frame_bytes: bytes) -> Dict:
    """
    Process a single frame for blink detection.
    Returns: {"verified": bool, "message": str, "blink_count": int}
    """
    global verification_state
    
    try:
        # Decode frame
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {"verified": False, "message": "Invalid frame", "blink_count": 0}
        
        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        
        if results.multi_face_landmarks:
            face = results.multi_face_landmarks[0]
            
            # Left eye landmarks
            top = face.landmark[159]
            bottom = face.landmark[145]
            
            eye_opening = distance(top, bottom)
            
            # Detect blink (close then open)
            if eye_opening < 0.01 and not verification_state["blink_flag"]:
                verification_state["blink_flag"] = True
            
            if eye_opening > 0.015 and verification_state["blink_flag"]:
                verification_state["blink_count"] += 1
                verification_state["blink_flag"] = False
                
                if verification_state["blink_count"] >= 1:
                    verification_state["blink_verified"] = True
                    return {
                        "verified": True,
                        "message": "Blink detected! ✓",
                        "blink_count": verification_state["blink_count"]
                    }
            
            return {
                "verified": False,
                "message": "Please blink your eyes",
                "blink_count": verification_state["blink_count"]
            }
        else:
            return {
                "verified": False,
                "message": "No face detected",
                "blink_count": verification_state["blink_count"]
            }
    
    except Exception as e:
        return {"verified": False, "message": f"Error: {str(e)}", "blink_count": 0}


def process_head_movement_frame(frame_bytes: bytes) -> Dict:
    """
    Process a single frame for head movement detection (LEFT then RIGHT).
    Returns: {"verified": bool, "message": str, "direction": str, "left_done": bool, "right_done": bool}
    """
    global verification_state
    
    try:
        # Decode frame
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {
                "verified": False,
                "message": "Invalid frame",
                "direction": verification_state["head_direction"],
                "left_done": False,
                "right_done": False
            }
        
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        
        if results.multi_face_landmarks:
            face = results.multi_face_landmarks[0]
            
            # Nose tip landmark
            nose = face.landmark[1]
            nose_x = int(nose.x * w)
            
            # Initialize center position
            if verification_state["head_center_x"] is None:
                verification_state["head_center_x"] = nose_x
            
            center_x = verification_state["head_center_x"]
            
            # Detect LEFT movement (threshold: 40 pixels)
            if verification_state["head_direction"] == "LEFT":
                if nose_x < center_x - 40:
                    verification_state["head_left_done"] = True
                    verification_state["head_direction"] = "RIGHT"
                    return {
                        "verified": False,
                        "message": "Left detected! Now turn RIGHT",
                        "direction": "RIGHT",
                        "left_done": True,
                        "right_done": False
                    }
                else:
                    return {
                        "verified": False,
                        "message": f"Turn your head LEFT (current: {nose_x - center_x}px)",
                        "direction": "LEFT",
                        "left_done": False,
                        "right_done": False
                    }
            
            # Detect RIGHT movement (threshold: 40 pixels)
            elif verification_state["head_direction"] == "RIGHT":
                if nose_x > center_x + 40:
                    verification_state["head_right_done"] = True
                    verification_state["head_direction"] = "DONE"
                    return {
                        "verified": True,
                        "message": "Head movement verified! ✓",
                        "direction": "DONE",
                        "left_done": True,
                        "right_done": True
                    }
                else:
                    return {
                        "verified": False,
                        "message": "Turn your head RIGHT",
                        "direction": "RIGHT",
                        "left_done": True,
                        "right_done": False
                    }
            
            # Already done
            else:
                return {
                    "verified": True,
                    "message": "Head movement verified! ✓",
                    "direction": "DONE",
                    "left_done": True,
                    "right_done": True
                }
        
        else:
            return {
                "verified": False,
                "message": "No face detected",
                "direction": verification_state["head_direction"],
                "left_done": verification_state["head_left_done"],
                "right_done": verification_state["head_right_done"]
            }
    
    except Exception as e:
        return {
            "verified": False,
            "message": f"Error: {str(e)}",
            "direction": verification_state["head_direction"],
            "left_done": False,
            "right_done": False
        }


def get_verification_state() -> Dict:
    """Get current verification state"""
    return {
        "blink_count": verification_state["blink_count"],
        "blink_verified": verification_state["blink_verified"],
        "head_left_done": verification_state["head_left_done"],
        "head_right_done": verification_state["head_right_done"],
        "head_direction": verification_state["head_direction"],
        "speech_verified": verification_state["speech_verified"],
        "speech_message": verification_state["speech_message"]
    }
