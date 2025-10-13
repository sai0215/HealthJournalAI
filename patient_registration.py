"""
Patient Registration System with ABHA Integration
Handles new patient registration, KYC verification, and data persistence
"""

import uuid
import hashlib
import re
from datetime import datetime, date
from typing import Dict, Optional, List, Tuple
import pandas as pd
from pymongo import MongoClient
import logging
import requests
import json

logger = logging.getLogger(__name__)


class ABHAValidator:
    """ABHA (Ayushman Bharat Health Account) validation and integration"""

    def __init__(self):
        # ABHA API endpoints (these would be real endpoints in production)
        self.abha_verify_url = "https://api.abha.gov.in/verify"  # Placeholder
        self.abha_create_url = "https://api.abha.gov.in/create"  # Placeholder

    def validate_abha_id(self, abha_id: str) -> Tuple[bool, Dict]:
        """
        Validate ABHA ID format and verify with ABHA system

        Args:
            abha_id: ABHA ID to validate

        Returns:
            Tuple of (is_valid, patient_data)
        """
        # Basic format validation for ABHA ID
        if not self._is_valid_abha_format(abha_id):
            return False, {"error": "Invalid ABHA ID format"}

        # In a real implementation, this would call the ABHA API
        # For now, we'll simulate the response
        try:
            # Simulate API call
            patient_data = self._simulate_abha_verification(abha_id)
            return True, patient_data
        except Exception as e:
            logger.error(f"ABHA verification failed: {e}")
            return False, {"error": "ABHA verification failed"}

    def _is_valid_abha_format(self, abha_id: str) -> bool:
        """Validate ABHA ID format (14 digits)"""
        # ABHA ID should be 14 digits
        pattern = r'^\d{14}$'
        return bool(re.match(pattern, abha_id))

    def _simulate_abha_verification(self, abha_id: str) -> Dict:
        """Simulate ABHA verification response"""
        # This is a mock response - in production, this would be real ABHA data
        return {
            "abha_id": abha_id,
            "name": "Verified Patient",
            "dob": "1990-01-01",
            "gender": "Male",
            "mobile": "9876543210",
            "email": "patient@example.com",
            "address": "Verified Address",
            "kyc_status": "verified",
            "verification_date": datetime.now().isoformat()
        }


