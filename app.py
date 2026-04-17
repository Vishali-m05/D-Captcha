"""
Streamlit Frontend for D-CAPTCHA System
Role-based dashboards for Admin, Faculty, and Student
"""

import streamlit as st
import requests
import time
import cv2
from PIL import Image
import numpy as np
import math
import mediapipe as mp
import speech_recognition as sr
from difflib import SequenceMatcher
from datetime import datetime


# Backend API base URL
API_URL = "http://localhost:8000"

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "name" not in st.session_state:
    st.session_state.name = None
if "email" not in st.session_state:
    st.session_state.email = None
if "token" not in st.session_state:
    st.session_state.token = None
if "exam_active" not in st.session_state:
    st.session_state.exam_active = False
if "exam_id" not in st.session_state:
    st.session_state.exam_id = None
if "selected_exam_id" not in st.session_state:
    st.session_state.selected_exam_id = None
if "liveness_step" not in st.session_state:
    st.session_state.liveness_step = None  # None, "blink", "head", "speech"
if "verification_phrase" not in st.session_state:
    st.session_state.verification_phrase = None
if "blink_done" not in st.session_state:
    st.session_state.blink_done = False
if "head_left_done" not in st.session_state:
    st.session_state.head_left_done = False
if "head_right_done" not in st.session_state:
    st.session_state.head_right_done = False


def logout():
    """Logout user and clear session"""
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.name = None
    st.session_state.email = None
    st.session_state.exam_active = False
    st.session_state.exam_id = None
    st.session_state.selected_exam_id = None
    st.session_state.liveness_step = None
    st.session_state.verification_phrase = None
    st.session_state.blink_done = False
    st.session_state.head_left_done = False
    st.session_state.head_right_done = False
    st.rerun()


