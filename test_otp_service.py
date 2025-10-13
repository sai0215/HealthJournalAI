"""
Test script for OTP Service
Tests the OTP generation and verification functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from otp_service import get_otp_service

def test_otp_service():
    """Test the OTP service functionality"""
    print("Testing OTP Service...")
    
    otp_service = get_otp_service()
    
    # Test phone number
    test_phone = "9876543210"
    
    print(f"\nTesting with phone number: {test_phone}")
    
    # Test OTP generation
    print("\n1. Testing OTP Generation...")
    success, otp_code, response = otp_service.generate_otp(test_phone)
    
    if success:
        print(f"SUCCESS: OTP generated successfully!")
        print(f"Response: {response}")
        print(f"OTP Code: {otp_code}")
        
        # Test OTP verification
        print("\n2. Testing OTP Verification...")
        verified, verify_response = otp_service.verify_otp(test_phone, otp_code)
        
        if verified:
            print(f"SUCCESS: OTP verified successfully!")
            print(f"Response: {verify_response}")
        else:
            print(f"FAILED: OTP verification failed!")
            print(f"Response: {verify_response}")
        
        # Test invalid OTP
        print("\n3. Testing Invalid OTP...")
        verified, verify_response = otp_service.verify_otp(test_phone, "123456")
        
        if not verified:
            print(f"SUCCESS: Invalid OTP correctly rejected!")
            print(f"Response: {verify_response}")
        else:
            print(f"FAILED: Invalid OTP was incorrectly accepted!")
    
    else:
        print(f"FAILED: OTP generation failed!")
        print(f"Response: {response}")
    
    # Test invalid phone number
    print("\n4. Testing Invalid Phone Number...")
    success, otp_code, response = otp_service.generate_otp("123")
    
    if not success:
        print(f"SUCCESS: Invalid phone number correctly rejected!")
        print(f"Response: {response}")
    else:
        print(f"FAILED: Invalid phone number was incorrectly accepted!")
    
    print("\nOTP Service testing completed!")

if __name__ == "__main__":
    test_otp_service()