class PatientRegistration:
    """Handles patient registration and data management"""

    def __init__(self, mongodb_client=None):
        self.mongodb_client = mongodb_client
        self.abha_validator = ABHAValidator()

    def register_new_patient(self, registration_data: Dict) -> Tuple[bool, str, Dict]:
        """
        Register a new patient with ABHA verification

        Args:
            registration_data: Patient registration information

        Returns:
            Tuple of (success, patient_id, response_data)
        """
        try:
            # Validate required fields
            validation_result = self._validate_registration_data(
                registration_data)
            if not validation_result["valid"]:
                return False, "", validation_result

            # Verify ABHA ID if provided
            abha_id = registration_data.get("abha_id")
            if abha_id:
                abha_valid, abha_data = self.abha_validator.validate_abha_id(
                    abha_id)
                if not abha_valid:
                    return False, "", {"error": "ABHA verification failed", "details": abha_data}

                # Merge ABHA data with registration data
                registration_data.update(abha_data)

            # Generate unique patient ID and MRN
            patient_id = self._generate_patient_id()
            mrn = self._generate_mrn()

            # Create patient record
            patient_record = self._create_patient_record(
                patient_id, registration_data, mrn)

            # Save to database
            if self.mongodb_client:
                self._save_to_database(patient_record)

            # Save to Excel file (for backward compatibility)
            self._save_to_excel(patient_record)

            logger.info(f"Successfully registered patient: {patient_id}")
            return True, patient_id, {
                "patient_id": patient_id,
                "message": "Registration successful",
                "abha_verified": bool(abha_id)
            }

        except Exception as e:
            logger.error(f"Patient registration failed: {e}")
            return False, "", {"error": "Registration failed", "details": str(e)}

    def _validate_registration_data(self, data: Dict) -> Dict:
        """Validate registration data"""
        required_fields = ["name", "dob", "gender", "phone", "email"]
        missing_fields = [
            field for field in required_fields if not data.get(field)]

        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data.get("email", "")):
            return {
                "valid": False,
                "error": "Invalid email format"
            }

        # Validate phone number
        phone = str(data.get("phone", ""))
        if not re.match(r'^\d{10}$', phone):
            return {
                "valid": False,
                "error": "Phone number must be 10 digits"
            }

        # Validate date of birth
        try:
            dob = data.get("dob")
            if isinstance(dob, str):
                dob = datetime.strptime(dob, "%Y-%m-%d").date()
            elif isinstance(dob, datetime):
                dob = dob.date()

            if dob > date.today():
                return {
                    "valid": False,
                    "error": "Date of birth cannot be in the future"
                }
        except ValueError:
            return {
                "valid": False,
                "error": "Invalid date format. Use YYYY-MM-DD"
            }

        return {"valid": True}

    def _generate_patient_id(self) -> str:
        """Generate unique patient ID"""
        # Generate a unique ID with timestamp and random component
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = str(uuid.uuid4())[:8].upper()
        return f"REG{timestamp}{random_part}"
    
    def _generate_mrn(self) -> str:
        """Generate unique Medical Record Number (MRN)"""
        # Generate a unique MRN with timestamp and random component
        timestamp = datetime.now().strftime("%Y%m%d")
        random_part = str(uuid.uuid4())[:6].upper()
        return f"MRN{timestamp}{random_part}"

    def _create_patient_record(self, patient_id: str, data: Dict, mrn: str) -> Dict:
        """Create standardized patient record"""
        # Calculate age from DOB
        dob = data.get("dob")
        if isinstance(dob, str):
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        elif isinstance(dob, datetime):
            dob = dob.date()

        age = (date.today() - dob).days // 365 if dob else None

        # Create patient record matching the Excel structure
        patient_record = {
            "Patient ID": patient_id,
            "MRN": mrn,  # Add MRN field
            "Name": data.get("name", ""),
            "DOB": dob.isoformat() if dob else None,
            "Gender": data.get("gender", ""),
            "Address": data.get("address", ""),
            "Phone": data.get("phone", ""),
            "Email": data.get("email", ""),
            "Insurance": data.get("insurance", ""),
            "Emergency Contact": data.get("emergency_contact", ""),
            "Primary Diagnosis": "",
            "Date of Diagnosis": None,
            "Secondary Diagnoses": "",
            "Family History": data.get("family_history", ""),
            "Past Medical History": data.get("past_medical_history", ""),
            "Current Medications": data.get("current_medications", ""),
            "Drug Allergies": data.get("drug_allergies", ""),
            "Blood Pressure": "",
            "Heart Rate": None,
            "Weight": None,
            "BMI": None,
            "Recent HbA1c": None,
            "Recent Creatinine": None,
            "Key Lab Values": "",
            "Primary Care Provider": "",
            "Specialists": "",
            "Chief Complaint": "",
            "Physical Exam Findings": "",
            "Care Gaps": "",
            "Treatment Plan": "",
            "Next Appointments": None,
            "Patient Goals": "",
            "Social Determinants": "",
            "Quality of Life Score": None,
            # Additional fields for registration
            "Registration Date": datetime.now().isoformat(),
            "ABHA ID": data.get("abha_id", ""),
            "KYC Status": "verified" if data.get("abha_id") else "pending",
            "Registration Source": "web_app"
        }

        return patient_record

    def _save_to_database(self, patient_record: Dict):
        """Save patient record to MongoDB"""
        try:
            if self.mongodb_client:
                db = self.mongodb_client.health_journal
                patients_collection = db.patients
                patients_collection.insert_one(patient_record)
                logger.info(
                    f"Patient {patient_record['Patient ID']} saved to MongoDB")
        except Exception as e:
            logger.error(f"Failed to save to MongoDB: {e}")

    def _save_to_excel(self, patient_record: Dict):
        """Save patient record to Excel file for backward compatibility"""
        try:
            # Load existing data
            try:
                df = pd.read_excel("Dummy Patient Data for OCR Use Case.xlsx")
            except FileNotFoundError:
                # Create new DataFrame if file doesn't exist
                df = pd.DataFrame()

            # Convert patient record to DataFrame row
            new_row = pd.DataFrame([patient_record])

            # Append to existing data
            df = pd.concat([df, new_row], ignore_index=True)

            # Save back to Excel
            df.to_excel(
                "Dummy Patient Data for OCR Use Case.xlsx", index=False)
            logger.info(
                f"Patient {patient_record['Patient ID']} saved to Excel")

        except Exception as e:
            logger.error(f"Failed to save to Excel: {e}")

    def check_patient_exists(self, identifier: str, identifier_type: str = "auto") -> Tuple[bool, Optional[Dict]]:
        """
        Check if patient exists by various identifiers

        Args:
            identifier: Patient ID, MRN, ABHA ID, email, or phone
            identifier_type: Type of identifier ("auto", "patient_id", "mrn", "abha", "email", "phone")

        Returns:
            Tuple of (exists, patient_data)
        """
        try:
            # Check in Excel file first
            df = pd.read_excel("Dummy Patient Data for OCR Use Case.xlsx")

            # If identifier_type is specified, check only that type
            if identifier_type != "auto":
                return self._check_by_type(df, identifier, identifier_type)

            # Auto-detect identifier type and check accordingly
            # Check by Patient ID (UHID)
            patient_row = df[df['Patient ID'].astype(str) == str(identifier)]
            if not patient_row.empty:
                return True, patient_row.iloc[0].to_dict()

            # Check by MRN (Medical Record Number) - if column exists
            if 'MRN' in df.columns:
                mrn_row = df[df['MRN'].astype(str) == str(identifier)]
                if not mrn_row.empty:
                    return True, mrn_row.iloc[0].to_dict()

            # Check by ABHA ID
            if 'ABHA ID' in df.columns:
                abha_row = df[df['ABHA ID'].astype(str) == str(identifier)]
                if not abha_row.empty:
                    return True, abha_row.iloc[0].to_dict()

            # Check by email
            email_row = df[df['Email'].astype(str) == str(identifier)]
            if not email_row.empty:
                return True, email_row.iloc[0].to_dict()

            # Check by phone
            phone_row = df[df['Phone'].astype(str) == str(identifier)]
            if not phone_row.empty:
                return True, phone_row.iloc[0].to_dict()

            # For demo purposes, check if it's a sample ABHA ID
            if self._is_sample_abha_id(identifier):
                return self._get_sample_patient_for_abha(identifier)

            return False, None

        except Exception as e:
            logger.error(f"Error checking patient existence: {e}")
            return False, None

    def _is_sample_abha_id(self, abha_id: str) -> bool:
        """Check if the ABHA ID is one of our sample IDs for testing"""
        sample_abha_ids = [
            "12345678901234",
            "23456789012345", 
            "34567890123456",
            "45678901234567",
            "56789012345678"
        ]
        return abha_id in sample_abha_ids

    def _get_sample_patient_for_abha(self, abha_id: str) -> Tuple[bool, Optional[Dict]]:
        """Get sample patient data for demo ABHA IDs"""
        try:
            df = pd.read_excel("Dummy Patient Data for OCR Use Case.xlsx")
            
            # Map ABHA IDs to patient indices
            abha_to_index = {
                "12345678901234": 0,  # GEN10001
                "23456789012345": 1,  # GEN10002
                "34567890123456": 2,  # GEN10003
                "45678901234567": 3,  # GEN10004
                "56789012345678": 4,  # GEN10005
            }
            
            if abha_id in abha_to_index and abha_to_index[abha_id] < len(df):
                patient_data = df.iloc[abha_to_index[abha_id]].to_dict()
                # Add the ABHA ID to the patient data
                patient_data['ABHA ID'] = abha_id
                return True, patient_data
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error getting sample patient for ABHA: {e}")
            return False, None

    def _check_by_type(self, df: pd.DataFrame, identifier: str, identifier_type: str) -> Tuple[bool, Optional[Dict]]:
        """Check patient by specific identifier type"""
        try:
            if identifier_type == "patient_id":
                patient_row = df[df['Patient ID'].astype(str) == str(identifier)]
                if not patient_row.empty:
                    return True, patient_row.iloc[0].to_dict()
            
            elif identifier_type == "mrn":
                if 'MRN' in df.columns:
                    mrn_row = df[df['MRN'].astype(str) == str(identifier)]
                    if not mrn_row.empty:
                        return True, mrn_row.iloc[0].to_dict()
            
            elif identifier_type == "abha":
                if 'ABHA ID' in df.columns:
                    abha_row = df[df['ABHA ID'].astype(str) == str(identifier)]
                    if not abha_row.empty:
                        return True, abha_row.iloc[0].to_dict()
                
                # For demo purposes, check if it's a sample ABHA ID
                if self._is_sample_abha_id(identifier):
                    return self._get_sample_patient_for_abha(identifier)
            
            elif identifier_type == "email":
                email_row = df[df['Email'].astype(str) == str(identifier)]
                if not email_row.empty:
                    return True, email_row.iloc[0].to_dict()
            
            elif identifier_type == "phone":
                phone_row = df[df['Phone'].astype(str) == str(identifier)]
                if not phone_row.empty:
                    return True, phone_row.iloc[0].to_dict()
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking patient by type {identifier_type}: {e}")
            return False, None

# Utility functions for the Streamlit app


def get_registration_form_data() -> Dict:
    """Get registration form data structure"""
    return {
        "name": "",
        "dob": "",
        "gender": "",
        "phone": "",
        "email": "",
        "address": "",
        "insurance": "",
        "emergency_contact": "",
        "family_history": "",
        "past_medical_history": "",
        "current_medications": "",
        "drug_allergies": "",
        "abha_id": ""
    }


def validate_abha_id_format(abha_id: str) -> bool:
    """Quick ABHA ID format validation"""
    if not abha_id:
        return True  # ABHA ID is optional
    pattern = r'^\d{14}$'
    return bool(re.match(pattern, abha_id))
