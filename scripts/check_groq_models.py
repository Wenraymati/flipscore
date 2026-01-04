import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

try:
    models = client.models.list()
    print(f"Found {len(models.data)} models. IDs:")
    all_ids = [m.id for m in models.data]
    for m_id in all_ids:
        print(f" - {m_id}")
        
    print("\nVision models candidates:")
    for m_id in all_ids:
        if "vision" in m_id.lower():
            print(f"FOUND: {m_id}")
            
except Exception as e:
    print(e)
