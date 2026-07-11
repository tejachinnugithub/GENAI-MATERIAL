# Travel MCP Server

MCP adapter microservice for the existing Travel LangGraph backend.

The service exposes the travel backend as MCP tools over Streamable HTTP:

```text
Claude / MCP Client -> Travel MCP Server -> Travel LangGraph API
```

## Tools

- `create_travel_booking`: complete booking flow with cheapest available flight and hotel.
- `start_travel_plan`: start a session and return flight/hotel options.
- `select_flight`: select a flight for a session.
- `select_hotel`: select a hotel for a session.
- `skip_hotel`: continue without hotel selection.
- `update_budget`: update the budget for an active session.
- `get_activities`: retrieve activity recommendations.
- `confirm_booking`: confirm itinerary and generate booking reference.
- `retrieve_booking`: retrieve a confirmed booking by reference.

## Resource

- `booking://{booking_reference}`: read a confirmed itinerary as JSON.

## Environment

```bash
TRAVEL_AGENT_API_URL=http://localhost:8000/chat
MCP_SERVER_NAME="Travel Booking MCP Server"
REQUEST_TIMEOUT_SECONDS=90
LOG_LEVEL=INFO
```

## Local Run

Start the existing LangGraph backend first:

```bash
cd ../langgraph-agent
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then start the MCP server:

```bash
cd ../travel-mcp-server
pip install -r requirements.txt
uvicorn app.server:app --host 0.0.0.0 --port 8001
```

The MCP endpoint is:

```text
http://localhost:8001/mcp
```

Health check:

```text
http://localhost:8001/health
```

## Claude Code Example

```bash
claude mcp add --transport http travel-booking http://localhost:8001/mcp
```

For Kubernetes ingress, replace the URL with your public host:

```bash
claude mcp add --transport http travel-booking https://<your-https-host>/mcp
```

The server is configured for reverse proxies/tunnels by setting FastMCP `host="0.0.0.0"`. Without that, FastMCP's localhost DNS rebinding protection can reject public tunnel hostnames with `Invalid Host header`.

## Docker Build

```bash
docker build -t travel-mcp-server .
```
