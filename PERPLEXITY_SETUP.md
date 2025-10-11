# 🔄 Perplexity Sonar Pro Integration Guide

The Health Assistant has been successfully migrated from OpenAI/Azure GPT to **Perplexity Sonar Pro**.

## ✅ What Was Changed

### Files Updated

#### 1. **`.env`** (Environment Variables) - NEW!
Added Perplexity API configuration:
```bash
# Perplexity API Configuration
PERPLEXITY_API_KEY=your_perplexity_api_key_here
PERPLEXITY_BASE_URL=https://api.perplexity.ai
PERPLEXITY_MODEL=sonar-pro
```

#### 2. **`std_hub/constants.py`**
- ✅ Now uses environment variables from `.env`
- ✅ Loads Perplexity configuration
- ✅ Removed hardcoded API keys

**Before:**
```python
BASE_URL="https://api.openai.com/v1/"
API_KEY="sk-proj-..."
MODEL="gpt-4o-mini"
```

**After:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("PERPLEXITY_API_KEY")
BASE_URL = os.environ.get("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")
```

#### 3. **`project.py`**
- ✅ Changed from `ChatOpenAI` (LangChain) to `OpenAI` client
- ✅ Uses Perplexity-compatible configuration
- ✅ Loads from environment variables

**Before:**
```python
from langchain_openai import ChatOpenAI
model = ChatOpenAI(
    base_url="https://genai-sharedservice-apac.pwcinternal.com",
    api_key=API_KEY,
    model="azure.gpt-4o-2024-11-20"
)
```

**After:**
```python
from openai import OpenAI
model = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)
```

#### 4. **`app.py`** (CLI Application)
- ✅ Updated to use Perplexity via OpenAI client
- ✅ Loads configuration from environment variables
- ✅ Removed hardcoded credentials

#### 5. **`streamlit_app.py`** (Web UI)
- ✅ Changed from LangChain's `ChatOpenAI` to `OpenAI` client
- ✅ Uses environment variables for configuration
- ✅ Cached initialization with Perplexity client

#### 6. **`std_hub/llm.py`** (Core LLM Module)
- ✅ Updated `generate()` method for OpenAI-compatible API
- ✅ Changed from `client.invoke()` to `client.chat.completions.create()`
- ✅ Improved token usage tracking
- ✅ Works with Perplexity Sonar Pro

**Before:**
```python
response = main_client.invoke(messages)
raw = response.content
```

**After:**
```python
response = main_client.chat.completions.create(
    model=model,
    messages=messages
)
raw = response.choices[0].message.content
```

#### 7. **`.gitignore`** - NEW!
- ✅ Created to protect sensitive files
- ✅ Excludes `.env`, API keys, virtual environments
- ✅ Prevents accidental commits of credentials

## 🔑 How to Get Your Perplexity API Key

### Step 1: Sign Up for Perplexity
1. Go to [Perplexity API](https://www.perplexity.ai/api)
2. Create an account or sign in
3. Navigate to API Settings

### Step 2: Generate API Key
1. Click "Generate New API Key"
2. Copy your API key (starts with `pplx-...`)
3. Store it securely

### Step 3: Add to .env File
Open `/Users/saivignesh/Downloads/Health Journal/.env` and update:

```bash
# Replace with your actual Perplexity API key
PERPLEXITY_API_KEY=pplx-your-actual-api-key-here
PERPLEXITY_BASE_URL=https://api.perplexity.ai
PERPLEXITY_MODEL=sonar-pro
```

**Available Models:**
- `sonar-pro` - Most powerful (recommended)
- `sonar` - Fast and efficient
- `sonar-reasoning` - Advanced reasoning
- `sonar-chat` - Conversational

## 🚀 Testing the Integration

### Test 1: MongoDB Connection
```bash
python test_mongodb_connection.py
```

Expected output:
```
✅ SUCCESS: MongoDB Atlas is connected!
✅ Application imports successful - ready to run!
```

### Test 2: Run Streamlit App
```bash
./run_streamlit.sh
```

Or:
```bash
source venv_mac/bin/activate
streamlit run streamlit_app.py
```

### Test 3: Run CLI App
```bash
source venv_mac/bin/activate
python app.py
```

## 📋 Configuration Reference

### Current `.env` File Structure

```bash
# MongoDB Atlas Configuration
MONGODB_URI=mongodb+srv://saivigneshguturu:ocwYxcpJbk74WbgL@cluster0.zoukpmy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0

# Perplexity API Configuration
PERPLEXITY_API_KEY=your_perplexity_api_key_here
PERPLEXITY_BASE_URL=https://api.perplexity.ai
PERPLEXITY_MODEL=sonar-pro
```

### API Endpoint Reference

**Perplexity API:**
- Base URL: `https://api.perplexity.ai`
- Docs: https://docs.perplexity.ai/
- Models: https://docs.perplexity.ai/docs/model-cards

