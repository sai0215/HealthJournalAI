"""
Medical History Reconciliation Service
Handles collection and reconciliation of medical history from multiple hospital sources
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MedicalHistoryReconciliation:
    """Handles medical history reconciliation from multiple sources"""
    
    def __init__(self):
        # Mock hospital data sources
        self.hospital_sources = {
            "hospital_a": {
                "name": "City General Hospital",
                "location": "Mumbai",
                "last_visit": "2024-10-15",
                "records_count": 3
            },
            "hospital_b": {
                "name": "Metro Medical Center", 
                "location": "Delhi",
                "last_visit": "2024-09-22",
                "records_count": 2
            },
            "hospital_c": {
                "name": "Regional Health Institute",
                "location": "Bangalore", 
                "last_visit": "2024-08-10",
                "records_count": 1
            }
        }
        
        # Sample medical conditions and treatments
        self.medical_conditions = [
            "Hypertension", "Diabetes Type 2", "Asthma", "Migraine", "Arthritis",
            "High Cholesterol", "Anxiety", "Depression", "Sleep Apnea", "GERD",
            "Allergic Rhinitis", "Back Pain", "Knee Pain", "Headaches", "Fatigue"
        ]
        
        self.medications = [
            "Metformin", "Lisinopril", "Atorvastatin", "Albuterol", "Ibuprofen",
            "Omeprazole", "Loratadine", "Sertraline", "Amlodipine", "Glipizide"
        ]
        
        self.procedures = [
            "Blood Test", "X-Ray", "MRI Scan", "ECG", "Echocardiogram",
            "Colonoscopy", "Endoscopy", "Physical Therapy", "Vaccination", "Biopsy"
        ]

    def get_patient_medical_sources(self, patient_id: str) -> List[Dict]:
        """
        Get list of hospitals/sources where patient has medical records
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            List of hospital sources with patient records
        """
        # For demo purposes, randomly select 2-3 hospitals
        available_sources = list(self.hospital_sources.keys())
        selected_sources = random.sample(available_sources, random.randint(2, 3))
        
        sources_with_records = []
        for source_id in selected_sources:
            source_data = self.hospital_sources[source_id].copy()
            source_data["source_id"] = source_id
            sources_with_records.append(source_data)
        
        return sources_with_records

    def collect_medical_history(self, patient_id: str, source_ids: List[str]) -> Dict:
        """
        Collect medical history from specified sources
        
        Args:
            patient_id: Patient identifier
            source_ids: List of source IDs to collect from
            
        Returns:
            Consolidated medical history data
        """
        consolidated_history = {
            "patient_id": patient_id,
            "collection_date": datetime.now().isoformat(),
            "sources": [],
            "conditions": [],
            "medications": [],
            "procedures": [],
            "allergies": [],
            "duplicates": []
        }
        
        for source_id in source_ids:
            if source_id in self.hospital_sources:
                source_data = self._get_source_medical_data(patient_id, source_id)
                consolidated_history["sources"].append(source_data)
                
                # Merge data
                consolidated_history["conditions"].extend(source_data.get("conditions", []))
                consolidated_history["medications"].extend(source_data.get("medications", []))
                consolidated_history["procedures"].extend(source_data.get("procedures", []))
                consolidated_history["allergies"].extend(source_data.get("allergies", []))
        
        # Detect and handle duplicates
        consolidated_history = self._detect_duplicates(consolidated_history)
        
        return consolidated_history

    def _get_source_medical_data(self, patient_id: str, source_id: str) -> Dict:
        """Get medical data from a specific source"""
        source_info = self.hospital_sources[source_id]
        
        # Generate random medical data for demo
        num_conditions = random.randint(1, 4)
        num_medications = random.randint(1, 3)
        num_procedures = random.randint(2, 5)
        num_allergies = random.randint(0, 2)
        
        # Ensure we don't get empty lists or None values
        conditions = random.sample(self.medical_conditions, num_conditions) if num_conditions > 0 else []
        medications = random.sample(self.medications, num_medications) if num_medications > 0 else []
        procedures = random.sample(self.procedures, num_procedures) if num_procedures > 0 else []
        allergies = random.sample(["Penicillin", "Sulfa", "Latex", "Shellfish"], num_allergies) if num_allergies > 0 else []
        
        source_data = {
            "source_id": source_id,
            "hospital_name": source_info["name"],
            "location": source_info["location"],
            "last_visit": source_info["last_visit"],
            "patient_id": patient_id,  # Add patient ID for duplicate detection
            "patient_name": f"Patient {patient_id}",  # Add patient name for duplicate detection
            "conditions": conditions,
            "medications": medications,
            "procedures": procedures,
            "allergies": allergies
        }
        
        return source_data

    def _detect_duplicates(self, consolidated_history: Dict) -> Dict:
        """Detect duplicate patient records across sources"""
        duplicates = []
        
        # Check for duplicate patient records (same patient ID across multiple hospitals)
        sources = consolidated_history["sources"]
        patient_id_counts = {}
        
        # Count how many hospitals have records for the same patient
        for source in sources:
            patient_id = source.get("patient_id", "Unknown")
            if patient_id not in patient_id_counts:
                patient_id_counts[patient_id] = []
            patient_id_counts[patient_id].append(source["hospital_name"])
        
        # Identify duplicate patient records
        for patient_id, hospitals in patient_id_counts.items():
            if len(hospitals) > 1:
                duplicates.append({
                    "type": "patient_record",
                    "value": f"Patient ID: {patient_id}",
                    "count": len(hospitals),
                    "sources": hospitals
                })
        
        # If no duplicate patient records found, check for potential duplicates based on name/DOB
        if not duplicates:
            # Check for potential duplicate patients with same name and similar details
            patient_names = {}
            for source in sources:
                patient_name = source.get("patient_name", "Unknown")
                if patient_name not in patient_names:
                    patient_names[patient_name] = []
                patient_names[patient_name].append(source["hospital_name"])
            
            for patient_name, hospitals in patient_names.items():
                if len(hospitals) > 1:
                    duplicates.append({
                        "type": "patient_record",
                        "value": f"Patient: {patient_name}",
                        "count": len(hospitals),
                        "sources": hospitals
                    })
        
        # Remove duplicates from main lists (keep unique conditions and medications)
        consolidated_history["conditions"] = list(set(consolidated_history["conditions"]))
        consolidated_history["medications"] = list(set(consolidated_history["medications"]))
        consolidated_history["duplicates"] = duplicates
        
        return consolidated_history

    def get_consent_form_data(self, patient_id: str, sources: List[Dict]) -> Dict:
        """
        Generate consent form data for medical history collection
        
        Args:
            patient_id: Patient identifier
            sources: List of hospital sources
            
        Returns:
            Consent form data
        """
        hospital_names = [source["name"] for source in sources]
        
        consent_data = {
            "patient_id": patient_id,
            "consent_date": datetime.now().isoformat(),
            "purpose": "Medical History Reconciliation",
            "data_sources": hospital_names,
            "data_types": [
                "Medical Conditions and Diagnoses",
                "Current and Past Medications", 
                "Medical Procedures and Tests",
                "Allergies and Adverse Reactions",
                "Visit History and Dates"
            ],
            "consent_period": "12 months",
            "data_retention": "As per medical record retention policies",
            "patient_rights": [
                "Right to access your medical records",
                "Right to request corrections",
                "Right to withdraw consent",
                "Right to data portability"
            ],
            "contact_info": {
                "privacy_officer": "privacy@healthjournal.com",
                "phone": "+91-9876543210"
            }
        }
        
        return consent_data

    def process_consent_response(self, patient_id: str, consent_given: bool, 
                                duplicate_confirmations: List[Dict] = None) -> Dict:
        """
        Process patient consent and duplicate confirmations
        
        Args:
            patient_id: Patient identifier
            consent_given: Whether patient gave consent
            duplicate_confirmations: List of duplicate confirmations
            
        Returns:
            Processing result
        """
        if not consent_given:
            return {
                "success": False,
                "message": "Consent not provided. Medical history reconciliation cancelled.",
                "action": "redirect_to_registration"
            }
        
        # Process duplicate confirmations if provided
        if duplicate_confirmations:
            for confirmation in duplicate_confirmations:
                logger.info(f"Patient {patient_id} confirmed duplicate {confirmation['type']}: {confirmation['value']} from {confirmation['confirmed_source']}")
        
        return {
            "success": True,
            "message": "Consent provided. Medical history reconciliation initiated.",
            "action": "proceed_to_reconciliation",
            "consent_timestamp": datetime.now().isoformat()
        }

    def create_final_reconciled_history(self, medical_history: Dict, duplicate_confirmations: List[Dict] = None) -> Dict:
        """
        Create final reconciled medical history based on duplicate confirmations
        
        Args:
            medical_history: Original medical history with duplicates
            duplicate_confirmations: List of duplicate confirmations
            
        Returns:
            Final reconciled medical history
        """
        final_history = medical_history.copy()
        
        # If no duplicates or confirmations, return as is
        if not duplicate_confirmations or not medical_history.get('duplicates'):
            return final_history
        
        # Process duplicate confirmations
        for confirmation in duplicate_confirmations:
            duplicate_type = confirmation['type']
            duplicate_value = confirmation['value']
            confirmed_source = confirmation['confirmed_source']
            
            # Find the source data for the confirmed hospital
            confirmed_source_data = None
            for source in medical_history['sources']:
                if source['hospital_name'] == confirmed_source:
                    confirmed_source_data = source
                    break
            
            if confirmed_source_data:
                # Ensure the confirmed item is in the final list
                if duplicate_type == 'condition':
                    if duplicate_value not in final_history['conditions']:
                        final_history['conditions'].append(duplicate_value)
                elif duplicate_type == 'medication':
                    if duplicate_value not in final_history['medications']:
                        final_history['medications'].append(duplicate_value)
                elif duplicate_type == 'procedure':
                    if duplicate_value not in final_history['procedures']:
                        final_history['procedures'].append(duplicate_value)
                elif duplicate_type == 'allergy':
                    if duplicate_value not in final_history['allergies']:
                        final_history['allergies'].append(duplicate_value)
        
        # Remove duplicates from final lists
        final_history['conditions'] = list(set(final_history['conditions']))
        final_history['medications'] = list(set(final_history['medications']))
        final_history['procedures'] = list(set(final_history['procedures']))
        final_history['allergies'] = list(set(final_history['allergies']))
        
        # Add reconciliation metadata
        final_history['reconciliation_completed'] = True
        final_history['reconciliation_timestamp'] = datetime.now().isoformat()
        final_history['duplicate_confirmations'] = duplicate_confirmations
        
        return final_history


# Global instance
medical_reconciliation = MedicalHistoryReconciliation()


def get_medical_reconciliation() -> MedicalHistoryReconciliation:
    """Get the global medical reconciliation instance"""
    return medical_reconciliation
