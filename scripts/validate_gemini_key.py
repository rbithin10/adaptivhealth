"""
Gemini API Key Validation Script
---------------------------------
Sends a minimal test prompt to Gemini 2.0 Flash to verify the API key
configured in .env.local (or .env) is valid and the model is reachable.

Usage:
    python scripts/validate_gemini_key.py

Requirements:
    pip install google-generativeai python-dotenv
"""

import sys
import os

# ---------------------------------------------------------------------------
# Load .env.local first, fall back to .env
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
except ImportError:
    print("[ERROR] python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env_local = os.path.join(BASE_DIR, ".env.local")
env_default = os.path.join(BASE_DIR, ".env")

if os.path.exists(env_local):
    load_dotenv(env_local, override=True)
    print(f"[INFO] Loaded environment from: .env.local")
elif os.path.exists(env_default):
    load_dotenv(env_default, override=True)
    print(f"[INFO] Loaded environment from: .env")
else:
    print("[WARNING] No .env.local or .env file found. Falling back to system env.")

# ---------------------------------------------------------------------------
# Read key
# ---------------------------------------------------------------------------
GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_API_KEY")
    or os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
)

if not GEMINI_API_KEY:
    print("[ERROR] GEMINI_API_KEY not found in environment.")
    print("        Add it to .env.local as:  GEMINI_API_KEY=<your-key>")
    sys.exit(1)

masked = GEMINI_API_KEY[:8] + "..." + GEMINI_API_KEY[-4:]
print(f"[INFO] API key found: {masked}")

# ---------------------------------------------------------------------------
# Import google-generativeai
# ---------------------------------------------------------------------------
try:
    import google.generativeai as genai
except ImportError:
    print("[ERROR] google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Send test prompt
# ---------------------------------------------------------------------------
MODEL_NAME = "gemini-2.0-flash"
TEST_PROMPT = "Reply with exactly: OK"

print(f"[INFO] Configuring Gemini with model: {MODEL_NAME}")
genai.configure(api_key=GEMINI_API_KEY)

try:
    model = genai.GenerativeModel(MODEL_NAME)
    print(f"[INFO] Sending test prompt: \"{TEST_PROMPT}\"")
    response = model.generate_content(
        TEST_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=20,
        ),
    )
    reply = response.text.strip()
    print(f"\n[SUCCESS] Gemini responded: \"{reply}\"")
    print("\n✅  API key is valid and Gemini 2.0 Flash is reachable.")
    sys.exit(0)

except Exception as e:
    error_str = str(e)
    print(f"\n[ERROR] Gemini call failed: {error_str}")

    if "API_KEY_INVALID" in error_str or "invalid api key" in error_str.lower():
        print("\n❌  The API key is INVALID. Generate a new one at: https://aistudio.google.com/app/apikey")
    elif "quota" in error_str.lower() or "429" in error_str:
        print("\n⚠️  API key is valid but QUOTA EXCEEDED (free tier 15 RPM limit). Try again in 1 minute.")
    elif "not found" in error_str.lower() or "404" in error_str:
        print(f"\n⚠️  Model '{MODEL_NAME}' not found for this key. Check API availability.")
    elif "permission" in error_str.lower() or "403" in error_str:
        print("\n⚠️  API key exists but does NOT have access to Gemini API. Enable Generative Language API in Google Cloud.")
    else:
        print("\n❌  Unexpected error. Check internet connectivity and key validity.")

    sys.exit(1)
