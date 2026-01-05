import google.generativeai as genai
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from backend.config import get_settings

def test_search():
    settings = get_settings()
    if not settings.gemini_api_key:
        print("Error: No GEMINI_API_KEY found.")
        return

    genai.configure(api_key=settings.gemini_api_key)
    
    # Try using the tools configuration
    # Note: Search grounding might require specific model versions or beta flags
    # We will try with standard syntax
    tools = [
        {"google_search": {}} # Syntax often used in other client libs, let's try standard SDK way
    ]
    
    try:
        # standard SDK often just takes tools arg in model or generate_content
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest') 
        
        # New dynamic retrieval syntax check
        from google.generativeai.types import content_types
        from collections.abc import Iterable
        
        print("Asking Gemini to search for real-time dollar price in Chile...")
        
        response = model.generate_content(
            "¿A cuánto está el dólar observado en Chile hoy? Busca la información actual en internet.",
            tools='google_search_retrieval' # Correct string for the tool alias in some versions
        )
        
        print(f"\nResponse Text: {response.text}")
        print(f"\nCandidates: {response.candidates}")
        
    except Exception as e:
        print(f"Error testing search: {e}")
        # Try alternative syntax if first fails
        try:
             print("\nRetrying with tool config object...")
             tool_config = {'google_search': {}}
             model = genai.GenerativeModel('models/gemini-1.5-flash-latest', tools=[tool_config])
             response = model.generate_content("Precio actual del dolar en Chile")
             print(response.text)
        except Exception as e2:
             print(f"Retry failed too: {e2}")

if __name__ == "__main__":
    test_search()
