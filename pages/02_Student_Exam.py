"""
Student Exam Portal for D-CAPTCHA System
Display scheduled exams and take exams with MCQs and timer
"""

import streamlit as st
import requests
import time
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Student Exam Portal", layout="wide", initial_sidebar_state="expanded")

# Check if user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("❌ Please login first")
    st.stop()

# Check if user is student
if st.session_state.role != "student":
    st.error("❌ Only students can access this page")
    st.stop()

st.title("📝 Exam Portal")
st.markdown(f"Welcome, **{st.session_state.name}**")

# Initialize session state for exam
if "exam_active" not in st.session_state:
    st.session_state.exam_active = False
if "selected_exam_id" not in st.session_state:
    st.session_state.selected_exam_id = None
if "exam_paper_id" not in st.session_state:
    st.session_state.exam_paper_id = None
if "exam_duration" not in st.session_state:
    st.session_state.exam_duration = None
if "exam_start_time" not in st.session_state:
    st.session_state.exam_start_time = None
if "student_answers" not in st.session_state:
    st.session_state.student_answers = {}
if "liveness_step" not in st.session_state:
    st.session_state.liveness_step = None
if "blink_done" not in st.session_state:
    st.session_state.blink_done = False
if "head_left_done" not in st.session_state:
    st.session_state.head_left_done = False
if "head_right_done" not in st.session_state:
    st.session_state.head_right_done = False
if "auto_submitted" not in st.session_state:
    st.session_state.auto_submitted = False
if "exam_scheduled_datetime" not in st.session_state:
    st.session_state.exam_scheduled_datetime = None

# Create tabs
if st.session_state.liveness_step is not None:
    # Liveness verification in progress
    st.warning("🔐 D-CAPTCHA Verification in Progress")
    st.info("Please complete the liveness verification to access your exam. Your session will return here once verification is complete.")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("✅ Verification Complete - Start Exam", type="primary", use_container_width=True):
            st.session_state.liveness_step = None
            st.session_state.exam_active = True
            st.rerun()
