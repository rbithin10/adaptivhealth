"""Quick test: try importing the app and print any errors."""
import sys
import traceback

print("Testing imports...", flush=True)

try:
    print("1. Config...", flush=True)
    from app.config import settings
    print(f"   OK: {settings.app_name}", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    print("2. Database...", flush=True)
    from app.database import init_db, check_db_connection, engine
    print("   OK", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    print("3. Models...", flush=True)
    from app.models import User, UserRole, AuthCredential, VitalSignRecord
    print("   OK", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    print("4. Schemas...", flush=True)
    from app.schemas import user, vital_signs, activity, alert, recommendation, risk_assessment
    print("   OK", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    print("5. Services...", flush=True)
    from app.services import ml_prediction, auth_service, encryption
    print("   OK", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    print("6. API routes...", flush=True)
    from app.api import auth, user, vital_signs, predict, activity, alert, advanced_ml, consent
    print("   OK", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    print("7. FastAPI app...", flush=True)
    from app.main import app
    print("   OK", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

print("\nAll imports successful!", flush=True)
