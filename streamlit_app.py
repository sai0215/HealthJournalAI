import streamlit as st
import json
import pandas as pd
import re
from datetime import datetime
from std_hub.llm import AgentProject
from openai import OpenAI
from project import project_init
import logging
import os
from dotenv import load_dotenv
from patient_registration import PatientRegistration, get_registration_form_data, validate_abha_id_format
from std_hub.db.mongodb import db_client
from otp_service import get_otp_service

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Page configuration
st.set_page_config(
    page_title="Health Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        height: 3rem;
        border-radius: 0.5rem;
        font-size: 1.1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        margin: 1rem 0;
    }
    h1 {
        color: #2c3e50;
    }
    h2 {
        color: #34495e;
    }
    </style>
""", unsafe_allow_html=True)

# Perplexity API Configuration from environment variables
API_KEY = os.environ.get("PERPLEXITY_API_KEY", "your_perplexity_api_key_here")
BASE_URL = os.environ.get("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")


@st.cache_resource
def initialize_project():
    """Initialize the project once"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    project = AgentProject()
    project = project_init(project)
    project.kickoff_id = "streamlit_session"
    return project


@st.cache_data
def load_patient_data():
    """Load patient data from Excel file"""
    try:
        df = pd.read_excel("Dummy Patient Data for OCR Use Case.xlsx")
        return df
    except Exception as e:
        logging.error(f"Error loading patient data: {e}")
        return pd.DataFrame()


def serialize_patient_info(patient_info):
    """Convert datetime objects to strings for serialization and calculate age"""
    serializable_info = {}
    for key, value in patient_info.items():
        if isinstance(value, datetime):
            serializable_info[key] = value.isoformat()
        elif pd.isna(value):
            serializable_info[key] = "N/A"
        else:
            serializable_info[key] = value

    # Calculate age from DOB if available
    dob = patient_info.get('DOB')
    if pd.notna(dob) and dob:
        if isinstance(dob, str):
            dob = datetime.strptime(dob, '%Y-%m-%d')
        age = datetime.now().year - dob.year
        serializable_info['Age'] = age

    return serializable_info


def recommend_diagnostic_tests(symptoms):
    """Recommend diagnostic tests based on symptoms"""
    recommendations = []

    if not symptoms:
        return ["No significant symptom changes reported. Monitor patient."]

    symptoms_lower = symptoms.lower()

    if "fever" in symptoms_lower:
        recommendations.append(
            "🔬 CBC (Complete Blood Count) for fever pattern")
    if "cough" in symptoms_lower:
        recommendations.append("🫁 Chest X-Ray for persistent cough")
    if "fatigue" in symptoms_lower:
        recommendations.append("🧪 Thyroid function and iron panel tests")
    if "headache" in symptoms_lower:
        recommendations.append("🧠 Neurological exam or CT scan")
    if "pain" in symptoms_lower:
        recommendations.append("📊 Pain location-specific imaging or labs")
    if "chest pain" in symptoms_lower or "chest" in symptoms_lower:
        recommendations.append("❤️ ECG and cardiac enzyme tests")
    if "breathing" in symptoms_lower or "breath" in symptoms_lower:
        recommendations.append("🌬️ Pulmonary function tests")

    return recommendations if recommendations else ["General health screening recommended"]


# Initialize session state
if 'stage' not in st.session_state:
    st.session_state.stage = 'welcome'
if 'patient_id' not in st.session_state:
    st.session_state.patient_id = None
if 'patient_records' not in st.session_state:
    st.session_state.patient_records = None
if 'additional_info' not in st.session_state:
    st.session_state.additional_info = ""
if 'symptom_changes' not in st.session_state:
    st.session_state.symptom_changes = ""
if 'final_summary' not in st.session_state:
    st.session_state.final_summary = None
if 'registration_data' not in st.session_state:
    st.session_state.registration_data = get_registration_form_data()
if 'show_registration' not in st.session_state:
    st.session_state.show_registration = False
