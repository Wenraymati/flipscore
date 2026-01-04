import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Searching for Gemini models...")
found = False
for m in genai.list_models():
    if 'gemini' in m.name.lower() and 'generateContent' in m.supported_generation_methods:
        print(f"ID: {m.name}")
        found = True

if not found:
    print("No models found matching 'gemini' + 'generateContent'")