def distance(p1, p2):
    """Calculate Euclidean distance between two landmarks"""
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def show_liveness_verification_modal():
    """
    D-CAPTCHA Liveness Verification with REAL continuous frame streaming.
    NO manual capture buttons - fully automatic verification.
    """

    st.markdown("## 🔐 D-CAPTCHA Liveness Verification")
    st.markdown("### Complete verification to start your exam")

    # Progress indicator
    steps_completed = 0
    if st.session_state.blink_done:
        steps_completed += 1
    if st.session_state.head_left_done and st.session_state.head_right_done:
        steps_completed += 1

    st.progress(steps_completed / 3, text=f"Step {steps_completed + 1} of 3")

    st.markdown("---")

    # ===================================================================
    # STEP 1: BLINK DETECTION (CONTINUOUS STREAMING - NO BUTTONS)
    # ===================================================================
    if st.session_state.liveness_step == "blink":
        st.info("👁️ **Step 1: Blink Detection**")
        st.markdown("### Please blink your eyes")
        st.markdown("*Camera is active... blink detection in progress...*")

        # HTML/JS for continuous webcam streaming
        video_html = """
        <div style="text-align: center;">
            <video id="video" width="640" height="480" autoplay style="border: 2px solid #4CAF50; border-radius: 10px;"></video>
            <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>
        </div>
        
        <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const context = canvas.getContext('2d');
        
        // Start webcam
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                video.srcObject = stream;
            })
            .catch(err => {
                console.error("Error accessing webcam: ", err);
            });
        
        // Capture and send frames every 500ms
        setInterval(() => {
            context.drawImage(video, 0, 0, 640, 480);
            canvas.toBlob((blob) => {
                const formData = new FormData();
                formData.append('file', blob, 'frame.jpg');
                
                fetch('http://localhost:8000/dcaptcha/verify-blink', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.verified) {
                        // Trigger Streamlit rerun via session state update
                        window.parent.postMessage({type: 'blink_verified'}, '*');
                    }
                })
                .catch(err => console.error('Frame upload error:', err));
            }, 'image/jpeg', 0.8);
        }, 500);
        </script>
        """

        st.components.v1.html(video_html, height=500)

        # Auto-refresh to check backend state
        if "blink_check_counter" not in st.session_state:
            st.session_state.blink_check_counter = 0

        # Poll backend every refresh
        try:
            response = requests.get(f"{API_URL}/dcaptcha/state")
            if response.status_code == 200:
                state = response.json()
                st.info(
                    f"📊 Blinks detected: {state.get('blink_count', 0)} / 3")

                if state.get("blink_verified", False):
                    st.session_state.blink_done = True
                    st.session_state.liveness_step = "head"
                    st.success("✅ Blink detected! Moving to next step...")
                    time.sleep(1)
                    st.rerun()
        except Exception as e:
            st.warning(f"Checking backend... {e}")

        # Auto-refresh every 1 second to poll backend
        st.session_state.blink_check_counter += 1
        time.sleep(1)
        st.rerun()

        st.markdown("---")
        st.caption(
            "💡 Tip: Keep your face visible to the camera and blink naturally")

    # ===================================================================
    # STEP 2: HEAD MOVEMENT (CONTINUOUS STREAMING - NO BUTTONS)
    # ===================================================================
    elif st.session_state.liveness_step == "head":
        st.info("↔️ **Step 2: Head Movement**")

        # Check current state to show instruction
        try:
            response = requests.get(f"{API_URL}/dcaptcha/state")
            if response.status_code == 200:
                state = response.json()

                left_done = state.get("head_left_done", False)
                right_done = state.get("head_right_done", False)

                if not left_done:
                    st.markdown("### ⬅️ Turn your head LEFT")
                elif not right_done:
                    st.markdown("### ➡️ Turn your head RIGHT")
                else:
                    st.markdown("### ✅ Both directions complete!")
        except:
            st.markdown("### Turn your head LEFT, then RIGHT")

        st.markdown("*Camera is active... movement detection in progress...*")

        # HTML/JS for continuous webcam streaming
        video_html = """
        <div style="text-align: center;">
            <video id="video" width="640" height="480" autoplay style="border: 2px solid #2196F3; border-radius: 10px;"></video>
            <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>
        </div>
        
        <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const context = canvas.getContext('2d');
        
        // Start webcam
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                video.srcObject = stream;
            })
            .catch(err => {
                console.error("Error accessing webcam: ", err);
            });
        
        // Capture and send frames every 500ms
        setInterval(() => {
            context.drawImage(video, 0, 0, 640, 480);
            canvas.toBlob((blob) => {
                const formData = new FormData();
                formData.append('file', blob, 'frame.jpg');
                
                fetch('http://localhost:8000/dcaptcha/verify-head-movement', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // Backend handles state internally
                })
                .catch(err => console.error('Frame upload error:', err));
            }, 'image/jpeg', 0.8);
        }, 500);
        </script>
        """

        st.components.v1.html(video_html, height=500)

        # Poll backend for state
        try:
            response = requests.get(f"{API_URL}/dcaptcha/state")
            if response.status_code == 200:
                state = response.json()

                left_done = state.get("head_left_done", False)
                right_done = state.get("head_right_done", False)

                # Progress indicators
                col1, col2 = st.columns(2)
                with col1:
                    if left_done:
                        st.success("✓ LEFT done")
                    else:
                        st.warning("⏳ LEFT pending")
                with col2:
                    if right_done:
                        st.success("✓ RIGHT done")
                    else:
                        st.warning("⏳ RIGHT pending")

                # Auto-advance when both done
                if left_done and right_done:
                    st.session_state.head_left_done = True
                    st.session_state.head_right_done = True
                    st.session_state.liveness_step = "speech"
                    st.success(
                        "✅ Head movement verified! Moving to final step...")
                    time.sleep(1)
                    st.rerun()
        except Exception as e:
            st.warning(f"Checking backend... {e}")

        # Auto-refresh every 1 second
        time.sleep(1)
        st.rerun()

        st.markdown("---")
        st.caption(
            "💡 Tip: Turn your head slowly and clearly - first LEFT, then RIGHT")

    # ===================================================================
    # STEP 3: SPEECH VERIFICATION (CLEAR STATE MACHINE + VISUAL FEEDBACK)
    # ===================================================================
    elif st.session_state.liveness_step == "speech":
        st.info("🎤 **Step 3: Voice Verification**")
        st.markdown(f"### 📝 Say this phrase:")
        st.code(st.session_state.verification_phrase, language=None)

        st.markdown("---")

        # Check backend state for verification result
        try:
            response = requests.get(f"{API_URL}/dcaptcha/state")
            if response.status_code == 200:
                state = response.json()
                if state.get("speech_verified", False):
                    st.success("✅ Voice verified successfully!")
                    st.success("🎉 All verifications completed!")

                    st.markdown("---")

                    if st.button("🚀 Start Exam Now", type="primary", use_container_width=True):
                        # Start the exam
                        try:
                            exam_response = requests.post(
                                f"{API_URL}/exam/start",
                                json={"student_id": st.session_state.user_id}
                            )

                            if exam_response.status_code == 200:
                                exam_data = exam_response.json()

                                # Clean up all speech-related state
                                st.session_state.exam_active = True
                                st.session_state.exam_id = exam_data["exam_id"]
                                st.session_state.liveness_step = None

                                st.success("🎉 Exam starting now!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Failed to start exam: {e}")

                    return  # Stop rendering the recorder

                elif state.get("speech_message") and not state.get("speech_verified"):
                    st.warning(f"⚠️ {state.get('speech_message')}")
        except:
            pass

        # HTML/JS for Client-Side Audio Recording (WAV ENCODING)
        # We need raw WAV for the backend, so we use AudioContext instead of MediaRecorder (which outputs WebM)

        audio_recorder_html = f"""
        <div style="text-align: center;">
            <p id="status_text">Click 'Start Recording' and speak the phrase</p>
            <button id="recordButton" onclick="toggleRecording()" style="
                background-color: #ff4b4b; 
                color: white; 
                padding: 10px 24px; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer; 
                font-size: 16px; 
                font-weight: bold;
                margin-bottom: 10px;">
                🎤 Start Recording
            </button>
            <div id="recording_indicator" style="display: none; color: red; font-weight: bold; margin-top: 10px;">
                🔴 Recording... Speak now!
            </div>
        </div>
        
        <script>
        let audioContext;
        let recorder;
        let input;
        let isRecording = false;
        let audioData = [];
        
        async function toggleRecording() {{
            const button = document.getElementById('recordButton');
            const status = document.getElementById('status_text');
            const indicator = document.getElementById('recording_indicator');
            
            if (!isRecording) {{
                // Start Recording
                try {{
                    const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                    
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    input = audioContext.createMediaStreamSource(stream);
                    
                    // Create script processor to capture raw audio
                    // bufferSize 4096, 1 input channel, 1 output channel
                    recorder = audioContext.createScriptProcessor(4096, 1, 1);
                    
                    audioData = [];
                    
                    recorder.onaudioprocess = function(e) {{
                        const channelData = e.inputBuffer.getChannelData(0);
                        audioData.push(new Float32Array(channelData));
                    }};
                    
                    input.connect(recorder);
                    recorder.connect(audioContext.destination);
                    
                    isRecording = true;
                    button.innerText = "⏹ Stop & Verify";
                    button.style.backgroundColor = "#333";
                    status.innerText = "Listening...";
                    indicator.style.display = "block";
                    
                }} catch (err) {{
                    console.error("Error accessing microphone:", err);
                    status.innerText = "❌ Error: Could not access microphone. Please allow permissions.";
                }}
            }} else {{
                // Stop Recording
                isRecording = false;
                button.innerText = "🎤 Start Recording";
                button.style.backgroundColor = "#ff4b4b";
                status.innerText = "Processing...";
                indicator.style.display = "none";
                
                // Disconnect
                if (recorder) {{
                    recorder.disconnect();
                    input.disconnect();
                }}
                
                // Encode to WAV
                const wavBlob = exportWAV(audioData, audioContext.sampleRate);
                uploadAudio(wavBlob);
            }}
        }}
        
        function exportWAV(audioData, sampleRate) {{
            // Flatten audioData
            let bufferLength = 0;
            for (let i = 0; i < audioData.length; i++) {{
                bufferLength += audioData[i].length;
            }}
            
            const samples = new Float32Array(bufferLength);
            let offset = 0;
            for (let i = 0; i < audioData.length; i++) {{
                samples.set(audioData[i], offset);
                offset += audioData[i].length;
            }}
            
            // Create WAV file
            const buffer = new ArrayBuffer(44 + samples.length * 2);
            const view = new DataView(buffer);
            
            // RIFF chunk descriptor
            writeString(view, 0, 'RIFF');
            view.setUint32(4, 36 + samples.length * 2, true);
            writeString(view, 8, 'WAVE');
            
            // fmt sub-chunk
            writeString(view, 12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true); // PCM format
            view.setUint16(22, 1, true); // Mono
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * 2, true);
            view.setUint16(32, 2, true);
            view.setUint16(34, 16, true); // 16-bit
            
            // data sub-chunk
            writeString(view, 36, 'data');
            view.setUint32(40, samples.length * 2, true);
            
            // Write PCM samples
            floatTo16BitPCM(view, 44, samples);
            
            return new Blob([view], {{ type: 'audio/wav' }});
        }}
        
        function writeString(view, offset, string) {{
            for (let i = 0; i < string.length; i++) {{
                view.setUint8(offset + i, string.charCodeAt(i));
            }}
        }}
        
        function floatTo16BitPCM(output, offset, input) {{
            for (let i = 0; i < input.length; i++, offset += 2) {{
                const s = Math.max(-1, Math.min(1, input[i]));
                output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }}
        }}
        
        function uploadAudio(blob) {{
            const formData = new FormData();
            formData.append('file', blob, 'recording.wav');
            
            // Phrase to verify against
            const phrase = "{st.session_state.verification_phrase}";
            
            fetch('http://localhost:8000/dcaptcha/verify-speech-audio?phrase=' + encodeURIComponent(phrase), {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                const status = document.getElementById('status_text');
                if (data.passed) {{
                    status.innerText = "✅ Verified! Please wait...";
                    status.style.color = "green";
                }} else {{
                    status.innerText = "❌ " + (data.message || "Verification failed");
                    status.style.color = "red";
                }}
            }})
            .catch(err => {{
                console.error("Upload error:", err);
                document.getElementById('status_text').innerText = "❌ Connection error";
            }});
        }}
        </script>
        """

        st.components.v1.html(audio_recorder_html, height=200)

        st.markdown("---")
        st.caption(
            "💡 Tip: Click 'Start Recording', say the phrase clearly, then click 'Stop & Verify'.")

        # Auto-refresh to check backend state updates
        time.sleep(1)
        st.rerun()


