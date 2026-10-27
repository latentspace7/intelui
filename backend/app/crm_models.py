from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
)

metadata = MetaData(schema="crm")


def identifier():
    return Column("id", Integer, primary_key=True, autoincrement=True)


def reference(name, target, nullable=False):
    return Column(name, Integer, ForeignKey(f"crm.{target}.id"), nullable=nullable, index=True)


Table(
    "staff",
    metadata,
    identifier(),
    Column("name", String(100), nullable=False),
    Column("team", String(60), nullable=False),
    Column("email", String(150), nullable=False, unique=True),
)
Table(
    "companies",
    metadata,
    identifier(),
    Column("name", String(120), nullable=False, unique=True),
    Column("industry", String(60), nullable=False),
    Column("status", String(30), nullable=False),
    Column("region", String(60), nullable=False),
    reference("owner_id", "staff"),
    Column("annual_revenue", Numeric(14, 2), nullable=False),
    Column("monthly_income", Numeric(12, 2), nullable=False),
    Column("monthly_expenses", Numeric(12, 2), nullable=False),
    Column("monthly_budget", Numeric(12, 2), nullable=False),
    Column("description", Text, nullable=False),
    Column("created_at", Date, nullable=False),
    CheckConstraint(
        "annual_revenue >= 0 AND monthly_income >= 0 AND monthly_expenses >= 0 AND monthly_budget >= 0"
    ),
)
Table(
    "contacts",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    Column("name", String(100), nullable=False),
    Column("email", String(150), nullable=False, unique=True),
    Column("role", String(60), nullable=False),
    Column("is_primary", Boolean, nullable=False),
)
Table(
    "deals",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    reference("contact_id", "contacts"),
    reference("owner_id", "staff"),
    Column("name", String(150), nullable=False),
    Column("stage", String(30), nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("probability", Integer, nullable=False),
    Column("created_at", Date, nullable=False),
    Column("expected_close", Date, nullable=False),
    Column("description", Text, nullable=False),
    CheckConstraint("amount >= 0 AND probability BETWEEN 0 AND 100"),
    CheckConstraint("stage IN ('Lead', 'Qualified', 'Proposal', 'Negotiation', 'Won', 'Lost')"),
)
Table(
    "tasks",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    reference("deal_id", "deals"),
    reference("owner_id", "staff"),
    Column("title", String(150), nullable=False),
    Column("status", String(30), nullable=False),
    Column("priority", String(20), nullable=False),
    Column("due_date", Date, nullable=False),
    CheckConstraint("status IN ('Outstanding', 'In progress', 'Complete')"),
)
Table(
    "documents",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    Column("title", String(150), nullable=False),
    Column("document_type", String(60), nullable=False),
    Column("body", Text, nullable=False),
    Column("received_at", Date, nullable=False),
    Column("expires_at", Date, nullable=False),
)
Table(
    "document_fields",
    metadata,
    identifier(),
    reference("document_id", "documents"),
    Column("field_name", String(80), nullable=False),
    Column("declared_value", String(200), nullable=False),
    Column("extracted_value", String(200), nullable=False),
    Column("review_status", String(30), nullable=False),
    CheckConstraint("review_status IN ('Pending', 'Accepted', 'Needs correction')"),
)
Table(
    "products",
    metadata,
    identifier(),
    Column("name", String(100), nullable=False),
    Column("category", String(60), nullable=False),
    Column("monthly_unit_price", Numeric(12, 2), nullable=False),
    Column("setup_fee", Numeric(12, 2), nullable=False),
    Column("description", Text, nullable=False),
    CheckConstraint("monthly_unit_price >= 0 AND setup_fee >= 0"),
)
Table(
    "quotes",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    reference("product_id", "products"),
    Column("quantity", Integer, nullable=False),
    Column("months", Integer, nullable=False),
    Column("discount_percent", Numeric(5, 2), nullable=False),
    Column("status", String(30), nullable=False),
    CheckConstraint(
        "quantity BETWEEN 1 AND 10000 AND months BETWEEN 1 AND 120 AND discount_percent BETWEEN 0 AND 100"
    ),
)
Table(
    "cash_entries",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    Column("occurred_at", Date, nullable=False),
    Column("description", String(150), nullable=False),
    Column("category", String(60), nullable=False),
    Column("direction", String(20), nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    CheckConstraint("direction IN ('Inflow', 'Outflow') AND amount > 0"),
)
Table(
    "activities",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    reference("contact_id", "contacts"),
    reference("owner_id", "staff"),
    Column("title", String(150), nullable=False),
    Column("category", String(30), nullable=False),
    Column("description", Text, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)
Table(
    "relationships",
    metadata,
    identifier(),
    reference("source_company_id", "companies"),
    reference("target_company_id", "companies"),
    Column("relationship", String(60), nullable=False),
    CheckConstraint("source_company_id <> target_company_id"),
)
Table(
    "rule_checks",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    Column("name", String(120), nullable=False),
    Column("observed_value", Numeric(14, 2), nullable=True),
    Column("threshold", Numeric(14, 2), nullable=False),
    Column("operator", String(5), nullable=False),
    Column("description", Text, nullable=False),
    Column("rule_version", String(30), nullable=False),
    Column("evaluated_at", Date, nullable=False),
    CheckConstraint("operator IN ('gte', 'lte', 'eq')"),
)
Table(
    "milestones",
    metadata,
    identifier(),
    reference("company_id", "companies"),
    reference("owner_id", "staff"),
    Column("title", String(150), nullable=False),
    Column("status", String(30), nullable=False),
    Column("due_date", Date, nullable=False),
    Column("sequence", Integer, nullable=False),
    CheckConstraint("status IN ('Complete', 'In progress', 'Blocked', 'Upcoming')"),
)
Table(
    "audit_events",
    metadata,
    identifier(),
    Column("entity", String(30), nullable=False),
    Column("record_id", Integer, nullable=False),
    Column("previous_status", String(30), nullable=False),
    Column("new_status", String(30), nullable=False),
    Column("actor", String(60), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)

CRM_TABLES = {table.name: table for table in metadata.sorted_tables}
