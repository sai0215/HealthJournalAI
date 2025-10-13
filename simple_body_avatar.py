import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Human Body Avatar",
    page_icon="🫀",
    layout="wide"
)

# Initialize session state
if 'selected_body_part' not in st.session_state:
    st.session_state.selected_body_part = None

def main():
    st.title("🫀 Human Body Avatar - Health Tracker")
    st.markdown("Click on body parts to view health data and add information")
    
    # Human Body Visual Representation
    st.markdown("### 🫀 Human Body Map")
    
    # Create a visual human body using ASCII art
    body_visual = """
    ```
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
    ```
    """
    st.code(body_visual, language="text")
    
    # Add a more detailed body map with organ locations
    st.markdown("#### 🫀 Detailed Body Map with Organ Locations")
    
    # Create a more detailed visual representation
    detailed_body = """
    ```
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

ORGANS LOCATION:
❤️ Heart    🫁 Lungs    🫀 Liver    🫄 Stomach
🫘 Kidneys  🫀 Bladder  🧠 Brain    🦴 Shoulders
💪 Arms     🦵 Legs
    ```
    """
    st.code(detailed_body, language="text")
    
    # Body part selection with hover-like preview
    st.markdown("#### 🎯 Click on Body Parts to View Health Data")
    
    # Create body part buttons in a grid layout
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Row 1: Head
    with col3:
        if st.button("🧠 Head", key="head_btn", use_container_width=True):
            st.session_state.selected_body_part = "head"
            st.rerun()
    
    # Row 2: Shoulders and Chest
    with col1:
        if st.button("🦴 Left Shoulder", key="l_shoulder_btn", use_container_width=True):
            st.session_state.selected_body_part = "left_shoulder"
            st.rerun()
    with col3:
        if st.button("🫁 Chest", key="chest_btn", use_container_width=True):
            st.session_state.selected_body_part = "chest"
            st.rerun()
    with col5:
        if st.button("🦴 Right Shoulder", key="r_shoulder_btn", use_container_width=True):
            st.session_state.selected_body_part = "right_shoulder"
            st.rerun()
    
    # Row 3: Arms
    with col1:
        if st.button("💪 Left Arm", key="l_arm_btn", use_container_width=True):
            st.session_state.selected_body_part = "left_arm"
            st.rerun()
    with col5:
        if st.button("💪 Right Arm", key="r_arm_btn", use_container_width=True):
            st.session_state.selected_body_part = "right_arm"
            st.rerun()
    
    # Row 4: Torso Organs
    with col1:
        if st.button("❤️ Heart", key="heart_btn", use_container_width=True):
            st.session_state.selected_body_part = "heart"
            st.rerun()
    with col2:
        if st.button("🫁 Lungs", key="lungs_btn", use_container_width=True):
            st.session_state.selected_body_part = "lungs"
            st.rerun()
    with col4:
        if st.button("🫀 Liver", key="liver_btn", use_container_width=True):
            st.session_state.selected_body_part = "liver"
            st.rerun()
    with col5:
        if st.button("🫀 Bladder", key="bladder_btn", use_container_width=True):
            st.session_state.selected_body_part = "bladder"
            st.rerun()
    
    # Row 5: Abdomen
    with col2:
        if st.button("🫄 Stomach", key="stomach_btn", use_container_width=True):
            st.session_state.selected_body_part = "stomach"
            st.rerun()
    with col4:
        if st.button("🫘 Kidneys", key="kidneys_btn", use_container_width=True):
            st.session_state.selected_body_part = "kidneys"
            st.rerun()
    
    # Row 6: Legs
    with col2:
        if st.button("🦵 Left Leg", key="l_leg_btn", use_container_width=True):
            st.session_state.selected_body_part = "left_leg"
            st.rerun()
    with col4:
        if st.button("🦵 Right Leg", key="r_leg_btn", use_container_width=True):
            st.session_state.selected_body_part = "right_leg"
            st.rerun()
    
    # Add a preview section that shows data for the currently hovered/selected part
    st.markdown("---")
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
    
    # Create a grid of all body parts
    cols = st.columns(7)
    for i, (part_key, part_data) in enumerate(body_parts_preview.items()):
        with cols[i % 7]:
            st.markdown(f"""
            <div style="text-align: center; padding: 8px; border: 1px solid #ddd; border-radius: 8px; margin: 2px; background-color: #f8f9fa;">
                <div style="font-size: 20px;">{part_data['emoji']}</div>
                <div style="font-size: 10px; font-weight: bold;">{part_data['name']}</div>
                <div style="font-size: 12px; color: #28a745;">{part_data['score']}</div>
                <div style="font-size: 10px;">{part_data['status']}</div>
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

if __name__ == "__main__":
    main()
