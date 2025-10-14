#!/usr/bin/env python3
"""
Test script for patient registration system
"""

from patient_registration import PatientRegistration, ABHAValidator, validate_abha_id_format
import json


def test_abha_validation():
    """Test ABHA ID validation"""
    print("Testing ABHA ID validation...")

    validator = ABHAValidator()

    # Test valid ABHA ID
    valid_abha = "12345678901234"
    is_valid, data = validator.validate_abha_id(valid_abha)
    print(f"Valid ABHA ID '{valid_abha}': {is_valid}")

    # Test invalid ABHA ID
    invalid_abha = "1234567890123"  # 13 digits
    is_valid, data = validator.validate_abha_id(invalid_abha)
    print(f"Invalid ABHA ID '{invalid_abha}': {is_valid}")

    # Test format validation
    print(
        f"Format validation for '12345678901234': {validate_abha_id_format('12345678901234')}")
    print(
        f"Format validation for '1234567890123': {validate_abha_id_format('1234567890123')}")


def test_patient_registration():
    """Test patient registration"""
    print("\nTesting patient registration...")

    registration = PatientRegistration()

    # Test registration data
    test_data = {
        "name": "Test Patient",
        "dob": "1990-01-01",
        "gender": "Male",
        "phone": "9876543210",
        "email": "test@example.com",
        "address": "123 Test Street",
        "insurance": "Test Insurance",
        "emergency_contact": "Emergency Contact +1234567890",
        "family_history": "Father had diabetes",
        "past_medical_history": "Hypertension",
        "current_medications": "Metformin",
        "drug_allergies": "Penicillin",
        "abha_id": "12345678901234"
    }

    print("Test registration data:")
    print(json.dumps(test_data, indent=2))

    # Test registration
    success, patient_id, response = registration.register_new_patient(
        test_data)

    if success:
        print(f"Registration successful!")
        print(f"Patient ID: {patient_id}")
        print(f"Response: {json.dumps(response, indent=2)}")

        # Test patient lookup
        exists, patient_data = registration.check_patient_exists(patient_id)
        print(f"Patient lookup by ID: {exists}")

        exists, patient_data = registration.check_patient_exists(
            "test@example.com")
        print(f"Patient lookup by email: {exists}")

    else:
        print(f"Registration failed: {response}")


def test_validation():
    """Test data validation"""
    print("\nTesting data validation...")

    registration = PatientRegistration()

    # Test missing required fields
    incomplete_data = {
        "name": "Test Patient",
        "dob": "1990-01-01"
        # Missing gender, phone, email
    }

    validation_result = registration._validate_registration_data(
        incomplete_data)
    print(f"Incomplete data validation: {validation_result}")

    # Test invalid email
    invalid_email_data = {
        "name": "Test Patient",
        "dob": "1990-01-01",
        "gender": "Male",
        "phone": "9876543210",
        "email": "invalid-email"
    }

    validation_result = registration._validate_registration_data(
        invalid_email_data)
    print(f"Invalid email validation: {validation_result}")

    # Test invalid phone
    invalid_phone_data = {
        "name": "Test Patient",
        "dob": "1990-01-01",
        "gender": "Male",
        "phone": "123",  # Too short
        "email": "test@example.com"
    }

    validation_result = registration._validate_registration_data(
        invalid_phone_data)
    print(f"Invalid phone validation: {validation_result}")


if __name__ == "__main__":
    print("Patient Registration System Test Suite")
    print("=" * 50)

    try:
        test_abha_validation()
        test_validation()
        test_patient_registration()

        print("\nAll tests completed successfully!")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


