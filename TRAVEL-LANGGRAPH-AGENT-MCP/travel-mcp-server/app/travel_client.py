from __future__ import annotations

import uuid
from typing import Any

import httpx
from mcp.server.fastmcp.exceptions import ToolError

from app.config import REQUEST_TIMEOUT_SECONDS, TRAVEL_AGENT_API_URL, logger


def new_thread_id() -> str:
    return f"mcp-{uuid.uuid4().hex[:12]}"


async def call_agent(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            logger.info("Calling travel backend action=%s", payload.get("action"))
            response = await client.post(TRAVEL_AGENT_API_URL, json=payload)
    except httpx.RequestError as exc:
        raise ToolError(f"Travel backend is unavailable: {exc}") from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise ToolError(f"Travel backend rejected the request: {detail}")

    try:
        return response.json()
    except ValueError as exc:
        raise ToolError("Travel backend returned a non-JSON response") from exc


def select_cheapest(items: list[dict[str, Any]], price_key: str = "price") -> dict[str, Any] | None:
    priced = [item for item in items if item.get(price_key) is not None]
    if not priced:
        return None
    return min(priced, key=lambda item: float(item[price_key]))


def compact_itinerary(response: dict[str, Any]) -> dict[str, Any]:
    itinerary = response.get("itinerary") or {}
    return {
        "thread_id": response.get("source_thread_id") or response.get("thread_id"),
        "booking_reference": response.get("booking_reference") or itinerary.get("booking_reference"),
        "booking_status": itinerary.get("booking_status"),
        "origin": itinerary.get("origin") or response.get("origin"),
        "destination": itinerary.get("destination") or response.get("destination"),
        "travel_date": itinerary.get("travel_date") or response.get("travel_date_formatted"),
        "flight": itinerary.get("flight"),
        "hotel": itinerary.get("hotel"),
        "financials": itinerary.get("financials"),
        "activities": itinerary.get("activities") or response.get("activities") or [],
        "data_source_notes": response.get("data_source_notes") or [],
    }

