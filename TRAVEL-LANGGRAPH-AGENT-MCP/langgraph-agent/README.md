# Travel LangGraph Backend

Internal GenAI travel planning backend used by the Travel MCP Server.

This service owns the LangGraph workflow, state checkpointing, flight/hotel/activity lookups, budget checks, booking confirmation, and booking retrieval. It is intentionally kept as a backend service; MCP clients should connect to `travel-mcp-server`, not directly to this API.

## Runtime Role

```text
MCP Client -> travel-mcp-server -> langgraph-agent -> LangGraph / APIs / Postgres
```

## Workflow

1. Start a travel session with origin, destination, travel date, and budget.
2. Normalize date and resolve IATA airport codes.
3. Search flights with Duffel, or return controlled demo data when unavailable.
4. Search hotels with SerpAPI Google Hotels, or return controlled demo data.
5. Select flight and hotel, or skip hotel.
6. Calculate remaining budget.
7. Retrieve sightseeing recommendations when budget is valid.
8. Confirm the booking and generate a `TRV-XXXXXX` reference.
9. Retrieve confirmed bookings by reference.

## Environment

Create `langgraph-agent/.env` or configure these in Kubernetes/ECS:

```bash
OPENAI_API_KEY=
LLM_MODEL=gpt-4o
SERPAPI_API_KEY=
DUFFEL_ACCESS_TOKEN=
CHECKPOINTER_TYPE=memory
LANGGRAPH_POSTGRES_URI=
LANGGRAPH_POSTGRES_SETUP=false
LANGGRAPH_POSTGRES_POOL_MODE=null
LANGGRAPH_POSTGRES_POOL_MIN_SIZE=1
LANGGRAPH_POSTGRES_POOL_MAX_SIZE=5
LANGGRAPH_POSTGRES_POOL_MAX_IDLE=300
LANGGRAPH_POSTGRES_POOL_MAX_LIFETIME=300
LANGGRAPH_POSTGRES_POOL_TIMEOUT=30
BOOKINGS_TABLE_ENABLED=true
BOOKINGS_TABLE_SETUP=false
BOOKINGS_TABLE_NAME=bookings
```

For local demos, use `CHECKPOINTER_TYPE=memory`. For production, use `CHECKPOINTER_TYPE=postgres` and provide `LANGGRAPH_POSTGRES_URI` or `DATABASE_URL`.

Set `LANGGRAPH_POSTGRES_SETUP=true` once to create/migrate LangGraph checkpointer tables, then set it back to `false`.

Set `BOOKINGS_TABLE_SETUP=true` once to create the business booking table and indexes, then set it back to `false`.

## Local Run

```bash
cd langgraph-agent
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```text
GET /health
```

The MCP server calls:

```text
POST /chat
```

## Docker Build

```bash
cd langgraph-agent
docker build -t travel-langgraph-agent .
```

## Recommended Production Improvements

- Add authentication between the MCP server and backend.
- Add request/response tracing with correlation IDs.
- Add unit tests with mocked Duffel and SerpAPI responses.
- Add retry/backoff for upstream providers.
