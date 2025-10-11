import json
import pandas as pd
from datetime import datetime
from std_hub.llm import AgentProject
from openai import OpenAI
from project import project_init
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Perplexity API Configuration from environment variables
API_KEY = os.environ.get("PERPLEXITY_API_KEY", "your_perplexity_api_key_here")
BASE_URL = os.environ.get("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")

# Initialize Perplexity client
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
project = AgentProject()
project = project_init(project)

# Load patient data from the Excel file
def load_patient_data(filepath):
    try:
        return pd.read_excel(filepath)
    except Exception as e:
        logging.error(f"Error loading patient data: {e}")
        return pd.DataFrame()  # Returns an empty DataFrame on failure

# Helper function to ask user feedback
async def ask_for_feedback_n(wsuid: str, prompt: str, final_answer: str):
    logging.info(f"Bot: {prompt}")
    user_input = input("User: ")
    logging.info(f"User: {user_input.strip()}")
    return {"feedback": user_input.strip()}

def serialize_patient_info(patient_info):
    serializable_info = {}
    for key, value in patient_info.items():
        if isinstance(value, datetime):
            serializable_info[key] = value.isoformat()
        else:
            serializable_info[key] = value
    return serializable_info

class SymptomCheckerFlow:

    def __init__(self, patient_data):
        self._state = {}
        self.project = project
        self.project.kickoff_id = "default_user_kickoff"
        self.patient_data = patient_data

    async def start_flow(self):
        await self.greet_and_collect_patient_id()

    async def greet_and_collect_patient_id(self):
        prompt = "Welcome to the Health Assistant! Please enter your Patient ID or UHID to begin."
        response = await ask_for_feedback_n(wsuid=self.project.kickoff_id, prompt=prompt, final_answer=prompt)
        patient_id = response.get("feedback", "").strip()

        if not self.is_valid_patient_id(patient_id):
            await ask_for_feedback_n(wsuid=self.project.kickoff_id, prompt="Invalid Patient ID. Please try again.", final_answer="")
            return await self.greet_and_collect_patient_id()

        self._state['patient_id'] = patient_id
        self._state['patient_records'] = await self.fetch_patient_records(patient_id)
        await self.collect_clarifying_questions()

    def is_valid_patient_id(self, patient_id):
        return patient_id in self.patient_data['Patient ID'].astype(str).values

    async def fetch_patient_records(self, patient_id):
        logging.info(f"Fetching records for Patient ID: {patient_id}")
        patient_row = self.patient_data[self.patient_data['Patient ID'].astype(str) == str(patient_id)]

        if patient_row.empty:
            logging.warning(f"No record found for Patient ID: {patient_id}")
            return {}

        return patient_row.iloc[0].to_dict()

    async def collect_clarifying_questions(self):
        patient_records = self._state.get('patient_records', {})
        allergies = patient_records.get("Drug Allergies", "Unknown")
        chronic_conditions = patient_records.get("Past Medical History", "Unknown")

        logging.info(f"Patient Allergies: {allergies}")
        logging.info(f"Patient Chronic Conditions: {chronic_conditions}")

        # Ask about new info
        prompt = "Do you have any new allergies or chronic conditions you should mention?"
        response = await ask_for_feedback_n(wsuid=self.project.kickoff_id, prompt=prompt, final_answer=prompt)
        additional_info = response.get("feedback", "").strip()

        prompt_symptom_change = "Have you noticed any sudden changes in your symptoms?"
        response_symptom_change = await ask_for_feedback_n(wsuid=self.project.kickoff_id, prompt=prompt_symptom_change, final_answer=prompt_symptom_change)
        symptom_changes = response_symptom_change.get("feedback", "").strip()

        self._state['additional_info'] = additional_info
        self._state['symptom_changes'] = symptom_changes

        await self.organize_data()

    async def organize_data(self):
        structured_data = {
            "patient_info": serialize_patient_info(self._state.get('patient_records', {})),
            "additional_info": self._state.get('additional_info'),
            "symptom_changes": self._state.get('symptom_changes')
        }

        diagnostic_tests = self.recommend_diagnostic_tests(structured_data)
        self._state['structured_data'] = structured_data
        self._state['diagnostic_tests'] = diagnostic_tests

        await self.generate_summary()

    def recommend_diagnostic_tests(self, data):
        symptoms = data['symptom_changes']
        recommendations = []

        if not symptoms:
            return ["No significant symptom changes reported. Monitor patient."]

        symptoms_lower = symptoms.lower()

        if "fever" in symptoms_lower:
            recommendations.append("Suggest CBC for fever pattern")
        if "cough" in symptoms_lower:
            recommendations.append("Suggest Chest X-Ray for persistent cough")
        if "fatigue" in symptoms_lower:
            recommendations.append("Suggest thyroid function and iron panel tests")
        if "headache" in symptoms_lower:
            recommendations.append("Suggest neurological exam or CT scan")
        if "pain" in symptoms_lower:
            recommendations.append("Recommend pain location-specific imaging or labs")

        return recommendations

    async def generate_summary(self):
        final_summary = {
            "structured_data": self._state['structured_data'],
            "diagnostic_tests": self._state['diagnostic_tests'],
        }

        logging.info(f"Final Summary: {json.dumps(final_summary, indent=2)}")
        await self.log_to_his(final_summary)
        
        # Friendly final message to user
        print("\nThank you! Your health details and symptom information have been successfully logged in our system.")
        print("Our healthcare team will review the information and get back to you if needed.\n")


    async def log_to_his(self, summary):
        logging.info(f"Logging summary to HIS: {summary}")

# For testing/debugging locally
if __name__ == "__main__":
    import asyncio

    patient_data = load_patient_data("Dummy Patient Data for OCR Use Case.xlsx")
    flow = SymptomCheckerFlow(patient_data)
    asyncio.run(flow.start_flow())
