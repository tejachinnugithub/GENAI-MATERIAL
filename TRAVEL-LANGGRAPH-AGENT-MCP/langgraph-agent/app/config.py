import logging
import os
import sys

from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("travel-langgraph-agent")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o")
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")
DUFFEL_ACCESS_TOKEN = os.environ.get("DUFFEL_ACCESS_TOKEN")

CHECKPOINTER_TYPE = os.environ.get("CHECKPOINTER_TYPE", "memory").lower()
LANGGRAPH_POSTGRES_URI = os.environ.get("LANGGRAPH_POSTGRES_URI") or os.environ.get("DATABASE_URL")
LANGGRAPH_POSTGRES_SETUP = os.environ.get("LANGGRAPH_POSTGRES_SETUP", "false").lower() == "true"
LANGGRAPH_POSTGRES_POOL_MODE = os.environ.get("LANGGRAPH_POSTGRES_POOL_MODE", "null").lower()
LANGGRAPH_POSTGRES_POOL_MIN_SIZE = int(os.environ.get("LANGGRAPH_POSTGRES_POOL_MIN_SIZE", "1"))
LANGGRAPH_POSTGRES_POOL_MAX_SIZE = int(os.environ.get("LANGGRAPH_POSTGRES_POOL_MAX_SIZE", "5"))
LANGGRAPH_POSTGRES_POOL_MAX_IDLE = float(os.environ.get("LANGGRAPH_POSTGRES_POOL_MAX_IDLE", "300"))
LANGGRAPH_POSTGRES_POOL_MAX_LIFETIME = float(os.environ.get("LANGGRAPH_POSTGRES_POOL_MAX_LIFETIME", "300"))
LANGGRAPH_POSTGRES_POOL_TIMEOUT = float(os.environ.get("LANGGRAPH_POSTGRES_POOL_TIMEOUT", "30"))

BOOKINGS_TABLE_ENABLED = os.environ.get("BOOKINGS_TABLE_ENABLED", "true").lower() == "true"
BOOKINGS_TABLE_SETUP = os.environ.get("BOOKINGS_TABLE_SETUP", "false").lower() == "true"
BOOKINGS_TABLE_NAME = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
