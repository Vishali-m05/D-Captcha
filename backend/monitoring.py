"""
Monitoring module for D-CAPTCHA system
Controls the ML-based exam proctoring monitoring in a background thread
"""

import cv2
import threading
import time
import os
import numpy as np
import mediapipe as mp
from datetime import datetime
from ultralytics import YOLO
from backend.database import log_alert, get_student_alert_count, get_face_image

# Create violations folder if it doesn't exist
VIOLATIONS_FOLDER = "backend/violations"
os.makedirs(VIOLATIONS_FOLDER, exist_ok=True)

# Global state variables
monitoring_active = False
monitoring_thread = None
camera_capture = None
current_student_id = None  # Track which student is being monitored
model = None  # YOLO model - loaded when monitoring starts
registered_face = None  # Registered face image
face_detection = None  # MediaPipe face detection
exam_terminated = False  # Track if exam was auto-terminated
termination_reason = None  # Reason for termination
latest_frame = None  # Store latest frame for streaming

# Counters for consecutive detections
face_mismatch_counter = 0  # Counter for consecutive face mismatches
multiple_persons_counter = 0  # Counter for consecutive multiple persons detection
phone_detected_counter = 0  # Counter for consecutive phone detection

# Detection limits
FACE_MISMATCH_LIMIT = 10  # Terminate if face mismatches 10 times consecutively
MULTIPLE_PERSONS_LIMIT = 5  # Log violation if multiple persons detected 5 times consecutively
PHONE_DETECTED_LIMIT = 5  # Log violation if phone detected 5 times consecutively

# Violation limit for auto-termination
VIOLATION_LIMIT = 5  # Auto-terminate exam after 5 violations


def load_yolo_model():
    """
    Load YOLO model - simple loading just like yolo_proctoring.py
    """
    global model
    
    if model is None:
        try:
            # Simple YOLO loading - same as your original yolo_proctoring.py
            model = YOLO("yolov8n.pt")
            print("✅ YOLO model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading YOLO model: {e}")
            model = None
    
    return model


def init_face_detection():
    """
    Initialize MediaPipe face detection
    """
    global face_detection
    
    if face_detection is None:
        mp_face_detection = mp.solutions.face_detection
        face_detection = mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.7
        )
        print("✅ Face detection initialized")
    
    return face_detection


