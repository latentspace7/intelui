import argparse
import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import SessionLocal
from app.models import (
    AIRLINE_TABLES,
    Customer,
)


def build_dataset(reference: date) -> dict[str, list[dict]]:
    rng = random.Random(42)
    end = datetime.combine(reference, datetime.min.time(), UTC)
    start = end - timedelta(days=175)
    data: dict[str, list[dict]] = {name: [] for name in AIRLINE_TABLES}
    names = ["Alex", "Morgan", "Sam", "Taylor", "Jordan", "Riley", "Casey", "Jamie"]
    surnames = ["Rivera", "Chen", "Patel", "Reed", "Kim"]
    for i in range(1, 41):
        tier = ["None", "Silver", "Gold", "Platinum"][i % 4]
        data["customers"].append(
            dict(
                id=i,
                name=f"{names[(i - 1) % 8]} {surnames[(i - 1) // 8]}",
                email=f"traveler{i:02}@example.invalid",
                phone=f"+1-202-555-{100 + i:04}",
                loyalty_member=tier != "None",
                loyalty_tier=tier,
                registered_at=reference - timedelta(days=400 + i * 20),
            )
        )
    for i, model, seats in [
        (1, "Boeing 787-9", 290),
        (2, "Airbus A350-900", 315),
        (3, "Airbus A321neo", 200),
    ]:
        data["aircraft"].append(dict(id=i, registration=f"AV-DEMO{i}", model=model, seats=seats))
    routes = [
        ("SYD", "SIN"),
        ("MEL", "LAX"),
        ("SIN", "LHR"),
        ("BKK", "SYD"),
        ("LAX", "JFK"),
        ("SYD", "MEL"),
    ]
    for i in range(1, 37):
        departure = start + timedelta(days=round((i - 1) * 169 / 35), hours=8 + i % 10)
        origin, destination = routes[(i - 1) % len(routes)]
        cancelled = i % 9 == 0 or i == 7
        delay = 0 if cancelled or i % 3 else rng.choice([35, 60, 95, 140])
        arrival = departure + timedelta(hours=2 + i % 12)
        data["flights"].append(
            dict(
                id=i,
                flight_number=f"AV{100 + i % 6}",
                origin=origin,
                destination=destination,
                aircraft_id=i % 3 + 1,
                scheduled_departure=departure,
                scheduled_arrival=arrival,
                actual_departure=None if cancelled else departure + timedelta(minutes=delay),
                actual_arrival=None if cancelled else arrival + timedelta(minutes=delay),
                status="Cancelled" if cancelled else "Delayed" if delay else "Arrived",
                delay_minutes=delay,
            )
        )
    classes = ["Economy", "Premium Economy", "Business", "First Class"]
    for i in range(1, 101):
        flight = data["flights"][(i * 7) % 36]
        customer_id = ((i * 3) % 12 + 1) if i <= 30 else ((i * 7) % 40 + 1)
        travel_class = classes[(i * 7 + i // 7) % 4]
        amount = Decimal(
            [180, 480, 1650, 3400][classes.index(travel_class)] + rng.randrange(20, 350)
        )
        cancelled = flight["status"] == "Cancelled"
        refunded = cancelled and i % 2 == 0
        booked = flight["scheduled_departure"] - timedelta(days=rng.randint(4, 40))
        data["bookings"].append(
            dict(
                id=i,
                customer_id=customer_id,
                flight_id=flight["id"],
                booking_reference=f"AV{i:06}",
                booked_at=booked,
                travel_class=travel_class,
                ticket_status="Refunded" if refunded else "Cancelled" if cancelled else "Flown",
                total_amount=amount,
            )
        )
        data["payments"].append(
            dict(
                id=i,
                booking_id=i,
                amount=amount,
                currency="USD",
                paid_at=booked + timedelta(minutes=5),
                method=["Card", "Bank Transfer", "Digital Wallet"][i % 3],
                status="Refunded" if refunded else "Refund Pending" if cancelled else "Completed",
            )
        )
        case_time = flight["scheduled_arrival"] + timedelta(hours=3)
        service_id = None
        complaint_id = None
        if cancelled or flight["delay_minutes"] or i % 5 == 0:
            service_id = len(data["service_requests"]) + 1
            resolved = refunded if cancelled else i % 3 != 0
            data["service_requests"].append(
                dict(
                    id=service_id,
                    customer_id=customer_id,
                    booking_id=i,
                    category="Refund"
                    if cancelled
                    else "Flight Delay"
                    if flight["delay_minutes"]
                    else "Baggage",
                    description=f"Synthetic support case for booking AV{i:06}.",
                    priority="High" if cancelled else "Medium",
                    status="Resolved" if resolved else "Open" if i % 2 else "In Progress",
                    created_at=case_time,
                    resolved_at=case_time + timedelta(days=2) if resolved else None,
                )
            )
        if cancelled or flight["delay_minutes"] or i % 7 == 0:
            complaint_id = len(data["complaints"]) + 1
            resolved = refunded if cancelled else i % 4 == 0
            data["complaints"].append(
                dict(
                    id=complaint_id,
                    customer_id=customer_id,
                    booking_id=i,
                    flight_id=flight["id"],
                    category="Cancellation"
                    if cancelled
                    else "Delay"
                    if flight["delay_minutes"]
                    else "Service Quality",
                    severity="High" if cancelled else "Medium",
                    description=f"Synthetic customer complaint about {flight['flight_number']}.",
                    status="Resolved" if resolved else "Open",
                    submitted_at=case_time + timedelta(hours=1),
                    resolved_at=case_time + timedelta(days=3) if resolved else None,
                    resolution_details="Customer notified; case reviewed and closed."
                    if resolved
                    else None,
                )
            )
        if service_id or complaint_id:
            data["conversations"].append(
                dict(
                    id=len(data["conversations"]) + 1,
                    customer_id=customer_id,
                    service_request_id=service_id,
                    complaint_id=complaint_id,
                    occurred_at=case_time + timedelta(hours=2),
                    channel=["Email", "Chat", "Phone"][i % 3],
                    participants=f"Customer {customer_id}; demo agent {i % 5 + 1}",
                    summary="Customer requested a status update. Agent acknowledged the case and explained next steps.",
                )
            )
    return data


def seed(reset: bool = False) -> dict[str, int]:
    dataset = build_dataset(settings.demo_reference_date)
    with SessionLocal.begin() as session:
        if reset:
            for table in reversed(list(AIRLINE_TABLES.values())):
                session.execute(delete(table))
        existing = session.scalar(select(Customer.id).limit(1))
        if existing is not None and not reset:
            return {"already_seeded": 1}
        for name, table in AIRLINE_TABLES.items():
            if dataset[name]:
                session.execute(insert(table).values(dataset[name]).on_conflict_do_nothing())
    return {name: len(rows) for name, rows in dataset.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset", action="store_true", help="Replace synthetic airline data; keep saved reports."
    )
    print(seed(parser.parse_args().reset))
