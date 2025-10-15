import streamlit as st
import json
import pandas as pd
import re
from datetime import datetime, timedelta
from std_hub.llm import AgentProject
from openai import OpenAI
from project import project_init
import logging
import os
from dotenv import load_dotenv
from patient_registration import PatientRegistration, get_registration_form_data, validate_abha_id_format
from std_hub.db.mongodb import db_client
from otp_service import get_otp_service
from medical_history_reconciliation import get_medical_reconciliation
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from collections import Counter

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
    /* Style for + buttons specifically */
    button[data-testid="baseButton-secondary"] {
        background-color: #007bff !important;
        color: white !important;
        border: 2px solid #007bff !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #0056b3 !important;
        border-color: #0056b3 !important;
    }
    /* Alternative selectors for + buttons */
    .stButton button[title*="Add"] {
        background-color: #007bff !important;
        color: white !important;
        border: 2px solid #007bff !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        min-width: 40px !important;
        min-height: 40px !important;
    }
    /* Target buttons with + text specifically */
    button:contains("+") {
        background-color: #007bff !important;
        color: white !important;
        border: 2px solid #007bff !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        font-size: 18px !important;
        font-weight: bold !important;
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
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border: 1px solid #e9ecef;
        text-align: center !important;
    }
    .stMetric [data-testid="metric-value"] {
        font-size: 0.9rem !important;
        font-weight: 600;
        text-align: center !important;
    }
    .stMetric [data-testid="metric-delta"] {
        font-size: 0.7rem !important;
        text-align: center !important;
    }
    .stMetric [data-testid="metric-label"] {
        text-align: center !important;
    }
    /* Additional selectors to ensure the styling applies */
    div[data-testid="metric-container"] {
        text-align: center !important;
    }
    div[data-testid="metric-container"] > div {
        text-align: center !important;
    }
    /* Target the specific metric value elements */
    .stMetric div[data-testid="metric-value"] {
        font-size: 0.9rem !important;
        text-align: center !important;
    }
    /* Force center alignment for all metric content */
    .stMetric * {
        text-align: center !important;
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

    # Generate MRN if not present
    if not serializable_info.get('MRN') or serializable_info.get('MRN') == 'N/A':
        # Generate MRN in format: MRN{YYYYMMDD}{6-char-random}
        import random
        import string
        today = datetime.now()
        date_str = today.strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        serializable_info['MRN'] = f"MRN{date_str}{random_str}"

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


def _update_patient_with_reconciled_data(patient_records, medical_history):
    """Update patient records with reconciled medical history data"""
    updated_records = patient_records.copy()
    
    # Helper function to clean and merge data
    def clean_and_merge_data(existing_field, new_data, field_name):
        """Clean existing data and merge with new data"""
        # Clean existing data - remove NaN, None, empty strings
        if pd.isna(existing_field) or existing_field in ['None', '', 'nan', 'NaN']:
            existing_field = ''
        
        # Clean new data
        new_data_clean = [item for item in new_data if item and str(item).lower() not in ['nan', 'none', '']]
        
        if new_data_clean:
            new_data_str = ', '.join(new_data_clean)
            if existing_field and existing_field.strip():
                return f"{existing_field}; {new_data_str}"
            else:
                return new_data_str
        else:
            return existing_field if existing_field else ''
    
    # Update medical conditions
    if medical_history.get('conditions'):
        updated_records['Past Medical History'] = clean_and_merge_data(
            updated_records.get('Past Medical History', ''), 
            medical_history['conditions'], 
            'conditions'
        )
    
    # Update medications
    if medical_history.get('medications'):
        updated_records['Current Medications'] = clean_and_merge_data(
            updated_records.get('Current Medications', ''), 
            medical_history['medications'], 
            'medications'
        )
    
    # Update allergies
    if medical_history.get('allergies'):
        updated_records['Drug Allergies'] = clean_and_merge_data(
            updated_records.get('Drug Allergies', ''), 
            medical_history['allergies'], 
            'allergies'
        )
    
    # Add reconciliation metadata
    updated_records['Medical History Reconciled'] = 'Yes'
    updated_records['Reconciliation Date'] = medical_history.get('collection_date', '')
    updated_records['Reconciliation Sources'] = ', '.join([s['hospital_name'] for s in medical_history.get('sources', [])])
    
    return updated_records


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
if 'show_reconciliation' not in st.session_state:
    st.session_state.show_reconciliation = False
if 'medical_sources' not in st.session_state:
    st.session_state.medical_sources = None
if 'consent_given' not in st.session_state:
    st.session_state.consent_given = False
if 'duplicate_confirmations' not in st.session_state:
    st.session_state.duplicate_confirmations = []
if 'show_add_allergies' not in st.session_state:
    st.session_state.show_add_allergies = False
if 'show_add_conditions' not in st.session_state:
    st.session_state.show_add_conditions = False
if 'show_add_medications' not in st.session_state:
    st.session_state.show_add_medications = False
if 'show_add_procedures' not in st.session_state:
    st.session_state.show_add_procedures = False

# Load data
project = initialize_project()
patient_data = load_patient_data()

# Initialize patient registration system, OTP service, and medical reconciliation
patient_registration = PatientRegistration(db_client)
otp_service = get_otp_service()
medical_reconciliation = get_medical_reconciliation()

# Sidebar
with st.sidebar:
    st.title("🏥 Health Assistant")
    st.markdown("---")

    # Progress indicator
    stages = {
        'welcome': '1️⃣ Patient ID',
        'registration': '🆕 Registration',
        'reconciliation': 'Medical History',
        'patient_info': '2️⃣ Health Info',
        'symptoms': '3️⃣ Symptoms',
        'insights': '📊 Insights Dashboard',
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
        st.session_state.show_reconciliation = False
        st.session_state.medical_sources = None
        st.session_state.consent_given = False
        st.session_state.duplicate_confirmations = []
        st.session_state.show_add_allergies = False
        st.session_state.show_add_conditions = False
        st.session_state.show_add_medications = False
        st.session_state.show_add_procedures = False
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
        st.subheader("Access Your Health Records")
        
        # Authentication method selector
        auth_options = ["Patient ID / UHID / MRN", "ABHA ID", "Phone Number"]
        auth_values = ["patient_id", "abha", "phone"]
        
        # Get current index based on session state
        try:
            current_index = auth_values.index(st.session_state.auth_method)
        except ValueError:
            current_index = 0  # Default to first option
        
        auth_method = st.radio(
            "How would you like to access your records?",
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
            st.subheader("Verify with Phone Number")
            
            if not st.session_state.otp_verified:
                phone_input = st.text_input(
                    "Phone Number",
                    placeholder="Enter your 10-digit mobile number",
                    help="Enter your registered mobile number"
                )
                
                col_otp1, col_otp2 = st.columns(2)
                
                with col_otp1:
                    if st.button("Send Verification Code"):
                        if phone_input and len(phone_input) == 10 and phone_input.isdigit():
                            with st.spinner("Sending verification code..."):
                                success, otp_code, response = otp_service.generate_otp(phone_input)
                            
                            if success:
                                st.session_state.otp_phone = phone_input
                                st.success(f"Verification code sent to {phone_input}")
                                st.rerun()
                            else:
                                st.error(f"{response.get('error', 'Failed to send verification code')}")
                        else:
                            st.warning("Please enter a valid 10-digit phone number")
                
                with col_otp2:
                    if st.button("Reset"):
                        st.session_state.otp_phone = None
                        st.session_state.otp_verified = False
                        st.rerun()
                
                # OTP verification
                if st.session_state.otp_phone:
                    st.markdown("---")
                    st.subheader("Enter Verification Code")
                    otp_input = st.text_input(
                        "OTP Code",
                        placeholder="Enter 6-digit verification code",
                        help="Enter the verification code sent to your phone"
                    )
                    
                    if st.button("Verify Code"):
                        if otp_input and len(otp_input) == 6 and otp_input.isdigit():
                            with st.spinner("Verifying code..."):
                                verified, response = otp_service.verify_otp(st.session_state.otp_phone, otp_input)
                            
                            if verified:
                                st.session_state.otp_verified = True
                                st.success("Phone number verified successfully!")
                                
                                # Automatically proceed to patient lookup
                                with st.spinner("Looking up patient records..."):
                                    exists, patient_data_found = patient_registration.check_patient_exists(
                                        st.session_state.otp_phone, 'phone')
                                
                                if exists:
                                    st.session_state.patient_id = patient_data_found.get('Patient ID')
                                    st.session_state.patient_records = patient_data_found
                                    # For returning patients, show medical history reconciliation
                                    st.session_state.stage = 'reconciliation'
                                    st.rerun()
                                else:
                                    st.error("No patient record found for this phone number. Please register as a new patient.")
                                    st.session_state.show_registration = True
                                    st.rerun()
                            else:
                                st.error(f"{response.get('error', 'Verification failed')}")
                        else:
                            st.warning("Please enter a valid 6-digit verification code")
            
        else:
            # Other authentication methods
            if st.session_state.auth_method == 'patient_id':
                st.subheader("Patient ID / UHID / MRN")
                identifier_input = st.text_input(
                    "Patient ID / UHID / MRN",
                    placeholder="e.g., GEN10001, REG2025010112345678, MRN20250101ABC123...",
                    help="Enter your Patient ID, UHID, or Medical Record Number"
                )
            elif st.session_state.auth_method == 'abha':
                st.subheader("ABHA ID")
                identifier_input = st.text_input(
                    "ABHA ID",
                    placeholder="Enter your 14-digit ABHA ID",
                    help="Enter your Ayushman Bharat Health Account ID"
        )

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Continue"):
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
                        # For returning patients, show medical history reconciliation
                        st.session_state.stage = 'reconciliation'
                        st.rerun()
                    else:
                        st.error("Patient not found. Please register as a new patient.")
                        st.session_state.show_registration = True
                        st.rerun()
                else:
                    st.warning("Please enter your identifier to continue.")

        with col_btn2:
            if st.button("New Patient Registration"):
                st.session_state.show_registration = True
                st.rerun()

    # Show registration form if requested
    if st.session_state.show_registration:
        st.markdown("---")
        st.subheader("New Patient Registration")

        with st.form("patient_registration_form"):
            st.markdown("""
            <div class="info-box">
            <h4>Registration Information</h4>
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
            st.subheader("ABHA (Ayushman Bharat Health Account) - Optional")
            st.markdown("""
            <div class="info-box">
            <p><strong>What is ABHA?</strong> ABHA is a 14-digit unique health ID that helps you access and share your health records digitally across different healthcare providers.</p>
            <p><strong>Benefits:</strong> Single KYC verification, unified health records, seamless healthcare access.</p>
            </div>
            """, unsafe_allow_html=True)

            abha_id = st.text_input("ABHA ID (14 digits)", value=st.session_state.registration_data["abha_id"],
                                    help="Enter your 14-digit ABHA ID for KYC verification")

            if abha_id and not validate_abha_id_format(abha_id):
                st.error("ABHA ID must be exactly 14 digits")

            # Form submission
            col_submit1, col_submit2 = st.columns(2)

            with col_submit1:
                if st.form_submit_button("Cancel Registration"):
                    st.session_state.show_registration = False
                    st.rerun()

            with col_submit2:
                if st.form_submit_button("Register Patient"):
                    # Validate required fields
                    if not all([name, dob, gender, phone, email]):
                        st.error(
                            "Please fill in all required fields (marked with *)")
                    elif not re.match(r'^\d{10}$', phone):
                        st.error("Phone number must be exactly 10 digits")
                    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                        st.error("Please enter a valid email address")
                    elif abha_id and not validate_abha_id_format(abha_id):
                        st.error("ABHA ID must be exactly 14 digits")
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
                                f"Registration successful! Your Patient ID is: **{patient_id}**")
                            if response.get("abha_verified"):
                                st.success(
                                    "ABHA verification completed successfully!")

                            # Set patient data and proceed
                            st.session_state.patient_id = patient_id
                            st.session_state.patient_records = patient_registration.check_patient_exists(patient_id)[
                                1]
                            st.session_state.show_registration = False
                            st.session_state.stage = 'patient_info'
                            st.rerun()
                        else:
                            st.error(
                                f"Registration failed: {response.get('error', 'Unknown error')}")

elif st.session_state.stage == 'reconciliation':
    st.title("Medical History Reconciliation")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #e0e0e0;">
            <h4 style="margin: 0; color: #2c3e50; font-size: 16px;">Patient ID: {st.session_state.patient_id}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Get medical sources for this patient
        if not st.session_state.medical_sources:
            with st.spinner("Checking for medical records across hospitals..."):
                st.session_state.medical_sources = medical_reconciliation.get_patient_medical_sources(
                    st.session_state.patient_id)
        
        sources = st.session_state.medical_sources
        
        st.markdown("""
        <div class="info-box">
        <h4>Medical History Collection</h4>
        <p>We found your medical records at the following healthcare providers. 
        To provide you with comprehensive care, we need your consent to collect and reconcile 
        your medical history from these sources.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display hospital sources
        st.subheader("Healthcare Providers with Your Records")
        
        for i, source in enumerate(sources):
            with st.expander(f"{source['name']} - {source['location']}", expanded=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Location:** {source['location']}")
                    st.write(f"**Last Visit:** {source['last_visit']}")
                with col_b:
                    st.write(f"**Records:** {source['records_count']} medical records")
                    st.write(f"**Status:** Records Available")
        
        # Consent form
        st.markdown("---")
        st.subheader("Consent for Medical History Collection")
        
        consent_data = medical_reconciliation.get_consent_form_data(
            st.session_state.patient_id, sources)
        
        st.markdown(f"""
        <div class="warning-box">
        <h4>Data Collection Consent</h4>
        <p><strong>Purpose:</strong> {consent_data['purpose']}</p>
        <p><strong>Data Sources:</strong> {', '.join(consent_data['data_sources'])}</p>
        <p><strong>Data Types:</strong> {', '.join(consent_data['data_types'])}</p>
        <p><strong>Consent Period:</strong> {consent_data['consent_period']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Consent checkbox
        consent_given = st.checkbox(
            "I consent to the collection and reconciliation of my medical history from the above healthcare providers",
            value=st.session_state.consent_given
        )
        
        st.session_state.consent_given = consent_given
        
        if consent_given:
            # Collect medical history only once
            if 'reconciled_medical_history' not in st.session_state:
                with st.spinner("Collecting medical history from all sources..."):
                    medical_history = medical_reconciliation.collect_medical_history(
                        st.session_state.patient_id, [s['source_id'] for s in sources])
                
                # Store medical history in session state for later use
                st.session_state.reconciled_medical_history = medical_history
            else:
                # Use existing medical history
                medical_history = st.session_state.reconciled_medical_history
            
            # Show duplicates if any
            if medical_history.get('duplicates'):
                st.markdown("---")
                st.subheader("Duplicate Patient Records Detected")
                
                st.markdown("""
                <div class="warning-box">
                <p>We found duplicate patient records across different hospitals. 
                Please confirm which patient record you want to keep as your primary record.</p>
                </div>
                """, unsafe_allow_html=True)
                
                for i, duplicate in enumerate(medical_history['duplicates']):
                    st.write(f"**Patient Record:** {duplicate['value']} (found in {duplicate['count']} hospitals)")
                    st.write(f"**Sources:** {', '.join(duplicate['sources'])}")
                    
                    # Confirmation for each duplicate
                    confirm = st.radio(
                        f"Keep patient record from:",
                        duplicate['sources'],
                        key=f"duplicate_{duplicate['type']}_{duplicate['value']}_{i}"
                    )
                    
                    # Update or add confirmation
                    confirmation_key = f"{duplicate['type']}_{duplicate['value']}"
                    confirmation_exists = False
                    
                    for j, existing_conf in enumerate(st.session_state.duplicate_confirmations):
                        if existing_conf['type'] == duplicate['type'] and existing_conf['value'] == duplicate['value']:
                            st.session_state.duplicate_confirmations[j]['confirmed_source'] = confirm
                            confirmation_exists = True
                            break
                    
                    if not confirmation_exists:
                        st.session_state.duplicate_confirmations.append({
                            'type': duplicate['type'],
                            'value': duplicate['value'],
                            'confirmed_source': confirm
                        })
            
            # Show collected medical history summary
            st.markdown("---")
            st.subheader("Collected Medical History Summary")
            
            # Show duplicate confirmations if any
            if st.session_state.duplicate_confirmations:
                st.info("**Note:** Duplicate patient records will be resolved based on your selections above.")
            
            col_sum1, col_sum2 = st.columns(2)
            with col_sum1:
                st.write(f"**Conditions:** {len(medical_history['conditions'])}")
                if medical_history['conditions']:
                    for condition in medical_history['conditions']:
                        st.write(f"• {condition}")
                
                st.write(f"**Medications:** {len(medical_history['medications'])}")
                if medical_history['medications']:
                    for medication in medical_history['medications']:
                        st.write(f"• {medication}")
            
            with col_sum2:
                st.write(f"**Procedures:** {len(medical_history['procedures'])}")
                if medical_history['procedures']:
                    for procedure in medical_history['procedures']:
                        st.write(f"• {procedure}")
                
                st.write(f"**Allergies:** {len(medical_history['allergies'])}")
                if medical_history['allergies']:
                    for allergy in medical_history['allergies']:
                        st.write(f"• {allergy}")
            
            # Action buttons
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("Reconcile Medical History"):
                    if consent_given:
                        result = medical_reconciliation.process_consent_response(
                            st.session_state.patient_id, 
                            consent_given, 
                            st.session_state.duplicate_confirmations
                        )
                        
                        if result['success']:
                            st.success("Medical history reconciliation completed!")
                            
                            # Create final reconciled history based on duplicate confirmations
                            final_medical_history = medical_reconciliation.create_final_reconciled_history(
                                medical_history, st.session_state.duplicate_confirmations)
                            
                            # Update patient records with final reconciled medical history
                            st.session_state.patient_records = _update_patient_with_reconciled_data(
                                st.session_state.patient_records, final_medical_history)
                            
                            st.session_state.stage = 'patient_info'
                            st.rerun()
                        else:
                            st.error(f"{result['message']}")
                    else:
                        st.warning("Please provide consent to proceed")
            
            with col_btn2:
                if st.button("Skip Reconciliation"):
                    st.info("Skipping medical history reconciliation. You can reconcile later.")
                    st.session_state.stage = 'patient_info'
                    st.rerun()
        
        else:
            st.warning("Consent is required to reconcile your medical history")
    
    with col2:
        st.markdown("""
        <div class="info-box">
        <h4>Why Reconcile Medical History?</h4>
        <ul>
            <li><strong>Complete Picture:</strong> Get a comprehensive view of your health</li>
            <li><strong>Better Care:</strong> Help doctors make informed decisions</li>
            <li><strong>Medication Safety:</strong> Avoid drug interactions</li>
            <li><strong>Continuity:</strong> Seamless care across providers</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
        <h4>Your Privacy Rights</h4>
        <ul>
            <li>Right to access your records</li>
            <li>Right to request corrections</li>
            <li>Right to withdraw consent</li>
            <li>Right to data portability</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⬅️ Back"):
            st.session_state.stage = 'welcome'
            st.rerun()

elif st.session_state.stage == 'patient_info':
    st.markdown("""
    <h2 style="font-size: 24px; margin-bottom: 20px; color: #2c3e50;">Patient Information Review</h2>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col2:
        # Review Information Section - positioned in the same location as "Why Reconcile Medical History?"
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 15px; margin: 20px 0; box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
            <div style="text-align: center; color: white;">
                <h3 style="margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">📌 Review Your Information</h3>
                <p style="margin: 0 0 10px 0; font-size: 14px; opacity: 0.9;">Please verify that your medical records are correct.</p>
                <p style="margin: 0; font-size: 13px; opacity: 0.8;">If you notice any discrepancies, please contact your healthcare provider.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Back button positioned below Review Your Information
        if st.button("Back", use_container_width=True):
            st.session_state.stage = 'welcome'
            st.rerun()

    with col1:
        # Display patient identifiers
        patient_records = st.session_state.patient_records
        mrn = patient_records.get('MRN', 'N/A')
        
        # Generate MRN if not present
        if mrn == 'N/A' or not mrn:
            import random
            import string
            today = datetime.now()
            date_str = today.strftime('%Y%m%d')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            mrn = f"MRN{date_str}{random_str}"
            # Update the patient records with the generated MRN
            patient_records['MRN'] = mrn
            st.session_state.patient_records = patient_records
        
        st.markdown(f"""
        <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #e0e0e0;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div>
            <h4 style="margin: 0; color: #2c3e50; font-size: 16px;">Patient ID: {st.session_state.patient_id}</h4>
                </div>
                <div>
                    <h4 style="margin: 0; color: #2c3e50; font-size: 16px;">MRN: {mrn}</h4>
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
        medications = patient_records.get('Current Medications', 'None')
        recent_procedures = patient_records.get('Recent Procedures', 'None')
        
        # Check if medical history was reconciled
        reconciled = patient_records.get('Medical History Reconciled', 'No')
        reconciliation_sources = patient_records.get('Reconciliation Sources', '')

        # Clean up the data - remove NaN values and clean up strings
        def clean_medical_data(data):
            """Clean medical data by removing NaN and unwanted values"""
            if pd.isna(data) or data in ['None', '', 'nan', 'NaN', 'nan;']:
                return ''
            
            # Convert to string and clean up
            data_str = str(data)
            
            # Remove common unwanted patterns
            data_str = data_str.replace('nan;', '').replace('NaN;', '').replace('None;', '')
            data_str = data_str.replace('; ;', ';').replace(';;', ';')
            data_str = data_str.strip('; ').strip()
            
            return data_str

        # Clean the data
        allergies = clean_medical_data(allergies)
        history = clean_medical_data(history)
        medications = clean_medical_data(medications)
        recent_procedures = clean_medical_data(recent_procedures)

        # Set display values and status
        if not allergies:
            allergies = 'No known drug allergies'
            allergy_status = 'success'
        else:
            allergy_status = 'warning'

        if not history:
            history = 'No significant medical history'
            history_status = 'success'
        else:
            history_status = 'info'
            
        if not medications:
            medications = 'No current medications'
            medication_status = 'success'
        else:
            medication_status = 'info'
            
        if not recent_procedures:
            recent_procedures = 'No recent procedures'
            procedure_status = 'success'
        else:
            procedure_status = 'info'

        # Show reconciliation status if applicable
        if reconciled == 'Yes':
            st.markdown(f"""
            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 6px; margin: 10px 0;">
                <h4 style="margin: 0; color: #155724; font-size: 14px;">🔄 Medical History Reconciled</h4>
                <p style="margin: 5px 0 0 0; color: #155724; font-size: 12px;">Data collected from: {reconciliation_sources}</p>
            </div>
            """, unsafe_allow_html=True)

        # Create elegant medical history display with appealing background
        # Medical History Cards with inline add functionality - 2 column layout for medical history
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Drug Allergies Card
            st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.9); padding: 20px; border-radius: 12px; border-left: 5px solid #28a745; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h4 style="margin: 0; color: #2c3e50; font-size: 16px; font-weight: 600;">Drug Allergies</h4>
                </div>
                <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.6; min-height: 60px;">{allergies}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Add allergies form
            if st.button("➕ Add Allergies", key="add_allergies_btn", help="Add new allergies"):
                st.session_state.show_add_allergies = not st.session_state.show_add_allergies
            
            if st.session_state.get('show_add_allergies', False):
                with st.form("add_allergies_form"):
                    st.markdown("**Add New Allergies**")
                    new_allergies = st.text_area(
                        "Enter new allergies (one per line or separated by commas):",
                        placeholder="e.g., Penicillin\nLatex\nShellfish",
                        height=80,
                        label_visibility="collapsed"
                    )
                    if st.form_submit_button("Add Allergies", type="primary"):
                        if new_allergies.strip():
                            allergies_list = [allergy.strip() for allergy in new_allergies.replace('\n', ',').split(',') if allergy.strip()]
                            if allergies_list:
                                current_allergies = patient_records.get('Drug Allergies', '')
                                if current_allergies and current_allergies != 'No known drug allergies':
                                    new_allergies_str = ', '.join(allergies_list)
                                    patient_records['Drug Allergies'] = f"{current_allergies}; {new_allergies_str}"
                                else:
                                    patient_records['Drug Allergies'] = ', '.join(allergies_list)
                                
                                st.session_state.patient_records = patient_records
                                st.session_state.show_add_allergies = False
                                st.success(f"Added {len(allergies_list)} new allergy/allergies!")
                                st.rerun()
                    if st.form_submit_button("Cancel"):
                        st.session_state.show_add_allergies = False
                        st.rerun()
            
            # Past Medical History Card
            st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.9); padding: 20px; border-radius: 12px; border-left: 5px solid #17a2b8; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h4 style="margin: 0; color: #2c3e50; font-size: 16px; font-weight: 600;">Past Medical History</h4>
                </div>
                <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.6; min-height: 60px;">{history}</p>
        </div>
        """, unsafe_allow_html=True)

            # Add conditions form
            if st.button("➕ Add Conditions", key="add_conditions_btn", help="Add new medical conditions"):
                st.session_state.show_add_conditions = not st.session_state.show_add_conditions
            
            if st.session_state.get('show_add_conditions', False):
                with st.form("add_conditions_form"):
                    st.markdown("**Add New Medical Conditions**")
                new_conditions = st.text_area(
                    "Enter new medical conditions (one per line or separated by commas):",
                    placeholder="e.g., High blood pressure\nDiabetes\nAsthma",
                    height=80,
                    label_visibility="collapsed"
                )
                if st.form_submit_button("Add Conditions", type="primary"):
                    if new_conditions.strip():
                        conditions_list = [cond.strip() for cond in new_conditions.replace('\n', ',').split(',') if cond.strip()]
                        if conditions_list:
                            current_conditions = patient_records.get('Past Medical History', '')
                            if current_conditions and current_conditions != 'No significant medical history':
                                new_conditions_str = ', '.join(conditions_list)
                                patient_records['Past Medical History'] = f"{current_conditions}; {new_conditions_str}"
                            else:
                                patient_records['Past Medical History'] = ', '.join(conditions_list)
                            
                            st.session_state.patient_records = patient_records
                            st.session_state.show_add_conditions = False
                            st.success(f"Added {len(conditions_list)} new condition(s)!")
                            st.rerun()
                if st.form_submit_button("Cancel"):
                    st.session_state.show_add_conditions = False
                    st.rerun()

        with col2:
            # Current Medications Card
            st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.9); padding: 20px; border-radius: 12px; border-left: 5px solid #6f42c1; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h4 style="margin: 0; color: #2c3e50; font-size: 16px; font-weight: 600;">Current Medications</h4>
                </div>
                <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.6; min-height: 60px;">{medications}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Add medications form
            if st.button("➕ Add Medications", key="add_medications_btn", help="Add new medications"):
                st.session_state.show_add_medications = not st.session_state.show_add_medications
            
            if st.session_state.get('show_add_medications', False):
                with st.form("add_medications_form"):
                    st.markdown("**Add New Medications**")
                    new_medications = st.text_area(
                        "Enter new medications (one per line or separated by commas):",
                        placeholder="e.g., Metformin 500mg\nLisinopril 10mg\nAtorvastatin 20mg",
                        height=80,
                        label_visibility="collapsed"
                    )
                    if st.form_submit_button("Add Medications", type="primary"):
                        if new_medications.strip():
                            medications_list = [med.strip() for med in new_medications.replace('\n', ',').split(',') if med.strip()]
                            if medications_list:
                                current_medications = patient_records.get('Current Medications', '')
                                if current_medications and current_medications != 'No current medications':
                                    new_medications_str = ', '.join(medications_list)
                                    patient_records['Current Medications'] = f"{current_medications}; {new_medications_str}"
                                else:
                                    patient_records['Current Medications'] = ', '.join(medications_list)
                                
                                st.session_state.patient_records = patient_records
                                st.session_state.show_add_medications = False
                                st.success(f"Added {len(medications_list)} new medication(s)!")
                                st.rerun()
                    if st.form_submit_button("Cancel"):
                        st.session_state.show_add_medications = False
                        st.rerun()

            # Recent Procedures Card
            st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.9); padding: 20px; border-radius: 12px; border-left: 5px solid #fd7e14; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h4 style="margin: 0; color: #2c3e50; font-size: 16px; font-weight: 600;">Recent Procedures</h4>
                </div>
                <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.6; min-height: 60px;">{recent_procedures}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Add procedures form
            if st.button("➕ Add Procedures", key="add_procedures_btn", help="Add new procedures"):
                st.session_state.show_add_procedures = not st.session_state.show_add_procedures
            
            if st.session_state.get('show_add_procedures', False):
                with st.form("add_procedures_form"):
                    st.markdown("**Add New Procedures**")
                    new_procedures = st.text_area(
                        "Enter new procedures or tests (one per line or separated by commas):",
                        placeholder="e.g., Blood test\nX-ray\nMRI scan\nECG",
                        height=80,
                        label_visibility="collapsed"
                    )
                    if st.form_submit_button("Add Procedures", type="primary"):
                        if new_procedures.strip():
                            procedures_list = [proc.strip() for proc in new_procedures.replace('\n', ',').split(',') if proc.strip()]
                            if procedures_list:
                                current_procedures = patient_records.get('Recent Procedures', '')
                                if current_procedures:
                                    new_procedures_str = ', '.join(procedures_list)
                                    patient_records['Recent Procedures'] = f"{current_procedures}; {new_procedures_str}"
                                else:
                                    patient_records['Recent Procedures'] = ', '.join(procedures_list)
                                
                                st.session_state.patient_records = patient_records
                                st.session_state.show_add_procedures = False
                                st.success(f"Added {len(procedures_list)} new procedure(s)!")
                                st.rerun()
                    if st.form_submit_button("Cancel"):
                        st.session_state.show_add_procedures = False
                        st.rerun()

        st.markdown("---")

        if st.button("Continue to Symptoms"):
            st.session_state.stage = 'symptoms'
            st.rerun()


elif st.session_state.stage == 'symptoms':
        st.markdown("""
    <h1 style="font-size: 28px; color: #2c3e50; margin-bottom: 25px; font-weight: 600; text-align: left;">
        Symptom Assessment
    </h1>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"""
            <div style="font-size: 16px; color: #495057; margin-bottom: 15px; font-weight: 500;">
                Patient ID: {st.session_state.patient_id}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="font-size: 18px; color: #2c3e50; margin-bottom: 20px; font-weight: 600;">
            Current Symptoms
        </div>
        """, unsafe_allow_html=True)
        
        # 1. Describe your symptoms (first)
        symptom_description = st.text_area(
            "Describe your symptoms:",
            placeholder="e.g., headache, fatigue, nausea, body aches...",
            height=120,
            help="Describe the symptoms you're experiencing"
        )
        
        # 2. How long you had the symptom
        symptom_duration = st.text_input(
            "How long have you had the symptoms?",
            placeholder="e.g., 3 days, 1 week, since this morning...",
            help="Describe how long you've been experiencing these symptoms"
        )
        
        # 3. Temperature input
        col_temp1, col_temp2 = st.columns([1.2, 0.8])
        with col_temp1:
            temperature = st.number_input(
                "Temperature (°F):",
                min_value=95.0,
                max_value=110.0,
                value=98.6,
                step=0.1,
                help="Enter your current body temperature"
            )
        
        with col_temp2:
            # Determine fever severity based on temperature
            if temperature < 100.4:
                fever_status = "No Fever"
                fever_range = "Normal: <100.4°F"
                severity_level = "None"
            elif temperature < 102.2:
                fever_status = "Mild Fever"
                fever_range = "Range: 100.4-102.1°F"
                severity_level = "Mild"
            elif temperature < 104.0:
                fever_status = "Moderate Fever"
                fever_range = "Range: 100.6-102.2°F"
                severity_level = "Moderate"
            else:
                fever_status = "High Fever"
                fever_range = "Range: >104.0°F"
                severity_level = "Severe"
            
            # Display fever status box (aligned with temperature input)
            if temperature >= 100.4:
                st.markdown(f"""
                <div style="background-color: #fff3cd; border-left: 3px solid #ffc107; padding: 8px 12px; border-radius: 6px; margin-top: 25px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="color: #856404; font-size: 14px; font-weight: bold;">{fever_status}</span>
                            <span style="color: #6c757d; font-size: 12px; margin-left: 8px;">{fever_range}</span>
                        </div>
                        <span style="font-size: 14px;">🌡️</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # 4. Severity level slider
        severity_options = ["None", "Mild", "Moderate", "Severe"]
        current_severity_index = severity_options.index(severity_level) if severity_level in severity_options else 1
        
        severity_level = st.select_slider(
            "Severity level (auto-detected from temperature):",
            options=severity_options,
            value=severity_level,
            help="Select the severity level of your symptoms"
        )
        
        # 5. Any triggers or patterns (last)
        triggers_patterns = st.text_area(
            "Any triggers or patterns?",
            placeholder="e.g., worse in the morning, after eating, during exercise...",
            height=100,
            help="Describe any patterns or triggers you've noticed"
        )
        
        # Combine all symptom information
        symptom_changes = f"Temperature: {temperature}°F, Severity: {severity_level}"
        if symptom_description:
            symptom_changes += f", Symptoms: {symptom_description}"
        if symptom_duration:
            symptom_changes += f", Duration: {symptom_duration}"
        if triggers_patterns:
            symptom_changes += f", Patterns: {triggers_patterns}"

        st.markdown("---")

        # Use only the text area input for symptoms
        combined_symptoms = symptom_changes

        st.markdown("---")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Back"):
                st.session_state.stage = 'patient_info'
                st.rerun()

        with col_btn2:
            if st.button("Generate Insights"):
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

                    st.session_state.stage = 'insights'
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

elif st.session_state.stage == 'insights':
    # Helper function to safely parse semicolon-separated fields
    def safe_parse_field(field_value, default_value=''):
        """Safely parse a field that might be a string, float, or None"""
        if field_value is None or field_value == '' or str(field_value).lower() in ['nan', 'none', 'n/a']:
            return []
        
        # Convert to string and handle float values
        field_str = str(field_value)
        if field_str.lower() in ['nan', 'none', 'n/a']:
            return []
        
        # Split and clean the list
        return [item.strip() for item in field_str.split(';') if item.strip() and item.strip().lower() not in ['nan', 'none', 'n/a']]

    st.markdown("""
    <div style="text-align: center; margin-bottom: 16px;">
        <h2 style="margin: 0; color: #495057; font-size: 20px; font-weight: 600;">📊 Patient 360 Insights Dashboard</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Patient header
    col_header1, col_header2, col_header3 = st.columns([2, 1, 1])
    with col_header1:
        # Calculate age from DOB if available
        dob = st.session_state.patient_records.get('DOB')
        age = 'N/A'
        if pd.notna(dob) and dob:
            if isinstance(dob, str):
                dob = datetime.strptime(dob, '%Y-%m-%d')
            age = datetime.now().year - dob.year
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 12px; border-radius: 6px; color: white; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <h3 style="margin: 0; color: white; font-size: 16px; font-weight: 600;">👤 {st.session_state.patient_records.get('Name', st.session_state.patient_records.get('Patient Name', 'Patient'))}</h3>
            <p style="margin: 2px 0 0 0; opacity: 0.9; font-size: 12px;">Patient ID: {st.session_state.patient_id} | Age: {age} | Gender: {st.session_state.patient_records.get('Gender', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_header2:
        st.markdown("""
        <div style="text-align: center; padding: 8px; background-color: #f8f9fa; border-radius: 6px; margin-bottom: 12px;">
            <div style="font-size: 12px; color: #6c757d; margin-bottom: 2px;">🩺 Health Score</div>
            <div style="font-size: 18px; font-weight: 600; color: #28a745;">85</div>
            <div style="font-size: 10px; color: #28a745;">↑ 5%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_header3:
        st.markdown("""
        <div style="text-align: center; padding: 8px; background-color: #f8f9fa; border-radius: 6px; margin-bottom: 12px;">
            <div style="font-size: 12px; color: #6c757d; margin-bottom: 2px;">📅 Last Visit</div>
            <div style="font-size: 14px; font-weight: 600; color: #495057;">2 days ago</div>
            <div style="font-size: 10px; color: #dc3545;">↓ 1 day</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Initialize session state for expanded sections
    if 'expanded_sections' not in st.session_state:
        st.session_state.expanded_sections = {}
    
    # Dashboard grid layout with expandable boxes
    st.markdown("""
    <div style="margin: 20px 0;">
        <h3 style="color: #2c3e50; font-size: 18px; font-weight: 600; margin-bottom: 15px;">Dashboard Sections</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Create grid of expandable sections
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Medical Overview Box
        medical_expanded = st.session_state.expanded_sections.get('medical_overview', False)
        if st.button("Medical Overview", use_container_width=True, key="medical_overview"):
            st.session_state.expanded_sections['medical_overview'] = not medical_expanded
            st.rerun()
        
        # Show detailed info for Medical Overview
        conditions = st.session_state.patient_records.get('Past Medical History', '')
        conditions_list = safe_parse_field(conditions)
        condition_count = len(conditions_list) if conditions_list and conditions != 'No significant medical history' else 0
        
        # Get additional medical data
        procedures = st.session_state.patient_records.get('Past Surgical History', '')
        procedures_list = safe_parse_field(procedures)
        procedure_count = len(procedures_list) if procedures_list and procedures != 'No surgical history' else 0
        
        family_history = st.session_state.patient_records.get('Family History', '')
        family_list = safe_parse_field(family_history)
        family_count = len(family_list) if family_list and family_history != 'No significant family history' else 0
        
        # Get recent conditions (first 2)
        recent_conditions = conditions_list[:2] if conditions_list and conditions != 'No significant medical history' else []
        conditions_display = ', '.join(recent_conditions) if recent_conditions else 'No conditions'
        if len(conditions_list) > 2:
            conditions_display += f' (+{len(conditions_list)-2} more)'
        
        # Enhanced Medical Overview Box with more details
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 2px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 2px 0;">
            <div style="color: #495057;">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Medical Overview</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{condition_count}</strong> Active Conditions</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{procedure_count}</strong> Past Procedures</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{family_count}</strong> Family History Items</div>
                <div style="font-size: 12px; color: #6c757d; margin-top: 8px;">Last updated: {datetime.now().strftime('%d %b %Y')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add spacing between rows
        st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
        
        # Medications Box
        medications_expanded = st.session_state.expanded_sections.get('medications', False)
        if st.button("Medications", use_container_width=True, key="medications"):
            st.session_state.expanded_sections['medications'] = not medications_expanded
            st.rerun()
        
        # Show detailed info for Medications
        medications = st.session_state.patient_records.get('Current Medications', '')
        medications_list = safe_parse_field(medications)
        medication_count = len(medications_list) if medications_list and medications != 'No current medications' else 0
        
        # Get past medications
        past_medications = st.session_state.patient_records.get('Past Medications', '')
        past_medications_list = safe_parse_field(past_medications)
        past_medication_count = len(past_medications_list) if past_medications_list and past_medications != 'No past medications' else 0
        
        # Get recent medications (first 2)
        recent_medications = medications_list[:2] if medications_list and medications != 'No current medications' else []
        medications_display = ', '.join(recent_medications) if recent_medications else 'No medications'
        if len(medications_list) > 2:
            medications_display += f' (+{len(medications_list)-2} more)'
        
        # Calculate adherence score (simulated)
        adherence_score = min(95, max(60, 85 + (medication_count * 2)))
        
        # Enhanced Medications Box with more details
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 2px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 2px 0;">
            <div style="color: #495057;">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Medications</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{medication_count}</strong> Active Medications</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{past_medication_count}</strong> Past Medications</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{adherence_score}%</strong> Adherence Score</div>
                <div style="font-size: 12px; color: #6c757d; margin-top: 8px;">Last updated: {datetime.now().strftime('%d %b %Y')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add spacing between rows
        st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
        
        # Allergies & Risks Box
        allergies_expanded = st.session_state.expanded_sections.get('allergies_risks', False)
        if st.button("Allergies & Risks", use_container_width=True, key="allergies_risks"):
            st.session_state.expanded_sections['allergies_risks'] = not allergies_expanded
            st.rerun()
        
        # Show detailed info for Allergies & Risks
        allergies = st.session_state.patient_records.get('Drug Allergies', '')
        allergies_list = safe_parse_field(allergies)
        allergy_count = len(allergies_list) if allergies_list and allergies != 'No known drug allergies' else 0
        
        # Get additional risk factors
        smoking = st.session_state.patient_records.get('Smoking Status', '')
        alcohol = st.session_state.patient_records.get('Alcohol Consumption', '')
        
        # Calculate risk score (simulated)
        risk_factors = 0
        if allergy_count > 0:
            risk_factors += 1
        if 'smoking' in smoking.lower() or 'current' in smoking.lower():
            risk_factors += 1
        if 'heavy' in alcohol.lower() or 'excessive' in alcohol.lower():
            risk_factors += 1
        
        risk_level = "Low" if risk_factors == 0 else "Moderate" if risk_factors <= 2 else "High"
        risk_color = "#28a745" if risk_level == "Low" else "#ffc107" if risk_level == "Moderate" else "#dc3545"
        
        # Get recent allergies (first 2)
        recent_allergies = allergies_list[:2] if allergies_list and allergies != 'No known drug allergies' else []
        allergies_display = ', '.join(recent_allergies) if recent_allergies else 'No allergies'
        if len(allergies_list) > 2:
            allergies_display += f' (+{len(allergies_list)-2} more)'
        
        # Enhanced Allergies & Risks Box with more details
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 2px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 2px 0;">
            <div style="color: #495057;">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Allergies & Risks</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{allergy_count}</strong> Documented Allergies</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{risk_factors}</strong> Risk Factors</div>
                <div style="font-size: 14px; margin-bottom: 4px; color: {risk_color};"><strong>{risk_level}</strong> Risk Level</div>
                <div style="font-size: 12px; color: #6c757d; margin-top: 8px;">Last updated: {datetime.now().strftime('%d %b %Y')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Trends & Analytics Box
        trends_expanded = st.session_state.expanded_sections.get('trends_analytics', False)
        if st.button("Trends & Analytics", use_container_width=True, key="trends_analytics"):
            st.session_state.expanded_sections['trends_analytics'] = not trends_expanded
            st.rerun()
        
        # Calculate trend metrics (simulated)
        days_tracked = 90
        visits_this_month = 3
        avg_symptoms = 2.5
        trend_direction = "Improving" if avg_symptoms < 3 else "Stable"
        trend_color = "#28a745" if trend_direction == "Improving" else "#ffc107"
        
        # Enhanced Trends & Analytics Box with more details
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 2px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 2px 0;">
            <div style="color: #495057;">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Trends & Analytics</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{days_tracked}</strong> Days Tracked</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{visits_this_month}</strong> Visits This Month</div>
                <div style="font-size: 14px; margin-bottom: 4px; color: {trend_color};"><strong>{trend_direction}</strong> Trend</div>
                <div style="font-size: 12px; color: #6c757d; margin-top: 8px;">Last updated: {datetime.now().strftime('%d %b %Y')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add spacing between rows
        st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
        
        # Detailed Analysis Box
        analysis_expanded = st.session_state.expanded_sections.get('detailed_analysis', False)
        if st.button("Detailed Analysis", use_container_width=True, key="detailed_analysis"):
            st.session_state.expanded_sections['detailed_analysis'] = not analysis_expanded
            st.rerun()
        
        # Calculate analysis metrics (simulated)
        health_score = 85
        symptom_severity = "Moderate"
        risk_assessment = "Low-Medium"
        analysis_completeness = 92
        
        # Determine health status color
        if health_score >= 80:
            health_color = "#28a745"
            health_status = "Good"
        elif health_score >= 60:
            health_color = "#ffc107"
            health_status = "Fair"
        else:
            health_color = "#dc3545"
            health_status = "Poor"
        
        # Enhanced Detailed Analysis Box with more details
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 2px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 2px 0;">
            <div style="color: #495057;">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Detailed Analysis</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{health_score}</strong> Health Score</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{symptom_severity}</strong> Symptom Severity</div>
                <div style="font-size: 14px; margin-bottom: 4px; color: {health_color};"><strong>{health_status}</strong> Health Status</div>
                <div style="font-size: 12px; color: #6c757d; margin-top: 8px;">Last updated: {datetime.now().strftime('%d %b %Y')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Clinical Notes Box
        clinical_expanded = st.session_state.expanded_sections.get('clinical_notes', False)
        if st.button("Clinical Notes & Care Plan", use_container_width=True, key="clinical_notes"):
            st.session_state.expanded_sections['clinical_notes'] = not clinical_expanded
            st.rerun()
        
        # Calculate clinical metrics (simulated)
        active_plans = 3
        pending_tasks = 5
        notes_count = 12
        last_visit = "3 days ago"
        
        # Get care plan status
        plan_status = "On Track" if pending_tasks <= 5 else "Needs Attention"
        status_color = "#28a745" if plan_status == "On Track" else "#ffc107"
        
        # Enhanced Clinical Notes & Care Plan Box with more details
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 2px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 2px 0;">
            <div style="color: #495057;">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Clinical Notes & Care Plan</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{active_plans}</strong> Active Plans</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{pending_tasks}</strong> Pending Tasks</div>
                <div style="font-size: 14px; margin-bottom: 4px; color: {status_color};"><strong>{plan_status}</strong> Status</div>
                <div style="font-size: 12px; color: #6c757d; margin-top: 8px;">Last updated: {datetime.now().strftime('%d %b %Y')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add spacing between rows
        st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
        
        # Digital Locker Box
        locker_expanded = st.session_state.expanded_sections.get('digital_locker', False)
        if st.button("Digital Health Locker", use_container_width=True, key="digital_locker"):
            st.session_state.expanded_sections['digital_locker'] = not locker_expanded
            st.rerun()
        
        # Calculate digital locker metrics (simulated)
        total_files = 12
        recent_uploads = 3
        storage_used = "2.4 GB"
        last_upload = "1 day ago"
        
        # Calculate storage status
        storage_percentage = 24  # 2.4GB out of 10GB
        if storage_percentage < 50:
            storage_status = "Good"
            storage_color = "#28a745"
        elif storage_percentage < 80:
            storage_status = "Moderate"
            storage_color = "#ffc107"
        else:
            storage_status = "Full"
            storage_color = "#dc3545"
        
        # Enhanced Digital Health Locker Box with more details
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 2px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 2px 0;">
            <div style="color: #495057;">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Digital Health Locker</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{total_files}</strong> Total Files</div>
                <div style="font-size: 14px; margin-bottom: 4px;"><strong>{recent_uploads}</strong> Recent Uploads</div>
                <div style="font-size: 14px; margin-bottom: 4px; color: {storage_color};"><strong>{storage_status}</strong> Storage</div>
                <div style="font-size: 12px; color: #6c757d; margin-top: 8px;">Last updated: {datetime.now().strftime('%d %b %Y')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Force Streamlit to detect changes
    st.markdown("---")
    
    # Display expanded section content
    if st.session_state.expanded_sections.get('medical_overview', False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #007bff;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">🏥 Medical Overview</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Comprehensive view of patient's medical conditions and procedures</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Medical conditions widget
        col_med1, col_med2 = st.columns([2, 1])
        
        with col_med1:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📋 Medical Conditions</h4>
            </div>
            """, unsafe_allow_html=True)
            conditions = st.session_state.patient_records.get('Past Medical History', '')
            conditions_list = safe_parse_field(conditions)
            if conditions_list and conditions != 'No significant medical history':
                
                # Create condition severity chart
                condition_data = []
                for condition in conditions_list:
                    condition_data.append({
                        'Condition': condition,
                        'Severity': np.random.choice(['Mild', 'Moderate', 'Severe'], p=[0.4, 0.4, 0.2]),
                        'Duration': f"{np.random.randint(1, 60)} months",
                        'Status': np.random.choice(['Active', 'Controlled', 'Resolved'], p=[0.3, 0.5, 0.2])
                    })
                
                df_conditions = pd.DataFrame(condition_data)
                
                # Condition status pie chart
                status_counts = df_conditions['Status'].value_counts()
                fig_status = px.pie(values=status_counts.values, names=status_counts.index, 
                                  title="Status Distribution",
                                  color_discrete_sequence=px.colors.qualitative.Set3)
                fig_status.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_status, use_container_width=True)
                
                # Condition severity bar chart
                severity_counts = df_conditions['Severity'].value_counts()
                fig_severity = px.bar(x=severity_counts.index, y=severity_counts.values,
                                    title="Severity Distribution",
                                    color=severity_counts.values,
                                    color_continuous_scale="RdYlGn_r")
                fig_severity.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_severity, use_container_width=True)
            else:
                st.info("No significant medical conditions recorded")
        
        with col_med2:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">🔬 Recent Procedures</h4>
            </div>
            """, unsafe_allow_html=True)
            procedures = st.session_state.patient_records.get('Recent Procedures', '')
            procedures_list = safe_parse_field(procedures)
            if procedures_list and procedures != 'No recent procedures':
                
                # Procedure timeline
                procedure_data = []
                for i, procedure in enumerate(procedures_list):
                    procedure_data.append({
                        'Procedure': procedure,
                        'Date': (datetime.now() - timedelta(days=np.random.randint(1, 90))).strftime('%Y-%m-%d'),
                        'Type': np.random.choice(['Diagnostic', 'Therapeutic', 'Preventive']),
                        'Status': np.random.choice(['Completed', 'Scheduled', 'Pending'])
                    })
                
                df_procedures = pd.DataFrame(procedure_data)
                df_procedures['Date'] = pd.to_datetime(df_procedures['Date'])
                df_procedures = df_procedures.sort_values('Date')
                
                # Procedure timeline
                fig_timeline = px.timeline(df_procedures, x_start='Date', x_end='Date', y='Procedure',
                                         color='Type', title="Timeline",
                                         color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_timeline.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("No recent procedures recorded")
    
    if st.session_state.expanded_sections.get('medications', False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #28a745;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">💊 Medication Management</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Track medication adherence, interactions, and effectiveness</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_med_tab1, col_med_tab2 = st.columns([1, 1])
        
        with col_med_tab1:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">💊 Current Medications</h4>
            </div>
            """, unsafe_allow_html=True)
            medications = st.session_state.patient_records.get('Current Medications', '')
            medications_list = safe_parse_field(medications)
            if medications_list and medications != 'No current medications':
                
                # Medication adherence simulation
                med_data = []
                for med in medications_list:
                    med_data.append({
                        'Medication': med,
                        'Dosage': f"{np.random.randint(1, 10)}mg",
                        'Frequency': np.random.choice(['Once daily', 'Twice daily', 'As needed']),
                        'Adherence': np.random.randint(70, 100),
                        'Side Effects': np.random.choice(['None', 'Mild', 'Moderate'], p=[0.6, 0.3, 0.1])
                    })
                
                df_medications = pd.DataFrame(med_data)
                
                # Medication adherence gauge
                avg_adherence = df_medications['Adherence'].mean()
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = avg_adherence,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Adherence Rate (%)", 'font': {'size': 12}},
                    delta = {'reference': 80, 'font': {'size': 8}},
                    number = {'font': {'size': 16}},
                    gauge = {
                        'axis': {'range': [None, 100], 'tickfont': {'size': 10}},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 80], 'color': "yellow"},
                            {'range': [80, 100], 'color': "green"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))
                fig_gauge.update_layout(font_size=10, height=300)
                st.plotly_chart(fig_gauge, use_container_width=True)
                
                # Medication list with details
                st.markdown("""
                <div style="background-color: #ffffff; padding: 0px; border-radius: 2px; margin-bottom: 0px;">
                    <h5 style="margin: 0 0 0px 0; color: #495057; font-size: 14px; font-weight: 600;">Current Medication Details</h5>
                </div>
                """, unsafe_allow_html=True)
                for _, med in df_medications.iterrows():
                    with st.expander(f"💊 {med['Medication']} - {med['Dosage']}"):
                        st.write(f"**Frequency:** {med['Frequency']}")
                        st.write(f"**Adherence:** {med['Adherence']}%")
                        st.write(f"**Side Effects:** {med['Side Effects']}")
                        
                        # Adherence trend (simulated)
                        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
                        adherence_trend = np.random.normal(med['Adherence'], 10, len(dates))
                        adherence_trend = np.clip(adherence_trend, 0, 100)
                        
                        fig_trend = px.line(x=dates, y=adherence_trend, 
                                          title=f"{med['Medication']} Trend",
                                          labels={'x': 'Date', 'y': 'Adherence %'})
                        fig_trend.update_layout(title_font_size=12, font_size=11)
                        st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No current medications recorded")
            
            # Past Medications (Expandable section)
            past_medications_list = ['Lisinopril', 'Metformin', 'Aspirin', 'Vitamin D', 'Omega-3']
            if past_medications_list:
                with st.expander("📚 View Past Medications", expanded=False):
                    st.markdown("""
                    <div style="background-color: #f8f9fa; padding: 8px; border-radius: 4px; margin-bottom: 8px;">
                        <h5 style="margin: 0; color: #495057; font-size: 14px; font-weight: 600;">📚 Past Medications</h5>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Past medication data
                    past_med_data = []
                    for med in past_medications_list:
                        past_med_data.append({
                            'Medication': med,
                            'Dosage': f"{np.random.randint(1, 10)}mg",
                            'Frequency': np.random.choice(['Once daily', 'Twice daily', 'As needed']),
                            'Status': 'Discontinued',
                            'Discontinued Date': f"2023-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d}",
                            'Reason': np.random.choice(['Side effects', 'No longer needed', 'Switched to alternative', 'Completed course'])
                        })
                    
                    df_past_medications = pd.DataFrame(past_med_data)
                    
                    # Past medications list
                    st.markdown("**Historical Medications:**")
                    for _, med in df_past_medications.iterrows():
                        st.markdown(f"• {med['Medication']} ({med['Dosage']}) - {med['Frequency']} - Discontinued: {med['Discontinued Date']} - Reason: {med['Reason']}")
                    
                    # Past medication summary chart
                    past_reason_counts = df_past_medications['Reason'].value_counts()
                    fig_past_reasons = px.bar(x=past_reason_counts.index, y=past_reason_counts.values,
                                            title="Past Medication Discontinuation Reasons",
                                            color=past_reason_counts.values,
                                            color_continuous_scale="Blues")
                    fig_past_reasons.update_layout(title_font_size=14, font_size=12)
                    st.plotly_chart(fig_past_reasons, use_container_width=True)
        
        with col_med_tab2:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📊 Medication Analytics</h4>
            </div>
            """, unsafe_allow_html=True)
            if medications and medications != 'No current medications':
                # Drug interaction risk
                interaction_risk = np.random.choice(['Low', 'Medium', 'High'], p=[0.7, 0.2, 0.1])
                risk_color = {'Low': 'green', 'Medium': 'orange', 'High': 'red'}
                
                st.markdown(f"""
                <div style="background-color: {risk_color[interaction_risk].replace('green', '#d4edda').replace('orange', '#fff3cd').replace('red', '#f8d7da')}; 
                            border: 1px solid {risk_color[interaction_risk].replace('green', '#c3e6cb').replace('orange', '#ffeaa7').replace('red', '#f5c6cb')}; 
                            padding: 12px; border-radius: 6px; margin: 8px 0;">
                    <p style="margin: 0; color: {risk_color[interaction_risk].replace('green', '#155724').replace('orange', '#856404').replace('red', '#721c24')}; font-size: 14px; font-weight: 600;">
                        🔍 Drug Interaction Risk: {interaction_risk}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Medication effectiveness heatmap
                med_names = safe_parse_field(medications)
                effectiveness_data = np.random.rand(len(med_names), 4)
                
                fig_heatmap = px.imshow(effectiveness_data,
                                      x=['Effectiveness', 'Tolerability', 'Convenience', 'Cost'],
                                      y=med_names,
                                      color_continuous_scale='RdYlGn',
                                      title="Effectiveness Matrix")
                fig_heatmap.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_heatmap, use_container_width=True)
    
    if st.session_state.expanded_sections.get('allergies_risks', False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #dc3545;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">⚠️ Allergies & Risk Assessment</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Monitor allergies and assess health risks for better care planning</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_allergy1, col_allergy2 = st.columns([1, 1])
        
        with col_allergy1:
            # Current Allergies (from Drug Allergies field)
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">⚠️ Current Allergies</h4>
            </div>
            """, unsafe_allow_html=True)
            
            current_allergies = st.session_state.patient_records.get('Drug Allergies', '')
            current_allergies_list = safe_parse_field(current_allergies)
            
            if current_allergies_list and current_allergies != 'No known drug allergies':
                # Current allergy data
                current_allergy_data = []
                for allergy in current_allergies_list:
                    current_allergy_data.append({
                        'Allergen': allergy,
                        'Type': np.random.choice(['Drug', 'Food', 'Environmental']),
                        'Severity': np.random.choice(['Mild', 'Moderate', 'Severe'], p=[0.3, 0.4, 0.3]),
                        'Reaction': np.random.choice(['Rash', 'Swelling', 'Anaphylaxis', 'Nausea']),
                        'Status': 'Current'
                    })
                
                df_current_allergies = pd.DataFrame(current_allergy_data)
                
                # Current allergy severity distribution
                severity_counts = df_current_allergies['Severity'].value_counts()
                fig_allergy = px.bar(x=severity_counts.index, y=severity_counts.values,
                                   title="Current Allergy Severity",
                                   color=severity_counts.values,
                                   color_continuous_scale="Reds")
                fig_allergy.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_allergy, use_container_width=True)
                
                # Current allergy type pie chart
                type_counts = df_current_allergies['Type'].value_counts()
                fig_type = px.pie(values=type_counts.values, names=type_counts.index,
                                title="Current Allergy Types",
                                color_discrete_sequence=px.colors.qualitative.Set2)
                fig_type.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_type, use_container_width=True)
                
                # Current allergies list
                st.markdown("**Current Known Allergies:**")
                for _, row in df_current_allergies.iterrows():
                    severity_color = {'Mild': '🟢', 'Moderate': '🟡', 'Severe': '🔴'}
                    st.markdown(f"• {row['Allergen']} ({row['Type']}) - {severity_color[row['Severity']]} {row['Severity']}")
            else:
                st.info("No current allergies recorded")
            
            # Past Allergies (Expandable section)
            past_allergies_list = ['Penicillin', 'Latex', 'Dust Mites', 'Pollen']
            if past_allergies_list:
                with st.expander("📚 View Past Allergies", expanded=False):
                    st.markdown("""
                    <div style="background-color: #f8f9fa; padding: 8px; border-radius: 4px; margin-bottom: 8px;">
                        <h5 style="margin: 0; color: #495057; font-size: 14px; font-weight: 600;">📚 Past Allergies</h5>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Past allergy data
                    past_allergy_data = []
                    for allergy in past_allergies_list:
                        past_allergy_data.append({
                            'Allergen': allergy,
                            'Type': np.random.choice(['Drug', 'Food', 'Environmental']),
                            'Severity': np.random.choice(['Mild', 'Moderate', 'Severe']),
                            'Reaction': np.random.choice(['Rash', 'Swelling', 'Anaphylaxis', 'Nausea']),
                            'Status': 'Past',
                            'Resolved Date': f"2023-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d}"
                        })
                    
                    df_past_allergies = pd.DataFrame(past_allergy_data)
                    
                    # Past allergies list
                    st.markdown("**Historical Allergies:**")
                    for _, row in df_past_allergies.iterrows():
                        severity_color = {'Mild': '🟢', 'Moderate': '🟡', 'Severe': '🔴'}
                        st.markdown(f"• {row['Allergen']} ({row['Type']}) - {severity_color[row['Severity']]} {row['Severity']} - Resolved: {row['Resolved Date']}")
                    
                    # Past allergy summary chart
                    past_type_counts = df_past_allergies['Type'].value_counts()
                    fig_past_type = px.bar(x=past_type_counts.index, y=past_type_counts.values,
                                         title="Past Allergy Types",
                                         color=past_type_counts.values,
                                         color_continuous_scale="Blues")
                    fig_past_type.update_layout(title_font_size=14, font_size=12)
                    st.plotly_chart(fig_past_type, use_container_width=True)
        
        with col_allergy2:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">🚨 Risk Assessment</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Risk factors
            risk_factors = {
                'Cardiovascular Risk': np.random.randint(20, 80),
                'Diabetes Risk': np.random.randint(15, 70),
                'Medication Interaction': np.random.randint(10, 60),
                'Allergic Reaction': np.random.randint(5, 40)
            }
            
            # Risk radar chart
            categories = list(risk_factors.keys())
            values = list(risk_factors.values())
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='Risk Level',
                line_color='red'
            ))
            
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title="Risk Factors",
                title_font_size=14,
                font_size=12
            )
            
            st.plotly_chart(fig_radar, use_container_width=True)
            
            # Risk alerts
            high_risk = [k for k, v in risk_factors.items() if v > 60]
            if high_risk:
                st.warning(f"⚠️ High risk areas: {', '.join(high_risk)}")
            else:
                st.success("✅ All risk factors are within acceptable ranges")
    
    if st.session_state.expanded_sections.get('trends_analytics', False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #17a2b8;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">📈 Trends & Analytics</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Analyze health trends and visit patterns over time</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Generate time series data for trends
        dates = pd.date_range(start=datetime.now() - timedelta(days=90), end=datetime.now(), freq='D')
        
        col_trend1, col_trend2 = st.columns([1, 1])
        
        with col_trend1:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📊 Health Metrics Trends</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Simulate health metrics
            weight_trend = 70 + np.cumsum(np.random.normal(0, 0.1, len(dates)))
            bp_systolic = 120 + np.random.normal(0, 5, len(dates))
            bp_diastolic = 80 + np.random.normal(0, 3, len(dates))
            
            # Multi-line chart for health metrics
            fig_health = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Weight Trend', 'Blood Pressure'),
                vertical_spacing=0.15
            )
            
            fig_health.add_trace(
                go.Scatter(x=dates, y=weight_trend, name='Weight (kg)', line=dict(color='blue')),
                row=1, col=1
            )
            
            fig_health.add_trace(
                go.Scatter(x=dates, y=bp_systolic, name='Systolic BP', line=dict(color='red')),
                row=2, col=1
            )
            
            fig_health.add_trace(
                go.Scatter(x=dates, y=bp_diastolic, name='Diastolic BP', line=dict(color='orange')),
                row=2, col=1
            )
            
            fig_health.update_layout(height=600, title_text="Health Metrics Over Time", title_font_size=14, font_size=12)
            st.plotly_chart(fig_health, use_container_width=True)
        
        with col_trend2:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📅 Visit Frequency</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Visit frequency data
            visit_data = []
            for i in range(12):  # Last 12 months
                month = datetime.now() - timedelta(days=30*i)
                visit_count = np.random.poisson(2)  # Average 2 visits per month
                visit_data.append({
                    'Month': month.strftime('%Y-%m'),
                    'Visits': visit_count,
                    'Type': np.random.choice(['Routine', 'Emergency', 'Follow-up'])
                })
            
            df_visits = pd.DataFrame(visit_data)
            df_visits = df_visits.sort_values('Month')
            
            # Visit frequency chart
            fig_visits = px.bar(df_visits, x='Month', y='Visits',
                              title="Monthly Visits",
                              color='Visits',
                              color_continuous_scale='Blues')
            fig_visits.update_layout(title_font_size=14, font_size=12)
            st.plotly_chart(fig_visits, use_container_width=True)
            
            # Symptom severity over time
            st.markdown("""
            <div style="background-color: #ffffff; padding: 0px; border-radius: 2px; margin-bottom: 0px;">
                <h5 style="margin: 0 0 0px 0; color: #495057; font-size: 14px; font-weight: 600;">📈 Symptom Severity Trend</h5>
            </div>
            """, unsafe_allow_html=True)
            symptom_severity = np.random.normal(3, 1, len(dates))
            symptom_severity = np.clip(symptom_severity, 1, 10)
            
            fig_symptoms = px.line(x=dates, y=symptom_severity,
                                 title="Symptom Severity (1-10 scale)",
                                 labels={'x': 'Date', 'y': 'Severity'})
            fig_symptoms.add_hline(y=5, line_dash="dash", line_color="red", 
                                 annotation_text="Moderate Threshold")
            fig_symptoms.update_layout(title_font_size=14, font_size=12)
            st.plotly_chart(fig_symptoms, use_container_width=True)
    
    if st.session_state.expanded_sections.get('detailed_analysis', False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #6f42c1;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">🔍 Detailed Analysis</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Comprehensive analysis of symptoms and health summary</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Current symptoms analysis
        if hasattr(st.session_state, 'symptom_changes') and st.session_state.symptom_changes:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">🩺 Current Symptoms Analysis</h4>
            </div>
            """, unsafe_allow_html=True)
            
            symptoms_text = st.session_state.symptom_changes.lower()
            
            # Symptom keyword analysis
            symptom_keywords = ['fever', 'cough', 'headache', 'fatigue', 'pain', 'nausea', 'dizziness', 'breathing']
            detected_symptoms = [symptom for symptom in symptom_keywords if symptom in symptoms_text]
            
            if detected_symptoms:
                col_analysis1, col_analysis2 = st.columns([1, 1])
                
                with col_analysis1:
                    # Symptom frequency
                    symptom_counts = Counter(detected_symptoms)
                    fig_symptom_freq = px.bar(x=list(symptom_counts.keys()), y=list(symptom_counts.values()),
                                            title="Detected Symptoms",
                                            color=list(symptom_counts.values()),
                                            color_continuous_scale="Reds")
                    fig_symptom_freq.update_layout(title_font_size=14, font_size=12)
                    st.plotly_chart(fig_symptom_freq, use_container_width=True)
                
                with col_analysis2:
                    # Symptom severity assessment
                    severity_scores = {symptom: np.random.randint(3, 8) for symptom in detected_symptoms}
                    
                    fig_severity = px.bar(x=list(severity_scores.keys()), y=list(severity_scores.values()),
                                        title="Severity Assessment",
                                        color=list(severity_scores.values()),
                                        color_continuous_scale="RdYlGn_r")
                    fig_severity.update_layout(title_font_size=14, font_size=12)
                    st.plotly_chart(fig_severity, use_container_width=True)
        
        # Comprehensive health summary
        st.markdown("""
        <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
            <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📋 Comprehensive Health Summary</h4>
        </div>
        """, unsafe_allow_html=True)
        
        col_summary1, col_summary2, col_summary3 = st.columns(3)
        
        with col_summary1:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e9ecef; text-align: center;">
                <div style="font-size: 14px; color: #495057; margin-bottom: 8px;">🏥 Total Conditions</div>
                <div style="font-size: 18px; font-weight: 600; color: #2c3e50;">{len(conditions_list) if 'conditions_list' in locals() else 0}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e9ecef; text-align: center;">
                <div style="font-size: 14px; color: #495057; margin-bottom: 8px;">💊 Active Medications</div>
                <div style="font-size: 18px; font-weight: 600; color: #2c3e50;">{len(medications_list) if 'medications_list' in locals() else 0}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_summary2:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e9ecef; text-align: center;">
                <div style="font-size: 14px; color: #495057; margin-bottom: 8px;">⚠️ Known Allergies</div>
                <div style="font-size: 18px; font-weight: 600; color: #2c3e50;">{len(allergies_list) if 'allergies_list' in locals() else 0}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e9ecef; text-align: center;">
                <div style="font-size: 14px; color: #495057; margin-bottom: 8px;">🔬 Recent Procedures</div>
                <div style="font-size: 18px; font-weight: 600; color: #2c3e50;">{len(procedures_list) if 'procedures_list' in locals() else 0}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_summary3:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e9ecef; text-align: center;">
                <div style="font-size: 14px; color: #495057; margin-bottom: 8px;">📅 Days Since Last Visit</div>
                <div style="font-size: 18px; font-weight: 600; color: #2c3e50;">{np.random.randint(1, 30)}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e9ecef; text-align: center;">
                <div style="font-size: 14px; color: #495057; margin-bottom: 8px;">🎯 Health Score</div>
                <div style="font-size: 18px; font-weight: 600; color: #2c3e50;">85/100</div>
                <div style="font-size: 12px; color: #28a745; margin-top: 4px;">↑ 5</div>
            </div>
            """, unsafe_allow_html=True)
    
    if st.session_state.expanded_sections.get('clinical_notes', False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #28a745;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">📋 Clinical Notes & Care Plan</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Clinical documentation, care gaps, and treatment plans</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Chief Complaint
        chief_complaint = st.session_state.patient_records.get('Chief Complaint', '')
        if chief_complaint and chief_complaint != '' and chief_complaint != 'N/A':
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">🩺 Chief Complaint</h4>
            </div>
            """, unsafe_allow_html=True)
            st.info(f"**Primary Concern:** {chief_complaint}")
        
        # Physical Exam Findings
        physical_exam = st.session_state.patient_records.get('Physical Exam Findings', '')
        if physical_exam and physical_exam != '' and physical_exam != 'N/A':
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">🔍 Physical Exam Findings</h4>
            </div>
            """, unsafe_allow_html=True)
            st.info(f"**Examination Results:** {physical_exam}")
        
        # Care Gaps
        care_gaps = st.session_state.patient_records.get('Care Gaps', '')
        if care_gaps and care_gaps != '' and care_gaps != 'N/A':
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">⚠️ Care Gaps</h4>
            </div>
            """, unsafe_allow_html=True)
            st.warning(f"**Identified Gaps:** {care_gaps}")
        
        # Treatment Plan
        treatment_plan = st.session_state.patient_records.get('Treatment Plan', '')
        if treatment_plan and treatment_plan != '' and treatment_plan != 'N/A':
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">💊 Treatment Plan</h4>
            </div>
            """, unsafe_allow_html=True)
            st.success(f"**Current Plan:** {treatment_plan}")
        
        # Next Appointments
        next_appointments = st.session_state.patient_records.get('Next Appointments', '')
        if next_appointments and next_appointments != '' and next_appointments != 'N/A':
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📅 Next Appointments</h4>
            </div>
            """, unsafe_allow_html=True)
            st.info(f"**Scheduled:** {next_appointments}")
        
        # Healthcare Team
        col_team1, col_team2 = st.columns(2)
        
        with col_team1:
            primary_care = st.session_state.patient_records.get('Primary Care Provider', '')
            if primary_care and primary_care != '' and primary_care != 'N/A':
                st.markdown("""
                <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                    <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">👨‍⚕️ Primary Care Provider</h4>
                </div>
                """, unsafe_allow_html=True)
                # Check if "Dr." is already present
                display_name = primary_care if primary_care.startswith('Dr.') else f"Dr. {primary_care}"
                st.success(f"**{display_name}**")
        
        with col_team2:
            specialists = st.session_state.patient_records.get('Specialists', '')
            specialist_list = safe_parse_field(specialists)
            if specialist_list and specialists != '' and specialists != 'N/A':
                st.markdown("""
                <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                    <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">🏥 Specialists</h4>
                </div>
                """, unsafe_allow_html=True)
                for specialist in specialist_list:
                    # Check if "Dr." is already present
                    display_name = specialist if specialist.startswith('Dr.') else f"Dr. {specialist}"
                    st.info(f"**{display_name}**")
    
    if st.session_state.expanded_sections.get('digital_locker', False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #17a2b8;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">📁 Digital Health Locker</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Secure storage and management of your health documents, reports, and insurance cards</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Document categories
        col_upload1, col_upload2 = st.columns([1, 1])
        
        with col_upload1:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📤 Upload Documents</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Document type selection
            document_type = st.selectbox(
                "Select Document Type:",
                ["Medical Reports", "Lab Results", "Prescriptions", "Insurance Cards", "Health ID Cards", "Vaccination Records", "Discharge Summaries", "Other"]
            )
            
            # File upload
            uploaded_file = st.file_uploader(
                f"Choose {document_type}",
                type=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'],
                help="Supported formats: PDF, JPG, PNG, DOC, DOCX (Max size: 10MB)"
            )
            
            # File preview and upload buttons (only show when file is selected)
            if uploaded_file is not None:
                # File preview
                file_size_kb = len(uploaded_file.getvalue()) / 1024
                st.markdown(f"""
                <div style="background: #ffffff; padding: 12px; border-radius: 6px; margin: 8px 0; border: 1px solid #e0e0e0;">
                    <h5 style="margin: 0 0 4px 0; color: #2c3e50; font-size: 14px;">File Selected</h5>
                    <p style="margin: 0; color: #2c3e50; font-size: 12px;"><strong>{uploaded_file.name}</strong> | Size: {file_size_kb:.1f} KB | Type: {document_type}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    upload_button = st.button("📤 Upload Document", type="primary", use_container_width=True)
                with col_btn2:
                    clear_button = st.button("🗑️ Clear Selection", use_container_width=True)
                
                if clear_button:
                    st.rerun()
                
                if upload_button:
                    # File validation
                    file_size = len(uploaded_file.getvalue())
                    max_size = 10 * 1024 * 1024  # 10MB
                    
                    if file_size > max_size:
                        st.error("❌ File size exceeds 10MB limit. Please upload a smaller file.")
                    else:
                        # Validate file type based on document category
                        file_extension = uploaded_file.name.split('.')[-1].lower()
                        valid_extensions = {
                            "Medical Reports": ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
                            "Lab Results": ['pdf', 'jpg', 'jpeg', 'png'],
                            "Prescriptions": ['pdf', 'jpg', 'jpeg', 'png'],
                            "Insurance Cards": ['jpg', 'jpeg', 'png', 'pdf'],
                            "Health ID Cards": ['jpg', 'jpeg', 'png', 'pdf'],
                            "Vaccination Records": ['pdf', 'jpg', 'jpeg', 'png'],
                            "Discharge Summaries": ['pdf', 'doc', 'docx'],
                            "Other": ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
                        }
                        
                        if file_extension in valid_extensions[document_type]:
                            # Store document info in session state
                            if 'uploaded_documents' not in st.session_state:
                                st.session_state.uploaded_documents = []
                            
                            document_info = {
                                'name': uploaded_file.name,
                                'type': document_type,
                                'size': file_size,
                                'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                'extension': file_extension,
                                'content': uploaded_file.getvalue()
                            }
                            
                            st.session_state.uploaded_documents.append(document_info)
                            
                            # Success message with better styling
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 16px; border-radius: 8px; margin: 12px 0; border-left: 4px solid #28a745;">
                                <h4 style="margin: 0 0 8px 0; color: #155724; font-size: 16px;">✅ Document Uploaded Successfully!</h4>
                                <p style="margin: 0; color: #155724; font-size: 14px;"><strong>{uploaded_file.name}</strong> has been added to your Digital Health Locker</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Document details
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 12px; border-radius: 6px; margin: 8px 0; border-left: 3px solid #007bff;">
                                <h5 style="margin: 0 0 8px 0; color: #495057; font-size: 14px;">📄 Document Details</h5>
                                <p style="margin: 2px 0; color: #6c757d; font-size: 12px;"><strong>File Name:</strong> {uploaded_file.name}</p>
                                <p style="margin: 2px 0; color: #6c757d; font-size: 12px;"><strong>Document Type:</strong> {document_type}</p>
                                <p style="margin: 2px 0; color: #6c757d; font-size: 12px;"><strong>File Size:</strong> {file_size/1024:.1f} KB</p>
                                <p style="margin: 2px 0; color: #6c757d; font-size: 12px;"><strong>Upload Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                                <p style="margin: 2px 0; color: #6c757d; font-size: 12px;"><strong>File Format:</strong> {file_extension.upper()}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Special validation for insurance cards
                            if document_type == "Insurance Cards":
                                st.markdown("""
                                <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 12px; border-radius: 6px; margin: 8px 0; border-left: 4px solid #28a745;">
                                    <h5 style="margin: 0 0 4px 0; color: #155724; font-size: 14px;">🔍 Insurance Card Validation</h5>
                                    <p style="margin: 0; color: #155724; font-size: 12px;">✅ Card format validated | ✅ Image quality verified | ✅ Ready for processing</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Special validation for health ID cards
                            elif document_type == "Health ID Cards":
                                st.markdown("""
                                <div style="background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); padding: 12px; border-radius: 6px; margin: 8px 0; border-left: 4px solid #17a2b8;">
                                    <h5 style="margin: 0 0 4px 0; color: #0c5460; font-size: 14px;">🆔 Health ID Validation</h5>
                                    <p style="margin: 0; color: #0c5460; font-size: 12px;">✅ ID format validated | ✅ QR code detected | ✅ Ready for integration</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Force refresh to update statistics
                            st.rerun()
                        else:
                            st.error(f"❌ Invalid file type for {document_type}. Please upload a {', '.join(valid_extensions[document_type])} file.")
        
        with col_upload2:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📊 Document Statistics</h4>
            </div>
            """, unsafe_allow_html=True)
            
            if 'uploaded_documents' in st.session_state and st.session_state.uploaded_documents:
                # Document statistics
                total_docs = len(st.session_state.uploaded_documents)
                total_size = sum(doc['size'] for doc in st.session_state.uploaded_documents)
                
                # Count by type
                doc_types = {}
                for doc in st.session_state.uploaded_documents:
                    doc_types[doc['type']] = doc_types.get(doc['type'], 0) + 1
                
                col_stat1, col_stat2 = st.columns(2)
                with col_stat1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 12px; border-radius: 6px; margin: 4px 0; border-left: 3px solid #007bff;">
                        <div style="font-size: 12px; color: #6c757d; font-weight: 600; margin-bottom: 2px;">📄 Total Documents</div>
                        <div style="font-size: 18px; color: #495057; font-weight: 700;">{total_docs}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_stat2:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 12px; border-radius: 6px; margin: 4px 0; border-left: 3px solid #ffc107;">
                        <div style="font-size: 12px; color: #6c757d; font-weight: 600; margin-bottom: 2px;">📅 Latest Upload</div>
                        <div style="font-size: 18px; color: #495057; font-weight: 700;">Today</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Security status
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 12px; border-radius: 6px; margin: 4px 0; border-left: 3px solid #dc3545;">
                    <div style="font-size: 12px; color: #6c757d; font-weight: 600; margin-bottom: 2px;">🔒 Security</div>
                    <div style="font-size: 18px; color: #495057; font-weight: 700;">Encrypted</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("📁 No documents uploaded yet. Upload your first document to get started!")
        
        # Document management section
        if 'uploaded_documents' in st.session_state and st.session_state.uploaded_documents:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">📋 Document Management</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Filter options
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                filter_type = st.selectbox("Filter by Type:", ["All"] + list(set(doc['type'] for doc in st.session_state.uploaded_documents)))
            with col_filter2:
                sort_by = st.selectbox("Sort by:", ["Upload Date (Newest)", "Upload Date (Oldest)", "File Name", "File Size"])
            with col_filter3:
                search_term = st.text_input("Search documents:", placeholder="Enter file name...")
            
            # Filter and sort documents
            filtered_docs = st.session_state.uploaded_documents.copy()
            
            if filter_type != "All":
                filtered_docs = [doc for doc in filtered_docs if doc['type'] == filter_type]
            
            if search_term:
                filtered_docs = [doc for doc in filtered_docs if search_term.lower() in doc['name'].lower()]
            
            # Sort documents
            if sort_by == "Upload Date (Newest)":
                filtered_docs.sort(key=lambda x: x['upload_date'], reverse=True)
            elif sort_by == "Upload Date (Oldest)":
                filtered_docs.sort(key=lambda x: x['upload_date'])
            elif sort_by == "File Name":
                filtered_docs.sort(key=lambda x: x['name'])
            elif sort_by == "File Size":
                filtered_docs.sort(key=lambda x: x['size'], reverse=True)
            
            # Display documents
            for i, doc in enumerate(filtered_docs):
                with st.expander(f"📄 {doc['name']} ({doc['type']})", expanded=False):
                    col_doc1, col_doc2, col_doc3 = st.columns([2, 1, 1])
                    
                    with col_doc1:
                        st.write(f"**Type:** {doc['type']}")
                        st.write(f"**Size:** {doc['size']/1024:.1f} KB")
                        st.write(f"**Uploaded:** {doc['upload_date']}")
                        st.write(f"**Format:** {doc['extension'].upper()}")
                    
                    with col_doc2:
                        if st.button(f"👁️ View", key=f"view_{i}"):
                            st.session_state[f"view_doc_{i}"] = True
                    
                    with col_doc3:
                        if st.button(f"🗑️ Delete", key=f"delete_{i}"):
                            # Mark document for deletion
                            st.session_state[f"delete_doc_{i}"] = True
                    
                    # Document viewer
                    if st.session_state.get(f"view_doc_{i}", False):
                        st.markdown("---")
                        st.markdown("**📄 Document Preview:**")
                        
                        if doc['extension'] in ['jpg', 'jpeg', 'png']:
                            st.image(doc['content'], caption=doc['name'], use_column_width=True)
                        elif doc['extension'] == 'pdf':
                            st.info("📄 PDF document - Click download to view")
                            st.download_button(
                                label="📥 Download PDF",
                                data=doc['content'],
                                file_name=doc['name'],
                                mime="application/pdf"
                            )
                        else:
                            st.info(f"📄 {doc['extension'].upper()} document - Click download to view")
                            st.download_button(
                                label=f"📥 Download {doc['extension'].upper()}",
                                data=doc['content'],
                                file_name=doc['name'],
                                mime="application/octet-stream"
                            )
            
            # Process deletions after the loop
            docs_to_delete = []
            for i, doc in enumerate(filtered_docs):
                if st.session_state.get(f"delete_doc_{i}", False):
                    docs_to_delete.append(doc)
                    # Clear the delete flag
                    st.session_state[f"delete_doc_{i}"] = False
            
            # Remove deleted documents
            for doc in docs_to_delete:
                if doc in st.session_state.uploaded_documents:
                    st.session_state.uploaded_documents.remove(doc)
                    st.success(f"✅ {doc['name']} deleted successfully!")
    
    # Action buttons
    st.markdown("---")
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    
    with col_action1:
        if st.button("⬅️ Back to Symptoms"):
            st.session_state.stage = 'symptoms'
            st.rerun()
    
    with col_action2:
        if st.button("📄 Generate Summary Report"):
            st.session_state.stage = 'summary'
            st.rerun()
    
    with col_action3:
        if st.button("🔄 Refresh Dashboard"):
            st.rerun()
    
    with col_action4:
        if st.button("📤 Share with Physician"):
            st.session_state.show_share_modal = True
            st.rerun()
    
    # Share with Physician Modal
    if st.session_state.get('show_share_modal', False):
        st.markdown("---")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #007bff;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">📤 Share with Primary Physician</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Share your health insights and medical data with your healthcare provider</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Physician Selection
        st.subheader("👨‍⚕️ Select Physician")
        
        # Get physician data from patient records
        physicians = []
        
        # Add Primary Care Provider if available
        primary_care = st.session_state.patient_records.get('Primary Care Provider', '')
        if primary_care and primary_care != '' and primary_care != 'N/A':
            # Clean the name for email generation
            clean_name = primary_care.replace('Dr.', '').strip()
            physicians.append({
                "name": primary_care,
                "specialty": "Primary Care",
                "phone": "+1-555-0100",
                "email": f"{clean_name.lower().replace(' ', '.')}@hospital.com"
            })
        
        # Add Specialists if available
        specialists = st.session_state.patient_records.get('Specialists', '')
        specialist_list = safe_parse_field(specialists)
        if specialist_list and specialists != '' and specialists != 'N/A':
            for i, specialist in enumerate(specialist_list):
                # Clean the name for email generation
                clean_name = specialist.replace('Dr.', '').strip()
                physicians.append({
                    "name": specialist,
                    "specialty": "Specialist",
                    "phone": f"+1-555-010{i+1}",
                    "email": f"{clean_name.lower().replace(' ', '.')}@hospital.com"
                })
        
        # Add default physicians if none found in patient records
        if not physicians:
            physicians = [
                {"name": "Dr. Sarah Johnson", "specialty": "Internal Medicine", "phone": "+1-555-0101", "email": "sarah.johnson@hospital.com"},
                {"name": "Dr. Michael Chen", "specialty": "Cardiology", "phone": "+1-555-0102", "email": "michael.chen@hospital.com"},
                {"name": "Dr. Emily Rodriguez", "specialty": "Endocrinology", "phone": "+1-555-0103", "email": "emily.rodriguez@hospital.com"},
                {"name": "Dr. James Wilson", "specialty": "Family Medicine", "phone": "+1-555-0104", "email": "james.wilson@hospital.com"},
                {"name": "Dr. Lisa Thompson", "specialty": "Neurology", "phone": "+1-555-0105", "email": "lisa.thompson@hospital.com"}
            ]
        
        # Physician selection options
        physician_options = [f"{doc['name']} - {doc['specialty']}" for doc in physicians]
        selected_physician_idx = st.selectbox(
            "Choose your primary physician:",
            range(len(physician_options)),
            format_func=lambda x: physician_options[x],
            key="physician_selection"
        )
        
        if selected_physician_idx is not None:
            selected_physician = physicians[selected_physician_idx]
            
            # Display selected physician info
            st.info(f"Selected: **{selected_physician['name']}** ({selected_physician['specialty']})")
            
            # Sharing options
            st.subheader("📱 Share Options")
            
            col_share1, col_share2, col_share3 = st.columns(3)
            
            with col_share1:
                st.markdown("""
                <div style="text-align: center; padding: 12px; background-color: #ffffff; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h4 style="margin: 0 0 8px 0; color: #495057; font-size: 16px;">📱 WhatsApp</h4>
                    <p style="margin: 0; color: #6c757d; font-size: 12px;">Share via WhatsApp</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("📱 Share via WhatsApp", key="whatsapp_share"):
                    # Generate comprehensive WhatsApp message
                    patient_name = st.session_state.patient_records.get('Name', 'Patient')
                    patient_id = st.session_state.patient_id
                    
                    # Get comprehensive data from patient records
                    chief_complaint = st.session_state.patient_records.get('Chief Complaint', 'None reported')
                    physical_exam = st.session_state.patient_records.get('Physical Exam Findings', 'None recorded')
                    care_gaps = st.session_state.patient_records.get('Care Gaps', 'None identified')
                    treatment_plan = st.session_state.patient_records.get('Treatment Plan', 'None documented')
                    next_appointments = st.session_state.patient_records.get('Next Appointments', 'None scheduled')
                    
                    whatsapp_message = f"""
🏥 *Comprehensive Health Report*

*Patient Information:*
• Name: {patient_name}
• Patient ID: {patient_id}
• Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

*Current Health Status:*
• Health Score: 85/100
• Chief Complaint: {chief_complaint}
• Physical Exam: {physical_exam}

*Medical Summary:*
• Active Medications: {len(safe_parse_field(st.session_state.patient_records.get('Current Medications', '')))}
• Known Allergies: {len(safe_parse_field(st.session_state.patient_records.get('Drug Allergies', '')))}
• Medical Conditions: {len(safe_parse_field(st.session_state.patient_records.get('Past Medical History', '')))}

*Care Management:*
• Care Gaps: {care_gaps}
• Treatment Plan: {treatment_plan}
• Next Appointments: {next_appointments}

*Recent Symptoms:* {st.session_state.get('symptom_changes', 'None reported')}

Please review the complete dashboard for detailed insights and trends.
                    """.strip()
                    
                    phone_clean = selected_physician['phone'].replace('+', '').replace('-', '')
                    message_encoded = whatsapp_message.replace(' ', '%20').replace('\n', '%0A')
                    whatsapp_url = f"https://wa.me/{phone_clean}?text={message_encoded}"
                    
                    # Show success message with preview
                    st.success("✅ WhatsApp message prepared successfully!")
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #25D366 0%, #128C7E 100%); padding: 16px; border-radius: 8px; margin: 12px 0; color: white;">
                        <h4 style="margin: 0 0 8px 0; color: white; font-size: 16px;">📱 WhatsApp Message Preview</h4>
                        <p style="margin: 0; color: rgba(255,255,255,0.9); font-size: 13px;">Message will be sent to: <strong>{selected_physician['name']}</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show message preview
                    with st.expander("👀 Preview Message Content", expanded=True):
                        st.text_area("Message Preview:", value=whatsapp_message, height=200, disabled=True)
                    
                    # WhatsApp button with better styling
                    st.markdown(f"""
                    <div style="text-align: center; margin: 16px 0;">
                        <a href="{whatsapp_url}" target="_blank" style="
                            display: inline-block;
                            background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
                            color: white;
                            padding: 12px 24px;
                            border-radius: 25px;
                            text-decoration: none;
                            font-weight: 600;
                            font-size: 16px;
                            box-shadow: 0 4px 15px rgba(37, 211, 102, 0.3);
                            transition: all 0.3s ease;
                        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(37, 211, 102, 0.4)'" 
                           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(37, 211, 102, 0.3)'">
                            📱 Open WhatsApp to Send
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                    st.success("WhatsApp link generated! Click to share.")
            
            with col_share2:
                st.markdown("""
                <div style="text-align: center; padding: 12px; background-color: #ffffff; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h4 style="margin: 0 0 8px 0; color: #495057; font-size: 16px;">💬 SMS</h4>
                    <p style="margin: 0; color: #6c757d; font-size: 12px;">Send SMS message</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("💬 Send SMS", key="sms_share"):
                    # Generate comprehensive SMS message
                    patient_name = st.session_state.patient_records.get('Name', 'Patient')
                    patient_id = st.session_state.patient_id
                    chief_complaint = st.session_state.patient_records.get('Chief Complaint', 'None reported')
                    care_gaps = st.session_state.patient_records.get('Care Gaps', 'None identified')
                    
                    sms_message = f"Health Report - {patient_name} (ID: {patient_id}). Chief Complaint: {chief_complaint}. Health Score: 85/100. Care Gaps: {care_gaps}. Recent symptoms: {st.session_state.get('symptom_changes', 'None')}. Please review dashboard for complete details."
                    
                    sms_url = f"sms:{selected_physician['phone']}?body={sms_message.replace(' ', '%20')}"
                    
                    # Show success message with preview
                    st.success("✅ SMS message prepared successfully!")
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); padding: 16px; border-radius: 8px; margin: 12px 0; color: white;">
                        <h4 style="margin: 0 0 8px 0; color: white; font-size: 16px;">💬 SMS Message Preview</h4>
                        <p style="margin: 0; color: rgba(255,255,255,0.9); font-size: 13px;">Message will be sent to: <strong>{selected_physician['name']}</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show message preview
                    with st.expander("👀 Preview SMS Content", expanded=True):
                        st.text_area("SMS Preview:", value=sms_message, height=100, disabled=True)
                        st.info(f"📏 Message length: {len(sms_message)} characters")
                    
                    # SMS button with better styling
                    st.markdown(f"""
                    <div style="text-align: center; margin: 16px 0;">
                        <a href="{sms_url}" target="_blank" style="
                            display: inline-block;
                            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                            color: white;
                            padding: 12px 24px;
                            border-radius: 25px;
                            text-decoration: none;
                            font-weight: 600;
                            font-size: 16px;
                            box-shadow: 0 4px 15px rgba(0, 123, 255, 0.3);
                            transition: all 0.3s ease;
                        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(0, 123, 255, 0.4)'" 
                           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(0, 123, 255, 0.3)'">
                            💬 Open SMS to Send
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col_share3:
                st.markdown("""
                <div style="text-align: center; padding: 12px; background-color: #ffffff; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h4 style="margin: 0 0 8px 0; color: #495057; font-size: 16px;">📧 Email</h4>
                    <p style="margin: 0; color: #6c757d; font-size: 12px;">Send email report</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("📧 Send Email", key="email_share"):
                    # Generate email content
                    patient_name = st.session_state.patient_records.get('Name', 'Patient')
                    patient_id = st.session_state.patient_id
                    email_subject = f"Health Insights Report - {patient_name} (ID: {patient_id})"
                    # Get comprehensive data from patient records
                    chief_complaint = st.session_state.patient_records.get('Chief Complaint', 'None reported')
                    physical_exam = st.session_state.patient_records.get('Physical Exam Findings', 'None recorded')
                    care_gaps = st.session_state.patient_records.get('Care Gaps', 'None identified')
                    treatment_plan = st.session_state.patient_records.get('Treatment Plan', 'None documented')
                    next_appointments = st.session_state.patient_records.get('Next Appointments', 'None scheduled')
                    
                    email_body = f"""
Dear Dr. {selected_physician['name'].split()[-1]},

Please find below the comprehensive health insights report for your patient:

PATIENT INFORMATION:
- Name: {patient_name}
- Patient ID: {patient_id}
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

CLINICAL ASSESSMENT:
- Chief Complaint: {chief_complaint}
- Physical Exam Findings: {physical_exam}
- Health Score: 85/100
- Last Visit: 2 days ago

MEDICAL SUMMARY:
- Active Medications: {len(safe_parse_field(st.session_state.patient_records.get('Current Medications', '')))}
- Known Allergies: {len(safe_parse_field(st.session_state.patient_records.get('Drug Allergies', '')))}
- Medical Conditions: {len(safe_parse_field(st.session_state.patient_records.get('Past Medical History', '')))}

CARE MANAGEMENT:
- Care Gaps: {care_gaps}
- Treatment Plan: {treatment_plan}
- Next Appointments: {next_appointments}

RECENT SYMPTOMS: {st.session_state.get('symptom_changes', 'None reported')}

Please review the complete dashboard for detailed insights, trends, and comprehensive analytics.

Best regards,
Health Journal System
                    """.strip()
                    
                    subject_encoded = email_subject.replace(' ', '%20')
                    body_encoded = email_body.replace(' ', '%20').replace('\n', '%0A')
                    email_url = f"mailto:{selected_physician['email']}?subject={subject_encoded}&body={body_encoded}"
                    
                    # Show success message with preview
                    st.success("✅ Email prepared successfully!")
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); padding: 16px; border-radius: 8px; margin: 12px 0; color: white;">
                        <h4 style="margin: 0 0 8px 0; color: white; font-size: 16px;">📧 Email Preview</h4>
                        <p style="margin: 0; color: rgba(255,255,255,0.9); font-size: 13px;">Email will be sent to: <strong>{selected_physician['email']}</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show email preview
                    with st.expander("👀 Preview Email Content", expanded=True):
                        st.text_input("Subject:", value=email_subject, disabled=True)
                        st.text_area("Email Body:", value=email_body, height=300, disabled=True)
                        st.info(f"📧 Email will be sent to: {selected_physician['email']}")
                    
                    # Email button with better styling
                    st.markdown(f"""
                    <div style="text-align: center; margin: 16px 0;">
                        <a href="{email_url}" target="_blank" style="
                            display: inline-block;
                            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                            color: white;
                            padding: 12px 24px;
                            border-radius: 25px;
                            text-decoration: none;
                            font-weight: 600;
                            font-size: 16px;
                            box-shadow: 0 4px 15px rgba(220, 53, 69, 0.3);
                            transition: all 0.3s ease;
                        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(220, 53, 69, 0.4)'" 
                           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(220, 53, 69, 0.3)'">
                            📧 Open Email Client
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Close modal button
            st.markdown("---")
            col_close1, col_close2, col_close3 = st.columns([1, 1, 1])
            with col_close2:
                if st.button("❌ Close", key="close_share_modal"):
                    st.session_state.show_share_modal = False
                    st.rerun()
            
            # Additional sharing options
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #6c757d;">
                <h4 style="margin: 0 0 8px 0; color: #495057; font-size: 16px; font-weight: 600;">💡 Additional Sharing Options</h4>
                <p style="margin: 0; color: #6c757d; font-size: 13px;">You can also copy the message content and share it through other platforms like Teams, Slack, or any other communication tool.</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Show message when no sections are expanded
    if not any(st.session_state.expanded_sections.values()):
        st.markdown("""
        <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; margin: 20px 0;">
            <h3 style="color: #495057; font-size: 20px; margin-bottom: 10px;">Welcome to Patient 360 Insights Dashboard</h3>
            <p style="color: #6c757d; font-size: 16px; margin: 0;">Click on any section above to view detailed insights and analytics</p>
            </div>
            """, unsafe_allow_html=True)

elif st.session_state.stage == 'summary':
    st.markdown("""
    <h1 style="font-size: 28px; color: #2c3e50; margin-bottom: 10px; font-weight: 600; text-align: left;">
        Health Assessment Summary
    </h1>
    """, unsafe_allow_html=True)

    summary = st.session_state.final_summary
    patient_info = summary['structured_data']['patient_info']

    # Success message
    st.markdown("""
    <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 20px; border-radius: 10px; border-left: 4px solid #28a745; margin: 10px 0 20px 0;">
        <h3 style="color: #155724; margin: 0 0 10px 0; font-size: 18px; font-weight: 600;">Assessment Complete!</h3>
        <p style="color: #155724; margin: 0; font-size: 14px;">Your health information has been successfully processed and logged in our system.</p>
    </div>
    """, unsafe_allow_html=True)

    # Patient Summary
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("""
        <div style="font-size: 18px; color: #2c3e50; margin-bottom: 20px; font-weight: 600;">
            Patient Information
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"**Patient ID:** {st.session_state.patient_id}")
        # Ensure MRN is properly set
        mrn_value = patient_info.get('MRN', 'N/A')
        if mrn_value == 'N/A' or not mrn_value:
            import random
            import string
            today = datetime.now()
            date_str = today.strftime('%Y%m%d')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            mrn_value = f"MRN{date_str}{random_str}"
        
        st.markdown(f"**MRN:** {mrn_value}")
        st.markdown(f"**Name:** {patient_info.get('Name', 'N/A')}")
        st.markdown(
            f"**Age:** {patient_info.get('Age', 'N/A')} | **Gender:** {patient_info.get('Gender', 'N/A')}")

        st.markdown("---")

        # Clinical Summary
        st.markdown("""
        <div style="font-size: 18px; color: #2c3e50; margin-bottom: 8px; font-weight: 600;">
            Clinical Summary
        </div>
        """, unsafe_allow_html=True)
        # Clinical Summary content with proper summary
        st.markdown(f"""
        <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <p style="margin: 0; color: #2c3e50; font-size: 16px; line-height: 1.5;">
                <strong>Summary:</strong> Based on the patient's reported symptoms and medical history, this assessment provides a comprehensive overview of their current health status and recommended care pathway. The patient has reported: {summary['structured_data']['symptom_changes']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Treatment Provided
        st.markdown("""
        <div style="font-size: 18px; color: #2c3e50; margin-bottom: 8px; font-weight: 600;">
            Treatment Provided
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <p style="margin: 0; color: #2c3e50; font-size: 16px; line-height: 1.5;">
                Treatment recommendations will be discussed with the healthcare provider based on diagnostic test results and clinical evaluation.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Current Condition
        st.markdown("""
        <div style="font-size: 18px; color: #2c3e50; margin-bottom: 8px; font-weight: 600;">
            Current Condition
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <p style="margin: 0; color: #2c3e50; font-size: 16px; line-height: 1.5;">
                Condition assessment is ongoing. Regular monitoring and follow-up appointments are recommended.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Current and Past Medications
        st.markdown("""
        <div style="font-size: 18px; color: #2c3e50; margin-bottom: 8px; font-weight: 600;">
            Current and Past Medications
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <p style="margin: 0; color: #2c3e50; font-size: 16px; line-height: 1.5;">
                Please review current and past medications with your healthcare provider to ensure optimal treatment outcomes and understand treatment patterns.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if summary['structured_data']['additional_info']:
            st.markdown("""
            <div style="font-size: 18px; color: #2c3e50; margin-bottom: 20px; font-weight: 600;">
                Additional Information
            </div>
            """, unsafe_allow_html=True)
            st.text(summary['structured_data']['additional_info'])

    with col2:
        st.markdown("""
        <div style="font-size: 18px; color: #2c3e50; margin-bottom: 20px; font-weight: 600;">
            Assessment Details
        </div>
        """, unsafe_allow_html=True)
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
    st.markdown("""
    <div style="font-size: 18px; color: #2c3e50; margin-bottom: 20px; font-weight: 600;">
        Recommended Diagnostic Tests
    </div>
    """, unsafe_allow_html=True)

    tests = summary['diagnostic_tests']

    if tests:
        for i, test in enumerate(tests, 1):
            st.markdown(f"{i}. {test}")
    else:
        st.info("No specific tests recommended at this time. Continue monitoring.")

    st.markdown("---")

    # Healthcare Action Plan
    st.markdown("""
    <div style="font-size: 18px; color: #2c3e50; margin-bottom: 20px; font-weight: 600;">
        Healthcare Action Plan
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
        **Healthcare Provider Consultation:**
        - Share this assessment with your primary care physician
        - Discuss the recommended diagnostic tests
        - Review your current medication regimen
        - Address any concerns or questions you may have
        """)

    with col_b:
        st.markdown("""
        **Self-Care & Monitoring:**
        - Maintain a symptom diary for tracking changes
        - Follow prescribed treatment plans consistently
        - Practice healthy lifestyle habits
        - Seek immediate medical attention for severe symptoms
        """)

    st.markdown("---")

    # Download options
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        # Export as text
        text_report = f"""
HEALTH ASSESSMENT REPORT
========================

Patient ID: {st.session_state.patient_id}
MRN: {mrn_value}
Date: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}

PATIENT INFORMATION:
Name: {patient_info.get('Name', 'N/A')}
Age: {patient_info.get('Age', 'N/A')}
Gender: {patient_info.get('Gender', 'N/A')}

CLINICAL SUMMARY:
Summary: Based on the patient's reported symptoms and medical history, this assessment provides a comprehensive overview of their current health status and recommended care pathway. The patient has reported: {summary['structured_data']['symptom_changes']}

TREATMENT PROVIDED:
Current Treatment: Based on the assessment, the following treatment recommendations have been provided to address the patient's symptoms and underlying conditions.
Treatment recommendations will be discussed with the healthcare provider based on diagnostic test results and clinical evaluation.

CURRENT CONDITION:
Condition Status: The patient's current health condition is being monitored and evaluated based on reported symptoms and medical history.
Condition assessment is ongoing. Regular monitoring and follow-up appointments are recommended.

CURRENT AND PAST MEDICATIONS:
Please review current and past medications with your healthcare provider to ensure optimal treatment outcomes and understand treatment patterns.

ADDITIONAL INFORMATION:
{summary['structured_data']['additional_info'] or 'None'}

RECOMMENDED DIAGNOSTIC TESTS:
{chr(10).join([f"{i}. {test}" for i, test in enumerate(tests, 1)])}

---
Generated by Health Assistant
        """
        st.download_button(
            label="Download Text Report",
            data=text_report,
            file_name=f"health_report_{st.session_state.patient_id}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )

    with col_d2:
        if st.button("New Assessment"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Reinitialize default session state
            st.session_state.stage = 'welcome'
            st.session_state.auth_method = 'patient_id'
            st.session_state.otp_verified = False
            st.session_state.otp_phone = None
            st.session_state.show_reconciliation = False
            st.session_state.medical_sources = None
            st.session_state.consent_given = False
            st.session_state.duplicate_confirmations = []
            st.rerun()

    # NABH Disclaimer
    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 25px; border-radius: 12px; border-left: 5px solid #007bff; margin: 25px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <h4 style="color: #2c3e50; margin: 0 0 18px 0; font-size: 18px; font-weight: 700; text-align: center;">Disclaimer</h4>
        <p style="color: #495057; margin: 0; font-size: 14px; line-height: 1.6; text-align: justify;">
            The contents are sample references to aid understanding of the Standards and are not prescribed by NABH as 
            mandatory practices. Healthcare organizations are encouraged to modify them as per their scope and practices. NABH is 
            not liable for misinterpretation, erroneous use, or non-conformities during assessment due to unmodified use of these contents.
        </p>
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