def compare_faces(face1, face2):
    """
    Compare two face images using histogram comparison.
    Returns similarity score (0 to 1, higher is more similar).
    """
    try:
        # Resize both faces to same size
        face1 = cv2.resize(face1, (100, 100))
        face2 = cv2.resize(face2, (100, 100))
        
        # Convert to grayscale
        face1_gray = cv2.cvtColor(face1, cv2.COLOR_BGR2GRAY)
        face2_gray = cv2.cvtColor(face2, cv2.COLOR_BGR2GRAY)
        
        # Calculate histograms
        hist1 = cv2.calcHist([face1_gray], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([face2_gray], [0], None, [256], [0, 256])
        
        # Normalize histograms
        cv2.normalize(hist1, hist1)
        cv2.normalize(hist2, hist2)
        
        # Compare histograms
        score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return score
        
    except Exception as e:
        print(f"❌ Error comparing faces: {e}")
        return 0.0


def load_registered_face(student_id: int):
    """
    Load registered face image from database
    """
    global registered_face
    
    try:
        face_bytes = get_face_image(student_id)
        if face_bytes:
            nparr = np.frombuffer(face_bytes, np.uint8)
            registered_face = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            print(f"✅ Registered face loaded for student ID: {student_id}")
            return True
        else:
            print(f"⚠️  No registered face found for student ID: {student_id}")
            return False
    except Exception as e:
        print(f"❌ Error loading registered face: {e}")
        return False


def start_monitoring(student_id: int = None):
    """
    Start the ML monitoring in a background thread.
    Called by POST /exam/start endpoint.
    
    Args:
        student_id: ID of the student being monitored
    """
    global monitoring_active, monitoring_thread, current_student_id
    global face_mismatch_counter, multiple_persons_counter, phone_detected_counter
    global exam_terminated, termination_reason
    
    if monitoring_active:
        print("⚠️  Monitoring is already running")
        return False
    
    current_student_id = student_id
    
    # Reset all counters
    face_mismatch_counter = 0
    multiple_persons_counter = 0
    phone_detected_counter = 0
    
    # Reset termination status
    exam_terminated = False
    termination_reason = None
    
    # Load registered face for this student
    if student_id:
        load_registered_face(student_id)
    
    monitoring_active = True
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    
    print(f"✅ Monitoring started for Student ID: {student_id}")
    return True


def stop_monitoring():
    """
    Stop the ML monitoring and release camera resources.
    Called by POST /exam/stop endpoint.
    """
    global monitoring_active, camera_capture, current_student_id
    global face_mismatch_counter, multiple_persons_counter, phone_detected_counter
    
    if not monitoring_active:
        print("⚠️  Monitoring is not running")
        return False
    
    monitoring_active = False
    
    # Wait for thread to finish (with timeout)
    if monitoring_thread:
        monitoring_thread.join(timeout=2.0)
    
    # Release camera if it's still open
    if camera_capture:
        camera_capture.release()
        camera_capture = None
    
    cv2.destroyAllWindows()
    
    # Reset all counters and student ID
    face_mismatch_counter = 0
    multiple_persons_counter = 0
    phone_detected_counter = 0
    current_student_id = None
    
    # Create a "Monitoring Stopped" placeholder frame
    height, width = 480, 640
    blank_image = np.zeros((height, width, 3), np.uint8)
    cv2.putText(blank_image, "Monitoring Stopped", (180, 240), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Update latest frame
    global latest_frame
    success, buffer = cv2.imencode('.jpg', blank_image)
    if success:
        latest_frame = buffer.tobytes()
    
    print("✅ Monitoring stopped")
    return True


def monitoring_loop():
    """
    Main monitoring loop that runs in background thread.
    Performs YOLO-based detection for:
    - Multiple persons (counter-based: logs at 5 consecutive detections)
    - Mobile phone detection (counter-based: logs at 5 consecutive detections)
    - Face verification (counter-based: terminates at 10 consecutive mismatches)
    
    Counter resets to 0 when violation is not detected.
    """
    global camera_capture, monitoring_active, current_student_id, model
    global registered_face, face_detection
    global face_mismatch_counter, multiple_persons_counter, phone_detected_counter
    global exam_terminated, termination_reason
    
    try:
        # Load YOLO model if not already loaded
        model = load_yolo_model()
        
        if model is None:
            print("❌ Cannot start monitoring: YOLO model not loaded")
            monitoring_active = False
            return
        
        # Initialize face detection
        face_detection = init_face_detection()
        
        # Initialize camera with robust search
        camera_capture = None
        
        # DIAGNOSTIC: Check OS
        import platform
        import os
        system_os = platform.system()
        print(f"\n📊 DIAGNOSTIC INFO:")
        print(f"   OS: {system_os}")
        print(f"   OpenCV Version: {cv2.__version__}")
        
        if system_os == 'Linux':
            print("⚠️  DETECTED: Linux/WSL environment detected.")
            print("   ℹ️  On WSL, Windows cameras are NOT automatically accessible.")
            print("   ℹ️  FIX: Use 'usbipd' to attach your camera from Windows:")
            print("        1. Run in PowerShell (Admin): usbipd list")
            print("        2. Find your camera BUS-ID")
            print("        3. Run: usbipd attach --wsl --busid <BUS-ID>")
            print("   ℹ️  For Linux: Use 'v4l2-ctl --list-devices' to find cameras")
            print("   ℹ️  Ensure: ls /dev/video* shows your camera device")

        # Check for any video devices available
        cameras_found = []
        for idx in [0, 1, 2, 3, 4, 5]:
            try:
                test_cap = cv2.VideoCapture(idx)
                if test_cap.isOpened():
                    cameras_found.append(idx)
                test_cap.release()
            except:
                pass
        
        if cameras_found:
            print(f"   📹 Cameras detected at indices: {cameras_found}")
        else:
            print(f"   ❌ NO cameras detected at indices 0-5")

        # Try specific backends to force Windows compatibility
        # cv2.CAP_DSHOW (DirectShow) and cv2.CAP_MSMF (Media Foundation)
        for index in [0, 1, 2, -1]:
            print(f"\n📷 Trying camera index {index}...")
            
            # Try DirectShow first (standard Windows)
            print(f"   → Attempting DirectShow backend...")
            try:
                temp_cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                
                if temp_cap.isOpened():
                    ret, frame = temp_cap.read()
                    if ret and frame is not None:
                        print(f"   ✅ SUCCESS: Camera initialized at index {index} (DirectShow)")
                        camera_capture = temp_cap
                        break
                    else:
                        print(f"   ❌ Camera opened but cannot read frames (DirectShow)")
                        temp_cap.release()
                else:
                    print(f"   ❌ Cannot open camera (DirectShow)")
            except Exception as e:
                print(f"   ❌ DirectShow error: {e}")
            
            if camera_capture:
                break
            
            # Try Media Foundation (newer Windows)
            print(f"   → Attempting Media Foundation backend...")
            try:
                temp_cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
                if temp_cap.isOpened():
                    ret, frame = temp_cap.read()
                    if ret and frame is not None:
                        print(f"   ✅ SUCCESS: Camera initialized at index {index} (Media Foundation)")
                        camera_capture = temp_cap
                        break
                    else:
                        print(f"   ❌ Camera opened but cannot read frames (Media Foundation)")
                        temp_cap.release()
                else:
                    print(f"   ❌ Cannot open camera (Media Foundation)")
            except Exception as e:
                print(f"   ❌ Media Foundation error: {e}")

            if camera_capture:
                break

            # If DirectShow/MSMF fail, try default (auto-detect)
            print(f"   → Attempting Auto-backend (OpenCV default)...")
            try:
                temp_cap = cv2.VideoCapture(index)
                if temp_cap.isOpened():
                    ret, frame = temp_cap.read()
                    if ret and frame is not None:
                        print(f"   ✅ SUCCESS: Camera initialized at index {index} (Auto)")
                        camera_capture = temp_cap
                        break
                    else:
                        print(f"   ❌ Camera opened but cannot read frames (Auto)")
                        temp_cap.release()
                else:
                    print(f"   ❌ Cannot open camera (Auto)")
            except Exception as e:
                print(f"   ❌ Auto-backend error: {e}")

        if camera_capture is None:
            print("\n" + "="*70)
            print("❌ CAMERA INITIALIZATION FAILED")
            print("="*70)
            print("No camera device was accessible at indices 0, 1, 2, -1")
            print("\n💡 TROUBLESHOOTING STEPS:")
            print("   1. On WSL: Use 'usbipd attach --wsl --busid <ID>' to attach camera")
            print("   2. Check if camera is plugged in")
            print("   3. Check Device Manager (Windows) or 'v4l2-ctl' (Linux)")
            print("   4. Try closing other apps using the camera (Teams, Zoom, etc.)")
            print("   5. Restart the system and try again")
            print("="*70 + "\n")
            monitoring_active = False
            return
        
        print("📹 Camera initialized")
        
        # Main monitoring loop
        while monitoring_active:
            ret, frame = camera_capture.read()
            
            if not ret:
                print("❌ Failed to read frame from camera")
                time.sleep(0.1)
                continue
            
            # Update latest frame for streaming
            global latest_frame
            with threading.Lock():
                 # Encode to JPEG for streaming
                success, buffer = cv2.imencode('.jpg', frame)
                if success:
                    latest_frame = buffer.tobytes()
            
            # Run YOLO detection - same parameters as yolo_proctoring.py
            results = model(frame, conf=0.4, verbose=False)[0]
            
            person_count = 0
            phone_detected = False
            
            # Analyze detections
            for box in results.boxes:
                cls_id = int(box.cls)
                
                if cls_id == 0:  # person class
                    person_count += 1
                
                if cls_id == 67:  # cell phone class
                    phone_detected = True
            
            # === FACE VERIFICATION ===
            if registered_face is not None and face_detection is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_results = face_detection.process(rgb)
                
                if face_results.detections:
                    # Extract face from current frame
                    bbox = face_results.detections[0].location_data.relative_bounding_box
                    h, w, _ = frame.shape
                    x, y = int(bbox.xmin * w), int(bbox.ymin * h)
                    bw, bh = int(bbox.width * w), int(bbox.height * h)
                    
                    live_face = frame[y:y+bh, x:x+bw]
                    
                    if live_face.size > 0:
                        # Compare faces
                        match_score = compare_faces(registered_face, live_face)
                        
                        if match_score > 0.6:
                            # Face matched - reset counter
                            face_mismatch_counter = 0
                        else:
                            # Face mismatch - increment counter
                            face_mismatch_counter += 1
                            print(f"⚠️  Face mismatch detected! Counter: {face_mismatch_counter}/{FACE_MISMATCH_LIMIT} (score: {match_score:.2f})")
                            
                            # Check if consecutive mismatches exceeded limit
                            if face_mismatch_counter >= FACE_MISMATCH_LIMIT:
                                # Save violation image
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                image_filename = f"student_{current_student_id}_face_mismatch_{timestamp}.jpg"
                                image_path = os.path.join(VIOLATIONS_FOLDER, image_filename)
                                cv2.imwrite(image_path, frame)
                                print(f"📸 Saved face mismatch image: {image_path}")
                                
                                log_alert("Face Verification Failed - Different Person", student_id=current_student_id)
                                print(f"🚫 EXAM AUTO-TERMINATED: Face mismatch limit exceeded ({face_mismatch_counter}/{FACE_MISMATCH_LIMIT})")
                                
                                # Set termination flags
                                exam_terminated = True
                                termination_reason = "Face verification failed - Different person detected"
                                
                                monitoring_active = False
                                break
            
            # === MULTIPLE PERSONS DETECTION with COUNTER ===
            if person_count > 1:
                # Multiple persons detected - increment counter
                multiple_persons_counter += 1
                print(f"⚠️  Multiple persons detected! Counter: {multiple_persons_counter}/{MULTIPLE_PERSONS_LIMIT}")
                
                # Check if consecutive detections exceeded limit
                if multiple_persons_counter >= MULTIPLE_PERSONS_LIMIT:
                    # Save violation image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_filename = f"student_{current_student_id}_multiple_persons_{timestamp}.jpg"
                    image_path = os.path.join(VIOLATIONS_FOLDER, image_filename)
                    cv2.imwrite(image_path, frame)
                    print(f"📸 Saved violation image: {image_path}")
                    
                    log_alert("Multiple Persons Detected", student_id=current_student_id)
                    print(f"🚨 VIOLATION LOGGED: Multiple persons detected {multiple_persons_counter} times consecutively")
                    
                    # Reset counter after logging
                    multiple_persons_counter = 0
            else:
                # Only one person or no person - reset counter
                if multiple_persons_counter > 0:
                    print(f"✅ Multiple persons cleared - counter reset from {multiple_persons_counter} to 0")
                multiple_persons_counter = 0
            
            # === PHONE DETECTION with COUNTER ===
            if phone_detected:
                # Phone detected - increment counter
                phone_detected_counter += 1
                print(f"⚠️  Phone detected! Counter: {phone_detected_counter}/{PHONE_DETECTED_LIMIT}")
                
                # Check if consecutive detections exceeded limit
                if phone_detected_counter >= PHONE_DETECTED_LIMIT:
                    # Save violation image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_filename = f"student_{current_student_id}_phone_detected_{timestamp}.jpg"
                    image_path = os.path.join(VIOLATIONS_FOLDER, image_filename)
                    cv2.imwrite(image_path, frame)
                    print(f"📸 Saved violation image: {image_path}")
                    
                    log_alert("Mobile Phone Detected", student_id=current_student_id)
                    print(f"🚨 VIOLATION LOGGED: Phone detected {phone_detected_counter} times consecutively")
                    
                    # Reset counter after logging
                    phone_detected_counter = 0
            else:
                # No phone detected - reset counter
                if phone_detected_counter > 0:
                    print(f"✅ Phone detection cleared - counter reset from {phone_detected_counter} to 0")
                phone_detected_counter = 0
            
            # Check if violations exceed limit - auto-terminate exam
            if current_student_id:
                violation_count = get_student_alert_count(current_student_id)
                if violation_count >= VIOLATION_LIMIT:
                    print(f"🚫 EXAM AUTO-TERMINATED: Student {current_student_id} exceeded violation limit ({violation_count}/{VIOLATION_LIMIT})")
                    
                    # Set termination flags
                    exam_terminated = True
                    termination_reason = "Excessive violations detected"
                    
                    monitoring_active = False  # Stop monitoring
                    break
            
            # Small delay to reduce CPU usage
            time.sleep(0.1)
        
    except Exception as e:
        print(f"❌ Error in monitoring loop: {e}")
    
    finally:
        # Cleanup
        if camera_capture:
            camera_capture.release()
            camera_capture = None
        cv2.destroyAllWindows()
        print("📹 Camera released")


def is_monitoring_active() -> bool:
    """
    Check if monitoring is currently active.
    
    Returns:
        True if monitoring is running, False otherwise
    """
    return monitoring_active


def is_exam_terminated() -> bool:
    """
    Check if exam was auto-terminated due to violations.
    
    Returns:
        True if exam was terminated, False otherwise
    """
    return exam_terminated


def get_termination_reason() -> str:
    """
    Get reason for exam termination.
    
    Returns:
        Termination reason string or None
    """
    return termination_reason


def reset_termination_status():
    """
    Reset exam termination status for new exam.
    Called when starting a new exam.
    """
    global exam_terminated, termination_reason
    exam_terminated = False
    termination_reason = None


def get_latest_frame():
    """
    Get the latest camera frame as JPEG bytes.
    Used for streaming video to frontend.
    """
    global latest_frame
    return latest_frame

