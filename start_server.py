"""Start the app and capture all output to a log file so we can debug startup problems."""
import sys
import logging
import os

# Make sure print statements appear immediately instead of being buffered
os.environ["PYTHONUNBUFFERED"] = "1"

# Set up logging to write to both a file and the console at the same time
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # Save all log messages to a file called "startup.log"
        logging.FileHandler("startup.log", mode="w"),
        # Also print log messages to the console so we can see them live
        logging.StreamHandler(sys.stdout)
    ]
)

# Let the developer know we are beginning the import process
print("Importing app...", flush=True)

try:
    # Load the main FastAPI application from the app folder
    from app.main import app
    print("App imported OK. Starting uvicorn...", flush=True)
    # Uvicorn is the web server that actually listens for HTTP requests
    import uvicorn
    # Start the server on all network interfaces (0.0.0.0) at port 8080
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
except Exception as e:
    # If anything goes wrong during startup, print the error clearly
    print(f"STARTUP ERROR: {e}", flush=True)
    import traceback
    # Show the full error trace so we can pinpoint the problem
    traceback.print_exc()
    # Also save the error trace to the log file for later review
    with open("startup.log", "a") as f:
        traceback.print_exc(file=f)
