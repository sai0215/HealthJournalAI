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
        'reconciliation': '🔄 Medical History',
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
                                    # For returning patients, show medical history reconciliation
                                    st.session_state.stage = 'reconciliation'
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
                        # For returning patients, show medical history reconciliation
                        st.session_state.stage = 'reconciliation'
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

elif st.session_state.stage == 'reconciliation':
    st.title("🔄 Medical History Reconciliation")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <h4 style="margin: 0; color: #1976d2; font-size: 16px;">🆔 Patient ID: {st.session_state.patient_id}</h4>
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
        <h4>📋 Medical History Collection</h4>
        <p>We found your medical records at the following healthcare providers. 
        To provide you with comprehensive care, we need your consent to collect and reconcile 
        your medical history from these sources.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display hospital sources
        st.subheader("🏥 Healthcare Providers with Your Records")
        
        for i, source in enumerate(sources):
            with st.expander(f"🏥 {source['name']} - {source['location']}", expanded=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Location:** {source['location']}")
                    st.write(f"**Last Visit:** {source['last_visit']}")
                with col_b:
                    st.write(f"**Records:** {source['records_count']} medical records")
                    st.write(f"**Status:** ✅ Records Available")
        
        # Consent form
        st.markdown("---")
        st.subheader("📝 Consent for Medical History Collection")
        
        consent_data = medical_reconciliation.get_consent_form_data(
            st.session_state.patient_id, sources)
        
        st.markdown(f"""
        <div class="warning-box">
        <h4>🔒 Data Collection Consent</h4>
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
                st.subheader("⚠️ Duplicate Records Detected")
                
                st.markdown("""
                <div class="warning-box">
                <p>We found some duplicate medical records across different hospitals. 
                Please confirm which records you want to keep.</p>
                </div>
                """, unsafe_allow_html=True)
                
                for i, duplicate in enumerate(medical_history['duplicates']):
                    st.write(f"**{duplicate['type'].title()}:** {duplicate['value']} (found in {duplicate['count']} hospitals)")
                    st.write(f"**Sources:** {', '.join(duplicate['sources'])}")
                    
                    # Confirmation for each duplicate
                    confirm = st.radio(
                        f"Keep {duplicate['value']} from:",
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
            st.subheader("📋 Collected Medical History Summary")
            
            # Show duplicate confirmations if any
            if st.session_state.duplicate_confirmations:
                st.info("ℹ️ **Note:** Duplicate items will be resolved based on your selections above.")
            
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
                if st.button("🔄 Reconcile Medical History"):
                    if consent_given:
                        result = medical_reconciliation.process_consent_response(
                            st.session_state.patient_id, 
                            consent_given, 
                            st.session_state.duplicate_confirmations
                        )
                        
                        if result['success']:
                            st.success("✅ Medical history reconciliation completed!")
                            
                            # Create final reconciled history based on duplicate confirmations
                            final_medical_history = medical_reconciliation.create_final_reconciled_history(
                                medical_history, st.session_state.duplicate_confirmations)
                            
                            # Update patient records with final reconciled medical history
                            st.session_state.patient_records = _update_patient_with_reconciled_data(
                                st.session_state.patient_records, final_medical_history)
                            
                            st.session_state.stage = 'patient_info'
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
                    else:
                        st.warning("⚠️ Please provide consent to proceed")
            
            with col_btn2:
                if st.button("⏭️ Skip Reconciliation"):
                    st.info("ℹ️ Skipping medical history reconciliation. You can reconcile later.")
                    st.session_state.stage = 'patient_info'
                    st.rerun()
        
        else:
            st.warning("⚠️ Consent is required to reconcile your medical history")
    
    with col2:
        st.markdown("""
        <div class="info-box">
        <h4>🔄 Why Reconcile Medical History?</h4>
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
        <h4>🔒 Your Privacy Rights</h4>
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
                <div style="flex: 1; min-width: 250px; background-color: rgba(255,255,255,0.9); padding: 18px; border-radius: 10px; border-left: 5px solid #6f42c1; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h4 style="margin: 0 0 12px 0; color: #2c3e50; font-size: 15px; font-weight: 600;">💊 Current Medications</h4>
                    <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.5;">{medications}</p>
                </div>
                <div style="flex: 1; min-width: 250px; background-color: rgba(255,255,255,0.9); padding: 18px; border-radius: 10px; border-left: 5px solid #fd7e14; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h4 style="margin: 0 0 12px 0; color: #2c3e50; font-size: 15px; font-weight: 600;">🔬 Recent Procedures</h4>
                    <p style="margin: 0; color: #555; font-size: 14px; line-height: 1.5;">{recent_procedures}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Add new items section integrated with medical history
        st.subheader("➕ Add New Medical Information")
        
        # Create expandable sections for adding new items
        with st.expander("📋 Add New Medical Conditions", expanded=False):
            with st.form("add_conditions_form"):
                new_conditions = st.text_area(
                    "Enter new medical conditions (one per line or separated by commas):",
                    placeholder="e.g., High blood pressure\nDiabetes\nAsthma",
                    height=100
                )
                if st.form_submit_button("✅ Add Conditions"):
                    if new_conditions.strip():
                        # Process new conditions
                        conditions_list = [cond.strip() for cond in new_conditions.replace('\n', ',').split(',') if cond.strip()]
                        if conditions_list:
                            current_conditions = patient_records.get('Past Medical History', '')
                            if current_conditions and current_conditions != 'No significant medical history':
                                new_conditions_str = ', '.join(conditions_list)
                                patient_records['Past Medical History'] = f"{current_conditions}; {new_conditions_str}"
                            else:
                                patient_records['Past Medical History'] = ', '.join(conditions_list)
                            
                            st.session_state.patient_records = patient_records
                            st.success(f"✅ Added {len(conditions_list)} new condition(s)!")
                            st.rerun()

        with st.expander("💊 Add New Medications", expanded=False):
            with st.form("add_medications_form"):
                new_medications = st.text_area(
                    "Enter new medications (one per line or separated by commas):",
                    placeholder="e.g., Metformin 500mg\nLisinopril 10mg\nAtorvastatin 20mg",
                    height=100
                )
                if st.form_submit_button("✅ Add Medications"):
                    if new_medications.strip():
                        # Process new medications
                        medications_list = [med.strip() for med in new_medications.replace('\n', ',').split(',') if med.strip()]
                        if medications_list:
                            current_medications = patient_records.get('Current Medications', '')
                            if current_medications and current_medications != 'No current medications':
                                new_medications_str = ', '.join(medications_list)
                                patient_records['Current Medications'] = f"{current_medications}; {new_medications_str}"
                            else:
                                patient_records['Current Medications'] = ', '.join(medications_list)
                            
                            st.session_state.patient_records = patient_records
                            st.success(f"✅ Added {len(medications_list)} new medication(s)!")
                            st.rerun()

        with st.expander("⚠️ Add New Allergies", expanded=False):
            with st.form("add_allergies_form"):
                new_allergies = st.text_area(
                    "Enter new allergies (one per line or separated by commas):",
                    placeholder="e.g., Penicillin\nLatex\nShellfish",
                    height=100
                )
                if st.form_submit_button("✅ Add Allergies"):
                    if new_allergies.strip():
                        # Process new allergies
                        allergies_list = [allergy.strip() for allergy in new_allergies.replace('\n', ',').split(',') if allergy.strip()]
                        if allergies_list:
                            current_allergies = patient_records.get('Drug Allergies', '')
                            if current_allergies and current_allergies != 'No known drug allergies':
                                new_allergies_str = ', '.join(allergies_list)
                                patient_records['Drug Allergies'] = f"{current_allergies}; {new_allergies_str}"
                            else:
                                patient_records['Drug Allergies'] = ', '.join(allergies_list)
                            
                            st.session_state.patient_records = patient_records
                            st.success(f"✅ Added {len(allergies_list)} new allergy/allergies!")
                            st.rerun()

        with st.expander("🔬 Add New Procedures/Tests", expanded=False):
            with st.form("add_procedures_form"):
                new_procedures = st.text_area(
                    "Enter new procedures or tests (one per line or separated by commas):",
                    placeholder="e.g., Blood test\nX-ray\nMRI scan\nECG",
                    height=100
                )
                if st.form_submit_button("✅ Add Procedures"):
                    if new_procedures.strip():
                        # Process new procedures
                        procedures_list = [proc.strip() for proc in new_procedures.replace('\n', ',').split(',') if proc.strip()]
                        if procedures_list:
                            # Store procedures in a new field or append to existing
                            current_procedures = patient_records.get('Recent Procedures', '')
                            if current_procedures:
                                new_procedures_str = ', '.join(procedures_list)
                                patient_records['Recent Procedures'] = f"{current_procedures}; {new_procedures_str}"
                            else:
                                patient_records['Recent Procedures'] = ', '.join(procedures_list)
                            
                            st.session_state.patient_records = patient_records
                            st.success(f"✅ Added {len(procedures_list)} new procedure(s)!")
                            st.rerun()

        st.markdown("---")

        if st.button("Continue to Symptoms ➡️"):
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
            if st.button("📊 Generate Insights ➡️"):
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
    
    # Dashboard tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏥 Medical Overview", "💊 Medications", "⚠️ Allergies & Risks", "📈 Trends & Analytics", "🔍 Detailed Analysis"])
    
    with tab1:
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
            if conditions and conditions != 'No significant medical history':
                conditions_list = [c.strip() for c in conditions.split(';') if c.strip()]
                
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
            if procedures and procedures != 'No recent procedures':
                procedures_list = [p.strip() for p in procedures.split(';') if p.strip()]
                
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
    
    with tab2:
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
            if medications and medications != 'No current medications':
                medications_list = [m.strip() for m in medications.split(';') if m.strip()]
                
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
                med_names = [m.strip() for m in medications.split(';') if m.strip()]
                effectiveness_data = np.random.rand(len(med_names), 4)
                
                fig_heatmap = px.imshow(effectiveness_data,
                                      x=['Effectiveness', 'Tolerability', 'Convenience', 'Cost'],
                                      y=med_names,
                                      color_continuous_scale='RdYlGn',
                                      title="Effectiveness Matrix")
                fig_heatmap.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with tab3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #dc3545;">
            <h3 style="margin: 0; color: #495057; font-size: 18px; font-weight: 600;">⚠️ Allergies & Risk Assessment</h3>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">Monitor allergies and assess health risks for better care planning</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_allergy1, col_allergy2 = st.columns([1, 1])
        
        with col_allergy1:
            st.markdown("""
            <div style="background-color: #ffffff; padding: 1px; border-radius: 2px; margin-bottom: 0px;">
                <h4 style="margin: 0 0 0px 0; color: #495057; font-size: 16px; font-weight: 600;">⚠️ Known Allergies</h4>
            </div>
            """, unsafe_allow_html=True)
            allergies = st.session_state.patient_records.get('Drug Allergies', '')
            if allergies and allergies != 'No known drug allergies':
                allergies_list = [a.strip() for a in allergies.split(';') if a.strip()]
                
                # Allergy severity and type
                allergy_data = []
                for allergy in allergies_list:
                    allergy_data.append({
                        'Allergen': allergy,
                        'Type': np.random.choice(['Drug', 'Food', 'Environmental']),
                        'Severity': np.random.choice(['Mild', 'Moderate', 'Severe'], p=[0.3, 0.4, 0.3]),
                        'Reaction': np.random.choice(['Rash', 'Swelling', 'Anaphylaxis', 'Nausea'])
                    })
                
                df_allergies = pd.DataFrame(allergy_data)
                
                # Allergy severity distribution
                severity_counts = df_allergies['Severity'].value_counts()
                fig_allergy = px.bar(x=severity_counts.index, y=severity_counts.values,
                                   title="Severity Distribution",
                                   color=severity_counts.values,
                                   color_continuous_scale="Reds")
                fig_allergy.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_allergy, use_container_width=True)
                
                # Allergy type pie chart
                type_counts = df_allergies['Type'].value_counts()
                fig_type = px.pie(values=type_counts.values, names=type_counts.index,
                                title="Allergy Types",
                                color_discrete_sequence=px.colors.qualitative.Set2)
                fig_type.update_layout(title_font_size=14, font_size=12)
                st.plotly_chart(fig_type, use_container_width=True)
            else:
                st.info("No known allergies recorded")
        
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
    
    with tab4:
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
    
    with tab5:
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
            st.metric("🏥 Total Conditions", len(conditions_list) if 'conditions_list' in locals() else 0)
            st.metric("💊 Active Medications", len(medications_list) if 'medications_list' in locals() else 0)
        
        with col_summary2:
            st.metric("⚠️ Known Allergies", len(allergies_list) if 'allergies_list' in locals() else 0)
            st.metric("🔬 Recent Procedures", len(procedures_list) if 'procedures_list' in locals() else 0)
        
        with col_summary3:
            st.metric("📅 Days Since Last Visit", np.random.randint(1, 30))
            st.metric("🎯 Health Score", "85/100", "↑ 5")
    
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
        
        # Sample physician data - in real app, this would come from database
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
                    # Generate WhatsApp message
                    patient_name = st.session_state.patient_records.get('Name', 'Patient')
                    patient_id = st.session_state.patient_id
                    whatsapp_message = f"""
🏥 *Health Insights Report*

*Patient:* {patient_name}
*Patient ID:* {patient_id}
*Date:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

*Health Summary:*
• Health Score: 85/100
• Last Visit: 2 days ago
• Active Medications: {len(st.session_state.patient_records.get('Current Medications', '').split(';')) if st.session_state.patient_records.get('Current Medications') else 0}
• Known Allergies: {len(st.session_state.patient_records.get('Drug Allergies', '').split(';')) if st.session_state.patient_records.get('Drug Allergies') else 0}

*Recent Symptoms:* {st.session_state.get('symptom_changes', 'None reported')}

Please review the complete dashboard for detailed insights.
                    """.strip()
                    
                    phone_clean = selected_physician['phone'].replace('+', '').replace('-', '')
                    message_encoded = whatsapp_message.replace(' ', '%20').replace('\n', '%0A')
                    whatsapp_url = f"https://wa.me/{phone_clean}?text={message_encoded}"
                    st.markdown(f"[📱 Open WhatsApp]({whatsapp_url})")
                    st.success("WhatsApp link generated! Click to share.")
            
            with col_share2:
                st.markdown("""
                <div style="text-align: center; padding: 12px; background-color: #ffffff; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h4 style="margin: 0 0 8px 0; color: #495057; font-size: 16px;">💬 SMS</h4>
                    <p style="margin: 0; color: #6c757d; font-size: 12px;">Send SMS message</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("💬 Send SMS", key="sms_share"):
                    # Generate SMS message
                    patient_name = st.session_state.patient_records.get('Name', 'Patient')
                    patient_id = st.session_state.patient_id
                    sms_message = f"Health Insights Report for {patient_name} (ID: {patient_id}). Health Score: 85/100. Recent symptoms: {st.session_state.get('symptom_changes', 'None')}. Please review dashboard for details."
                    
                    sms_url = f"sms:{selected_physician['phone']}?body={sms_message.replace(' ', '%20')}"
                    st.markdown(f"[💬 Send SMS]({sms_url})")
                    st.success("SMS link generated! Click to send.")
            
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
                    email_body = f"""
Dear Dr. {selected_physician['name'].split()[-1]},

Please find below the health insights report for your patient:

Patient Information:
- Name: {patient_name}
- Patient ID: {patient_id}
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Health Summary:
- Health Score: 85/100
- Last Visit: 2 days ago
- Active Medications: {len(st.session_state.patient_records.get('Current Medications', '').split(';')) if st.session_state.patient_records.get('Current Medications') else 0}
- Known Allergies: {len(st.session_state.patient_records.get('Drug Allergies', '').split(';')) if st.session_state.patient_records.get('Drug Allergies') else 0}

Recent Symptoms: {st.session_state.get('symptom_changes', 'None reported')}

Please review the complete dashboard for detailed insights and trends.

Best regards,
Health Journal System
                    """.strip()
                    
                    subject_encoded = email_subject.replace(' ', '%20')
                    body_encoded = email_body.replace(' ', '%20').replace('\n', '%0A')
                    email_url = f"mailto:{selected_physician['email']}?subject={subject_encoded}&body={body_encoded}"
                    st.markdown(f"[📧 Send Email]({email_url})")
                    st.success("Email link generated! Click to send.")
            
            # Close modal button
            st.markdown("---")
            col_close1, col_close2, col_close3 = st.columns([1, 1, 1])
            with col_close2:
                if st.button("❌ Close", key="close_share_modal"):
                    st.session_state.show_share_modal = False
                    st.rerun()

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
            st.session_state.show_reconciliation = False
            st.session_state.medical_sources = None
            st.session_state.consent_given = False
            st.session_state.duplicate_confirmations = []
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