**OpenAI-Compatible Format:**
```python
POST /chat/completions
Headers:
  - Authorization: Bearer {PERPLEXITY_API_KEY}
  - Content-Type: application/json

Body:
{
  "model": "sonar-pro",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello"}
  ]
}
```

## 🔐 Security Best Practices

### ✅ DO:
- Store API keys in `.env` file
- Add `.env` to `.gitignore`
- Use environment variables
- Rotate keys periodically
- Keep `.env` file private

### ❌ DON'T:
- Hardcode API keys in code
- Commit `.env` to Git
- Share API keys publicly
- Use production keys in development
- Store keys in plain text files

## 🆚 Perplexity vs OpenAI/Azure

| Feature | Perplexity Sonar Pro | OpenAI GPT-4 | Azure GPT |
|---------|---------------------|--------------|-----------|
| **Real-time Data** | ✅ Yes | ❌ No | ❌ No |
| **Web Search** | ✅ Built-in | ❌ Requires plugins | ❌ Requires plugins |
| **Citations** | ✅ Automatic | ❌ Manual | ❌ Manual |
| **Cost** | 💰 Moderate | 💰💰 Higher | 💰💰 Higher |
| **Speed** | ⚡ Fast | ⚡ Fast | ⚡ Moderate |
| **Context Window** | 🔢 Large | 🔢 Large | 🔢 Large |

## 💡 Why Perplexity?

### Advantages:
1. **Real-time Information** - Access to current data
2. **Built-in Search** - No need for external tools
3. **Citations** - Automatic source attribution
4. **Cost-Effective** - Competitive pricing
5. **OpenAI Compatible** - Easy migration

### Use Cases:
- Medical information that requires current data
- Symptom analysis with latest research
- Diagnostic recommendations with citations
- Real-time health updates

## 🛠️ Troubleshooting

### Issue: "Invalid API Key"
**Solution:** 
1. Check your `.env` file has the correct key
2. Ensure key starts with `pplx-`
3. Verify no extra spaces in the key
4. Restart the application

### Issue: "Connection Error"
**Solution:**
1. Check internet connection
2. Verify Perplexity API is accessible
3. Check firewall settings
4. Try: `curl -I https://api.perplexity.ai`

### Issue: "Model Not Found"
**Solution:**
1. Verify model name in `.env` is correct
2. Available models: `sonar-pro`, `sonar`, `sonar-reasoning`, `sonar-chat`
3. Check Perplexity docs for current models

### Issue: "Rate Limit Exceeded"
**Solution:**
1. Check your API plan limits
2. Implement rate limiting in code
3. Upgrade your Perplexity plan
4. Add retry logic with backoff

## 📊 Token Usage & Costs

### Perplexity Sonar Pro Pricing (as of 2025)
- Input: ~$X per 1M tokens
- Output: ~$X per 1M tokens
- Includes search in base price

### Monitoring Usage
The application now tracks token usage:
```python
result = {
    "raw": response_text,
    "token_usage": {
        "prompt_tokens": 150,
        "completion_tokens": 300,
        "total_tokens": 450
    }
}
```

## 🔄 Rollback to OpenAI (If Needed)

If you need to switch back to OpenAI:

### Quick Rollback:
1. Update `.env`:
```bash
PERPLEXITY_API_KEY=sk-your-openai-key
PERPLEXITY_BASE_URL=https://api.openai.com/v1
PERPLEXITY_MODEL=gpt-4o-mini
```

2. Restart application

Note: The code is OpenAI-compatible, so it works with both!

## 📚 Additional Resources

- **Perplexity API Docs:** https://docs.perplexity.ai/
- **Model Cards:** https://docs.perplexity.ai/docs/model-cards
- **Pricing:** https://www.perplexity.ai/api/pricing
- **OpenAI Compatibility:** Uses standard OpenAI SDK

## ✨ Next Steps

1. ✅ Get Perplexity API key
2. ✅ Update `.env` file
3. ✅ Test the integration
4. ✅ Monitor token usage
5. ⏭️ Optimize prompts for Perplexity
6. ⏭️ Leverage real-time search capabilities
7. ⏭️ Implement citation display

## 🎉 Summary

Your Health Assistant is now powered by **Perplexity Sonar Pro**!

### Migration Complete:
- ✅ All API keys moved to `.env`
- ✅ OpenAI/LangChain replaced with OpenAI client
- ✅ Perplexity configuration ready
- ✅ Token tracking implemented
- ✅ Security improved with `.gitignore`

### Action Required:
- ⏳ Add your Perplexity API key to `.env`
- ⏳ Test the application
- ⏳ Update model if needed

---

**Need Help?**
- Check this guide
- Review `.env.template` for format
- Test with `python test_mongodb_connection.py`
- Read Perplexity docs for advanced features

**Created:** 2025-01-11  
**Status:** ✅ Ready for API Key

