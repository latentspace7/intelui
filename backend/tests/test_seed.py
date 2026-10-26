from collections import Counter
from datetime import date

from app.seed import build_dataset


def test_deterministic_and_relational_integrity():
    reference = date(2026, 10, 26)
    data = build_dataset(reference)
    assert data == build_dataset(reference)
    assert len(data["bookings"]) == 100
    flights = {row["id"]: row for row in data["flights"]}
    bookings = {row["id"]: row for row in data["bookings"]}
    customers = {row["id"] for row in data["customers"]}
    payments = {row["booking_id"]: row for row in data["payments"]}
    assert {b["travel_class"] for b in bookings.values()} == {
        "Economy",
        "Premium Economy",
        "Business",
        "First Class",
    }
    assert len({b["booked_at"].strftime("%Y-%m") for b in bookings.values()}) >= 6
    assert any(b["booked_at"].month == reference.month for b in bookings.values())
    assert max(Counter(b["customer_id"] for b in bookings.values()).values()) > 5
    for booking in bookings.values():
        flight = flights[booking["flight_id"]]
        assert booking["customer_id"] in customers
        assert booking["booked_at"] < flight["scheduled_departure"]
        payment = payments[booking["id"]]
        assert payment["amount"] == booking["total_amount"]
        assert payment["paid_at"] >= booking["booked_at"]
        if flight["status"] == "Cancelled":
            assert flight["actual_departure"] is None
            assert flight["actual_arrival"] is None
            assert booking["ticket_status"] in ("Refunded", "Cancelled")
            assert payment["status"] in ("Refunded", "Refund Pending")
        else:
            assert flight["actual_arrival"] > flight["actual_departure"]
            assert (
                int(
                    (flight["actual_departure"] - flight["scheduled_departure"]).total_seconds()
                    / 60
                )
                == flight["delay_minutes"]
            )
    for case_type, created in (("complaints", "submitted_at"), ("service_requests", "created_at")):
        for case in data[case_type]:
            booking = bookings[case["booking_id"]]
            assert case["customer_id"] == booking["customer_id"]
            assert (case["status"] == "Resolved") == (case["resolved_at"] is not None)
            if case["resolved_at"]:
                assert case["resolved_at"] >= case[created]
                assert case["resolved_at"].date() <= reference
            if "flight_id" in case:
                assert case["flight_id"] == booking["flight_id"]
    for conversation in data["conversations"]:
        for key, table in (
            ("service_request_id", "service_requests"),
            ("complaint_id", "complaints"),
        ):
            if conversation[key]:
                case = next(row for row in data[table] if row["id"] == conversation[key])
                assert conversation["customer_id"] == case["customer_id"]


def test_seed_includes_required_analytical_scenarios():
    data = build_dataset(date(2026, 10, 26))
    bookings = {b["id"]: b for b in data["bookings"]}
    assert any(
        c["status"] != "Resolved" and bookings[c["booking_id"]]["travel_class"] == "Business"
        for c in data["complaints"]
    )
    assert any(
        r["category"] == "Refund" and r["status"] != "Resolved" for r in data["service_requests"]
    )
    assert max(Counter(c["customer_id"] for c in data["complaints"]).values()) > 1
