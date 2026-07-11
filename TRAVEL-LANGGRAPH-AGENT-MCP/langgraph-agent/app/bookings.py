from __future__ import annotations

import json
from datetime import date
from typing import Any, Dict, Optional

from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, NullConnectionPool

from app.config import (
    BOOKINGS_TABLE_ENABLED,
    BOOKINGS_TABLE_NAME,
    BOOKINGS_TABLE_SETUP,
    LANGGRAPH_POSTGRES_POOL_MAX_SIZE,
    LANGGRAPH_POSTGRES_POOL_TIMEOUT,
    LANGGRAPH_POSTGRES_URI,
    logger,
)


_pool: Optional[NullConnectionPool] = None


def _table_identifier():
    return sql.Identifier(BOOKINGS_TABLE_NAME)


def _json(value: Any) -> str:
    return json.dumps(value or [])


def _float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _booking_pool() -> Optional[NullConnectionPool]:
    global _pool
    if not BOOKINGS_TABLE_ENABLED:
        return None
    if not LANGGRAPH_POSTGRES_URI:
        logger.warning("Bookings table is enabled but LANGGRAPH_POSTGRES_URI/DATABASE_URL is missing")
        return None
    if _pool is None:
        _pool = NullConnectionPool(
            conninfo=LANGGRAPH_POSTGRES_URI,
            max_size=LANGGRAPH_POSTGRES_POOL_MAX_SIZE,
            timeout=LANGGRAPH_POSTGRES_POOL_TIMEOUT,
            check=ConnectionPool.check_connection,
            kwargs={"autocommit": True, "row_factory": dict_row},
            open=True,
        )
        if BOOKINGS_TABLE_SETUP:
            setup_bookings_table()
    return _pool


def close_bookings_pool() -> None:
    if _pool is not None:
        _pool.close()


def setup_bookings_table() -> None:
    pool = _booking_pool()
    if pool is None:
        return

    table = _table_identifier()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        booking_reference TEXT PRIMARY KEY,
                        source_thread_id TEXT NOT NULL,
                        origin TEXT NOT NULL,
                        destination TEXT NOT NULL,
                        travel_date DATE,
                        origin_iata TEXT,
                        destination_iata TEXT,
                        selected_flight_info TEXT,
                        selected_flight_price NUMERIC(10, 2),
                        selected_hotel_name TEXT,
                        selected_hotel_price NUMERIC(10, 2),
                        hotel_skipped BOOLEAN DEFAULT FALSE,
                        total_budget NUMERIC(10, 2),
                        amount_planned NUMERIC(10, 2),
                        remaining_budget NUMERIC(10, 2),
                        activities JSONB DEFAULT '[]'::jsonb,
                        itinerary JSONB NOT NULL,
                        status TEXT DEFAULT 'confirmed',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                ).format(table=table)
            )
            cur.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} (source_thread_id)").format(
                    idx=sql.Identifier(f"idx_{BOOKINGS_TABLE_NAME}_source_thread_id"),
                    table=table,
                )
            )
            cur.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} (origin, destination)").format(
                    idx=sql.Identifier(f"idx_{BOOKINGS_TABLE_NAME}_route"),
                    table=table,
                )
            )
            cur.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} (created_at DESC)").format(
                    idx=sql.Identifier(f"idx_{BOOKINGS_TABLE_NAME}_created_at"),
                    table=table,
                )
            )
    logger.info("Bookings table setup complete for table %s", BOOKINGS_TABLE_NAME)


