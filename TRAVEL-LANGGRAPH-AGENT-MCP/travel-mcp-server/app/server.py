from __future__ import annotations

import contextlib
import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.config import MCP_SERVER_NAME
from app.travel_client import call_agent, compact_itinerary, new_thread_id, select_cheapest


mcp = FastMCP(
    MCP_SERVER_NAME,
    instructions=(
        "Use these tools to plan and confirm travel bookings through the existing "
        "LangGraph travel backend. For a complete booking in one step, use "
        "create_travel_booking. For guided user choice, start with start_travel_plan, "
        "then select a flight, select or skip hotel, and confirm the booking."
    ),
    host="0.0.0.0",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
async def start_travel_plan(
    origin: str,
    destination: str,
    travel_date_input: str,
    total_budget: float,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Start a travel planning session and return available flight and hotel options."""
    session_id = thread_id or new_thread_id()
    response = await call_agent(
        {
            "thread_id": session_id,
            "action": "start",
            "data": {
                "origin": origin,
                "destination": destination,
                "travel_date_input": travel_date_input,
                "total_budget": total_budget,
            },
        }
    )
    response["thread_id"] = session_id
    return response


@mcp.tool()
async def select_flight(
    thread_id: str,
    selected_flight_price: float,
    selected_flight_info: str,
) -> dict[str, Any]:
    """Select a flight for an active travel planning session."""
    response = await call_agent(
        {
            "thread_id": thread_id,
            "action": "select_prices",
            "data": {
                "selected_flight_price": selected_flight_price,
                "selected_flight_info": selected_flight_info,
            },
        }
    )
    response["thread_id"] = thread_id
    return response


@mcp.tool()
async def select_hotel(
    thread_id: str,
    selected_hotel_price: float,
    selected_hotel_name: str,
) -> dict[str, Any]:
    """Select a hotel for an active travel planning session."""
    response = await call_agent(
        {
            "thread_id": thread_id,
            "action": "select_prices",
            "data": {
                "selected_hotel_price": selected_hotel_price,
                "selected_hotel_name": selected_hotel_name,
            },
        }
    )
    response["thread_id"] = thread_id
    return response


@mcp.tool()
async def skip_hotel(thread_id: str) -> dict[str, Any]:
    """Skip hotel planning and continue with a flight-only itinerary."""
    response = await call_agent({"thread_id": thread_id, "action": "skip_hotel"})
    response["thread_id"] = thread_id
    return response


@mcp.tool()
async def update_budget(thread_id: str, total_budget: float) -> dict[str, Any]:
    """Update the budget for an active travel planning session."""
    response = await call_agent(
        {
            "thread_id": thread_id,
            "action": "fix_budget",
            "data": {"total_budget": total_budget},
        }
    )
    response["thread_id"] = thread_id
    return response


@mcp.tool()
async def get_activities(thread_id: str) -> dict[str, Any]:
    """Retrieve or generate sightseeing/activity recommendations for the itinerary."""
    response = await call_agent({"thread_id": thread_id, "action": "get_activities"})
    response["thread_id"] = thread_id
    return response


@mcp.tool()
async def confirm_booking(thread_id: str) -> dict[str, Any]:
    """Confirm an active itinerary and generate a booking reference."""
    response = await call_agent({"thread_id": thread_id, "action": "confirm_booking"})
    response["thread_id"] = thread_id
    return compact_itinerary(response)


@mcp.tool()
async def retrieve_booking(booking_reference: str, thread_id: str | None = None) -> dict[str, Any]:
    """Retrieve a confirmed itinerary by booking reference."""
    response = await call_agent(
        {
            "thread_id": thread_id or new_thread_id(),
            "reference": booking_reference,
            "action": "retrieve",
        }
    )
    return compact_itinerary(response)


@mcp.tool()
async def create_travel_booking(
    origin: str,
    destination: str,
    travel_date_input: str,
    total_budget: float,
    include_hotel: bool = True,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Create a complete booking by choosing the cheapest available flight and hotel."""
    session_id = thread_id or new_thread_id()
    plan = await start_travel_plan(origin, destination, travel_date_input, total_budget, session_id)

    flight = select_cheapest(plan.get("flight_options") or [])
    if not flight:
        raise ToolError("No flight options were returned by the travel backend.")

    await select_flight(
        session_id,
        selected_flight_price=float(flight["price"]),
        selected_flight_info=flight.get("info") or flight.get("airline") or "Selected flight",
    )

    selected_hotel: dict[str, Any] | None = None
    if include_hotel:
        selected_hotel = select_cheapest(plan.get("hotel_options") or [])
        if selected_hotel:
            await select_hotel(
                session_id,
                selected_hotel_price=float(selected_hotel["price"]),
                selected_hotel_name=selected_hotel.get("name") or "Selected hotel",
            )
        else:
            await skip_hotel(session_id)
    else:
        await skip_hotel(session_id)

    confirmed = await confirm_booking(session_id)
    confirmed["thread_id"] = session_id
    confirmed["auto_selected"] = {
        "flight": flight,
        "hotel": selected_hotel,
        "hotel_skipped": not bool(selected_hotel),
    }
    return confirmed


@mcp.resource("booking://{booking_reference}", mime_type="application/json")
async def booking_resource(booking_reference: str) -> str:
    """Read a confirmed booking as a JSON resource."""
    booking = await retrieve_booking(booking_reference)
    return json.dumps(booking, indent=2)


@mcp.prompt()
def plan_and_book_trip() -> str:
    """Guide the client through a complete travel booking."""
    return (
        "Collect origin, destination, travel date, budget, and whether hotel is needed. "
        "If the user wants the server to choose options, call create_travel_booking. "
        "If the user wants to compare options, call start_travel_plan, present the returned "
        "flight and hotel options, then call select_flight, select_hotel or skip_hotel, "
        "and confirm_booking."
    )


async def health(_: Any) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "travel-mcp-server"})


mcp.settings.streamable_http_path = "/mcp"


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
