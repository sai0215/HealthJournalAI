from std_hub.llm import AgentProject
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Perplexity API Configuration from environment variables
API_KEY = os.environ.get("PERPLEXITY_API_KEY", "your_perplexity_api_key_here")
BASE_URL = os.environ.get("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")

# Initialize the Perplexity client (OpenAI-compatible)
model = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)
 
 
def project_init(project: AgentProject) -> AgentProject:
    project.setup(
        model=model,
        base_client=model,
        project_id="symptom_checker_flow",
        project_name="Symptom Checker Assistant",
        description="An AI-powered symptom checker that maps user symptoms to possible conditions using a structured medical database, suggests tests, and guides users on appropriate actions.",
        inputs_types={
            "user_symptoms": {
                "description": "brief description of user symptoms",
                "type": "str"
            }
        }
    )

    # ✅ Add default kickoff ID to avoid NoneType error
    project.kickoff_id = "default_user_kickoff"

    # ---- Message templates (unchanged) ---- #
    project.set_llm_messages(
    message_id="symptom_checker_template",
    message=[
        {
            "role": "system",
            "content": (
                "You are a medical assistant. Based on the user's symptoms {user_symptoms}, "
                "details about symptom duration and triggers: {symptom_details}, "
                "past medical history: {past_medical_history}, "
                "and matched records {matched_records}, generate a personalized diagnostic report including tests and consult suggestions..."
            )
        },
        {
            "role": "user",
            "content": "Please provide the health advisory report."
        }
        ]
    )

    project.set_llm_messages(
        message_id="extract_tests_template",
        message=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Extract all test names listed in the Suggested tests/Recommended tests section in the {report} "
                    "Don't leave any test names mentioned and return them only as a valid list of strings without any special characters.\n"
                    "Don't add any unnecessary tests of your own into it."
                )
            },
            {
                "role": "user",
                "content": "{report}"
            }
        ]
    )

    project.set_llm_messages(
        message_id="map_symptoms_template",
        message=[
            {
                "role": "system",
                "content": (
                    "You are a medical assistant. Map each user symptom to the most relevant dataset column using the provided synonym database. "
                    "Synonym database: {synonym_mappings} "
                    "User symptoms: {user_symptoms} "
                    "Dataset columns: {dataset_columns} "
                    "Output a list of mapped symptoms using dataset column names only. "
                    '✅ Example output:["fever", "cold", "cough"]'
                )
            },
            {
                "role": "user",
                "content": (
                    "User symptoms: {user_symptoms}\n"
                    "Dataset columns: {dataset_columns}\n"
                    "Map each symptom to the most relevant column."
                )
            }
        ]
    )

    return project
