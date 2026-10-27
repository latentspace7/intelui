import argparse
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.crm_models import CRM_TABLES
from app.db import SessionLocal


def build_crm_dataset(reference: date, batch: int = 0) -> dict[str, list[dict]]:
    if not 0 <= batch <= 99:
        raise ValueError("Batch must be between 0 and 99.")
    offset = batch * 100000
    data: dict[str, list[dict]] = {name: [] for name in CRM_TABLES}
    staff = [
        "Alex Rivera",
        "Morgan Chen",
        "Sam Patel",
        "Taylor Reed",
        "Jordan Kim",
        "Riley Brooks",
        "Casey Shah",
        "Jamie Ellis",
    ]
    companies = [
        "Northstar Labs",
        "Cedar Works",
        "Harbor Studio",
        "Summit Logistics",
        "Juniper Health",
        "Orbit Systems",
        "Maple Foods",
        "Bluebird Media",
        "Atlas Retail",
        "Cobalt Energy",
        "Meadow Learning",
        "Aster Design",
        "Willow Services",
        "Beacon Digital",
        "Riverstone Group",
        "Lumen Analytics",
        "Pinecrest Supply",
        "Coral Networks",
        "Evergreen Travel",
        "Nimbus Software",
        "Copperfield Co",
        "Silverline Events",
        "Oakridge Partners",
        "Solstice Creative",
    ]
    stages = ["Lead", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]
    for i, name in enumerate(staff, 1):
        data["staff"].append(
            dict(
                id=offset + i,
                name=name,
                team=["Sales", "Customer success"][i % 2],
                email=f"staff{offset + i}@example.invalid",
            )
        )
    for i, (name, price, fee) in enumerate(
        [
            ("Workspace Essential", 35, 250),
            ("Workspace Growth", 65, 500),
            ("Workspace Enterprise", 110, 1200),
            ("Support Plus", 25, 100),
            ("Analytics Studio", 80, 750),
            ("Automation Suite", 95, 900),
        ],
        1,
    ):
        data["products"].append(
            dict(
                id=offset + i,
                name=name,
                category="Subscription" if i < 4 else "Add-on",
                monthly_unit_price=Decimal(price),
                setup_fee=Decimal(fee),
                description=f"Synthetic {name.lower()} service, priced per seat per month. Setup charged once; taxes excluded.",
            )
        )
    for i, original_name in enumerate(companies, 1):
        company_id = offset + i
        name = original_name if batch == 0 else f"{original_name} · batch {batch}"
        owner_id = offset + (i - 1) % 8 + 1
        income = Decimal(18000 + i * 1750)
        expenses = Decimal(12000 + i * 1100)
        budget = Decimal(1000 + i * 125)
        data["companies"].append(
            dict(
                id=company_id,
                name=name,
                industry=[
                    "Technology",
                    "Services",
                    "Retail",
                    "Healthcare",
                    "Logistics",
                    "Education",
                ][(i - 1) % 6],
                status=["Active", "Prospect", "Onboarding"][(i - 1) % 3],
                region=["APAC", "Europe", "North America"][(i - 1) % 3],
                owner_id=owner_id,
                annual_revenue=income * 12,
                monthly_income=income,
                monthly_expenses=expenses,
                monthly_budget=budget,
                description=f"{name} is a fictional business evaluating collaboration and analytics services.",
                created_at=reference - timedelta(days=220 + i * 5),
            )
        )
        for j, role in enumerate(["Operations lead", "Finance manager", "Director"]):
            contact_id = offset + (i - 1) * 3 + j + 1
            data["contacts"].append(
                dict(
                    id=contact_id,
                    company_id=company_id,
                    name=f"{['Avery', 'Quinn', 'Cameron'][j]} {['Stone', 'Park', 'Lane', 'Wells'][(i - 1) % 4]} {i}",
                    email=f"contact{contact_id}@example.invalid",
                    role=role,
                    is_primary=j == 0,
                )
            )
        for j in range(4):
            deal_id = offset + (i - 1) * 4 + j + 1
            stage = stages[(i + j - 1) % 6]
            data["deals"].append(
                dict(
                    id=deal_id,
                    company_id=company_id,
                    contact_id=offset + (i - 1) * 3 + 1,
                    owner_id=owner_id,
                    name=f"{name} · {['Workspace rollout', 'Analytics expansion', 'Support renewal', 'Automation pilot'][j]}",
                    stage=stage,
                    amount=Decimal(4500 + i * 650 + j * 1700),
                    probability=[10, 30, 55, 80, 100, 0][stages.index(stage)],
                    created_at=reference - timedelta(days=150 - i * 3 - j * 7),
                    expected_close=reference + timedelta(days=(i + j * 4) % 40 - 10),
                    description=f"{['New service agreement', 'Team expansion', 'Annual renewal', 'Pilot programme'][j]} for {name}. All deal values are synthetic USD contract values.",
                )
            )
            for k, title in enumerate(
                ["Confirm requirements", "Review service agreement", "Schedule stakeholder call"]
            ):
                data["tasks"].append(
                    dict(
                        id=offset + (i - 1) * 12 + j * 3 + k + 1,
                        company_id=company_id,
                        deal_id=deal_id,
                        owner_id=owner_id,
                        title=f"{title} · {name}",
                        status=["Outstanding", "In progress", "Complete"][(i + j + k) % 3],
                        priority=["High", "Medium", "Low"][(i + k) % 3],
                        due_date=reference + timedelta(days=k * 5 + j - i % 7),
                    )
                )
        for j, title in enumerate(
            ["Company profile", "Service agreement", "Billing details", "Delivery brief"]
        ):
            doc_id = offset + (i - 1) * 4 + j + 1
            extracted_budget = str(budget + 250 if (i + j) % 4 == 0 else budget)
            body = f"SYNTHETIC DOCUMENT — {title}\nCompany: {name}\nMonthly budget (USD): {extracted_budget}\nPrimary region: {data['companies'][-1]['region']}\nPrepared for demonstration only. No real personal or business information."
            data["documents"].append(
                dict(
                    id=doc_id,
                    company_id=company_id,
                    title=f"{title} · {name}",
                    document_type=title,
                    body=body,
                    received_at=reference - timedelta(days=i + j + 10),
                    expires_at=reference + timedelta(days=60 - i * 3 + j),
                )
            )
            for k, (field, declared, extracted) in enumerate(
                [
                    ("Company", name, name),
                    ("Monthly budget (USD)", str(budget), extracted_budget),
                    (
                        "Primary region",
                        data["companies"][-1]["region"],
                        data["companies"][-1]["region"],
                    ),
                ]
            ):
                data["document_fields"].append(
                    dict(
                        id=offset + (i - 1) * 12 + j * 3 + k + 1,
                        document_id=doc_id,
                        field_name=field,
                        declared_value=declared,
                        extracted_value=extracted,
                        review_status="Pending",
                    )
                )
        for j in range(3):
            data["quotes"].append(
                dict(
                    id=offset + (i - 1) * 3 + j + 1,
                    company_id=company_id,
                    product_id=offset + j + 1,
                    quantity=10 + i,
                    months=12,
                    discount_percent=Decimal(j * 5),
                    status="Draft",
                )
            )
        for month in range(6):
            when = reference - timedelta(days=150 - month * 30)
            for k, (direction, category, amount) in enumerate(
                [
                    ("Inflow", "Service income", income + Decimal(month * 300)),
                    ("Outflow", "Payroll", expenses * Decimal("0.65")),
                    ("Outflow", "Operations", expenses * Decimal("0.35")),
                ]
            ):
                data["cash_entries"].append(
                    dict(
                        id=offset + (i - 1) * 18 + month * 3 + k + 1,
                        company_id=company_id,
                        occurred_at=when,
                        description=f"{category} · {name}",
                        category=category,
                        direction=direction,
                        amount=amount.quantize(Decimal("0.01")),
                    )
                )
        for j in range(8):
            category = ["Email", "Call", "Meeting", "Note"][j % 4]
            data["activities"].append(
                dict(
                    id=offset + (i - 1) * 8 + j + 1,
                    company_id=company_id,
                    contact_id=offset + (i - 1) * 3 + 1,
                    owner_id=owner_id,
                    title=[
                        "Requirements discussed",
                        "Proposal shared",
                        "Delivery reviewed",
                        "Account update",
                    ][j % 4],
                    category=category,
                    description=f"Synthetic {category.lower()} with {name}: reviewed requirements and agreed to follow up on the service proposal.",
                    occurred_at=datetime.combine(
                        reference - timedelta(days=30 - j * 4), datetime.min.time(), UTC
                    )
                    + timedelta(hours=9 + j),
                )
            )
        data["relationships"].append(
            dict(
                id=offset + i,
                source_company_id=company_id,
                target_company_id=offset + i % 24 + 1,
                relationship=["Partner", "Supplier", "Referral"][(i - 1) % 3],
            )
        )
        for j, (label, observed, threshold, operator, description) in enumerate(
            [
                (
                    "Monthly spending within budget",
                    Decimal(900 + i * 80),
                    budget,
                    "lte",
                    "Demo procurement rule: proposed monthly service spend must fit the recorded budget.",
                ),
                (
                    "Primary contact assigned",
                    Decimal(1),
                    Decimal(1),
                    "eq",
                    "Demo onboarding rule: an account needs one primary contact.",
                ),
                (
                    "Required documents received",
                    None if i % 5 == 0 else Decimal(i % 5),
                    Decimal(4),
                    "gte",
                    "Demo onboarding rule: four documents are required. Missing observations need review.",
                ),
                (
                    "Document validity remaining (days)",
                    Decimal(60 - i * 3),
                    Decimal(0),
                    "gte",
                    "Demo document rule: the recorded document must not be expired as of the reference date.",
                ),
            ]
        ):
            data["rule_checks"].append(
                dict(
                    id=offset + (i - 1) * 4 + j + 1,
                    company_id=company_id,
                    name=label,
                    observed_value=observed,
                    threshold=threshold,
                    operator=operator,
                    description=description,
                    rule_version="demo-2026.1",
                    evaluated_at=reference,
                )
            )
        for j, title in enumerate(
            ["Discovery", "Agreement", "Data setup", "Team training", "Go live"]
        ):
            data["milestones"].append(
                dict(
                    id=offset + (i - 1) * 5 + j + 1,
                    company_id=company_id,
                    owner_id=owner_id,
                    title=title,
                    status="Complete"
                    if j < i % 3
                    else "Blocked"
                    if j == i % 3 and i % 4 == 0
                    else "In progress"
                    if j == i % 3
                    else "Upcoming",
                    due_date=reference + timedelta(days=(j - 2) * 7 + i % 5),
                    sequence=j + 1,
                )
            )
    return data


def seed_crm(batch: int = 0) -> dict[str, int]:
    dataset = build_crm_dataset(settings.demo_reference_date, batch)
    counts = {}
    with SessionLocal.begin() as session:
        session.execute(text("SELECT pg_advisory_xact_lock(482901)"))
        for name, table in CRM_TABLES.items():
            rows = dataset[name]
            if rows:
                outcome = session.execute(
                    insert(table).values(rows).on_conflict_do_nothing().returning(table.c.id)
                )
                counts[name] = len(outcome.scalars().all())
                maximum = session.scalar(select(func.max(table.c.id)))
                session.execute(
                    text("SELECT setval(pg_get_serial_sequence(:table, 'id'), :maximum, true)"),
                    {"table": f"crm.{name}", "maximum": maximum},
                )
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch",
        type=int,
        default=0,
        help="Append a deterministic synthetic batch (0–99); repeat runs preserve existing rows.",
    )
    print(seed_crm(parser.parse_args().batch))
