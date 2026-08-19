import os
import sys
import json
from google import genai
from google.genai import types

def run_grounding_test():
    api_key = os.getenv("GEMINI_API_KEY")
    
    print("=" * 60)
    print("🔍 GEMINI SEARCH GROUNDING TEST RUNNER")
    print("=" * 60)
    
    if not api_key:
        print("❌ ERROR: 'GEMINI_API_KEY' environment variable is NOT set.")
        print("Please set it using: export GEMINI_API_KEY='your_key_here'")
        sys.exit(1)
        
    print(f"✓ API Key Detected: {api_key[:6]}...{api_key[-4:] if len(api_key) > 10 else ''}")

    # 1. Initialize Client
    try:
        client = genai.Client(api_key=api_key)
        print("✓ Initialized genai.Client successfully.")
    except Exception as e:
        print(f"❌ Client Initialization Failed: {e}")
        sys.exit(1)

    # 2. Configure Google Search Tool
    print("\n--- [1/3] Building Configuration ---")
    try:
        search_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[search_tool])
        print("✓ Created `types.Tool(google_search=types.GoogleSearch())` successfully.")
    except Exception as e:
        print(f"❌ Failed to construct Search Tool Config: {e}")
        sys.exit(1)

    # 3. Execute Request
    prompt = "What is the latest update or patch notes for Wuthering Waves today?"
    print(f"\n--- [2/3] Sending Request to Gemini 2.5 Flash ---")
    print(f"Prompt: \"{prompt}\"")
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config
        )
        print("✓ API Call Executed Successfully!")
    except Exception as e:
        print("\n❌ API CALL FAILED WITH ERROR:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
        print("\nPossible Causes:")
        print("  1. Key does not have permissions/quota for Search Grounding.")
        print("  2. Incorrect package version (run `pip install -U google-genai`).")
        print("  3. Host machine is blocking egress traffic to Google APIs.")
        sys.exit(1)

    # 4. Print Raw Output and Metadata
    print("\n--- [3/3] Inspecting Metadata & Grounding Results ---")
    
    candidate = response.candidates[0] if (hasattr(response, 'candidates') and response.candidates) else None
    grounding = getattr(candidate, 'grounding_metadata', None) if candidate else None

    if grounding:
        print("✅ GROUNDING METADATA FOUND:")
        
        # Display Search Queries used by Gemini
        queries = getattr(grounding, 'web_search_queries', None)
        if queries:
            print(f"  • Search Queries Executed: {queries}")
            
        # Display Retrieved Sources / Chunks
        chunks = getattr(grounding, 'grounding_chunks', None)
        if chunks:
            print(f"  • Total Web Chunks Retrieved: {len(chunks)}")
            for i, chunk in enumerate(chunks, 1):
                web = getattr(chunk, 'web', None)
                if web:
                    print(f"     [{i}] Title: {getattr(web, 'title', 'N/A')}")
                    print(f"         URI:   {getattr(web, 'uri', 'N/A')}")
    else:
        print("⚠️ NO GROUNDING METADATA: Model answered using general knowledge without searching.")

    print("\n--- Model Output Preview ---")
    print(response.text[:500] + ("..." if len(response.text or "") > 500 else ""))
    print("\n=" * 60)

if __name__ == "__main__":
    run_grounding_test()
