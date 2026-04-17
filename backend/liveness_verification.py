"""
Liveness Verification Module for D-CAPTCHA
Performs 3-step verification before exam starts:
1. Blink Detection
2. Head Movement (Left & Right)
3. Speech Recognition (Random phrase)
"""

import cv2
import mediapipe as mp
import math
import random
import speech_recognition as sr
from difflib import SequenceMatcher

# MediaPipe setup
mp_face_mesh = mp.solutions.face_mesh

# Random phrases for speech verification
VERIFICATION_PHRASES = [
    "I am ready for my exam",
    "This is my exam session",
    "I verify my identity",
    "I am the registered student",
    "My exam starts now",
    "I agree to exam rules",
    "This is my online test",
    "I confirm my presence",
    "Ready to begin exam",
    "I am taking this exam",
    "My identity is verified",
    "I accept exam conditions",
    "Starting my examination",
    "I am here for exam",
    "This is my test session"
]

# Verification state
verification_state = {
    "blink_done": False,
    "head_left_done": False,
    "head_right_done": False,
    "speech_done": False,
    "current_step": "blink",  # blink -> head -> speech
    "selected_phrase": None
}


def distance(p1, p2):
    """Calculate Euclidean distance between two landmarks"""
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def verify_blink(frame, face_mesh_instance):
    """
    Verify eye blink using MediaPipe face mesh.
    Returns: (verified, message, frame_with_overlay)
    """
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh_instance.process(rgb)
    
    blink_verified = False
    message = "Please BLINK your eyes"
    
    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]
        
        # Left eye landmarks
        top = face.landmark[159]
        bottom = face.landmark[145]
        
        eye_opening = distance(top, bottom)
        
        # Check for blink (eye closing and opening)
        if eye_opening < 0.01:
            message = "Blink detected! Opening eyes..."
        elif eye_opening > 0.015:
            blink_verified = True
            message = "✓ Blink verified!"
    
    # Draw message on frame
    cv2.putText(frame, message, (30, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    return blink_verified, message, frame


def verify_head_movement(frame, face_mesh_instance, center_x=None):
    """
    Verify head movement (left then right).
    Returns: (left_done, right_done, center_x, message, frame_with_overlay)
    """
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh_instance.process(rgb)
    
    left_done = verification_state["head_left_done"]
    right_done = verification_state["head_right_done"]
    message = "Move head LEFT"
    
    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]
        
        # Nose tip landmark
        nose = face.landmark[1]
        nose_x = int(nose.x * w)
        
        # Initialize center position
        if center_x is None:
            center_x = nose_x
        
        # Detect LEFT movement
        if not left_done and nose_x < center_x - 50:
            left_done = True
            message = "✓ Left done! Now move RIGHT"
        
        # Detect RIGHT movement (after left is done)
        elif left_done and not right_done and nose_x > center_x + 50:
            right_done = True
            message = "✓ Head movement verified!"
        
        # Update message
        if not left_done:
            message = "Turn head LEFT"
        elif left_done and not right_done:
            message = "Now turn head RIGHT"
        
        # Draw nose position
        cv2.circle(frame, (nose_x, int(nose.y * h)), 5, (0, 255, 0), -1)
    
    # Draw message on frame
    cv2.putText(frame, message, (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    return left_done, right_done, center_x, message, frame


def verify_speech(phrase):
    """
    Verify speech recognition - user must read the given phrase.
    Returns: (verified, similarity_score, recognized_text)
    """
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            print(f"🎤 Listening... Please say: '{phrase}'")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
        
        # Recognize speech
        recognized_text = recognizer.recognize_google(audio).lower()
        expected_text = phrase.lower()
        
        # Calculate similarity
        similarity = SequenceMatcher(None, recognized_text, expected_text).ratio()
        
        print(f"📝 You said: '{recognized_text}'")
        print(f"📊 Similarity: {similarity * 100:.1f}%")
        
        verified = similarity >= 0.70  # 70% threshold
        
        return verified, similarity, recognized_text
        
    except sr.WaitTimeoutError:
        print("⏰ Timeout - No speech detected")
        return False, 0.0, ""
    except sr.UnknownValueError:
        print("❌ Could not understand audio")
        return False, 0.0, ""
    except sr.RequestError as e:
        print(f"❌ Speech recognition error: {e}")
        return False, 0.0, ""
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, 0.0, ""


def get_random_phrase():
    """Get a random verification phrase"""
    return random.choice(VERIFICATION_PHRASES)


def run_liveness_verification():
    """
    Run complete liveness verification flow.
    Returns: True if all checks pass, False otherwise
    """
    # Initialize face mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Cannot open camera")
        return False
    
    # Reset verification state
    verification_state["blink_done"] = False
    verification_state["head_left_done"] = False
    verification_state["head_right_done"] = False
    verification_state["speech_done"] = False
    verification_state["current_step"] = "blink"
    verification_state["selected_phrase"] = get_random_phrase()
    
    center_x = None
    blink_counter = 0
    blink_detected_flag = False
    
    print("="*60)
    print("🔐 LIVENESS VERIFICATION STARTED")
    print("="*60)
    print("Step 1: Blink your eyes")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)  # Mirror view
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        
        # Step 1: Blink Detection
        if verification_state["current_step"] == "blink":
            if results.multi_face_landmarks:
                face = results.multi_face_landmarks[0]
                top = face.landmark[159]
                bottom = face.landmark[145]
                eye_opening = distance(top, bottom)
                
                if eye_opening < 0.01 and not blink_detected_flag:
                    blink_detected_flag = True
                
                if eye_opening > 0.015 and blink_detected_flag:
                    blink_counter += 1
                    blink_detected_flag = False
                    
                    if blink_counter >= 1:
                        verification_state["blink_done"] = True
                        verification_state["current_step"] = "head"
                        print("✅ Step 1 Complete: Blink verified")
                        print("Step 2: Turn your head LEFT then RIGHT")
                
                cv2.putText(frame, f"BLINK YOUR EYES", (30, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                if blink_counter > 0:
                    cv2.putText(frame, f"Blinks: {blink_counter}", (30, 100),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Step 2: Head Movement
        elif verification_state["current_step"] == "head":
            if results.multi_face_landmarks:
                face = results.multi_face_landmarks[0]
                nose = face.landmark[1]
                nose_x = int(nose.x * w)
                
                if center_x is None:
                    center_x = nose_x
                
                # LEFT movement
                if not verification_state["head_left_done"] and nose_x < center_x - 60:
                    verification_state["head_left_done"] = True
                    print("  ✓ Left movement detected")
                
                # RIGHT movement
                if verification_state["head_left_done"] and not verification_state["head_right_done"]:
                    if nose_x > center_x + 60:
                        verification_state["head_right_done"] = True
                        print("  ✓ Right movement detected")
                        verification_state["current_step"] = "speech"
                        print("✅ Step 2 Complete: Head movement verified")
                        print(f"Step 3: Say the phrase: '{verification_state['selected_phrase']}'")
                
                cv2.circle(frame, (nose_x, int(nose.y * h)), 5, (0, 255, 0), -1)
                
                if not verification_state["head_left_done"]:
                    cv2.putText(frame, "Turn HEAD LEFT", (30, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                elif not verification_state["head_right_done"]:
                    cv2.putText(frame, "Now turn HEAD RIGHT", (30, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Step 3: Speech Recognition
        elif verification_state["current_step"] == "speech":
            cv2.putText(frame, "READ THE PHRASE:", (30, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, f'"{verification_state["selected_phrase"]}"', (30, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, "Press SPACE to record", (30, 150),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Check for spacebar press
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                cv2.putText(frame, "RECORDING...", (30, 200),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow("Liveness Verification", frame)
                cv2.waitKey(100)
                
                # Perform speech recognition
                verified, similarity, recognized = verify_speech(verification_state["selected_phrase"])
                
                if verified:
                    verification_state["speech_done"] = True
                    print("✅ Step 3 Complete: Speech verified")
                    print("="*60)
                    print("🎉 ALL VERIFICATION STEPS PASSED!")
                    print("="*60)
                    
                    # Show success message
                    success_frame = frame.copy()
                    cv2.putText(success_frame, "VERIFICATION COMPLETE!", (50, h//2),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                    cv2.imshow("Liveness Verification", success_frame)
                    cv2.waitKey(2000)
                    
                    cap.release()
                    cv2.destroyAllWindows()
                    face_mesh.close()
                    return True
                else:
                    print(f"❌ Speech verification failed ({similarity*100:.1f}% match)")
                    print("Please try again...")
            
            cv2.imshow("Liveness Verification", frame)
            continue
        
        # Display frame
        cv2.imshow("Liveness Verification", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()
    return False


if __name__ == "__main__":
    result = run_liveness_verification()
    if result:
        print("✅ Liveness verification passed!")
    else:
        print("❌ Liveness verification failed!")
