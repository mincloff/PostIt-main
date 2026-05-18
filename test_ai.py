import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
import google.generativeai as genai

# 1. Load the keys directly from your .env file
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("ERROR: Could not find GEMINI_API_KEY in the .env file!")
else:
    print(f"SUCCESS: API Key loaded starting with: {api_key[:10]}...")

# 2. Authenticate with Google
genai.configure(api_key=api_key)

# 3. Ask Google what models your specific key is allowed to use
print("\n--- MODELS AVAILABLE TO YOUR KEY ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
    print("------------------------------------")
except Exception as e:
    print(f"Google API Error: {e}")