def save_booking_record(source_thread_id: str, state: Dict[str, Any], response: Dict[str, Any]) -> None:
    pool = _booking_pool()
    if pool is None:
        return

    itinerary = response.get("itinerary") or {}
    financials = itinerary.get("financials") or {}
    hotel = itinerary.get("hotel") or {}
    flight = itinerary.get("flight") or {}
    booking_reference = state.get("booking_reference")
    if not booking_reference:
        return

    travel_date = itinerary.get("travel_date")
    if travel_date:
        travel_date = date.fromisoformat(str(travel_date))

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                    INSERT INTO {table} (
                        booking_reference,
                        source_thread_id,
                        origin,
                        destination,
                        travel_date,
                        origin_iata,
                        destination_iata,
                        selected_flight_info,
                        selected_flight_price,
                        selected_hotel_name,
                        selected_hotel_price,
                        hotel_skipped,
                        total_budget,
                        amount_planned,
                        remaining_budget,
                        activities,
                        itinerary,
                        status,
                        updated_at
                    )
                    VALUES (
                        %(booking_reference)s,
                        %(source_thread_id)s,
                        %(origin)s,
                        %(destination)s,
                        %(travel_date)s,
                        %(origin_iata)s,
                        %(destination_iata)s,
                        %(selected_flight_info)s,
                        %(selected_flight_price)s,
                        %(selected_hotel_name)s,
                        %(selected_hotel_price)s,
                        %(hotel_skipped)s,
                        %(total_budget)s,
                        %(amount_planned)s,
                        %(remaining_budget)s,
                        %(activities)s::jsonb,
                        %(itinerary)s::jsonb,
                        %(status)s,
                        NOW()
                    )
                    ON CONFLICT (booking_reference)
                    DO UPDATE SET
                        source_thread_id = EXCLUDED.source_thread_id,
                        origin = EXCLUDED.origin,
                        destination = EXCLUDED.destination,
                        travel_date = EXCLUDED.travel_date,
                        origin_iata = EXCLUDED.origin_iata,
                        destination_iata = EXCLUDED.destination_iata,
                        selected_flight_info = EXCLUDED.selected_flight_info,
                        selected_flight_price = EXCLUDED.selected_flight_price,
                        selected_hotel_name = EXCLUDED.selected_hotel_name,
                        selected_hotel_price = EXCLUDED.selected_hotel_price,
                        hotel_skipped = EXCLUDED.hotel_skipped,
                        total_budget = EXCLUDED.total_budget,
                        amount_planned = EXCLUDED.amount_planned,
                        remaining_budget = EXCLUDED.remaining_budget,
                        activities = EXCLUDED.activities,
                        itinerary = EXCLUDED.itinerary,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    """
                ).format(table=_table_identifier()),
                {
                    "booking_reference": booking_reference,
                    "source_thread_id": source_thread_id,
                    "origin": itinerary.get("origin"),
                    "destination": itinerary.get("destination"),
                    "travel_date": travel_date,
                    "origin_iata": itinerary.get("origin_iata"),
                    "destination_iata": itinerary.get("destination_iata"),
                    "selected_flight_info": flight.get("summary"),
                    "selected_flight_price": _float(flight.get("price")),
                    "selected_hotel_name": hotel.get("name"),
                    "selected_hotel_price": _float(hotel.get("price")),
                    "hotel_skipped": bool(hotel.get("skipped")),
                    "total_budget": _float(financials.get("total_budget")),
                    "amount_planned": _float(financials.get("amount_planned")),
                    "remaining_budget": _float(financials.get("remaining_budget")),
                    "activities": _json(itinerary.get("activities")),
                    "itinerary": json.dumps(itinerary),
                    "status": itinerary.get("booking_status", "confirmed"),
                },
            )
    logger.info("Saved booking record %s", booking_reference)


def get_booking_record(booking_reference: str) -> Optional[Dict[str, Any]]:
    pool = _booking_pool()
    if pool is None:
        return None

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT * FROM {table} WHERE booking_reference = %(booking_reference)s").format(
                    table=_table_identifier()
                ),
                {"booking_reference": booking_reference.upper()},
            )
            row = cur.fetchone()

    if not row:
        return None

    itinerary = row.get("itinerary") or {}
    return {
        "booking_reference": row["booking_reference"],
        "is_booked": row["status"] == "confirmed",
        "origin": row["origin"],
        "destination": row["destination"],
        "travel_date_formatted": row["travel_date"].isoformat() if row.get("travel_date") else None,
        "origin_iata": row.get("origin_iata"),
        "destination_iata": row.get("destination_iata"),
        "selected_flight_info": row.get("selected_flight_info"),
        "selected_flight_price": _float(row.get("selected_flight_price")),
        "selected_hotel_name": row.get("selected_hotel_name"),
        "selected_hotel_price": _float(row.get("selected_hotel_price")),
        "hotel_skipped": row.get("hotel_skipped"),
        "total_budget": _float(row.get("total_budget")),
        "remaining_budget": _float(row.get("remaining_budget")),
        "activities": row.get("activities") or [],
        "itinerary": itinerary,
    }
