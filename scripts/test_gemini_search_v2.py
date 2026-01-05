import google.generativeai as genai
import os
import sys

sys.path.append(os.getcwd())
from backend.config import get_settings

def test_search_v2():
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    # Try gemini-1.5-flash with proper tool string
    model_name = "gemini-1.5-flash" 
    
    try:
        print(f"Testing {model_name} with tools='google_search_retrieval'...")
        model = genai.GenerativeModel(model_name, tools='google_search_retrieval')
        
        response = model.generate_content("¿Cuál es el precio promedio de un iPhone XR usado en Chile hoy?")
        
        print(f"\nResponse: {response.text}")
        # Check if grounding metadata exists
        if response.candidates[0].grounding_metadata:
            print("\n✅ Grounding Metadata found! (Search worked)")
            print(response.candidates[0].grounding_metadata)
        else:
            print("\n❌ No grounding metadata.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search_v2()