else:
    # Show tab names dynamically based on exam selection
    if st.session_state.exam_active:
        tab1, tab2 = st.tabs(["📋 Available Exams (Locked)", "📖 Take Exam (Active)"])
    else:
        tab1, tab2 = st.tabs(["📋 Available Exams", "📖 Take Exam"])

    # ============================================================================
    # TAB 1: AVAILABLE EXAMS
    # ============================================================================
    with tab1:
        st.header("📋 Available Exams")
        st.markdown("---")
        
        # Show warning if exam is active
        if st.session_state.exam_active:
            st.warning("⚠️ You have an active exam in progress. Complete it first before starting another exam.")
            st.info(f"📌 **Active Exam ID:** {st.session_state.selected_exam_id}")
        
        try:
            response = requests.get(
                f"{API_URL}/student/available-exams",
                headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                exams = data["exams"]
                
                # Sort exams by scheduled date and time (most recent/next first)
                if exams:
                    try:
                        exams_sorted = sorted(exams, key=lambda x: datetime.strptime(f"{x['scheduled_date']} {x['start_time']}", "%Y-%m-%d %H:%M"), reverse=False)
                        exams = exams_sorted
                    except:
                        pass  # If sorting fails, use original order
                
                if exams:
                    st.success(f"✅ Found {len(exams)} available exam(s)")
                    
                    for exam in exams:
                        with st.container():
                            col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1.5])
                            
                            with col1:
                                st.write(f"**📚 {exam['paper_name']}**")
                            with col2:
                                st.write(f"Subject: {exam['subject']}")
                            with col3:
                                st.write(f"⏱️ {exam['duration_minutes']} min")
                            with col4:
                                st.write(f"Marks: {exam['total_marks']}")
                            with col5:
                                # Check if exam time has arrived
                                try:
                                    scheduled_dt = datetime.strptime(exam.get('scheduled_datetime', f"{exam['scheduled_date']} {exam['start_time']}:00"), "%Y-%m-%d %H:%M:%S")
                                except:
                                    try:
                                        scheduled_dt = datetime.strptime(f"{exam['scheduled_date']} {exam['start_time']}", "%Y-%m-%d %H:%M")
                                    except:
                                        scheduled_dt = datetime.now()
                                
                                now = datetime.now()
                                time_until_start = (scheduled_dt - now).total_seconds()
                                
                                # Disable button if:
                                # 1. Another exam is active
                                # 2. Scheduled time hasn't arrived yet
                                button_disabled = st.session_state.exam_active or time_until_start > 0
                                
                                if st.session_state.exam_active:
                                    button_help = "Complete your active exam first"
                                elif time_until_start > 0:
                                    mins = int(time_until_start // 60)
                                    secs = int(time_until_start % 60)
                                    button_help = f"Exam starts in {mins}:{secs:02d}"
                                else:
                                    button_help = None
                                
                                if st.button(f"🚀 Start Exam", key=f"start_{exam['paper_id']}", type="primary", disabled=button_disabled, help=button_help):
                                    st.session_state.selected_exam_id = exam['paper_id']
                                    st.session_state.exam_duration = exam['duration_minutes']
                                    st.session_state.exam_scheduled_datetime = exam.get('scheduled_datetime', f"{exam['scheduled_date']} {exam['start_time']}:00")
                                    
                                    # Reset D-CAPTCHA backend state
                                    try:
                                        requests.post(f"{API_URL}/dcaptcha/reset")
                                    except:
                                        pass
                                    
                                    # Initialize liveness verification
                                    st.session_state.liveness_step = "blink"
                                    st.session_state.blink_done = False
                                    st.session_state.head_left_done = False
                                    st.session_state.head_right_done = False
                                    
                                    # Get random phrase
                                    try:
                                        response = requests.get(f"{API_URL}/exam/get-verification-phrase")
                                        if response.status_code == 200:
                                            st.session_state.verification_phrase = response.json()["phrase"]
                                    except:
                                        st.session_state.verification_phrase = "I am ready for my exam"
                                    
                                    st.rerun()
                            
                            # Display scheduled time with countdown
                            try:
                                scheduled_dt = datetime.strptime(exam.get('scheduled_datetime', f"{exam['scheduled_date']} {exam['start_time']}:00"), "%Y-%m-%d %H:%M:%S")
                            except:
                                try:
                                    scheduled_dt = datetime.strptime(f"{exam['scheduled_date']} {exam['start_time']}", "%Y-%m-%d %H:%M")
                                except:
                                    scheduled_dt = datetime.now()
                            
                            now = datetime.now()
                            time_until_start = (scheduled_dt - now).total_seconds()
                            
                            if time_until_start > 0:
                                mins = int(time_until_start // 60)
                                secs = int(time_until_start % 60)
                                st.write(f"📅 **{exam['scheduled_date']}** at **{exam['start_time']}** | ⏳ **Starts in: {mins:02d}:{secs:02d}**")
                            else:
                                st.write(f"📅 **{exam['scheduled_date']}** at **{exam['start_time']}** | ✅ **Available now!**")
                            st.divider()
                else:
                    st.info("📭 No exams scheduled for you at the moment.")
            else:
                st.error("❌ Failed to fetch exams")
        except Exception as e:
            st.error(f"❌ Connection error: {str(e)}")

    # ============================================================================
    # TAB 2: TAKE EXAM
    # ============================================================================
    with tab2:
        if st.session_state.exam_active and st.session_state.selected_exam_id:
            # Display selected exam info
            st.success(f"✅ Active Exam ID: {st.session_state.selected_exam_id}")
            st.header("📖 Exam Questions")
            
            try:
                response = requests.get(
                    f"{API_URL}/student/exam/{st.session_state.selected_exam_id}",
                    headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
                )
                
                if response.status_code == 200:
                    exam_data = response.json()
                    
                    # Parse scheduled datetime and calculate timer based on it
                    try:
                        scheduled_dt = datetime.strptime(st.session_state.exam_scheduled_datetime, "%Y-%m-%d %H:%M:%S")
                    except:
                        # Fallback if format is different
                        scheduled_dt = datetime.strptime(st.session_state.exam_scheduled_datetime, "%Y-%m-%d %H:%M")
                    
                    exam_end_dt = scheduled_dt + timedelta(minutes=st.session_state.exam_duration)
                    now = datetime.now()
                    
                    # Calculate remaining time from scheduled start time (not from when student clicked)
                    remaining_seconds = int((exam_end_dt - now).total_seconds())
                    remaining_seconds = max(0, remaining_seconds)
                    
                    # Also calculate if exam has started
                    time_until_start = int((scheduled_dt - now).total_seconds())
                    
                    minutes = remaining_seconds // 60
                    seconds = remaining_seconds % 60
                    
                    # ===== TIMER DISPLAY AT TOP =====
                    st.markdown("---")
                    
                    col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 1.5, 1])
                    col1.metric("📚 Paper", exam_data["paper_name"][:20])
                    col2.metric("📖 Subject", exam_data["subject"][:20])
                    col3.metric("⭐ Total Marks", exam_data["total_marks"])
                    
                    # Timer with color coding - show "Starts in" if not started yet
                    if time_until_start > 0:
                        start_min = time_until_start // 60
                        start_sec = time_until_start % 60
                        col4.metric("⏰ Starts In", f"{start_min:02d}:{start_sec:02d}", delta="NOT YET", delta_color="off")
                        col5.write("")
                        time_color = "🟡"
                        st.info(f"⏳ Exam will start on **{scheduled_dt.strftime('%H:%M:%S')}** ({start_min} min {start_sec} sec)")
                    elif remaining_seconds == 0:
                        col4.metric("⏰ Time Left", "00:00", delta="EXAM ENDED", delta_color="off")
                        col5.write("")
                        time_color = "🔴"
                    elif remaining_seconds < 300:  # Less than 5 minutes
                        col4.metric("⏰ Time Left", f"{minutes:02d}:{seconds:02d}", delta="HURRY!", delta_color="inverse")
                        col5.write("")
                        time_color = "🟠"
                    else:
                        col4.metric("⏰ Time Left", f"{minutes:02d}:{seconds:02d}")
                        col5.write("")
                        time_color = "🟢"
                    
                    st.divider()
                    st.info(f"📝 **Total Questions:** {exam_data['total_questions']} | {time_color} Time Remaining: {minutes:02d}:{seconds:02d}")
                    
                    # Only allow questions display if exam has started
                    if time_until_start > 0:
                        st.warning(f"⏳ **Exam hasn't started yet!** It will begin at {scheduled_dt.strftime('%H:%M:%S')}")
                        st.stop()
                    
                    # AUTO-SUBMIT if time is up
                    if remaining_seconds == 0 and not st.session_state.auto_submitted:
                        st.session_state.auto_submitted = True
                        st.error("❌ **Time's up!** Your exam is being auto-submitted...")
                        
                        try:
                            submit_response = requests.post(
                                f"{API_URL}/student/submit-exam",
                                json={
                                    "exam_id": st.session_state.selected_exam_id,
                                    "answers": st.session_state.student_answers
                                },
                                headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
                            )
                            
                            if submit_response.status_code == 200:
                                st.success("✅ Exam auto-submitted successfully!")
                                st.balloons()
                                
                                # Reset exam state
                                time.sleep(2)
                                st.session_state.exam_active = False
                                st.session_state.selected_exam_id = None
                                st.session_state.student_answers = {}
                                st.session_state.exam_start_time = None
                                st.session_state.auto_submitted = False
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error during auto-submit: {str(e)}")
                        
                        st.stop()
                    
                    # Display questions
                    questions = exam_data["questions"]
                    
                    with st.form("exam_form", clear_on_submit=False):
                        for idx, question in enumerate(questions, 1):
                            st.write(f"### Q{idx}: {question['question_text']}")
                            st.write(f"*Marks: {question['marks']}*")
                            
                            # Initialize answer for this question if not exists
                            question_key = f"q_{question['question_id']}"
                            if question_key not in st.session_state:
                                st.session_state[question_key] = None
                            
                            # Radio button for options - NO DEFAULT SELECTION
                            selected_option = st.radio(
                                "Select your answer:",
                                [None, "A", "B", "C", "D"],
                                format_func=lambda x: "Select an option" if x is None else f"{x}) {question['options'][x]}",
                                key=question_key,
                                horizontal=False
                            )
                            
                            # Store answer
                            if selected_option:
                                st.session_state.student_answers[question['question_id']] = selected_option
                            
                            st.divider()
                        
                        # Submit button - DISABLED if time is up
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col2:
                            submitted = st.form_submit_button(
                                "✅ Submit Exam",
                                type="primary",
                                use_container_width=True,
                                disabled=(remaining_seconds == 0)
                            )
                        
                        if submitted:
                            try:
                                submit_response = requests.post(
                                    f"{API_URL}/student/submit-exam",
                                    json={
                                        "exam_id": st.session_state.selected_exam_id,
                                        "answers": st.session_state.student_answers
                                    },
                                    headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
                                )
                                
                                if submit_response.status_code == 200:
                                    st.success("✅ Exam submitted successfully!")
                                    st.info("📊 Your exam is being evaluated. You will receive results shortly.")
                                    st.balloons()
                                    
                                    # Reset exam state
                                    st.session_state.exam_active = False
                                    st.session_state.selected_exam_id = None
                                    st.session_state.student_answers = {}
                                    st.session_state.exam_start_time = None
                                    st.session_state.auto_submitted = False
                                    
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to submit exam")
                            except Exception as e:
                                st.error(f"❌ Error submitting exam: {str(e)}")
                    
                    # Auto-refresh every second for timer update (only if not in form submission)
                    if "submitted" not in st.session_state:
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("❌ Failed to load exam")
            except Exception as e:
                st.error(f"❌ Connection error: {str(e)}")
        else:
            st.info("📭 Select an exam from the 'Available Exams' tab to start.")
            st.markdown("""
            ### How to take an exam:
            1. ✅ Go to **Available Exams** tab
            2. 🔍 Find and review your scheduled exam
            3. 🚀 Click **Start Exam** button
            4. 🔐 Complete the D-CAPTCHA verification
            5. 📝 Answer all MCQ questions in the exam monitoring view
            6. ⏰ Keep an eye on the timer
            7. ✅ Click **Submit Exam** when done
            """)
            
            # Option to reset if exam state is stuck
            if st.session_state.selected_exam_id:
                st.divider()
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("🔄 Reset to Available Exams", type="secondary"):
                        st.session_state.exam_active = False
                        st.session_state.selected_exam_id = None
                        st.session_state.liveness_step = None
                        st.session_state.exam_start_time = None
                        st.session_state.student_answers = {}
                        st.session_state.auto_submitted = False
                        st.rerun()