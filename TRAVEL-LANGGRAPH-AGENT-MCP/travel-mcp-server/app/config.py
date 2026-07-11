import logging
import os
import sys


logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("TRAVEL_MCP_SERVER")

TRAVEL_AGENT_API_URL = os.environ.get("TRAVEL_AGENT_API_URL", "http://localhost:8000/chat")
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "90"))
MCP_SERVER_NAME = os.environ.get("MCP_SERVER_NAME", "Travel Booking MCP Server")

