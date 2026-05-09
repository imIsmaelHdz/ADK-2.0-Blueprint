import os
from dotenv import load_dotenv

load_dotenv()

# For local development, default to API-key auth (non-Vertex) when a key is present.
# This keeps `uvicorn travel_helper_api.main:app` working without extra exports.
if os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"

APP_NAME = "travel_helper_api"
API_TITLE = "Travel Helper API Gateway"
API_VERSION = "1.0.0"
