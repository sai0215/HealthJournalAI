# Patient Authentication Features

This document describes the enhanced patient authentication system implemented in the Health Journal application.

## Overview

The application now supports multiple authentication methods for patient record access:

1. **Patient ID / UHID / MRN** - Combined patient identification (supports all three)
2. **ABHA ID** - Ayushman Bharat Health Account authentication
3. **Phone Number with OTP** - Secure phone-based authentication

## Features Implemented

### 1. MRN (Medical Record Number) Support

- **Auto-generation**: New patients automatically receive a unique MRN upon registration
- **Format**: `MRN{YYYYMMDD}{6-char-random}` (e.g., `MRN20250101ABC123`)
- **Display**: MRN is shown alongside Patient ID in all patient information displays
- **Lookup**: Patients can authenticate using their MRN

### 2. Enhanced ABHA Integration

- **Validation**: ABHA ID format validation (14 digits)
- **Verification**: Simulated ABHA verification process
- **Lookup**: Patients can authenticate using their ABHA ID
- **KYC Status**: ABHA verification status is tracked in patient records

### 3. Phone Number OTP Authentication

- **OTP Generation**: 6-digit OTP codes with 5-minute expiry
- **Rate Limiting**: 1 OTP per minute per phone number
- **Verification**: 3 attempts maximum before requiring new OTP
- **Security**: OTPs are stored securely with expiration tracking
- **Demo Mode**: For testing, uses constant OTP "123456"

### 4. Enhanced Patient Lookup

The system now supports lookup by multiple identifier types:
- Patient ID / UHID
- MRN
- ABHA ID
- Email address
- Phone number

## Technical Implementation

### OTP Service (`otp_service.py`)

```python
class OTPService:
    - generate_otp(phone_number) -> (success, otp_code, response)
    - verify_otp(phone_number, otp_code) -> (is_valid, response)
    - Rate limiting and security features
    - Cleanup of expired OTPs
```

### Enhanced Patient Registration (`patient_registration.py`)

```python
class PatientRegistration:
    - check_patient_exists(identifier, identifier_type) -> (exists, patient_data)
    - _generate_mrn() -> unique_mrn
    - Enhanced patient record creation with MRN
    - Support for multiple identifier types
```

### Updated UI (`streamlit_app.py`)

- **Authentication Method Selector**: Radio buttons for choosing authentication method
- **Dynamic Forms**: Different input fields based on selected method
- **OTP Flow**: Complete OTP generation and verification workflow
- **Enhanced Display**: MRN shown alongside Patient ID
- **Session Management**: Proper state management for OTP verification

## Usage Guide

### For Patients

1. **Select Authentication Method**: Choose from Patient ID/UHID/MRN, ABHA ID, or Phone Number
2. **Enter Identifier**: Provide the appropriate identifier
3. **Demo Identifiers** (for testing):
   - **Patient ID/UHID/MRN**: `GEN10001`, `GEN10002`, `GEN10003`, `GEN10004`, `GEN10005`
   - **ABHA ID**: `12345678901234`, `23456789012345`, `34567890123456`, `45678901234567`, `56789012345678`
   - **MRN**: `MRN20250101ABC123`, `MRN20250101DEF456`, `MRN20250101GHI789`, `MRN20250101JKL012`, `MRN20250101MNO345`
4. **OTP Process** (for phone authentication):
   - Enter phone number
   - Click "Send OTP"
   - Enter the constant OTP: **123456**
   - Click "Verify OTP"
5. **Access Records**: Once authenticated, access patient records and health assessment

### For Administrators

1. **Patient Registration**: New patients automatically receive both Patient ID and MRN
2. **ABHA Integration**: ABHA verification is performed during registration
3. **OTP Management**: OTP service handles secure authentication
4. **Record Management**: All patient records include MRN for better organization

## Security Features

### OTP Security
- **Expiration**: OTPs expire after 5 minutes
- **Rate Limiting**: Maximum 1 OTP per minute per phone number
- **Attempt Limiting**: Maximum 3 verification attempts per OTP
- **Cleanup**: Expired OTPs are automatically removed

### Data Protection
- **Phone Number Validation**: Indian mobile number format validation
- **ABHA Validation**: 14-digit format validation
- **Secure Storage**: OTPs stored with metadata and expiration
- **Session Management**: Proper cleanup of authentication state

## Configuration

### Environment Variables
- `MONGODB_URI`: MongoDB connection string (optional)
- `PERPLEXITY_API_KEY`: API key for AI features
- `PERPLEXITY_BASE_URL`: API base URL
- `PERPLEXITY_MODEL`: AI model to use

### SMS Integration (Production)
To enable real SMS sending, integrate with SMS providers:
- **Twilio**: Uncomment and configure Twilio settings in `otp_service.py`
- **AWS SNS**: Add AWS SNS integration
- **Other Providers**: Add support for other SMS services

## Testing

Run the test script to verify OTP functionality:
```bash
python test_otp_service.py
```

## Future Enhancements

1. **Real SMS Integration**: Connect to actual SMS service providers
2. **Email OTP**: Add email-based OTP authentication
3. **Biometric Authentication**: Add fingerprint/face recognition
4. **Multi-Factor Authentication**: Combine multiple authentication methods
5. **Audit Logging**: Track authentication attempts and security events

## Troubleshooting

### Common Issues

1. **OTP Not Received**: Check phone number format and SMS service configuration
2. **Invalid ABHA ID**: Ensure 14-digit format is used
3. **Patient Not Found**: Verify identifier type and format
4. **Session Issues**: Use "Reset Session" button to clear state

### Support

For technical support or feature requests, please refer to the main project documentation or contact the development team.
