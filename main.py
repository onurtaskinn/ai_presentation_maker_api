# fastapi_main.py - Updated
import json
import os
from datetime import datetime, timedelta, timezone
import time
from dotenv import load_dotenv

# Import the app from the new location
from api.app import app

# Import all modules to register endpoints
import api.auth
import api.endpoints
import api.presentation

# Import necessary for direct execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)