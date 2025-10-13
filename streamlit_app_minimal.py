import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp
import numpy as np
from datetime import datetime, timedelta
from collections import Counter
import os

# Import our modules
try:
    from patient_registration import PatientRegistration
    from otp_service import OTPService
    from medical_history_reconciliation import get_medical_reconciliation
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Health Journal AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'stage' not in st.session_state:
    st.session_state.stage = 'auth'
if 'patient_id' not in st.session_state:
    st.session_state.patient_id = None
if 'patient_records' not in st.session_state:
    st.session_state.patient_records = None
if 'auth_method' not in st.session_state:
    st.session_state.auth_method = 'patient_id'
if 'otp_verified' not in st.session_state:
    st.session_state.otp_verified = False
if 'show_share_modal' not in st.session_state:
    st.session_state.show_share_modal = False
if 'uploaded_documents' not in st.session_state:
    st.session_state.uploaded_documents = []

# Initialize services
patient_reg = PatientRegistration()
otp_service = OTPService()

# Main application
def main():
    st.title("🏥 Health Journal AI")
    st.markdown("Comprehensive Health Management System")
    
    # Authentication Stage
    if st.session_state.stage == 'auth':
        st.header("🔐 Patient Authentication")
        
        # Authentication method selection
        auth_method = st.radio(
            "Select authentication method:",
            ["Patient ID / UHID / MRN", "ABHA ID", "Phone Number (OTP)"],
            key="auth_method_radio"
        )
        
        if auth_method == "Phone Number (OTP)":
            phone = st.text_input("Enter phone number:", placeholder="+91 9876543210")
            
            if st.button("Send OTP"):
                if phone:
                    otp_service.send_otp(phone)
                    st.success("OTP sent! Use 123456 for demo.")
                    st.session_state.otp_verified = True
                    st.session_state.auth_method = 'phone'
                else:
                    st.error("Please enter a phone number")
            
            if st.session_state.otp_verified:
                otp = st.text_input("Enter OTP:", placeholder="123456")
                if st.button("Verify OTP"):
                    if otp == "123456":
                        st.success("OTP verified successfully!")
                        st.session_state.stage = 'patient_info'
                        st.rerun()
                    else:
                        st.error("Invalid OTP")
        else:
            identifier = st.text_input(f"Enter {auth_method}:", placeholder="GEN10001")
            
            if st.button("Login"):
                if identifier:
                    # Determine identifier type
                    if auth_method == "Patient ID / UHID / MRN":
                        identifier_type = 'auto'
                    elif auth_method == "ABHA ID":
                        identifier_type = 'abha'
                    else:
                        identifier_type = 'patient_id'
                    
                    # Check if patient exists
                    patient_data = patient_reg.check_patient_exists(identifier, identifier_type)
                    
                    if patient_data:
                        st.session_state.patient_records = patient_data
                        st.session_state.patient_id = patient_data.get('Patient ID', identifier)
                        st.session_state.auth_method = identifier_type
                        st.session_state.stage = 'patient_info'
                        st.rerun()
                    else:
                        st.error("Patient not found. Please check your ID or register as a new patient.")
                        if st.button("Register New Patient"):
                            st.session_state.stage = 'registration'
                            st.rerun()
                else:
                    st.error("Please enter a valid identifier")
    
    # Patient Information Stage
    elif st.session_state.stage == 'patient_info':
        st.header("👤 Patient Information")
        
        if st.session_state.patient_records:
            patient = st.session_state.patient_records
            
            # Basic Information
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Patient ID", patient.get('Patient ID', 'N/A'))
            with col2:
                st.metric("Name", patient.get('Name', 'N/A'))
            with col3:
                st.metric("Age", patient.get('Age', 'N/A'))
            
            # Medical History
            st.subheader("📋 Medical History")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Allergies:**", patient.get('Drug Allergies', 'None'))
                st.write("**Current Medications:**", patient.get('Current Medications', 'None'))
            
            with col2:
                st.write("**Past Medical History:**", patient.get('Past Medical History', 'None'))
                st.write("**Recent Procedures:**", patient.get('Recent Procedures', 'None'))
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📊 Generate Insights"):
                    st.session_state.stage = 'insights'
                    st.rerun()
            with col2:
                if st.button("📝 Add Symptoms"):
                    st.session_state.stage = 'symptoms'
                    st.rerun()
            with col3:
                if st.button("⬅️ Back to Login"):
                    st.session_state.stage = 'auth'
                    st.rerun()
    
    # Symptoms Stage
    elif st.session_state.stage == 'symptoms':
        st.header("📝 Symptom Assessment")
        
        symptoms = st.multiselect(
            "Select your symptoms:",
            ["Fever", "Headache", "Cough", "Fatigue", "Nausea", "Dizziness", "Chest Pain", "Shortness of Breath"]
        )
        
        severity = st.select_slider("Overall Severity:", options=["Mild", "Moderate", "Severe"])
        
        if st.button("📊 Generate Insights"):
            st.session_state.stage = 'insights'
            st.rerun()
        
        if st.button("⬅️ Back to Patient Info"):
            st.session_state.stage = 'patient_info'
            st.rerun()
    
    # Insights Dashboard Stage
    elif st.session_state.stage == 'insights':
        st.header("📊 Patient 360 Insights Dashboard")
        
        if st.session_state.patient_records:
            patient = st.session_state.patient_records
            
            # Patient header
            st.subheader(f"👤 {patient.get('Name', 'Patient')} - Patient ID: {st.session_state.patient_id}")
            
            # Create tabs
            tab1, tab2, tab3, tab4 = st.tabs(["🏥 Medical Overview", "💊 Medications", "⚠️ Allergies", "👤 Avatar Journaling"])
            
            with tab1:
                st.subheader("Medical Overview")
                
                # Medical conditions
                conditions = patient.get('Past Medical History', 'None')
                st.write("**Medical Conditions:**", conditions)
                
                # Recent procedures
                procedures = patient.get('Recent Procedures', 'None')
                st.write("**Recent Procedures:**", procedures)
                
                # Health metrics chart
                dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='D')
                weight = 75 - np.cumsum(np.random.normal(0.1, 0.3, len(dates)))
                
                fig = px.line(x=dates, y=weight, title="Weight Trend")
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                st.subheader("Medication Management")
                
                medications = patient.get('Current Medications', 'None')
                st.write("**Current Medications:**", medications)
                
                # Medication adherence gauge
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = 76.5,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Adherence %"},
                    gauge = {'axis': {'range': [None, 100]},
                            'bar': {'color': "darkblue"},
                            'steps': [{'range': [0, 50], 'color': "lightgray"},
                                    {'range': [50, 100], 'color': "gray"}],
                            'threshold': {'line': {'color': "red", 'width': 4},
                                        'thickness': 0.75, 'value': 90}}))
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                st.subheader("Allergies & Risk Assessment")
                
                allergies = patient.get('Drug Allergies', 'None')
                st.write("**Known Allergies:**", allergies)
                
                # Risk assessment
                risk_factors = ["Drug Interactions", "Allergic Reactions", "Side Effects"]
                risk_scores = [75, 60, 45]
                
                fig = px.bar(x=risk_factors, y=risk_scores, title="Risk Assessment")
                st.plotly_chart(fig, use_container_width=True)
            
            with tab4:
                st.subheader("👤 Avatar Journaling - Human Body Health Tracker")
                st.write("Click on body parts to view health data and add information")
                
                # Human Body Visual Representation
                st.markdown("### 🫀 Human Body Map")
                
                # Create a more visible human body representation
                st.markdown("""
                <div style="text-align: center; font-family: monospace; font-size: 18px; line-height: 1.3; background-color: #f8f9fa; padding: 25px; border-radius: 15px; border: 3px solid #007bff; margin: 20px 0;">
                <pre style="margin: 0; font-size: 16px;">
                           🧠 HEAD
                          /   \\
                         /     \\
                    🦴---🫁---🦴
                   /  CHEST   \\
                  💪           💪
                 /  ARMS       \\
                /               \\
               /                 \\
              /                   \\
             /                     \\
            /                       \\
           /                         \\
          /                           \\
         /                             \\
        /                               \\
       /                                 \\
      /                                   \\
     /                                     \\
    /                                       \\
   /                                         \\
  /                                           \\
 /                                             \\
/                                               \\
🦵 LEGS                                        🦵
                </pre>
                </div>
                """, unsafe_allow_html=True)
                
                # Add organ locations
                st.markdown("#### 🫀 Organ Locations")
                st.markdown("""
                <div style="text-align: center; font-family: monospace; font-size: 16px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 20px; border-radius: 12px; border: 2px solid #2196f3; margin: 15px 0;">
                <strong style="font-size: 18px; color: #1976d2;">ORGANS LOCATION:</strong><br><br>
                <span style="font-size: 20px;">❤️ Heart</span>    <span style="font-size: 20px;">🫁 Lungs</span>    <span style="font-size: 20px;">🫀 Liver</span>    <span style="font-size: 20px;">🫄 Stomach</span><br>
                <span style="font-size: 20px;">🫘 Kidneys</span>  <span style="font-size: 20px;">🫀 Bladder</span>  <span style="font-size: 20px;">🧠 Brain</span>    <span style="font-size: 20px;">🦴 Shoulders</span><br>
                <span style="font-size: 20px;">💪 Arms</span>     <span style="font-size: 20px;">🦵 Legs</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Body part selection with hover-like preview
                st.markdown("#### 🎯 Click on Body Parts to View Health Data")
                
                # Create a more organized body part selection
                st.markdown("**Select a body part to view detailed health information:**")
                
                # Create body part buttons in a more organized layout
                col1, col2, col3, col4, col5 = st.columns(5)
                
                # Row 1: Head
                with col3:
                    if st.button("🧠 Head", key="head_btn", use_container_width=True, help="Click to view head health data"):
                        st.session_state.selected_body_part = "head"
                        st.rerun()
                
                # Row 2: Shoulders and Chest
                with col1:
                    if st.button("🦴 Left Shoulder", key="l_shoulder_btn", use_container_width=True, help="Click to view left shoulder health data"):
                        st.session_state.selected_body_part = "left_shoulder"
                        st.rerun()
                with col3:
                    if st.button("🫁 Chest", key="chest_btn", use_container_width=True, help="Click to view chest health data"):
                        st.session_state.selected_body_part = "chest"
                        st.rerun()
                with col5:
                    if st.button("🦴 Right Shoulder", key="r_shoulder_btn", use_container_width=True, help="Click to view right shoulder health data"):
                        st.session_state.selected_body_part = "right_shoulder"
                        st.rerun()
                
                # Row 3: Arms
                with col1:
                    if st.button("💪 Left Arm", key="l_arm_btn", use_container_width=True, help="Click to view left arm health data"):
                        st.session_state.selected_body_part = "left_arm"
                        st.rerun()
                with col5:
                    if st.button("💪 Right Arm", key="r_arm_btn", use_container_width=True, help="Click to view right arm health data"):
                        st.session_state.selected_body_part = "right_arm"
                        st.rerun()
                
                # Row 4: Torso Organs
                with col1:
                    if st.button("❤️ Heart", key="heart_btn", use_container_width=True, help="Click to view heart health data"):
                        st.session_state.selected_body_part = "heart"
                        st.rerun()
                with col2:
                    if st.button("🫁 Lungs", key="lungs_btn", use_container_width=True, help="Click to view lungs health data"):
                        st.session_state.selected_body_part = "lungs"
                        st.rerun()
                with col4:
                    if st.button("🫀 Liver", key="liver_btn", use_container_width=True, help="Click to view liver health data"):
                        st.session_state.selected_body_part = "liver"
                        st.rerun()
                with col5:
                    if st.button("🫀 Bladder", key="bladder_btn", use_container_width=True, help="Click to view bladder health data"):
                        st.session_state.selected_body_part = "bladder"
                        st.rerun()
                
                # Row 5: Abdomen
                with col2:
                    if st.button("🫄 Stomach", key="stomach_btn", use_container_width=True, help="Click to view stomach health data"):
                        st.session_state.selected_body_part = "stomach"
                        st.rerun()
                with col4:
                    if st.button("🫘 Kidneys", key="kidneys_btn", use_container_width=True, help="Click to view kidneys health data"):
                        st.session_state.selected_body_part = "kidneys"
                        st.rerun()
                
                # Row 6: Legs
                with col2:
                    if st.button("🦵 Left Leg", key="l_leg_btn", use_container_width=True, help="Click to view left leg health data"):
                        st.session_state.selected_body_part = "left_leg"
                        st.rerun()
                with col4:
                    if st.button("🦵 Right Leg", key="r_leg_btn", use_container_width=True, help="Click to view right leg health data"):
                        st.session_state.selected_body_part = "right_leg"
                        st.rerun()
                
                # Add a visual separator
                st.markdown("---")
                
                # Add a preview section that shows data for the currently hovered/selected part
                st.markdown("#### 📊 Body Part Health Preview")
                
                # Show preview for all body parts
                body_parts_preview = {
                    "head": {"emoji": "🧠", "name": "Head", "score": "85%", "status": "🟢 Good", "details": "Memory: Good, Focus: Excellent"},
                    "chest": {"emoji": "🫁", "name": "Chest", "score": "78%", "status": "🟢 Good", "details": "Breathing: Normal, Capacity: Good"},
                    "heart": {"emoji": "❤️", "name": "Heart", "score": "88%", "status": "🟢 Excellent", "details": "BPM: 72, BP: 120/80"},
                    "lungs": {"emoji": "🫁", "name": "Lungs", "score": "82%", "status": "🟢 Good", "details": "Capacity: 4.2L, O2 Sat: 98%"},
                    "liver": {"emoji": "🫀", "name": "Liver", "score": "90%", "status": "🟢 Excellent", "details": "Enzymes: Normal, Function: Excellent"},
                    "stomach": {"emoji": "🫄", "name": "Stomach", "score": "75%", "status": "🟡 Fair", "details": "Digestion: Good, pH: Normal"},
                    "kidneys": {"emoji": "🫘", "name": "Kidneys", "score": "85%", "status": "🟢 Good", "details": "GFR: 95, Creatinine: Normal"},
                    "left_arm": {"emoji": "💪", "name": "Left Arm", "score": "80%", "status": "🟢 Good", "details": "Strength: Good, Flexibility: Fair"},
                    "right_arm": {"emoji": "💪", "name": "Right Arm", "score": "80%", "status": "🟢 Good", "details": "Strength: Good, Flexibility: Fair"},
                    "left_leg": {"emoji": "🦵", "name": "Left Leg", "score": "77%", "status": "🟡 Fair", "details": "Strength: Good, Circulation: Fair"},
                    "right_leg": {"emoji": "🦵", "name": "Right Leg", "score": "77%", "status": "🟡 Fair", "details": "Strength: Good, Circulation: Fair"},
                    "left_shoulder": {"emoji": "🦴", "name": "Left Shoulder", "score": "72%", "status": "🟡 Fair", "details": "Flexibility: Good, Tension: Low"},
                    "right_shoulder": {"emoji": "🦴", "name": "Right Shoulder", "score": "72%", "status": "🟡 Fair", "details": "Flexibility: Good, Tension: Low"},
                    "bladder": {"emoji": "🫀", "name": "Bladder", "score": "83%", "status": "🟢 Good", "details": "Function: Normal, Capacity: Good"}
                }
                
                # Display all body parts in a grid for easy preview
                st.markdown("**Quick Health Overview - Click any part above for detailed view:**")
                
                # Create a more visible grid of all body parts
                cols = st.columns(7)
                for i, (part_key, part_data) in enumerate(body_parts_preview.items()):
                    with cols[i % 7]:
                        st.markdown(f"""
                        <div style="text-align: center; padding: 12px; border: 2px solid #007bff; border-radius: 10px; margin: 3px; background: linear-gradient(135deg, #e3f2fd 0%, #f8f9fa 100%); box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="font-size: 24px; margin-bottom: 5px;">{part_data['emoji']}</div>
                            <div style="font-size: 11px; font-weight: bold; color: #2c3e50; margin-bottom: 3px;">{part_data['name']}</div>
                            <div style="font-size: 14px; color: #28a745; font-weight: bold; margin-bottom: 2px;">{part_data['score']}</div>
                            <div style="font-size: 11px; color: #6c757d;">{part_data['status']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Display selected body part information
                selected_part = st.session_state.get('selected_body_part', None)
                
                if selected_part:
                    st.markdown("---")
                    st.subheader(f"📊 {selected_part.replace('_', ' ').title()} Health Data")
                    
                    # Body part specific data
                    body_part_data = {
                        "head": {"score": "85", "details": "Memory: Good, Focus: Excellent, Sleep: 7.5hrs", "color": "🟢"},
                        "chest": {"score": "78", "details": "Breathing: Normal, Capacity: Good, Pain: None", "color": "🟢"},
                        "heart": {"score": "88", "details": "BPM: 72, BP: 120/80, Rhythm: Regular", "color": "🟢"},
                        "lungs": {"score": "82", "details": "Capacity: 4.2L, O2 Sat: 98%, Function: Good", "color": "🟢"},
                        "liver": {"score": "90", "details": "Enzymes: Normal, Function: Excellent, Toxins: Low", "color": "🟢"},
                        "stomach": {"score": "75", "details": "Digestion: Good, pH: Normal, Discomfort: None", "color": "🟡"},
                        "kidneys": {"score": "85", "details": "GFR: 95, Creatinine: Normal, Function: Good", "color": "🟢"},
                        "left_arm": {"score": "80", "details": "Strength: Good, Flexibility: Fair, Pain: None", "color": "🟢"},
                        "right_arm": {"score": "80", "details": "Strength: Good, Flexibility: Fair, Pain: None", "color": "🟢"},
                        "left_leg": {"score": "77", "details": "Strength: Good, Circulation: Fair, Pain: Mild", "color": "🟡"},
                        "right_leg": {"score": "77", "details": "Strength: Good, Circulation: Fair, Pain: Mild", "color": "🟡"},
                        "left_shoulder": {"score": "72", "details": "Flexibility: Good, Tension: Low, Posture: Fair", "color": "🟡"},
                        "right_shoulder": {"score": "72", "details": "Flexibility: Good, Tension: Low, Posture: Fair", "color": "🟡"},
                        "bladder": {"score": "83", "details": "Function: Normal, Capacity: Good, No Issues", "color": "🟢"}
                    }
                    
                    if selected_part in body_part_data:
                        data = body_part_data[selected_part]
                        
                        # Display health information
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Health Score", f"{data['score']}%")
                        with col2:
                            st.metric("Status", data['color'])
                        with col3:
                            st.metric("Last Check", "2 days ago")
                        
                        st.info(f"**Details:** {data['details']}")
                        
                        # Action buttons for the selected body part
                        st.subheader("📝 Actions")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if st.button("💊 Add Medication", key=f"med_{selected_part}"):
                                st.success(f"💊 Medication form for {selected_part.replace('_', ' ').title()}")
                        
                        with col2:
                            if st.button("⚠️ Add Symptom", key=f"symptom_{selected_part}"):
                                st.success(f"⚠️ Symptom form for {selected_part.replace('_', ' ').title()}")
                        
                        with col3:
                            if st.button("📊 View Trends", key=f"trends_{selected_part}"):
                                st.success(f"📊 Trends for {selected_part.replace('_', ' ').title()}")
                        
                        with col4:
                            if st.button("📋 View History", key=f"history_{selected_part}"):
                                st.success(f"📋 History for {selected_part.replace('_', ' ').title()}")
                        
                        # Quick health form
                        with st.expander("📝 Quick Health Log", expanded=False):
                            with st.form(f"health_form_{selected_part}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    pain_level = st.select_slider("Pain Level", options=["None", "Mild", "Moderate", "Severe"])
                                    energy_level = st.select_slider("Energy Level", options=["Low", "Fair", "Good", "High"])
                                with col2:
                                    notes = st.text_area("Notes", placeholder="Any additional observations...")
                                    submit = st.form_submit_button("Save Health Log")
                                    
                                    if submit:
                                        st.success(f"✅ Health log saved for {selected_part.replace('_', ' ').title()}")
                
                else:
                    st.info("👆 Click on any body part above to view its health data and add information")
                
                # Overall health summary
                st.markdown("---")
                st.subheader("📊 Overall Health Summary")
                
                # Health metrics grid
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Overall Score", "82%", "↗️ +5%")
                with col2:
                    st.metric("Active Issues", "2", "↘️ -1")
                with col3:
                    st.metric("Medications", "3", "→ 0")
                with col4:
                    st.metric("Last Checkup", "2 days", "→ 0")
                
                # Recent activity
                st.subheader("📅 Recent Activity")
                activity_data = [
                    {"date": "Today", "activity": "💊 Took morning medication", "body_part": "Heart"},
                    {"date": "Yesterday", "activity": "⚠️ Mild headache reported", "body_part": "Head"},
                    {"date": "2 days ago", "activity": "📊 Health checkup completed", "body_part": "Overall"},
                    {"date": "3 days ago", "activity": "💪 Exercise session logged", "body_part": "Legs"}
                ]
                
                for activity in activity_data:
                    st.write(f"**{activity['date']}:** {activity['activity']} ({activity['body_part']})")
                
                # Health progress tracking
                st.subheader("📊 Health Progress Over Time")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**3 Months Ago:**")
                    st.write("⚖️ Weight: 75kg")
                    st.write("🩸 BP: 140/90")
                    st.write("⚡ Energy: Low")
                
                with col2:
                    st.write("**Now:**")
                    st.write("⚖️ Weight: 70kg")
                    st.write("🩸 BP: 120/80")
                    st.write("⚡ Energy: High")
                
                st.success("📈 Overall Health Improvement: 75% Better")
            
            # Action buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⬅️ Back to Symptoms"):
                    st.session_state.stage = 'symptoms'
                    st.rerun()
            with col2:
                if st.button("📄 Generate Summary Report"):
                    st.session_state.stage = 'summary'
                    st.rerun()
            with col3:
                if st.button("🔄 Refresh Dashboard"):
                    st.rerun()
    
    # Summary Stage
    elif st.session_state.stage == 'summary':
        st.header("📄 Health Summary Report")
        
        if st.session_state.patient_records:
            patient = st.session_state.patient_records
            
            st.write(f"**Patient:** {patient.get('Name', 'N/A')}")
            st.write(f"**Patient ID:** {st.session_state.patient_id}")
            st.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")
            
            st.subheader("Medical Summary")
            st.write("**Allergies:**", patient.get('Drug Allergies', 'None'))
            st.write("**Medications:**", patient.get('Current Medications', 'None'))
            st.write("**History:**", patient.get('Past Medical History', 'None'))
            
            if st.button("⬅️ Back to Dashboard"):
                st.session_state.stage = 'insights'
                st.rerun()
    
    # Registration Stage
    elif st.session_state.stage == 'registration':
        st.header("📝 New Patient Registration")
        st.info("Registration form would be implemented here")
        
        if st.button("⬅️ Back to Login"):
            st.session_state.stage = 'auth'
            st.rerun()

if __name__ == "__main__":
    main()
