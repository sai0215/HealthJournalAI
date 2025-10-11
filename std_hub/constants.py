
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Perplexity API Configuration (from .env)
API_KEY = os.environ.get("PERPLEXITY_API_KEY", "your_perplexity_api_key_here")
BASE_URL = os.environ.get("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")

# Base server URL for local services
base_server_url = "http://0.0.0.0:8000"

# Legacy configurations (commented out)
# API_KEY="lm-studio"
# BASE_URL="http://127.0.0.1:1234/v1"
# MODEL="llama-3.2-1b-instruct"

# OpenAI Configuration (legacy)
# BASE_URL="https://api.openai.com/v1/"
# API_KEY="sk-proj-..."
# MODEL="gpt-4o-mini"

# Azure Configuration (legacy)
# API_KEY='sk-w2FSnMmjDyj5ZWgcR8H7hw'
# BASE_URL='https://genai-sharedservice-apac.pwcinternal.com/'
# MODEL="azure.gpt-4-1106-preview"


