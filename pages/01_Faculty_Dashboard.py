"""
Faculty Dashboard for D-CAPTCHA System
Create and manage question papers with MCQs
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Faculty Dashboard", layout="wide", initial_sidebar_state="expanded")

# Check if user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("❌ Please login first")
    st.stop()

# Check if user is faculty
if st.session_state.role != "faculty":
    st.error("❌ Only faculty members can access this page")
    st.stop()

st.title("📚 Faculty Dashboard")
st.markdown(f"Welcome, **{st.session_state.name}**")

# Sidebar navigation
page = st.sidebar.selectbox(
    "📋 Navigation",
    ["Create Question Paper", "Manage Papers", "Schedule Exam", "View Analytics"]
)

# ============================================================================
# CREATE QUESTION PAPER
# ============================================================================
if page == "Create Question Paper":
    st.header("✏️ Create New Question Paper")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        paper_name = st.text_input("📝 Paper Name", placeholder="e.g., Midterm Exam 2026")
        subject = st.text_input("📚 Subject", placeholder="e.g., Data Structures")
        total_marks = st.number_input("⭐ Total Marks", min_value=10, max_value=500, value=100, step=10)
    
    with col2:
        duration_minutes = st.number_input("⏱️ Exam Duration (Minutes)", min_value=15, max_value=480, value=60, step=15)
        st.info(f"📊 Duration: **{duration_minutes} minutes**")
    
    if st.button("✅ Create Question Paper", key="create_paper", type="primary"):
        if not paper_name or not subject:
            st.error("❌ Please fill in all required fields")
        else:
            try:
                token = st.session_state.get('token', '')
                print(f"DEBUG FACULTY: Token from session_state")
                print(f"DEBUG FACULTY: Token type: {type(token)}")
                print(f"DEBUG FACULTY: Token length: {len(token)}")
                print(f"DEBUG FACULTY: Token first 30 chars: {token[:30] if token else 'EMPTY'}")
                
                headers = {"Authorization": f"Bearer {token}"}
                print(f"DEBUG FACULTY: Authorization header: {headers['Authorization'][:50]}...")
                
                response = requests.post(
                    f"{API_URL}/faculty/create-question-paper",
                    json={
                        "paper_name": paper_name,
                        "subject": subject,
                        "total_marks": total_marks,
                        "duration_minutes": duration_minutes
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ {data['message']}")
                    st.info(f"📝 **Paper ID: {data['paper_id']}**")
                    st.session_state.current_paper_id = data['paper_id']
                    st.rerun()
                else:
                    st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"❌ Connection error: {str(e)}")
    
    # Add Questions Section
    if "current_paper_id" in st.session_state:
        st.divider()
        st.subheader(f"📝 Add Questions to Paper ID: {st.session_state.current_paper_id}")
        
        with st.form("add_question_form"):
            question_text = st.text_area("❓ Question Text", placeholder="Enter the question...")
            
            col1, col2 = st.columns(2)
            with col1:
                option_a = st.text_input("Option A:", placeholder="Answer A")
                option_c = st.text_input("Option C:", placeholder="Answer C")
            with col2:
                option_b = st.text_input("Option B:", placeholder="Answer B")
                option_d = st.text_input("Option D:", placeholder="Answer D")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                correct_option = st.selectbox("✔️ Correct Answer", ["A", "B", "C", "D"], key="correct_select")
            with col2:
                marks = st.number_input("⭐ Marks", min_value=1, max_value=100, value=1)
            
            submitted = st.form_submit_button("➕ Add Question", type="primary")
            
            if submitted:
                if not question_text or not all([option_a, option_b, option_c, option_d]):
                    st.error("❌ Please complete all fields")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/faculty/add-question",
                            json={
                                "paper_id": st.session_state.current_paper_id,
                                "question_text": question_text,
                                "option_a": option_a,
                                "option_b": option_b,
                                "option_c": option_c,
                                "option_d": option_d,
                                "correct_option": correct_option,
                                "marks": marks
                            },
                            headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.success(f"✅ {data['message']}")
                            st.balloons()
                        else:
                            st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")


# ============================================================================
# MANAGE PAPERS
# ============================================================================
elif page == "Manage Papers":
    st.header("📄 My Question Papers")
    
    try:
        response = requests.get(
            f"{API_URL}/faculty/question-papers",
            headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            papers = data["papers"]
            
            if papers:
                st.success(f"✅ Found {len(papers)} question paper(s)")
                for paper in papers:
                    with st.expander(f"📄 **{paper['paper_name']}** - {paper['subject']}", expanded=False):
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("⏱️ Duration", f"{paper['duration_minutes']} min")
                        col2.metric("⭐ Total Marks", paper['total_marks'])
                        col3.metric("❓ Questions", paper['total_questions'])
                        col4.metric("📅 Created", paper['created_at'][:10])
                        
                        st.divider()
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button(f"👁️ View Details", key=f"view_{paper['paper_id']}"):
                                st.session_state.view_paper_id = paper['paper_id']
                                st.rerun()
                        with col2:
                            if st.button(f"✏️ Edit", key=f"edit_{paper['paper_id']}"):
                                st.info("Edit functionality coming soon!")
                        with col3:
                            if st.button(f"🗑️ Delete", key=f"delete_{paper['paper_id']}"):
                                try:
                                    delete_response = requests.delete(
                                        f"{API_URL}/faculty/question-paper/{paper['paper_id']}",
                                        headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
                                    )
                                    if delete_response.status_code == 200:
                                        st.success("✅ Paper deleted successfully!")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
            else:
                st.info("📭 No question papers created yet. Create one to get started!")
        else:
            st.error("❌ Failed to fetch papers")
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")
    
    # View paper details
    if "view_paper_id" in st.session_state:
        st.divider()
        st.subheader("📋 Paper Details")
        
        try:
            response = requests.get(
                f"{API_URL}/faculty/question-paper/{st.session_state.view_paper_id}",
                headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
            )
            
            if response.status_code == 200:
                paper = response.json()["paper"]
                
                st.write(f"**Paper Name:** {paper['paper_name']}")
                st.write(f"**Subject:** {paper['subject']}")
                st.write(f"**Duration:** {paper['duration_minutes']} minutes")
                st.write(f"**Total Marks:** {paper['total_marks']}")
                st.write(f"**Total Questions:** {paper['total_questions']}")
                
                st.divider()
                st.subheader("📝 Questions")
                
                for idx, q in enumerate(paper['questions'], 1):
                    with st.expander(f"Q{idx}: {q['question_text'][:50]}..."):
                        st.write(f"**Marks:** {q['marks']}")
                        st.write(f"**Options:**")
                        st.write(f"  A) {q['options']['A']}")
                        st.write(f"  B) {q['options']['B']}")
                        st.write(f"  C) {q['options']['C']}")
                        st.write(f"  D) {q['options']['D']}")
                        st.write(f"**Correct Answer:** {q['correct_option']}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


# ============================================================================
# SCHEDULE EXAM
# ============================================================================
elif page == "Schedule Exam":
    st.header("📅 Schedule Exam for Students")
    
    try:
        response = requests.get(
            f"{API_URL}/faculty/question-papers",
            headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
        )
        
        if response.status_code == 200:
            papers = response.json()["papers"]
            
            if not papers:
                st.warning("⚠️ No question papers available. Create one first!")
            else:
                paper_options = {f"{p['paper_name']} ({p['subject']})" : p['paper_id'] for p in papers}
                
                with st.form("schedule_exam_form"):
                    selected_paper_name = st.selectbox("📄 Select Question Paper", list(paper_options.keys()))
                    selected_paper_id = paper_options[selected_paper_name]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        class_id = st.number_input("🏫 Class/Section ID", min_value=1, value=1)
                    with col2:
                        exam_date = st.date_input("📅 Exam Date", value=datetime.now() + timedelta(days=1))
                    with col3:
                        # Create time dropdown with 5-minute intervals
                        time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 5)]
                        current_time = datetime.now()
                        default_time = f"{current_time.hour:02d}:{(current_time.minute//5)*5:02d}"
                        selected_time_str = st.selectbox("🕐 Exam Start Time", time_options, index=time_options.index(default_time) if default_time in time_options else 0)
                    
                    submitted = st.form_submit_button("📅 Schedule Exam", type="primary")
                    
                    if submitted:
                        try:
                            response = requests.post(
                                f"{API_URL}/faculty/assign-exam",
                                json={
                                    "paper_id": selected_paper_id,
                                    "class_id": class_id,
                                    "scheduled_date": str(exam_date),
                                    "start_time": selected_time_str
                                },
                                headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
                            )
                            
                            if response.status_code == 200:
                                st.success("✅ Exam scheduled successfully!")
                                st.balloons()
                            else:
                                st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Connection error: {str(e)}")
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")


# ============================================================================
# VIEW ANALYTICS
# ============================================================================
elif page == "View Analytics":
    st.header("📊 Analytics & Reports")
    
    col1, col2, col3 = st.columns(3)
    
    try:
        response = requests.get(
            f"{API_URL}/faculty/question-papers",
            headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
        )
        
        if response.status_code == 200:
            papers = response.json()["papers"]
            
            with col1:
                st.metric("📄 Total Papers", len(papers))
            with col2:
                total_questions = sum(p['total_questions'] for p in papers)
                st.metric("❓ Total Questions", total_questions)
            with col3:
                total_marks = sum(p['total_marks'] for p in papers)
                st.metric("⭐ Total Marks", total_marks)
            
            st.divider()
            st.subheader("📈 Paper Statistics")
            
            for paper in papers:
                st.write(f"**{paper['paper_name']}** - {paper['subject']}")
                st.write(f"  - Questions: {paper['total_questions']}")
                st.write(f"  - Total Marks: {paper['total_marks']}")
                st.write(f"  - Duration: {paper['duration_minutes']} minutes")
                st.divider()
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")
