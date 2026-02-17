"""Start the app and capture all output to a log file."""
import sys
import logging
import os

# Force unbuffered output
os.environ["PYTHONUNBUFFERED"] = "1"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("startup.log", mode="w"),
        logging.StreamHandler(sys.stdout)
    ]
)

print("Importing app...", flush=True)

try:
    from app.main import app
    print("App imported OK. Starting uvicorn...", flush=True)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
except Exception as e:
    print(f"STARTUP ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
    with open("startup.log", "a") as f:
        traceback.print_exc(file=f)
