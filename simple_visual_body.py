import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Visual Human Body Avatar",
    page_icon="🫀",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
.stButton>button {
    width: 100%;
    border-radius: 10px;
    border: 2px solid #007bff;
    color: #007bff;
    background-color: #e0f2ff;
    padding: 15px 0;
    font-size: 16px;
    font-weight: bold;
    transition: all 0.3s ease;
}
.stButton>button:hover {
    background-color: #007bff;
    color: white;
    transform: scale(1.05);
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_body_part' not in st.session_state:
    st.session_state.selected_body_part = None

# Header
st.title("🫀 Visual Human Body Avatar")
st.markdown("**Interactive body map for detailed health tracking and journaling**")

# Human Body Visual
st.markdown("### 🫀 Human Body Map")
st.markdown("**Click on the body parts below to view health data:**")

# Large visual human body
st.markdown("""
<div style="text-align: center; font-family: monospace; font-size: 24px; line-height: 1.4; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 40px; border-radius: 25px; border: 5px solid #007bff; margin: 30px 0; box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
<pre style="margin: 0; font-size: 22px; color: #2c3e50;">
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

# Organ locations guide
st.markdown("#### 🫀 Organ Locations Guide")
st.markdown("""
<div style="text-align: center; font-family: monospace; font-size: 20px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 30px; border-radius: 20px; border: 4px solid #2196f3; margin: 25px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
<strong style="font-size: 24px; color: #1976d2;">ORGANS LOCATION:</strong><br><br>
<span style="font-size: 28px;">❤️ Heart</span>    <span style="font-size: 28px;">🫁 Lungs</span>    <span style="font-size: 28px;">🫀 Liver</span>    <span style="font-size: 28px;">🫄 Stomach</span><br>
<span style="font-size: 28px;">🫘 Kidneys</span>  <span style="font-size: 28px;">🫀 Bladder</span>  <span style="font-size: 28px;">🧠 Brain</span>    <span style="font-size: 28px;">🦴 Shoulders</span><br>
<span style="font-size: 28px;">💪 Arms</span>     <span style="font-size: 28px;">🦵 Legs</span>
</div>
""", unsafe_allow_html=True)

# Body part selection buttons
st.markdown("#### 🎯 Click on Body Parts to View Health Data")

# Create columns for body part buttons
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

# Health preview grid
st.markdown("---")
st.markdown("#### 📊 Body Part Health Preview")
st.markdown("**Quick Health Overview - Click any part above for detailed view:**")

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

# Create a more visible grid of all body parts
cols = st.columns(7)
for i, (part_key, part_data) in enumerate(body_parts_preview.items()):
    with cols[i % 7]:
        st.markdown(f"""
        <div style="text-align: center; padding: 18px; border: 4px solid #007bff; border-radius: 15px; margin: 8px; background: linear-gradient(135deg, #e3f2fd 0%, #f8f9fa 100%); box-shadow: 0 5px 15px rgba(0,0,0,0.2);">
            <div style="font-size: 32px; margin-bottom: 10px;">{part_data['emoji']}</div>
            <div style="font-size: 13px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;">{part_data['name']}</div>
            <div style="font-size: 18px; color: #28a745; font-weight: bold; margin-bottom: 5px;">{part_data['score']}</div>
            <div style="font-size: 13px; color: #6c757d;">{part_data['status']}</div>
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
    
    else:
        st.info("👆 Click on any body part above to view its health data and add information")

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
    st.markdown("**📅 3 Months Ago**")
    st.write("⚖️ Weight: 75kg")
    st.write("🩸 BP: 140/90")
    st.write("⚡ Energy: Low")
    st.write("🧠 Memory: Fair")
    st.write("❤️ Heart Rate: 85 BPM")

with col2:
    st.markdown("**🎯 Now**")
    st.write("⚖️ Weight: 70kg")
    st.write("🩸 BP: 120/80")
    st.write("⚡ Energy: High")
    st.write("🧠 Memory: Good")
    st.write("❤️ Heart Rate: 72 BPM")

st.success("📈 Overall Health Improvement: 75% Better")
