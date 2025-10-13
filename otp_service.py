"""
OTP Service for Phone Number Authentication
Handles OTP generation, sending, and verification for patient authentication
"""

import random
import string
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class OTPService:
    """Handles OTP generation, storage, and verification"""
    
    def __init__(self):
        # In-memory storage for OTPs (in production, use Redis or database)
        self.otp_storage = {}
        self.otp_expiry_minutes = 5  # OTP expires in 5 minutes
        self.max_attempts = 3  # Maximum verification attempts
        
    def generate_otp(self, phone_number: str) -> Tuple[bool, str, Dict]:
        """
        Generate and store OTP for phone number
        
        Args:
            phone_number: Phone number to send OTP to
            
        Returns:
            Tuple of (success, otp_code, response_data)
        """
        try:
            # Clean phone number
            clean_phone = self._clean_phone_number(phone_number)
            
            if not self._validate_phone_number(clean_phone):
                return False, "", {"error": "Invalid phone number format"}
            
            # Check if OTP was recently sent (rate limiting)
            if self._is_rate_limited(clean_phone):
                return False, "", {"error": "OTP already sent. Please wait before requesting another."}
            
            # Generate 6-digit OTP
            otp_code = self._generate_otp_code()
            
            # Store OTP with metadata
            otp_data = {
                "otp": otp_code,
                "phone": clean_phone,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(minutes=self.otp_expiry_minutes),
                "attempts": 0,
                "verified": False
            }
            
            self.otp_storage[clean_phone] = otp_data
            
            # In production, send OTP via SMS service
            sms_sent = self._send_sms_otp(clean_phone, otp_code)
            
            if sms_sent:
                logger.info(f"OTP sent successfully to {clean_phone}")
                return True, otp_code, {
                    "message": "OTP sent successfully",
                    "phone": clean_phone,
                    "expires_in_minutes": self.otp_expiry_minutes
                }
            else:
                # For demo purposes, return the OTP even if SMS fails
                logger.warning(f"SMS sending failed for {clean_phone}, but OTP generated")
                return True, otp_code, {
                    "message": "OTP generated (SMS service unavailable)",
                    "phone": clean_phone,
                    "otp": otp_code,  # Include OTP for demo purposes
                    "expires_in_minutes": self.otp_expiry_minutes
                }
                
        except Exception as e:
            logger.error(f"OTP generation failed: {e}")
            return False, "", {"error": "Failed to generate OTP"}
    
    def verify_otp(self, phone_number: str, otp_code: str) -> Tuple[bool, Dict]:
        """
        Verify OTP for phone number
        
        Args:
            phone_number: Phone number
            otp_code: OTP code to verify
            
        Returns:
            Tuple of (is_valid, response_data)
        """
        try:
            clean_phone = self._clean_phone_number(phone_number)
            
            if clean_phone not in self.otp_storage:
                return False, {"error": "No OTP found for this phone number"}
            
            otp_data = self.otp_storage[clean_phone]
            
            # Check if OTP is expired
            if datetime.now() > otp_data["expires_at"]:
                del self.otp_storage[clean_phone]
                return False, {"error": "OTP has expired. Please request a new one."}
            
            # Check if already verified
            if otp_data["verified"]:
                return False, {"error": "OTP has already been used"}
            
            # Check attempt limit
            if otp_data["attempts"] >= self.max_attempts:
                del self.otp_storage[clean_phone]
                return False, {"error": "Maximum verification attempts exceeded. Please request a new OTP."}
            
            # Increment attempts
            otp_data["attempts"] += 1
            
            # Verify OTP
            if otp_data["otp"] == otp_code:
                otp_data["verified"] = True
                otp_data["verified_at"] = datetime.now()
                
                logger.info(f"OTP verified successfully for {clean_phone}")
                return True, {
                    "message": "OTP verified successfully",
                    "phone": clean_phone,
                    "verified_at": otp_data["verified_at"].isoformat()
                }
            else:
                logger.warning(f"Invalid OTP attempt for {clean_phone}")
                return False, {
                    "error": f"Invalid OTP. {self.max_attempts - otp_data['attempts']} attempts remaining."
                }
                
        except Exception as e:
            logger.error(f"OTP verification failed: {e}")
            return False, {"error": "OTP verification failed"}
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean and normalize phone number"""
        # Remove all non-digit characters
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Remove country code if present (assuming Indian numbers)
        if clean_phone.startswith('91') and len(clean_phone) == 12:
            clean_phone = clean_phone[2:]
        
        return clean_phone
    
    def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        # Indian mobile numbers: 10 digits starting with 6, 7, 8, or 9
        pattern = r'^[6-9]\d{9}$'
        import re
        return bool(re.match(pattern, phone))
    
    def _generate_otp_code(self) -> str:
        """Generate 6-digit OTP code"""
        # For demo purposes, use a constant OTP
        return "123456"
    
    def _is_rate_limited(self, phone: str) -> bool:
        """Check if phone number is rate limited"""
        if phone not in self.otp_storage:
            return False
        
        otp_data = self.otp_storage[phone]
        # Rate limit: 1 OTP per minute
        time_since_last = datetime.now() - otp_data["created_at"]
        return time_since_last.total_seconds() < 60
    
    def _send_sms_otp(self, phone: str, otp: str) -> bool:
        """
        Send OTP via SMS service
        In production, integrate with SMS providers like Twilio, AWS SNS, etc.
        """
        try:
            # For demo purposes, simulate SMS sending
            # In production, replace with actual SMS service integration
            
            # Example with Twilio (commented out):
            # from twilio.rest import Client
            # account_sid = "your_account_sid"
            # auth_token = "your_auth_token"
            # client = Client(account_sid, auth_token)
            # 
            # message = client.messages.create(
            #     body=f"Your Health Journal OTP is: {otp}. Valid for 5 minutes.",
            #     from_="+1234567890",  # Your Twilio number
            #     to=f"+91{phone}"
            # )
            # return True
            
            # For demo, just log the OTP
            logger.info(f"DEMO: SMS would be sent to +91{phone} with OTP: {otp}")
            return False  # Return False to indicate SMS service is not available
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False
    
    def cleanup_expired_otps(self):
        """Clean up expired OTPs from storage"""
        current_time = datetime.now()
        expired_phones = [
            phone for phone, data in self.otp_storage.items()
            if current_time > data["expires_at"]
        ]
        
        for phone in expired_phones:
            del self.otp_storage[phone]
        
        if expired_phones:
            logger.info(f"Cleaned up {len(expired_phones)} expired OTPs")


# Global OTP service instance
otp_service = OTPService()


def get_otp_service() -> OTPService:
    """Get the global OTP service instance"""
    return otp_service
