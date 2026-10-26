import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("loyalty_tier IN ('None', 'Silver', 'Gold', 'Platinum')"),
        {"schema": "airline"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    phone: Mapped[str] = mapped_column(String(30))
    loyalty_member: Mapped[bool] = mapped_column(Boolean)
    loyalty_tier: Mapped[str] = mapped_column(String(20))
    registered_at: Mapped[date] = mapped_column(Date)


class Aircraft(Base):
    __tablename__ = "aircraft"
    __table_args__ = (CheckConstraint("seats > 0"), {"schema": "airline"})
    id: Mapped[int] = mapped_column(primary_key=True)
    registration: Mapped[str] = mapped_column(String(15), unique=True)
    model: Mapped[str] = mapped_column(String(50))
    seats: Mapped[int]


class Flight(Base):
    __tablename__ = "flights"
    __table_args__ = (
        CheckConstraint("origin <> destination"),
        CheckConstraint("scheduled_arrival > scheduled_departure"),
        CheckConstraint("delay_minutes >= 0"),
        CheckConstraint("status IN ('Arrived', 'Delayed', 'Cancelled')"),
        CheckConstraint(
            "(status = 'Cancelled' AND actual_departure IS NULL AND actual_arrival IS NULL) OR "
            "(status <> 'Cancelled' AND actual_departure IS NOT NULL AND actual_arrival > actual_departure)"
        ),
        {"schema": "airline"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(10))
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    aircraft_id: Mapped[int] = mapped_column(ForeignKey("airline.aircraft.id"))
    scheduled_departure: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    scheduled_arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), index=True)
    delay_minutes: Mapped[int]


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("total_amount >= 0"),
        CheckConstraint(
            "travel_class IN ('Economy', 'Premium Economy', 'Business', 'First Class')"
        ),
        CheckConstraint("ticket_status IN ('Flown', 'Cancelled', 'Refunded')"),
        {"schema": "airline"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("airline.customers.id"), index=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("airline.flights.id"), index=True)
    booking_reference: Mapped[str] = mapped_column(String(12), unique=True)
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    travel_class: Mapped[str] = mapped_column(String(20))
    ticket_status: Mapped[str] = mapped_column(String(20))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0"),
        CheckConstraint("status IN ('Completed', 'Refunded', 'Refund Pending')"),
        {"schema": "airline"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("airline.bookings.id"), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    method: Mapped[str] = mapped_column(String(25))
    status: Mapped[str] = mapped_column(String(20))


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        CheckConstraint("status IN ('Open', 'In Progress', 'Resolved')"),
        CheckConstraint("resolved_at IS NULL OR resolved_at >= created_at"),
        {"schema": "airline"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("airline.customers.id"), index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("airline.bookings.id"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint("status IN ('Open', 'In Progress', 'Resolved')"),
        CheckConstraint("resolved_at IS NULL OR resolved_at >= submitted_at"),
        {"schema": "airline"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("airline.customers.id"), index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("airline.bookings.id"), index=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("airline.flights.id"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_details: Mapped[str | None] = mapped_column(Text)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("service_request_id IS NOT NULL OR complaint_id IS NOT NULL"),
        {"schema": "airline"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("airline.customers.id"), index=True)
    service_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("airline.service_requests.id")
    )
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("airline.complaints.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String(10))
    participants: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = {"schema": "app"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("app.analyses.id"))
    question: Mapped[str] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("refresh_interval_hours IN (0, 1, 4, 12, 24)"),
        Index("ix_reports_next_refresh_at", "next_refresh_at"),
        {"schema": "app"},
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("app.analyses.id"))
    title: Mapped[str] = mapped_column(String(120))
    question: Mapped[str] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(JSON)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_interval_hours: Mapped[int] = mapped_column(Integer, default=0)
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_status: Mapped[str] = mapped_column(String(20), default="success")
    refresh_error: Mapped[str | None] = mapped_column(String(500))


AIRLINE_TABLES = {
    table.name: table for table in Base.metadata.sorted_tables if table.schema == "airline"
}