# ============================================================================
# AUTHENTICATION PAGES
# ============================================================================

def login_page():
    """Login page for all roles"""
    st.title("🔐 D-CAPTCHA Login")
    st.markdown("### AI-based Online Exam Proctoring System")

    st.markdown("---")

    # Role selection
    role = st.radio(
        "Select your role:",
        ["Student", "Faculty", "Admin"],
        horizontal=True
    )

    st.markdown("---")

    # Login form
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("Please fill in all fields")
            else:
                # Call login API
                try:
                    response = requests.post(
                        f"{API_URL}/login",
                        json={
                            "email": email,
                            "password": password,
                            "role": role.lower()
                        }
                    )

                    data = response.json()
                    print(f"DEBUG APP: Login response: {data}")

                    if data["success"]:
                        st.session_state.logged_in = True
                        st.session_state.role = data["role"]
                        st.session_state.user_id = data["user_id"]
                        st.session_state.name = data["name"]
                        st.session_state.email = data["email"]

                        # Check if token exists in response
                        if "token" in data:
                            st.session_state.token = data["token"]
                            print(f"DEBUG APP: Token stored successfully")
                            print(
                                f"DEBUG APP: Token type: {type(st.session_state.token)}")
                            print(
                                f"DEBUG APP: Token length: {len(st.session_state.token) if st.session_state.token else 0}")
                            print(
                                f"DEBUG APP: Token first 30 chars: {st.session_state.token[:30] if st.session_state.token else 'EMPTY'}")
                        else:
                            print(f"DEBUG APP: ERROR - No token in response!")
                            print(f"DEBUG APP: Response keys: {data.keys()}")
                            st.error("❌ Login failed: No token in response")

                        st.success(f"Welcome, {data['name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(data["message"])

                except Exception as e:
                    print(
                        f"DEBUG APP: Exception during login: {type(e).__name__}: {str(e)}")
                    st.error(f"Connection error: {e}")

    st.markdown("---")

    # Registration link
    if role in ["Student", "Faculty"]:
        st.info("Don't have an account?")
        if st.button("Register", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    else:
        st.warning("⚠️ Admin credentials are hardcoded")
        st.code("Email: admin@dcaptcha.com\nPassword: admin123")
        st.info("Use these credentials to login as Admin")


def registration_page():
    """Registration page for students and faculty"""
    st.title("📝 Registration")

    # Back button
    if st.button("← Back to Login"):
        st.session_state.page = "login"
        st.rerun()

    st.markdown("---")

    # Role selection
    role = st.radio(
        "Register as:",
        ["Student", "Faculty"],
        horizontal=True
    )

    st.markdown("---")

    # Registration form
    with st.form("registration_form"):
        name = st.text_input("Full Name", placeholder="John Doe")
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        submit = st.form_submit_button("Register", use_container_width=True)

        if submit:
            if not name or not email or not password:
                st.error("Please fill in all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                # Call registration API
                try:
                    response = requests.post(
                        f"{API_URL}/register",
                        json={
                            "name": name,
                            "email": email,
                            "password": password,
                            "role": role.lower()
                        }
                    )

                    data = response.json()

                    if data["success"]:
                        # For students: go to face capture page
                        # For faculty: skip face capture and go directly to login
                        if role.lower() == "student":
                            st.session_state.pending_user_id = data["user_id"]
                            st.session_state.pending_role = role.lower()
                            st.session_state.page = "capture_face"
                            st.rerun()
                        else:
                            # Faculty registration complete - go to login
                            st.success(
                                "Registration successful! Please login.")
                            time.sleep(2)
                            st.session_state.page = "login"
                            st.rerun()
                    else:
                        st.error(data["message"])

                except Exception as e:
                    st.error(f"Connection error: {e}")


def capture_face_page():
    """Face capture page after registration"""
    st.title("📸 Register Your Face")
    st.info("For student verification during exams, please capture your face image.")

    st.markdown("---")

    # Camera input
    st.markdown("### Click the button below to capture your face")
    camera_image = st.camera_input("Take a photo")

    if camera_image is not None:
        # Display captured image
        st.image(camera_image, caption="Captured Image", width=300)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Use This Photo", use_container_width=True, type="primary"):
                try:
                    # Send image to backend
                    files = {"file": camera_image.getvalue()}
                    response = requests.post(
                        f"{API_URL}/register-face/{st.session_state.pending_user_id}",
                        files=files
                    )

                    if response.status_code == 200:
                        st.success("✅ Face registered successfully!")
                        st.success("Registration complete! Please login.")
                        time.sleep(2)

                        # Clear pending data
                        del st.session_state.pending_user_id
                        del st.session_state.pending_role
                        st.session_state.page = "login"
                        st.rerun()
                    else:
                        error_data = response.json()
                        st.error(
                            f"❌ {error_data.get('detail', 'Face registration failed')}")

                except Exception as e:
                    st.error(f"Connection error: {e}")

        with col2:
            if st.button("🔄 Retake Photo", use_container_width=True):
                st.rerun()

    st.markdown("---")
    st.warning("⚠️ Face registration is mandatory for students")


# ============================================================================
# STUDENT DASHBOARD
# ============================================================================

def student_dashboard():
    """Dashboard for students"""
    st.title("🎓 Student Dashboard")

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### Welcome, {st.session_state.name}!")
    with col2:
        if st.button("Logout", use_container_width=True):
            logout()

    st.markdown("---")

    # Liveness Verification Modal (appears when starting exam)
    if st.session_state.liveness_step is not None:
        show_liveness_verification_modal()
    else:
        # Show exams only if no liveness verification is in progress
        if not st.session_state.exam_active and st.session_state.selected_exam_id is None:
            st.info("📝 Select an exam to get started")
            st.markdown("---")

        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            response = requests.get(
                f"{API_URL}/student/available-exams",
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                exams = data.get("exams", [])

                if exams:
                    st.markdown("### 📋 Available Exams")

                    for exam in exams:
                        with st.container():
                            col1, col2, col3, col4, col5 = st.columns(
                                [2, 2, 1.5, 1.5, 1.5])

                            with col1:
                                st.write(f"**📚 {exam['paper_name']}**")
                            with col2:
                                st.write(f"Subject: {exam['subject']}")
                            with col3:
                                st.write(f"⏱️ {exam['duration_minutes']} min")
                            with col4:
                                st.write(f"Marks: {exam['total_marks']}")
                            with col5:
                                if st.button(f"🚀 Start", key=f"exam_{exam['paper_id']}", type="primary"):
                                    # Store selected exam
                                    st.session_state.selected_exam_id = exam['paper_id']
                                    st.session_state.exam_duration_minutes = exam['duration_minutes']

                                    # Reset D-CAPTCHA backend state
                                    try:
                                        requests.post(
                                            f"{API_URL}/dcaptcha/reset")
                                    except:
                                        pass

                                    # Initialize liveness verification
                                    st.session_state.liveness_step = "blink"
                                    st.session_state.blink_done = False
                                    st.session_state.head_left_done = False
                                    st.session_state.head_right_done = False

                                    # Get random phrase
                                    try:
                                        response = requests.get(
                                            f"{API_URL}/exam/get-verification-phrase")
                                        if response.status_code == 200:
                                            st.session_state.verification_phrase = response.json()[
                                                "phrase"]
                                    except:
                                        st.session_state.verification_phrase = "I am ready for my exam"

                                    st.rerun()

                            st.write(
                                f"📅 Scheduled: **{exam['scheduled_date']}** at **{exam['start_time']}**")
                            st.divider()
                else:
                    st.warning("📭 No exams available at this time")
            else:
                st.error("❌ Failed to load available exams")

        except Exception as e:
            st.error(f"Connection error: {e}")
    
    if st.session_state.exam_active:
        # Exam in progress - CONTINUOUS POLLING FOR TERMINATION
        # st.success("✅ Exam in Progress")
        st.markdown(f"**Exam ID:** {st.session_state.exam_id}")
        
        # ===== TIMER INITIALIZATION =====
        if "exam_start_time" not in st.session_state or st.session_state.exam_start_time is None:
            st.session_state.exam_start_time = datetime.now()

        # Calculate remaining time (outside if block so it updates on every rerun)
        elapsed = datetime.now() - st.session_state.exam_start_time
        total_seconds = st.session_state.exam_duration_minutes * 60
        remaining_seconds = max(
            0, total_seconds - int(elapsed.total_seconds()))

        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60

        # ===== TIMER DISPLAY WITH COLOR CODING =====
        col_timer1, col_timer2, col_timer3 = st.columns([1, 2, 1])

        with col_timer2:
            # Color coding logic
            if remaining_seconds == 0:
                timer_color = "🔴"
                timer_bg = "#ff4444"
                timer_text = "TIME UP!"
            elif remaining_seconds < 60:  # Less than 1 minute
                timer_color = "🔴"
                timer_bg = "#ff6666"
                timer_text = f"{seconds:02d}s"
            elif remaining_seconds < 300:  # Less than 5 minutes
                timer_color = "🟠"
                timer_bg = "#ffaa44"
                timer_text = f"{minutes:02d}:{seconds:02d}"
            else:
                timer_color = "🟢"
                timer_bg = "#44ff44"
                timer_text = f"{minutes:02d}:{seconds:02d}"

            # Display timer in prominent box
            st.markdown(f"""
            <div style="
                background-color: {timer_bg};
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                font-size: 48px;
                font-weight: bold;
            color: white;
            font-family: 'Courier New', monospace;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        ">
            ⏰ {timer_text}
        </div>
        """, unsafe_allow_html=True)

        # Status message
        if remaining_seconds == 0:
            st.error("❌ **TIME'S UP!** Exam will auto-submit in 3 seconds...")
            time.sleep(1)

            # AUTO-SUBMIT when time is up
            try:
                submit_response = requests.post(
                    f"{API_URL}/student/submit-exam",
                    json={
                        "exam_id": st.session_state.exam_id,
                        "answers": st.session_state.student_answers if hasattr(st.session_state, 'student_answers') else {}
                    },
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                
                if submit_response.status_code == 200:
                    st.success("✅ Exam auto-submitted successfully!")
                    st.balloons()
                    time.sleep(2)
                    
                    # Reset state
                    st.session_state.exam_active = False
                    st.session_state.exam_id = None
                    st.session_state.exam_start_time = None
                    st.rerun()
                else:
                    st.error("❌ Failed to auto-submit exam")
            except Exception as e:
                st.error(f"❌ Error during auto-submit: {str(e)}")
            
            st.stop()
        
        elif remaining_seconds < 60:
            st.warning(f"⚠️ **HURRY UP!** Only {seconds:02d} seconds left!")
        elif remaining_seconds < 300:
            st.warning(
                f"⚠️ **5 minutes or less remaining** - {minutes:02d}:{seconds:02d}")
        else:
            st.info(f"✅ Time remaining: {minutes:02d}:{seconds:02d}")
        
        # Warning message
        st.warning("""
        ⚠️ **Important Instructions:**
        - Stay centered in the camera frame
        - Do not use mobile phone
        - Only one person should be visible
        - Exam will auto-terminate after 5 violations
        """)
        
        # Main layout: Video + Questions side by side
        col_video, col_questions = st.columns([1, 2])
        
        with col_video:
            st.markdown("### 📹 Live Feed")
            # MJPEG Stream in a fixed-size container
            st.markdown(
                f'<div style="width: 100%; max-width: 450px;"><img src="{API_URL}/exam/video_feed" width="100%" style="border-radius: 10px; border: 2px solid #e6e6e6;"></div>',
                unsafe_allow_html=True
            )
            
            st.markdown("### 📊 Status")
            st.info("Monitor active. Do not leave the camera view.")
            
            # JavaScript & HTML for background polling (Runs inside iframe)
            js_code = f"""
            <div id="violation_status_box" style="
            padding: 15px; 
            border-radius: 8px; 
            background-color: #f0f2f6; 
            margin-top: 10px; 
            font-family: system-ui, -apple-system, sans-serif;">
            <strong style="color: #31333F;">Tracking Violations...</strong>
            <p id="violation_count_text" style="font-size: 24px; margin: 10px 0; color: #31333F;">-- / 5</p>
            <div id="status_indicator" style="color: green; font-weight: bold;">● Monitoring Active</div>
        </div>

        <script>
        function checkStatus() {{
            fetch('{API_URL}/exam/status?student_id={st.session_state.user_id}')
            .then(response => response.json())
            .then(data => {{
                // Update DOM elements inside this iframe
                const countText = document.getElementById("violation_count_text");
                const indicator = document.getElementById("status_indicator");
                const box = document.getElementById("violation_status_box");
                
                if(data.terminated) {{
                    // Try to reload parent window to show termination screen
                    try {{
                        window.parent.location.reload();
                    }} catch(e) {{
                        // Fallback if blocked
                        box.style.backgroundColor = "#ff4444";
                        box.innerHTML = '<h2 style="color:white">EXAM TERMINATED</h2><p style="color:white">Please refresh the page</p>';
                    }}
                }} else {{
                    // Update stats
                    if(countText) countText.innerText = data.student_alert_count + " / " + data.max_violations;
                    
                    if(data.student_alert_count > 0) {{
                        if(indicator) {{
                            indicator.innerText = "● Violations Detected!";
                            indicator.style.color = "red";
                        }}
                        if(box) box.style.border = "2px solid red";
                    }} else {{
                        if(indicator) {{
                            indicator.innerText = "● Monitoring Active";
                            indicator.style.color = "green";
                        }}
                        if(box) box.style.border = "none";
                    }}
                }}
            }})
            .catch(err => console.error("Poll error:", err));
        }}
        
        // Poll every 2 seconds
        setInterval(checkStatus, 2000);
        </script>
        """
            import streamlit.components.v1 as components
            components.html(js_code, height=200)

        with col_questions:
            st.markdown("### 📝 Exam Questions")

            # Load exam questions
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                response = requests.get(
                    f"{API_URL}/student/exam/{st.session_state.selected_exam_id}",
                    headers=headers
                )

                if response.status_code == 200:
                    exam_data = response.json()

                    # Display exam info
                    st.markdown(
                        f"**📚 {exam_data['paper_name']}** - {exam_data['subject']}")
                    st.markdown(
                        f"**Marks:** {exam_data['total_marks']} | **Questions:** {exam_data['total_questions']}")
                    st.divider()

                    # Display questions in scrollable area
                    questions = exam_data["questions"]

                    with st.form("exam_form"):
                        for idx, question in enumerate(questions, 1):
                            st.write(
                                f"**Q{idx}: {question['question_text']}** ({question['marks']} marks)")

                            # Radio button for options
                            selected_option = st.radio(
                                "Select your answer:",
                                ["A", "B", "C", "D"],
                                format_func=lambda x: f"{x}) {question['options'][x]}",
                                key=f"q_{question['question_id']}",
                                horizontal=True,
                                label_visibility="collapsed"
                            )

                            if "student_answers" not in st.session_state:
                                st.session_state.student_answers = {}
                            st.session_state.student_answers[question['question_id']
                                                             ] = selected_option
                            st.divider()

                        # Submit button
                        submitted = st.form_submit_button(
                            "✅ Submit Exam", type="primary", use_container_width=True)

                        if submitted:
                            st.success("✅ Exam submitted successfully!")
                            st.info("📊 Your exam is being evaluated.")

                            # Reset exam state
                            st.session_state.exam_active = False
                            st.session_state.selected_exam_id = None
                            st.session_state.exam_id = None
                            st.session_state.student_answers = {}

                            time.sleep(2)
                            st.rerun()
                else:
                    st.error("❌ Failed to load exam questions")

            except Exception as e:
                st.error(f"❌ Connection error: {e}")
        
        # Auto-refresh to update timer every second
        time.sleep(1)
        st.rerun()


# ============================================================================
# FACULTY DASHBOARD
# ============================================================================

def faculty_dashboard():
    """Dashboard for faculty"""
    st.title("👨‍🏫 Faculty Dashboard")

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### Welcome, {st.session_state.name}!")
    with col2:
        if st.button("Logout", use_container_width=True):
            logout()

    st.markdown("---")

    # Get all students
    try:
        response = requests.get(f"{API_URL}/faculty/students")

        if response.status_code == 200:
            data = response.json()
            students = data["students"]

            if not students:
                st.info("No students registered yet")
            else:
                st.markdown(f"### 📋 Students ({len(students)})")

                # Display students
                for student in students:
                    with st.expander(f"👤 {student['name']} - {student['email']}"):
                        # Get student violations
                        try:
                            alert_response = requests.get(
                                f"{API_URL}/faculty/alerts/{student['id']}"
                            )

                            if alert_response.status_code == 200:
                                alert_data = alert_response.json()
                                violations = alert_data["total_violations"]
                                alerts = alert_data["alerts"]
                                exams = alert_data["exams"]

                                # Display statistics
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Total Violations", violations)
                                with col2:
                                    st.metric("Total Exams", len(exams))

                                # Display violations
                                if alerts:
                                    st.markdown("**Violation History:**")
                                    for alert in alerts[:10]:  # Show last 10
                                        st.text(
                                            f"⚠️ {alert['violation']} - {alert['timestamp']}")
                                else:
                                    st.success("✅ No violations recorded")

                                # Display exam history
                                if exams:
                                    st.markdown("**Exam History:**")
                                    for exam in exams[:5]:  # Show last 5
                                        status_emoji = "✅" if exam['status'] == "completed" else "❌"
                                        st.text(
                                            f"{status_emoji} {exam['status'].title()} - {exam['start_time']}")

                        except Exception as e:
                            st.error(f"Error loading student data: {e}")

        else:
            st.error("Failed to load students")

    except Exception as e:
        st.error(f"Connection error: {e}")


# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

def admin_dashboard():
    """Dashboard for admin"""
    st.title("👑 Admin Dashboard")

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### Welcome, {st.session_state.name}!")
    with col2:
        if st.button("Logout", use_container_width=True):
            logout()

    st.markdown("---")

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["👥 Users", "📝 Exams", "⚠️ Violations"])

    # Tab 1: Users
    with tab1:
        try:
            response = requests.get(f"{API_URL}/admin/users")

            if response.status_code == 200:
                data = response.json()

                # Statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Users", data["total_users"])
                with col2:
                    st.metric("Students", data["total_students"])
                with col3:
                    st.metric("Faculty", data["total_faculty"])

                st.markdown("---")

                # Display users table
                users = data["users"]
                if users:
                    st.markdown("### User List")
                    for user in users:
                        role_emoji = "🎓" if user["role"] == "student" else "👨‍🏫"
                        st.text(
                            f"{role_emoji} {user['name']} - {user['email']} ({user['role'].title()})")
                else:
                    st.info("No users registered yet")

            else:
                st.error("Failed to load users")

        except Exception as e:
            st.error(f"Connection error: {e}")

    # Tab 2: Exams
    with tab2:
        try:
            response = requests.get(f"{API_URL}/admin/exams")

            if response.status_code == 200:
                data = response.json()

                # Statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Exams", data["total_exams"])
                with col2:
                    st.metric("Completed", data["completed"])
                with col3:
                    st.metric("Terminated", data["terminated"])
                with col4:
                    st.metric("In Progress", data["in_progress"])

                st.markdown("---")

                # Display exams
                exams = data["exams"]
                if exams:
                    st.markdown("### Exam History")
                    for exam in exams[:20]:  # Show last 20
                        status_color = "🟢" if exam["status"] == "completed" else (
                            "🔴" if exam["status"] == "terminated" else "🟡")
                        st.text(
                            f"{status_color} [{exam['status'].upper()}] {exam['student_name']} - {exam['start_time']}")
                else:
                    st.info("No exams conducted yet")

            else:
                st.error("Failed to load exams")

        except Exception as e:
            st.error(f"Connection error: {e}")

    # Tab 3: Violations
    with tab3:
        try:
            response = requests.get(f"{API_URL}/admin/alerts")

            if response.status_code == 200:
                data = response.json()

                # Statistics
                st.metric("Total Violations", data["total_violations"])

                st.markdown("---")

                # Display violations
                alerts = data["alerts"]
                if alerts:
                    st.markdown("### Violation Log")
                    for alert in alerts[:50]:  # Show last 50
                        st.text(
                            f"⚠️ {alert['violation']} - {alert['timestamp']}")
                else:
                    st.success("✅ No violations recorded")

            else:
                st.error("Failed to load violations")

        except Exception as e:
            st.error(f"Connection error: {e}")


# ============================================================================
# MAIN APP LOGIC
# ============================================================================

def main():
    """Main application logic"""

    # Set page config
    st.set_page_config(
        page_title="D-CAPTCHA System",
        page_icon="🎓",
        layout="wide"
    )

    # Initialize page state
    if "page" not in st.session_state:
        st.session_state.page = "login"

    # Route to appropriate page
    if not st.session_state.logged_in:
        # Show authentication pages
        if st.session_state.page == "register":
            registration_page()
        elif st.session_state.page == "capture_face":
            capture_face_page()
        else:
            login_page()
    else:
        # Show role-based dashboard
        if st.session_state.role == "student":
            student_dashboard()
        elif st.session_state.role == "faculty":
            faculty_dashboard()
        elif st.session_state.role == "admin":
            admin_dashboard()
        else:
            st.error("Unknown role")
            logout()


if __name__ == "__main__":
    main()