if 'auth_method' not in st.session_state:
    st.session_state.auth_method = 'patient_id'
if 'otp_verified' not in st.session_state:
    st.session_state.otp_verified = False
if 'otp_phone' not in st.session_state:
    st.session_state.otp_phone = None

# Load data
project = initialize_project()
patient_data = load_patient_data()

# Initialize patient registration system and OTP service
patient_registration = PatientRegistration(db_client)
otp_service = get_otp_service()

# Sidebar
with st.sidebar:
    st.title("🏥 Health Assistant")
    st.markdown("---")

    # Progress indicator
    stages = {
        'welcome': '1️⃣ Patient ID',
        'registration': '🆕 Registration',
        'patient_info': '2️⃣ Health Info',
        'symptoms': '3️⃣ Symptoms',
        'summary': '4️⃣ Summary'
    }

    st.subheader("Progress")
    for stage_key, stage_name in stages.items():
        if st.session_state.stage == stage_key:
            st.markdown(f"**➤ {stage_name}**")
        else:
            st.markdown(f"　 {stage_name}")

    st.markdown("---")
    st.info("📊 **Total Patients:** " + str(len(patient_data)))

    if st.button("🔄 Reset Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # Reinitialize default session state
        st.session_state.stage = 'welcome'
        st.session_state.auth_method = 'patient_id'
        st.session_state.otp_verified = False
        st.session_state.otp_phone = None
        st.rerun()

# Main content
if st.session_state.stage == 'welcome':
    st.title("🏥 Welcome to Health Assistant")
    st.markdown("### Your AI-Powered Healthcare Companion")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <div class="info-box">
        <h4>How it works:</h4>
        <ol>
            <li><strong>Enter Patient ID:</strong> Provide your Patient ID or UHID</li>
            <li><strong>Review Records:</strong> We'll fetch your medical history</li>
            <li><strong>Share Symptoms:</strong> Tell us about any new symptoms</li>
            <li><strong>Get Recommendations:</strong> Receive personalized test suggestions</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Authentication method selection
        st.subheader("🔐 Patient Authentication")
        
        # Authentication method selector
        auth_options = ["Patient ID / UHID / MRN", "ABHA ID", "Phone Number (OTP)"]
        auth_values = ["patient_id", "abha", "phone"]
        
        # Get current index based on session state
        try:
            current_index = auth_values.index(st.session_state.auth_method)
        except ValueError:
            current_index = 0  # Default to first option
        
        auth_method = st.radio(
            "Select authentication method:",
            auth_options,
            index=current_index
        )
        
        # Update session state
        selected_index = auth_options.index(auth_method)
        st.session_state.auth_method = auth_values[selected_index]

        st.markdown("---")

        # Dynamic input based on authentication method
        if st.session_state.auth_method == 'phone':
            # Phone number authentication with OTP
            st.subheader("📱 Phone Number Authentication")
            
            if not st.session_state.otp_verified:
                phone_input = st.text_input(
                    "Phone Number",
                    placeholder="Enter your 10-digit mobile number",
                    help="Enter your registered mobile number"
                )
                
                col_otp1, col_otp2 = st.columns(2)
                
                with col_otp1:
                    if st.button("📤 Send OTP"):
                        if phone_input and len(phone_input) == 10 and phone_input.isdigit():
                            with st.spinner("Sending OTP..."):
                                success, otp_code, response = otp_service.generate_otp(phone_input)
                            
                            if success:
                                st.session_state.otp_phone = phone_input
                                st.success(f"✅ OTP sent to {phone_input}")
                                st.rerun()
                            else:
                                st.error(f"❌ {response.get('error', 'Failed to send OTP')}")
                        else:
                            st.warning("⚠️ Please enter a valid 10-digit phone number")
                
                with col_otp2:
                    if st.button("🔄 Reset"):
                        st.session_state.otp_phone = None
                        st.session_state.otp_verified = False
                        st.rerun()
                
                # OTP verification
                if st.session_state.otp_phone:
                    st.markdown("---")
                    st.subheader("🔑 Enter OTP")
                    otp_input = st.text_input(
                        "OTP Code",
                        placeholder="Enter 6-digit OTP",
                        help="Enter the OTP sent to your phone"
                    )
                    
                    if st.button("✅ Verify OTP"):
                        if otp_input and len(otp_input) == 6 and otp_input.isdigit():
                            with st.spinner("Verifying OTP..."):
                                verified, response = otp_service.verify_otp(st.session_state.otp_phone, otp_input)
                            
                            if verified:
                                st.session_state.otp_verified = True
                                st.success("✅ OTP verified successfully!")
                                
                                # Automatically proceed to patient lookup
                                with st.spinner("Looking up patient records..."):
                                    exists, patient_data_found = patient_registration.check_patient_exists(
                                        st.session_state.otp_phone, 'phone')
                                
                                if exists:
                                    st.session_state.patient_id = patient_data_found.get('Patient ID')
                                    st.session_state.patient_records = patient_data_found
                                    st.session_state.stage = 'patient_info'
                                    st.rerun()
                                else:
                                    st.error("❌ No patient record found for this phone number. Please register as a new patient.")
                                    st.session_state.show_registration = True
                                    st.rerun()
                            else:
                                st.error(f"❌ {response.get('error', 'OTP verification failed')}")
                        else:
                            st.warning("⚠️ Please enter a valid 6-digit OTP")
            
        else:
            # Other authentication methods
            if st.session_state.auth_method == 'patient_id':
                st.subheader("🆔 Patient ID / UHID / MRN")
                identifier_input = st.text_input(
                    "Patient ID / UHID / MRN",
                    placeholder="e.g., GEN10001, REG2025010112345678, MRN20250101ABC123...",
                    help="Enter your Patient ID, UHID, or Medical Record Number"
                )
            elif st.session_state.auth_method == 'abha':
                st.subheader("🆔 ABHA ID")
                identifier_input = st.text_input(
                    "ABHA ID",
                    placeholder="Enter your 14-digit ABHA ID",
                    help="Enter your Ayushman Bharat Health Account ID"
                )

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("Continue ➡️"):
                    if identifier_input:
                        # Check if patient exists
                        # For patient_id method, use auto-detection to check both Patient ID and MRN
                        if st.session_state.auth_method == 'patient_id':
                            exists, patient_data_found = patient_registration.check_patient_exists(
                                identifier_input, 'auto')
                        else:
                            exists, patient_data_found = patient_registration.check_patient_exists(
                                identifier_input, st.session_state.auth_method)
                        
                        if exists:
                            st.session_state.patient_id = patient_data_found.get('Patient ID')
                            st.session_state.patient_records = patient_data_found
                            st.session_state.stage = 'patient_info'
                            st.rerun()
                        else:
                            st.error("❌ Patient not found. Please register as a new patient.")
                            st.session_state.show_registration = True
                            st.rerun()
                    else:
                        st.warning("⚠️ Please enter your identifier to continue.")

            with col_btn2:
                if st.button("🆕 New Patient Registration"):
                    st.session_state.show_registration = True
                    st.rerun()

    # Show registration form if requested
    if st.session_state.show_registration:
        st.markdown("---")
        st.subheader("🆕 New Patient Registration")

        with st.form("patient_registration_form"):
            st.markdown("""
            <div class="info-box">
            <h4>📋 Registration Information</h4>
            <p>Please fill in your details. ABHA ID is optional but recommended for KYC verification.</p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(
                    "Full Name *", value=st.session_state.registration_data["name"])
                dob = st.date_input("Date of Birth *", value=None)
                gender = st.selectbox(
                    "Gender *", ["", "Male", "Female", "Other"], index=0)
                phone = st.text_input("Phone Number *", value=st.session_state.registration_data["phone"],
                                      help="10-digit mobile number")
                email = st.text_input(
                    "Email Address *", value=st.session_state.registration_data["email"])
                address = st.text_area(
                    "Address", value=st.session_state.registration_data["address"])

            with col2:
                insurance = st.text_input(
                    "Insurance Provider", value=st.session_state.registration_data["insurance"])
                emergency_contact = st.text_input("Emergency Contact", value=st.session_state.registration_data["emergency_contact"],
                                                  help="Name and phone number")
                family_history = st.text_area(
                    "Family Medical History", value=st.session_state.registration_data["family_history"])
                past_medical_history = st.text_area(
                    "Past Medical History", value=st.session_state.registration_data["past_medical_history"])
                current_medications = st.text_area(
                    "Current Medications", value=st.session_state.registration_data["current_medications"])
                drug_allergies = st.text_area(
                    "Drug Allergies", value=st.session_state.registration_data["drug_allergies"])

            # ABHA ID section
            st.markdown("---")
            st.subheader("🆔 ABHA (Ayushman Bharat Health Account) - Optional")
            st.markdown("""
            <div class="info-box">
            <p><strong>What is ABHA?</strong> ABHA is a 14-digit unique health ID that helps you access and share your health records digitally across different healthcare providers.</p>
            <p><strong>Benefits:</strong> Single KYC verification, unified health records, seamless healthcare access.</p>
            </div>
            """, unsafe_allow_html=True)

            abha_id = st.text_input("ABHA ID (14 digits)", value=st.session_state.registration_data["abha_id"],
                                    help="Enter your 14-digit ABHA ID for KYC verification")

            if abha_id and not validate_abha_id_format(abha_id):
                st.error("❌ ABHA ID must be exactly 14 digits")

            # Form submission
            col_submit1, col_submit2 = st.columns(2)

            with col_submit1:
                if st.form_submit_button("🔄 Cancel Registration"):
                    st.session_state.show_registration = False
                    st.rerun()

            with col_submit2:
                if st.form_submit_button("✅ Register Patient"):
                    # Validate required fields
                    if not all([name, dob, gender, phone, email]):
                        st.error(
                            "❌ Please fill in all required fields (marked with *)")
                    elif not re.match(r'^\d{10}$', phone):
                        st.error("❌ Phone number must be exactly 10 digits")
                    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                        st.error("❌ Please enter a valid email address")
                    elif abha_id and not validate_abha_id_format(abha_id):
                        st.error("❌ ABHA ID must be exactly 14 digits")
                    else:
                        # Prepare registration data
                        registration_data = {
                            "name": name,
                            "dob": dob.isoformat() if dob else "",
                            "gender": gender,
                            "phone": phone,
                            "email": email,
                            "address": address,
                            "insurance": insurance,
                            "emergency_contact": emergency_contact,
                            "family_history": family_history,
                            "past_medical_history": past_medical_history,
                            "current_medications": current_medications,
                            "drug_allergies": drug_allergies,
                            "abha_id": abha_id
                        }

                        # Register patient
                        with st.spinner("Registering patient and verifying ABHA..."):
                            success, patient_id, response = patient_registration.register_new_patient(
                                registration_data)

                        if success:
                            st.success(
                                f"✅ Registration successful! Your Patient ID is: **{patient_id}**")
                            if response.get("abha_verified"):
                                st.success(
                                    "🆔 ABHA verification completed successfully!")

                            # Set patient data and proceed
                            st.session_state.patient_id = patient_id
                            st.session_state.patient_records = patient_registration.check_patient_exists(patient_id)[
                                1]
                            st.session_state.show_registration = False
                            st.session_state.stage = 'patient_info'
                            st.rerun()
                        else:
                            st.error(
                                f"❌ Registration failed: {response.get('error', 'Unknown error')}")

elif st.session_state.stage == 'patient_info':
    st.title("📋 Patient Information Review")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Display patient identifiers
        patient_records = st.session_state.patient_records
        mrn = patient_records.get('MRN', 'N/A')
        
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div>
                    <h4 style="margin: 0; color: #1976d2; font-size: 16px;">🆔 Patient ID: {st.session_state.patient_id}</h4>
                </div>
                <div>
                    <h4 style="margin: 0; color: #1976d2; font-size: 16px;">📋 MRN: {mrn}</h4>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Display patient records
        patient_records = st.session_state.patient_records

        # Basic Information
        st.markdown("""
        <div style="margin: 20px 0 15px 0;">
            <h3 style="margin: 0; color: #333; font-size: 18px; font-weight: 600;">👤 Basic Information</h3>
        </div>
        """, unsafe_allow_html=True)

        # Calculate age from DOB
        dob = patient_records.get('DOB')
        age = 'N/A'
        if pd.notna(dob) and dob:
            from datetime import datetime
            if isinstance(dob, str):
                dob = datetime.strptime(dob, '%Y-%m-%d')
            age = datetime.now().year - dob.year

        # Create a clean and elegant basic information display
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 20px; border-radius: 8px; margin: 15px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
                <div style="flex: 1; min-width: 200px;">
                    <p style="margin: 0; font-size: 12px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px;">👤 Name</p>
                    <p style="margin: 8px 0 0 0; font-size: 18px; font-weight: 600; color: #2c3e50;">{patient_records.get('Name', 'N/A')}</p>
                </div>
                <div style="flex: 1; min-width: 100px;">
                    <p style="margin: 0; font-size: 12px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px;">🎂 Age</p>
                    <p style="margin: 8px 0 0 0; font-size: 18px; font-weight: 600; color: #2c3e50;">{age}</p>
                </div>
                <div style="flex: 1; min-width: 100px;">
                    <p style="margin: 0; font-size: 12px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px;">⚥ Gender</p>
                    <p style="margin: 8px 0 0 0; font-size: 18px; font-weight: 600; color: #2c3e50;">{patient_records.get('Gender', 'N/A')}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Medical History
        st.markdown("""
        <div style="margin: 25px 0 15px 0;">
            <h3 style="margin: 0; color: #333; font-size: 18px; font-weight: 600;">🏥 Medical History</h3>
        </div>
        """, unsafe_allow_html=True)

        # Get medical history data
        allergies = patient_records.get('Drug Allergies', 'None')
        history = patient_records.get('Past Medical History', 'None')

        # Clean up the data
        if pd.isna(allergies) or allergies == 'None' or allergies == '':
            allergies = 'No known drug allergies'
            allergy_status = 'success'
        else:
            allergy_status = 'warning'

        if pd.isna(history) or history == 'None' or history == '':
            history = 'No significant medical history'
            history_status = 'success'
        else:
            history_status = 'info'

        # Create elegant medical history display with appealing background
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 20px; border-radius: 12px; margin: 15px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 250px; background-color: rgba(255,255,255,0.9); padding: 18px; border-radius: 10px; border-left: 5px solid #28a745; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h4 style="margin: 0 0 12px 0; color: #2c3e50; font-size: 15px; font-weight: 600;">💊 Drug Allergies</h4>
                    <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.5;">{allergies}</p>
                </div>
                <div style="flex: 1; min-width: 250px; background-color: rgba(255,255,255,0.9); padding: 18px; border-radius: 10px; border-left: 5px solid #17a2b8; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h4 style="margin: 0 0 12px 0; color: #2c3e50; font-size: 15px; font-weight: 600;">📋 Past Medical History</h4>
                    <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.5;">{history}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Additional information form
        st.subheader("🆕 Additional Health Information")
        additional_info = st.text_area(
            "Do you have any new allergies or chronic conditions to report?",
            placeholder="e.g., Recently developed peanut allergy, diagnosed with diabetes...",
            height=100,
            help="This helps us provide better recommendations"
        )

        if st.button("Continue to Symptoms ➡️"):
            st.session_state.additional_info = additional_info
            st.session_state.stage = 'symptoms'
            st.rerun()

    with col2:
        st.markdown("""
        <div class="info-box">
        <h4>📌 Review Your Information</h4>
        <p>Please verify that your medical records are correct.</p>
        <p>If you notice any discrepancies, please contact your healthcare provider.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("⬅️ Back"):
            st.session_state.stage = 'welcome'
            st.rerun()

elif st.session_state.stage == 'symptoms':
    st.title("🩺 Symptom Assessment")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"### Patient ID: {st.session_state.patient_id}")

        st.subheader("📝 Current Symptoms")
        st.markdown("""
        Please describe any symptoms you're experiencing. Be as specific as possible.
        Include details such as:
        - When did the symptoms start?
        - How severe are they (mild, moderate, severe)?
        - Any triggers or patterns?
        """)

        symptom_changes = st.text_area(
            "Describe your symptoms:",
            placeholder="e.g., Persistent fever for 3 days, mild headache in the morning, fatigue throughout the day...",
            height=150,
            help="The more details you provide, the better recommendations we can make"
        )

        st.markdown("---")

        # Quick symptom selector
        st.subheader("✅ Quick Symptom Selector")
        st.markdown("Select any symptoms that apply:")

        col_s1, col_s2, col_s3 = st.columns(3)

        quick_symptoms = []
        with col_s1:
            if st.checkbox("🌡️ Fever"):
                quick_symptoms.append("fever")
            if st.checkbox("😴 Fatigue"):
                quick_symptoms.append("fatigue")
            if st.checkbox("🤕 Headache"):
                quick_symptoms.append("headache")

        with col_s2:
            if st.checkbox("🤧 Cough"):
                quick_symptoms.append("cough")
            if st.checkbox("❤️ Chest Pain"):
                quick_symptoms.append("chest pain")
            if st.checkbox("😣 Body Pain"):
                quick_symptoms.append("body pain")

        with col_s3:
            if st.checkbox("😮‍💨 Breathing Issues"):
                quick_symptoms.append("difficulty breathing")
            if st.checkbox("🤢 Nausea"):
                quick_symptoms.append("nausea")
            if st.checkbox("😵 Dizziness"):
                quick_symptoms.append("dizziness")

        if quick_symptoms:
            st.info(f"Selected symptoms: {', '.join(quick_symptoms)}")
            combined_symptoms = symptom_changes + \
                " " + ", ".join(quick_symptoms)
        else:
            combined_symptoms = symptom_changes

        st.markdown("---")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("⬅️ Back"):
                st.session_state.stage = 'patient_info'
                st.rerun()

        with col_btn2:
            if st.button("Generate Report ➡️"):
                if combined_symptoms.strip():
                    st.session_state.symptom_changes = combined_symptoms

                    # Generate summary
                    structured_data = {
                        "patient_info": serialize_patient_info(st.session_state.patient_records),
                        "additional_info": st.session_state.additional_info,
                        "symptom_changes": st.session_state.symptom_changes
                    }

                    diagnostic_tests = recommend_diagnostic_tests(
                        st.session_state.symptom_changes)

                    st.session_state.final_summary = {
                        "structured_data": structured_data,
                        "diagnostic_tests": diagnostic_tests,
                        "timestamp": datetime.now().isoformat()
                    }

                    st.session_state.stage = 'summary'
                    st.rerun()
                else:
                    st.warning(
                        "⚠️ Please describe your symptoms before continuing.")

    with col2:
        st.markdown("""
        <div class="info-box">
        <h4>💡 Tips for Describing Symptoms</h4>
        <ul>
            <li><strong>Be specific:</strong> "Sharp pain in lower back" is better than "back pain"</li>
            <li><strong>Include duration:</strong> "For 3 days" or "Started this morning"</li>
            <li><strong>Note severity:</strong> Mild, moderate, or severe</li>
            <li><strong>Mention patterns:</strong> "Worse in the morning" or "After eating"</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.stage == 'summary':
    st.title("📊 Health Assessment Summary")

    summary = st.session_state.final_summary
    patient_info = summary['structured_data']['patient_info']

    # Success message
    st.markdown("""
    <div class="success-box">
    <h3>✅ Assessment Complete!</h3>
    <p>Your health information has been successfully processed and logged in our system.</p>
    </div>
    """, unsafe_allow_html=True)

    # Patient Summary
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("👤 Patient Information")
        st.markdown(f"**Patient ID:** {st.session_state.patient_id}")
        st.markdown(f"**MRN:** {patient_info.get('MRN', 'N/A')}")
        st.markdown(f"**Name:** {patient_info.get('Name', 'N/A')}")
        st.markdown(
            f"**Age:** {patient_info.get('Age', 'N/A')} | **Gender:** {patient_info.get('Gender', 'N/A')}")

        st.markdown("---")

        # Symptoms
        st.subheader("🩺 Reported Symptoms")
        st.info(summary['structured_data']['symptom_changes'])

        if summary['structured_data']['additional_info']:
            st.subheader("ℹ️ Additional Information")
            st.text(summary['structured_data']['additional_info'])

    with col2:
        st.subheader("⏰ Assessment Details")
        timestamp = datetime.fromisoformat(summary['timestamp'])

        # Create a more compact and elegant timestamp display
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <p style="margin: 0; font-size: 14px; color: #666;"><strong>📅 Date:</strong> {timestamp.strftime("%B %d, %Y")}</p>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: #666;"><strong>🕐 Time:</strong> {timestamp.strftime("%I:%M %p")}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Diagnostic Tests
    st.subheader("🔬 Recommended Diagnostic Tests")

    tests = summary['diagnostic_tests']

    if tests:
        for i, test in enumerate(tests, 1):
            st.markdown(f"{i}. {test}")
    else:
        st.info("No specific tests recommended at this time. Continue monitoring.")

    st.markdown("---")

    # Action items
    st.subheader("📋 Next Steps")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
        **Immediate Actions:**
        - Review the recommended tests with your healthcare provider
        - Schedule appointments as needed
        - Monitor your symptoms and note any changes
        """)

    with col_b:
        st.markdown("""
        **Follow-up:**
        - Keep track of symptom progression
        - Report any severe or worsening symptoms immediately
        - Maintain regular communication with your healthcare team
        """)

    st.markdown("---")

    # Download options
    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        # Export as JSON
        json_data = json.dumps(summary, indent=2)
        st.download_button(
            label="📥 Download JSON Report",
            data=json_data,
            file_name=f"health_report_{st.session_state.patient_id}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )

    with col_d2:
        # Export as text
        text_report = f"""
HEALTH ASSESSMENT REPORT
========================

Patient ID: {st.session_state.patient_id}
MRN: {patient_info.get('MRN', 'N/A')}
Date: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}

PATIENT INFORMATION:
Name: {patient_info.get('Name', 'N/A')}
Age: {patient_info.get('Age', 'N/A')}
Gender: {patient_info.get('Gender', 'N/A')}

REPORTED SYMPTOMS:
{summary['structured_data']['symptom_changes']}

ADDITIONAL INFORMATION:
{summary['structured_data']['additional_info'] or 'None'}

RECOMMENDED DIAGNOSTIC TESTS:
{chr(10).join([f"{i}. {test}" for i, test in enumerate(tests, 1)])}

---
Generated by Health Assistant
        """
        st.download_button(
            label="📄 Download Text Report",
            data=text_report,
            file_name=f"health_report_{st.session_state.patient_id}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )

    with col_d3:
        if st.button("🔄 New Assessment"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Reinitialize default session state
            st.session_state.stage = 'welcome'
            st.session_state.auth_method = 'patient_id'
            st.session_state.otp_verified = False
            st.session_state.otp_phone = None
            st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div class="info-box">
    <p><strong>⚠️ Important Notice:</strong> This assessment is for informational purposes only and does not replace professional medical advice. 
    Please consult with qualified healthcare professionals for diagnosis and treatment.</p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 1rem;'>"
    "🏥 Health Assistant • Powered by AI • © 2025"
    "</div>",
    unsafe_allow_html=True
)
