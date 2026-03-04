"""
DEV ONLY - Manual test for Gemini chat service.
Run: python scripts/_test_chat.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import get_db
from app.services.chat_service import generate_chat_response

db = next(get_db())

TESTS = [
    ("How is my heart rate looking today?", "template: risk_summary"),
    ("What workout should I do today?",      "template: workout"),
    ("What is cardiac rehabilitation?",      "open-ended → Gemini"),
    ("Tell me about a healthy diet",         "open-ended → Gemini"),
]

async def run():
    print("\n" + "="*60)
    print("  ADAPTIVHEALTH CHAT SERVICE TEST  (user_id=3 / patient)")
    print("="*60)
    for msg, expected_path in TESTS:
        print(f"\n[EXPECTED PATH] {expected_path}")
        print(f"[Q] {msg}")
        try:
            result = await generate_chat_response(
                user_message=msg,
                user_id=3,
                db=db,
                conversation_history=[],
                screen_context="home",
            )
            source = result["source"]
            response = result["response"]
            print(f"[SOURCE]   {source}")
            print(f"[RESPONSE] {response[:400]}")
            print(f"[STATUS]   {'OK' if response else 'EMPTY RESPONSE'}")
        except Exception as e:
            print(f"[ERROR]    {type(e).__name__}: {e}")
    print("\n" + "="*60)
    print("Test complete.")
    print("="*60)

asyncio.run(run())
