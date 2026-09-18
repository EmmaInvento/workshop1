from dotenv import load_dotenv
import os

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME")

PHOENIX_PROJECT_NAME: str = os.getenv(
    "PHOENIX_PROJECT_NAME", "project-1"
)
PHOENIX_COLLECTOR_ENDPOINT: str = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT",
    "http://localhost:6006/v1/traces",
)