from langchain_openai import ChatOpenAI
ak = "sk-h2zLW0DZLXXgWkqwfvrZWg"
model = ChatOpenAI(
    base_url="https://genai-sharedservice-apac.pwcinternal.com",
    api_key=ak,  # use your actual key
    model="azure.gpt-4o-2024-11-20",      # from your curl
)

response = model.invoke("hi")
print(response)